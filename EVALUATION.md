# Evaluation

This project includes a full evaluation package aligned with the final-project rubric: a 20-question test set, retrieval metrics, generation evaluation, a two-configuration comparison, and documented failure cases with root-cause analysis.

## 1. Test Set

The main evaluation file is:

- `evaluation/testset.json`

It contains 20 evaluation questions. Each item includes:
- `id`
- `query`
- `route_expected`
- `ground_truth_answer`
- `expected_sources`

The goal of the test set is to check both retrieval quality and end-to-end answer quality across crop, pest, soil, irrigation, and market questions.

## 2. Retrieval Evaluation

Run:

```bash
docker compose exec agent-system-a python /app/scripts/evaluate_retrieval.py
```

The retrieval script evaluates:
- Precision@K
- Recall@K
- MRR

### Baseline Retrieval Results

Configuration:
- Embedding provider: `local_deterministic`
- Embedding model: `local-deterministic-v2`
- `top_k = 5`
- `chunk_size = 900`
- `chunk_overlap = 180`

Results:
- Precision@5 = **0.15**
- Recall@5 = **0.60**
- MRR = **0.4517**
- Question count = **20**

### Interpretation

The retrieval system usually finds at least one relevant source for many questions, which is why recall is moderate. However, precision is still low, meaning the top retrieved chunks often include irrelevant or weakly related documents. This indicates that retrieval is functional but still noisy, especially for pest, irrigation, and abstract market questions.

## 3. Generation Evaluation

Run:

```bash
docker compose exec agent-system-a python /app/scripts/evaluate_generation.py
```

The packaged build uses a heuristic evaluator based on:
- answer overlap with the reference answer
- coverage of expected evidence sources

Tracked metrics:
- faithfulness
- correctness
- relevance

### Baseline Generation Results

Configuration:
- `top_k = 5`
- `chunk_size = 900`
- `chunk_overlap = 180`

Results:
- Faithfulness = **0.55**
- Correctness = **0.431**
- Relevance = **0.4667**
- Question count = **20**

### Interpretation

The generation layer is partially grounded, but performance is uneven. The system performs much better when it retrieves the correct crop or market guide and worse when routing sends the query down the wrong specialist path or when web fallback dominates the answer.

## 4. Configuration Comparison

Run:

```bash
docker compose exec agent-system-a python /app/scripts/compare_configs.py
```

Two configurations were compared.

### Profile A: `baseline_localdet_top5_900_180`

Environment:
- `EMBEDDING_PROVIDER=local_deterministic`
- `TOP_K=5`
- `RAG_CHUNK_SIZE=900`
- `RAG_CHUNK_OVERLAP=180`

Retrieval:
- Precision@5 = **0.15**
- Recall@5 = **0.60**
- MRR = **0.4517**

Generation:
- Faithfulness = **0.55**
- Correctness = **0.431**
- Relevance = **0.4667**

### Profile B: `baseline_localdet_top3_700_120`

Environment:
- `EMBEDDING_PROVIDER=local_deterministic`
- `TOP_K=3`
- `RAG_CHUNK_SIZE=700`
- `RAG_CHUNK_OVERLAP=120`

Retrieval:
- Precision@3 = **0.2166**
- Recall@3 = **0.65**
- MRR = **0.5092**

Generation:
- Faithfulness = **0.55**
- Correctness = **0.502**
- Relevance = **0.5164**

## 5. Best Configuration

The stronger configuration was:

- `TOP_K = 3`
- `RAG_CHUNK_SIZE = 700`
- `RAG_CHUNK_OVERLAP = 120`

This configuration improved:
- retrieval precision
- retrieval recall
- mean reciprocal rank
- generation correctness
- generation relevance

Faithfulness remained unchanged, but overall answer quality improved. This suggests that the smaller chunk size and lower top-k reduced retrieval noise and produced more focused grounding.

## 6. Documented Failure Cases

### Failure Case 1: Olive irrigation question failed retrieval

**Query:**  
`For olives, when is irrigation especially important for high yield?`

**Expected route:**  
`crop`, `irrigation`

**Expected source:**  
`crops/02_fao_olive_crop_info.md`

**Observed issue:**  
Retrieval failed to return the gold source in the top results. Retrieval metrics for this item were:
- Precision = 0.0
- Recall = 0.0
- MRR = 0.0

**Root cause:**  
The irrigation framing appears to bias retrieval toward generic irrigation and soil materials instead of the olive crop guide. This suggests weak query-to-document alignment for olive-specific irrigation wording.

**What this means:**  
The system can answer many tomato questions reasonably well, but olive irrigation remains a weak spot in both retrieval and downstream answer grounding.

---

### Failure Case 2: Early blight question was routed poorly

**Query:**  
`How can early blight pressure be reduced in tomato?`

**Expected route:**  
`pest`

**Expected source:**  
`pests/03_curated_tomato_pests_and_diseases.md`

**Observed issue:**  
The actual end-to-end route drifted toward crop-focused handling, and retrieval missed the expected pest document entirely. Retrieval metrics for this item were:
- Precision = 0.0
- Recall = 0.0
- MRR = 0.0

**Root cause:**  
The routing and retrieval behavior appear to overweight the token “tomato” and underweight “early blight” as a disease-specific signal. As a result, the system retrieves general tomato crop material rather than the disease guide.

**What this means:**  
Domain routing still needs stronger disease-term awareness, especially for symptom and pathogen questions.

---

### Failure Case 3: Harvest-versus-hold abstract phrasing confused retrieval

**Query:**  
`What kind of answer should the assistant give for harvest-versus-hold decisions?`

**Expected route:**  
`market`

**Expected source:**  
`market/05_curated_harvest_or_hold_rules.md`

**Observed issue:**  
Although the market route is conceptually appropriate, retrieval missed the gold source and instead surfaced unrelated materials. Retrieval metrics for this item were:
- Precision = 0.0
- Recall = 0.0
- MRR = 0.0

**Root cause:**  
This query is abstract and meta-level. It does not directly resemble the wording of the curated market rules, so dense retrieval is distracted by other documents with loosely related planning language.

**What this means:**  
The system handles concrete market questions better than abstract phrasing about decision style or answer style.

## 7. Additional Weak Cases Observed

Other questions that showed weak retrieval or weak end-to-end performance include:
- whiteflies on tomatoes
- aphids on tomato young growth
- practical tomato irrigation style
- tomato pH range phrased indirectly
- drip irrigation suitability for tomato

These cases reinforce the same pattern: the system is stronger on direct factual crop-guide queries than on disease-specific, abstract, or cross-topic questions.

## 8. Main Findings

The evaluation supports five important conclusions:

1. The system is operational and measurable across 20 questions.
2. Retrieval is functional but still noisy.
3. End-to-end answer quality depends heavily on routing quality and whether the right corpus document is retrieved early.
4. A smaller chunk size with lower top-k performed better than the larger baseline configuration.
5. The project demonstrates real engineering iteration because the configuration comparison led to a measurable improvement rather than a purely subjective preference.

## 9. What to Show in the Demo

For the presentation, the best sequence is:

1. Run retrieval evaluation
2. Run generation evaluation
3. Run configuration comparison
4. Show one strong example
5. Show one failure case honestly and explain the root cause

A good demo should emphasize not only what worked, but also what failed, why it failed, and how the evaluation results guided improvements.

## 10. Recommended Next Improvements

The most useful next improvements would be:

- strengthen routing for disease and irrigation questions
- reduce retrieval noise with better filtering or reranking
- expand crop-specific irrigation coverage beyond tomato
- replace the heuristic generation scorer with a true LLM-as-judge evaluator
- improve follow-up query handling for short contextual questions

## 11. Summary

This project satisfies the evaluation requirement by including:
- a 20-question grounded test set
- retrieval metrics
- generation evaluation
- a two-configuration comparison
- documented failure analysis

The evaluation also shows that the system is not only functional, but improvable in a measurable way, which is a core sign of mature RAG and agent-system design.
