import os
import re
import subprocess
import sys
import tempfile
import time
import traceback
import uuid
import zipfile
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from converter import binary_locator
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


_PDFTOPPM = binary_locator.resolve_pdftoppm()
_TESSERACT = binary_locator.resolve_tesseract()
_TESSDATA_DIR = binary_locator.tessdata_dir()

# Tesseract's runtime (and memory use) grows with pixel count. The app runs
# on a resource-constrained instance (512 MB RAM, ~0.1 shared vCPU), so
# photos from phones/scanners — routinely 3000px+ on a side — need a much
# smaller working size than a beefier server would require. 1200px is still
# plenty for OCR of printed text (roughly 150 DPI on a normal page).
_OCR_MAX_DIMENSION = 1200

# Overall wall-clock budget for OCR work on a multi-page PDF (rasterizing +
# every page's tesseract pass combined). The hosting platform's own reverse
# proxy drops the connection at ~60s no matter what timeout this app sets
# internally, so a document that can't finish in time needs to return
# whatever pages it did recognize rather than nothing at all.
_OCR_TIME_BUDGET = 40

# Hard cap on pages OCRed per PDF, independent of the time budget — this is
# a document converter for things like IDs and short forms, not a book
# scanner, and rendering every page of an oversized PDF at once is itself a
# memory spike on a 512 MB instance regardless of how much time is left.
_PDF_OCR_MAX_PAGES = 5


def _prepare_for_ocr(image_path: str, out_dir: str) -> str | None:
    """Preprocess an image for OCR: downscale if oversized, convert to
    grayscale, and boost contrast. This is standard OCR preprocessing that
    measurably helps tesseract on real-world photos (uneven lighting,
    low contrast) rather than clean flat scans. Returns the prepared file's
    path, or None if the image can't be read."""
    try:
        with Image.open(image_path) as img:
            if max(img.size) > _OCR_MAX_DIMENSION:
                img = img.convert('RGB')
                img.thumbnail((_OCR_MAX_DIMENSION, _OCR_MAX_DIMENSION), Image.LANCZOS)
            img = ImageOps.autocontrast(img.convert('L'))
            out_path = os.path.join(out_dir, 'ocr-prepared.png')
            img.save(out_path, 'PNG')
            return out_path
    except (OSError, UnidentifiedImageError):
        return None


def _run_tesseract(ocr_path: str, psm: int | None = None, timeout: float = 40) -> tuple[str, bool]:
    """Returns (text, timed_out)."""
    cmd = [_TESSERACT, ocr_path, 'stdout', '-l', 'por+eng']
    if _TESSDATA_DIR:
        cmd += ['--tessdata-dir', _TESSDATA_DIR]
    if psm is not None:
        cmd += ['--psm', str(psm)]
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, encoding='utf-8', timeout=max(timeout, 1),
        )
        text = r.stdout.strip()
        if not text:
            print(
                f'tesseract (psm={psm}) produced no text (returncode={r.returncode}, '
                f'stderr={r.stderr[:500]!r})',
                file=sys.stderr,
            )
        return text, False
    except subprocess.TimeoutExpired as exc:
        print(f'tesseract (psm={psm}) timed out: {exc!r}', file=sys.stderr)
        return '', True
    except (subprocess.CalledProcessError, OSError) as exc:
        print(f'tesseract (psm={psm}) failed: {exc!r}', file=sys.stderr)
        return '', False


def _tesseract_ocr(image_path: str, timeout: float = 40) -> tuple[str, bool]:
    """Run tesseract on a single image file. Returns (text, timed_out).

    Uses "sparse text" mode (PSM 11), which doesn't assume any particular
    page layout — it finds text wherever it is without expecting a single
    uniform block. That works about as well on a document-like scan as
    tesseract's default automatic segmentation, and unlike the default it
    also handles photos where text is scattered over a graphic layout (a
    flyer or poster). A single mode means a single tesseract invocation:
    on a resource-constrained instance, trying the default first and
    falling back to PSM 11 doubles worst-case latency past what the
    hosting platform's own request timeout allows.
    """
    if not os.path.exists(_TESSERACT):
        return '', False
    with tempfile.TemporaryDirectory() as tmpdir:
        ocr_path = _prepare_for_ocr(image_path, tmpdir) or image_path
        return _run_tesseract(ocr_path, psm=11, timeout=timeout)


def _pdf_ocr(full_path: str) -> tuple[str, bool]:
    """OCR fallback for PDFs where text extraction returns empty (e.g. custom-encoded
    fonts, or a scanned/photographed document with no real text layer at all).

    Rasterizes and OCRs one page at a time (rather than rendering the whole
    document up front) so peak memory stays bounded to a single page on a
    512 MB instance, and runs within an overall time budget covering all of
    it combined. A document that can't finish in time returns whatever pages
    it did manage to recognize rather than failing the conversion outright —
    better a partial result than none, especially since the hosting
    platform's own proxy timeout can't be worked around from here.

    Returns (recognized_text, ran_out_of_time) — the second value lets the
    caller tell "genuinely found nothing" apart from "didn't get to finish",
    so the error message shown for the latter can say so specifically.
    """
    if not os.path.exists(_PDFTOPPM):
        return '', False
    deadline = time.monotonic() + _OCR_TIME_BUDGET
    texts = []
    ran_out_of_time = False
    with tempfile.TemporaryDirectory() as tmpdir:
        for page_num in range(1, _PDF_OCR_MAX_PAGES + 1):
            remaining = deadline - time.monotonic()
            if remaining < 5:
                ran_out_of_time = True
                break
            prefix = os.path.join(tmpdir, f'page{page_num}')
            try:
                subprocess.run(
                    [_PDFTOPPM, '-r', '150', '-png', '-f', str(page_num), '-l', str(page_num),
                     full_path, prefix],
                    check=True, capture_output=True, timeout=min(remaining, 20),
                )
            except subprocess.TimeoutExpired:
                ran_out_of_time = True
                break
            except (subprocess.CalledProcessError, OSError):
                break  # rasterization failed — treat as no (more) pages

            page_prefix = f'page{page_num}'
            page_files = [
                f for f in os.listdir(tmpdir) if f.startswith(page_prefix) and f.endswith('.png')
            ]
            if not page_files:
                break  # page_num is past the end of the document

            page_path = os.path.join(tmpdir, page_files[0])
            remaining = deadline - time.monotonic()
            if remaining < 3:
                os.remove(page_path)
                ran_out_of_time = True
                break
            text, page_timed_out = _tesseract_ocr(page_path, timeout=remaining)
            os.remove(page_path)
            if text:
                texts.append(text)
            if page_timed_out:
                ran_out_of_time = True
                break
    return '\n\n'.join(texts), ran_out_of_time


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
        'errorOcrTimeout': _(
            'This document took too long to process (it may have several pages or '
            'large scanned images). Try uploading fewer pages at a time, or a '
            'lower-resolution scan.'
        ),
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

    ran_out_of_time = False
    try:
        if ext in _ZIP_LIKE and not _zip_safe(full_path):
            return JsonResponse({'success': False, 'error': 'corrupted'}, status=400)

        if ext in _IMAGE_EXTENSIONS:
            # markitdown has no real OCR for plain images (just EXIF
            # metadata without an LLM client), so skip it entirely rather
            # than pay for importing its heavy dependencies (pandas, numpy,
            # onnxruntime) on top of running tesseract — this app runs on a
            # memory-constrained instance where that stacks up fast.
            content, ran_out_of_time = _tesseract_ocr(full_path)
        else:
            from markitdown import MarkItDown
            result = MarkItDown().convert_local(full_path)
            content = result.text_content
            if ext == '.pdf' and not content.strip():
                content, ran_out_of_time = _pdf_ocr(full_path)
    except Exception:
        print(f'conversion failed for {ext}: {traceback.format_exc()}', file=sys.stderr)
        return JsonResponse({'success': False, 'error': 'conversion_failed'}, status=500)
    finally:
        if os.path.exists(full_path):
            os.remove(full_path)

    if not content or not content.strip():
        if ran_out_of_time:
            return JsonResponse({'success': False, 'error': 'ocr_timeout'}, status=422)
        return JsonResponse({'success': False, 'error': 'no_content'}, status=422)

    out_name = f'{_safe_stem(file.name)}.md'
    return JsonResponse({
        'success': True,
        'content': content,
        'filename': out_name,
    })
