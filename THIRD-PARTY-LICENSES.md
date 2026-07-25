# Third-Party Licenses and Notices

doc4ai is distributed and/or bundled together with third-party components
that are licensed **separately** by their respective authors, under their
own terms. Those terms are reproduced or referenced below.

**Important:** The noncommercial restriction in the doc4ai license (see
`LICENSE`) applies **only** to doc4ai's own original code. It does **not**
restrict any rights you have in the components listed here under their own
licenses. In particular, components under the GNU GPL remain fully governed
by the GPL, and your rights in them — including commercial use of those
components — are unaffected by doc4ai's license.

The OCR binaries (Poppler, Tesseract) are invoked by doc4ai as separate
programs via `subprocess` (process-level aggregation); they are not linked
into doc4ai's code. In the desktop build they are packaged together with
the application for convenience, but they remain independent works under
their own licenses and can be identified and extracted as such.

---

## 1. Poppler — GNU General Public License, version 2 (or later)

**Component:** Poppler (`pdftoppm` and its accompanying libraries),
used for rasterizing PDF pages prior to OCR.

**Copyright:** © the Poppler developers and contributors.

**License:** GNU General Public License, version 2 (GPLv2). Poppler is
distributed under the GPL; see the upstream project for the exact terms
and version applicable to the binaries you ship.

**Upstream source:** https://poppler.freedesktop.org/ and
https://gitlab.freedesktop.org/poppler/poppler

**Binary provenance (Windows build):** the bundled Windows binaries were
obtained from the poppler-windows release project.
> **[FILL IN]** Exact release version and download URL used, e.g.
> `poppler-windows vXX.YY.Z` — https://github.com/oschwartz10612/poppler-windows/releases/tag/vXX.YY.Z-0

### Written offer for source code (GPLv2 §3(b))

The Poppler binaries distributed with doc4ai are covered by the GNU GPL
v2. In accordance with Section 3 of the GPL, the complete corresponding
source code for the exact version of Poppler distributed here is available
from the upstream project at the URL above. In addition, the copyright
holder of doc4ai hereby makes a written offer, valid for at least three
(3) years, to provide, upon request and for no more than the cost of
physically performing source distribution, a complete machine-readable
copy of the corresponding source code of the Poppler version distributed
with doc4ai. Requests may be sent to the maintainer via the project
repository at https://github.com/claulis/doc4ai.

A full copy of the GNU General Public License version 2 is included in this
distribution as `licenses/GPL-2.0.txt`.
> **[ACTION]** Add `licenses/GPL-2.0.txt` (verbatim GPLv2 text from
> https://www.gnu.org/licenses/old-licenses/gpl-2.0.txt).

---

## 2. Tesseract OCR — Apache License 2.0

**Component:** Tesseract OCR engine (`tesseract` and accompanying DLLs)
and the trained language data (`tessdata`: `eng`, `por`, `osd`).

**Copyright:** © the Tesseract OCR contributors; trained data © Google and
contributors.

**License:** Apache License, Version 2.0.

**Upstream source:**
- Engine: https://github.com/tesseract-ocr/tesseract
- Trained data: https://github.com/tesseract-ocr/tessdata

Under Apache 2.0 §4, this redistribution retains the copyright notice and
license. A full copy of the Apache License 2.0 is included as
`licenses/Apache-2.0.txt`, and any upstream `NOTICE` content is reproduced
in `licenses/Tesseract-NOTICE.txt`.
> **[ACTION]** Add `licenses/Apache-2.0.txt`
> (https://www.apache.org/licenses/LICENSE-2.0.txt) and copy the upstream
> Tesseract `NOTICE` file if present.

---

## 3. MarkItDown — MIT License

**Component:** MarkItDown, used as the core document-to-Markdown
conversion library.

**Copyright:** © Microsoft Corporation and contributors.

**License:** MIT License.

**Upstream source:** https://github.com/microsoft/markitdown

The MIT License permits commercial and noncommercial use, modification,
and redistribution, provided the copyright notice and permission notice are
retained.
> **[ACTION]** Add the MarkItDown MIT license text as
> `licenses/MarkItDown-MIT.txt`.

---

## 4. Other bundled dependencies

The web and desktop builds also include, among others: Django (BSD
3-Clause), Pillow (HPND/MIT-CMU-style), gunicorn (MIT), whitenoise (MIT),
django-ratelimit (BSD), waitress (ZPL), pywebview (BSD), and the
dependencies pulled in transitively by `markitdown[...]` (e.g. magika,
onnxruntime, numpy, pdfminer.six, python-docx, python-pptx, openpyxl),
each under its own permissive license.

Because the desktop build redistributes these as compiled artifacts, the
distribution should carry their license texts as well.
> **[RECOMMENDED]** Generate a complete manifest for the exact build with:
>
> ```
> pip install pip-licenses
> pip-licenses --format=markdown --with-authors --with-urls \
>   --with-license-file --output-file licenses/DEPENDENCY-LICENSES.md
> ```
>
> Commit the result under `licenses/` so every distributed dependency's
> license travels with the binary.

---

## Summary of actions to complete compliance

- [ ] Fill in the exact Poppler (poppler-windows) version and URL above.
- [ ] Add `licenses/GPL-2.0.txt` (verbatim GPLv2).
- [ ] Add `licenses/Apache-2.0.txt` and `licenses/Tesseract-NOTICE.txt`.
- [ ] Add `licenses/MarkItDown-MIT.txt`.
- [ ] Generate and commit `licenses/DEPENDENCY-LICENSES.md` for the build.
- [ ] (Desktop) Prefer shipping Poppler/Tesseract as files next to the
      `.exe`, or clearly document them as separable GPL/Apache components.
