# DocDNA — Arquitetura do Projeto

**Documento de arquitetura e decisões técnicas**

**Estado:** ativo  
**Fase atual:** Fase 2  
**Versão documental:** 0.3

---

# 1. Visão geral

DocDNA é uma ferramenta interna de análise documental e antifraude.

Seu objetivo é analisar documentos PDF individualmente e em lote por meio de múltiplas técnicas independentes de análise forense, preservando evidências técnicas estruturadas e apresentando-as de forma compreensível para revisão humana.

O sistema não deve depender de uma única técnica para determinar a confiabilidade de um documento.

A arquitetura foi construída para permitir a coexistência de diferentes camadas de análise, incluindo:

- integridade do arquivo;
- estrutura do PDF;
- texto nativo;
- OCR;
- documento normalizado;
- imagens;
- fingerprints;
- códigos de barras;
- linhas digitáveis;
- validações financeiras;
- comparação entre linha digitável e barcode;
- localização visual de evidências;
- Prompt Injection;
- ocultação visual de texto;
- análise individual;
- análise em lote;
- agregação de achados;
- priorização para revisão humana.

O projeto utiliza principalmente:

- Python;
- FastAPI;
- Uvicorn;
- Jinja2;
- HTML;
- CSS;
- JavaScript;
- PyMuPDF;
- Pillow;
- pytesseract / Tesseract;
- OpenCV e NumPy quando necessários;
- pytest.

O ambiente principal de desenvolvimento é Windows + PowerShell + `.venv`.

Execução local:

```powershell
python -m uvicorn app.main:app --reload
```

O projeto não utiliza Docker como requisito de desenvolvimento ou execução.

---

# 2. Princípio arquitetural central

A regra mais importante do DocDNA é:

> **Análise produz evidências. Detectores não produzem conclusões de fraude.**

Um detector pode afirmar, por exemplo:

- texto com cor branca ou próxima de branco foi encontrado;
- texto muito pequeno foi encontrado;
- determinada linha digitável possui dígito verificador inválido;
- barcode e representação textual divergem;
- determinado padrão textual é compatível com Prompt Injection;
- determinada região do PDF possui características incomuns.

Um detector não deve afirmar automaticamente:

> "Este documento é fraudulento."

A conclusão investigativa pertence a uma camada posterior de interpretação e, principalmente, à revisão humana.

Portanto:

```text
Sinal técnico
    ↓
Finding / Evidence
    ↓
Contexto da análise
    ↓
Apresentação / correlação
    ↓
Priorização
    ↓
Revisão humana
```

Esse princípio também deverá ser preservado quando a camada de IA for implementada.

---

# 3. Objetivos arquiteturais

A arquitetura do DocDNA busca:

1. separar extração, detecção, interpretação e apresentação;
2. evitar dependência entre detectores;
3. permitir evolução incremental;
4. permitir testes unitários das regras de domínio;
5. preservar evidências técnicas estruturadas;
6. permitir rastrear um achado até sua origem;
7. permitir análise individual e agregada;
8. impedir que a interface seja a responsável por regras de domínio;
9. impedir que detectores sejam responsáveis por decisões de UX;
10. preparar o sistema para processamento futuro de grandes lotes;
11. manter explicabilidade;
12. permitir futura integração com IA sem substituir análises determinísticas.

---

# 4. Organização conceitual

A arquitetura atual pode ser representada de forma simplificada como:

```text
PDF
 │
 ▼
Readers / Extractors
 │
 ▼
Modelos estruturados
 │
 ▼
Detectors / Services / Validators
 │
 ▼
Findings / Evidences / Locations
 │
 ▼
AnalysisContext
 │
 ▼
Use Cases
 │
 ▼
View Models / Builders
 │
 ├───────────────┐
 ▼               ▼
Investigação     Batch
 │               │
 ▼               ▼
Templates      Agregação
 │               │
 └───────┬───────┘
         ▼
      Usuário
```

Essa separação deve ser mantida sempre que uma nova feature for criada.

---

# 5. Regra de completude de feature

Uma feature não é considerada concluída apenas porque seu detector funciona.

Quando aplicável, uma feature deve percorrer:

```text
Detector / Service
        ↓
AnalysisContext
        ↓
UseCase
        ↓
ViewModel
        ↓
Template / Investigação
        ↓
Panorama individual ou lote
        ↓
Usuário
```

Isso evita funcionalidades que existam tecnicamente no backend, mas permaneçam invisíveis ao analista.

Nem toda feature precisa obrigatoriamente possuir todas essas etapas.

Por exemplo:

- uma regra puramente estrutural pode não gerar imagem;
- uma localização visual pode não participar de determinada agregação;
- uma informação operacional pode não representar um finding.

A regra é:

> se a informação é relevante para a decisão do usuário, deve existir um caminho claro até a interface.

---

# 6. Domínio documental

O DocDNA trabalha com uma representação normalizada do documento.

A normalização permite que diferentes detectores trabalhem sobre uma estrutura comum, em vez de cada detector reinterpretar diretamente o PDF.

Conceitualmente:

```text
PDF
 ↓
extração
 ↓
Document
 ├── Page
 │    ├── TextSpan
 │    └── informações estruturais
 │
 └── representação normalizada
```

Essa camada é particularmente importante para análises tipográficas e visuais.

Ela permite preservar características como:

- página;
- conteúdo textual;
- posição;
- bounding box;
- fonte;
- tamanho da fonte;
- cor;
- atributos visuais.

Esses dados podem posteriormente ser consumidos por detectores diferentes.

---

# 7. AnalysisContext

`AnalysisContext` representa o conjunto estruturado de resultados produzidos durante a análise de um documento.

Ele funciona como ponto de consolidação entre a pipeline de análise e as camadas posteriores.

O contexto atual inclui, entre outros:

- identidade do documento;
- nome original;
- nome armazenado;
- caminho;
- extensão;
- MIME type;
- tamanho;
- SHA-256;
- data de upload;
- status operacional;
- informações estruturais do PDF;
- texto nativo;
- OCR;
- imagens;
- image fingerprints;
- barcodes;
- linhas digitáveis;
- validações de linha digitável;
- OCR text boxes;
- localizações de linha digitável;
- documento normalizado;
- análise de ocultação visual;
- localizações de ocultação visual.

O `AnalysisContext` não deve se transformar em detector.

Sua responsabilidade é transportar o estado consolidado da análise.

---

# 8. Integridade e identidade do arquivo

O DocDNA calcula SHA-256 do documento analisado.

O hash possui função de identidade e integridade.

Ele permite:

- identificar exatamente o arquivo analisado;
- detectar arquivos binariamente idênticos;
- registrar a versão exata do documento;
- preparar futuras rotinas de deduplicação;
- permitir rastreabilidade;
- apoiar auditoria futura.

Importante:

> SHA-256 não determina autenticidade documental.

Dois PDFs visualmente iguais podem possuir hashes diferentes.

Dois arquivos com o mesmo SHA-256 podem ser considerados, para fins práticos do sistema, o mesmo conteúdo binário.

O hash deve ser tratado como evidência de identidade do arquivo, e não como detector de fraude.

---

# 9. Estrutura do PDF

A análise estrutural coleta informações do documento PDF.

Entre elas:

- quantidade de páginas;
- presença de texto;
- presença de imagens;
- versão do PDF;
- título;
- autor;
- creator;
- producer;
- data de criação;
- data de modificação.

Esses dados alimentam o panorama técnico do documento e poderão futuramente alimentar detectores de anomalias de metadados.

A ausência ou presença isolada de determinado metadado não deve ser tratada automaticamente como fraude.

---

# 10. Texto nativo

O DocDNA extrai o texto nativo existente no PDF.

Essa camada permite:

- identificar documentos que possuem camada textual;
- obter conteúdo sem OCR quando disponível;
- alimentar normalização;
- alimentar detectores textuais;
- comparar conteúdo nativo e conteúdo visual futuramente.

A ausência de texto nativo não representa, por si só, comportamento suspeito.

Documentos escaneados podem ser inteiramente compostos por imagens.

---

# 11. OCR

OCR é uma etapa própria da pipeline.

Não deve ser tratado apenas como fallback.

O OCR permite:

- ler documentos escaneados;
- recuperar texto presente apenas visualmente;
- produzir caixas/localizações textuais;
- alimentar detectores que dependem do conteúdo visual;
- complementar o texto nativo.

A arquitetura deve preservar a origem da informação.

Sempre que relevante, deve ser possível distinguir:

```text
native_text
ocr
normalized_document
```

Essa distinção é importante para análise forense.

---

# 12. Imagens e fingerprints

O DocDNA extrai imagens internas dos documentos e pode gerar fingerprints dessas imagens.

Fingerprints devem ser tratados como representações técnicas para comparação.

Eles não devem produzir conclusão de fraude diretamente.

A arquitetura prevê evolução para fingerprints especializados:

- ImageFingerprint;
- LogoFingerprint;
- QRCodeFingerprint;
- SignatureFingerprint.

Existe um item de refatoração arquitetural em aberto:

> avaliar futuramente a criação de um conceito genérico de "Fingerprint Visual" compartilhado pelos diferentes tipos de fingerprint.

Essa abstração não deve ser criada prematuramente.

Primeiro devem existir implementações concretas suficientes para justificar uma interface comum.

---

# 13. Barcode

O DocDNA realiza leitura de códigos de barras presentes nos documentos.

A análise de barcode é independente da representação textual impressa.

Isso é importante porque um dos casos de fraude que motivaram o projeto envolve:

```text
barras
   ≠
numeração textual apresentada
```

Portanto, sempre que possível, o sistema deve preservar separadamente:

- conteúdo lido do barcode;
- conteúdo da linha impressa;
- resultado da conversão;
- resultado da comparação.

---

# 14. Linha digitável

O DocDNA identifica sequências numéricas compatíveis com linhas digitáveis.

Essas sequências podem possuir origens diferentes, como:

- OCR;
- texto nativo;
- documento normalizado;
- análise visual normalizada.

A origem deve ser preservada.

A identificação de uma sequência compatível não significa automaticamente que ela seja válida.

Por isso, identificação e validação são responsabilidades diferentes.

---

# 15. Validação financeira

Linhas digitáveis detectadas podem ser submetidas a validações estruturais.

Entre os estados possíveis:

```text
VALID
INVALID
INCONCLUSIVE
```

As validações podem utilizar regras como:

- Módulo 10;
- Módulo 11;
- regras específicas de boleto;
- regras específicas de arrecadação/concessionária.

A arquitetura separa:

```text
detecção da linha
        ↓
classificação do tipo
        ↓
validação estrutural
        ↓
resultado
```

Um resultado inválido é um achado técnico relevante, mas ainda não equivale automaticamente a fraude.

---

# 16. Comparação linha digitável × barcode

Quando os dados necessários estão disponíveis, o DocDNA compara a representação textual com o código de barras.

Estados conceituais:

```text
MATCH
MISMATCH
INCONCLUSIVE
```

Essa análise possui especial relevância porque permite detectar divergências entre duas representações que deveriam ser consistentes.

Um `MISMATCH` deve ser tratado como evidência relevante e priorizável para revisão humana.

---

# 17. Localização visual da linha digitável

O DocDNA pode localizar visualmente a linha digitável no documento.

Essa camada existe para transformar um resultado técnico em evidência revisável.

Conceitualmente:

```text
linha detectada
      ↓
localização
      ↓
página
      ↓
coordenadas
      ↓
imagem de origem
      ↓
imagem anotada
      ↓
usuário
```

A localização não altera o resultado da validação.

Ela aumenta a explicabilidade.

---

# 18. Prompt Injection

O DocDNA possui análise de Prompt Injection em conteúdo documental.

Essa análise busca padrões textuais compatíveis com tentativas de instruir, manipular ou interferir em sistemas de IA ou processamento automatizado.

A arquitetura separa:

```text
detecção textual
      ↓
evidências
      ↓
assessment
      ↓
score / categorias / detectores
      ↓
localização visual
      ↓
apresentação
```

A existência de um padrão compatível com Prompt Injection não implica automaticamente intenção maliciosa.

O sistema deve apresentar:

- evidências;
- categoria;
- confiança;
- risco;
- localização quando disponível;
- contexto para revisão.

---

# 19. Localização de Prompt Injection

A localização visual de Prompt Injection é uma etapa distinta da detecção.

Ela procura relacionar a evidência textual a uma região da página.

Dependendo da origem da evidência, essa localização pode utilizar mecanismos de correspondência textual e/ou OCR.

A localização deve ser tratada como evidência derivada.

Ela existe para responder:

> "Onde está no documento o trecho que produziu esse apontamento?"

---

# 20. Ocultação visual textual

O DocDNA possui uma camada específica para análise de possíveis formas de ocultação visual de texto.

Atualmente essa camada inclui:

- WhiteTextDetector;
- TinyTextDetector;
- VisualConcealmentAnalysisService.

O objetivo é detectar fatos observáveis relacionados à apresentação do texto.

Exemplos:

- texto branco;
- texto quase branco;
- texto muito pequeno;
- texto pequeno em relação ao contexto;
- combinações de sinais técnicos.

A arquitetura não deve presumir intenção.

Portanto:

```text
texto branco
    ≠
fraude

texto pequeno
    ≠
Prompt Injection

ocultação visual
    ≠
intenção maliciosa
```

Esses sinais podem ser relevantes isoladamente ou em combinação com outras evidências.

---

# 21. TextConcealmentFinding

`TextConcealmentFinding` representa um achado objetivo relacionado à possível ocultação visual textual.

O finding preserva informações como:

- código;
- detector;
- página;
- texto;
- BoundingBox;
- fonte;
- tamanho da fonte;
- cor;
- confiança;
- sinais técnicos;
- indicação de near-white;
- indicação de small text;
- indicação de relative small text;
- indicação de conteúdo semelhante a instrução.

O modelo deve continuar sendo factual.

Ele não deve declarar:

- fraude;
- Prompt Injection;
- intenção maliciosa.

A presença do `BoundingBox` é especialmente importante porque permite que a evidência seja localizada diretamente no PDF.

---

# 22. VisualConcealmentAnalysisService

O `VisualConcealmentAnalysisService` coordena detectores relacionados à ocultação visual.

Atualmente ele combina resultados de:

```text
WhiteTextDetector
TinyTextDetector
```

Conceitualmente:

```text
Normalized Document
        ↓
VisualConcealmentAnalysisService
        │
        ├── WhiteTextDetector
        │
        └── TinyTextDetector
        │
        ▼
VisualConcealmentAnalysis
```

O service coordena.

Os detectores detectam.

O modelo consolida.

Essas responsabilidades devem permanecer separadas.

---

# 23. Localização visual de ocultação

A localização de ocultação visual segue uma regra arquitetural diferente da localização de Prompt Injection.

Para `TextConcealmentFinding`, a posição já é conhecida.

O finding preserva o `BoundingBox` nativo extraído do PDF.

Portanto:

> a localização visual de ocultação não deve refazer OCR nem executar matching textual para descobrir onde o texto está.

Fluxo:

```text
TextSpan
   ↓
BoundingBox nativo
   ↓
TextConcealmentFinding
   ↓
VisualConcealmentEvidenceBuilder
   ↓
VisualConcealmentLocation
   ↓
renderização da página
   ↓
região destacada
   ↓
usuário
```

Essa decisão evita:

- matching desnecessário;
- falsos matches;
- custo adicional de OCR;
- perda de precisão;
- duplicação de responsabilidade.

---

# 24. VisualConcealmentEvidenceBuilder

O `VisualConcealmentEvidenceBuilder` transforma um finding já localizado em evidência visual para revisão humana.

Sua responsabilidade é:

1. receber o PDF;
2. receber `TextConcealmentFinding`;
3. utilizar o `BoundingBox` preservado;
4. renderizar a página;
5. destacar a região;
6. salvar imagem de origem;
7. salvar imagem anotada;
8. produzir `VisualConcealmentLocation`.

O builder não deve tentar redetectar o texto.

Ele não é detector.

Ele é um produtor de evidência visual derivada.

---

# 25. VisualConcealmentLocation

`VisualConcealmentLocation` representa a localização visual de um finding.

Ele preserva:

- índice do finding;
- código;
- detector;
- página;
- conteúdo;
- coordenadas;
- confiança;
- caminho da imagem de origem;
- caminho da imagem anotada;
- estado de localização;
- mensagem;
- fonte;
- tamanho;
- cor.

As coordenadas são mantidas na escala nativa do PDF.

As imagens são artefatos derivados para revisão humana.

---

# 26. AnalysisViewBuilder

O `AnalysisViewBuilder` transforma os resultados técnicos da análise em uma estrutura apropriada para apresentação.

Ele não deve executar detecção.

Entre suas responsabilidades atuais estão:

- formatação de datas;
- formatação de tamanhos;
- tradução de estados;
- preparação de metadados;
- preparação de OCR;
- preparação do documento normalizado;
- preparação de fingerprints;
- preparação de barcode;
- preparação de linha digitável;
- preparação das validações;
- preparação das comparações;
- preparação de localizações;
- preparação de Prompt Injection;
- preparação de ocultação visual;
- preparação de evidências.

Fluxo:

```text
AnalysisContext / dados da análise
        ↓
AnalysisViewBuilder
        ↓
dict / ViewModel de apresentação
        ↓
InvestigationViewBuilder / Templates / Batch
```

Regras forenses novas não devem ser implementadas diretamente no `AnalysisViewBuilder`.

---

# 27. Investigação individual

A análise individual é apresentada em cards temáticos.

Os cards agrupam informações relacionadas para facilitar revisão humana.

A organização temática atual inclui áreas como:

- identidade e integridade;
- estrutura;
- conteúdo;
- visual;
- financeiro;
- IA e segurança;
- evidências.

Cada card possui um status analítico de apresentação.

Estados:

```text
ALERT
ATTENTION
CLEAR
NOT_EXECUTED
```

A interface deve permanecer sóbria.

O objetivo não é criar alarmes visuais excessivos.

O status deve chamar atenção de forma proporcional, profissional e compreensível.

---

# 28. Ordenação dos cards individuais

Os cards da investigação individual são ordenados por prioridade analítica.

Precedência:

```text
ALERT
   ↓
ATTENTION
   ↓
CLEAR
   ↓
NOT_EXECUTED
```

Cards com maior necessidade de revisão aparecem primeiro.

Quando dois ou mais cards possuem o mesmo status, a ordem temática original é preservada.

Isso garante:

- prioridade sem desorganização;
- comportamento previsível;
- estabilidade visual;
- facilidade de leitura.

A quantidade de evidências não é utilizada atualmente como critério automático de desempate.

---

# 29. Status operacional × status analítico

O DocDNA diferencia dois conceitos que não podem ser confundidos.

## 29.1 Status operacional

Responde:

> "O processamento terminou?"

Exemplos conceituais:

```text
PENDING
PROCESSING
COMPLETED
FAILED
```

## 29.2 Status analítico

Responde:

> "O resultado produzido precisa de revisão?"

Estados:

```text
ALERT
ATTENTION
CLEAR
NOT_EXECUTED
```

Portanto:

```text
COMPLETED
```

não significa:

```text
CLEAR
```

Um documento pode estar:

```text
processamento = COMPLETED
situação analítica = ALERT
```

Essa separação deve ser preservada em toda a aplicação.

---

# 30. Significado dos estados analíticos

## ALERT

Indica que existem achados com prioridade elevada para revisão.

Não significa automaticamente fraude.

Representação de interface:

```text
Alta prioridade
```

## ATTENTION

Indica que existem achados que justificam revisão humana.

Representação de interface:

```text
Revisão recomendada
```

## CLEAR

Indica que os verificadores relevantes executados não produziram apontamentos suficientes para elevar a prioridade.

`CLEAR` não significa:

- documento autêntico;
- ausência absoluta de fraude;
- certificação.

Significa apenas ausência de apontamentos relevantes nas análises executadas.

## NOT_EXECUTED

Indica que determinada análise não foi executada ou não produziu dados suficientes para classificação.

`NOT_EXECUTED` não deve ser tratado como `CLEAR`.

---

# 31. InvestigationStatusResolver

A determinação do status analítico deve seguir uma precedência clara.

Conceitualmente:

```text
ALERT > ATTENTION > CLEAR > NOT_EXECUTED
```

Quando múltiplos componentes contribuem para um estado agregado, prevalece o estado de maior prioridade.

Essa regra deve permanecer centralizada e testável.

Templates não devem decidir precedência analítica.

---

# 32. Análise em lote

A análise em lote não deve ser uma simples lista de documentos processados.

Ela deve permitir identificar:

- padrões recorrentes;
- frequência de findings;
- prevalência;
- documentos prioritários;
- distribuição de status;
- diferenças entre documentos;
- achados dominantes no conjunto.

O lote possui duas perspectivas principais:

```text
A) por tipo de achado
B) por documento
```

---

# 33. BatchFindingAggregationService

`BatchFindingAggregationService` agrega findings provenientes das análises individuais.

A unidade principal de prevalência é:

> **documento afetado**

Isso significa:

```text
Documento A
10 ocorrências de ocultação
```

conta como:

```text
1 documento afetado
```

para cálculo de prevalência.

Entretanto, a quantidade total de ocorrências pode continuar sendo preservada separadamente.

Portanto:

```text
affected_documents
```

e:

```text
occurrence_count
```

representam conceitos diferentes.

Essa distinção é obrigatória.

---

# 34. Prevalência

A prevalência de um finding no lote é calculada por:

```text
documentos afetados
─────────────────── × 100
total de documentos
```

Exemplo:

```text
28 documentos afetados
30 documentos analisados
```

resulta em aproximadamente:

```text
93,33%
```

Um finding não precisa existir em 100% dos documentos para aparecer no panorama agregado.

A antiga lógica conceitual de unanimidade não deve ser utilizada como regra geral.

Exemplo correto:

```text
Ocultação visual
28 / 30 documentos
93,33%
```

O fato de dois documentos não apresentarem o finding não deve ocultar o padrão predominante.

---

# 35. Agrupamento por tipo de finding

O lote deve permitir visualizar findings por categoria.

Exemplo:

```text
Ocultação visual        28 / 30
Prompt Injection         3 / 30
Linha inconsistente     12 / 30
Barcode divergente       8 / 30
```

Cada summary pode preservar, conforme aplicável:

- código;
- título;
- documentos afetados;
- total de documentos;
- total de ocorrências;
- prevalência percentual;
- IDs dos documentos afetados;
- maior confiança observada.

---

# 36. Agregação genérica e especializada

O batch pode possuir fontes diferentes de findings.

A arquitetura atual permite:

- agregação genérica de evidências;
- agregação especializada de Prompt Injection;
- agregação especializada de ocultação visual.

Isso existe porque nem todos os módulos possuem exatamente a mesma representação interna.

No futuro, essa duplicação poderá motivar uma interface de finding mais uniforme.

Entretanto, não deve ser criada uma abstração prematura apenas para eliminar diferenças superficiais.

A prioridade é preservar:

- clareza;
- rastreabilidade;
- comportamento correto;
- testes.

---

# 37. Agrupamento por documento

Além da visão por finding, o lote apresenta os documentos de acordo com sua prioridade analítica.

Conceitualmente:

```text
Alta prioridade
Revisão recomendada
Sem apontamentos
Não executado
```

A ordenação segue:

```text
ALERT
ATTENTION
CLEAR
NOT_EXECUTED
```

Assim, documentos que demandam maior atenção aparecem primeiro.

---

# 38. Status analítico do lote

O lote não pode ser considerado "sem suspeitas" apenas porque o processamento foi concluído.

O status analítico agregado deve refletir os resultados dos documentos.

Se pelo menos um documento possui estado de maior prioridade, o lote deve refletir adequadamente essa necessidade de revisão.

Conceitualmente:

```text
Documento A → CLEAR
Documento B → ATTENTION
Documento C → ALERT
```

resultado agregado:

```text
Lote → ALERT
```

A regra deve seguir a mesma precedência:

```text
ALERT > ATTENTION > CLEAR > NOT_EXECUTED
```

---

# 39. UX da análise em lote

A UX do lote deve seguir os mesmos princípios da investigação individual:

- sobriedade;
- clareza;
- hierarquia;
- prioridade sem excesso visual;
- distinção entre execução e resultado analítico.

Achados relevantes devem chamar atenção, mas a interface não deve utilizar recursos excessivamente alarmistas.

O objetivo é apoiar o analista, não induzir conclusão.

---

# 40. Evidência visual e explicabilidade

Sempre que tecnicamente possível e útil, um finding deve permitir que o usuário compreenda:

```text
O que foi encontrado?
Por que foi apontado?
Onde está no documento?
Qual detector encontrou?
Qual a confiança?
Qual informação técnica sustenta o achado?
```

Isso é especialmente importante para:

- Prompt Injection;
- ocultação visual;
- linha digitável;
- comparação financeira;
- futuras anomalias tipográficas.

Explicabilidade não é uma camada opcional do DocDNA.

Ela faz parte da arquitetura.

---

# 41. Artefatos derivados

O sistema pode produzir artefatos derivados da análise, como:

- imagens renderizadas;
- páginas anotadas;
- regiões destacadas;
- arquivos temporários de extração.

Esses artefatos:

- não substituem o documento original;
- não alteram a evidência original;
- servem à apresentação e revisão;
- podem ser regeneráveis.

A arquitetura deve distinguir:

```text
evidência original
```

de:

```text
artefato derivado de visualização
```

---

# 42. Testes

Novas regras de domínio devem possuir testes.

A estratégia de desenvolvimento é:

```text
1. implementar regra
2. executar teste específico
3. executar testes da camada
4. executar suíte completa
5. somente então validar no Uvicorn
```

Testes devem existir especialmente para:

- detectores;
- validators;
- services;
- builders com regras observáveis;
- agregadores;
- resolvers;
- transformações relevantes de ViewModel.

Alterações puramente cosméticas podem não exigir testes automatizados próprios.

---

# 43. Testes de frontend

O frontend do DocDNA não é apenas HTML/CSS.

Builders e resolvers de apresentação possuem comportamento observável e, portanto, devem ser testados quando carregam regras.

Exemplos:

- prioridade dos cards;
- prioridade dos documentos;
- status analítico;
- labels;
- agregação;
- ordenação;
- transformação de dados.

A existência de testes de frontend não significa testar pixel a pixel a interface.

Significa testar a lógica que determina o que será apresentado.

---

# 44. Regra de alteração segura

Antes de alterar código existente:

1. consultar a árvore atual;
2. identificar os componentes envolvidos;
3. solicitar somente os arquivos necessários;
4. ler o código existente;
5. não presumir paths;
6. não presumir nomes de classes;
7. preservar responsabilidades existentes;
8. criar ou atualizar testes;
9. rodar teste específico;
10. rodar suíte completa;
11. validar no Uvicorn.

O código existente é a fonte da verdade.

Este documento descreve a arquitetura, mas não deve ser usado para inventar componentes que não existam no código atual.

---

# 45. Regra de arquivos completos

Durante o desenvolvimento assistido, sempre que possível, alterações devem ser fornecidas como arquivos completos.

Isso reduz:

- erro de posicionamento;
- erro de indentação;
- substituição incorreta;
- dificuldade para desenvolvedores em aprendizado.

Exceções são aceitáveis quando:

- o arquivo é muito grande;
- a alteração é extremamente localizada;
- substituir o arquivo inteiro aumenta o risco.

Nesses casos, deve ser informado claramente:

- caminho;
- trecho a localizar;
- trecho a substituir;
- novo conteúdo.

---

# 46. Responsabilidades por camada

## Detector

Responsável por identificar um sinal técnico específico.

Não deve:

- renderizar HTML;
- decidir UX;
- declarar fraude;
- persistir estado de interface.

## Service

Responsável por coordenar regras ou detectores relacionados.

Não deve se transformar em ViewModel.

## Builder de evidência

Responsável por transformar informação técnica em evidência derivada estruturada ou visual.

Não deve redetectar fatos já conhecidos sem necessidade.

## AnalysisContext

Responsável por consolidar resultados da análise.

Não deve executar regras de detecção.

## UseCase

Responsável por orquestrar o fluxo de aplicação.

## ViewBuilder

Responsável por preparar dados para apresentação.

Não deve implementar novos detectores.

## Resolver

Responsável por resolver estados derivados de regras claras e testáveis.

## Template

Responsável por apresentar.

Não deve decidir regra forense.

---

# 47. Processamento individual — fluxo de referência

Fluxo conceitual atual:

```text
Upload
  ↓
Arquivo salvo
  ↓
SHA-256
  ↓
Leitura estrutural do PDF
  ↓
Texto nativo
  ↓
OCR
  ↓
Documento normalizado
  ↓
Extração de imagens
  ↓
Fingerprints
  ↓
Barcode
  ↓
Linha digitável
  ↓
Validação
  ↓
Comparação barcode × linha
  ↓
Detectores textuais / visuais
  ↓
Prompt Injection
  ↓
Visual Concealment
  ↓
Localizações / evidências visuais
  ↓
AnalysisContext
  ↓
UseCase
  ↓
AnalysisViewBuilder
  ↓
InvestigationViewBuilder
  ↓
InvestigationStatus
  ↓
Template
  ↓
Usuário
```

A ordem exata de execução deve sempre ser confirmada no código atual antes de alterações estruturais.

Este diagrama representa responsabilidades e dependências conceituais.

---

# 48. Processamento em lote — fluxo de referência

Fluxo conceitual:

```text
N documentos
     ↓
análises individuais
     ↓
resultados estruturados
     ↓
┌──────────────────────────────┐
│ BatchFindingAggregationService
└──────────────────────────────┘
     ↓
findings agrupados
     ↓
documentos afetados
     ↓
ocorrências
     ↓
prevalência
     ↓
┌──────────────────────────────┐
│ status analítico por documento
└──────────────────────────────┘
     ↓
priorização
     ↓
status analítico do lote
     ↓
BatchViewBuilder
     ↓
Template
     ↓
Usuário
```

---

# 49. IA — arquitetura futura

A camada de IA não substituirá os detectores determinísticos.

Arquitetura planejada:

```text
Detectores determinísticos
          ↓
Evidências estruturadas
          ↓
Camada de IA
          ↓
Interpretação
Correlação
Priorização
          ↓
Revisão humana
```

A IA poderá atuar em tarefas como:

- interpretação contextual;
- correlação entre detectores;
- explicação para o analista;
- identificação de combinações incomuns;
- clusterização de documentos;
- comparação semântica;
- priorização;
- geração de hipóteses investigativas;
- auxílio à classificação.

A IA não deverá declarar fraude sem base evidencial.

---

# 50. Exemplo futuro de correlação por IA

Considere um lote:

```text
30 documentos

28 possuem texto oculto
26 usam fonte semelhante
25 possuem conteúdo semelhante
24 possuem ocorrência na mesma região
```

Detectores determinísticos produzem esses fatos.

A camada de IA poderá interpretar:

> existe um padrão recorrente entre diferentes documentos que merece investigação conjunta.

Ela não deverá transformar automaticamente essa correlação em:

> os 30 documentos são fraudulentos.

---

# 51. Score futuro

O DocDNA poderá futuramente possuir scores.

Possíveis níveis:

- score por evidência;
- score por categoria;
- score por documento;
- score do lote.

Scores não devem ser criados apenas pela soma arbitrária de findings.

A implementação futura deverá considerar:

- calibração;
- severidade;
- confiança;
- prevalência;
- correlação;
- independência entre detectores;
- explicabilidade.

O usuário deve conseguir compreender por que determinado score foi produzido.

---

# 52. Banco de dados — etapa futura

Persistência estruturada será implementada posteriormente.

Objetivos:

- histórico;
- reanálise;
- auditoria;
- comparação temporal;
- consultas;
- lotes persistidos;
- relatórios;
- rastreabilidade.

A introdução do banco não deve alterar as regras de domínio existentes.

Repositories deverão isolar persistência das demais camadas.

---

# 53. Processamento em escala

O objetivo futuro inclui lotes entre aproximadamente:

```text
1.000–5.000 documentos
```

O processamento atual não deve presumir que a arquitetura definitiva de filas já existe.

A evolução futura poderá incluir:

- processamento assíncrono;
- filas;
- workers;
- checkpoints;
- retomada;
- persistência de progresso;
- limites de concorrência;
- monitoramento;
- cancelamento;
- recuperação de falhas;
- dashboard de progresso.

Essas decisões devem ser implementadas quando a necessidade operacional justificar a complexidade.

---

# 54. Relatórios futuros

O sistema deverá futuramente permitir relatórios:

- PDF;
- HTML;
- XLSX;
- consolidados por lote;
- individuais.

Os relatórios deverão preservar:

- identidade do arquivo;
- SHA-256;
- findings;
- evidências;
- localização;
- status;
- prevalência;
- contexto suficiente para auditoria.

---

# 55. Próximas features técnicas

Após a estabilização da Fase 2 de UX e lote, o roadmap técnico inclui:

1. LowContrastTextDetector;
2. agregação de TextSpans adjacentes;
3. Font Anomaly Detector;
4. detecção off-canvas / posição anômala;
5. LogoFingerprint;
6. QRCodeFingerprint;
7. SignatureFingerprint;
8. comparação entre documentos;
9. detecção de elementos reutilizados;
10. ELA;
11. raster vs vetor;
12. análise forense avançada de fontes;
13. metadados ampliados.

A ordem pode ser ajustada conforme os resultados encontrados durante o desenvolvimento.

---

# 56. LowContrastTextDetector

Próxima feature planejada.

Objetivo conceitual:

detectar texto cuja cor possua contraste insuficiente em relação ao fundo ou contexto visual.

Essa feature deverá aproveitar a arquitetura existente de ocultação visual sempre que isso fizer sentido.

Antes da implementação devem ser avaliados:

- representação atual de cor;
- disponibilidade de informação de fundo;
- diferença entre cor clara e baixo contraste;
- falsos positivos;
- thresholds;
- relação com WhiteTextDetector;
- relação com TextConcealmentFinding;
- possibilidade de localização por BoundingBox nativo.

Não se deve assumir que todo texto de baixo contraste é oculto intencionalmente.

---

# 57. Agregação de TextSpans adjacentes

Feature futura planejada para reduzir fragmentação de achados.

Problema conceitual:

um trecho visualmente único pode estar representado internamente por vários `TextSpan`.

Sem agregação:

```text
"ignore"
"previous"
"instructions"
```

poderiam produzir três findings separados.

Com agregação adequada:

```text
"ignore previous instructions"
```

poderá ser tratado como uma unidade contextual.

A agregação deverá considerar cuidadosamente:

- mesma página;
- proximidade espacial;
- linha;
- fonte;
- tamanho;
- cor;
- direção;
- distância;
- ordem de leitura.

Não deve haver concatenação indiscriminada.

---

# 58. Font Anomaly Detector

Feature futura para identificar características tipográficas incomuns.

Possíveis sinais:

- fonte rara em relação ao restante do documento;
- mudança abrupta de fonte;
- tamanho discrepante;
- combinação tipográfica localizada;
- fonte presente em região específica;
- padrões recorrentes entre documentos.

O detector deverá produzir evidências objetivas.

Não deverá concluir adulteração apenas pela presença de uma fonte diferente.

---

# 59. Off-canvas / posição anômala

Feature futura para identificar elementos textuais posicionados fora ou próximos dos limites esperados da página.

Possíveis sinais:

- texto fora da área visível;
- bounding boxes anômalos;
- coordenadas negativas;
- regiões extremas;
- texto tecnicamente existente, mas não naturalmente visível.

A análise deverá distinguir:

- layout legítimo;
- problemas de geração de PDF;
- elementos técnicos;
- possíveis formas de ocultação.

---

# 60. Comparação entre documentos

Uma das etapas futuras mais importantes do DocDNA será a comparação de documentos de um mesmo lote.

O objetivo será identificar padrões como:

- imagens reutilizadas;
- logos idênticos;
- assinaturas repetidas;
- elementos gráficos repetidos;
- regiões visualmente idênticas;
- divergências em campos específicos;
- documentos quase idênticos com pequenas alterações;
- padrões de edição.

Essa camada deverá reutilizar fingerprints sempre que possível.

---

# 61. Elementos reutilizados

A detecção de elementos reutilizados deverá responder perguntas como:

```text
Esta assinatura aparece em quantos documentos?
Esta imagem de hidrômetro foi reutilizada?
Este logo é exatamente o mesmo?
Esta região gráfica aparece repetidamente?
```

Reutilização não significa automaticamente fraude.

Pode representar:

- template;
- logo legítimo;
- elemento institucional;
- assinatura digitalizada legítima;
- artefato recorrente.

A interpretação dependerá do tipo de elemento e do contexto.

---

# 62. ELA

Error Level Analysis permanece no roadmap.

ELA deverá ser tratada como técnica complementar.

Não deverá ser usada isoladamente para declarar manipulação.

Resultados de ELA deverão ser apresentados como evidência técnica, com explicação das limitações.

---

# 63. Raster × vetor

A análise futura deverá distinguir elementos rasterizados e vetoriais quando isso for tecnicamente útil.

Possíveis aplicações:

- identificar sobreposições;
- comparar composição;
- analisar regiões alteradas;
- entender a estrutura gráfica do PDF.

Assim como outras técnicas, raster/vetor não deve produzir conclusão isolada de fraude.

---

# 64. Metadados ampliados

A análise de metadados poderá futuramente incluir:

- inconsistências temporais;
- ferramentas produtoras;
- histórico estrutural disponível;
- objetos internos;
- fontes incorporadas;
- imagens;
- informações EXIF quando existentes;
- padrões entre documentos.

Metadados devem ser tratados como sinais.

Ausência ou diferença de metadados não equivale automaticamente a fraude.

---

# 65. Refatoração contínua

O DocDNA utiliza desenvolvimento incremental.

Após conjuntos relevantes de features:

1. revisar responsabilidades;
2. identificar duplicações;
3. avaliar abstrações;
4. atualizar testes;
5. atualizar este documento.

Refatoração não deve ser usada para introduzir abstrações sem necessidade comprovada.

A regra é:

> primeiro compreender padrões concretos; depois abstrair.

---

# 66. Backlog arquitetural

Itens atualmente relevantes para avaliação futura:

## Fingerprint Visual

Avaliar conceito comum para:

- ImageFingerprint;
- LogoFingerprint;
- QRCodeFingerprint;
- SignatureFingerprint.

## Finding genérico

Avaliar se diferentes findings podem compartilhar uma interface mínima para:

- code;
- detector;
- confidence;
- localização;
- categoria.

Não implementar apenas para reduzir linhas de código.

## Agregação batch

Avaliar progressivamente se novos tipos de findings podem utilizar o agregador genérico sem adapters especializados.

## AnalysisViewBuilder

Monitorar crescimento da classe.

Caso continue aumentando, avaliar divisão por domínios de apresentação, por exemplo:

```text
FinancialViewBuilder
PromptInjectionViewBuilder
ConcealmentViewBuilder
DocumentStructureViewBuilder
```

Essa divisão somente deve ocorrer quando reduzir complexidade real.

---

# 67. Dívida técnica observável

O crescimento do `AnalysisViewBuilder` deve ser acompanhado.

Um builder muito grande pode indicar que múltiplos contextos de apresentação estão sendo concentrados na mesma classe.

Entretanto, a refatoração não deve ser realizada apenas pelo tamanho do arquivo.

Critérios melhores:

- dificuldade de teste;
- conflitos frequentes;
- responsabilidades claramente independentes;
- mudanças em um módulo afetando outro;
- duplicação;
- baixa coesão.

---

# 68. Princípios para novas features

Toda nova feature deve responder:

```text
1. Qual fato técnico ela detecta?
2. Qual é o modelo desse fato?
3. Qual é a evidência?
4. Como ela entra no AnalysisContext?
5. Como chega ao usuário?
6. Ela participa do batch?
7. Como é agregada?
8. Qual status pode produzir?
9. Como será testada?
10. Qual é o risco de falso positivo?
```

Se essas perguntas não estiverem claras, a feature ainda não está arquiteturalmente pronta.

---

# 69. Filosofia de confiança

DocDNA não é um "oráculo de fraude".

É uma plataforma de apoio à investigação documental.

O sistema deve favorecer:

- evidência;
- transparência;
- rastreabilidade;
- explicabilidade;
- comparação;
- priorização;
- revisão humana.

O sistema deve evitar:

- conclusões absolutas sem fundamento;
- scores opacos;
- regras mágicas;
- dependência exclusiva de IA;
- alarmismo visual;
- mistura entre ausência de achado e autenticidade.

---

# 70. Regra de ausência de achados

Uma regra fundamental de comunicação é:

> ausência de alerta não equivale a autenticidade comprovada.

`CLEAR` significa apenas que, considerando os verificadores executados e os dados disponíveis, não foram encontrados sinais suficientes para elevar a prioridade analítica.

A interface e os relatórios devem preservar essa distinção.

---

# 71. Regra de evidência combinada

Um sinal isolado pode possuir baixo valor investigativo.

Múltiplos sinais independentes podem aumentar a relevância de revisão.

Exemplo:

```text
texto quase branco
+
fonte muito pequena
+
conteúdo instrucional
+
posição incomum
```

pode ser mais relevante do que qualquer sinal isolado.

Essa correlação deverá ser tratada cuidadosamente.

Detectores continuam independentes.

A correlação pertence a services, resolvers ou à futura camada de interpretação.

---

# 72. Regra de prevalência em lote

Prevalência mede distribuição.

Ela não mede, isoladamente, gravidade.

Exemplo:

```text
Finding A → 95% dos documentos
Finding B → 3% dos documentos
```

não significa necessariamente que `Finding A` seja mais grave.

Pode significar apenas que é mais frequente.

Portanto:

```text
frequência
≠
severidade
≠
confiança
≠
fraude
```

Esses conceitos devem permanecer separados.

---

# 73. Regra de ocorrência

Da mesma forma:

```text
100 ocorrências
```

não significa automaticamente:

```text
100 documentos afetados
```

O batch deve preservar ambas as dimensões quando forem úteis:

```text
occurrence_count
affected_documents
```

Isso é essencial para análise correta de lotes.

---

# 74. Regra de localização

Localização é uma dimensão de explicabilidade.

Sempre que uma posição nativa confiável já existir, ela deve ser preferida a uma nova tentativa de localização.

Ordem conceitual de preferência:

```text
coordenada nativa confiável
        ↓
matching estrutural confiável
        ↓
matching textual
        ↓
OCR / aproximação
```

A técnica concreta depende do tipo de evidência.

A regra geral é evitar reconstruir informação que já foi preservada de forma mais precisa.

---

# 75. Regra de origem

Sempre que possível, evidências devem preservar sua origem.

Exemplos:

```text
native_text
ocr
normalized_document
barcode
visual
metadata
```

A origem é importante para:

- explicabilidade;
- debugging;
- comparação;
- confiança;
- futuras correlações;
- auditoria.

---

# 76. Regra de confiança

`confidence` representa confiança técnica de um detector ou procedimento.

Ela não representa probabilidade matemática de fraude, salvo se futuramente existir um modelo explicitamente calibrado para isso.

Portanto:

```text
confidence = 0.95
```

não deve ser apresentado automaticamente como:

```text
95% de chance de fraude
```

Essa distinção deve ser preservada em toda a aplicação.

---

# 77. Estado atual da Fase 2

A Fase 2 iniciou com foco em:

```text
UX + análise em lote
```

Os principais problemas tratados foram:

- findings individuais que não refletiam corretamente no lote;
- resumo agregado excessivamente dependente de unanimidade;
- ausência de prevalência por documento;
- necessidade de agrupamento por finding;
- necessidade de agrupamento por documento;
- distinção entre status operacional e analítico;
- priorização visual;
- ordenação de cards e documentos.

O estado atual já contempla:

- agregação por frequência;
- prevalência percentual;
- documentos afetados;
- contagem de ocorrências;
- agrupamento por finding;
- status analítico;
- priorização de documentos;
- ordenação da investigação individual;
- UX sóbria para prioridade;
- testes específicos dessa camada.

---

# 78. Checkpoint arquitetural da Fase 2

Este documento representa o checkpoint realizado após a estabilização do primeiro grande bloco da Fase 2.

A arquitetura atual passa a reconhecer explicitamente três dimensões diferentes:

```text
1. PROCESSAMENTO
   O sistema conseguiu executar?

2. ANÁLISE
   O que os detectores encontraram?

3. PRIORIZAÇÃO
   O que merece revisão primeiro?
```

Essas dimensões não devem ser fundidas.

---

# 79. Direção imediata

Após este checkpoint, a próxima sequência recomendada é:

```text
LowContrastTextDetector
        ↓
agregação de TextSpans adjacentes
        ↓
Font Anomaly Detector
        ↓
off-canvas / posição anômala
```

Essas features completam progressivamente a camada de análise textual/visual antes da expansão dos fingerprints especializados.

---

# 80. Critério de conclusão de uma feature

Uma feature é considerada concluída quando:

- a regra técnica está implementada;
- os modelos necessários existem;
- o fluxo está integrado;
- os testes específicos passam;
- a suíte completa permanece verde;
- a informação relevante chega ao usuário;
- o comportamento foi validado no Uvicorn quando aplicável;
- a documentação é atualizada quando a mudança é arquiteturalmente relevante.

---

# 81. Fonte da verdade

A fonte da verdade do DocDNA é:

> **o código atual do projeto.**

Este documento existe para registrar:

- arquitetura;
- decisões;
- princípios;
- responsabilidades;
- direção técnica.

Se houver divergência entre este documento e o código:

1. consultar o código;
2. verificar se houve mudança arquitetural não documentada;
3. corrigir a documentação ou o código conforme a intenção real;
4. não presumir automaticamente que este arquivo está correto.

---

# 82. Resumo arquitetural

O DocDNA deve continuar evoluindo segundo esta cadeia:

```text
DOCUMENTO
   ↓
EXTRAÇÃO
   ↓
NORMALIZAÇÃO
   ↓
DETECTORES DETERMINÍSTICOS
   ↓
FINDINGS / EVIDÊNCIAS
   ↓
LOCALIZAÇÕES
   ↓
ANALYSIS CONTEXT
   ↓
USE CASES
   ↓
VIEW MODELS
   ↓
INVESTIGAÇÃO / BATCH
   ↓
PRIORIZAÇÃO
   ↓
REVISÃO HUMANA
```

No futuro:

```text
FINDINGS / EVIDÊNCIAS
          ↓
     CAMADA DE IA
          ↓
INTERPRETAÇÃO / CORRELAÇÃO
          ↓
      PRIORIZAÇÃO
          ↓
     REVISÃO HUMANA
```

A IA complementará a arquitetura.

Ela não substituirá as evidências determinísticas.

---

# 83. Princípio final

O DocDNA deve ser capaz de responder não apenas:

> "Há algo incomum neste documento?"

mas também:

> "O que foi encontrado?"

> "Qual componente encontrou?"

> "Por que isso foi considerado relevante?"

> "Onde isso está no documento?"

> "Quantos documentos do lote apresentam o mesmo padrão?"

> "Qual é a prevalência?"

> "Quais documentos devem ser revisados primeiro?"

E, principalmente:

> **"Quais evidências sustentam essa priorização?"**

Essa é a base arquitetural do projeto.