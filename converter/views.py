import os
import re
import shutil
import subprocess
import tempfile
import uuid
import zipfile
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.translation import gettext as _
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

# (code, native name) — native names so users recognize their own
# language regardless of which locale is currently active. The flag icon
# for each code is rendered as an inline SVG in the template (emoji flags
# don't render on Windows Chrome/Edge, which lacks color flag glyphs).
LANGUAGE_SWITCHER_OPTIONS = [
    ('en', 'English'),
    ('pt-br', 'Português'),
    ('it', 'Italiano'),
    ('de', 'Deutsch'),
    ('fr', 'Français'),
    ('es', 'Español'),
    ('zh-hans', '中文'),
    ('hi', 'हिन्दी'),
]

ALLOWED_EXTENSIONS = {
    '.pdf', '.docx', '.doc', '.pptx', '.ppt', '.xlsx', '.xls',
    '.html', '.htm', '.csv', '.json', '.xml', '.txt', '.md',
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif',
    '.epub', '.zip', '.mp3', '.wav', '.msg',
}

# Extensions that are ZIP-based and must pass the zip-bomb check
_ZIP_LIKE = {'.zip', '.docx', '.xlsx', '.pptx', '.epub'}

# markitdown has no built-in OCR for plain images (without an LLM client it
# only reads EXIF metadata), so these always go through tesseract directly.
_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif'}

MAX_UPLOAD_SIZE = 50 * 1024 * 1024
_ZIPBOMB_MAX_UNCOMPRESSED = 512 * 1024 * 1024  # 512 MB

# Magic-byte signatures keyed by extension.
# Text-based formats (.html, .csv, .json, .xml, .txt, .md) have no entry —
# they pass validation unconditionally.
_MAGIC: dict[str, bytes | tuple[bytes, ...]] = {
    '.pdf':  b'%PDF',
    '.png':  b'\x89PNG\r\n\x1a\n',
    '.jpg':  b'\xff\xd8\xff',
    '.jpeg': b'\xff\xd8\xff',
    '.gif':  (b'GIF87a', b'GIF89a'),
    '.bmp':  b'BM',
    '.tiff': (b'II*\x00', b'MM\x00*'),
    '.tif':  (b'II*\x00', b'MM\x00*'),
    '.mp3':  (b'ID3', b'\xff\xfb', b'\xff\xf3', b'\xff\xf2'),
    '.wav':  b'RIFF',
    # Office Open XML and plain ZIP share the PK header
    '.zip':  b'PK\x03\x04',
    '.docx': b'PK\x03\x04',
    '.xlsx': b'PK\x03\x04',
    '.pptx': b'PK\x03\x04',
    '.epub': b'PK\x03\x04',
    # Legacy OLE2 compound document
    '.doc':  b'\xd0\xcf\x11\xe0',
    '.xls':  b'\xd0\xcf\x11\xe0',
    '.ppt':  b'\xd0\xcf\x11\xe0',
    '.msg':  b'\xd0\xcf\x11\xe0',
}


def _magic_ok(header: bytes, ext: str) -> bool:
    sig = _MAGIC.get(ext)
    if sig is None:
        return True
    if isinstance(sig, tuple):
        return any(header.startswith(s) for s in sig)
    return header.startswith(sig)


def _zip_safe(path: str) -> bool:
    try:
        with zipfile.ZipFile(path) as zf:
            return sum(i.file_size for i in zf.infolist()) <= _ZIPBOMB_MAX_UNCOMPRESSED
    except zipfile.BadZipFile:
        return False


_PDFTOPPM = shutil.which('pdftoppm') or r'C:\Program Files\poppler\Library\bin\pdftoppm.exe'
_TESSERACT = shutil.which('tesseract') or r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Tesseract's runtime (and memory use) grows with pixel count. The app runs
# on a resource-constrained instance (512 MB RAM, ~0.1 shared vCPU), so
# photos from phones/scanners — routinely 3000px+ on a side — need a much
# smaller working size than a beefier server would require. 1200px is still
# plenty for OCR of printed text (roughly 150 DPI on a normal page).
_OCR_MAX_DIMENSION = 1200


def _downscale_for_ocr(image_path: str, out_dir: str) -> str | None:
    """Shrink an oversized image before OCR. Returns the resized file's path,
    or None if the image is already small enough (or unreadable as an image)."""
    try:
        with Image.open(image_path) as img:
            if max(img.size) <= _OCR_MAX_DIMENSION:
                return None
            img = img.convert('RGB')
            img.thumbnail((_OCR_MAX_DIMENSION, _OCR_MAX_DIMENSION), Image.LANCZOS)
            out_path = os.path.join(out_dir, 'ocr-resized.png')
            img.save(out_path, 'PNG')
            return out_path
    except (OSError, UnidentifiedImageError):
        return None


def _tesseract_ocr(image_path: str) -> str:
    """Run tesseract on a single image file, returning extracted text (or '' on failure)."""
    if not os.path.exists(_TESSERACT):
        return ''
    with tempfile.TemporaryDirectory() as tmpdir:
        ocr_path = _downscale_for_ocr(image_path, tmpdir) or image_path
        try:
            r = subprocess.run(
                [_TESSERACT, ocr_path, 'stdout', '-l', 'por+eng'],
                capture_output=True, text=True, encoding='utf-8', timeout=45,
            )
            return r.stdout.strip()
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
            return ''


def _pdf_ocr(full_path: str) -> str:
    """OCR fallback for PDFs where text extraction returns empty (e.g. custom-encoded fonts)."""
    if not os.path.exists(_PDFTOPPM):
        return ''
    with tempfile.TemporaryDirectory() as tmpdir:
        prefix = os.path.join(tmpdir, 'page')
        try:
            subprocess.run(
                [_PDFTOPPM, '-r', '150', '-png', full_path, prefix],
                check=True, capture_output=True, timeout=120,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
            return ''
        texts = []
        for fname in sorted(os.listdir(tmpdir)):
            if not fname.endswith('.png'):
                continue
            text = _tesseract_ocr(os.path.join(tmpdir, fname))
            if text:
                texts.append(text)
        return '\n\n'.join(texts)


def _safe_stem(name: str) -> str:
    stem = Path(name).stem
    stem = re.sub(r'[^\w\-. ]', '_', stem)
    return stem[:100] or 'documento'


@ensure_csrf_cookie
def index(request):
    js_strings = {
        'tooLarge': _('File too large. The maximum allowed size is 50 MB.'),
        'lessThan5s': _('less than 5 s'),
        'secondsFormat': _('~%s s'),
        'minutesFormat': _('~%s min'),
        'uploading': _('Uploading...'),
        'uploadingPct': _('Uploading... %s%'),
        'converting': _('Converting · %s'),
        'finalizing': _('Finalizing...'),
        'errorGeneric': _('Could not convert the file. Try again with another document.'),
        'errorNoFile': _('No file was selected.'),
        'errorTooLarge': _('File too large. The maximum allowed size is 50 MB.'),
        'errorUnsupportedType': _("This file type isn't supported."),
        'errorCorrupted': _('The file appears to be corrupted or invalid.'),
        'errorConversionFailed': _('Something went wrong while converting this file.'),
        'errorNoContent': _('No readable text could be found in this file.'),
    }
    return render(request, 'converter/index.html', {
        'language_options': LANGUAGE_SWITCHER_OPTIONS,
        'js_strings': js_strings,
    })


@ratelimit(key='ip', rate='10/m', method='POST', block=True)
@require_POST
def convert(request):
    file = request.FILES.get('document')
    if not file:
        return JsonResponse({'success': False, 'error': 'no_file'}, status=400)

    if file.size > MAX_UPLOAD_SIZE:
        return JsonResponse({'success': False, 'error': 'too_large'}, status=400)

    ext = os.path.splitext(file.name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return JsonResponse({'success': False, 'error': 'unsupported_type'}, status=400)

    file_bytes = file.read()

    if not _magic_ok(file_bytes[:16], ext):
        return JsonResponse({'success': False, 'error': 'corrupted'}, status=400)

    file_id = str(uuid.uuid4())
    temp_name = f'{file_id}{ext}'
    temp_path = default_storage.save(f'uploads/{temp_name}', ContentFile(file_bytes))
    full_path = str(Path(settings.MEDIA_ROOT) / temp_path)

    try:
        if ext in _ZIP_LIKE and not _zip_safe(full_path):
            return JsonResponse({'success': False, 'error': 'corrupted'}, status=400)

        from markitdown import MarkItDown
        result = MarkItDown().convert_local(full_path)
        content = result.text_content
        if ext == '.pdf' and not content.strip():
            content = _pdf_ocr(full_path)
        elif ext in _IMAGE_EXTENSIONS:
            ocr_text = _tesseract_ocr(full_path)
            if ocr_text:
                content = ocr_text
    except Exception:
        return JsonResponse({'success': False, 'error': 'conversion_failed'}, status=500)
    finally:
        if os.path.exists(full_path):
            os.remove(full_path)

    if not content or not content.strip():
        return JsonResponse({'success': False, 'error': 'no_content'}, status=422)

    out_name = f'{_safe_stem(file.name)}.md'
    return JsonResponse({
        'success': True,
        'content': content,
        'filename': out_name,
    })
