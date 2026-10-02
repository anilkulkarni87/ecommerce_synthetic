"""Store (physical location) generator.

Generates realistic US retail store locations across 5 regions,
with proper state/city distribution, store types, and sizing.
"""

from __future__ import annotations

from datetime import timedelta

import polars as pl

from .base import BaseGenerator


# Realistic US cities by region for store placement
US_STORE_LOCATIONS = {
    "Northeast": [
        ("New York", "NY", "10001"), ("Boston", "MA", "02101"),
        ("Philadelphia", "PA", "19101"), ("Pittsburgh", "PA", "15201"),
        ("Hartford", "CT", "06101"), ("Newark", "NJ", "07101"),
        ("Providence", "RI", "02901"), ("Buffalo", "NY", "14201"),
        ("Baltimore", "MD", "21201"), ("Washington", "DC", "20001"),
    ],
    "Southeast": [
        ("Atlanta", "GA", "30301"), ("Miami", "FL", "33101"),
        ("Charlotte", "NC", "28201"), ("Nashville", "TN", "37201"),
        ("Orlando", "FL", "32801"), ("Tampa", "FL", "33601"),
        ("Raleigh", "NC", "27601"), ("Jacksonville", "FL", "32099"),
        ("Richmond", "VA", "23218"), ("Charleston", "SC", "29401"),
    ],
    "Midwest": [
        ("Chicago", "IL", "60601"), ("Detroit", "MI", "48201"),
        ("Minneapolis", "MN", "55401"), ("Columbus", "OH", "43201"),
        ("Indianapolis", "IN", "46201"), ("Milwaukee", "WI", "53201"),
        ("Kansas City", "MO", "64101"), ("St. Louis", "MO", "63101"),
        ("Cincinnati", "OH", "45201"), ("Cleveland", "OH", "44101"),
    ],
    "West": [
        ("Los Angeles", "CA", "90001"), ("San Francisco", "CA", "94101"),
        ("Seattle", "WA", "98101"), ("Portland", "OR", "97201"),
        ("Denver", "CO", "80201"), ("San Diego", "CA", "92101"),
        ("Las Vegas", "NV", "89101"), ("Sacramento", "CA", "95801"),
        ("Salt Lake City", "UT", "84101"), ("Honolulu", "HI", "96801"),
    ],
    "Southwest": [
        ("Houston", "TX", "77001"), ("Dallas", "TX", "75201"),
        ("Phoenix", "AZ", "85001"), ("San Antonio", "TX", "78201"),
        ("Austin", "TX", "73301"), ("Albuquerque", "NM", "87101"),
        ("Tucson", "AZ", "85701"), ("Oklahoma City", "OK", "73101"),
        ("El Paso", "TX", "79901"), ("Fort Worth", "TX", "76101"),
    ],
}

STORE_TYPES = {
    "flagship": {"sq_ft": (25000, 60000), "employees": (80, 200), "pct": 0.10},
    "standard": {"sq_ft": (8000, 20000), "employees": (20, 60), "pct": 0.50},
    "outlet": {"sq_ft": (5000, 15000), "employees": (15, 40), "pct": 0.25},
    "kiosk": {"sq_ft": (200, 1000), "employees": (3, 10), "pct": 0.15},
}

STREET_TEMPLATES = [
    "{num} Main Street",
    "{num} Broadway",
    "{num} Market Street",
    "{num} Oak Avenue",
    "{num} Elm Street",
    "{num} Commerce Drive",
    "{num} Retail Boulevard",
    "{num} Shopping Center Way",
    "{num} Mall Drive",
    "{num} Plaza Avenue",
    "{num} Galleria Drive",
    "{num} Parkway Boulevard",
]


class StoreGenerator(BaseGenerator):
    """Generate physical store locations."""

    def generate(self, **deps) -> pl.DataFrame:
        n = self.config.store_count
        start_date = self.config.date_range.start

        records: list[dict] = []

        # Flatten all locations
        all_locations: list[tuple[str, str, str, str]] = []
        for region, cities in US_STORE_LOCATIONS.items():
            for city, state, zip_code in cities:
                all_locations.append((city, state, zip_code, region))

        # Assign store types
        store_type_list = []
        for stype, info in STORE_TYPES.items():
            count = max(1, int(round(n * info["pct"])))
            store_type_list.extend([stype] * count)

        # Pad or trim to exact n
        while len(store_type_list) < n:
            store_type_list.append("standard")
        store_type_list = store_type_list[:n]
        self.rng.shuffle(store_type_list)

        for i in range(n):
            loc = all_locations[i % len(all_locations)]
            city, state, zip_code, region = loc
            stype = store_type_list[i]
            sinfo = STORE_TYPES[stype]

            sq_ft = self.rng.randint(*sinfo["sq_ft"])
            emp_count = self.rng.randint(*sinfo["employees"])

            # Stores opened 1-8 years ago
            days_ago = self.rng.randint(365, 365 * 8)
            opened = start_date - timedelta(days=days_ago)

            street = self.rng.choice(STREET_TEMPLATES).format(
                num=self.rng.randint(100, 9999)
            )

            store_name_prefixes = {
                "flagship": "Flagship",
                "standard": "",
                "outlet": "Outlet",
                "kiosk": "Express",
            }
            prefix = store_name_prefixes[stype]
            store_name = f"{prefix + ' ' if prefix else ''}{city} {self.rng.choice(['Center', 'Mall', 'Plaza', 'Square', 'Market'])}"

            records.append({
                "store_id": f"STORE-{i + 1:03d}",
                "store_name": store_name.strip(),
                "store_type": stype,
                "street_address": street,
                "city": city,
                "state": state,
                "zip_code": zip_code,
                "region": region,
                "opened_date": opened,
                "square_footage": sq_ft,
                "employee_count": emp_count,
            })

        return pl.DataFrame(records).cast({
            "square_footage": pl.Int64,
            "employee_count": pl.Int64,
            "opened_date": pl.Date,
        })
