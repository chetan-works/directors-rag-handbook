# Evaluation

The golden dataset at `data/eval/golden.jsonl` is a small, human-readable regression suite. Each case
contains a stable ID, a question, concepts expected in a useful answer, and expected source IDs.

## Metrics

- **Answer relevance** combines expected-phrase recall with question/answer lexical overlap.
- **Citation recall** checks whether expected sources appeared in the returned evidence.
- **Citation validity** checks that answer citation numbers exist in the returned citation list.
- **Groundedness** combines answer/context term overlap and citation validity.
- **Latency** measures the full local request and helps catch expensive prompt/model changes.
- **Pass rate** requires minimum relevance, citation recall, and groundedness per case.

## Correct interpretation

These metrics are inexpensive, deterministic regression signals. Lexical overlap can reward copying,
miss valid paraphrases, and cannot prove factual entailment. Citation presence does not prove that a
source supports the exact preceding claim. Do not market the scores as comprehensive model quality.

Before production, add expert-written reference answers, adversarial and unanswerable questions,
faithfulness labels at the claim level, retrieval recall@k, and a separately governed model-based
judge. Keep judge prompts/version/model outputs so runs remain auditable.

## Adding a case

Add one JSON object on a new line:

```json
{"id":"unique-id","question":"A focused question","expected_terms":["term"],"expected_source_ids":["catalog-id"]}
```

Ingest the relevant sources, run all three strategies, inspect the evidence—not just the score—and
commit the case with the prompt/model change it protects.
