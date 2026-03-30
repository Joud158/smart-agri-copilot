from __future__ import annotations

import re
from typing import Any


def _normalize_text(text: str) -> str:
    return " ".join(str(text).replace("m²", "m2").replace("mÂ²", "m2").lower().split())


def _parse_float(patterns: list[str], text: str) -> float | None:
    normalized = _normalize_text(text)
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if match:
            return float(match.group(1))
    return None


def _parse_area_m2(text: str, explicit_area: float | None = None) -> float | None:
    if explicit_area is not None:
        return float(explicit_area)
    normalized = _normalize_text(text)
    for pattern, multiplier in [
        (r"(\d+(?:\.\d+)?)\s*(?:m2|sqm|square meters?|square metres?)", 1.0),
        (r"(\d+(?:\.\d+)?)\s*(?:hectares?|ha)", 10_000.0),
    ]:
        match = re.search(pattern, normalized)
        if match:
            return round(float(match.group(1)) * multiplier, 2)
    return None


def _parse_soil_ph(text: str, explicit_ph: float | None = None) -> float | None:
    if explicit_ph is not None:
        return float(explicit_ph)
    return _parse_float([r"(?:soil\s*)?ph\s*(?:is|=|:)?\s*(\d(?:\.\d+)?)"], text)


def _parse_organic_matter(text: str, explicit_om: float | None = None) -> float | None:
    if explicit_om is not None:
        return float(explicit_om)
    return _parse_float([
        r"(?:organic matter|om)\s*(?:is|=|:)?\s*(\d+(?:\.\d+)?)\s*%",
        r"(\d+(?:\.\d+)?)\s*%\s*(?:organic matter|om)",
    ], text)


def _parse_texture(text: str, explicit_texture: str | None = None) -> str:
    if explicit_texture:
        return explicit_texture.lower()
    normalized = _normalize_text(text)
    for texture in ("sandy", "sand", "loam", "loamy", "clay", "clayey", "silt", "silty"):
        if re.search(rf"(?<!\w){texture}(?!\w)", normalized):
            return texture.replace("y", "") if texture.endswith("y") else texture
    return "loam"


def _parse_month(text: str, explicit_month: str | None = None) -> str:
    if explicit_month:
        return explicit_month.lower()
    normalized = _normalize_text(text)
    for month in ("june", "july", "august", "september", "october"):
        if re.search(rf"(?<!\w){month}(?!\w)", normalized):
            return month
    return "july"


def analyze_soil(soil_ph: float, organic_matter_pct: float | None = None, texture: str = "loam") -> dict[str, Any]:
    if soil_ph < 5.5:
        ph_label = "acidic"
        ph_note = "Many crops may face stress unless they are adapted or the soil is amended."
    elif soil_ph <= 7.2:
        ph_label = "generally suitable"
        ph_note = "This pH is within a practical range for many crops."
    else:
        ph_label = "alkaline"
        ph_note = "Micronutrient availability can become more limiting at higher pH."

    om_note = "Organic matter not provided."
    if organic_matter_pct is not None:
        if organic_matter_pct < 1.5:
            om_note = "Organic matter is low; water retention and nutrient buffering may be limited."
        elif organic_matter_pct < 3.0:
            om_note = "Organic matter is moderate."
        else:
            om_note = "Organic matter is relatively strong for many cropped systems."

    texture_lookup = texture.lower()
    texture_note = {
        "sand": "Sandy soils drain quickly and may need more frequent, smaller irrigation events.",
        "sandy": "Sandy soils drain quickly and may need more frequent, smaller irrigation events.",
        "loam": "Loam is often a practical balance between drainage and retention.",
        "clay": "Clay soils retain more water but can face aeration and compaction issues.",
        "silt": "Silt soils can crust and compact if structure is weak; monitor infiltration."
    }.get(texture_lookup, "Texture provided should be interpreted alongside field structure and drainage.")

    return {
        "soil_ph": soil_ph,
        "ph_label": ph_label,
        "ph_note": ph_note,
        "organic_matter_note": om_note,
        "texture": texture_lookup,
        "texture_note": texture_note,
        "recommendation": "Use this as a planning interpretation only. Confirm with local soil testing before making a high-stakes amendment plan.",
    }


def calculate_fertilizer(crop: str, area_m2: float, soil_type: str = "loam") -> dict[str, Any]:
    crop_lower = crop.lower()
    base_table = {
        "tomato": {"fertilizer": "balanced NPK with stronger potassium emphasis near fruiting", "kg_per_1000m2": 40},
        "cucumber": {"fertilizer": "balanced fertigation plan with moderate potassium support", "kg_per_1000m2": 35},
        "grape": {"fertilizer": "moderate balanced nutrition; avoid excessive nitrogen", "kg_per_1000m2": 20},
        "olive": {"fertilizer": "moderate balanced nutrition adjusted to tree age and yield goal", "kg_per_1000m2": 18},
        "wheat": {"fertilizer": "nitrogen-focused plan with stage timing", "kg_per_1000m2": 25},
        "potato": {"fertilizer": "balanced program with strong potassium support", "kg_per_1000m2": 32},
    }
    chosen = base_table.get(crop_lower, {"fertilizer": "general balanced program", "kg_per_1000m2": 22})
    rate = chosen["kg_per_1000m2"] * (area_m2 / 1000.0)

    soil_modifier = {
        "sand": "Split applications more carefully because leaching risk is higher.",
        "sandy": "Split applications more carefully because leaching risk is higher.",
        "clay": "Watch drainage and salt buildup if irrigation is intensive.",
        "loam": "Use normal split planning with monitoring.",
        "silt": "Monitor sealing and runoff after irrigation or rainfall.",
    }.get(soil_type.lower(), "Adjust based on field observations and soil testing.")

    return {
        "crop": crop,
        "area_m2": area_m2,
        "soil_type": soil_type,
        "suggested_fertilizer_direction": chosen["fertilizer"],
        "estimated_total_kg_for_area": round(rate, 2),
        "soil_modifier": soil_modifier,
        "note": "Exact programs should be refined using soil and tissue tests when available.",
    }


def estimate_water_usage(crop: str, area_m2: float, month: str = "july") -> dict[str, Any]:
    crop_factor = {
        "tomato": 5.8,
        "cucumber": 5.5,
        "grape": 3.6,
        "olive": 2.8,
        "wheat": 4.0,
        "potato": 5.0,
    }.get(crop.lower(), 4.5)

    month_factor = {
        "june": 0.9,
        "july": 1.0,
        "august": 1.0,
        "september": 0.8,
        "october": 0.65,
    }.get(month.lower(), 1.0)

    liters_day = crop_factor * month_factor * area_m2
    return {
        "crop": crop,
        "area_m2": area_m2,
        "month": month,
        "estimated_liters_per_day": round(liters_day, 1),
        "note": "This is a planning estimate and should be adjusted for local weather, soil, and irrigation system efficiency.",
    }


def analyze_bundle(
    message: str,
    crop: str | None = None,
    region: str | None = None,
    growth_stage: str | None = None,
    area_m2: float | None = None,
    soil_ph: float | None = None,
    organic_matter_pct: float | None = None,
    soil_texture: str | None = None,
    month: str | None = None,
) -> dict[str, Any]:
    parsed_area = _parse_area_m2(message, area_m2) or 500.0
    parsed_ph = _parse_soil_ph(message, soil_ph) or 6.8
    parsed_om = _parse_organic_matter(message, organic_matter_pct)
    parsed_texture = _parse_texture(message, soil_texture)
    parsed_month = _parse_month(message, month)

    soil = analyze_soil(soil_ph=parsed_ph, organic_matter_pct=parsed_om, texture=parsed_texture)
    fert = calculate_fertilizer(crop or "general crop", area_m2=parsed_area, soil_type=parsed_texture)
    water = estimate_water_usage(crop or "general crop", area_m2=parsed_area, month=parsed_month)

    answer = (
        f"Soil interpretation: pH is treated as {soil['ph_label']} and {soil['ph_note']} "
        f"Fertilizer direction: {fert['suggested_fertilizer_direction']} with an estimated total of "
        f"{fert['estimated_total_kg_for_area']} kg for the referenced area. "
        f"Water planning baseline: about {water['estimated_liters_per_day']} liters/day in {parsed_month}."
    )

    return {
        "status": "ok",
        "answer": answer,
        "structured_result": {
            "soil": soil,
            "fertilizer": fert,
            "water": water,
            "region": region,
            "growth_stage": growth_stage,
            "parsed_inputs": {
                "area_m2": parsed_area,
                "soil_ph": parsed_ph,
                "organic_matter_pct": parsed_om,
                "soil_texture": parsed_texture,
                "month": parsed_month,
            },
        },
    }
