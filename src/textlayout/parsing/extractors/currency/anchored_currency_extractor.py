from __future__ import annotations

from ..anchored_extractor import AnchoredExtractor, TextPosition
from ..extraction_result import ExtractionResult
from ..i_currency_extractor import ICurrencyExtractor
from ...money_parser import MoneyParser


class AnchoredCurrencyExtractor(ICurrencyExtractor):
    AmountProximityThreshold = 12

    @property
    def Name(self) -> str:
        return "Anchored currency (token)"

    def Extract(self, context):
        results = self.ExtractAll(context)
        return ExtractionResult.NoMatch if not results else max(results, key=lambda result: result.Votes)

    def ExtractAll(self, context):
        matches = AnchoredExtractor.FindAnchored(
            context.Text,
            MoneyParser.CurrencyTokenPattern,
            AnchoredExtractor.TotalAmountAnchors,
            base_votes=1,
        )

        if not matches:
            return []

        amount_tokens = MoneyParser.FindAmountTokens(context.Text)
        results: list[ExtractionResult] = []

        for match in matches:
            if match.AnchorBonus <= 0:
                continue

            currency = self._normalize_currency_token(match.Value)
            if not currency:
                continue

            bonus = self._get_amount_proximity_bonus(amount_tokens, match.ValuePosition)
            votes = match.TotalVotes + bonus
            if votes <= 0:
                continue

            results.append(ExtractionResult(currency, votes, match.MatchedText or match.Value))

        return results

    @staticmethod
    def _normalize_currency_token(token: str) -> str | None:
        trimmed = token.strip()
        if not trimmed:
            return None

        if "€" in trimmed:
            return "EUR"

        if "$" in trimmed:
            return "USD"

        if "£" in trimmed:
            return "GBP"

        if trimmed.lower() == "kr":
            return "SEK"

        upper = trimmed.upper()
        return upper if upper in {"USD", "EUR", "GBP", "SEK", "NOK", "DKK", "CHF", "INR"} else None

    @classmethod
    def _get_amount_proximity_bonus(
        cls,
        amount_tokens,
        value_position: TextPosition,
    ) -> int:
        if not amount_tokens:
            return 0

        value_start = value_position.CharIndex
        value_end = value_position.CharIndex + value_position.Length
        min_distance = 2**31 - 1

        for token in amount_tokens:
            if token.Index < value_start:
                distance = value_start - token.Index
            elif token.Index > value_end:
                distance = token.Index - value_end
            else:
                distance = 0

            if distance < min_distance:
                min_distance = distance

        if min_distance <= cls.AmountProximityThreshold:
            return 2

        if min_distance <= cls.AmountProximityThreshold * 2:
            return 1

        return 0
