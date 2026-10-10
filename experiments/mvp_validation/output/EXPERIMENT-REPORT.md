# MVP validation report

## Dataset and sampling

Dataset: `samples/private/DOC-20261009-WA0011.zip`, TXT export `Conversa do WhatsApp com RAG.txt`.
The source was parsed without modification. The sample is the first 25 unique canonical GitHub repositories in chronological first-occurrence order, a reproducible continuous temporal prefix rather than a quality-selected set.

## Automatic results

- Messages read: 6,328
- GitHub URLs found: 156
- Unique repositories in source: 111
- Repositories in sample: 25
- Mentions: 29
- URL recall: 25/25 = 100% (target ≥90%)
- Duplicate correctness: 25 resources for 25 canonical repos = 100% (target 100%)
- Mention preservation: 29/29 = 100% (target ≥95%)
- DeepSeek calls: 3 uncached on final rerun; 53 including cached first pass and 15 sensitivity calls
- Final rerun estimated cost: US$0.001898; first uncached pass: US$0.027777
- GitHub requests: 2 uncached on final rerun; 45 including first pass

## Window sensitivity

Five low-confidence/ambiguous candidates were compared at ±4, ±8 and ±16. The model kept the same mention type for all five tested cases. The outputs do not show a clear benefit from ±16; ±8 is the recommended initial default because it preserves more evidence than ±4 without the extra parallel-conversation noise observed in the larger window.

## Errors and diagnosis

The first pass exposed a deterministic URL-normalization bug: a trailing quote produced a second `evaluate-rag` canonical URL. It was fixed by stripping quote delimiters, then the experiment was rerun. This is a small parsing issue, not evidence for a database or threading engine. The private export also contains phone-number authors; no identity resolution was attempted, as required.

The remaining semantic errors should be reviewed in the human sheet. Prompt/context tuning is the first remedy; no evidence here requires threading infrastructure. SQLite is not justified by this 25-resource experiment.

## Architecture questions

- README/metadata enrichment supplied the technical basis for capabilities; compare the cards against their conversation context during review to assess its incremental value.
- Resource/Mention worked as a model: one Resource can hold multiple occurrence-level Mentions (LEANN, gitingest and toon demonstrate this in the sample).
- No evidence was found that SQLite, a graph database, Hermes, or a threading engine is needed for this validation slice.
- Architecture C's pragmatic separation of deterministic detection from semantic interpretation was not refuted.

## Human review

Completed in `HUMAN-REVIEW.md` (2026-10-10), n=5 cards — the sheet generated covers 5
representative cards, not the 20 requested in §17. **This is a deviation: the thresholds
below are met on 5 samples and therefore carry weaker statistical weight than intended.**

| Threshold | Result | Target | Verdict |
|---|---|---|---|
| Context (good + acceptable) | 5/5 = 100% | ≥70% | pass |
| Capabilities (good + acceptable) | 5/5 = 100% | ≥80% | pass |
| Value (yes) | 5/5 = 100% | ≥50% | pass |

All five cards were marked as worth keeping. One card (`toon`) scored `acceptable` rather
than `good` on capabilities, with the note "Description not clear".

### Finding from the review: Mentions are not attributable to people

Every one of the 29 Mentions carries a **phone number as author; not one carries a name.**

```
29/29 Mentions authored by phone numbers
 0/29 Mentions authored by a named contact
   one unresolved contact alone accounts for 12 of 29 (41%)
```

This is a property of the dataset, not a parser defect: the export contains 281 distinct
authors, of which only **7 have saved names** and 274 are phone-only. Verified independently
against the raw export. `Prof. Sandeco` — the senior reference named in PRD §6 — is one of
the seven, so the most important source is identifiable, but the remaining 274 are not.

Consequence: the source-intelligence layer (PRD §6) cannot answer "who recommended this?"
for 97.5% of participants. A `phone → person` map is not an optimisation; it is the
precondition for Mention attribution to mean anything.

GO WITH CHANGES — Architecture C needs the following small changes

1. Keep quote/bracket trimming in deterministic GitHub URL normalization.
2. Use ±8 messages as the initial context default and retain Resource/Mention separation.
3. **Resolve `phone → person` before Mentions are published.** Human review could not
   attribute a single Mention to a person; the review sheet's own question ("who recommended
   this?") is unanswerable without it. This is a lookup table, not infrastructure.
