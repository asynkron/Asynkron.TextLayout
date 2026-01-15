from __future__ import annotations

from dataclasses import dataclass

from ..locale import Locale


@dataclass(frozen=True)
class ExtractionContext:
    Text: str
    Lines: list[str]
    Locale: Locale
    SenderHint: str | None = None
    EmailBodyHint: str | None = None
    EmailSubject: str | None = None

    def with_text(self, text: str) -> "ExtractionContext":
        return ExtractionContext(
            text,
            self.Lines,
            self.Locale,
            self.SenderHint,
            self.EmailBodyHint,
            self.EmailSubject,
        )
