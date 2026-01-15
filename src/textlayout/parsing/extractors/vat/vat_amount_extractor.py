from __future__ import annotations

import re

from ..extraction_result import ExtractionResult
from ..i_vat_amount_extractor import IVatAmountExtractor
from ...money_parser import MoneyParser


class VatAmountExtractor(IVatAmountExtractor):
    @property
    def Name(self) -> str:
        return "VAT amount"

    def Extract(self, context):
        results = self.ExtractAll(context)
        return ExtractionResult.NoMatch if not results else max(results, key=lambda result: result.Votes)

    def ExtractAll(self, context):
        patterns = [
            (r"vat\s+amount\s*[:：]?\s*", 3),
            (r"(?:moms|mva)\s*[:：]?\s*", 3),
            (r"vat\s*[-–]\s*\w+\s*\d+%\s*(?:on\s*[€$£]?[\d\s\.,]+)?\s*", 2),
        ]

        results: list[ExtractionResult] = []

        for pattern, votes in patterns:
            full_pattern = pattern + r"([€$£]?\s*[\d\s\.,]+)"
            for match in re.finditer(full_pattern, context.Text, re.IGNORECASE):
                amount_str = match.group(1)
                amount = MoneyParser.ParseAmount(amount_str, context.Locale)
                if amount is not None and amount > 0 and amount < 10_000_000:
                    results.append(ExtractionResult(amount_str, votes, match.group(0)))

        return results
