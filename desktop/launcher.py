"""Entry point for the desktop build. Boots the exact same Django app used
in production, serves it locally via waitress (a pure-Python WSGI server —
no fork(), so it works on Windows, unlike gunicorn), and shows it in a
native window via pywebview instead of a browser tab. Same interface, same
conversion logic, zero network dependency: everything runs on localhost.
"""
import os
import secrets
import socket
import sys
import threading

# Make the bundled app package importable, whether we're running from the
# PyInstaller bundle (sys._MEIPASS) or straight from source during dev.
BASE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Must be set before Django (or anything importing doc4ai.settings) loads.
os.environ['DOC4AI_DESKTOP'] = '1'
os.environ.setdefault('DJANGO_SECRET_KEY', secrets.token_urlsafe(50))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'doc4ai.settings')
os.environ.setdefault('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1')

for folder in ('media', 'staticfiles'):
    os.makedirs(os.path.join(BASE_DIR, folder), exist_ok=True)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def _serve(port: int) -> None:
    import django
    django.setup()
    from waitress import serve
    from doc4ai.wsgi import application
    serve(application, host='127.0.0.1', port=port, threads=4)


def _wait_until_ready(port: int, timeout: float = 15.0) -> None:
    import time
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.1)


def _patch_pywebview_file_dialog_threading() -> None:
    """pywebview 6.2.1's WinForms backend calls dialog.ShowDialog() straight
    from whatever thread invokes create_file_dialog. Every other window-
    mutating function in that same module (set_title, toggle_fullscreen,
    minimize, ...) checks `i.InvokeRequired` and marshals onto the UI thread
    via `i.Invoke(...)` first — create_file_dialog is missing that check.
    Since js_api calls arrive on a non-UI thread, this is a real WinForms
    thread-affinity violation: it sometimes "works" by accident and
    sometimes deadlocks the whole window with no dialog ever appearing
    (reproduced via repeated calls during testing). Wrap it the same way
    the library's own working functions already do.
    """
    if sys.platform != 'win32':
        return
    from webview.platforms import winforms as wf

    original = wf.create_file_dialog

    def patched(dialog_type, directory, allow_multiple, save_filename, file_types, uid):
        i = wf.BrowserView.instances.get(uid)
        if i is None:
            return None
        if i.InvokeRequired:
            box: dict = {}

            def _run():
                box['result'] = original(
                    dialog_type, directory, allow_multiple, save_filename, file_types, uid
                )

            i.Invoke(wf.Func[wf.Type](_run))
            return box.get('result')
        return original(dialog_type, directory, allow_multiple, save_filename, file_types, uid)

    wf.create_file_dialog = patched


class Api:
    """Exposed to the page as `window.pywebview.api`. The web build has no
    equivalent — the frontend falls back to a browser download there — so
    this is the only bridge between JS and the desktop shell.

    pywebview builds this bridge by recursively walking every non-callable
    attribute of this object via `dir()` (see `inject_pywebview` in
    webview/util.py) to auto-discover exposed methods. Any attribute name
    NOT starting with `_` is descended into. Storing the real `webview.Window`
    object under a public name here previously made that walk recurse into
    the whole native window graph (WinForms controls, WebView2 COM objects,
    accessibility trees), which produced "maximum recursion depth exceeded"
    spam, cross-thread COM exceptions, and an unstable/vanishing JS bridge.
    Keeping the reference private (leading underscore) opts it out of that
    walk entirely.
    """

    def __init__(self):
        self._window = None

    def save_markdown(self, content: str, filename: str) -> dict:
        import webview

        if self._window is None:
            return {'ok': False, 'error': 'no window'}
        try:
            path = self._window.create_file_dialog(
                webview.FileDialog.SAVE,
                save_filename=filename or 'documento.md',
                file_types=('Markdown files (*.md)', 'All files (*.*)'),
            )
        except Exception:
            return {'ok': False, 'error': 'dialog failed'}
        if not path:
            return {'ok': False}  # user cancelled the dialog
        target = path if isinstance(path, str) else path[0]
        try:
            with open(target, 'w', encoding='utf-8') as f:
                f.write(content)
        except OSError:
            return {'ok': False, 'error': 'write failed'}
        return {'ok': True, 'path': target}


def main() -> None:
    import webview

    # pyi_splash only exists at runtime inside the PyInstaller onefile bundle
    # (injected by the bootloader when the spec defines a Splash()) — absent
    # when running from source.
    try:
        import pyi_splash
    except ImportError:
        pyi_splash = None

    _patch_pywebview_file_dialog_threading()

    port = _free_port()
    server_thread = threading.Thread(target=_serve, args=(port,), daemon=True)
    server_thread.start()
    if pyi_splash is not None:
        # The splash's progress bar spends 0-70% on real self-extraction
        # progress (counted Tcl-side from the bootloader's own per-file
        # updates); these are the real remaining milestones of our own
        # startup, applied directly instead of counted.
        pyi_splash.update_text('PCT:78')
    _wait_until_ready(port)
    if pyi_splash is not None:
        pyi_splash.update_text('PCT:88')

    api = Api()
    window = webview.create_window(
        'doc4ai — Document to Markdown Converter',
        f'http://127.0.0.1:{port}/',
        width=560,
        height=800,
        min_size=(420, 600),
        js_api=api,
    )
    api._window = window

    if pyi_splash is not None:
        pyi_splash.update_text('PCT:96')

        def _finish_splash():
            pyi_splash.update_text('PCT:100')
            pyi_splash.close()

        # Keep the splash up until the page has actually painted, so there's
        # no blank-window flash between the splash closing and content
        # appearing. close() is idempotent, so the timer below is just a
        # safety net in case 'loaded' never fires for some reason — without
        # it a missed event would leave the splash stuck on screen forever.
        window.events.loaded += _finish_splash
        timer = threading.Timer(15.0, pyi_splash.close)
        timer.daemon = True
        timer.start()

    webview.start()


if __name__ == '__main__':
    main()
