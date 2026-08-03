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

---

# Refatoração #1 — Consolidação da Camada de Fingerprints

## Status

Concluída.

## Contexto

Os ciclos CF-020 e CF-021 introduziram a primeira camada de identificação visual do DocDNA.

Essa camada é responsável por representar elementos estruturais presentes em documentos, sem realizar qualquer inferência sobre autenticidade ou fraude.

Cada fingerprint representa exclusivamente um elemento técnico identificado durante a leitura documental.

A responsabilidade pela comparação entre fingerprints permanece restrita aos Comparators e Engines.

## Fingerprints implementados

```text
Fingerprint
├── BarcodeFingerprint
├── ImageFingerprint
│   ├── LogoFingerprint
│   └── SignatureFingerprint
└── QRCodeFingerprint
```

Todos os fingerprints são objetos imutáveis (`dataclass(frozen=True)`) e encapsulam apenas informações técnicas necessárias para as etapas posteriores da análise.

---

## Builders implementados

Foi criada uma camada responsável pela construção dos fingerprints a partir das informações extraídas pelos Readers.

Builders implementados:

```text
app/services/

ImageFingerprintBuilder

QRCodeFingerprintBuilder

LogoFingerprintBuilder

SignatureFingerprintBuilder
```

Esses componentes possuem uma única responsabilidade:

converter dados técnicos extraídos pelos Readers em objetos pertencentes ao domínio.

Eles não executam OCR, leitura de PDF, comparações ou inferências.

---

## Serviços de Domínio

Permanece separada a camada de serviços de domínio.

```text
app/domain/services/
```

Essa camada contém apenas regras de negócio puras e componentes responsáveis por coordenar modelos do domínio.

Não possui dependências de infraestrutura, FastAPI, banco de dados ou bibliotecas externas.

---

## Padronização das dataclasses

Durante esta refatoração foi identificada uma incompatibilidade entre:

- `@dataclass(slots=True)`
- `super().__post_init__()`

Todas as subclasses de `Fingerprint` passaram a invocar explicitamente o `__post_init__` da classe base, garantindo comportamento consistente e previsível.

---

## Testes

Ao término da Refatoração #1 a suíte completa de testes foi executada com sucesso.

Resultado:

```text
150 testes aprovados
```

A partir deste ponto, a camada de fingerprints é considerada estável.

---

## Próximos ciclos

A próxima etapa da arquitetura inicia a integração entre Readers e Fingerprints.

Roadmap:

```text
CF-022
Extração automática de fingerprints

↓

CF-023
Comparadores

↓

CF-024
Evidence Builder

↓

CF-025
Pipeline completa de análise documental
```

---

## Backlog Arquitetural

Itens aprovados para futura avaliação:

- Reavaliar a criação de uma camada explícita de Application caso o crescimento do projeto justifique a separação entre `app/services` e `app/domain/services`.
- Revisar a localização do model `DocumentImage` conforme a evolução da infraestrutura de leitura documental.
- Expandir a cobertura com testes de integração da pipeline completa.