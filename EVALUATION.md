# Evaluation Plan and Submission Template

The rubric requires:
- a **20+ question** test set
- retrieval metrics
- generation evaluation
- at least **2 configuration comparisons**
- **3 documented failure cases**. fileciteturn2file6

This file gives you a ready structure to fill after running the project.

## 1) Test Set

| ID | User Query | Expected Route | Ground Truth Summary | Gold Sources |
|---|---|---|---|---|
| Q01 | I want to plant tomatoes in Bekaa. What should I check first? | crop | Tomato prefers warm conditions, well-drained light loam, and careful frost/water management. | crops/tomato, crops/lebanon_context |
| Q02 | My tomato leaves have yellow spots. What could it be? | pest | Multiple possibilities: mites, whiteflies, nutrient issue, early disease. Need clarification. | pests/tomato, pests/symptom_index |
| Q03 | Tomatoes at flowering stage, 800 m² in Bekaa. How much water this week? | irrigation | Weekly irrigation estimate should account for crop, area, stage, region profile. | soil/water docs + agent-b |
| Q04 | Is pH 8.1 okay for cucumber? | soil | High pH can reduce micronutrient availability; practical caution needed. | soil/ph_basics, soil/fertility |
| Q05 | Should I harvest tomatoes now or wait? | market | Depends on perishability, current quality, storage, disease/weather risk, and seasonal trend. | market/seasonal_rules |
| Q06 | Compare tomato and grape irrigation sensitivity. | crop + irrigation | Tomato flowering/fruiting is water-sensitive; grapes need more controlled irrigation logic. | tomato + grape guides |
| Q07 | What fertilizer direction makes sense for tomatoes around fruiting? | soil | Potassium importance rises around flowering/fruiting; use soil testing where possible. | tomato guide + fertilizer planning |
| Q08 | White insects fly when I disturb cucumber plants. What does that suggest? | pest | Whiteflies are a strong possibility; use traps, hygiene, and scouting. | pests/tomato or greenhouse IPM |
| Q09 | I have wheat. What market factors matter most? | market | Storage feasibility and moisture control matter more than short freshness windows. | market/simulated trends |
| Q10 | Give me an action plan for greenhouse hygiene. | pest | Prevention, sanitation, screening, scouting, sticky traps, record keeping. | greenhouse IPM |
| Q11 | Which region is more humidity-sensitive for disease, coast or Bekaa? | crop | Coastal humidity raises disease pressure more often than inland dry zones. | lebanon crop context |
| Q12 | What is a safe way to interpret sticky residue on leaves? | pest | It suggests sap-feeding insects like aphids/whiteflies but needs confirmation. | symptom index |
| Q13 | What should I ask before diagnosing yellow leaves? | pest | Crop, stage, region, open field vs greenhouse, uniform vs patchy, insects/powder/residue. | symptom index |
| Q14 | Estimate daily water requirement for tomatoes on 500 m² in July. | mcp | Use MCP water estimation rules. | MCP estimate_water_usage |
| Q15 | Analyze soil with pH 5.2, low organic matter, sandy texture. | mcp | Soil is acidic and low-retention; needs amendment and careful nutrition planning. | MCP analyze_soil |
| Q16 | How does pH affect nutrients? | soil | pH changes nutrient availability and microbial activity. | soil fertility docs |
| Q17 | Give me a complete answer for tomatoes with yellow spots and irrigation concerns. | multi-route | Should combine pest RAG + irrigation service + soil/fertilizer notes. | multiple |
| Q18 | Can I rely on this system for a final pesticide prescription? | guardrail | No; it is decision support, not a substitute for certified agronomist advice. | policy/output guardrail |
| Q19 | What if Agent B is down? | resilience | Primary system should degrade gracefully and state what could not be computed. | fallback behavior |
| Q20 | What storage trade-offs matter for tomatoes? | market | High perishability reduces the value of waiting without strong cold-chain support. | storage docs |
| Q21 | Tell me today’s exact local tomato market price in Lebanon. | guardrail + market | System should explain that it provides seasonal guidance, not live price certainty. | market docs |

## 2) Retrieval Metrics Template

Compute:
- Precision@K
- Recall@K
- MRR

| Config | Chunk Size | Overlap | Top K | P@K | R@K | MRR | Notes |
|---|---:|---:|---:|---:|---:|---:|---|
| A | 650 | 120 | 4 | TBD | TBD | TBD | Default |
| B | 950 | 150 | 4 | TBD | TBD | TBD | Larger chunk baseline |
| C | 650 | 120 | 6 | TBD | TBD | TBD | Higher recall attempt |

## 3) Generation Evaluation Template

| Query ID | Faithfulness | Correctness | Relevance | Notes |
|---|---:|---:|---:|---|
| Q01 | TBD | TBD | TBD | |
| Q02 | TBD | TBD | TBD | |
| Q03 | TBD | TBD | TBD | |
| ... | ... | ... | ... | |

## 4) Configuration Comparison Conclusions

### Comparison 1 — Chunk size
- **A:** 650 / 120
- **B:** 950 / 150

Hypothesis:
Smaller chunks should improve symptom-level retrieval because agronomic sections are often compact and topic-dense.

### Comparison 2 — Top-K
- **A:** K=4
- **B:** K=6

Hypothesis:
K=6 may improve recall, but may introduce more noise in multi-topic answers.

## 5) Failure Cases

### Failure Case 1 — Overbroad symptom query
**Query:** “Leaves are yellow. What disease is it?”  
**Problem:** insufficient context.  
**Root cause:** input ambiguity, not retrieval failure.  
**Fix:** clarification-first guardrail.

### Failure Case 2 — Market precision request
**Query:** “What is today’s exact tomato price in Tripoli?”  
**Problem:** system only has seasonal guidance, not live local price feed.  
**Root cause:** data scope mismatch.  
**Fix:** explicit scope statement + future live feed integration.

### Failure Case 3 — Service dependency unavailable
**Query:** irrigation query while Agent B is offline.  
**Problem:** cross-service dependency failure.  
**Root cause:** network/service availability.  
**Fix:** timeout handling + degraded response + retry / circuit-breaker in future version.

