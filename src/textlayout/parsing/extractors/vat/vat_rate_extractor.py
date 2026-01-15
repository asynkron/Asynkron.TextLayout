from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from ..extraction_result import ExtractionResult
from ..i_vat_rate_extractor import IVatRateExtractor


class VatRateExtractor(IVatRateExtractor):
    @property
    def Name(self) -> str:
        return "VAT rate"

    def Extract(self, context):
        results = self.ExtractAll(context)
        return ExtractionResult.NoMatch if not results else max(results, key=lambda result: result.Votes)

    def ExtractAll(self, context):
        patterns = [
            r"(?:vat|moms|tax)\s*[-–]?\s*[^0-9]*(\d+(?:[.,]\d+)?)\s*%",
            r"(\d+(?:[.,]\d+)?)\s*%\s*(?:vat|moms|tax)",
            r"vat\s+rate\s*[:：]?\s*(\d+(?:[.,]\d+)?)\s*%",
        ]

        results: list[ExtractionResult] = []

        for pattern in patterns:
            for match in re.finditer(pattern, context.Text, re.IGNORECASE):
                rate_str = match.group(1).replace(",", ".")
                try:
                    rate = Decimal(rate_str)
                except (InvalidOperation, ValueError):
                    continue

                if rate >= 0 and rate <= 100:
                    results.append(ExtractionResult(rate_str, 3, match.group(0)))

        return results
