# Corpus Inventory — Smart Agriculture Advisor

## Goal
Build a domain RAG corpus for a Smart Agriculture Advisor focused on Lebanese and Mediterranean farming contexts.

## Planned Collections
1. crops
2. pests
3. soil_fertilizer
4. market

## Metadata Schema
- source_type
- source_title
- crop_name
- season
- region
- growth_stage
- pest_type
- soil_type
- topic
- file_status

---

## 1) crops

### Planned files
- fao_tomato_crop_info.md
- fao_olive_crop_info.md
- fao_wheat_crop_info.md
- greenhouse_vegetable_practices_mediterranean.md
- crop_water_requirements_general.md
- lebanon_crop_context.md

### What this collection should answer
- What can I plant?
- When should I plant or harvest?
- What soil and water conditions are suitable?
- Which crops fit Bekaa / coast / mountain conditions?

### Priority crops for MVP
- tomatoes
- olives
- wheat
- grapes
- cucumbers
- potatoes

---

## 2) pests

### Planned files
- tomato_common_pests_and_diseases.md
- cucumber_common_pests_and_diseases.md
- grape_common_pests_and_diseases.md
- wheat_common_pests_and_diseases.md
- ipm_general_principles.md
- symptom_to_likely_cause_index.md

### What this collection should answer
- What might be causing these symptoms?
- What are likely pests or diseases for this crop?
- What prevention and treatment options exist?
- What monitoring guidance should be followed?

### Priority pest topics for MVP
- aphids
- whiteflies
- powdery mildew
- early blight
- spider mites
- leaf spot / yellow spotting patterns

---

## 3) soil_fertilizer

### Planned files
- soil_ph_basics.md
- nutrient_availability_by_ph.md
- nutrient_management_basics.md
- fertilizer_recommendations_by_crop.md
- water_usage_estimation_notes.md
- soil_interpretation_rules.md

### What this collection should answer
- Is this soil suitable for this crop?
- What pH range is generally appropriate?
- What fertilizer type and amount should be suggested?
- How does pH affect nutrient availability?

### Priority topics for MVP
- pH interpretation
- NPK basics
- nutrient availability
- fertilizer planning
- soil suitability rules
- water-use estimation notes

---

## 4) market

### Planned files
- faostat_price_notes.md
- fao_price_monitoring_notes.md
- world_bank_commodity_notes.md
- post_harvest_storage_guidance.md
- harvest_or_hold_rules.md
- seasonal_price_trends_curated.csv

### What this collection should answer
- Is it better to harvest now or wait?
- What are seasonal price patterns?
- How should produce be stored?
- What lightweight market guidance can be given without pretending to predict prices?

### MVP market scope
- seasonal trends only
- storage guidance
- harvest-or-hold suggestions
- no real-time local trading feed

---

## File Status Legend
- planned
- collecting
- cleaned
- chunked
- embedded
- loaded_to_qdrant

## Current Status
All files: planned