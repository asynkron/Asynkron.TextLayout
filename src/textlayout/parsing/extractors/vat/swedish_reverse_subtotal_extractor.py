from __future__ import annotations

import re

from ..extraction_result import ExtractionResult
from ..i_subtotal_extractor import ISubtotalExtractor
from ...money_parser import MoneyParser

_YEAR_LIKE_PATTERN = re.compile(r"^20\d{4}[.,]\d{2,3}")


class SwedishReverseSubtotalExtractor(ISubtotalExtractor):
    @property
    def Name(self) -> str:
        return "Swedish reverse subtotal (amount before label)"

    def Extract(self, context):
        results = self.ExtractAll(context)
        return ExtractionResult.NoMatch if not results else max(results, key=lambda result: result.Votes)

    def ExtractAll(self, context):
        pattern = r"(?<!\d)([€$£]?\d{1,6}[.,]\d{2,3}[€$£]?)\s*Delsumma\s+i\s+(?:EUR|SEK|USD|GBP)"
        matches = list(re.finditer(pattern, context.Text, re.IGNORECASE))
        if not matches:
            return []

        results: list[ExtractionResult] = []
        for match in matches:
            if _YEAR_LIKE_PATTERN.search(match.group(1)):
                continue

            amount_text = match.group(1).strip()
            amount = MoneyParser.ParseAmount(amount_text, context.Locale)
            if amount is not None and amount > 0 and amount < 10_000_000:
                results.append(ExtractionResult(amount_text, 3, match.group(0)))

        return results
