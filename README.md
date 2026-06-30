<p align="center">
  <img src="converter/static/converter/images/Doc4ai_Logo.png" alt="doc4ai" height="160">
</p>

# doc4ai — Conversor de Documentos para IA

Converta qualquer documento para **Markdown** com um clique. O formato Markdown economiza tokens ao eliminar o ruído de formatação de arquivos como `.docx`, `.pdf` ou `.html`, mantendo apenas a estrutura semântica essencial — o formato que modelos de linguagem entendem e processam com mais precisão e eficiência.

## Como funciona

1. Arraste ou selecione um arquivo
2. Clique em **Converter para Markdown**
3. Baixe o `.md` gerado e use direto no seu prompt

## Formatos suportados

| Categoria | Extensões |
|-----------|-----------|
| Documentos | PDF, DOCX, DOC, PPTX, PPT, XLSX, XLS |
| Web / Texto | HTML, HTM, CSV, JSON, XML, TXT, MD |
| Imagens | JPG, JPEG, PNG, GIF, BMP, TIFF, TIF |
| Outros | EPUB, ZIP, MP3, WAV, MSG |

> PDFs sem camada de texto são processados automaticamente via OCR (Tesseract + Poppler).

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Framework web | [Django](https://www.djangoproject.com/) 5.x |
| Conversão de documentos | [MarkItDown](https://github.com/microsoft/markitdown) |
| OCR (fallback PDF) | [Tesseract](https://github.com/tesseract-ocr/tesseract) + [Poppler](https://poppler.freedesktop.org/) |
| Servidor WSGI | [Gunicorn](https://gunicorn.org/) |
| Arquivos estáticos | [WhiteNoise](http://whitenoise.evans.io/) |
| Rate limiting | [django-ratelimit](https://django-ratelimit.readthedocs.io/) |
| Banco de dados | SQLite |
| Frontend | Vanilla JS + CSS (sem dependências) |
| Deploy | Heroku / qualquer plataforma com suporte a `Procfile` |

## Segurança

- Validação de assinatura de bytes (magic bytes) para cada tipo de arquivo
- Proteção contra zip bombs (limite de 512 MB descomprimido)
- Limite de upload de 50 MB por arquivo
- Rate limiting de 10 requisições/minuto por IP
- CSRF habilitado em todas as rotas POST
- Headers de segurança via middleware customizado

## Rodando localmente

```bash
# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
export DJANGO_SECRET_KEY="sua-chave-secreta"
export DJANGO_DEBUG=True

# Coletar arquivos estáticos e iniciar
python manage.py collectstatic --noinput
python manage.py runserver
```

Acesse `http://localhost:8000`.

### Variáveis de ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `DJANGO_SECRET_KEY` | *(obrigatório em produção)* | Chave secreta do Django |
| `DJANGO_DEBUG` | `False` | Ativa modo debug |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Hosts permitidos (separados por vírgula) |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `http://localhost,http://127.0.0.1` | Origens confiáveis para CSRF |
| `DJANGO_SECURE_SSL_REDIRECT` | `False` | Redireciona HTTP → HTTPS |
| `DJANGO_HSTS_SECONDS` | `0` | Duração do HSTS em segundos |
