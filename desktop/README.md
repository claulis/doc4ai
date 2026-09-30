# doc4ai desktop (Windows)

Roda o mesmo app Django do site, servido localmente (waitress) e exibido
numa janela nativa (pywebview) — mesma interface, mesma lógica de
conversão, tudo offline. Distribuído como instalador por usuário
(`doc4ai-setup.exe`, sem precisar de administrador) e como `.zip` portátil.

## Publicar uma versão (recomendado: via CI)

1. Atualize `desktop/VERSION` (ex.: `1.2.0`) e faça commit.
2. `git tag desktop-v1.2.0 && git push origin desktop-v1.2.0`
3. O workflow [`.github/workflows/desktop-release.yml`](../.github/workflows/desktop-release.yml)
   compila tudo no GitHub Actions e cria a release com `doc4ai-setup.exe`,
   `doc4ai-portable.zip`, `SHA256SUMS.txt` e atestado de origem do build.
4. Depois de publicar, siga o [checklist anti-falso-positivo](#checklist-por-release).

## Rebuild local

```
# 1. Dependências. PYINSTALLER_COMPILE_BOOTLOADER + --no-binary compilam o
#    bootloader do PyInstaller do fonte (precisa do Visual Studio Build Tools)
#    — veja "Por que os antivírus reclamavam" abaixo.
set PYINSTALLER_COMPILE_BOOTLOADER=1
pip install -r desktop/requirements-desktop.txt --no-binary pyinstaller

# 2. Coletar estáticos e traduções
python manage.py collectstatic --noinput
python manage.py compilemessages   # precisa de gettext; ou use polib localmente

# 3. Build (pasta desktop/dist/doc4ai/ com doc4ai.exe + _internal/)
pyinstaller desktop/doc4ai.spec --noconfirm --distpath desktop/dist --workpath desktop/build

# 4. Instalador (Inno Setup 6) → desktop/dist/doc4ai-setup.exe
ISCC desktop\installer.iss
```

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
  empacotado (via `sys._MEIPASS`, que no build onedir é a pasta `_internal/`)
  ou dev local. O mesmo `converter/views.py` funciona sem alteração nos três casos.
- `desktop/launcher.py` — ponto de entrada: gera uma `DJANGO_SECRET_KEY`
  aleatória, sobe o Django via waitress numa porta livre local, abre a
  janela pywebview.
- `doc4ai/settings.py` — `DESKTOP_MODE` (via `DOC4AI_DESKTOP=1`, setado
  pelo launcher) desliga `SESSION_COOKIE_SECURE`/`CSRF_COOKIE_SECURE`
  apenas no build desktop, já que ali não há HTTPS (é loopback local), e
  move os uploads temporários para `%LOCALAPPDATA%\doc4ai\media` — nunca
  afeta o deploy web.
- `desktop/VERSION` — versão única, usada pelo spec (metadados do exe),
  pelo `installer.iss` e conferida contra a tag pelo workflow.

## Por que os antivírus/navegadores reclamavam (e o que foi feito)

| Causa | Medida |
|---|---|
| Exe `--onefile` se autoextrai no `%TEMP%` e carrega DLLs de lá a cada execução (padrão de "dropper") | Build **onedir** + instalador Inno Setup em `%LOCALAPPDATA%\Programs\doc4ai` |
| Bootloader pré-compilado do PyInstaller é o mesmo usado por muito malware | Bootloader **compilado do fonte** no CI (binário próprio) |
| Exe sem editor/produto/versão | **Metadados de versão** (Propriedades → Detalhes) no exe e no instalador |
| Binário de origem desconhecida | Build no **GitHub Actions**, SHA-256 publicado e **atestado de origem** (`gh attestation verify doc4ai-setup.exe -R claulis/doc4ai`) |
| Sem assinatura digital | **Não resolvido** (ver abaixo) |

Sem assinatura de código, o SmartScreen ("O Windows protegeu o computador")
e o aviso de "arquivo pouco baixado" do Chrome/Edge **continuam aparecendo**
para versões novas — são avisos de *reputação*, que diminuem conforme o
mesmo arquivo acumula downloads. A página de download explica como passar
por ele ("Mais informações → Executar assim mesmo"). A única forma de
eliminá-lo é assinar o instalador (certificado de assinatura de código, ou
distribuir pela Microsoft Store).

## Checklist por release

1. Enviar `doc4ai-setup.exe` e `doc4ai-portable.zip` ao portal de
   falso-positivo da Microsoft: <https://www.microsoft.com/wdsi/filesubmission>
   → "Software developer" → "Incorrectly detected as malware/malicious".
   Costuma ser liberado em 1–3 dias e alimenta a reputação no SmartScreen.
2. Enviar ao <https://www.virustotal.com> e, se algum fornecedor acusar,
   reportar falso-positivo no site dele (a maioria tem formulário próprio).
3. Evitar republicar arquivos com o mesmo nome e hash diferente sem
   necessidade: cada hash novo recomeça a reputação do zero.

## Riscos conhecidos (aceitos para este build)

- Sem assinatura de código — aviso de reputação residual (acima).
- Poppler é GPL — os binários são apenas invocados via subprocess
  (não linkados ao código), mas vale revisão jurídica se for distribuição
  comercial ampla.
- Sem checador de atualização — usuário baixa manualmente uma versão nova
  do site quando houver (o instalador atualiza a instalação existente).

## Testado (nesta máquina, sem Python/Tesseract/Poppler no PATH do processo)

- Abertura da janela e carregamento da UI (idêntica ao site).
- Conversão de imagem via OCR (tesseract embutido).
- Conversão de PDF sem camada de texto via OCR (poppler + tesseract embutidos).
- Conversão de XLSX (markitdown).
