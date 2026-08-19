# Recommendation Evaluation Dataset

`data/recommendation_eval_cases.json` stores recommendation policies as user scenarios.
Each case defines the input, the RAG chunks assumed to be retrieved, and tag-level constraints.
The tests intentionally do not require exact song titles because music recommendation is subjective.

Run the deterministic regression evaluation without Gemini or Spotify API calls:

```bash
PYTHONPATH=server server/.venv/bin/python -m unittest discover -s server/tests -v
```

Add a case whenever a recommendation feels mismatched. Prefer constraints such as
`must_exclude_tags` and `must_include_any_tags` over pinning a specific track.
