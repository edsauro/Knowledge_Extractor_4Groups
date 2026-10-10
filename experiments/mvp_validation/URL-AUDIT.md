# URL audit — complete WhatsApp export

## Ground truth

The complete TXT export contains **162 raw GitHub URL occurrences** and **127 distinct raw URL strings**. After deterministic classification and canonicalization, the ground truth is **110 unique GitHub repositories**.

The canonical form is `https://github.com/<owner>/<repo>`; path suffixes are removed, a trailing `.git` is removed, and URL punctuation/query/fragment delimiters are not part of repository identity.

## Classification

| Category | Occurrences | Treatment |
|---|---:|---|
| Repository root after normalization | 155 | Keep as repository occurrence |
| Repository subpath (`/tree/`, `/blob/`) | 12 | Keep occurrence; canonicalize to root |
| Issue/pull URL | 1 | Keep occurrence; canonicalize to root |
| GitHub user/profile or organization | 6 | Exclude from repository ground truth |
| Gist, release, malformed URL | 0 | None found |

The 110 total is computed after canonicalizing and deduplicating repository occurrences; profiles and organizations are excluded. Subpaths and the issue/pull URL remain evidence of a repository occurrence, not separate Resources.

## Origin of 126 vs 111

The architectural study's approximate **126 unique repositories** came from an earlier broad URL extraction/count that did not apply the same canonical repository-root rules. The experiment's **111** was closer but still retained `https://github.com/sandeco/prompts.git` separately from `https://github.com/sandeco/prompts`, and did not document a complete category audit. Removing `.git` and applying the full deterministic classification produces **110 unique repositories**; the issue URL counts toward its valid repository root.

The difference is therefore URL identity policy, not missing messages: non-repository GitHub pages were included by the broad estimate, while aliases and punctuation were not normalized consistently.

## Parser correction

The experimental parser was corrected so `.git` is removed from the repository component before canonicalization. Existing rules preserve subpath/issue occurrences while reducing them to the root repository and reject profile URLs that lack an owner/repository pair. The correction is limited to `experiments/mvp_validation/experiment.py`; no `src/` code was changed.

## MVP ground-truth rule

Detection remains deterministic. Every occurrence preserves its original text and message index. Only canonical repository-root URLs enter `expected_repos`; profiles, organizations, gists and other non-repository GitHub pages are not Resources.
