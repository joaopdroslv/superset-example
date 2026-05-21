"""Shared Faker instance, helpers, and reference data used by the seeders.

The `Faker` and `random.Random` instances are seeded from `config.yml`
(`random_seed`) so every run is reproducible — same seed → same dataset. Bump
the value in `config.yml` to regenerate.
"""

from __future__ import annotations

import random
from decimal import ROUND_HALF_UP, Decimal
from typing import Mapping, Sequence, TypeVar

from faker import Faker

from ..config import CONFIG

fake = Faker("pt_BR")
fake.seed_instance(CONFIG.random_seed)
rng = random.Random(CONFIG.random_seed)


T = TypeVar("T")


def pick(items: Sequence[T]) -> T:
    """Single random pick from a non-empty sequence (uses the seeded RNG)."""
    return rng.choice(list(items))


def weighted(items: Sequence[T], weights: Sequence[float]) -> T:
    """Single weighted random pick (uses the seeded RNG)."""
    return rng.choices(list(items), weights=list(weights), k=1)[0]


def from_weights(weights: Mapping[T, float]) -> T:
    """Convenience: weighted pick straight from a `{value: weight}` mapping
    (the shape every entry under `config.yml::weights` uses).
    """
    return weighted(list(weights.keys()), list(weights.values()))


def money(value: float | Decimal) -> Decimal:
    """Quantize to 2 decimals, half-up — match `Numeric(_, 2)` columns."""
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def slugify(text: str) -> str:
    """Tiny, ASCII-only slug helper. Good enough for synthetic data."""
    out: list[str] = []
    for ch in text.lower():
        if ch.isalnum():
            out.append(ch)
        elif ch in {" ", "-", "_", "&"}:
            out.append("-")
    slug = "".join(out)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")


# ---------------------------------------------------------------------------
# Geographic reference data
# ---------------------------------------------------------------------------
# Country distribution comes from `config.yml::weights.countries`. The state
# codes per country stay here because they're a lookup table, not a knob.
# Keep `_GEO_STATES` in sync with `weights.countries` — `_validate_geo()`
# trips at import time if a configured country has no states defined.

_GEO_STATES: dict[str, list[str]] = {
    "BR": ["SP", "RJ", "MG", "RS", "PR", "BA", "SC", "PE", "CE", "GO", "DF", "ES"],
    "US": ["CA", "NY", "TX", "FL", "IL", "WA", "MA", "GA"],
    "AR": ["BA", "CO", "SF", "MZ", "TU"],
    "MX": ["CMX", "JAL", "NLE", "BCN", "PUE"],
    "PT": ["LIS", "POR", "BRG", "FAR"],
}


def _validate_geo() -> None:
    missing = [c for c in CONFIG.weights.countries if c not in _GEO_STATES]
    if missing:
        raise RuntimeError(
            f"config.yml weights.countries lists {missing} but no state codes "
            f"are defined for them in factories._GEO_STATES."
        )


_validate_geo()


def fake_location() -> tuple[str, str, str, str]:
    """Returns (country_code, state, city, postal_code)."""
    country = from_weights(CONFIG.weights.countries)
    state = rng.choice(_GEO_STATES[country])
    # Faker city/postcode are pt_BR-flavored, which is fine for synthetic data.
    return country, state, fake.city(), fake.postcode()


# ---------------------------------------------------------------------------
# Catalog reference data
# ---------------------------------------------------------------------------

CATEGORY_TREE: dict[str, list[str]] = {
    "Electronics": ["Smartphones", "Laptops", "Headphones", "Cameras"],
    "Apparel": ["Men's Clothing", "Women's Clothing", "Footwear"],
    "Home & Garden": ["Furniture", "Kitchen", "Gardening"],
    "Books": ["Fiction", "Non-Fiction"],
    "Sports": ["Outdoor", "Fitness"],
}

BRANDS_BY_SUBCATEGORY: dict[str, list[str]] = {
    "Smartphones": ["Apple", "Samsung", "Motorola", "Xiaomi", "Google"],
    "Laptops": ["Dell", "HP", "Lenovo", "Apple", "Asus", "Acer"],
    "Headphones": ["Sony", "Bose", "Apple", "JBL", "Sennheiser"],
    "Cameras": ["Canon", "Nikon", "Sony", "Fujifilm"],
    "Men's Clothing": ["Nike", "Adidas", "Tommy Hilfiger", "Calvin Klein", "Lacoste"],
    "Women's Clothing": ["Zara", "H&M", "Forever 21", "Mango", "Nike"],
    "Footwear": ["Nike", "Adidas", "Puma", "Vans", "Converse"],
    "Furniture": ["IKEA", "Tok&Stok", "Etna", "MadeiraMadeira"],
    "Kitchen": ["Tramontina", "Brastemp", "Electrolux", "Oster"],
    "Gardening": ["Tramontina", "Black+Decker", "Stihl"],
    "Fiction": ["Penguin", "Random House", "Companhia das Letras", "Intrínseca"],
    "Non-Fiction": ["O'Reilly", "Sextante", "Companhia das Letras"],
    "Outdoor": ["Columbia", "The North Face", "Patagonia", "Nautika"],
    "Fitness": ["Nike", "Adidas", "Puma", "Under Armour"],
}


# ---------------------------------------------------------------------------
# Shipping reference data
# ---------------------------------------------------------------------------

# Brazilian macro-regions plus a catch-all "INTL" for everything outside BR.
# `ShippingZone` rows are seeded from this list; addresses get their `zone_id`
# resolved via STATE_TO_ZONE below.
SHIPPING_ZONES_BR: list[dict[str, str]] = [
    {"code": "SE", "name": "Sudeste",      "country": "BR", "description": "SP, RJ, MG, ES"},
    {"code": "S",  "name": "Sul",          "country": "BR", "description": "PR, SC, RS"},
    {"code": "NE", "name": "Nordeste",     "country": "BR", "description": "BA, PE, CE, MA, PI, RN, PB, AL, SE"},
    {"code": "N",  "name": "Norte",        "country": "BR", "description": "PA, AM, RO, RR, AC, AP, TO"},
    {"code": "CO", "name": "Centro-Oeste", "country": "BR", "description": "DF, GO, MT, MS"},
]
SHIPPING_ZONE_INTL = {
    "code": "INTL", "name": "International", "country": "XX",
    "description": "Everything outside Brazil",
}

# Maps BR state codes (as used in `_GEO_STATES`) → zone code. States not in
# this map (e.g. US/AR/MX/PT) fall back to the "INTL" zone at lookup time.
STATE_TO_ZONE: dict[str, str] = {
    # Sudeste
    "SP": "SE", "RJ": "SE", "MG": "SE", "ES": "SE",
    # Sul
    "PR": "S",  "SC": "S",  "RS": "S",
    # Nordeste
    "BA": "NE", "PE": "NE", "CE": "NE",
    # Norte (no _GEO_STATES entries yet, kept for future expansion)
    # Centro-Oeste
    "GO": "CO", "DF": "CO",
}


def state_to_zone_code(country: str, state: str) -> str:
    """Return the shipping zone code for (country, state). Non-BR → 'INTL'."""
    if country != "BR":
        return SHIPPING_ZONE_INTL["code"]
    return STATE_TO_ZONE.get(state, SHIPPING_ZONE_INTL["code"])


# Brazilian-flavored carrier roster. `service_levels` is a CSV of values from
# `enums.shipping.ServiceLevel`; `typical_lead_time_hours` feeds the seeder's
# estimated_delivery calculation.
SHIPPING_CARRIERS: list[dict] = [
    {
        "name": "Correios",
        "code": "BR-CORREIOS",
        "country": "BR",
        "service_levels": "economy,standard,express",
        "typical_lead_time_hours": 96,
    },
    {
        "name": "Loggi",
        "code": "BR-LOGGI",
        "country": "BR",
        "service_levels": "standard,express,same_day",
        "typical_lead_time_hours": 48,
    },
    {
        "name": "Total Express",
        "code": "BR-TOTAL",
        "country": "BR",
        "service_levels": "standard,express",
        "typical_lead_time_hours": 72,
    },
    {
        "name": "Jadlog",
        "code": "BR-JADLOG",
        "country": "BR",
        "service_levels": "economy,standard",
        "typical_lead_time_hours": 96,
    },
    {
        "name": "Mercado Envios",
        "code": "BR-ML",
        "country": "BR",
        "service_levels": "standard,express,same_day",
        "typical_lead_time_hours": 36,
    },
    {
        "name": "FedEx International",
        "code": "INTL-FEDEX",
        "country": "US",
        "service_levels": "standard,express",
        "typical_lead_time_hours": 168,
    },
]


def compute_shipping_cost(
    weight_kg: Decimal,
    *,
    same_zone: bool,
) -> Decimal:
    """Synthetic shipping cost formula:

        base + (weight_kg * weight_factor) + (cross_zone_penalty if not same_zone)

    All three components are drawn from the configured ranges, so two calls
    with identical inputs still vary — realistic for a sandbox.
    """
    c = CONFIG.shipments.cost
    base = Decimal(str(round(rng.uniform(float(c.base_min), float(c.base_max)), 2)))
    wf = Decimal(str(round(rng.uniform(float(c.weight_factor_min), float(c.weight_factor_max)), 2)))
    penalty = (
        Decimal("0")
        if same_zone
        else Decimal(str(round(rng.uniform(
            float(c.cross_zone_penalty_min), float(c.cross_zone_penalty_max)
        ), 2)))
    )
    return money(base + (weight_kg * wf) + penalty)


# Tracking-event location samples — used by the shipments seeder to fill in
# `ShipmentEvent.location`. Realistic-sounding pt_BR strings.
TRACKING_LOCATION_TEMPLATES: list[str] = [
    "Centro de Distribuição {city} - {state}",
    "Agência {city}",
    "Hub Regional {city}",
    "Unidade de Tratamento {city}",
    "Em trânsito - {city}/{state}",
]


def tracking_location(city: str, state: str) -> str:
    return rng.choice(TRACKING_LOCATION_TEMPLATES).format(city=city, state=state)
