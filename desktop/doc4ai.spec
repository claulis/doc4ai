# PyInstaller spec for the doc4ai desktop build.
# Build with:  pyinstaller desktop/doc4ai.spec --noconfirm
import os

from PyInstaller.building import splash_templates
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(SPEC)), '..'))

# PyInstaller's Splash only supports an image plus a plain status-text
# label (see splash_templates.py) — text_pos also happens to be the switch
# that makes the bootloader stream raw "loading module X" progress lines
# into that label during self-extraction, which reads as noisy internals to
# an end user. There's no public option to keep the text widget off while
# still getting a progress indicator, so this replaces build_script()
# entirely: same image/transparency/positioning scaffolding, but with the
# text widget swapped for a small light-blue bar that animates on its own
# via Tcl's `after`, so it keeps moving through both the self-extraction
# phase (before any Python code runs), and our own startup, with nothing
# external driving it.
_BAR_SCRIPT = r"""
set bar_width [expr {int($image_width * 0.62)}]
set bar_height 5
set bar_x [expr {int(($image_width - $bar_width) / 2)}]
set bar_y [expr {$image_height - 34}]

.root.canvas create rectangle \
    $bar_x $bar_y [expr {$bar_x + $bar_width}] [expr {$bar_y + $bar_height}] \
    -fill #e2e8f0 -outline {} -tag bar_track

set _bar_seg [expr {int($bar_width * 0.3)}]
.root.canvas create rectangle \
    $bar_x $bar_y [expr {$bar_x + $_bar_seg}] [expr {$bar_y + $bar_height}] \
    -fill #7dc4f2 -outline {} -tag bar_fill

set _bar_dir 1
proc _bar_animate {} {
    global bar_x bar_width _bar_seg _bar_dir
    .root.canvas move bar_fill [expr {$_bar_dir * 7}] 0
    set _coords [.root.canvas coords bar_fill]
    if {[lindex $_coords 2] >= $bar_x + $bar_width} {
        set _bar_dir -1
    } elseif {[lindex $_coords 0] <= $bar_x} {
        set _bar_dir 1
    }
    after 20 _bar_animate
}
_bar_animate
"""


def _build_script_with_progress_bar(text_options=None, always_on_top=False):
    script = [
        splash_templates.ipc_script,
        splash_templates.image_script,
        splash_templates.splash_canvas_setup,
        _BAR_SCRIPT,
        splash_templates.transparent_setup,
        splash_templates.pack_widgets,
        splash_templates.position_window_on_top if always_on_top else splash_templates.position_window,
        splash_templates.raise_window,
    ]
    return '\n'.join(script)


splash_templates.build_script = _build_script_with_progress_bar

datas = [
    (os.path.join(ROOT, 'desktop', 'bin', 'tesseract'), 'bin/tesseract'),
    (os.path.join(ROOT, 'desktop', 'bin', 'poppler'), 'bin/poppler'),
    (os.path.join(ROOT, 'staticfiles'), 'staticfiles'),
    (os.path.join(ROOT, 'locale'), 'locale'),
    (os.path.join(ROOT, 'converter', 'templates'), 'converter/templates'),
]
# markitdown's MIME-sniffing dependency (magika) ships pretrained ONNX
# models as package data — PyInstaller's static import analysis only sees
# magika's .py code, not these, so they have to be collected explicitly or
# every conversion fails at startup with "model dir not found".
datas += collect_data_files('magika')

hiddenimports = [
    'doc4ai',
    'doc4ai.settings',
    'doc4ai.urls',
    'doc4ai.wsgi',
    'doc4ai.middleware',
    'converter',
    'converter.views',
    'converter.urls',
    'converter.binary_locator',
    'whitenoise',
    'whitenoise.middleware',
    'whitenoise.runserver_nostatic',
    'whitenoise.storage',
    'django.contrib.staticfiles',
    'django_ratelimit',
    'django_ratelimit.decorators',
    'waitress',
    'markitdown',
    'PIL',
    'PIL.Image',
    'PIL.ImageOps',
]

a = Analysis(
    [os.path.join(ROOT, 'desktop', 'launcher.py')],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['test', 'unittest'],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Shown instantly by the bootloader while the onefile exe self-extracts and
# Django/waitress/webview finish booting (~15-20s) — without it the user
# just sees nothing happen for that whole stretch. Needs the Tcl/Tk runtime
# (hence 'tkinter' isn't in excludes above); launcher.py closes it via
# pyi_splash once the window is actually showing content. text_pos is left
# unset on purpose — see _build_script_with_progress_bar above, which
# replaces the text widget with an animated progress bar instead.
splash = Splash(
    os.path.join(ROOT, 'desktop', 'splash.png'),
    binaries=a.binaries,
    datas=a.datas,
    minify_script=True,
    always_on_top=True,
)

exe = EXE(
    pyz,
    a.scripts,
    splash,
    a.binaries,
    splash.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='doc4ai',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(ROOT, 'desktop', 'app_icon.ico'),
)
