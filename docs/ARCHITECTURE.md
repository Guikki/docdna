# DocDNA

## Arquitetura do Projeto

Versão da Arquitetura: 0.2

---

# Objetivo

O DocDNA é uma plataforma de inteligência documental baseada em evidências.

Seu objetivo não é afirmar que um documento é fraudulento.

Seu objetivo é produzir evidências técnicas que auxiliem o analista na tomada de decisão.

---

# Princípios

- Clean Architecture
- SOLID
- REST API
- Programação Orientada a Objetos
- Componentização
- Separação entre domínio e infraestrutura

---

# Filosofia

Toda análise produz evidências.

Nenhum detector produz conclusões.

Conclusões são produzidas exclusivamente pelos motores de análise.

---

# Estrutura

api/

Domain/

Infrastructure/

Frontend/

Config/

Schemas/

Utils/

Exceptions/

---

# Convenções

Detector → termina com Detector

Engine → termina com Engine

Repository → termina com Repository

Use Case → termina com UseCase

Service → termina com Service

Model → substantivos

DTO → Request / Response

---

# Checkpoints

CF-001 ✅ Recepção de documentos

CF-002 ✅ Identidade documental

CF-003 ✅ Interface de Upload

---

CA-001

Centralização dos caminhos do projeto.

Introdução do BASE_DIR.

---

## Pipeline de leitura documental

O DocDNA utiliza leitores independentes para extrair informações brutas dos documentos.

Os Readers não produzem conclusões nem classificações de fraude. Sua responsabilidade é apenas extrair e estruturar dados que serão utilizados posteriormente pelos Detectores.

Fluxo atual:

```text
PDF recebido
    │
    ▼
Document
    │
    ├── PdfReader
    │       └── PdfInfo
    │
    ├── NativeTextReader
    │       └── DocumentText
    │
    └── ImageReader
            └── list[DocumentImage]

---

# CA-004 — Consolidação do OCR e das evidências visuais

## Status

Concluído.

## Contexto

Durante os ciclos CF-012, CF-013 e CF-014, o DocDNA passou a executar:

- validação estrutural de sequências numéricas;
- comparação entre linha digitável e código de barras;
- OCR posicional;
- localização visual de sequências;
- geração de páginas anotadas para auditoria.

A primeira implementação possuía dois componentes independentes de OCR:

- `OcrReader`, responsável pelo texto consolidado;
- `OcrLayoutReader`, responsável pelas palavras, coordenadas e confiança.

Essa estrutura fazia o Tesseract processar cada página duas vezes.

O custo duplicado seria especialmente prejudicial ao futuro processamento em lote previsto no CF-015.

## Decisão arquitetural

Foi criado o model:

```text
app/domain/models/ocr_result.py