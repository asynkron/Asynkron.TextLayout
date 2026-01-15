from __future__ import annotations

from ..anchored_extractor import AnchoredExtractor
from ..extraction_result import ExtractionResult
from ..i_invoice_number_extractor import IInvoiceNumberExtractor


class AlphaNumericHyphenExtractor(IInvoiceNumberExtractor):
    ValuePattern = r"[A-Z]{4,}\d{2,}-\d{3,}"

    @property
    def Name(self) -> str:
        return "Alpha-numeric hyphen (XXXX00-000)"

    def Extract(self, context):
        results = self.ExtractAll(context)
        return ExtractionResult.NoMatch if not results else max(results, key=lambda result: result.Votes)

    def ExtractAll(self, context):
        matches = AnchoredExtractor.FindAnchored(
            context.Text,
            self.ValuePattern,
            AnchoredExtractor.InvoiceNumberAnchors,
            base_votes=2,
        )

        if not matches:
            return []

        results: list[ExtractionResult] = []
        for match in matches:
            if match.Value and len(match.Value) >= 4:
                results.append(ExtractionResult(match.Value, match.TotalVotes, match.MatchedText))

        return results
