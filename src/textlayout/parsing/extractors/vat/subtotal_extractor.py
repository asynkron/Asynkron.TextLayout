from __future__ import annotations

import re

from ..extraction_result import ExtractionResult
from ..i_subtotal_extractor import ISubtotalExtractor
from ...money_parser import MoneyParser


class SubtotalExtractor(ISubtotalExtractor):
    @property
    def Name(self) -> str:
        return "Subtotal/Total excl VAT"

    def Extract(self, context):
        results = self.ExtractAll(context)
        return ExtractionResult.NoMatch if not results else max(results, key=lambda result: result.Votes)

    def ExtractAll(self, context):
        patterns = [
            (r"total\s+excl(?:uding)?\s+(?:vat|tax)\s*[:：]?\s*", 3),
            (r"subtotal\s*[:：]?\s*", 3),
            (r"exc(?:l(?:uding)?)?\.?\s*(?:vat|moms|tax)\s*[:：]?\s*", 2),
            (r"netto\s*[:：]?\s*", 2),
        ]

        results: list[ExtractionResult] = []

        for pattern, votes in patterns:
            full_pattern = pattern + r"([€$£]?\s*[\d\s\.,]+)"
            for match in re.finditer(full_pattern, context.Text, re.IGNORECASE):
                amount_str = match.group(1).strip()
                amount = MoneyParser.ParseAmount(amount_str, context.Locale)
                if amount is not None and amount > 0 and amount < 10_000_000:
                    results.append(ExtractionResult(amount_str, votes, match.group(0)))

        return results
