# Privacy Notice — doc4ai

*Last updated: [FILL IN DATE]*

This notice explains how **doc4ai** handles data when you use the service,
in accordance with the Brazilian General Data Protection Law (Law No.
13,709/2018 – LGPD) and, for users in the European Union, the General Data
Protection Regulation (GDPR).

## Who is responsible (controller)

- **Controller:** [FILL IN: your name or entity]
- **Contact / Data Protection Officer:** [FILL IN: contact email]

## One-sentence summary

doc4ai converts the file you upload and **deletes it immediately after
conversion**. We do not store your files, do not share them, and do not
send them to any external service — all processing happens on the
application's own server.

## What data is processed and why

| Data | Purpose | Legal basis (LGPD / GDPR) | Retention |
|------|---------|---------------------------|-----------|
| **Uploaded file** (may contain personal data you included) | Perform the Markdown conversion you requested | Performance of the data subject's request / legitimate interest — LGPD art. 7; GDPR art. 6(1)(b)/(f) | **None** — the file is processed transiently and deleted right after conversion |
| **IP address** | Prevent abuse (limit of 10 requests/minute) and security | Legitimate interest — LGPD art. 7(IX)/art. 10; GDPR art. 6(1)(f) | Transient, only for rate limiting |
| **Essential cookies** (Django session and CSRF) | Request security (CSRF protection) | Legitimate interest / technical necessity | Session duration |

We do not use analytics, tracking, or advertising cookies.

## What we do NOT do

- We do **not store** uploaded files or converted content.
- We do **not share** data with third parties.
- We do **not send** files to external cloud, AI, or OCR services — text
  recognition (OCR) is performed locally by Tesseract and conversion by
  MarkItDown, with no LLM client.
- There is **no international transfer** of data resulting from conversion.
- We do **not log** the content of your files. Any operational logging is
  limited to technical information (e.g. the error code of a failed
  conversion), without the document's content.

## Desktop version (offline)

The desktop version of doc4ai runs entirely on your machine, served on
`http://127.0.0.1` (local loopback). No data leaves your computer.

## Your rights

As a data subject, you have the rights set out in LGPD art. 18 (and, where
applicable, GDPR arts. 15–22): confirmation of processing, access,
correction, deletion, portability, and information about sharing, among
others. Because doc4ai does **not retain** your files after conversion,
there is no stored copy to access or delete afterward. For questions or to
exercise your rights, use the contact above.

## Responsibility for submitted content

You are responsible for holding the necessary rights over the content you
submit for conversion and for ensuring your use complies with applicable
law. See also [`DISCLAIMER.md`](./DISCLAIMER.md).

## Changes to this notice

This notice may be updated. **Important:** if, in the future, doc4ai begins
using any external service (for example, Azure Document Intelligence or an
LLM provider), this notice must be revised to include sharing with the
processor and the rules on international data transfers (LGPD arts. 33–36;
GDPR Chapter V) — which do **not** apply to the current version.

---

## Short block for the footer / UI

```markdown
**Privacy:** doc4ai converts your file and deletes it right after
conversion. We do not store, share, or send your files to external
services — processing is done locally.
[Full Privacy Notice](./PRIVACY-NOTICE.md).
```
