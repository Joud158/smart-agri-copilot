# Evaluation

This project includes an evaluation package aligned with the rubric.

## 1. Test Set

The main evaluation file is:

- `evaluation/testset.json`

It contains 20 questions, each with:
- query
- expected route
- grounded answer
- expected source references

## 2. Retrieval Metrics

Run:

```bash
docker compose exec agent-system-a python /app/scripts/evaluate_retrieval.py
```

Metrics:
- Precision@K
- Recall@K
- MRR

The script reads `evaluation/testset.json` and evaluates the indexed corpus in Qdrant.

## 3. Generation Evaluation

Run:

```bash
docker compose exec agent-system-a python /app/scripts/evaluate_generation.py
```

Default packaged mode:
- heuristic scorer based on answer overlap and source coverage

Recommended extension for final polishing:
- swap the judge logic to a true LLM-as-judge when an API-backed model is available

Tracked metrics:
- faithfulness
- correctness
- relevance

## 4. Configuration Comparison

Run:

```bash
docker compose exec agent-system-a python /app/scripts/compare_configs.py
```

Current comparison profiles:
1. `baseline_localdet_top5_900_180`
2. `baseline_localdet_top3_700_120`

This gives you the 2-configuration comparison required by the rubric.

## 5. Documented Failure Cases

### Failure Case 1: Yellow spotting is ambiguous
**Example query:** “My tomato leaves have yellow spots. What disease is it?”

**What can go wrong:**
The symptom is under-specified. The corpus itself warns that yellow spotting alone is not enough for confident diagnosis.

**Likely root cause:**
The user query lacks location, growth stage, distribution pattern, and whether spotting is uniform or patchy.

**What the system should do:**
Ask a follow-up question or explicitly state uncertainty instead of pretending certainty.

### Failure Case 2: Exact irrigation numbers can overfit to defaults
**Example query:** “How many liters exactly do I need per day?”

**What can go wrong:**
If area, month, or growth stage are missing, Agent B falls back to planning assumptions.

**Likely root cause:**
The calculation engine needs structured inputs but the user provided only a vague question.

**What the system should do:**
State the assumption clearly and encourage the user to provide crop, region, stage, and area.

### Failure Case 3: Market timing can never be fully certain
**Example query:** “Should I always hold my crop because prices may rise next month?”

**What can go wrong:**
The system can retrieve harvest/hold logic, but the decision still depends on perishability, storage, and risk.

**Likely root cause:**
The task is inherently conditional; the retrieval evidence supports trade-offs, not a guaranteed forecast.

**What the system should do:**
Explain trade-offs rather than output false certainty.

## 6. Interpreting Results

When presenting, focus on:
- whether expected sources were retrieved
- whether the route chosen by Agent A matched the route expected in the test set
- whether the answer stayed grounded and cautious when evidence was incomplete

## 7. What to Show in the Demo

- run retrieval evaluation
- run generation evaluation
- run config comparison
- open one failure case and explain the root cause honestly
