from __future__ import annotations

import math
from typing import Any


REGION_PROFILES = {
    "bekaa": {"eto_mm_day": 6.2, "frost_risk": "moderate"},
    "coast": {"eto_mm_day": 4.8, "frost_risk": "low"},
    "mountain": {"eto_mm_day": 4.2, "frost_risk": "high"},
    "mountains": {"eto_mm_day": 4.2, "frost_risk": "high"},
    "lebanon": {"eto_mm_day": 5.0, "frost_risk": "variable"},
}

CROP_STAGE_FACTORS = {
    "tomato": {"seedling": 0.55, "vegetative": 0.85, "flowering": 1.05, "fruiting": 1.1, "full_cycle": 0.9},
    "cucumber": {"seedling": 0.55, "vegetative": 0.9, "flowering": 1.0, "fruiting": 1.05, "full_cycle": 0.9},
    "grape": {"seedling": 0.45, "vegetative": 0.65, "flowering": 0.8, "fruiting": 0.75, "full_cycle": 0.7},
    "olive": {"seedling": 0.35, "vegetative": 0.45, "flowering": 0.55, "fruiting": 0.6, "full_cycle": 0.5},
    "wheat": {"seedling": 0.4, "vegetative": 0.75, "flowering": 0.95, "fruiting": 0.8, "full_cycle": 0.7},
    "default": {"seedling": 0.5, "vegetative": 0.8, "flowering": 0.95, "fruiting": 1.0, "full_cycle": 0.8},
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


def calculate_irrigation_plan(crop: str | None, region: str | None, growth_stage: str | None, area_m2: float | None) -> dict[str, Any]:
    """Simple agronomic-style irrigation estimate.

    Formula:
    ETc = ETo * Kc
    liters/day ≈ ETc(mm/day) * area(m²)

    This is intentionally approximate and should be explained as a planning estimate,
    not an exact agronomic prescription.
    """

    profile = _get_region_profile(region)
    kc = _get_kc(crop, growth_stage)
    eto = profile["eto_mm_day"]
    etc = round(eto * kc, 2)

    area = area_m2 or 1000.0
    liters_day = round(etc * area, 1)
    liters_week = round(liters_day * 7, 1)

    return {
        "crop": crop or "unspecified crop",
        "region": region or "unspecified region",
        "growth_stage": growth_stage or "unspecified stage",
        "eto_mm_day": eto,
        "kc": kc,
        "etc_mm_day": etc,
        "area_m2": area,
        "estimated_liters_per_day": liters_day,
        "estimated_liters_per_week": liters_week,
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

    return {
        "region": region or "unspecified region",
        "spray_timing_guidance": window,
    }


def build_irrigation_answer(message: str, metadata: dict[str, Any]) -> dict[str, Any]:
    crop = metadata.get("crop")
    region = metadata.get("region")
    stage = metadata.get("growth_stage")
    area_m2 = _extract_area(message)

    irrigation = calculate_irrigation_plan(crop, region, stage, area_m2)
    frost = assess_frost_risk(region, stage)
    spray = estimate_spray_window(region)

    answer = (
        f"For {irrigation['crop']} in {irrigation['region']} at {irrigation['growth_stage']}, "
        f"the planning estimate is about {irrigation['estimated_liters_per_day']} liters/day "
        f"and {irrigation['estimated_liters_per_week']} liters/week for {irrigation['area_m2']} m². "
        f"Frost risk is {frost['frost_risk']}. {frost['advisory']} {spray['spray_timing_guidance']}"
    )

    return {
        "answer": answer,
        "mode": "deterministic",
        "structured_result": {
            "irrigation": irrigation,
            "frost": frost,
            "spray": spray,
        },
    }


def _extract_area(message: str) -> float | None:
    lowered = message.lower().replace(",", "")
    tokens = lowered.split()

    for index, token in enumerate(tokens):
        if token.endswith("m²"):
            try:
                return float(token.replace("m²", ""))
            except ValueError:
                continue

        if token in {"m2", "square", "sqm"} and index > 0:
            try:
                return float(tokens[index - 1])
            except ValueError:
                continue

    return None
