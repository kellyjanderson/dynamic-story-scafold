from __future__ import annotations

import hashlib
from dataclasses import dataclass
from random import Random
from typing import Any


@dataclass(frozen=True, slots=True)
class RandomStreams:
    """Produces independent deterministic random streams from one scene seed.

    A named stream is derived from the master seed and semantic keys rather
    than from the order in which other random operations happened. This keeps
    perception noise, decision jitter, action rolls, initiative, and
    environment evolution independently reproducible.
    """

    seed: int

    def seed_for(self, *keys: Any) -> int:
        digest = hashlib.blake2b(digest_size=16)
        digest.update(str(self.seed).encode("utf-8"))
        for key in keys:
            digest.update(b"\x00")
            digest.update(str(key).encode("utf-8"))
        return int.from_bytes(digest.digest(), "big")

    def stream(self, *keys: Any) -> Random:
        if not keys:
            raise ValueError("random stream requires at least one semantic key")
        return Random(self.seed_for(*keys))
