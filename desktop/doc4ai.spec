# PyInstaller spec for the doc4ai desktop build.
# Build with:  pyinstaller desktop/doc4ai.spec --noconfirm
import os

from PyInstaller.utils.hooks import collect_data_files

block_cipher = None
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(SPEC)), '..'))

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
    excludes=['tkinter', 'test', 'unittest'],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
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
