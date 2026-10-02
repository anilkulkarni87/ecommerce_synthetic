"""Abstract base generator."""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

import polars as pl
from faker import Faker

if TYPE_CHECKING:
    from ..config import GenerationConfig


class BaseGenerator(ABC):
    """Base class for all data generators."""

    def __init__(self, config: GenerationConfig):
        self.config = config
        self.rng = random.Random(config.seed)
        self.faker = Faker()
        Faker.seed(config.seed)

    @abstractmethod
    def generate(self, **deps: Any) -> pl.DataFrame | dict[str, pl.DataFrame]:
        """Generate data, receiving upstream dependencies as keyword args.

        May return a single DataFrame or a dict of named DataFrames.
        """
        ...

    def _uuid(self) -> str:
        """Generate a deterministic UUID-like string."""
        return self.faker.uuid4()

    def _pick_weighted(self, options: list, weights: list[float]) -> Any:
        """Pick from options with weights."""
        return self.rng.choices(options, weights=weights, k=1)[0]
