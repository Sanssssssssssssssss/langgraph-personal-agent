from __future__ import annotations

import hashlib
import math
import re


class HashEmbedding:
    def __init__(self, dim: int = 64) -> None:
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dim
        tokens = re.findall(r"\w+", text.lower())
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for offset in range(0, min(len(digest), self.dim), 4):
                bucket = int.from_bytes(digest[offset : offset + 4], "big") % self.dim
                sign = 1.0 if digest[offset] % 2 == 0 else -1.0
                vector[bucket] += sign
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

