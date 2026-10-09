Knowledge Extractor — Technical Specification


Status: Draft M0
Data-base: 09/10/2026


1. Escopo técnico


Esta especificação descreve como implementar o Knowledge Extractor no Omarchy com processos reproduzíveis, incrementais e auditáveis.


2. Organização local


Código:
~/Work/knowledge-extractor/
  src/
  tests/
  prompts/
  schemas/
  workflows/
  migrations/
  scripts/
  config/
  docs/


Dados:
~/KnowledgeExtractor/
  raw/
    whatsapp/
    telegram/
    other/
  working/
  dead_archive/
  db/
    knowledge.sqlite
  vault/
    Inbox/
    Threads/
    Resources/
    Capabilities/
    Contacts/
    Domains/
    Sources/
    Reviews/
    Dashboards/
  review/
    deletion_candidates/
    uncertain_threads/
    possible_duplicates/
    version_conflicts/
  logs/
  exports/


3. O que é software neste projeto


Software é o código que ainda será construído para executar o pipeline. Exemplos:
- parser de exportações WhatsApp;
- CLI kb;
- módulo de hashing;
- deduplicador;
- import manager;
- SQLite migrations;
- thread preprocessor;
- adapters para DeepSeek/Codex/Antigravity;
- exportador Obsidian;
- policy engine;
- state machine do Hermes;
- calculador de custos;
- audit logger;
- testes.


Portanto, Git não é uma fonte externa do produto: ele versionará esse software que nós mesmos desenvolveremos.


Conhecimento e RAW não precisam ficar no Git. Por padrão:
- Git: código, schemas, workflows, prompts versionados, migrations, testes e documentação técnica local.
- Fora do Git: RAW, banco SQLite operacional, anexos, cache, logs volumosos e Vault com conteúdo privado, salvo decisão posterior.


4. CLI proposta


kb ingest <source> <path>
kb normalize <import_id>
kb process <scope>
kb review [queue]
kb publish <scope>
kb notify <scope>
kb run <workflow>
kb status
kb usage
kb retention scan
kb retention approve <candidate>
kb retention execute <approval_id>


Todo comando deve aceitar --dry-run quando houver mutação relevante.


5. Pipeline


INGEST
Entrada: export bruto.
Saída: import registrado, arquivos copiados/referenciados, manifest.


NORMALIZE
Parse, timestamps, contatos, mensagens, URLs, anexos, reply-to, fingerprints.


DEDUP
Hash/fingerprint e reconciliação com dados existentes.


THREAD
Agrupamento por regras + LLM quando necessário.


TRIAGE
Relevância técnica, assunto, domínio e prioridade.


EXTRACT
Resources, Capabilities, Sources, Evidence, Relations.


REVIEW
Itens com baixa confiança, conflito, possível versão, fonte nova ou deleção.


PUBLISH
Markdown/Obsidian e atualização de índices.


NOTIFY
Resumo operacional, erros, itens que exigem ação humana.


6. Banco SQLite inicial


Tabelas mínimas:
imports
groups
contacts
contact_domain_trust
messages
attachments
document_families
document_versions
threads
thread_messages
resources
capabilities
resource_capabilities
domains
sources
evidence
edges
processing_jobs
job_steps
review_queue
retention_policies
deletion_candidates
approvals
usage_records
model_rates


Princípios:
- foreign keys ligadas;
- migrations versionadas;
- WAL mode quando adequado;
- transações por step;
- uniqueness constraints para idempotência;
- FTS5 para busca textual local;
- nenhum arquivo binário dentro do SQLite.


7. Identificadores e deduplicação


Mensagem:
Se houver ID oficial, preservar.
Se não houver, gerar fingerprint determinístico a partir de source/group + sender + timestamp normalizado + content + attachment fingerprints.


Arquivo:
SHA-256 para duplicata binária.


URL:
normalização conservadora; preservar URL original e canonical URL separadamente.


Contato:
contact_id interno + aliases por plataforma.


Nunca usar apenas filename para deduplicação.


8. Threading


Sinais determinísticos:
- reply_to;
- menções;
- mesma URL;
- mesmo anexo/document family;
- proximidade temporal;
- participantes;
- marcadores de citação.


Sinais semânticos:
- continuidade temática;
- referência anafórica;
- mudança de assunto;
- equivalência conceitual.


Processo recomendado:
1. construir candidatos por código;
2. enviar apenas candidatos ambíguos ao LLM;
3. exigir resposta JSON conforme schema;
4. validar;
5. guardar confidence e rationale curta;
6. enviar baixa confiança a Review.


9. Extração de conhecimento


Formato de output estruturado de cada worker:
job_id
worker_version
input_ids
output_schema_version
model/provider
confidence
payload
usage
started_at
finished_at


Workers:
thread_builder
technical_triage
resource_extractor
capability_extractor
source_profiler
file_version_analyzer
knowledge_linker
review_generator


Prompts ficam versionados em prompts/ e possuem prompt_version.


10. Código versus LLM — decisão registrada


Criar tabela/registro DecisionRoute:
task_type
preferred_route
fallback_route
reason
estimated_cost
actual_cost
latency
quality_metric
date


Exemplos:


Parsing WhatsApp
Código: alta confiabilidade, custo quase zero, rápido, fácil testar.
LLM: caro, não determinístico, desnecessário.
Escolha: código.


Threading ambíguo
Código: barato, mas perde relações semânticas.
LLM: melhor compreensão, custo variável.
Escolha: híbrido.


Detecção de arquivo idêntico
Código/hash: exato.
LLM: inadequado.
Escolha: código.


Detecção de nova edição do mesmo livro
Código: metadata/text diff/similarity é barato e explicável.
LLM: ajuda quando título/nome divergem ou estrutura mudou.
Escolha: híbrido.


Technical relevance
Código: regras ajudam a remover ruído óbvio.
LLM: melhor para contexto.
Escolha: híbrido.


11. Versionamento de documentos


Etapas:
1. hash exato;
2. extração de metadata;
3. identificação de título/autor;
4. page count/size;
5. text fingerprint;
6. similaridade;
7. LLM somente para casos ambíguos.


DocumentFamily mantém uma versão CURRENT.


Ao reconhecer uma nova versão:
- nova = CURRENT;
- anterior = SUPERSEDED;
- mover anterior opcionalmente para dead_archive;
- gerar Review quando confiança abaixo do threshold;
- deleção posterior requer aprovação.


12. Retenção de RAW


RetentionPolicy por grupo:
scope_id
mode
value
min_publish_age
criticality
archive_before_delete
requires_approval=true


Critério de elegibilidade para DELETE_CANDIDATE:
- conhecimento relevante já publicado OU conteúdo classificado como não técnico;
- nenhum job pendente depende do RAW;
- período de segurança cumprido;
- política do grupo permite;
- manifest e metadados preservados.


A varredura apenas cria candidatos.


Execução física:
scan → candidate → human approval → approval record → execute.


Sem approval_id válido, o comando de delete deve falhar.


13. Uso/custo


usage_records:
provider
model
job_id
input_tokens
cached_input_tokens
output_tokens
reasoning_tokens
cost_usd
quota_before
quota_after
quota_delta
window_reset_at
rate_version
timestamp


DeepSeek:
calcular por tokens reais retornados.
DeepSeek Flash em 09/10/2026:
off-peak cache-hit input 0.003 USD/M;
peak cache-hit input 0.006 USD/M;
off-peak cache-miss input 0.15 USD/M;
peak cache-miss input 0.30 USD/M;
off-peak output 0.60 USD/M;
peak output 1.20 USD/M.


Codex:
capturar status antes/depois quando disponível por interface suportada. O custo marginal do uso incluído pode ser zero até atingir franquia, mas a métrica prioritária é quota consumida. Registrar modelo, reasoning/effort e tipo de execução.


Antigravity:
capturar quota.remaining_fraction/reset_time via CLI/statusline quando disponível. Converter para used_percentage = 100 × (1 - remaining_fraction).


14. Obsidian publish format


Não publicar uma nota por mensagem.


Notas:
Thread
Resource
Capability
Contact
Domain
Source
DocumentFamily
Review


Cada nota deve ter YAML frontmatter com IDs estáveis e backlinks.


Exemplo Thread:
type: thread
thread_id: th_x
groups: [...]
participants: [...]
date_start:
date_end:
confidence:
source_message_ids: [...]


Corpo:
Resumo
Contexto reconstruído
Capabilities
Resources
Evidências
Fontes
Pendências


15. Hermes Workflow Contract


Hermes nunca deve decidir livremente o próximo passo.


Definir workflow declarativo, por exemplo:
workflows/knowledge_extractor_v1.yaml


Cada step contém:
id
allowed_command
input_schema
preconditions
postconditions
timeout
retry_policy
on_failure
requires_human_approval
next


Hermes recebe apenas a capacidade de chamar uma allowlist de comandos kb.


Ele não recebe permissão ampla para:
- alterar schemas;
- editar migrations;
- deletar arquivos diretamente;
- executar rm;
- pular review gates;
- mudar retention policy;
- publicar conteúdo inválido.


16. Garantia contra improvisação do Hermes


Camadas de defesa:
1. State machine: estado corrente determina único conjunto permitido de transições.
2. Command allowlist: Hermes chama kb, não shell arbitrário para operações do produto.
3. JSON Schema: entradas e saídas de cada step são validadas.
4. Preconditions/postconditions: step não avança se contrato falhar.
5. Idempotency keys: reexecução não duplica efeitos.
6. Database transaction: mutações atômicas.
7. Human gates: deleção e mudanças sensíveis exigem approval_id.
8. Dry-run: obrigatório durante M1/M2 para operações destrutivas.
9. Audit log append-only: comando, ator, entradas, saída e hashes.
10. Workflow version pinning: job registra exatamente workflow_version e prompt_versions.
11. Tests: golden datasets antes de promover workflow.
12. Least privilege: processo Hermes sem permissão de escrita direta fora de diretórios autorizados.
13. Fail closed: output inválido interrompe; nunca “tenta improvisar”.
14. No arbitrary fallback: fallback precisa estar no workflow.


17. Testes


Unit:
parser, hashes, cost calculator, policy engine.


Golden datasets:
pequenas exportações artificiais com threads intercaladas e anexos.


Integration:
ingest→publish.


Idempotency:
rodar duas vezes e comparar DB/Vault.


Failure recovery:
matar processo entre steps e retomar.


Safety:
tentativa de delete sem approval deve falhar.


18. M0 deliverables


- repo knowledge-extractor;
- pyproject;
- CLI kb;
- SQLite schema v1;
- migrations;
- config;
- workflow schema;
- retention policy schema;
- usage schema;
- WhatsApp sample parser skeleton;
- Obsidian note schemas;
- tests;
- ADRs iniciais.