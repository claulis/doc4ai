# PyInstaller spec for the doc4ai desktop build.
# Build with:  pyinstaller desktop/doc4ai.spec --noconfirm
import os

from PyInstaller.building import splash_templates
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo, StringFileInfo, StringStruct, StringTable,
    VarFileInfo, VarStruct, VSVersionInfo,
)

block_cipher = None
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(SPEC)), '..'))

# Single source of truth for the release version — also read by
# installer.iss and checked against the git tag by the release workflow.
with open(os.path.join(ROOT, 'desktop', 'VERSION'), encoding='utf-8') as f:
    APP_VERSION = f.read().strip()
_ver_tuple = tuple(int(p) for p in (APP_VERSION.split('.') + ['0'] * 4)[:4])

# Windows version resource (Properties > Details). An exe with no
# publisher/product/description metadata is one of the things antivirus
# heuristics and SmartScreen treat as suspicious.
VERSION_INFO = VSVersionInfo(
    ffi=FixedFileInfo(filevers=_ver_tuple, prodvers=_ver_tuple),
    kids=[
        StringFileInfo([StringTable('040904B0', [
            StringStruct('CompanyName', 'Claudio Ulisse'),
            StringStruct('FileDescription', 'doc4ai - Document to Markdown Converter'),
            StringStruct('FileVersion', APP_VERSION),
            StringStruct('InternalName', 'doc4ai'),
            StringStruct('LegalCopyright', 'Copyright (c) 2026 Claudio Ulisse'),
            StringStruct('OriginalFilename', 'doc4ai.exe'),
            StringStruct('ProductName', 'doc4ai'),
            StringStruct('ProductVersion', APP_VERSION),
        ])]),
        VarFileInfo([VarStruct('Translation', [0x0409, 1200])]),
    ],
)

# PyInstaller's Splash only supports an image plus a plain status-text
# label (see splash_templates.py) — text_pos also happens to be the switch
# that makes the bootloader stream raw "loading module X" progress lines
# into that label during self-extraction, which reads as noisy internals to
# an end user. There's no public option to keep the text widget off while
# still getting a progress indicator, so this replaces build_script()
# entirely: same image/transparency/positioning scaffolding, but with the
# text widget swapped for an actual progress bar.
#
# The bar tracks real startup progress over the same IPC channel the
# bootloader already uses (ipc_script's status_text variable is set
# regardless of whether a text widget is bound to it): launcher.py sends
# explicit "PCT:<n>" messages at each real milestone (server started,
# server ready, window created, page loaded), applied directly. Anything
# else written there is ignored.
_BAR_SCRIPT = r"""
set bar_width [expr {int($image_width * 0.62)}]
set bar_height 5
set bar_x [expr {int(($image_width - $bar_width) / 2)}]
set bar_y [expr {$image_height - 34}]

.root.canvas create rectangle \
    $bar_x $bar_y [expr {$bar_x + $bar_width}] [expr {$bar_y + $bar_height}] \
    -fill #e2e8f0 -outline {} -tag bar_track

.root.canvas create rectangle \
    $bar_x $bar_y $bar_x [expr {$bar_y + $bar_height}] \
    -fill #7dc4f2 -outline {} -tag bar_fill

proc _set_bar_pct {pct} {
    global bar_x bar_width bar_y bar_height
    if {$pct < 0} { set pct 0 }
    if {$pct > 100} { set pct 100 }
    set w [expr {int($bar_width * $pct / 100.0)}]
    .root.canvas coords bar_fill $bar_x $bar_y [expr {$bar_x + $w}] [expr {$bar_y + $bar_height}]
}

proc _on_status_text {name1 name2 op} {
    upvar #0 $name1 value
    if {[string match "PCT:*" $value]} {
        _set_bar_pct [string range $value 4 end]
    }
}

set status_text ""
trace add variable status_text write _on_status_text
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

# Shown instantly by the bootloader while Django/waitress/webview finish
# booting — without it the user just sees nothing happen for a few seconds. Needs the Tcl/Tk runtime
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

# onedir (exe + _internal/ folder), packaged by installer.iss — NOT onefile.
# A onefile exe unpacks itself into %TEMP% and loads DLLs from there on
# every launch, which is exactly the dropper pattern antivirus heuristics
# look for; it was the main source of "may be malicious" flags.
exe = EXE(
    pyz,
    a.scripts,
    splash,
    [],
    exclude_binaries=True,
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
    version=VERSION_INFO,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    splash.binaries,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='doc4ai',
)
