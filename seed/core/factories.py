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
