from __future__ import annotations

import re

from ..extraction_result import ExtractionResult
from ..i_invoice_number_extractor import IInvoiceNumberExtractor

_PATTERN = re.compile(r"\bINV(\d{6,})\b", re.IGNORECASE)


class InvPrefixExtractor(IInvoiceNumberExtractor):
    @property
    def Name(self) -> str:
        return "INV prefix"

    def Extract(self, context):
        results = self.ExtractAll(context)
        return ExtractionResult.NoMatch if not results else max(results, key=lambda result: result.Votes)

    def ExtractAll(self, context):
        matches = list(_PATTERN.finditer(context.Text))
        if not matches:
            return []

        return [ExtractionResult(f"INV{match.group(1)}", 3, match.group(0)) for match in matches]
