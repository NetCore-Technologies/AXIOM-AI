# Offline Evaluation

AXIOM can score **already-produced** model outputs in local JSONL files. It does
not load a model or run inference. Each selected row must contain string values
for a prediction field and a reference field. Optional split filtering limits
scoring to rows whose split field equals the selected split value.

## Metrics

- **Exact match:** fraction of selected samples whose prediction exactly equals
  the reference, including case and whitespace.
- **Normalized exact match:** fraction equal after Unicode case folding and
  collapsing whitespace runs to one space.
- **Micro token precision/recall/F1:** whitespace-token multisets are compared
  case-insensitively across all samples; overlap counts repeated tokens.

Every report includes the valid sample count, skipped/invalid row counts,
bounded scan limits, selected fields and split, and a content SHA-256 when the
entire stable file was read. Raw prediction and reference strings are neither
returned nor persisted. A scan limit may produce partial metrics; reports label
the scan as partial and carry the truncation causes.

## Baselines and regression gates

Create an immutable baseline report, then select it for a later run. Comparisons
are allowed only when the report uses the same fully hashed dataset, reference
field, and split. The selected metric and allowed absolute score drop are stored
with the comparison result. A failed gate means the score dropped beyond that
threshold; it does not infer statistical significance or replace human review.

## CLI

```bash
axiom evaluation run ./data/eval.jsonl \
  --prediction-field prediction --reference-field reference --split-field split \
  --split-value test --baseline --json
axiom evaluation list --json
axiom evaluation show <run-id>
axiom evaluation delete <run-id>
```

Evaluation history is local in `.axiom/evaluations.json`, bounded to 1,000
records and 4 MB. Deleting a report never changes its dataset.
