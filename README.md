# DocDNA

Ferramenta de inteligência documental para análise antifraude baseada em evidências.

## Stack

- Python
- FastAPI
- OpenCV
- Tesseract OCR
- OpenPyXL
- Jinja2

## Executando

python -m uvicorn app.main:app --reload

## Estrutura

app/
domain/
frontend/
infrastructure/
schemas/
storage/

## Status

CF017
✔ Upload individual
✔ Upload em lote
✔ OCR
✔ Código de barras
✔ Comparação entre documentos
✔ Exportação Excel
✔ Inteligência Comparativa