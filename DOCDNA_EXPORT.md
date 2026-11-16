# DocDNA — continuidade e checkpoints

Este arquivo registra trabalho verificado no repositório local. Não substitui
o código nem representa a recuperação integral das conversas anteriores.

## 2026-11-16 — CF-QA 003.9.5: cobertura da correlação e agregação

### Contexto

- Checkpoint anterior informado pelo usuário: 1.896 testes aprovados.
- O repositório já continha numerosas alterações locais; foram preservadas.
- A etapa `qr_visual_concealment_correlation` já estava implementada entre
  inspeção estrutural QR e análise de prompt injection. Seu contrato de
  performance foi preservado.

### Mudanças

- Adicionados 17 casos diretos para `QrVisualConcealmentCorrelator`, cobrindo
  remoção de evidência tipográfica de grupo confirmado e preservação em casos
  de incerteza, truncamento, payload divergente, hash incompatível, página,
  fonte ou região diferente, evidências incompletas/reordenadas e texto
  instrucional misturado com bits.
- Os testes verificam a preservação de texto branco, baixo contraste e texto
  minúsculo independente. Usam registros estruturais sintéticos já confirmados;
  não validam reconstrução ou decodificação real de QR.
- Corrigido `BatchFindingAggregationService._aggregate_visual_concealment()`:
  `low_contrast_text_findings` agora participa das ocorrências, documentos
  afetados, prevalência e confiança máxima de ocultação visual.
- Adicionados dois testes de regressão: documento apenas com baixo contraste
  e lote com achados mistos. Nenhuma aba Excel foi criada.

### Validação executada

Ambiente confirmado pelo PyCharm: Python 3.12.10 em `.venv`, gerenciador `pip`.

Antes da correção, o comando abaixo apresentou **2 failed, 26 passed**:

```powershell
& '.\.venv\Scripts\python.exe' -B -m pytest -q -p no:cacheprovider tests/domain/concealment/services/test_qr_visual_concealment_correlator.py tests/domain/services/test_batch_finding_aggregation_service.py
```

As duas falhas demonstraram a omissão de baixo contraste na agregação.
Após a correção, foi executada a suíte completa:

```powershell
& '.\.venv\Scripts\python.exe' -B -m pytest -q -p no:cacheprovider
```

Resultado: **1.915 passed in 54.99s**. Verificação de whitespace dos dois
arquivos rastreados alterados: `git diff --check`, sem erros.

### Limitações e próximos passos

- Não houve validação funcional dos cinco PDFs históricos nem comparação com
  laudo externo; não se conclui que os 195 alertas históricos eram falsos.
- O filtro `_span_is_qr_graphics()` da análise de prompt injection ainda usa
  critérios geométricos menos estritos que o correlacionador de ocultação.
  Caracterizar e reconciliar esse contrato em alteração separada.
- Auditar/expor `qr_structural_findings` nos dashboards e no Excel, incluindo
  justificativa rastreável da correlação e estados inconclusivos.
- Avaliar a preservação de coordenadas nas evidências de texto minúsculo.
- Validar decodificação real e casos variados, preservando alertas independentes
  e análise semântica de payloads potencialmente maliciosos.
- Nenhum commit, push ou upgrade de dependências foi executado.

## 2026-11-16 — auditoria funcional do lote f502ebd5 e melhorias de triagem

### Identidade e escopo

- Localizado `storage/reports/batches/docdna_lote_f502ebd5.xlsx`.
- Os seis PDFs em `storage/uploads/<ID da análise>.pdf` tiveram SHA-256
  conferido contra a aba `01 - Documentos`: seis correspondências exatas.
- Isso vincula os PDFs à exportação; não demonstra identidade com os processos
  diferentes citados no laudo externo. O laudo externo não foi revalidado.
- O Excel original e os PDFs originais foram preservados. Nenhum documento
  foi enviado a serviços externos.

### Diagnóstico funcional local

- Nos três PDFs com camada nativa, cada grupo matricial QR obteve
  `CONFIRMED_PAYLOAD_MATCH` usando os leitores/decodificadores reais. Cada um
  passou de 65 para zero evidências tipográficas após a correlação.
- Os três PDFs escaneados não possuíam texto nativo nem alertas tipográficos
  nessa análise. Os detectores nativos não demonstram ausência de ocultação
  em imagens rasterizadas.
- A segmentação textual do OCR separava blocos numéricos que estavam na mesma
  linha visual. Foram recuperados candidatos adicionais de 48 dígitos nos
  três PDFs escaneados: comprimentos [40] → [40,48], [] → [48], [] → [48].
- Todos os candidatos numéricos dessa auditoria continuam INCONCLUSIVE no
  validador estrito. Captura não equivale a validação ou confirmação de fraude.
- Conta/cliente foram extraídos, mas titular e débito automático continuaram
  não identificados nos seis documentos. Parte das faturas também não foi
  lida. Esses campos não foram inferidos a partir de outros arquivos.

### Alterações

- `PrintedNumericLineReader.read()` aceita opcionalmente `ocr_text_boxes`.
  Complementa o texto agregado com quatro blocos ASCII de 12 dígitos próximos
  na mesma linha/página. Não altera dígitos, não fatia fluxos maiores e não
  flexibiliza `NumericLineValidator`. O builder de contexto fornece as caixas.
- Dashboard do lote: resumo comparativo independente, com maior severidade,
  documentos afetados e documentos sem achados individuais que possuem
  apontamentos comparativos. A classificação individual foi preservada.
- Excel: findings `PAYMENT_LINE_INVALID_STRUCTURE` participam da justificativa
  de triagem, com referência a `03 - Evidências` e explicação da diferença
  frente ao status INVALID estrito. A contagem de validações não foi adulterada.
- Campos cadastrais não extraídos são explicitados como limitações na triagem,
  quando há identificadores observados. Ausência de leitura não aumenta por
  si só a prioridade nem significa ausência do campo no PDF.
- Descrição QR passou a "Mesmo conteúdo QR com imagens diferentes". O código
  persistido `QRCODE_REGENERATED` e a severidade foram preservados. O texto
  esclarece que a causa da diferença visual não foi determinada.
- Adicionado `scripts/audit_exported_batch.py`: auditoria local reproduzível,
  com bloqueio de inspeção quando o PDF falta ou seu hash diverge. Registra
  falhas separadamente, sem convertê-las em ausência de findings.
- Nenhuma aba Excel adicional foi criada.

### Validação executada na versão final

```powershell
& '.\.venv\Scripts\python.exe' -B -m pytest -q -p no:cacheprovider
```

Resultado: **1.931 passed in 51.83s** (16 testes novos desde o checkpoint 1.915).
Os testes abrangem geometria com controles negativos, integração de export,
triagem contextual e integridade da auditoria. `git diff --check` dos arquivos
rastreados envolvidos passou. Não foi realizada inspeção visual em navegador.

```powershell
& '.\.venv\Scripts\python.exe' -B -m scripts.audit_exported_batch --workbook storage/reports/batches/docdna_lote_f502ebd5.xlsx --output storage/reports/audits/f502ebd5/audit_current.json
```

Resultado: **INSPECTED_HASH_VERIFIED: 6**. O JSON local contém hashes e métricas,
sem payloads QR. Arquivos de auditoria em `storage/reports` permanecem ignorados
pelo Git. A auditoria executa extração e correlação; não recria o lote original,
não atualiza repositórios em memória e não equivale ao processamento completo
de um novo lote ou à revisão visual humana das regiões detectadas.

### Continuidade

- Reprocessar os seis documentos em um novo lote para conferir as novas
  localizações, findings contextuais, dashboard e exportação integrada.
- Investigar OCR localizado dos campos cadastrais não lidos, com recortes
  generalizáveis e controles negativos; não preencher dados por semelhança.
- Ampliar controles reais de ocultação em PDFs nativos e rasterizados.
- Permanece pendente reconciliar o filtro geométrico da análise tipográfica
  de prompt injection e expor registros estruturais QR na apresentação.
- Sem commits, pushes, upgrades ou sobrescrita das alterações locais anteriores.

## 2026-11-16 — localização integral e confiança OCR no Excel

### Problemas demonstrados

- No lote `8ad01dad`, quatro candidatos de 48 dígitos tinham localização
  registrada com apenas 47. A ordenação priorizava a hipótese bancária de
  47 posições sobre o candidato integral de estrutura desconhecida.
- Na aba de localizações, a confiança OCR em 0–100 passava por um helper de
  proporções 0–1. Valores como 42,25 eram limitados a 1 e exibidos como 100%.
- Antes das correções, os testes centrais apresentaram **8 failed, 12 passed**.

### Correções controladas

- `NumericLineVisualEvidenceBuilder._build_candidate_targets()` prioriza o
  conteúdo integral. A busca de todas as ocorrências continua ativa, mantendo
  bloqueios por ambiguidade. Subseções continuam disponíveis quando o conteúdo
  integral não é encontrado. Localização não altera a validação estrutural.
- `BatchExcelExportService` converte explicitamente a confiança de localizações
  `numeric_line` de porcentagem OCR para proporção Excel. Assim, 42,25 vira
  0,4225 e 0,5 vira 0,005. Outros tipos mantêm seu contrato anterior.
- Os dados analíticos e limites de confiança do detector foram preservados.
- Adicionados 14 casos de regressão e controle.

### Testes executados

Testes centrais reproduzíveis:

```powershell
& '.\.venv\Scripts\python.exe' -B -m pytest -q -p no:cacheprovider tests/test_cf_qa_002_4_localizador_seguranca.py tests/frontend/exports/test_numeric_location_confidence_excel.py
```

O conjunto ampliado, incluindo extração/localização, contexto financeiro,
geometria ITF, corroboração nativa e baixo contraste no Excel, passou:
**55 passed in 0.84s**.

```powershell
& '.\.venv\Scripts\python.exe' -B -m pytest -q -p no:cacheprovider
```

Suíte completa: **1.945 passed in 47.22s**. `git diff --check` dos arquivos
rastreados envolvidos passou.

### Validação funcional com os seis PDFs

- Os seis hashes dos PDFs foram conferidos contra `docdna_lote_8ad01dad.xlsx`.
- Executados `BatchProcessor.process()` e `BatchExcelExportService.export()`
  reais, em processo local separado: **6 concluídos, 0 falhas**.
- Novo lote: `d9fb7647-02d9-4e04-870a-aac08888c7a2`.
- Novo Excel: `storage/reports/batches/docdna_lote_d9fb7647.xlsx`.
- Manifesto: `storage/reports/audits/8ad01dad/numeric_locations_checkpoint.json`.
- O hash do Excel original foi novamente verificado após o processamento:
  permaneceu inalterado.
- As nove localizações exportadas correspondem integralmente aos respectivos
  candidatos. Os seis candidatos de 48 dígitos preservam seus 48 dígitos.
- As nove confianças exportadas coincidem com a confiança OCR original / 100.
- Findings contextuais `PAYMENT_LINE_INVALID_STRUCTURE`: **2 → 4 documentos**.
  Os dois últimos continuam bloqueados por baixa confiança e falta de
  corroboração nativa; não foram promovidos artificialmente.
- As nove validações estritas permanecem inconclusivas. Não houve alteração
  para forçar divergência linha × código.
- Esse lote foi gerado em processo separado do servidor web; seu Excel está
  disponível no disco, mas seu estado em memória não foi inserido na sessão
  do servidor em execução. Não houve validação visual de navegador.

### Pendências preservadas

- Os candidatos de 40/42 dígitos oriundos de campos concatenados ainda exigem
  tratamento contextual, sem remover ocorrências legítimas indiscriminadamente.
- Aproveitar spans nativos com geometria para fatura/débito automático e
  avaliar OCR localizado para documentos escaneados.
- Corrigir a apresentação de "0/4 DVs" quando o método de cálculo não foi
  selecionado, sem tratar esse estado como quatro DVs reprovados.
- Continuam pendentes a exposição dos registros estruturais QR e controles
  reais variados de ocultação. CF-QA 003.9.5 não foi declarado concluído.
- Sem commits, pushes, upgrades ou substituição dos exports anteriores.

## 2026-11-16 — integridade numérica e identificadores posicionados

### Causa raiz e distinção implementada

O leitor encontrava candidatas pelo total de dígitos, mas não transportava
evidência de que parte delas vinha de campos diferentes da mesma linha visual.
O extrator cadastral tinha associação OCR de cabeçalho/valor, porém não recebia
spans nativos posicionados e não separava a região do valor da região do rótulo.

- `PrintedNumericLine` ganhou metadados opcionais, preservando conteúdo bruto,
  normalizado, fonte e índice. Campos comprovadamente unidos são marcados como
  `concatenated_fields`; os casos sem prova suficiente permanecem `unclassified`.
- O leitor exige ocorrência OCR integral única, pelo menos dois campos de tipos
  distintos, página e sistema de coordenadas conhecidos, valores em células
  não sobrepostas na ordem textual e na mesma linha física. Suporte OCR para
  exclusão usa o piso conservador existente de 80%; suporte nativo não recebe
  confiança OCR inventada. Não existe regra por fornecedor, processo ou valor.
- A observação concatenada permanece armazenada e localizada, mas não entra
  como linha de pagamento nos caminhos legado e canônico de comparação ITF.
  O validador mantém INCONCLUSIVE e explica por que a validação de pagamento
  não se aplica. Não foi modificado o cálculo dos padrões bancários.
- O domínio forense preserva o elemento bruto e os metadados no normalizado.
  O detector contextual não promove concatenações comprovadas a findings.
- A estrutura existente de comparação/validação/localização continua distinguindo
  candidata incerta, localização confirmada e associação financeira suficiente.
  Uma localização sozinha não demonstra linha de pagamento nem vínculo com ITF.

### Identificadores nativos e integração

- `DocumentIdentifierService` reutiliza seu motor existente de associação OCR
  para spans nativos normalizados. Internamente utiliza escala equivalente a
  Matrix(2,2); retorna `NATIVE_SPAN`, `pdf_points`, página e retângulos nativos.
  A confiança exportada desses dados é None, não um percentual OCR fabricado.
- Campos empilhados agora preservam `value_region` separada do rótulo.
- `AnalysisContextBuilder` extrai uma vez e compartilha os identificadores com
  o leitor e o contexto. O caso de uso reutiliza esses resultados.
- Metadados chegam ao schema, view model, investigação financeira, aba 01,
  justificativas da aba 04 e classificação das localizações da aba 07.
- Não foram adicionadas abas. Campos cadastrais continuam observacionais.

### Testes e controles executados

Antes da implementação: **2 failed, 3 passed in 0.15s** no módulo novo,
demonstrando a concatenação não tipificada e a ausência da região do valor.
Na fase nativa: **1 failed, 6 passed in 0.27s**, demonstrando a integração ausente.

Comando direcionado final:

```powershell
& '.\.venv\Scripts\python.exe' -B -m pytest -q -p no:cacheprovider tests/domain/readers/test_numeric_line_field_context.py tests/domain/readers/test_printed_numeric_line_reader_preservation.py tests/domain/readers/test_printed_numeric_line_reader_geometry.py tests/domain/services/test_barcode_numeric_line_candidate_selector.py tests/domain/services/test_numeric_line_forensic_element_adapter_location.py tests/test_cf_qa_002_barcode_numeric_line_red.py tests/test_cf_qa_002_barcode_numeric_line_safety.py tests/test_cf_qa_002_financial_reconciliation_red.py tests/test_cf_qa_003_6_identificadores.py tests/test_cf_qa_003_8_geometria_canhoto_real.py tests/domain/concealment/services/test_qr_visual_concealment_correlator.py
```

Resultado: **152 passed in 0.45s**. Controles incluem linhas válidas de 47/48,
concatenação de 40/48, fontes/retângulos nativos, campos sem rótulo, páginas e
linhas diferentes, geometria rotacionada sem associação horizontal, repetição,
baixa confiança, comparação financeira e preservação QR/ocultação.

```powershell
& '.\.venv\Scripts\python.exe' -B -m pytest -q -p no:cacheprovider
```

Resultado final: **1.958 passed in 53.56s**; 13 casos novos desde 1.945.
`git diff --check` dos arquivos envolvidos passou.

### Validação funcional reproduzível

```powershell
& '.\.venv\Scripts\python.exe' -B -m scripts.validate_financial_checkpoint --workbook storage/reports/batches/docdna_lote_f81da90c.xlsx --reference storage/reports/batches/docdna_lote_f502ebd5.xlsx --reference storage/reports/batches/docdna_lote_8ad01dad.xlsx --output-dir storage/reports/audits/f81da90c/field_context_verified
```

Executados BatchProcessor, caso de uso, comparadores e exportador reais:
**6 concluídos, 0 falhas**, hashes dos seis PDFs conferidos contra f81da90c.
Os hashes dos três exports de referência foram preservados.

- Lote final: `fed0f92e-cf5e-4d11-9e5d-b5ae89d56653`.
- Excel: `storage/reports/batches/docdna_lote_fed0f92e.xlsx`.
- Manifesto completo: `storage/reports/audits/f81da90c/field_context_verified/checkpoint.json`.
- Dashboard do lote e seis investigações financeiras: HTTP 200 via TestClient;
  presença da explicação de campos concatenados conferida no HTML.
- Foram conferidas as abas 01, 03, 04, 07, 08 e 09. Os nove valores numéricos
  originais (conteúdo/índice/documento) e os 18 valores financeiros foram
  comparados ao baseline e preservados pelo script.

| Documento (prefixo identificador) | Antes | Depois | Campos recuperados |
|---|---|---|---|
| 0006078-36 | 42 + 48 candidatas genéricas | 42 como campos concatenados; 48 preservada | débito automático |
| 0005510-67 | 42 + 48 candidatas genéricas | 42 como campos concatenados; 48 preservada | fatura e débito automático |
| 4002640-82 | 48 candidata | 48 preservada | fatura e débito automático |
| 8004804-14 | 40 + 48 candidatas | ambas preservadas como incertas | nenhum novo campo |
| 8001785-54 | 48 candidata | preservada como incerta | nenhum novo campo |
| 0878681-35 | 48 candidata | preservada como incerta | nenhum novo campo |

As nove observações permanecem no relatório: duas são identificadas como
concatenações e sete permanecem candidatas incertas (incluindo a de 40 dígitos).
Continuam nove validações e nove comparações inconclusivas, zero INVALID e
zero MISMATCH, com quatro PAYMENT_LINE_INVALID_STRUCTURE. As diferenças
PRINTED/ITF/PIX continuam com vínculo pendente; nenhum valor foi alterado.

As comparações passaram de **62 para 64** exclusivamente por duas coincidências
DOCUMENT_IDENTIFIER_EXACT_MATCH adicionais: fatura e débito automático dos
dois primeiros documentos. ITF, QR e imagens mantiveram as contagens anteriores.
A descrição da comparação de candidatas agora explicita seus limites.

Aviso observado no experimento HTTP: StarletteDeprecationWarning sobre uso de
httpx no TestClient. Nenhuma dependência foi instalada ou atualizada. O teste
HTTP confere renderização de servidor/conteúdo, não inspeção visual em navegador.
O lote de validação viveu em processo separado do servidor web em execução.

### Continuidade e limites

O próximo experimento é OCR localizado de região identificada por cabeçalhos no
canhoto escaneado, começando pelo caso de 40 dígitos, para obter suporte suficiente
à associação de campos sem inferir dados nem usar regras por fornecedor.
Os campos faltantes continuam faltantes; os dois últimos documentos não foram
promovidos artificialmente a findings contextuais. Identidade com o laudo externo
não foi demonstrada. CF-QA 003.9.5 não foi encerrado.

Sem commits, pushes, exclusões de dados, upgrades ou alteração dos baselines.

## 2026-11-16 — continuidade do lote 67f7242f: OCR localizado e papéis numéricos

### Defeitos e escopo demonstrados

- A classificação de concatenações usava apenas caixas OCR, mesmo quando a
  observação vinha de texto nativo. Agora cada fonte utiliza sua própria
  geometria; o motor de associação existente foi preservado.
- A aba 07 chamava sequências não reconhecidas de "Linha digitável". A
  apresentação agora distingue concatenação comprovada, candidata sustentada
  por contexto e sequência inconclusiva, sem alterar os estados do validador.
- O OCR integral omitia campos em canhotos escaneados. Foram adicionados
  recortes derivados de cabeçalhos detectados, sem coordenadas fixas, fornecedor,
  processo, prefixo numérico ou valor monetário usado como regra de detecção.

### Implementação

- `PrintedNumericLineReader` recebe o documento normalizado para localizar
  observações nativas; observações OCR continuam vinculadas às caixas originais.
- `BarcodeNumericLineDetector.classify_candidates()` reutiliza os critérios de
  localização confiável, rótulo e contexto ITF existentes. Marca
  `payment_line_candidate` ou `unresolved_numeric_sequence`; mantém
  `concatenated_fields` intacto. Página, confiança observada e geometria são
  preservadas mesmo quando não há suporte para confiar na associação.
- Localização de candidata não equivale a validação nem vínculo de cobrança.
  Os metadados usam `CONTEXTUAL_NOT_PROVEN`/`UNRESOLVED` explicitamente.
- `DocumentIdentifierService.propose_ocr_regions()` utiliza cabeçalhos de
  campos já suportados e seu tamanho visual. O orçamento local é de quatro
  regiões por documento; nenhuma régua global de validação foi relaxada.
- `OcrReader.read_regions()` lê os recortes a 4x/PSM 6 e converte posições
  para a escala OCR original 2x. O OCR integral não é substituído. Páginas
  rotacionadas conservam o processamento original; o recorte adicional é
  omitido quando sua transformação não foi comprovada.
- Leituras recuperadas são `OCR_REGION`, com confiança real, configuração e
  regiões de origem. Elas não completam dígitos nem corrigem valores por heurística.
- Uma divergência observada entre OCR integral e localizado gerou um controle
  adicional: `reading_conflict`, com `alternative_readings` e justificativa.
  Ambas as leituras são preservadas; a conflitante não sustenta comparação
  cadastral nem exclusão da sequência por suposta concatenação.
- O comparador ITF conserva em metadados os três papéis:
  `payment_line_candidate`, `observed_concatenated_identifiers` e
  `unresolved_numeric_sequence`. Só concatenações comprovadas são excluídas
  dos valores comparados; sequências incertas continuam visíveis.
- Dashboard financeiro e abas 01, 03, 07 e 08 explicitam a distinção e os
  conflitos. A planilha continua unificada, sem abas novas.

### Testes efetivamente executados

Antes das mudanças: **3 failed, 14 passed in 0.37s** para integração nativa
e rótulos; **4 failed in 0.48s** para recuperação por região; posteriormente
**1 failed, 5 passed in 0.39s** para preservação do conflito entre leituras.

Comando direcionado final:

```powershell
& '.\.venv\Scripts\python.exe' -B -m pytest -q -p no:cacheprovider tests/domain/readers/test_identifier_region_ocr.py tests/domain/services/test_numeric_candidate_context_roles.py tests/domain/readers/test_numeric_line_field_context.py tests/frontend/exports/test_numeric_location_context_labels.py tests/test_cf_qa_002_barcode_numeric_line_red.py tests/test_cf_qa_002_barcode_numeric_line_safety.py tests/test_cf_qa_003_4_barcode_multileitura.py tests/test_cf_qa_003_6_identificadores.py tests/test_cf_qa_003_8_geometria_canhoto_real.py tests/frontend/exports/test_numeric_location_confidence_excel.py tests/domain/concealment/services/test_qr_visual_concealment_correlator.py
```

Resultado: **112 passed in 1.42s**.

```powershell
& '.\.venv\Scripts\python.exe' -B -m pytest -q -p no:cacheprovider
```

Resultado final: **1.972 passed in 63.92s**, 14 casos novos desde 1.958.
`git diff --check` dos arquivos desta etapa passou. Os controles incluem
linhas válidas, ITF curto, páginas/linhas diferentes, baixa confiança,
transformação de coordenadas, rotação sem atribuição indevida e conflito OCR.

### Processamento real e artefatos

```powershell
& '.\.venv\Scripts\python.exe' -B -m scripts.validate_financial_checkpoint --workbook storage/reports/batches/docdna_lote_67f7242f.xlsx --reference storage/reports/batches/docdna_lote_f81da90c.xlsx --reference storage/reports/batches/docdna_lote_f502ebd5.xlsx --reference storage/reports/batches/docdna_lote_8ad01dad.xlsx --output-dir storage/reports/audits/67f7242f/ocr_context_verified
```

- Lote final: `e2d72d38-0976-40af-a76f-326af9ab6f95`.
- Excel: `storage/reports/batches/docdna_lote_e2d72d38.xlsx`.
- Manifesto: `storage/reports/audits/67f7242f/ocr_context_verified/checkpoint.json`.
- **6/6 concluídos, 0 falhas**. PDFs conferidos por SHA-256, não por ID interno.
- Os quatro exports de referência permaneceram intactos. As nove observações
  originais e os 18 registros de valores foram comparados e preservados.
- Dashboard do lote e seis páginas financeiras: HTTP 200 via TestClient.
  Não houve inspeção visual em navegador. O lote viveu em processo separado
  do servidor web; o Excel e os HTMLs locais estão disponíveis no disco.
- Abas 01, 03, 04, 07, 08 e 09 conferidas. A aba 08 identifica candidatas e
  sequências incertas por documento, incluindo a sequência BA de 40 dígitos.

### Antes/depois em relação a 67f7242f

| Indicador | Antes | Depois |
|---|---:|---:|
| Observações numéricas/localizações | 9/9 | 9/9 |
| Concatenações comprovadas | 2 | 2 |
| Candidatas com suporte contextual explicitado | sem papel separado | 4 |
| Sequências explicitamente inconclusivas | sem papel separado | 3 |
| Observações cadastrais | 19 | 24 |
| Comparativos | 64 | 64 |
| PAYMENT_LINE_INVALID_STRUCTURE | 4 | 4 |
| INVALID/MISMATCH estritos | 0/0 | 0/0 |

| Documento (prefixo) | Papéis das observações numéricas | Recuperação OCR |
|---|---|---|
| 0006078-36 | 42: concatenação; 48: candidata contextual | sem novo campo |
| 0005510-67 | 42: concatenação; 48: candidata contextual | sem novo campo |
| 4002640-82 | 48: candidata contextual | sem novo campo |
| 8004804-14 | 40: inconclusiva; 48: candidata contextual | débito automático como leitura conflitante |
| 8001785-54 | 48: inconclusiva | fatura/débito como leituras OCR, com confiança limitada |
| 0878681-35 | 48: inconclusiva | fatura/débito como leituras OCR |

As 24 observações não equivalem a 24 identificadores confirmados. No caso BA
de 40 dígitos, o OCR integral leu o fragmento normalizado `381750962417`, enquanto
o recorte leu `381750962477`. O conflito permanece visível na aba 03, com ambas
as leituras; o candidato não foi forçado a concatenação nem a linha válida.
As novas observações não criaram comparativos adicionais.

Os seis documentos continuam em revisão, com nove validações e nove comparações
estritas inconclusivas. As diferenças PRINTED/ITF/PIX mantêm vínculo pendente.
QR/ocultação não foi alterado nem declarado resolvido neste checkpoint.

### Avisos, controle de versão e continuidade

O experimento HTTP emitiu StarletteDeprecationWarning sobre httpx/TestClient.
Nenhuma dependência foi instalada ou atualizada. Uma checagem auxiliar de
texto foi refeita por codificação de literais acentuados no PowerShell; a
verificação corrigida confirmou os papéis na aba comparativa.

`git diff --stat` foi registrado em `git_diff_stat.txt` na pasta de auditoria.
Esse diff inclui mudanças preexistentes de checkpoints anteriores e não inclui
arquivos ainda não rastreados; não representa apenas esta etapa.

Próximo experimento: confrontar visualmente a célula com conflito e testar uma
segunda leitura localizada independente, mantendo as duas versões até obter
suporte suficiente. Não escolher dígitos pelo valor esperado ou pelo laudo.
Sem commits, pushes, exclusões, upgrades ou envio de PDFs a serviços externos.
