Knowledge Extractor — System Architecture


Status: Draft M0
Data-base: 09/10/2026


1. Princípios arquiteturais


- Local-first.
- Pipeline antes de agente.
- Knowledge-centric, Capability-first.
- Human-in-the-loop para operações destrutivas e incerteza importante.
- Determinismo quando possível; LLM quando necessário.
- Fornecedores de LLM intercambiáveis.
- Auditoria e reprocessamento.
- Dados brutos temporários por política, não dogmaticamente permanentes.
- Separação entre operational truth e semantic knowledge.


2. Visão de componentes


Fontes
  ↓
RAW stores por grupo
  ↓
Ingest/Normalize/Dedup
  ↓
SQLite Control Plane
  ↓
Semantic Workers
  ↓
Knowledge Graph lógico
  ↓
Review
  ↓
Obsidian Vault + SQLite indexes
  ↓
Hermes orchestration / notification


Codex e Antigravity evoluem o software.
DeepSeek Flash processa volume semântico.
Hermes coordena jobs aprovados.


3. Três planos arquiteturais


Data Plane
RAW, working files, dead archive, Obsidian Vault.


Control Plane
SQLite, jobs, estados, policies, manifests, approvals, usage.


Agent Plane
Hermes, Codex, Antigravity, DeepSeek adapters.


Essa separação impede que um agente seja a única fonte de verdade.


4. Por que Obsidian + SQLite + Graph


Obsidian/Markdown:
bom para leitura humana, correção, backlinks, contexto e edição manual.


SQLite:
bom para milhares/milhões de mensagens, constraints, queries, hashes, estado, idempotência, métricas e automação.


Graph:
necessário conceitualmente para relações como SENT_BY, REPLIES_TO, BELONGS_TO, MENTIONS, HAS_CAPABILITY, EXPERT_IN, VERSION_OF e SUPERSEDES.


M0–M2:
o grafo é implementado em SQLite por tabelas relacionais/edges e refletido em wikilinks do Obsidian.


Graph DB dedicado só será avaliado quando consultas reais justificarem a complexidade.


5. Git — papel correto


Git versiona SOFTWARE e especificações técnicas, não é o repositório primário do conhecimento.


Software significa o pipeline que será criado neste projeto:
parsers, CLI, schemas, migrations, tests, workflows, adapters, prompts e scripts.


O benefício do Git:
- saber o que mudou;
- desfazer regressões;
- criar branches para Codex/Antigravity;
- fazer code review;
- marcar releases M0/M1/M2;
- vincular um job à versão do código que o processou.


Dados privados e volumosos ficam fora do Git por padrão.


.gitignore deve cobrir:
raw/
working/
dead_archive/
*.sqlite
logs/
secrets/
cache/


O Vault pode ou não ser versionado depois. Inicialmente, não é necessário.


6. Topologia no Omarchy


Processos locais:
knowledge-extractor CLI
SQLite
Obsidian
Hermes
Codex CLI/app
Antigravity CLI/app


DeepSeek é serviço externo via API.


O pipeline deve funcionar mesmo com Hermes parado:
kb ingest
kb process
kb review
kb publish


Hermes é uma camada superior de automação.


7. Fluxo M1


Usuário exporta grupo.
Usuário coloca conteúdo em raw/whatsapp/<group>/imports/<date>/.
Usuário executa kb ingest.
Parser registra import.
Dedup reconhece conteúdo já conhecido.
Processamento gera novos itens.
Review apresenta exceções.
Publish atualiza Vault.
Usuário confirma candidatos de deleção quando desejar.


8. Fluxo M2


Mesmo fluxo, mas Semantic Workers processam partes ambíguas automaticamente.


Roteamento padrão:
determinístico → Python;
semântico de alto volume → DeepSeek Flash;
engenharia/refatoração → Codex;
revisão/segunda opinião → Antigravity, com Codex como fallback.


Não se deve usar LLM para hashing, retenção, transações ou validação de schema.


9. Fluxo M3/M4 com Hermes


Hermes executa um workflow congelado:


INGEST
↓
PROCESS
↓
REVIEW-GATE
↓
PUBLISH
↓
NOTIFY


Cada seta é transição de state machine, não sugestão em prompt.


Hermes não recebe a instrução genérica “organize estes dados”. Recebe algo equivalente a:
Run workflow knowledge_extractor_v1 for import X.


O executor valida o estado atual e retorna apenas ações permitidas.


10. Padrão Command Pattern


Hermes deve invocar comandos estruturados:
kb workflow step --job JOB --step ingest


Não comandos shell arbitrários.


O comando consulta workflow YAML/JSON e DB.


Exemplo de transição:
NEW → INGESTED → NORMALIZED → PROCESSED → REVIEWED → PUBLISHED → NOTIFIED


Estados de falha:
FAILED_RETRYABLE
FAILED_BLOCKED
WAITING_HUMAN


DELETE não faz parte da linha principal; é um workflow separado.


11. Segurança contra improvisação


Prompt não é mecanismo de segurança.


As garantias devem estar em código.


Hermes pode pedir para executar algo inválido; o executor rejeita.


Exemplo:
Hermes: delete arquivo X.
Executor: ERROR approval_id required.


Hermes: skip review.
Executor: ERROR transition PROCESSED→PUBLISHED forbidden.


Hermes: altere retention policy.
Executor: ERROR capability not allowed for orchestrator role.


Assim, “seguir o processo” é propriedade do software, não comportamento esperado do modelo.


12. RBAC/capabilities internas


Role ORCHESTRATOR:
run allowed workflow steps
read status
read review queue
notify


Role ENGINEER:
alterar código em branch/worktree
rodar testes
propor migration
não apagar dados produtivos


Role HUMAN_APPROVER:
aprovar delete
alterar policy
aprovar merge de mudanças sensíveis


Role WORKER_LLM:
receber input minimizado
retornar output estruturado
nenhuma permissão direta ao filesystem/DB


13. Dados e privacidade


Enviar ao LLM apenas conteúdo necessário ao job.


Contatos e grupos podem receber IDs internos quando nome real não for necessário ao processamento.


Segredos/API keys nunca entram em prompt, Vault ou Git.


RAW pode conter dados pessoais; seu ciclo de retenção é configurável.


14. Política de armazenamento


ACTIVE RAW:
exportações recentes necessárias para reprocessamento.


WORKING:
arquivos temporários e normalizados.


CURRENT DOCUMENTS:
últimas versões de famílias conhecidas.


DEAD ARCHIVE:
versões antigas potencialmente úteis, comprimíveis e descartáveis com aprovação.


CURATED KNOWLEDGE:
Vault + SQLite, retenção longa.


METADATA TOMBSTONES:
pequenos registros sobre arquivos deletados para evitar reingestão inútil.


15. Observabilidade


Cada job registra:
job_id
workflow_version
code_commit
prompt_versions
provider/models
timestamps
inputs/outputs
counts
errors
cost
quota snapshots
review decisions


Dashboard mínimo:
novas mensagens;
novos arquivos;
duplicatas;
threads;
resources;
capabilities;
review pendente;
bytes RAW;
bytes dead archive;
bytes candidatos a deleção;
DeepSeek USD;
Codex quota delta;
Antigravity quota delta.


16. Uso inteligente das cotas


Codex:
prioridade para engenharia de pipeline, correções complexas, testes e revisão quando Agy indisponível. Registrar status de uso antes/depois de sessões relevantes. A existência de janela de cinco horas/limite semanal depende do plano e deve ser lida do estado real da conta.


Antigravity:
engenheiro/revisor complementar. CLI expõe quota por modelo, remaining_fraction e reset. Consumir quota gratuita/inclusa primeiro conforme política.


DeepSeek Flash:
preferência para workloads batch repetitivos. O preço off-peak oficial torna possível agendar processamento pesado fora dos horários de pico.


17. ADRs a criar


ADR-001 Obsidian + SQLite como arquitetura híbrida.
ADR-002 SQLite edges antes de Graph DB.
ADR-003 Hermes como orchestrator, não source of truth.
ADR-004 Deterministic-first routing.
ADR-005 RAW retention configurável.
ADR-006 Human approval obrigatório para delete.
ADR-007 LLM providers substituíveis.
ADR-008 Source trust por domínio.
ADR-009 Git somente para software e specs inicialmente.
ADR-010 Workflow state machine para Hermes.


18. Evolução por maturidade


M0:
arquitetura, schemas, repo, state machine skeleton.


M1:
pipeline manual completo e observável.


M2:
semantic workers e review queue.


M3:
Hermes orquestra com guardrails.


M4:
scheduling, retention automation, policy-driven routing e otimização contínua.


19. Critério para promover automações


Uma etapa só passa de manual para automática quando:
- possui testes suficientes;
- é idempotente;
- possui rollback/recovery;
- métricas de erro conhecidas;
- custos conhecidos;
- input/output schema estável;
- comportamento de falha definido;
- não depende de decisão humana não modelada.


20. Decisão arquitetural central


O Knowledge Extractor não deve ser “um bot que lê grupos”.


Ele deve ser um sistema de processamento de conhecimento, no qual agentes são componentes substituíveis e supervisionados.


Isso permite começar manual, medir, amadurecer e automatizar sem reconstruir a base a cada mudança de modelo.