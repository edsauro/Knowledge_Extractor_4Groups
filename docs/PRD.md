Knowledge Extractor — Product Requirements Document (PRD)


Status: Draft M0
Data-base: 09/10/2026
Produto: Knowledge Extractor


1. Visão do produto


Knowledge Extractor é um sistema local-first para transformar grandes volumes de conversas, anexos, links e documentos oriundos de WhatsApp, Telegram e fontes similares em conhecimento técnico organizado, rastreável e pesquisável.


O produto deve privilegiar Capabilities: o objetivo não é acumular links ou nomes de ferramentas, mas responder o que é possível fazer, quais recursos habilitam cada capability, quem forneceu a informação, onde está a evidência original, quão confiável é a fonte e se a informação já foi revisada.


O sistema será executado inicialmente em um computador Linux com Omarchy. Hermes será o orquestrador do processo. Codex e Antigravity atuarão principalmente como engenheiros do pipeline e revisores, enquanto DeepSeek Flash será o worker barato para processamento semântico em escala.


2. Problema


Grupos técnicos misturam discussões paralelas, mensagens curtas, respostas encadeadas, links, anexos, versões sucessivas de documentos e participantes com diferentes níveis de conhecimento. Ler tudo manualmente é inviável.


Uma mensagem isolada frequentemente não possui significado suficiente. O sistema precisa reconstruir threads levando em conta resposta-a, autores, menções, horário, URLs, anexos, similaridade semântica e mudança de assunto.


Também é necessário distinguir três coisas: quem compartilhou a informação, quem é o autor original e a qualidade da evidência. Uma pessoa iniciante pode compartilhar uma excelente fonte primária; uma pessoa sênior pode emitir uma opinião sem evidência externa.


3. Objetivos


- Ingerir exportações periódicas de grupos independentemente.
- Detectar apenas conteúdo novo em exportações que repetem o histórico.
- Preservar autoria, contato, grupo, data, mensagem, reply-to, URLs e anexos.
- Reconstruir threads temáticas mesmo quando mensagens de assuntos diferentes estão intercaladas.
- Extrair Resources, Capabilities, Domains, Sources e relações.
- Consolidar vários grupos em uma única base global.
- Manter conhecimento curado em Obsidian/Markdown.
- Usar SQLite como control plane operacional, índice e base relacional/grafo inicial.
- Deduplicar mensagens e arquivos.
- Detectar famílias e versões evolutivas de documentos.
- Manter sempre a versão corrente; versões antigas podem ir para Arquivo Morto.
- Toda deleção física exige confirmação humana.
- Permitir política configurável de retenção de RAW por fonte/grupo.
- Medir custo de APIs e consumo de cotas dos agentes.
- Permitir escolher entre implementação determinística por código e classificação por LLM sempre que ambas forem viáveis.
- Tornar Hermes estritamente aderente a um workflow definido, auditável e sem improvisação.


4. Não objetivos iniciais


- Não construir um knowledge graph dedicado como Neo4j no MVP.
- Não indexar todas as mensagens individualmente no Obsidian.
- Não exigir preservação permanente de RAW.
- Não automatizar deleções sem aprovação humana.
- Não depender de um único fornecedor de LLM.
- Não tentar resolver todo tipo de mídia já em M0.


5. Modelo conceitual


Camadas:


RAW → Ingest → Normalize/Deduplicate → Threading → Technical Triage → Knowledge Extraction → Review → Publish → Notify.


Entidades principais:
- Group
- Import
- Contact
- Message
- Attachment
- DocumentFamily
- Thread
- Resource
- Capability
- Domain
- Source
- Evidence
- Edge/Relationship
- ReviewItem
- DeletionCandidate
- ProcessingJob
- UsageRecord


6. Source intelligence


Fonte/contato é entidade de primeira classe.


O sistema deve registrar:
- nome/identidade conhecida;
- plataforma;
- aliases;
- grupos em que aparece;
- áreas/domínios;
- user_prior por domínio;
- observed_reliability por domínio;
- quantidade de recomendações;
- quantidade posteriormente validada/refutada;
- autoria original quando diferente de quem compartilhou.


Política inicial de confiança:
- Sandeco: referência/sênior global para temas em que opina.
- Devolver: referência/sênior global para temas em que opina.
- Rodrigo Calé: nível intermediário global, com prioridade maior em Web Development.
- Demais contatos começam sem julgamento automático e acumulam evidência.


O user_prior nunca deve ser alterado silenciosamente pelo sistema. O sistema pode sugerir mudança e colocar em Review.


7. Política de RAW e retenção


RAW não é necessariamente permanente.


Cada fonte/grupo terá uma política configurável:
- retention_mode: days | months | volume | manual | keep;
- retention_value;
- criticality;
- archive_before_delete;
- delete_requires_human_approval: sempre true.


O objetivo de RAW é permitir reprocessamento durante um período de segurança. Depois de o conhecimento ter sido consolidado e publicado, RAW pode ser candidato a remoção para economizar espaço.


Grupos futuros classificados como críticos poderão receber retenção longa ou permanente.


8. Versões de arquivos


Arquivos idênticos são deduplicados por hash.


Documentos evolutivos exigem detecção de família e versão. Exemplo: livros do Sandeco que ganham novos capítulos.


Estados:
CURRENT
SUPERSEDED
DEAD_ARCHIVE
DELETE_CANDIDATE
DELETE_APPROVED
DELETED


A versão mais recente fica em armazenamento ativo. As anteriores podem ser movidas para Arquivo Morto. O Arquivo Morto serve para consulta e recuperação e pode ser limpo posteriormente quando houver pressão de espaço, sempre após aprovação humana.


Mesmo após deleção, preservar metadados pequenos: hash, nome, tamanho, família, versão, motivo, data de deleção e superseded_by.


9. Maturidade do produto


M0 — Fundamentos
- estrutura de diretórios;
- repositório de software;
- SQLite inicial;
- schemas;
- modelos de dados;
- CLI mínima;
- manifests;
- política de retenção/deleção;
- métricas/custos;
- testes básicos.


M1 — Pipeline manual
- usuário coloca exports em RAW;
- execução manual de ingest/process/review/publish;
- WhatsApp como primeira fonte;
- deduplicação determinística;
- identificação inicial de contatos;
- extração e revisão manual das primeiras threads;
- Obsidian Vault gerado pelo pipeline.


M2 — Assistido
- DeepSeek Flash para threading/triagem/extraction;
- fila de revisão;
- Hermes pode executar comandos individuais aprovados;
- detecção de famílias/versões;
- dashboards de uso e custo;
- sugestões de classificação de fontes.


M3 — Semi-automático
- Hermes executa workflow completo sob contrato;
- processamento incremental;
- notificações;
- revisão humana apenas de exceções, deleções, conflitos e baixa confiança;
- retenção programada gera candidatos, nunca deleção autônoma.


M4 — Automático
- ingestões e processamento recorrentes;
- policy engine por grupo;
- escalonamento automático entre código/LLMs conforme política;
- observabilidade e recuperação;
- conhecimento consolidado contínuo;
- intervenção humana concentrada em aprovação de risco/qualidade.


10. Critérios de sucesso do MVP M1/M2


- Reimportar o mesmo histórico não duplica mensagens.
- Arquivos idênticos não são armazenados múltiplas vezes no working set.
- Novas mensagens são reconhecidas incrementalmente.
- Cada conhecimento publicado aponta para contato/fonte/data e evidência rastreável.
- Threads intercaladas podem ser reconstruídas com revisão humana.
- Pelo menos Resources e Capabilities são consolidados entre múltiplos grupos.
- O sistema registra custo DeepSeek por job.
- O sistema registra snapshot de uso Codex/Antigravity antes/depois quando disponível.
- Nenhuma deleção física ocorre sem aprovação explícita.
- Reexecução do mesmo job é idempotente ou detectada.
- Uma falha no meio do workflow pode ser retomada sem corromper o conhecimento.


11. Matriz código versus LLM


Regra geral: preferir código quando a regra for determinística e verificável; preferir LLM quando exigir interpretação semântica.


Tarefas primariamente por código:
- hashing;
- deduplicação exata;
- parsing de export;
- IDs determinísticos;
- checksums;
- mover arquivos;
- retenção por data/volume;
- transações SQLite;
- schemas;
- validação JSON;
- logs;
- state machine;
- cálculo de custo.


Tarefas primariamente por LLM:
- reconstrução semântica de threads ambíguas;
- identificação de mudança de assunto;
- descrição de capability;
- classificação de domínio;
- avaliação de relevância técnica;
- síntese de evidências;
- sugestão de relações.


Tarefas híbridas:
- versões de documento;
- similaridade de conteúdo;
- reputação de fonte;
- classificação de anexos;
- identificação de duplicata semântica.


Para toda tarefa híbrida, documentar: opção código, opção LLM, qualidade esperada, custo, latência, facilidade de teste e risco de erro.


12. Política de modelos e custos


Codex:
Uso principal no MVP: engenheiro de pipeline e, quando vantajoso, processamento assistido usando a franquia do plano. O consumo depende do modelo, complexidade, contexto e ferramentas. O produto deve registrar snapshots do painel/CLI de uso antes e depois de jobs relevantes. O sistema não deve assumir que horário noturno do Codex possui preço menor sem evidência oficial; tratar como hipótese operacional e medir.


Antigravity:
Uso principal: engenheiro/revisor, especialmente quando houver quota disponível. Registrar remaining_fraction/used percentage e reset quando expostos pela CLI/statusline. Quando a quota acabar, Codex pode assumir a revisão conforme política.


DeepSeek Flash:
Worker pago preferencial para volume semântico. Modelo atual documentado: deepseek-flash (DeepSeek V4.1 Flash). Preço oficial em 09/10/2026 por 1M tokens:
- input cache hit: US$0,003 off-peak; US$0,006 peak;
- input cache miss: US$0,15 off-peak; US$0,30 peak;
- output: US$0,60 off-peak; US$1,20 peak.
Off-peak é metade do pico. O UsageRecord deve usar tokens reais retornados pela API.


13. Perguntas em aberto


- Qual formato exato do export de WhatsApp será o primeiro suportado?
- Como detectar reply-to quando a exportação não preservar explicitamente IDs?
- Por quanto tempo cada grupo deve manter RAW?
- Qual limite de disco deve disparar limpeza prioritária?
- Quando promover SQLite/edges para um graph database dedicado?
- Quais modelos Codex serão preferidos para tarefas batch do MVP?
- Qual formato do dashboard de Review: Obsidian puro, TUI ou web local?


14. Referências operacionais atuais


OpenAI: consultar Settings → Usage ou /status para franquia e resets Codex.
Antigravity: /usage ou /quota e statusline expõem quotas/remaining_fraction.
DeepSeek: https://api-docs.deepseek.com/quick_start/pricing/