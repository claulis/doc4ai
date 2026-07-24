"""Resolves paths to the external OCR binaries (tesseract, pdftoppm) across
every environment this app runs in:

- Production (Render/Docker): installed system-wide via apt, found on PATH.
- Packaged desktop executable (PyInstaller --onefile): bundled inside the
  exe and self-extracted to a temp folder at runtime (``sys._MEIPASS``).
- Local development: whatever's on PATH, or a common Windows install path.

Each caller just asks for a binary by name; this module picks the right
strategy for the environment currently running so ``converter/views.py``
never has to know or care which one it's in.
"""
import shutil
import sys
from pathlib import Path


def _bundled_root() -> Path | None:
    """Returns the folder PyInstaller extracted this executable into, or
    None if we're not running from a bundle at all (plain `python manage.py`,
    Docker, etc.)."""
    meipass = getattr(sys, '_MEIPASS', None)
    return Path(meipass) if meipass else None


def _resolve(name: str, bundled_subdir: str, windows_fallback: str) -> str:
    bundled_root = _bundled_root()
    if bundled_root is not None:
        exe_name = f'{name}.exe' if sys.platform == 'win32' else name
        bundled_path = bundled_root / 'bin' / bundled_subdir / exe_name
        if bundled_path.exists():
            return str(bundled_path)

    on_path = shutil.which(name)
    if on_path:
        return on_path

    if sys.platform == 'win32' and Path(windows_fallback).exists():
        return windows_fallback

    # Nothing found — return the bare name so the eventual subprocess call
    # fails with a clear "file not found" rather than silently.
    return name


def resolve_tesseract() -> str:
    return _resolve('tesseract', 'tesseract', r'C:\Program Files\Tesseract-OCR\tesseract.exe')


def resolve_pdftoppm() -> str:
    return _resolve('pdftoppm', 'poppler', r'C:\Program Files\poppler\Library\bin\pdftoppm.exe')


def tessdata_dir() -> str | None:
    """Only needed for the bundled desktop build — production/dev tesseract
    installs already know where their own tessdata lives."""
    bundled_root = _bundled_root()
    if bundled_root is None:
        return None
    path = bundled_root / 'bin' / 'tesseract' / 'tessdata'
    return str(path) if path.exists() else None
