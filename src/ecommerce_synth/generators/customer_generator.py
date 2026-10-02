"""Customer and address generator.

Generates customers with persona assignments, realistic demographics,
and 1-3 addresses per customer (billing + shipping).
"""

from __future__ import annotations

from datetime import date, timedelta

import polars as pl

from ..persona import CustomerPersona, PersonaEngine
from ..utils.temporal import random_timestamp_in_range
from .base import BaseGenerator


# Gender distribution (US Census approximation)
GENDERS = ["M", "F", "Non-binary", "Prefer not to say"]
GENDER_WEIGHTS = [0.48, 0.48, 0.03, 0.01]

ACQUISITION_CHANNELS = ["web", "store", "social", "referral"]
ACQUISITION_WEIGHTS = [0.45, 0.25, 0.20, 0.10]

# US states with population-weighted distribution
US_STATES_WEIGHTED = [
    ("CA", 0.12), ("TX", 0.09), ("FL", 0.07), ("NY", 0.06), ("PA", 0.04),
    ("IL", 0.04), ("OH", 0.04), ("GA", 0.03), ("NC", 0.03), ("MI", 0.03),
    ("NJ", 0.03), ("VA", 0.03), ("WA", 0.02), ("AZ", 0.02), ("MA", 0.02),
    ("TN", 0.02), ("IN", 0.02), ("MO", 0.02), ("MD", 0.02), ("WI", 0.02),
    ("CO", 0.02), ("MN", 0.02), ("SC", 0.02), ("AL", 0.015), ("LA", 0.015),
    ("KY", 0.014), ("OR", 0.013), ("OK", 0.012), ("CT", 0.011), ("UT", 0.01),
    ("IA", 0.01), ("NV", 0.01), ("AR", 0.01), ("MS", 0.009), ("KS", 0.009),
    ("NM", 0.007), ("NE", 0.006), ("ID", 0.006), ("WV", 0.006), ("HI", 0.005),
    ("NH", 0.004), ("ME", 0.004), ("MT", 0.003), ("RI", 0.003), ("DE", 0.003),
    ("SD", 0.003), ("ND", 0.002), ("AK", 0.002), ("VT", 0.002), ("WY", 0.002),
    ("DC", 0.002),
]


class CustomerGenerator(BaseGenerator):
    """Generate customers and addresses."""

    def generate(self, **deps) -> dict[str, pl.DataFrame]:
        n = self.config.tier.customers
        persona_engine = PersonaEngine(self.config, self.rng)

        customers: list[dict] = []
        addresses: list[dict] = []
        personas: list[CustomerPersona] = []

        states = [s for s, _ in US_STATES_WEIGHTED]
        state_weights = [w for _, w in US_STATES_WEIGHTED]

        for i in range(n):
            cust_id = self._uuid()
            persona = persona_engine.assign(i, n)
            personas.append(persona)

            # Demographics
            gender = self._pick_weighted(GENDERS, GENDER_WEIGHTS)

            # Use gender-appropriate names
            if gender == "M":
                first_name = self.faker.first_name_male()
            elif gender == "F":
                first_name = self.faker.first_name_female()
            else:
                first_name = self.faker.first_name()
            last_name = self.faker.last_name()

            # Fraudsters with synthetic identity get mismatched names
            if persona.is_fraudster and persona.fraud_type == "synthetic_identity":
                # Mix parts from different names
                first_name = self.faker.first_name()
                last_name = self.faker.last_name()

            email = f"{first_name.lower()}.{last_name.lower()}{self.rng.randint(1, 9999)}@{self.rng.choice(['gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com', 'icloud.com', 'aol.com', 'protonmail.com', 'mail.com'])}"

            phone = self.faker.phone_number()

            # Age distribution: 18-85, peaked around 30-45
            age = max(18, min(85, int(self.rng.gauss(35, 12))))
            dob = date.today() - timedelta(days=age * 365 + self.rng.randint(0, 364))

            # Registration date weighted by seasonality
            created_at = random_timestamp_in_range(
                self.rng,
                self.config.date_range.start,
                self.config.date_range.end,
                channel="online",
                config=self.config,
            )

            channel = self._pick_weighted(ACQUISITION_CHANNELS, ACQUISITION_WEIGHTS)
            if persona.is_omnichannel and self.rng.random() < 0.4:
                channel = "store"

            # Activity status
            is_active = persona.persona_name not in ("window_shopper",) or self.rng.random() < 0.3
            if persona.persona_name == "one_and_done" and self.rng.random() < 0.5:
                is_active = False

            customers.append({
                "customer_id": cust_id,
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "phone": phone,
                "date_of_birth": dob,
                "gender": gender,
                "created_at": created_at,
                "channel_acquired": channel,
                "is_active": is_active,
                "customer_segment": persona.customer_segment,
            })

            # Addresses: 1-3 per customer
            state = self._pick_weighted(states, state_weights)
            city = self.faker.city()
            street = self.faker.street_address()
            zip_code = self.faker.zipcode_in_state(state)

            # Primary billing+shipping (same address for most)
            for addr_type in ["billing", "shipping"]:
                addr_id = self._uuid()
                addresses.append({
                    "address_id": addr_id,
                    "customer_id": cust_id,
                    "address_type": addr_type,
                    "street_address": street,
                    "city": city,
                    "state": state,
                    "zip_code": zip_code,
                    "country": "US",
                    "is_default": True,
                })

            # ~30% have a second shipping address
            if self.rng.random() < 0.30:
                state2 = self._pick_weighted(states, state_weights)
                addresses.append({
                    "address_id": self._uuid(),
                    "customer_id": cust_id,
                    "address_type": "shipping",
                    "street_address": self.faker.street_address(),
                    "city": self.faker.city(),
                    "state": state2,
                    "zip_code": self.faker.zipcode_in_state(state2),
                    "country": "US",
                    "is_default": False,
                })

            # Fraudsters (account_takeover) add suspicious new shipping address
            if persona.is_fraudster and persona.fraud_type == "account_takeover":
                diff_state = self._pick_weighted(states, state_weights)
                addresses.append({
                    "address_id": self._uuid(),
                    "customer_id": cust_id,
                    "address_type": "shipping",
                    "street_address": self.faker.street_address(),
                    "city": self.faker.city(),
                    "state": diff_state,
                    "zip_code": self.faker.zipcode_in_state(diff_state),
                    "country": "US",
                    "is_default": False,
                })

        customers_df = pl.DataFrame(customers).cast({
            "date_of_birth": pl.Date,
            "created_at": pl.Datetime,
            "is_active": pl.Boolean,
        })

        addresses_df = pl.DataFrame(addresses).cast({
            "is_default": pl.Boolean,
        })

        # Attach personas as metadata (stored in memory, not in Parquet)
        customers_df.__dict__["_personas"] = {
            customers[i]["customer_id"]: personas[i] for i in range(n)
        }

        return {
            "customers": customers_df,
            "addresses": addresses_df,
        }
