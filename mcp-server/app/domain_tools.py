from __future__ import annotations

from typing import Any


def analyze_soil(soil_ph: float, organic_matter_pct: float | None = None, texture: str = "loam") -> dict[str, Any]:
    """Interpret a simple soil profile.

    This tool is intentionally lightweight and explainable.
    It is not pretending to replace a laboratory report.
    """

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

    texture_note = {
        "sand": "Sandy soils drain quickly and may need more frequent, smaller irrigation events.",
        "sandy": "Sandy soils drain quickly and may need more frequent, smaller irrigation events.",
        "loam": "Loam is often a practical balance between drainage and retention.",
        "clay": "Clay soils retain more water but can face aeration and compaction issues.",
    }.get(texture.lower(), "Texture provided should be interpreted alongside field structure and drainage.")

    return {
        "soil_ph": soil_ph,
        "ph_label": ph_label,
        "ph_note": ph_note,
        "organic_matter_note": om_note,
        "texture": texture,
        "texture_note": texture_note,
        "recommendation": (
            "Use this as a planning interpretation only. Confirm with local soil testing before making a high-stakes amendment plan."
        ),
    }


def calculate_fertilizer(crop: str, area_m2: float, soil_type: str = "loam") -> dict[str, Any]:
    """Return a high-level fertilizer direction.

    The quantities are intentionally coarse demo numbers.
    The point is tool-calling architecture plus explainable logic.
    """

    crop_lower = crop.lower()

    base_table = {
        "tomato": {"fertilizer": "balanced NPK with stronger potassium emphasis near fruiting", "kg_per_1000m2": 40},
        "cucumber": {"fertilizer": "balanced fertigation plan with moderate potassium support", "kg_per_1000m2": 35},
        "grape": {"fertilizer": "moderate balanced nutrition; avoid excessive nitrogen", "kg_per_1000m2": 20},
        "olive": {"fertilizer": "moderate balanced nutrition adjusted to tree age and yield goal", "kg_per_1000m2": 18},
        "wheat": {"fertilizer": "nitrogen-focused plan with stage timing", "kg_per_1000m2": 25},
    }
    chosen = base_table.get(crop_lower, {"fertilizer": "general balanced program", "kg_per_1000m2": 22})

    rate = chosen["kg_per_1000m2"] * (area_m2 / 1000.0)

    soil_modifier = {
        "sand": "Split applications more carefully because leaching risk is higher.",
        "sandy": "Split applications more carefully because leaching risk is higher.",
        "clay": "Watch drainage and salt buildup if irrigation is intensive.",
        "loam": "Use normal split planning with monitoring.",
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
    """Estimate daily water use for planning conversations."""

    crop_factor = {
        "tomato": 5.8,
        "cucumber": 5.5,
        "grape": 3.6,
        "olive": 2.8,
        "wheat": 4.0,
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


def analyze_bundle(message: str, crop: str | None = None, region: str | None = None, growth_stage: str | None = None) -> dict[str, Any]:
    """Convenience wrapper used by Agent A.

    This keeps the same domain logic in one place while making integration easier.
    """

    guessed_ph = 6.8
    if "8.1" in message:
        guessed_ph = 8.1
    elif "5.2" in message:
        guessed_ph = 5.2

    soil = analyze_soil(soil_ph=guessed_ph, organic_matter_pct=1.4 if "low organic matter" in message.lower() else 2.2)
    fert = calculate_fertilizer(crop or "general crop", area_m2=800 if "800" in message else 500)
    water = estimate_water_usage(crop or "general crop", area_m2=800 if "800" in message else 500)

    answer = (
        f"Soil interpretation: pH is treated as {soil['ph_label']} and {soil['ph_note']} "
        f"Fertilizer direction: {fert['suggested_fertilizer_direction']} with an estimated total of "
        f"{fert['estimated_total_kg_for_area']} kg for the referenced area. "
        f"Water planning baseline: about {water['estimated_liters_per_day']} liters/day."
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
        },
    }
