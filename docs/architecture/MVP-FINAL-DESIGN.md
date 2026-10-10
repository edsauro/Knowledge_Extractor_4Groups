# Knowledge Extractor — MVP final design

This is the frozen implementation contract for the first MVP. It deliberately does not introduce SQLite, graph database, Hermes, state machine, workflow engine, embeddings, provider abstraction, threading, sophisticated CLI, or automated reputation scoring. Markdown is the source of truth; JSONL is disposable cache.

## 1. Ground truth and scope

The complete reference export contains 162 raw GitHub URL occurrences and 110 unique canonical repositories after deterministic classification. Six profile/organization URLs are excluded; subpaths and the one issue/pull URL resolve to their repository root. Details: `experiments/mvp_validation/URL-AUDIT.md`.

The first supported input is one WhatsApp TXT export. Every repository occurrence becomes a Mention, even when its Resource already exists.

## 2. Frozen flow

```text
WhatsApp TXT → deterministic parser → GitHub URL detection/normalization
→ occurrence IDs + ±8-message windows → DeepSeek Mention context/type
→ GitHub API + README → DeepSeek description/capabilities
→ in-memory Resource + N Mentions → one Markdown file per Resource
```

The parser owns timestamps, raw author, multiline text and sequential indexes. The LLM never decides whether a string is a GitHub repository.

## 3. Minimal schemas

### Resource

```json
{
  "canonical_url": "https://github.com/owner/repo",
  "name": "repo",
  "what_it_does": "README-derived description",
  "capabilities": ["specific action-oriented capability"],
  "github": {
    "full_name": "owner/repo", "description": null, "topics": [],
    "language": null, "stars": null, "license": null,
    "default_branch": "main", "readme": "..."
  },
  "mentions": []
}
```

Missing GitHub values remain null or empty. Capabilities are approximately 3–8 specific actions.

### Mention

```json
{
  "mention_id": "deterministic-id",
  "canonical_url": "https://github.com/owner/repo",
  "group": "raw group name", "source_message_index": 123,
  "date": "2026-10-09", "contact_id": "+5511999999999",
  "display_name": null, "identity_status": "unresolved",
  "mention_type": "recommendation|question|comparison|reference|announcement|other",
  "context": "why this resource appeared", "technical_topic": "...",
  "confidence": "high|medium|low",
  "original_url": "https://github.com/owner/repo/tree/main/..."
}
```

The ID is deterministic from group, timestamp, raw author, canonical URL and message index. A repeated occurrence always creates another Mention.

## 4. Contacts and privacy

Create `config/contacts.yaml` as a small manual mapping:

```yaml
"+5511999999999":
  name: "Example"
  trust:
    default: strong
    web-development: reference
```

Before any external API call, replace raw authors with stable local pseudonyms such as `CONTACT_017`. DeepSeek receives the pseudonym, never the phone number. After the response, resolve through `contacts.yaml`; known contacts receive `display_name` and `identity_status: resolved`, others remain `unresolved` without blocking processing.

Unknown-contact reporting is a later read-only aggregation sorted by Mention count, then distinct Resource count. It is not a UI or identity system.

## 5. URL normalization

1. Extract HTTP(S) URLs for `github.com` or `www.github.com`.
2. Preserve the exact original URL on the occurrence.
3. Remove surrounding punctuation, query parameters and fragments.
4. Require owner and repository; exclude profiles/organizations without both.
5. For `/issues/...`, `/pull/...`, `/tree/...`, `/blob/...` and other subpaths, keep the occurrence but use only `owner/repo` as identity.
6. Remove trailing slash and `.git` from the repository component.
7. Emit `https://github.com/<owner>/<repo>`.
8. Deduplicate Resources only by canonical URL; never deduplicate Mentions.

## 6. Cache strategy

```text
.cache/repos.jsonl
.cache/mentions.jsonl
.cache/runs.jsonl
```

`repos.jsonl` caches GitHub metadata/README by canonical URL; `mentions.jsonl` caches structured analysis by Mention ID; `runs.jsonl` records counts, model, timestamps and token usage. Deleting `.cache/` must leave the vault valid and allow complete reconstruction. Cache reuse may skip enrichment or analysis, never a newly detected Mention.

## 7. Markdown output

Write `vault/resources/<slug>.md`, one file per Resource:

```markdown
---
name: LightRAG
url: https://github.com/HKUDS/LightRAG
kind: github_repo
language: Python
stars: 12345
capabilities:
  - perform hybrid retrieval
---

# LightRAG

## What it does
README-derived description.

## Capabilities
- perform hybrid retrieval

## Mentions
### 2026-10-09 — CONTACT_017
Type: recommendation
Confidence: high
Identity: unresolved

Context...

## Human review
<!-- notes below are human-owned -->
```

Conversation explains why the Resource appeared; README/metadata explains what it does. Keep both separate.

## 8. Minimal repository structure

```text
src/kb/{parse.py,urls.py,mentions.py,enrich.py,capabilities.py,publish.py,run.py}
config/contacts.yaml
prompts/{mention.md,capabilities.md}
tests/{test_parse.py,test_urls.py,test_mentions.py}
raw/       # gitignored input
.cache/    # gitignored JSONL
vault/     # gitignored generated knowledge
```

No migrations, schemas package, adapters, workflows, plugin system or generic CLI belongs in this contract.

## 9. Minimum tests

1. Parse single-line and multiline WhatsApp messages, preserving order and `<Mídia oculta>`.
2. Extract multiple URLs from one message and preserve each original URL.
3. Normalize root, slash, query, fragment, `.git`, issue, pull, tree and blob URLs to one repository.
4. Reject profiles/organizations and non-GitHub URLs.
5. Produce deterministic Mention IDs and exact ±8 windows at boundaries.
6. Prove two occurrences produce one Resource and two Mentions.
7. Pseudonymize authors before mocked DeepSeek and resolve contacts afterward.
8. Rebuild identical Markdown from identical input/cache and keep unresolved contacts processable.

## 10. Implementation plan — eight steps

1. Add the minimal layout, environment example and ignored `raw/`, `.cache/` and `vault/` paths.
2. Implement and test the WhatsApp parser.
3. Implement URL extraction/classification/canonicalization and fixtures.
4. Implement occurrence IDs, pseudonymization, contacts lookup and ±8 windows.
5. Add the direct DeepSeek Mention call with strict JSON validation and cache lookup.
6. Add GitHub metadata/README enrichment cached by canonical URL.
7. Add capability extraction, Resource/Mention merge and Markdown rendering.
8. Run fixture tests and one real export; inspect Markdown and record run metrics.

## 11. Acceptance criteria

- Reference export yields 110 canonical repositories under this document's rules.
- Every detected repository occurrence becomes exactly one Mention; existing Resources never suppress it.
- One canonical repository yields one Markdown Resource file.
- Mention analysis receives pseudonymized authors and ±8 context; raw phone numbers never leave the local process.
- Unknown contacts remain processable and are marked `identity_status: unresolved`.
- GitHub metadata/README are the primary source for description and capabilities.
- Re-running input is deterministic, reuses cache where possible, and does not duplicate Resources or Mentions.
- Deleting `.cache/` permits reconstruction from raw input and regeneration of the vault.
- No SQLite, graph database, Hermes, workflow/state machine, embeddings, provider abstraction, threading engine or future UI is introduced.
