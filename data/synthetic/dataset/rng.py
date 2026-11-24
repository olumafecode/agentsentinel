"""Seeded random choices that come out the same on every Python version (NFR-14).

Python guarantees only one thing across versions: random.Random.random() gives the
same sequence for the same seed ("Notes on Reproducibility" in the random module's
documentation). Helpers such as choice() and shuffle() may change how they use it,
so every method here is built on random() alone.

Each stream has its own seed, made from the project seed and the stream's name, so
drawing more numbers in one stream (the review sample, say) never shifts another
(the events).
"""

import hashlib
import random
from collections.abc import Sequence
from decimal import Decimal
from typing import TypeVar

T = TypeVar("T")

CENT = Decimal("0.01")


class Rng:
    def __init__(self, seed: int, stream: str) -> None:
        digest = hashlib.sha256(f"{seed}:{stream}".encode()).digest()
        self._random = random.Random(int.from_bytes(digest[:8], "big"))

    def fraction(self) -> float:
        """A number from 0 up to, but not including, 1."""
        return self._random.random()

    def below(self, n: int) -> int:
        """A whole number from 0 to n - 1."""
        if n < 1:
            raise ValueError("n must be at least 1")
        return min(int(self.fraction() * n), n - 1)

    def between(self, low: int, high: int) -> int:
        """A whole number from low to high, both included."""
        return low + self.below(high - low + 1)

    def chance(self, probability: float) -> bool:
        return self.fraction() < probability

    def choice(self, items: Sequence[T]) -> T:
        return items[self.below(len(items))]

    def shuffled(self, items: Sequence[T]) -> list[T]:
        """A new list with the items in random order (Fisher and Yates)."""
        result = list(items)
        for i in range(len(result) - 1, 0, -1):
            j = self.below(i + 1)
            result[i], result[j] = result[j], result[i]
        return result

    def money(self, low: Decimal, high: Decimal) -> Decimal:
        """An amount from low to high in whole cents, both included."""
        cents = self.between(int(low / CENT), int(high / CENT))
        return (Decimal(cents) * CENT).quantize(CENT)
