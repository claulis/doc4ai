#!/usr/bin/env bash
set -o errexit

apt-get install -y poppler-utils tesseract-ocr tesseract-ocr-por tesseract-ocr-eng libmagic1

pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --noinput
