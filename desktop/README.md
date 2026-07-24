# doc4ai desktop (Windows)

Executável único, sem instalação: roda o mesmo app Django do site,
servido localmente (waitress) e exibido numa janela nativa (pywebview) —
mesma interface, mesma lógica de conversão, tudo offline.

## Rebuild

```
# 1. Ambiente com as dependências (inclui waitress, pywebview, pyinstaller)
pip install -r desktop/requirements-desktop.txt

# 2. Coletar estáticos e traduções
python manage.py collectstatic --noinput
python manage.py compilemessages   # precisa de gettext; ou use polib localmente

# 3. Build
pyinstaller desktop/doc4ai.spec --noconfirm --distpath desktop/dist --workpath desktop/build
```

Gera `desktop/dist/doc4ai.exe` — um único arquivo (~125 MB), sem instalador,
sem precisar de Python/Tesseract/Poppler no computador do usuário.

## O que está empacotado

- `desktop/bin/tesseract/` — Tesseract 5.2 portátil (tesseract.exe + DLLs +
  tessdata para eng/por/osd), montado a partir dos pacotes win-64 do
  conda-forge (sem instalador, sem precisar de admin).
- `desktop/bin/poppler/` — pdftoppm.exe portátil (poppler-windows release).
- `staticfiles/`, `locale/`, `converter/templates/` — coletados do próprio
  projeto Django antes do build.

## Redução de tamanho

O site usa `markitdown[all]`, que traz SDKs do Azure, transcrição de áudio
(speechrecognition/pydub, ~30 MB) e YouTube — nada disso serve para um app
desktop offline. O build desktop usa `markitdown[pdf,docx,pptx,xls,xlsx,outlook]`
(veja `requirements-desktop.txt`), cortando essas dependências. `magika`
(detecção de tipo de arquivo) continua sendo uma dependência obrigatória do
markitdown e traz onnxruntime+numpy — é o maior peso restante, sem como
evitar sem trocar de biblioteca de conversão.

## Arquitetura

- `converter/binary_locator.py` — resolve o caminho do tesseract/pdftoppm
  conforme o ambiente: produção (Docker/Render, via PATH), executável
  empacotado (via `sys._MEIPASS`) ou dev local. O mesmo `converter/views.py`
  funciona sem alteração nos três casos.
- `desktop/launcher.py` — ponto de entrada: gera uma `DJANGO_SECRET_KEY`
  aleatória, sobe o Django via waitress numa porta livre local, abre a
  janela pywebview.
- `doc4ai/settings.py` — `DESKTOP_MODE` (via `DOC4AI_DESKTOP=1`, setado
  pelo launcher) desliga `SESSION_COOKIE_SECURE`/`CSRF_COOKIE_SECURE`
  apenas no build desktop, já que ali não há HTTPS (é loopback local) —
  nunca afeta o deploy web.

## Riscos conhecidos (aceitos para este build)

- Antivírus podem sinalizar falso-positivo em executáveis PyInstaller
  `--onefile` — não testado ainda contra VirusTotal.
- Poppler é GPL — os binários são apenas invocados via subprocess
  (não linkados ao código), mas vale revisão jurídica se for distribuição
  comercial ampla.
- Sem assinatura de código — Windows SmartScreen pode alertar no primeiro
  uso ("Editor desconhecido").
- Sem checador de atualização — usuário baixa manualmente uma versão nova
  do site quando houver.

## Testado (nesta máquina, sem Python/Tesseract/Poppler no PATH do processo)

- Abertura da janela e carregamento da UI (idêntica ao site).
- Conversão de imagem via OCR (tesseract embutido).
- Conversão de PDF sem camada de texto via OCR (poppler + tesseract embutidos).
- Conversão de XLSX (markitdown).
