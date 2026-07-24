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


def main() -> None:
    import webview

    port = _free_port()
    server_thread = threading.Thread(target=_serve, args=(port,), daemon=True)
    server_thread.start()
    _wait_until_ready(port)

    webview.create_window(
        'doc4ai — Document to Markdown Converter',
        f'http://127.0.0.1:{port}/',
        width=560,
        height=800,
        min_size=(420, 600),
    )
    webview.start()


if __name__ == '__main__':
    main()
