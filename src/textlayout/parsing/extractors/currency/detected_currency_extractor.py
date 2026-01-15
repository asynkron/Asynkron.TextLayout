from __future__ import annotations

from ..extraction_result import ExtractionResult
from ..i_currency_extractor import ICurrencyExtractor
from ...money_parser import MoneyParser


class DetectedCurrencyExtractor(ICurrencyExtractor):
    @property
    def Name(self) -> str:
        return "Detected currency (fallback)"

    def Extract(self, context):
        results = self.ExtractAll(context)
        return ExtractionResult.NoMatch if not results else max(results, key=lambda result: result.Votes)

    def ExtractAll(self, context):
        currency = MoneyParser.DetectCurrency(context.Text)
        return [] if not currency else [ExtractionResult(currency, 1, currency)]
