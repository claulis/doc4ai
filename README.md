<p align="center">
  <img src="converter/static/converter/images/Doc4ai_Logo.png" alt="doc4ai" height="160">
</p>

<h1 align="center">doc4ai — Document to Markdown Converter for AI</h1>

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.12-3776AB?style=plastic&logo=python&logoColor=white" alt="Python"></a>
  <a href="https://www.djangoproject.com/"><img src="https://img.shields.io/badge/Django-5.x-092E20?style=plastic&logo=django&logoColor=white" alt="Django"></a>
  <a href="https://www.docker.com/"><img src="https://img.shields.io/badge/Docker-Container-2496ED?style=plastic&logo=docker&logoColor=white" alt="Docker"></a>
  <a href="https://render.com/"><img src="https://img.shields.io/badge/Render-Deploy-46E3B7?style=plastic&logo=render&logoColor=white" alt="Render"></a>
  <a href="https://gunicorn.org/"><img src="https://img.shields.io/badge/Gunicorn-WSGI-499848?style=plastic&logo=gunicorn&logoColor=white" alt="Gunicorn"></a>
  <a href="http://whitenoise.evans.io/"><img src="https://img.shields.io/badge/WhiteNoise-Static%20Files-4B8BBE?style=plastic" alt="WhiteNoise"></a>
  <a href="https://github.com/microsoft/markitdown"><img src="https://img.shields.io/badge/MarkItDown-Conversion-5C2D91?style=plastic&logo=microsoft&logoColor=white" alt="MarkItDown"></a>
  <a href="https://github.com/tesseract-ocr/tesseract"><img src="https://img.shields.io/badge/Tesseract-OCR-4285F4?style=plastic" alt="Tesseract OCR"></a>
  <a href="https://poppler.freedesktop.org/"><img src="https://img.shields.io/badge/Poppler-PDF%20Render-CC0000?style=plastic" alt="Poppler"></a>
  <a href="https://pywebview.flowrl.com/"><img src="https://img.shields.io/badge/PyWebview-Desktop%20UI-1F6FEB?style=plastic" alt="PyWebview"></a>
  <a href="https://pyinstaller.org/"><img src="https://img.shields.io/badge/PyInstaller-Windows%20Build-2E2E2E?style=plastic" alt="PyInstaller"></a>
  <a href="./LICENSE"><img src="https://img.shields.io/badge/License-Noncommercial-red?style=plastic" alt="License"></a>
</p>

<p align="center">
  <a href="https://doc4ai-own5.onrender.com"><b>🌐 Open the live Render deploy</b></a>
  ·
  <a href="https://github.com/claulis/doc4ai/releases/latest/download/doc4ai.exe"><b>⬇ Download the desktop version (Windows)</b></a>
</p>

Convert any document to **Markdown** in one click. Markdown saves tokens by stripping away the formatting noise of files like `.docx`, `.pdf`, or `.html`, keeping only the essential semantic structure — the format language models understand and process with the most accuracy and efficiency.

## Table of contents

- [Features](#features)
- [Advantages](#advantages)
- [Supported formats](#supported-formats)
- [Get started](#get-started)
- [Deploy](#deploy)
- [How processing works](#how-processing-works)
- [Software architecture](#software-architecture)
- [Design patterns used](#design-patterns-used)
- [Stack](#stack)
- [Project structure](#project-structure)
- [Security](#security)
- [Environment variables](#environment-variables)
- [Licenses and legal notices](#licenses-and-legal-notices)

## Features

- **One-click Markdown conversion** for 20+ file formats (documents, spreadsheets, presentations, images, emails, audio, HTML/text).
- **Automatic OCR** for scanned PDFs with no text layer and for images (photos of documents, posters, flyers), via Tesseract + Poppler.
- **Multilingual interface** — 8 languages (Portuguese, English, Italian, German, French, Spanish, Chinese, Hindi), with automatic browser-language detection.
- **Offline desktop version** for Windows — single executable, no installation and no network dependency, with the same interface and conversion logic as the website.
- **Transient processing** — the uploaded file is converted and deleted immediately afterward; nothing is stored or shared with third parties.

## Advantages

- **Token savings:** Markdown strips the redundant markup of `.docx`/`.pdf`/`.html`, reducing cost and increasing the accuracy of LLM prompts.
- **Privacy by default:** all conversion and OCR run locally, on the server itself (or on your own machine, in the desktop version) — no file is ever sent to an external AI or cloud service.
- **Light enough to run on a free-tier instance:** an optimized OCR pipeline (image downscaling, time budget, page-by-page processing) keeps everything within 512 MB of RAM.
- **Resilient to bad documents:** byte-signature validation, zip-bomb protection, and size limits keep a malformed file from crashing the process.
- **Same codebase, three ways to run:** web (Docker/Render), desktop (Windows, offline), and local development — with no logic forked between them.

## Supported formats

| Category | Extensions |
|-----------|-----------|
| Documents | PDF, DOCX, DOC, PPTX, PPT, XLSX, XLS |
| Web / Text | HTML, HTM, CSV, JSON, XML, TXT |
| Images | JPG, JPEG, PNG, GIF, BMP, TIFF, TIF |
| Other | EPUB, ZIP, MP3, WAV, MSG |

> PDFs with no text layer and all images are automatically processed via OCR (Tesseract + Poppler).

## Get started

### Requirements

- Python 3.12+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) and [Poppler](https://poppler.freedesktop.org/) installed and on `PATH` (for the OCR fallback)

### Running locally

```bash
# Clone the repository
git clone https://github.com/claulis/doc4ai.git
cd doc4ai

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DJANGO_SECRET_KEY="your-secret-key"
export DJANGO_DEBUG=True

# Collect static files and start
python manage.py collectstatic --noinput
python manage.py runserver
```

Open `http://localhost:8000`.

### Running with Docker

```bash
docker build -t doc4ai .
docker run -p 10000:10000 -e DJANGO_SECRET_KEY="your-secret-key" doc4ai
```

### Desktop version (Windows)

Download the ready-made executable from [Releases](https://github.com/claulis/doc4ai/releases/latest/download/doc4ai.exe), or see how to build your own in [`desktop/README.md`](desktop/README.md).

## Deploy

The public instance runs on [Render](https://render.com/), built from this repository's own Docker image (`Dockerfile` + `render.yaml`):

**🌐 https://doc4ai-own5.onrender.com**

## How processing works

1. **Upload** — the file is sent via POST (`/convert`), rate-limited to 10 requests/minute per IP.
2. **Layered validation**, in this order:
   - extension checked against an allow-list (`ALLOWED_EXTENSIONS`);
   - maximum size of 50 MB;
   - byte-signature (*magic bytes*) check, compared against the declared extension;
   - for ZIP-based formats (`.docx`, `.xlsx`, `.pptx`, `.epub`, `.zip`), an uncompressed-size check to block *zip bombs*.
3. **Routing by type:**
   - **Images** (`.jpg`, `.png`, `.gif`, `.bmp`, `.tiff`...) go straight to Tesseract — MarkItDown has no real image OCR without an LLM client, so that step is skipped entirely rather than paying for its heavy dependencies.
   - **Every other format** goes through **MarkItDown**, which already knows how to extract Markdown from PDF, DOCX, XLSX, PPTX, HTML, emails (`.msg`), EPUB, ZIP, audio, and more.
   - **PDFs with no text layer** (scanned documents) automatically fall back to **page-by-page OCR**: each page is rasterized individually by Poppler (`pdftoppm`) and passed to Tesseract, keeping peak memory bounded to a single page at a time instead of the whole document.
4. **Time and page budget** — PDF OCR respects a page cap and an overall time budget; if a document can't finish in time, whatever text was already recognized is returned instead of failing the whole conversion (the hosting platform's own reverse proxy drops the connection at ~60s anyway).
5. **Response and cleanup** — the resulting Markdown is returned as JSON, and the temporary file is **always deleted** in the `finally` block, even on error. None of the submitted content is ever persisted or logged.

## Software architecture

The project follows Django's **MVT (Model-View-Template)** pattern, but without a persistence layer — there's no database, since no state needs to survive beyond the conversion request itself.

```
HTTP request
      │
      ▼
┌─────────────────────────────┐
│ Middleware chain              │  SecurityMiddleware → LocaleMiddleware →
│ (doc4ai/middleware.py)        │  WhiteNoise → CommonMiddleware → CSRF →
│                               │  XFrameOptions → SecurityHeadersMiddleware
└─────────────────────────────┘
      │
      ▼
┌─────────────────────────────┐
│ View (converter/views.py)    │  validates the upload, picks the conversion route
└─────────────────────────────┘
      │            │
      ▼            ▼
┌───────────┐  ┌──────────────────────────┐
│ MarkItDown │  │ Tesseract + Poppler       │  via converter/binary_locator.py
│ (facade)   │  │ (direct or page-by-page OCR)│ (resolves the right binary per environment)
└───────────┘  └──────────────────────────┘
      │            │
      └─────┬──────┘
            ▼
      Template (index.html) + JSON response
```

The same code runs in **three environments** with no forked logic:

| Environment | Server | Packaging |
|----------|----------|----------------|
| Web (production) | Gunicorn behind Render's proxy | Docker image (`Dockerfile`) |
| Desktop (Windows) | Waitress (pure-Python WSGI, no `fork()`) + native window via PyWebview | Single executable via PyInstaller |
| Local development | Django's `runserver` | — |

`converter/binary_locator.py` is what makes this possible: it resolves the path to `tesseract`/`pdftoppm` differently in each environment (system `PATH` in production, `sys._MEIPASS` in the packaged executable, the default Windows install path in local dev), so `views.py` never has to know which of the three it's running in.

## Design patterns used

- **MVT (Model-View-Template):** Django's standard structure — `views.py` holds the application logic and hands rendering off to the `template`, with no `models.py` since there's no persistence.
- **Facade:** `MarkItDown().convert_local(...)` exposes a single interface for dozens of distinct document formats, hiding each format's specific parser.
- **Strategy:** `binary_locator.py` picks its binary-resolution strategy at runtime (production/Docker, packaged PyInstaller executable, or local dev) without the calling code needing to know which environment it's in.
- **Chain of Responsibility:** Django's `MIDDLEWARE` stack (including the custom `SecurityHeadersMiddleware`) processes every request through a chain of linked responsibilities.
- **Decorator:** views use composed decorators (`@ensure_csrf_cookie`, `@require_POST`, `@ratelimit`) to add cross-cutting behavior (CSRF, HTTP method, rate limiting) without changing the view function itself.
- **Adapter:** `desktop/launcher.py` adapts the same Django application — built with production HTTP in mind — to run as an offline desktop app, swapping Gunicorn for Waitress and the browser for a native PyWebview window.

## Stack

| Layer | Technology |
|--------|-----------|
| Web framework | [Django](https://www.djangoproject.com/) 5.x |
| Document conversion | [MarkItDown](https://github.com/microsoft/markitdown) |
| OCR (PDF/image fallback) | [Tesseract](https://github.com/tesseract-ocr/tesseract) + [Poppler](https://poppler.freedesktop.org/) |
| WSGI server (production) | [Gunicorn](https://gunicorn.org/) |
| WSGI server (desktop) | [Waitress](https://github.com/Pylons/waitress) |
| Native UI (desktop) | [PyWebview](https://pywebview.flowrl.com/) |
| Packaging (desktop) | [PyInstaller](https://pyinstaller.org/) |
| Static files | [WhiteNoise](http://whitenoise.evans.io/) |
| Rate limiting | [django-ratelimit](https://django-ratelimit.readthedocs.io/) |
| Image processing | [Pillow](https://python-pillow.org/) |
| Frontend | Vanilla JS + CSS (no dependencies) |
| Containerization | [Docker](https://www.docker.com/) |
| Deploy | [Render](https://render.com/) (Docker) |

## Project structure

```
doc4ai/
├── converter/              # Django app: views, routes, templates, static assets
│   ├── views.py             # Upload validation + conversion/OCR routing
│   ├── binary_locator.py    # Resolves tesseract/pdftoppm per environment
│   ├── templates/converter/
│   └── static/converter/    # Frontend CSS, JS and images
├── doc4ai/                  # Django project configuration
│   ├── settings.py
│   ├── middleware.py        # Custom security headers
│   └── urls.py / wsgi.py
├── desktop/                 # Desktop build (Windows)
│   ├── launcher.py          # Entry point: waitress + pywebview
│   ├── doc4ai.spec          # PyInstaller spec
│   └── bin/                 # Bundled portable Tesseract and Poppler
├── locale/                  # Translations (8 languages)
├── Dockerfile               # Production image
├── render.yaml              # Render deploy configuration
├── LICENSE
├── THIRD-PARTY-LICENSES.md
├── PRIVACY-NOTICE.md
└── DISCLAIMER.md
```

## Security

- Byte-signature (magic bytes) validation for every file type
- Zip-bomb protection (512 MB uncompressed limit)
- 50 MB upload size limit per file
- Rate limiting of 10 requests/minute per IP
- CSRF enabled on every POST route
- Security headers via custom middleware (CSP, Referrer-Policy, Permissions-Policy)
- Container runs as a non-root user

## Environment variables

| Variable | Default | Description |
|----------|--------|-----------|
| `DJANGO_SECRET_KEY` | *(required in production)* | Django's secret key |
| `DJANGO_DEBUG` | `False` | Enables debug mode |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Allowed hosts (comma-separated) |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `http://localhost,http://127.0.0.1` | Trusted origins for CSRF |
| `DJANGO_SECURE_SSL_REDIRECT` | `False` | Redirects HTTP → HTTPS |
| `DJANGO_HSTS_SECONDS` | `0` | HSTS duration in seconds |

## Licenses and legal notices

This project is **source-available and noncommercial**. Please read before using:

| File | Content |
|---------|----------|
| [`LICENSE`](./LICENSE) | doc4ai Noncommercial License 1.0 — use, study, and redistribution permitted for noncommercial purposes |
| [`THIRD-PARTY-LICENSES.md`](./THIRD-PARTY-LICENSES.md) | Licenses of third-party components (MarkItDown/MIT, Poppler/GPLv2, Tesseract/Apache 2.0, and others) |
| [`PRIVACY-NOTICE.md`](./PRIVACY-NOTICE.md) | How doc4ai handles submitted data (LGPD/GDPR) — summary: nothing is stored |
| [`DISCLAIMER.md`](./DISCLAIMER.md) | Disclaimer of warranty on conversion/OCR quality and responsibility for submitted content |
