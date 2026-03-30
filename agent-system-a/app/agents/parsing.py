from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Iterable

# Canonical values kept intentionally compact and explainable.
CROP_ALIASES = {
    "tomato": "tomato",
    "tomatoes": "tomato",
    "olive": "olive",
    "olives": "olive",
    "wheat": "wheat",
    "grape": "grape",
    "grapes": "grape",
    "vine": "grape",
    "vines": "grape",
    "cucumber": "cucumber",
    "cucumbers": "cucumber",
    "potato": "potato",
    "potatoes": "potato",
    "طماطم": "tomato",
    "زيتون": "olive",
    "قمح": "wheat",
    "عنب": "grape",
    "خيار": "cucumber",
    "tomate": "tomato",
    "olivier": "olive",
    "ble": "wheat",
    "blé": "wheat",
    "raisin": "grape",
    "concombre": "cucumber",
}

REGION_ALIASES = {
    "bekaa": "bekaa",
    "beqaa": "bekaa",
    "coast": "coast",
    "coastal": "coast",
    "mountain": "mountain",
    "mountains": "mountain",
    "lebanon": "lebanon",
    "mediterranean": "mediterranean",
    "البقاع": "bekaa",
    "لبنان": "lebanon",
    "beka": "bekaa",
}

STAGE_ALIASES = {
    "seedling": "seedling",
    "seedlings": "seedling",
    "vegetative": "vegetative",
    "flowering": "flowering",
    "bloom": "flowering",
    "blooming": "flowering",
    "fruiting": "fruiting",
    "fruit set": "fruiting",
    "harvest": "harvest",
    "harvesting": "harvest",
    "full cycle": "full_cycle",
    "إزهار": "flowering",
    "حصاد": "harvest",
    "floraison": "flowering",
    "récolte": "harvest",
}

TEXTURE_ALIASES = {
    "sand": "sand",
    "sandy": "sand",
    "loam": "loam",
    "loamy": "loam",
    "clay": "clay",
    "clayey": "clay",
    "silt": "silt",
    "silty": "silt",
}

MONTHS = {
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
}

ROUTE_KEYWORDS = {
    "crop": ["crop", "plant", "grow", "suitable", "suitability", "region", "variety"],
    "pest": ["pest", "disease", "yellow", "spot", "spots", "sticky", "aphid", "whitefly", "powder", "rot", "mildew", "lesion", "symptom"],
    "market": ["price", "market", "sell", "storage", "store", "hold", "profit", "harvest now", "post-harvest"],
    "irrigation": ["water", "watering", "irrigation", "drip", "liters", "litres", "spray timing", "frost"],
    "soil": ["soil", "ph", "pH", "fertilizer", "fertiliser", "fertigation", "organic matter", "npk", "nitrogen", "phosphorus", "potassium", "texture", "تربة", "سماد", "engrais", "sol"],
}


@dataclass(slots=True)
class ParsedMessage:
    crop: str | None = None
    region: str | None = None
    growth_stage: str | None = None
    area_m2: float | None = None
    soil_ph: float | None = None
    organic_matter_pct: float | None = None
    soil_texture: str | None = None
    month: str | None = None


_WORD_RE = re.compile(r"[\w\u0600-\u06FF\-]+", flags=re.UNICODE)


def normalize_text(text: str) -> str:
    return " ".join(text.replace("m²", "m2").replace("mÂ²", "m2").lower().split())


def tokenize(text: str) -> list[str]:
    return _WORD_RE.findall(normalize_text(text))


def _find_alias(normalized_text: str, alias_map: dict[str, str]) -> str | None:
    for raw_alias, canonical in sorted(alias_map.items(), key=lambda item: len(item[0]), reverse=True):
        pattern = rf"(?<!\w){re.escape(raw_alias)}(?!\w)"
        if re.search(pattern, normalized_text):
            return canonical
    return None


def _parse_area_m2(normalized_text: str) -> float | None:
    patterns = [
        (r"(\d+(?:\.\d+)?)\s*(?:m2|sqm|square meters?|square metres?)", 1.0),
        (r"(\d+(?:\.\d+)?)\s*(?:hectares?|ha)\b", 10_000.0),
    ]
    for pattern, multiplier in patterns:
        match = re.search(pattern, normalized_text)
        if match:
            return round(float(match.group(1)) * multiplier, 2)
    return None


def _parse_soil_ph(normalized_text: str) -> float | None:
    match = re.search(r"(?:soil\s*)?ph\s*(?:is|=|:)?\s*(\d(?:\.\d+)?)", normalized_text)
    if match:
        return float(match.group(1))
    return None


def _parse_organic_matter(normalized_text: str) -> float | None:
    patterns = [
        r"(?:organic matter|om)\s*(?:is|=|:)?\s*(\d+(?:\.\d+)?)\s*%",
        r"(\d+(?:\.\d+)?)\s*%\s*(?:organic matter|om)",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized_text)
        if match:
            return float(match.group(1))
    return None


def _parse_month(normalized_text: str) -> str | None:
    return next((month for month in MONTHS if re.search(rf"(?<!\w){month}(?!\w)", normalized_text)), None)


def parse_message(text: str) -> ParsedMessage:
    normalized = normalize_text(text)
    return ParsedMessage(
        crop=_find_alias(normalized, CROP_ALIASES),
        region=_find_alias(normalized, REGION_ALIASES),
        growth_stage=_find_alias(normalized, STAGE_ALIASES),
        area_m2=_parse_area_m2(normalized),
        soil_ph=_parse_soil_ph(normalized),
        organic_matter_pct=_parse_organic_matter(normalized),
        soil_texture=_find_alias(normalized, TEXTURE_ALIASES),
        month=_parse_month(normalized),
    )


def merge_context(primary: ParsedMessage, history: Iterable[dict[str, str]] | None) -> ParsedMessage:
    merged = replace(primary)
    if not history:
        return merged

    for item in reversed(list(history)):
        if item.get("role") != "user":
            continue

        past = parse_message(item.get("content", ""))

        if merged.crop is None and past.crop is not None:
            merged.crop = past.crop
        if merged.region is None and past.region is not None:
            merged.region = past.region
        if merged.growth_stage is None and past.growth_stage is not None:
            merged.growth_stage = past.growth_stage
        if merged.area_m2 is None and past.area_m2 is not None:
            merged.area_m2 = past.area_m2
        if merged.soil_ph is None and past.soil_ph is not None:
            merged.soil_ph = past.soil_ph
        if merged.organic_matter_pct is None and past.organic_matter_pct is not None:
            merged.organic_matter_pct = past.organic_matter_pct
        if merged.soil_texture is None and past.soil_texture is not None:
            merged.soil_texture = past.soil_texture
        if merged.month is None and past.month is not None:
            merged.month = past.month

        if all([
            merged.crop is not None,
            merged.region is not None,
            merged.growth_stage is not None,
            merged.area_m2 is not None,
            merged.soil_ph is not None,
            merged.organic_matter_pct is not None,
            merged.soil_texture is not None,
            merged.month is not None,
        ]):
            break

    return merged


def decide_routes(text: str, parsed: ParsedMessage) -> list[str]:
    normalized = normalize_text(text)
    routes: list[str] = []

    for route_name, keywords in ROUTE_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            routes.append(route_name)

    if parsed.soil_ph is not None or parsed.organic_matter_pct is not None or parsed.soil_texture is not None:
        routes.append("soil")
    if parsed.area_m2 is not None and any(word in normalized for word in ["water", "watering", "irrigation", "liters", "litres"]):
        routes.append("irrigation")
    if parsed.crop is not None and not routes:
        routes.append("crop")
    if not routes:
        routes.append("crop")

    deduped: list[str] = []
    seen: set[str] = set()
    for route in routes:
        if route not in seen:
            deduped.append(route)
            seen.add(route)
    return deduped