"""Customer and address generator.

Generates customers with persona assignments, realistic demographics,
and 1-3 addresses per customer (billing + shipping).
"""

from __future__ import annotations

import re
from datetime import date, timedelta

import polars as pl

from ..persona import CustomerPersona, PersonaEngine
from ..utils.temporal import random_timestamp_in_range
from .base import BaseGenerator


NICKNAME_MAP = {
    "robert": "bob", "william": "bill", "james": "jim", "john": "jack",
    "michael": "mike", "david": "dave", "richard": "rick", "joseph": "joe",
    "thomas": "tom", "charles": "charlie", "christopher": "chris",
    "daniel": "dan", "matthew": "matt", "anthony": "tony", "andrew": "andy",
    "jennifer": "jen", "elizabeth": "liz", "katherine": "kate",
    "margaret": "maggie", "patricia": "pat", "stephanie": "steph",
    "rebecca": "becca", "samantha": "sam", "alexandra": "alex",
}


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
        from faker import Faker

        n = self.config.tier.customers
        persona_engine = PersonaEngine(self.config, self.rng)
        identity_noise = getattr(self.config, "identity_noise", 0.0) or 0.0
        regions = getattr(self.config, "regions", ["US"]) or ["US"]
        region_configs = getattr(self.config, "region_configs", {}) or {}
        compliance_mode = getattr(self.config, "compliance_mode", False)
        is_multi_region = regions != ["US"]

        # Cache localized Faker instances if multi-region is enabled
        locale_fakers: dict[str, Faker] = {}
        if is_multi_region:
            for r_code in regions:
                rc = region_configs.get(r_code)
                loc = rc.faker_locale if rc else "en_US"
                f = Faker(loc)
                f.seed_instance(self.config.seed)
                locale_fakers[r_code] = f
        region_weights = [
            region_configs[r].weight if r in region_configs else 1.0 for r in regions
        ]

        customers: list[dict] = []
        addresses: list[dict] = []
        personas: list[CustomerPersona] = []
        ground_truth: list[dict] = []
        consents: list[dict] = []
        canonical_pool: list[tuple[dict, dict]] = []

        states = [s for s, _ in US_STATES_WEIGHTED]
        state_weights = [w for _, w in US_STATES_WEIGHTED]

        for i in range(n):
            cust_id = self._uuid()
            persona = persona_engine.assign(i, n)
            personas.append(persona)

            cust_country = (
                self._pick_weighted(regions, region_weights) if is_multi_region else "US"
            )
            loc_faker = locale_fakers.get(cust_country, self.faker)

            if identity_noise > 0 and canonical_pool and self.rng.random() < identity_noise:
                orig_cust, orig_addr = self.rng.choice(canonical_pool)
                mutated_cust, mutated_addr, noise_type = self._mutate_identity(
                    cust_id, orig_cust, orig_addr, persona
                )
                customers.append(mutated_cust)
                ground_truth.append({
                    "record_type": "customer",
                    "customer_id": cust_id,
                    "instore_account_id": None,
                    "true_entity_id": orig_cust["customer_id"],
                    "is_duplicate": True,
                    "noise_type": noise_type,
                })
                for addr_type in ["billing", "shipping"]:
                    addresses.append({
                        "address_id": self._uuid(),
                        "customer_id": cust_id,
                        "address_type": addr_type,
                        "street_address": mutated_addr["street_address"],
                        "city": mutated_addr["city"],
                        "state": mutated_addr["state"],
                        "zip_code": mutated_addr["zip_code"],
                        "country": orig_addr.get("country", "US"),
                        "is_default": True,
                    })
                continue

            # Demographics
            gender = self._pick_weighted(GENDERS, GENDER_WEIGHTS)

            # Use gender-appropriate names
            if gender == "M":
                first_name = loc_faker.first_name_male()
            elif gender == "F":
                first_name = loc_faker.first_name_female()
            else:
                first_name = loc_faker.first_name()
            last_name = loc_faker.last_name()

            # Fraudsters with synthetic identity get mismatched names
            if persona.is_fraudster and persona.fraud_type == "synthetic_identity":
                first_name = loc_faker.first_name()
                last_name = loc_faker.last_name()

            email = f"{first_name.lower()}.{last_name.lower()}{self.rng.randint(1, 9999)}@{self.rng.choice(['gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com', 'icloud.com', 'aol.com', 'protonmail.com', 'mail.com'])}"

            phone = loc_faker.phone_number()

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

            # Compliance: GDPR/CCPA consent ledger & ~2% Right-to-Erasure tombstones
            if compliance_mode:
                rc = region_configs.get(cust_country)
                framework = rc.privacy_framework if rc else "CCPA"
                for purpose in ("marketing_email", "analytics_cookies", "personalization"):
                    status = "granted" if self.rng.random() < 0.78 else "withdrawn"
                    consents.append({
                        "consent_id": self._uuid(),
                        "customer_id": cust_id,
                        "jurisdiction": framework,
                        "purpose": purpose,
                        "status": status,
                        "updated_at": created_at,
                    })
                # 2% DSAR Right-to-Erasure tombstone (anonymizes PII, keeps customer_id for FK)
                if self.rng.random() < 0.02:
                    first_name = "REDACTED"
                    last_name = "REDACTED"
                    email = f"erased_{cust_id[:8]}@anonymized.local"
                    phone = "REDACTED"
                    is_active = False

            cust_row = {
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
            }
            customers.append(cust_row)

            # ~5% household sharing: distinct person sharing phone & address with an existing household
            household_addr = None
            if canonical_pool and self.rng.random() < 0.05:
                hh_cust, hh_addr = self.rng.choice(canonical_pool)
                if hh_addr.get("country", "US") == cust_country and hh_cust.get("phone") != "REDACTED":
                    last_name = hh_cust["last_name"]
                    phone = hh_cust["phone"]
                    household_addr = hh_addr
                    email = f"{first_name.lower()}.{last_name.lower()}{self.rng.randint(1, 9999)}@{self.rng.choice(['gmail.com', 'yahoo.com', 'outlook.com', 'icloud.com'])}"

            # Addresses: 1-3 per customer
            if household_addr is not None:
                street = household_addr["street_address"]
                city = household_addr["city"]
                state = household_addr["state"]
                zip_code = household_addr["zip_code"]
            elif cust_country == "US":
                state = self._pick_weighted(states, state_weights)
                zip_code = self.faker.zipcode_in_state(state)
                city = loc_faker.city()
                street = loc_faker.street_address()
            else:
                state = getattr(loc_faker, "state_abbr", lambda: cust_country)() if hasattr(loc_faker, "state_abbr") else cust_country
                zip_code = loc_faker.postcode()
                city = loc_faker.city()
                street = loc_faker.street_address()

            primary_addr = {
                "street_address": street,
                "city": city,
                "state": state,
                "zip_code": zip_code,
                "country": cust_country,
            }
            if identity_noise > 0:
                canonical_pool.append((cust_row, primary_addr))
                ground_truth.append({
                    "record_type": "customer",
                    "customer_id": cust_id,
                    "instore_account_id": None,
                    "true_entity_id": cust_id,
                    "is_duplicate": False,
                    "noise_type": "none",
                })
            elif len(canonical_pool) < 200:
                canonical_pool.append((cust_row, primary_addr))

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
                    "country": cust_country,
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

        result: dict[str, pl.DataFrame] = {
            "customers": customers_df,
            "addresses": addresses_df,
        }

        if identity_noise > 0:
            result["identity_ground_truth"] = pl.DataFrame(ground_truth).cast({
                "record_type": pl.Utf8,
                "customer_id": pl.Utf8,
                "instore_account_id": pl.Utf8,
                "true_entity_id": pl.Utf8,
                "is_duplicate": pl.Boolean,
                "noise_type": pl.Utf8,
            })

        if compliance_mode and consents:
            result["customer_consents"] = pl.DataFrame(consents).cast({
                "updated_at": pl.Datetime,
            })

        return result

    def _mutate_identity(
        self,
        new_cust_id: str,
        orig_cust: dict,
        orig_addr: dict,
        persona: CustomerPersona,
    ) -> tuple[dict, dict, str]:
        """Create a realistic duplicate customer profile with entity-resolution noise."""
        noise_type = self.rng.choice([
            "email_alias", "phone_format", "nickname_typo", "household_split", "temporal_pii_change"
        ])

        first_name = orig_cust["first_name"]
        last_name = orig_cust["last_name"]
        email = orig_cust["email"]
        phone = orig_cust["phone"]
        dob = orig_cust["date_of_birth"]
        street = orig_addr["street_address"]

        if noise_type == "email_alias":
            local, domain = email.split("@", 1)
            if domain == "gmail.com" and self.rng.random() < 0.5:
                email = f"{local}@googlemail.com"
            else:
                email = f"{local}+shop@{domain}"
        elif noise_type == "phone_format":
            digits = re.sub(r"\D", "", phone)[-10:]
            if len(digits) == 10:
                fmt = self.rng.choice(["dashed", "parens", "e164", "dots"])
                if fmt == "dashed":
                    phone = f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
                elif fmt == "parens":
                    phone = f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
                elif fmt == "e164":
                    phone = f"+1{digits}"
                else:
                    phone = f"{digits[:3]}.{digits[3:6]}.{digits[6:]}"
            street = re.sub(r"\bStreet\b", "St", street)
            street = re.sub(r"\bAvenue\b", "Ave", street)
        elif noise_type == "nickname_typo":
            nick = NICKNAME_MAP.get(first_name.lower())
            if nick:
                first_name = nick.capitalize()
            elif len(first_name) >= 4:
                # Adjacent character swap typo
                idx = self.rng.randint(1, len(first_name) - 2)
                chars = list(first_name)
                chars[idx], chars[idx + 1] = chars[idx + 1], chars[idx]
                first_name = "".join(chars)
            email = f"{first_name.lower()}.{last_name.lower()}{self.rng.randint(1, 99)}@gmail.com"
        elif noise_type == "household_split":
            # Same last name, phone, and address, but different email
            email = f"{first_name.lower()}_{last_name.lower()}{self.rng.randint(10, 99)}@outlook.com"
        elif noise_type == "temporal_pii_change":
            # Same person changed email and phone over time, same name/DOB/address
            email = f"{first_name.lower()}.{last_name.lower()}.new{self.rng.randint(10, 99)}@icloud.com"
            phone = self.faker.phone_number()

        created_at = random_timestamp_in_range(
            self.rng,
            self.config.date_range.start,
            self.config.date_range.end,
            channel="online",
            config=self.config,
        )

        mutated_cust = {
            "customer_id": new_cust_id,
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": phone,
            "date_of_birth": dob,
            "gender": orig_cust["gender"],
            "created_at": created_at,
            "channel_acquired": self._pick_weighted(ACQUISITION_CHANNELS, ACQUISITION_WEIGHTS),
            "is_active": True,
            "customer_segment": persona.customer_segment,
        }
        mutated_addr = {
            "street_address": street,
            "city": orig_addr["city"],
            "state": orig_addr["state"],
            "zip_code": orig_addr["zip_code"],
        }
        return mutated_cust, mutated_addr, noise_type
