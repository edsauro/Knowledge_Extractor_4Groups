# Knowledge Extractor — MVP Architecture Study

> **Context / entrega:** este arquivo É o estudo pedido. Ao aprovar, a única ação de
> implementação é copiá-lo para `docs/architecture/MVP-ARCHITECTURE-STUDY.md`.
> Nenhum código do MVP será escrito nesta etapa.

---

## 0. Evidência: o que os dados reais dizem

Antes de opinar, medi o único export real disponível
(`samples/private/DOC-20261009-WA0011.zip` → "Conversa do WhatsApp com RAG.txt"):

| Métrica | Valor |
|---|---|
| Tamanho | 1,17 MB (~330k tokens) |
| Período | 10/10/2025 → 09/10/2026 (**1 ano de 1 grupo**) |
| Linhas de mensagem | 6.328 |
| Linhas com URL | 1.103 |
| URLs totais | 1.118 |
| URLs GitHub | 162 (**126 repos únicos**) |
| `<Mídia oculta>` | 978 (export **sem mídia**) |
| Anexos reais no zip | 1 (`.vcf`) |
| Autores com nome | **20**; todo o resto é número de telefone |
| Autor mais ativo | `Prof. Sandeco` (576 msgs, 9%) |

**Cinco consequências que mudam a arquitetura inteira:**

1. **Um ano inteiro de grupo cabe em uma leitura de ~330k tokens.** No DeepSeek Flash
   off-peak (US$0,15/1M input miss, US$0,60/1M output) uma passagem completa custa
   **~US$0,05–0,09**. Qualquer infraestrutura construída para "economizar tokens"
   custa mais em tempo de desenvolvimento do que economizará em dólares durante anos.
2. **O sinal é raríssimo e trivialmente localizável:** 126 repos úteis em 6.328
   mensagens (~2%). Um `grep` de URL já elimina 83% do volume antes de qualquer LLM.
3. **A mídia não veio no export.** Todo o subsistema de anexos/PDF/hash de arquivo do
   `TECHNICAL-SPEC`/`PRD` é, no formato de export realmente usado, **código morto no MVP**.
   DocumentFamily/versões de livros só existe se o usuário colocar os PDFs à mão.
4. **Identidade é o gargalo real, não reputação.** 90% dos autores são números de
   telefone. Nenhum "observed_reliability por domínio" é computável sobre
   `+55 62 90000-0000`. O que falta é um mapa `telefone → pessoa`, feito à mão, com ~15 linhas.
5. **Reply-to não existe no formato.** O export é texto plano linha-a-linha, sem IDs,
   sem citações estruturadas. Threading determinístico é **impossível** por construção;
   só sobra janela temporal + LLM.

---

## 1. Executive conclusion

**Recomendação: construa um script Python de ~200–300 linhas que faz um vertical slice
completo, e nada mais. Sem SQLite, sem grafo, sem state machine, sem Hermes, sem CLI
sofisticada, sem schemas de 18 entidades.**

O pipeline recomendado:

```
raw/<grupo>/<export>.txt
   ↓  parser regex de 30 linhas (data, autor, texto)
   ↓  filtro: mensagens com URL + janela de ±5 mensagens de contexto
   ↓  agrupamento em blocos de ~20k tokens
   ↓  DeepSeek Flash, 1 prompt, saída JSON (schema de 8 campos)
   ↓  merge por URL normalizada (dedup = dicionário Python)
   ↓  vault/resources/<slug>.md  (um arquivo por recurso, frontmatter YAML)
```

Custo operacional por grupo-ano: **menos de US$0,10**. Esforço: **LOW**.
Resultado: ~126 fichas de recursos com capabilities, fonte e contexto — que é
exatamente o produto descrito no item 2 do briefing.

**Diagnóstico direto da documentação atual: há overengineering substancial.** O PRD
define 18 entidades, 6 estados de ciclo de vida de arquivo, RBAC com 4 roles, state
machine com estados de falha, cost accounting, quota snapshots e 10 ADRs — para um
sistema cujo output inicial são ~126 arquivos Markdown. Estimo que **~70% do que está
especificado em `PRD.md` + `ARCHITECTURE.md` + `TECHNICAL-SPEC.md` não deve ser
construído agora**, e uma parte relevante nunca precisará ser construída.

Isso não significa que a documentação está errada como *visão*. Significa que ela
descreve o **Perfect System** (seção 4) e o está apresentando como M0.

---

## 2. Restatement of the actual problem

**O que realmente estamos resolvendo:**

> "Participo de grupos técnicos de alto volume. Pessoas competentes compartilham
> ferramentas boas. Eu não consigo ler tudo e perco as recomendações. Quero uma
> biblioteca pesquisável de *recursos recomendados* — principalmente repositórios
> GitHub — com o que fazem e por que alguém os indicou."

**O que NÃO estamos resolvendo:**

- não é um arquivo fiel da conversa;
- não é um sistema de memória de grupo;
- não é um produto multiusuário;
- não é auditoria regulatória;
- não é busca semântica sobre mensagens.

**Unidade de valor:** uma ficha de recurso. Não uma mensagem, não uma thread.
Tudo o que não produz nem melhora uma ficha de recurso é, por definição, overhead.

**Critério de sucesso honesto do MVP:** rodar sobre este export e obter uma pasta de
fichas em que o usuário, lendo-as, diga "isto eu teria perdido" pelo menos ~10 vezes.

---

## 3. Minimum MVP (Arquitetura A)

### Fluxo

```
┌──────────────────────┐
│ raw/rag-group.txt    │  (colocado à mão)
└──────────┬───────────┘
           │
      parse.py          regex: ^(\d{2}/\d{2}/\d{4}) (\d{2}:\d{2}) - ([^:]+): (.*)$
           │            continuação = linha que não casa → append na anterior
           ▼
   list[Message]  (date, author, text)
           │
      filter: tem URL?  → mantém msg + 5 antes + 5 depois
           ▼
   ~1.100 mensagens-âncora + contexto (~25% do volume)
           │
      chunk em blocos de ~20k tokens, respeitando fronteira de mensagem
           ▼
   DeepSeek Flash × ~12 chamadas, prompt único, response_format=json_object
           ▼
   list[Resource]  JSON
           │
      merge por URL normalizada (dict), concatena contextos/fontes
           ▼
   render Jinja/f-string → vault/resources/<slug>.md
```

### Componentes (são 4, não 18)

| # | Componente | Tamanho estimado |
|---|---|---|
| 1 | `parse.py` — export WhatsApp → lista de dicts | ~40 linhas |
| 2 | `select.py` — filtro de URL + janela de contexto + chunking | ~50 linhas |
| 3 | `extract.py` — chamada DeepSeek + prompt + validação JSON | ~80 linhas |
| 4 | `publish.py` — merge por URL + render Markdown | ~70 linhas |
| | `run.py` encadeando os quatro | ~20 linhas |

Mais um `prompts/extract.md` e um `contacts.yaml` com 15 linhas de `telefone: nome`.

### Schema de saída (8 campos — resista a ampliar)

```json
{
  "name": "LightRAG",
  "url": "https://github.com/HKUDS/LightRAG",
  "kind": "github_repo",
  "what_it_does": "RAG com indexação em grafo de conhecimento",
  "capabilities": ["graph-based retrieval", "incremental indexing"],
  "mentioned_by": ["+55 85 90000-0000"],
  "context": "Perguntado se alguém usa; comparado a RAGFlow e RAGLight",
  "confidence": "high"
}
```

### O que explicitamente NÃO entra no MVP

| Candidato | Veredito | Razão |
|---|---|---|
| SQLite | **não** | 126 registros. Um `dict` resolve. |
| Graph | **não** | Zero queries de grafo foram formuladas até hoje. |
| State machine | **não** | 4 funções em sequência; o estado é "o script terminou ou não". |
| Workers/paralelismo | **não** | 12 chamadas de API; serial leva ~2 min. |
| CLI sofisticada | **não** | `python run.py raw/arquivo.txt`. |
| Banco relacional | **não** | — |
| Schemas complexos / Pydantic de 18 entidades | **não** | 1 schema de 8 campos. |
| Threading próprio | **não** | Impossível no formato (sem reply-to) e desnecessário. |
| Hermes | **não** | Orquestrar um script de 1 passo é custo puro. |
| Cost accounting | **não** | O custo é US$0,07. Olhe o dashboard da DeepSeek uma vez por mês. |
| Dedup de mensagens | **não** | Dedup é por URL, no fim. Reprocessar é barato. |
| Retention policy engine | **não** | Os RAW são arquivos `.txt` de 1 MB. Não há pressão de espaço. |

**Esforço total: LOW.** (uma sessão de trabalho focada com o Codex)

---

## 4. Perfect System (Arquitetura B) — o limite superior

Apenas para estabelecer a fronteira. **Não construir.**

```
┌─ Connectors ──────────────────────────────────────────────┐
│ WhatsApp export · Telegram API · RSS · email · drop folder│
└───────────────┬───────────────────────────────────────────┘
                ▼
┌─ Ingest ──────────────────────────────────────────────────┐
│ parsers determinísticos por formato · content hash (sha256)│
│ import manifest · idempotência por (source, hash)          │
└───────────────┬───────────────────────────────────────────┘
                ▼
┌─ Store: PostgreSQL ───────────────────────────────────────┐
│ messages · contacts · attachments · imports · resources    │
│ edges · evidence · review_items · usage_records            │
│ pgvector para similaridade semântica                       │
└───────────────┬───────────────────────────────────────────┘
                ▼
┌─ Processing (incremental, só o delta) ────────────────────┐
│ threading: embeddings + janela temporal + menções + LLM    │
│ triagem de relevância: classificador barato antes do caro  │
│ extraction: model routing por dificuldade/custo            │
│ enrichment: fetch do README do GitHub, stars, linguagem,   │
│   licença, última release → capabilities de alta qualidade │
│ dedup semântico: embedding + LLM arbitration               │
│ entity resolution: alias de contatos entre grupos          │
└───────────────┬───────────────────────────────────────────┘
                ▼
┌─ Quality ─────────────────────────────────────────────────┐
│ LLM-as-judge sobre amostra · golden set de regressão       │
│ confidence gating → review queue · prompt versioning       │
└───────────────┬───────────────────────────────────────────┘
                ▼
┌─ Publish ─────────────────────────────────────────────────┐
│ Obsidian vault gerado · wikilinks bidirecionais            │
│ índices por capability/domínio/fonte · diff antes de escrever│
└───────────────┬───────────────────────────────────────────┘
                ▼
┌─ Orchestration (Hermes) ──────────────────────────────────┐
│ workflow engine com state machine · retry/backoff          │
│ scheduling · notificações · cost accounting por job        │
│ observabilidade (traces, métricas, dashboards)             │
│ retention policy engine + deletion approval workflow       │
└───────────────────────────────────────────────────────────┘
```

Peças que **só** o Perfect System justifica: Postgres+pgvector, dedup semântico por
embedding, entity resolution cross-grupo, model routing dinâmico, LLM-as-judge
automático, workflow engine, RBAC, versionamento de prompts, cost accounting granular,
audit log, graph DB dedicado.

Esforço: **HIGH** (ordem de grandeza: 20–50× o MVP).

**Observação crítica:** mesmo o Perfect System **não** precisa de Neo4j nem de RBAC.
Ambos aparecem na documentação atual sem um caso de uso que os force. RBAC com 4 roles
em um sistema de usuário único é cerimônia.

---

## 5. Optimal / Pragmatic System (Arquitetura C) — **a recomendação**

O ponto ótimo é **MVP + 4 adições**, cada uma justificada por uma dor que os dados
reais já demonstram.

```
raw/<grupo>/<data>.txt
   ↓
[1] parse (regex)                                      ← CODE
   ↓
[2] filtro URL + janela de contexto                    ← CODE
   ↓
[3] extração de URLs + normalização + classificação    ← CODE   ★ADIÇÃO 1
       github.com/owner/repo → canônico, minúsculo, sem tracking params
   ↓
[4] skip de URLs já conhecidas (lê o vault existente)  ← CODE   ★ADIÇÃO 2
   ↓
[5] chunk + DeepSeek Flash → JSON                      ← LLM
   ↓
[6] enrichment do GitHub API (descrição, topics,       ← CODE   ★ADIÇÃO 3
       stars, linguagem) para os repos novos
   ↓
[7] merge por URL + resolução de nome via contacts.yaml← CODE   ★ADIÇÃO 4
   ↓
[8] escrita idempotente no vault (preserva edições     ← CODE
       humanas abaixo de um marcador `<!-- /auto -->`)
   ↓
vault/resources/*.md  +  vault/_index.md
```

### Por que exatamente estas 4 adições

| Adição | Dor concreta observada | Valor |
|---|---|---|
| **1. Normalização de URL** | 162 URLs GitHub → 126 únicas; há `?tab=readme`, barras finais, maiúsculas. Sem normalização, duplicatas sujas. | Alto, custo quase zero |
| **2. Skip de conhecidos** | Exports do WhatsApp **repetem todo o histórico**. Sem isso, cada reexport reprocessa 1 ano. | Alto — é o verdadeiro "incremental processing", e custa 10 linhas |
| **3. GitHub API enrichment** | O README do repo descreve capabilities melhor do que qualquer mensagem de WhatsApp. É a maior alavanca de **qualidade** do sistema inteiro. | **Muito alto** |
| **4. `contacts.yaml`** | 90% dos autores são telefones; sem o mapa, "Source" é inútil. | Alto, custo ~15 linhas de YAML |

Note que **nenhuma** das 4 é SQLite, grafo, state machine ou orquestração. Todas são
código determinístico simples. O vault de Markdown continua sendo o banco.

**Adição 3 merece destaque:** é a inversão mais importante deste estudo. O instinto é
investir em entender melhor a *conversa*. Mas a conversa diz apenas *que* algo foi
recomendado e *por quê*; o README diz *o que a coisa faz*. Separe as duas fontes:
LLM extrai recomendação+contexto da conversa, GitHub API fornece capabilities.
Isso melhora drasticamente a qualidade e **reduz** a dependência do LLM.

**Esforço: LOW–MEDIUM.**

---

## 6. MVP vs Optimal vs Perfect

| Dimensão | A — Minimum MVP | C — **Optimal** | B — Perfect |
|---|---|---|---|
| Linhas de código | ~250 | ~500–700 | 10.000+ |
| Esforço de desenvolvimento | LOW | LOW–MEDIUM | HIGH |
| Armazenamento | Markdown | Markdown (+JSONL de cache) | PostgreSQL + pgvector + Obsidian |
| Processamento incremental | não (reprocessa, é barato) | sim (skip por URL) | sim (delta por hash) |
| Dedup | por URL exata | URL normalizada | semântico |
| Threading | janela fixa de ±5 | janela fixa de ±5 | embeddings + LLM |
| Qualidade das capabilities | média (só conversa) | **alta (README)** | muito alta (README + judge) |
| Identificação de fonte | telefone cru | `contacts.yaml` | entity resolution |
| Custo por grupo-ano | ~US$0,07 | ~US$0,05 (filtra mais) | ~US$0,30 |
| Revisão humana | ler o vault | ler o vault | fila de exceções |
| Fontes suportadas | WhatsApp | WhatsApp (+Telegram trivial) | n fontes |
| Observabilidade | `print()` | `print()` + log JSONL | traces + dashboards |
| Tempo até o primeiro valor | horas | ~1–2 dias | meses |
| Risco de nunca terminar | ~0 | baixo | **alto** |

---

## 7. Code vs LLM matrix

Legenda de esforço/custo/risco: VERY LOW / LOW / MEDIUM / HIGH.

| # | Task | MVP approach | Ideal approach | **Recommended** | Why | Dev effort | Runtime cost | Error risk |
|---|---|---|---|---|---|---|---|---|
| 1 | Leitura do export | CODE (regex) | CODE (parser por locale/formato) | **CODE** | Formato é rigidamente regular; LLM aqui é desperdício puro | VERY LOW | zero | LOW |
| 2 | Identificação de mensagens (multi-linha) | CODE | CODE | **CODE** | "linha que não casa o timestamp = continuação" acerta ~100% | VERY LOW | zero | LOW |
| 3 | Identificação de URLs | CODE (regex) | CODE + unfurl de encurtadores | **CODE** | 100% determinístico | VERY LOW | zero | LOW |
| 4 | Identificação de repos GitHub | CODE (regex) | CODE + API validation | **CODE + API** | `github.com/owner/repo` é trivialmente parseável; a API confirma existência | VERY LOW | zero | LOW |
| 5 | Deduplicação (recursos) | CODE (dict por URL) | CODE + embedding semântico | **CODE (URL normalizada)** | Mesmo repo = mesma URL em ~98% dos casos | VERY LOW | zero | LOW |
| 6 | Deduplicação (mensagens em reexport) | nenhuma / reprocessa | hash por mensagem em DB | **CODE: skip de URL já no vault** | Resolve o problema real (custo) sem DB | VERY LOW | zero | LOW |
| 7 | Reconstruction / context | LLM (janela ±5) | embeddings + LLM | **LLM com janela ±5–10** | Ver §7.1 abaixo | VERY LOW | LOW | MEDIUM |
| 8 | Threading | **nenhum** | grafo temporal + semântico | **nenhum — janela fixa** | Ver §7.1. Não construir | zero | zero | MEDIUM (aceitável) |
| 9 | Technical relevance | LLM | classificador barato + LLM | **CODE (tem URL?) + LLM** | O filtro de URL já faz 80% do trabalho de graça | VERY LOW | LOW | MEDIUM |
| 10 | Capability extraction | LLM sobre a conversa | README + LLM + judge | **HYBRID: README via API + LLM** | ★ maior alavanca de qualidade do projeto | LOW | LOW | LOW |
| 11 | Resource description | LLM | API metadata + LLM | **HYBRID (API primeiro)** | `description` e `topics` do GitHub são melhores e grátis | LOW | VERY LOW | LOW |
| 12 | Source identification | CODE (string do autor) | entity resolution | **CODE + `contacts.yaml` manual** | 20 nomes; o resto é telefone. YAML de 15 linhas | VERY LOW | zero | LOW |
| 13 | Source reputation | **nenhuma** | observed reliability bayesiana | **tag manual por pessoa** (§11) | Dados insuficientes para estatística; e o julgamento é seu | VERY LOW | zero | LOW |
| 14 | File version detection | **nenhuma** | família + hash + diff + LLM | **nenhuma no MVP** → depois: `nome + sha256` | O export nem traz mídia (978 `<Mídia oculta>`) | zero | zero | LOW |
| 15 | Obsidian output | CODE (template) | CODE + diff + wikilinks | **CODE (template + bloco auto/manual)** | Geração de texto estruturado é trabalho de código | VERY LOW | zero | LOW |
| 16 | Retenção | **manual** (`rm`) | policy engine + aprovação | **script `kb-gc` que lista e pergunta** (§10) | Risco baixíssimo, 1 MB/ano | VERY LOW | zero | LOW |
| 17 | Limpeza / garbage | revisão humana do vault | confidence gating automático | **campo `confidence` + revisão humana** | Olho humano sobre 126 fichas é rápido e insubstituível | VERY LOW | zero | LOW |

### 7.1 Threading — avaliação explícita (pedido do item 4)

**Pergunta:** quanto do problema de reconstrução de contexto precisamos realmente resolver?

**Resposta: praticamente nada, e a evidência é estrutural, não otimista.**

1. O export **não tem reply-to**. Threading determinístico é impossível. Qualquer
   solução seria heurística — ou seja, um LLM com passos extras.
2. A unidade de valor é a *ficha de recurso*, não a thread. Para preencher
   `context` basta saber o que se discutia **em torno** do link. Veja o trecho real:
   uma pergunta ("Alguém conhece essa ferramenta?"), o link, e duas mensagens depois a
   resposta mencionando RAGFlow e RAGLight. Tudo dentro de ±3 mensagens.
3. O erro de intercalação é **autolimitado**: se um LLM lê uma janela com duas
   conversas misturadas, ele atribui contexto errado a *um* recurso, não corrompe
   nada. O custo do erro é uma ficha com uma frase imprecisa — perfeitamente aceitável
   segundo o item 13 do briefing.
4. Janela maior é mais barata que lógica melhor. Ampliar de ±5 para ±15 mensagens
   custa 3× os tokens de um sistema que custa US$0,07. Construir threading custa dias.

**Veredito: dê ao LLM uma janela generosa e pare por aí. Economia de ~80–90% do esforço
de threading, perdendo talvez 10% de precisão de contexto.** Se ao revisar o output
você vir fichas com contexto visivelmente errado, a primeira correção é **aumentar a
janela**, não construir threading.

---

## 8. Pareto 80/20

### Os ~20% que entregam ~80% do valor

| Componente | % do valor (estimativa) | Esforço |
|---|---|---|
| **Extração + normalização de URL GitHub** | ~35% | VERY LOW |
| **Enrichment via GitHub API (README/topics/descrição)** | ~25% | LOW |
| **Uma boa chamada de LLM com janela de contexto** | ~20% | LOW |
| **Template Markdown + merge por URL** | ~10% | VERY LOW |
| Soma | **~90%** | **LOW** |

Os outros ~10% do valor estão espalhados por todo o resto da especificação atual —
e custariam 20–50× mais.

**Onde está a alavanca escondida:** o prompt. A diferença entre um prompt medíocre e um
bom prompt vale mais do que SQLite, grafo e state machine somados. Invista aí o tempo
que seria gasto em infraestrutura.

### Parece sofisticado, agrega pouco (com análise de custo-benefício)

| Funcionalidade | Veredito | Análise |
|---|---|---|
| **Graph database** | **não construir** | Nenhuma query de grafo foi articulada até agora. "Que ferramentas de browser automation o Sandeco recomendou?" é `grep` em 126 arquivos. Grafo só vale com milhares de entidades e perguntas multi-hop reais. Custo: HIGH. Benefício atual: ~0. |
| **Complex source scoring** | **não construir** | Impossível: 90% dos autores são telefones anônimos. E a amostra por pessoa/domínio é pequena demais para estatística. Uma tag manual carrega quase toda a informação. |
| **Reconstrução perfeita de threads** | **não construir** | §7.1. Impossível pelo formato, desnecessário pelo objetivo. |
| **Sophisticated workflow engine** | **não construir** | Orquestrar 4 funções sequenciais. O "workflow engine" chama-se `def main()`. Reavaliar só com múltiplas fontes + agendamento + falhas parciais reais. |
| **Preservação completa de RAW** | **parcialmente — e é barato** | 1 MB/ano comprime para ~300 KB. O custo de guardar *tudo* por anos é desprezível; o custo de construir um policy engine de retenção não é. **Guarde tudo e não construa nada.** Inverte a premissa do PRD — para melhor. |
| **Document version detection** | **adiar** | O export não traz os arquivos. Quando trouxer: `nome + sha256 + data` resolve ~90%. |
| **Granular audit logs** | **não construir** | Um `run.jsonl` com uma linha por execução (data, arquivo, nº de recursos, custo) cobre tudo que você vai realmente querer saber. |
| **Cost accounting / quota snapshots** | **não construir** | Rastrear US$0,07 com rigor contábil custa mais que o próprio gasto. |
| **RBAC com 4 roles** | **não construir** | Sistema local de usuário único. Cerimônia pura. |
| **State machine com FAILED_RETRYABLE / WAITING_HUMAN** | **não construir** | A recuperação de falha é: rode o script de novo. É barato e idempotente. |

---

## 9. Storage comparison

| Critério | 1. Só Markdown | 2. JSONL + MD | 3. SQLite + MD | 4. SQLite + Obsidian + graph | **5. MD + cache JSONL (recomendada)** |
|---|---|---|---|---|---|
| Simplicidade | ★★★★★ | ★★★★ | ★★★ | ★ | ★★★★★ |
| Esforço de desenvolvimento | VERY LOW | LOW | MEDIUM | HIGH | VERY LOW |
| Busca (126–2.000 itens) | `grep`/Obsidian: ótimo | idem | SQL: melhor em escala | melhor | ótimo |
| Deduplicação | ler frontmatter | trivial | trivial | trivial | trivial |
| Processamento incremental | ler vault no início | fácil | fácil | fácil | fácil |
| Edição humana | ★★★★★ | ★★★★★ | risco de conflito MD↔DB | risco alto | ★★★★★ |
| Migração futura | fácil (MD → qualquer coisa) | fácil | — | difícil | fácil |
| Risco de dessincronização | nenhum | baixo | **real** | **alto** | baixo |

### Recomendação: **opção 5**

- **`vault/resources/*.md` é o banco de dados.** Fonte única de verdade, legível,
  editável, versionável, imune a corrupção de schema.
- **`.cache/seen_urls.jsonl`** (append-only): URLs já processadas. Serve só para pular
  trabalho; se for apagado, o sistema reconstrói a partir do vault.
- **`.cache/runs.jsonl`**: uma linha por execução. Esse é o "observability stack".

**O argumento decisivo contra SQLite+Markdown agora:** manter duas fontes de verdade
sincronizadas é a principal fonte de bugs em sistemas deste tipo, e você quer **editar
as fichas à mão** (o briefing aceita revisão humana). Com SQLite, cada edição manual no
Markdown é uma divergência. Com Markdown puro, é simplesmente o estado correto.

**Obsidian é interface, não banco** (resposta direta à pergunta 5 do item 18). Nunca
escreva código que dependa de recursos do Obsidian. Escreva Markdown com frontmatter
YAML; o Obsidian é apenas um visualizador agradável por cima — substituível por `grep`,
`ripgrep` ou qualquer editor.

---

## 10. RAW and retention recommendation

**Proposta: inverter a premissa atual do PRD.**

Dados medidos: 1,17 MB por grupo-ano; ~300 KB comprimido. Dez grupos durante cinco anos
= ~60 MB. **Não existe problema de espaço.** O PRD gasta uma seção inteira, seis estados
de ciclo de vida e um workflow de aprovação para resolver um problema que não existe.

**Mecanismo recomendado (o mais simples suficientemente seguro):**

1. `raw/` guarda tudo, indefinidamente. Está no `.gitignore`.
2. Comprima exports com mais de 6 meses: `gzip` num cron, ou nunca — tanto faz.
3. Deleção: **não escreva nenhum código.** Quando (se) o espaço virar problema, o
   usuário roda `du -sh raw/*` e `rm` o que quiser. Isso já exige confirmação humana
   por construção — a confirmação é o usuário digitar o comando.
4. **Única regra formal:** o pipeline nunca apaga nada. Zero código de deleção no
   repositório. Essa é a garantia mais forte possível, e custa zero linhas.

**Risco: LOW.** Solução proporcional: nenhuma infraestrutura.

**Se mais tarde surgir volume real** (ex.: >50 GB por conta de mídia), aí sim:
um script `kb-gc` que *lista* candidatos e pede `y/N` — ~30 linhas. Não antes.

---

## 11. Source reputation recommendation

As quatro opções pedidas:

| Opção | Avaliação |
|---|---|
| 1. Tags manuais simples | **Recomendada para o MVP.** `contacts.yaml`: `"+55 62 90000-0000": {name: ..., trust: high}` |
| 2. Classificação manual por domínio | **Recomendada para o sistema pragmático.** `trust: {default: medium, web-dev: high}` — exatamente o caso do Rodrigo Calé |
| 3. Reputação calculada | **Rejeitar.** Precisa de ground truth ("esta recomendação era boa?") que você nunca vai fornecer em volume. Clássico sistema que gera números sem significado. |
| 4. Híbrido | **Só no Perfect System**, e mesmo lá com ceticismo |

**O problema real não é reputação, é identidade.** Com 20 nomes e ~100+ telefones,
`contacts.yaml` tem que ser preenchido à mão e crescer sob demanda — você acrescenta
uma linha quando reconhece um número que aparece com frequência. O pipeline usa o
nome quando existe e o telefone quando não existe, sem nunca falhar.

**Uso concreto no MVP:** o campo `trust` **não** filtra nada automaticamente. Ele só
vira uma linha no Markdown (`Recommended by: Prof. Sandeco (reference)`), para que
*você* dê o peso ao ler. Essa é a diferença entre um sistema útil e um sistema que
esconde informação com base em heurísticas que você não auditou.

---

## 12. File / version strategy

**MVP: não implementar.** Justificativa empírica: o export real contém 978
`<Mídia oculta>` e **um** anexo (`.vcf`). Não há arquivos para versionar.

**Quando o usuário começar a colocar PDFs numa pasta à mão:**

Nível 1 (~20 linhas): `sha256` → idênticos são ignorados.
Nível 2 (~40 linhas): família = nome de arquivo normalizado (minúsculas, sem
`v2`/`final`/datas/`(1)`). Mais recente = `CURRENT`, resto vai para `archive/`.
Nível 3: só se o nível 2 falhar visivelmente — comparação de conteúdo via LLM.

Comece no nível 1. Pule para o nível 2 só quando houver pelo menos 3 famílias reais.
Os seis estados do PRD (`CURRENT`/`SUPERSEDED`/`DEAD_ARCHIVE`/`DELETE_CANDIDATE`/
`DELETE_APPROVED`/`DELETED`) devem virar **dois diretórios**: `current/` e `archive/`.

---

## 13. Agent / model strategy

| Agente | Papel recomendado | Entra quando |
|---|---|---|
| **Claude Code** | Arquitetura, revisão de design, prompt engineering (é onde está o valor real). | agora |
| **Codex** | Engenheiro do pipeline: escreve as ~500 linhas. Escopo pequeno e bem definido = caso ideal. | passo 1 |
| **Antigravity** | Reviewer do código do Codex, com quota disponível. **Não** monte processo formal de revisão para 500 linhas. | oportunístico |
| **DeepSeek Flash** | Worker de extração em volume. Único modelo no caminho de dados. **Escolha certa**: US$0,15/1M input off-peak torna o custo irrelevante. | passo 1 |
| **Hermes** | **Não integrar no MVP.** | ver §17 |

**Resposta direta sobre Hermes:** integrar agora é um erro. Hermes é um orquestrador;
não há nada para orquestrar num script de um passo que roda em 2 minutos quando você
digita um comando. Pior: a interface entre pipeline e orquestrador seria desenhada
*antes* de saber como o pipeline realmente se comporta — garantindo retrabalho. Faça o
pipeline funcionar, rode-o manualmente ~10 vezes, descubra o que de fato incomoda, e só
então automatize *isso*.

**Nota sobre model routing:** não construa abstração de provider. Use a API da DeepSeek
diretamente (compatível com o SDK da OpenAI). Trocar de provider depois é um
`find & replace`, não uma camada de arquitetura. "Fornecedores intercambiáveis" é um
princípio correto implementado com uma função, não com um plugin system.

---

## 14. Risk analysis (proporcional)

| # | Risco | Severidade | Mitigação proporcional |
|---|---|---|---|
| 1 | **Overengineering — construir meses de infra e nunca usar o output** | **HIGH** | *O maior risco do projeto.* Mitigação: o vertical slice da §16, com data-limite. |
| 2 | Qualidade do output decepcionar (fichas genéricas/inúteis) | **MEDIUM** | GitHub API enrichment; iterar no prompt; validar com o experimento da §20 **antes** de construir |
| 3 | Perder um recurso bom (falso negativo) | **MEDIUM** | O filtro de URL é quase perfeito para repos. Recursos mencionados *sem link* se perdem — aceite isso no MVP |
| 4 | Classificação/contexto errado | **LOW** | Campo `confidence`; revisão humana; o erro custa uma frase imprecisa |
| 5 | Acumular lixo no vault | **LOW** | 126 fichas são revisáveis à mão em uma hora. `rm` resolve |
| 6 | Gastar tokens desnecessariamente | **LOW** | Teto medido: ~US$0,10/grupo-ano. Não vale código para otimizar |
| 7 | Reexport reprocessar tudo | **LOW** | Skip por URL (10 linhas) |
| 8 | Vazamento de dados pessoais ao LLM | **LOW–MEDIUM** | Telefones vão no prompt. Se incomodar: substituir por `P1..Pn` antes de enviar e remapear depois (~15 linhas). Decisão sua |
| 9 | RAW perdido / irreconstruível | **LOW** | Guardar tudo; é 1 MB/ano |
| 10 | Perda/corrupção do vault | **LOW** | `git init` no vault, commit após cada run. Uma linha |

Nenhum risco é HIGH exceto o de overengineering — e ele é mitigado por este documento.

---

## 15. What NOT to build yet

Seção agressiva, conforme pedido. **Não construa, até que um gatilho da §17 dispare:**

- SQLite / Postgres / qualquer banco
- Graph database e tabelas de edges
- Workflow engine / state machine / estados de falha
- Integração com Hermes
- RBAC, roles, capabilities internas
- Cost accounting, UsageRecord, quota snapshots
- Dashboard de observabilidade
- Retention policy engine, DeletionCandidate, workflow de aprovação de deleção
- Metadata tombstones
- DocumentFamily, versionamento de documentos, dead archive
- Threading engine
- Reputação computada de fontes
- Review queue (uma fila; o vault *é* a fila)
- Pipeline de embeddings / dedup semântico
- Abstração de múltiplos providers de LLM
- Camada de plugins / registro de parsers
- Suporte a Telegram (até existir um export de Telegram em mãos)
- Pipeline de anexos/PDF/OCR
- CLI com subcomandos (`kb ingest|process|review|publish`)
- Migrations, 18 entidades de domínio, os 10 ADRs
- Suíte de testes abrangente (**sim**: teste o parser e a normalização de URL; não teste o LLM)

**Das 18 entidades do PRD, o MVP precisa de duas:** `Message` (transitória, em memória)
e `Resource` (persistida em Markdown).

---

## 16. Recommended MVP vertical slice

**Definição exata do menor sistema funcional:**

```
ENTRADA:  raw/rag-group.txt                    (export real, 1,17 MB)

SAÍDA:    vault/resources/lightrag.md
          vault/resources/khoj.md
          vault/resources/ragflow.md
          ... (~126 arquivos)
          vault/_index.md                      (tabela de todos os recursos)
```

Exemplo de ficha gerada:

```markdown
---
name: LightRAG
url: https://github.com/HKUDS/LightRAG
kind: github_repo
language: Python
stars: 18400
topics: [rag, knowledge-graph, llm]
capabilities: [graph-based-retrieval, incremental-indexing, hybrid-search]
source_group: RAG
mentioned_by: ["+55 85 90000-0000"]
first_seen: 2025-10-11
confidence: high
---

# LightRAG

RAG com indexação baseada em grafo de conhecimento, combinando busca vetorial
e travessia de grafo. *(fonte: GitHub README)*

## Capabilities
- graph-based retrieval
- incremental indexing
- hybrid search (vector + graph)

## Context
Perguntado no grupo "RAG" se alguém já usava. Na discussão foi comparado com
RAGFlow e RAGLight, no contexto de frameworks low-code de RAG.

## Source
Grupo RAG · +55 85 90000-0000 · 11/10/2025

<!-- /auto --> <!-- edições manuais abaixo desta linha são preservadas -->
```

**Escopo congelado:** apenas repositórios GitHub. Ignore YouTube, arXiv, LinkedIn e o
resto no primeiro corte — são 126 de 1.118 URLs, mas carregam a maior parte do valor.
Ampliar para arXiv depois é uma linha no prompt.

---

## 17. Evolution triggers

Cada item: **"Implemente isto somente quando..."**

| Funcionalidade | Implemente somente quando... |
|---|---|
| **SQLite** | ...o vault passar de ~5.000 fichas **e** você tiver escrito pelo menos 3 queries que `grep`/Dataview não respondem. *(Previsão: provavelmente nunca)* |
| **Graph / edges** | ...você tiver feito, por escrito, 5 perguntas multi-hop reais (ex.: "ferramentas recomendadas por pessoas confiáveis que também recomendaram X") e sentido falta das respostas pelo menos uma vez por semana. |
| **Hermes / orquestração** | ...você tiver rodado o pipeline manualmente ≥10 vezes **e** estiver processando ≥3 fontes com agendamento. |
| **Threading real** | ...a revisão do output mostrar contexto errado em >30% das fichas **depois** de já ter ampliado a janela para ±20 mensagens. |
| **Reputação computada** | ...você tiver ≥500 recursos com feedback explícito de "foi útil / não foi". *(Previsão: nunca)* |
| **Embeddings / dedup semântico** | ...você observar duplicatas reais que a normalização de URL não pega (mesmo projeto em domínios diferentes) ≥20 vezes. |
| **Suporte a Telegram** | ...houver um export de Telegram real na pasta `samples/`. |
| **Pipeline de anexos/PDF** | ...houver ≥10 PDFs que você realmente queira indexar. |
| **Versionamento de documentos** | ...existirem ≥3 famílias de documentos com ≥2 versões cada. |
| **Review queue** | ...o volume por execução passar de ~50 fichas novas e ler o vault deixar de ser viável. |
| **Retention / deleção** | ...`du -sh raw/` ultrapassar 20 GB. |
| **Cost accounting** | ...o gasto mensal com LLM passar de US$20. |
| **Testes abrangentes** | ...uma regressão real tiver quebrado o output **duas** vezes. |
| **Múltiplos providers** | ...a DeepSeek ficar indisponível ou cara. (É uma função, não uma camada.) |

---

## 18. Recommended repository structure

```
000_Knowledge_Extractor_WA/
├── README.md
├── .gitignore                 # raw/ vault/ .cache/ .env samples/private/
├── .env.example               # DEEPSEEK_API_KEY, GITHUB_TOKEN
├── pyproject.toml
│
├── docs/
│   ├── PRD.md                 # manter como visão de longo prazo
│   ├── ARCHITECTURE.md        # idem
│   ├── TECHNICAL-SPEC.md      # idem
│   └── architecture/
│       └── MVP-ARCHITECTURE-STUDY.md   ← este documento
│
├── src/kb/
│   ├── parse.py               # export WhatsApp → list[Message]
│   ├── select.py              # filtro de URL + janela + chunking
│   ├── extract.py             # DeepSeek → list[Resource]
│   ├── enrich.py              # GitHub API
│   ├── publish.py             # merge + render Markdown
│   └── run.py                 # main()
│
├── prompts/
│   └── extract.md             # o artefato de maior valor do repositório
│
├── config/
│   └── contacts.yaml          # telefone → nome + trust
│
├── tests/
│   ├── test_parse.py          # inclui casos multi-linha e `<Mídia oculta>`
│   └── test_urls.py           # normalização
│
├── raw/                       # gitignored — exports, guardados indefinidamente
├── .cache/                    # gitignored — seen_urls.jsonl, runs.jsonl
├── vault/                     # gitignored — resources/*.md, _index.md
└── samples/private/           # gitignored
```

Doze arquivos de código. Sem `migrations/`, sem `workflows/`, sem `adapters/`, sem
`schemas/`, sem `cli/`.

---

## 19. Implementation plan (9 passos, cada um testável)

> **Nenhum destes passos é executado agora.** Este é o plano para a próxima sessão.

| # | Passo | Resultado testável |
|---|---|---|
| **0** | **Experimento manual** (§20) — antes de qualquer código | Decisão go/no-go baseada em output real |
| 1 | `parse.py` + `test_parse.py` | `python -m kb.parse raw/rag.txt` imprime 6.328 mensagens; multi-linha e `<Mídia oculta>` tratados |
| 2 | `select.py`: extração/normalização de URL + `test_urls.py` | Imprime 126 URLs GitHub únicas, canônicas |
| 3 | `select.py`: janela de contexto + chunking | Produz ~12 blocos de ≤20k tokens, sem cortar mensagem ao meio |
| 4 | `prompts/extract.md` + `extract.py` em **um** bloco | JSON válido com ~10 recursos; inspecionado à mão |
| 5 | `extract.py` em todos os blocos + merge | `resources.json` com ~120 recursos únicos |
| 6 | `publish.py` → Markdown + `_index.md` | `vault/resources/` populado; abre bem no Obsidian |
| 7 | `enrich.py` (GitHub API) | Fichas ganham stars/linguagem/topics/descrição do README |
| 8 | `contacts.yaml` + resolução de nome | Fichas mostram "Prof. Sandeco" em vez de telefone |
| 9 | Skip de URLs conhecidas (`.cache/seen_urls.jsonl`) | Segunda execução sobre o mesmo arquivo: 0 chamadas de LLM, 0 duplicatas |

Passos 1–6 = MVP funcionando. 7–9 = o sistema pragmático.
**Pare depois do passo 9 e use o sistema por algumas semanas antes de decidir mais nada.**

---

## 20. First experiment (faça isto antes de escrever código)

**Objetivo:** validar as três hipóteses centrais com ~30 minutos de trabalho manual,
antes de investir em desenvolvimento.

**Hipóteses sob teste:**
- H1 — uma janela de ±5–10 mensagens dá contexto suficiente (sem threading);
- H2 — um LLM barato extrai nome/capabilities/contexto com qualidade aceitável;
- H3 — o output resultante é subjetivamente valioso ("eu teria perdido isso").

**Procedimento:**

1. Extraia um recorte de ~2.000 linhas do export real (ex.: um mês com densidade alta
   de links).
2. Cole no DeepSeek Flash (ou no Claude) um prompt-rascunho:
   *"Este é um trecho de um grupo técnico de WhatsApp. Extraia todo repositório GitHub
   mencionado. Para cada um retorne JSON com: name, url, what_it_does, capabilities[],
   mentioned_by, context (por que foi mencionado, o que se discutia), confidence."*
3. Não ajude o modelo. Não limpe os dados. Não faça threading.
4. Conte, sobre o resultado:
   - **precisão** — quantas fichas estão corretas?
   - **recall** — compare com `grep -oE 'github.com/[^ ]+'` no mesmo trecho: quantos
     repos reais o LLM perdeu?
   - **qualidade do contexto** — quantas fichas têm um `context` genuinamente
     informativo (vs. vazio ou errado)?
   - **valor** — quantas te fazem pensar "isto eu teria perdido"?

**Critérios de decisão:**

| Resultado | Ação |
|---|---|
| Recall ≥90% e contexto útil em ≥60% das fichas | Construa a arquitetura C (§5). Hipóteses validadas. |
| Recall alto, contexto fraco | Construa o pipeline, mas ancore as capabilities no **GitHub README** (adição 3) e reduza a dependência da conversa. |
| Recall baixo | O problema é o prompt ou o chunking, **não** a arquitetura. Itere no prompt antes de escrever qualquer código. |
| Output sem valor subjetivo | **Pare o projeto.** Melhor descobrir isso agora do que depois de construir SQLite, grafo e Hermes. |

Este experimento custa centavos e meia hora, e é a decisão de arquitetura mais
importante que você vai tomar.

---

## 21. Respostas diretas às 10 perguntas

**1. Qual é o sistema mínimo que já gera valor?**
Parser regex + filtro de URL + uma chamada de LLM + template Markdown. ~250 linhas de
Python, ~US$0,07 por grupo-ano. Sem banco, sem grafo, sem orquestrador.

**2. Conseguimos fazer o MVP basicamente com LLM + arquivos, sem banco?**
Sim, com folga. 126 recursos é um `dict`. O vault de Markdown é o banco, e é melhor
que um banco porque você pode editá-lo à mão sem criar divergência.

**3. Quando SQLite realmente passa a valer a pena?**
Quando houver ~5.000+ fichas **e** queries que `grep`/Dataview não respondam — e,
crucialmente, quando você parar de querer editar as fichas à mão (o que torna duas
fontes de verdade aceitável). Minha previsão honesta: isso provavelmente nunca
acontece neste projeto.

**4. Precisamos reconstruir threads perfeitamente?**
Não — e nem é possível: o export não tem reply-to. Uma janela de ±5–10 mensagens
resolve ~85% dos casos. Quando errar, o custo é uma frase imprecisa numa ficha.
Se precisar de mais, aumente a janela antes de construir qualquer coisa.

**5. Obsidian deveria ser banco ou interface?**
**Interface.** Escreva Markdown + frontmatter YAML padrão. Nunca dependa de recursos
proprietários do Obsidian. Assim o Obsidian é opcional e substituível.

**6. O graph traz valor agora?**
Não. Nenhuma query de grafo foi formulada até hoje. Com 126 nós, `grep` vence.
Além disso, wikilinks no Obsidian já dão 80% do benefício visual de um grafo, de graça.

**7. Qual parte deveria ser código desde o primeiro dia?**
Parsing do export, extração e **normalização de URL**, classificação de URL
(GitHub/arXiv/YouTube), merge/dedup por URL, chamada à GitHub API, renderização do
Markdown, skip de URLs conhecidas. Tudo determinístico e verificável.

**8. Qual parte deveria ser simplesmente delegada à LLM?**
Relevância semântica, descrição de capability a partir da conversa, reconstrução de
contexto ("por que isto foi recomendado"), mudança de assunto, e o julgamento geral de
"isto é interessante?". Tudo em **uma única chamada** — não encadeie 5 chamadas de LLM
para fazer o trabalho de uma.

**9. Quanto do projeto atual parece overengineering?**
**~70% da especificação atual.** Concretamente: SQLite control plane, knowledge graph,
state machine com estados de falha, RBAC com 4 roles, 18 entidades de domínio, 6
estados de ciclo de vida de arquivo, retention policy engine, deletion approval
workflow, metadata tombstones, cost accounting, quota snapshots, dashboard de
observabilidade, 10 ADRs, e a integração com Hermes. A seção 15 do PRD (maturidade
M0→M4) está essencialmente correta como *direção*, mas M0 ("SQLite inicial, schemas,
modelos de dados, CLI, manifests, política de retenção, métricas") é ela própria mais
trabalho do que o sistema inteiro que recomendo. **Você construiria a fundação de um
prédio antes de saber se quer uma casa.**
Observação justa: a documentação é de alta qualidade e o raciocínio é sólido — o
problema não é a qualidade do pensamento, é o *timing* da construção.

**10. Qual arquitetura eu construiria se este fosse meu projeto?**
Exatamente a arquitetura C (§5). Começaria pelo experimento da §20 na mesma tarde.
Se o output me impressionasse, escreveria as ~500 linhas com o Codex em um ou dois
dias, rodaria sobre todos os exports que tenho, e **usaria o sistema por um mês sem
tocar no código**. Só então olharia para a lista de gatilhos da §17 e veria qual, se
algum, disparou. Minha aposta: depois de um mês, a única coisa que eu iria querer é um
prompt melhor e suporte a arXiv — nenhum dos dois é infraestrutura.

---

## Verificação (quando o MVP for construído)

1. `pytest tests/` — parser e normalização de URL verdes.
2. `python -m kb.run raw/rag-group.txt` sobre o export real → `vault/resources/` com
   ~120 fichas.
3. Comparar com `grep -oiE 'https?://github.com/[^ )>,]+' | sort -u | wc -l` (= 126):
   recall deve ficar ≥90%.
4. Rodar o mesmo comando duas vezes → segunda execução faz 0 chamadas de LLM e não
   cria nem altera nenhum arquivo (idempotência).
5. Abrir o vault no Obsidian e ler 20 fichas ao acaso: o teste final é humano.
