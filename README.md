# Knowledge Extractor

Sistema local-first para transformar grandes volumes de conversas, anexos, links e
documentos (WhatsApp, Telegram e fontes similares) em conhecimento técnico
organizado, rastreável e pesquisável.

**Status:** Draft M0 — fundamentos.

## Documentação

| Documento | Conteúdo |
|---|---|
| [PRD.md](docs/PRD.md) | Visão do produto, problema, objetivos, maturidade M0–M4, critérios de sucesso |
| [TECHNICAL-SPEC.md](docs/TECHNICAL-SPEC.md) | Organização local, CLI `kb`, pipeline, schema SQLite, threading, retenção, workflow contract |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Princípios, três planos, RBAC, observabilidade, ADRs, critério de promoção de automação |

## Estrutura

```
.
├── docs/       # especificações (versionadas)
├── samples/    # amostras pequenas para testes e desenvolvimento
└── .gitignore
```

Os diretórios de dados (`raw/`, `working/`, `dead_archive/`, `db/`, `vault/`,
`review/`, `logs/`, `exports/`) descritos em TECHNICAL-SPEC §2 **não são
versionados** e ainda não foram criados.

## Princípios

- Local-first; pipeline antes de agente.
- Knowledge-centric, Capability-first.
- Determinismo quando possível, LLM quando necessário.
- Nenhuma deleção física sem `approval_id` humano.
- O pipeline funciona com Hermes parado — Hermes é camada de orquestração, não
  fonte de verdade.

## Convenções

- Git versiona **software e especificações**, não dados brutos nem conhecimento
  curado.
- Ver `.gitignore` para o que fica fora.
