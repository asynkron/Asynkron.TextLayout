from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExtractionResult:
    Value: str | None
    Votes: int
    MatchedText: str | None = None

    @property
    def HasValue(self) -> bool:
        return self.Value is not None and self.Votes > 0


ExtractionResult.NoMatch = ExtractionResult("", 0)
