from __future__ import annotations

import re

from ..extraction_result import ExtractionResult
from ..i_invoice_date_extractor import IInvoiceDateExtractor
from ...date_parser import DateTokenPattern


class AnyDateExtractor(IInvoiceDateExtractor):
    @property
    def Name(self) -> str:
        return "Any date (fallback)"

    def Extract(self, context):
        results = self.ExtractAll(context)
        return ExtractionResult.NoMatch if not results else max(results, key=lambda result: result.Votes)

    def ExtractAll(self, context):
        matches = list(re.finditer(DateTokenPattern, context.Text, re.IGNORECASE))
        if not matches:
            return []

        return [ExtractionResult(match.group(0), 1, match.group(0)) for match in matches]
