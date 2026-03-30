from __future__ import annotations

import re
from typing import Any

REGION_PROFILES = {
    "bekaa": {"eto_mm_day": 6.2, "frost_risk": "moderate"},
    "coast": {"eto_mm_day": 4.8, "frost_risk": "low"},
    "mountain": {"eto_mm_day": 4.2, "frost_risk": "high"},
    "mountains": {"eto_mm_day": 4.2, "frost_risk": "high"},
    "lebanon": {"eto_mm_day": 5.0, "frost_risk": "variable"},
}

REGION_ALIASES = {
    "bekaa": "bekaa",
    "beqaa": "bekaa",
    "coast": "coast",
    "coastal": "coast",
    "mountain": "mountain",
    "mountains": "mountains",
    "lebanon": "lebanon",
}

CROP_STAGE_FACTORS = {
    "tomato": {"seedling": 0.55, "vegetative": 0.85, "flowering": 1.05, "fruiting": 1.1, "full_cycle": 0.9},
    "cucumber": {"seedling": 0.55, "vegetative": 0.9, "flowering": 1.0, "fruiting": 1.05, "full_cycle": 0.9},
    "grape": {"seedling": 0.45, "vegetative": 0.65, "flowering": 0.8, "fruiting": 0.75, "full_cycle": 0.7},
    "olive": {"seedling": 0.35, "vegetative": 0.45, "flowering": 0.55, "fruiting": 0.6, "full_cycle": 0.5},
    "wheat": {"seedling": 0.4, "vegetative": 0.75, "flowering": 0.95, "fruiting": 0.8, "full_cycle": 0.7},
    "potato": {"seedling": 0.6, "vegetative": 0.85, "flowering": 1.0, "fruiting": 1.0, "full_cycle": 0.9},
    "default": {"seedling": 0.5, "vegetative": 0.8, "flowering": 0.95, "fruiting": 1.0, "full_cycle": 0.8},
}

MONTH_FACTORS = {
    "june": 0.9,
    "july": 1.0,
    "august": 1.0,
    "september": 0.85,
    "october": 0.7,
}

CROP_ALIASES = {
    "tomatoes": "tomato",
    "tomato": "tomato",
    "cucumbers": "cucumber",
    "cucumber": "cucumber",
    "grapes": "grape",
    "grape": "grape",
    "olives": "olive",
    "olive": "olive",
    "wheat": "wheat",
    "potatoes": "potato",
    "potato": "potato",
}


def _normalize_text(text: str) -> str:
    return " ".join(str(text).replace("m²", "m2").replace("mÂ²", "m2").replace(",", " ").lower().split())


def _extract_alias(text: str, alias_map: dict[str, str]) -> str | None:
    normalized = _normalize_text(text)
    for alias, canonical in sorted(alias_map.items(), key=lambda item: len(item[0]), reverse=True):
        if re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", normalized):
            return canonical
    return None


def _extract_area_m2(text: str) -> float | None:
    normalized = _normalize_text(text)
    for pattern, multiplier in [
        (r"(\d+(?:\.\d+)?)\s*(?:m2|sqm|square meters?|square metres?)", 1.0),
        (r"(\d+(?:\.\d+)?)\s*(?:ha|hectares?)", 10_000.0),
    ]:
        match = re.search(pattern, normalized)
        if match:
            return round(float(match.group(1)) * multiplier, 2)
    return None


def _extract_month(text: str) -> str | None:
    normalized = _normalize_text(text)
    for month in MONTH_FACTORS:
        if re.search(rf"(?<!\w){month}(?!\w)", normalized):
            return month
    return None


def extract_request_context(message: str, metadata: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_text(message)
    crop = metadata.get("crop") or _extract_alias(normalized, CROP_ALIASES)
    region = metadata.get("region") or _extract_alias(normalized, REGION_ALIASES)
    stage = metadata.get("growth_stage") or next(
        (stage_name for stage_name in ["seedling", "vegetative", "flowering", "fruiting", "harvest", "full_cycle"] if stage_name in normalized),
        None,
    )
    area_m2 = metadata.get("area_m2") or _extract_area_m2(normalized)
    month = metadata.get("month") or _extract_month(normalized)
    return {
        "crop": crop,
        "region": region,
        "growth_stage": stage,
        "area_m2": float(area_m2) if area_m2 is not None else None,
        "month": month,
    }


def _get_region_profile(region: str | None) -> dict[str, Any]:
    if not region:
        return REGION_PROFILES["lebanon"]
    return REGION_PROFILES.get(region.lower(), REGION_PROFILES["lebanon"])


def _get_kc(crop: str | None, stage: str | None) -> float:
    crop_key = (crop or "default").lower()
    stage_key = (stage or "full_cycle").lower()
    crop_map = CROP_STAGE_FACTORS.get(crop_key, CROP_STAGE_FACTORS["default"])
    return crop_map.get(stage_key, crop_map["full_cycle"])


def calculate_irrigation_plan(crop: str | None, region: str | None, growth_stage: str | None, area_m2: float | None, month: str | None = None) -> dict[str, Any]:
    profile = _get_region_profile(region)
    kc = _get_kc(crop, growth_stage)
    eto = profile["eto_mm_day"] * MONTH_FACTORS.get((month or "").lower(), 1.0)
    etc = round(eto * kc, 2)

    area = area_m2 or 1000.0
    liters_day = round(etc * area, 1)
    liters_week = round(liters_day * 7, 1)

    if area_m2 is None:
        area_note = "Area was not explicitly provided, so a 1000 m² planning baseline was used."
    else:
        area_note = "Area came from the user request or carried metadata."

    return {
        "crop": crop or "unspecified crop",
        "region": region or "unspecified region",
        "growth_stage": growth_stage or "unspecified stage",
        "month": month or "general season",
        "eto_mm_day": round(eto, 2),
        "kc": kc,
        "etc_mm_day": etc,
        "area_m2": area,
        "estimated_liters_per_day": liters_day,
        "estimated_liters_per_week": liters_week,
        "area_note": area_note,
    }


def assess_frost_risk(region: str | None, growth_stage: str | None) -> dict[str, Any]:
    profile = _get_region_profile(region)
    base = profile["frost_risk"]

    if base == "high":
        advisory = "Plan early-morning inspection and protect sensitive crops during cold spells."
    elif base == "moderate":
        advisory = "Monitor forecast swings and protect sensitive flowering crops if temperatures drop sharply."
    else:
        advisory = "Frost risk is generally lower, but vulnerable crops should still be checked in exposed locations."

    return {
        "region": region or "unspecified region",
        "growth_stage": growth_stage or "unspecified stage",
        "frost_risk": base,
        "advisory": advisory,
    }


def estimate_spray_window(region: str | None) -> dict[str, Any]:
    profile = _get_region_profile(region)
    eto = profile["eto_mm_day"]

    if eto >= 6.0:
        window = "Prefer early morning or late afternoon to reduce evaporation and drift."
    elif eto >= 5.0:
        window = "Use calm, cooler parts of the day and avoid peak heat."
    else:
        window = "A wider spray window may be available, but avoid windy or wet periods."

    return {"region": region or "unspecified region", "spray_timing_guidance": window}


def build_irrigation_answer(message: str, metadata: dict[str, Any]) -> dict[str, Any]:
    context = extract_request_context(message, metadata)
    irrigation = calculate_irrigation_plan(
        context["crop"],
        context["region"],
        context["growth_stage"],
        context["area_m2"],
        context["month"],
    )
    frost = assess_frost_risk(context["region"], context["growth_stage"])
    spray = estimate_spray_window(context["region"])

    answer = (
        f"For {irrigation['crop']} in {irrigation['region']} at {irrigation['growth_stage']}, "
        f"the planning estimate is about {irrigation['estimated_liters_per_day']} liters/day "
        f"and {irrigation['estimated_liters_per_week']} liters/week for {irrigation['area_m2']} m². "
        f"{irrigation['area_note']} Frost risk is {frost['frost_risk']}. {frost['advisory']} "
        f"{spray['spray_timing_guidance']}"
    )

    return {
        "answer": answer,
        "mode": "deterministic",
        "structured_result": {
            "request_context": context,
            "irrigation": irrigation,
            "frost": frost,
            "spray": spray,
        },
    }
