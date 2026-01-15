from __future__ import annotations

import re

from ..extraction_result import ExtractionResult
from ..i_invoice_number_extractor import IInvoiceNumberExtractor

_PATTERN = re.compile(r"(?:invoice|faktura)\s*(?:#|no\.?|nr\.?|nummer)[:\s]*([A-Z]*\d+[A-Z0-9\-]*)", re.IGNORECASE)
_DIGIT_PATTERN = re.compile(r"\d")


class InvoiceNoExtractor(IInvoiceNumberExtractor):
    @property
    def Name(self) -> str:
        return "Invoice No/Nr/Nummer"

    def Extract(self, context):
        results = self.ExtractAll(context)
        return ExtractionResult.NoMatch if not results else max(results, key=lambda result: result.Votes)

    def ExtractAll(self, context):
        matches = list(_PATTERN.finditer(context.Text))
        if not matches:
            return []

        results: list[ExtractionResult] = []
        for match in matches:
            num = match.group(1).strip()
            if len(num) >= 4 and _DIGIT_PATTERN.search(num):
                results.append(ExtractionResult(num, 3, match.group(0)))

        return results
