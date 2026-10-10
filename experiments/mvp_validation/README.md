# MVP validation experiment

This is a disposable validation experiment, not the Knowledge Extractor MVP.
It reads the private WhatsApp export from `samples/private/` without modifying it,
selects a deterministic temporal sample of GitHub repositories, and tests the
Resource/Mention model with DeepSeek Flash and GitHub enrichment.

Run from the repository root:

```bash
python experiments/mvp_validation/experiment.py
```

Required environment variable: `DEEPSEEK_API_KEY`. Optional: `GITHUB_TOKEN`.
The source TXT is extracted to `/tmp` by the runner and is never copied into Git.
All generated files are under this directory. The script caches API responses in
`output/cache/` and writes metrics and the final report under `output/`.
