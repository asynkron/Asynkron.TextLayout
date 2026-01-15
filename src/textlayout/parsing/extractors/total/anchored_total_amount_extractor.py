from __future__ import annotations

import re
from decimal import Decimal

from ..anchored_extractor import Anchor, AnchoredExtractor, TextPosition
from ..extraction_result import ExtractionResult
from ..i_total_amount_extractor import ITotalAmountExtractor
from ...money_parser import MoneyParser

_TOTAL_DUE_LINE_PATTERN = re.compile(
    r"(?:total\s*due|due\s*[:：]?\s*total|amount\s+due|balance\s+due|att\s+betala)",
    re.IGNORECASE,
)
_VAT_LINE_PATTERN = re.compile(r"\b(?:vat|moms|mva|tax|mwst|iva|gst)\b", re.IGNORECASE)
_EXCLUDING_LINE_PATTERN = re.compile(
    r"\b(?:excl|exklusive|excluding|subtotal|sub[-\s]?total|netto|net)\b",
    re.IGNORECASE,
)
_ROUNDING_LINE_PATTERN = re.compile(r"\b(?:rounding|avrund|rundning)\b", re.IGNORECASE)
_DATE_LINE_PATTERN = re.compile(
    r"\b\d{4}[-/\.]\d{2}[-/\.]\d{2}\b|\b\d{2}[-/\.]\d{2}[-/\.]\d{4}\b",
    re.IGNORECASE,
)


class AnchoredTotalAmountExtractor(ITotalAmountExtractor):
    CurrencyProximityThreshold = 12
    TotalDueSearchWindow = 6

    @property
    def Name(self) -> str:
        return "Anchored total amount (token)"

    def Extract(self, context):
        results = self.ExtractAll(context)
        return ExtractionResult.NoMatch if not results else max(results, key=lambda result: result.Votes)

    def ExtractAll(self, context):
        results: list[ExtractionResult] = []
        total_due_result = self._try_extract_total_due_from_block(context)
        if total_due_result is not None and total_due_result.HasValue:
            results.append(total_due_result)

        matches = AnchoredExtractor.FindAnchored(
            context.Text,
            MoneyParser.AmountTokenPattern,
            AnchoredExtractor.TotalAmountAnchors,
            base_votes=2,
        )

        if not matches:
            return results

        currency_tokens = MoneyParser.FindCurrencyTokens(context.Text)
        lines = context.Text.split("\n")
        anchor_lines = self._find_anchor_lines(lines, AnchoredExtractor.TotalAmountAnchors)

        for match in matches:
            if match.AnchorBonus <= 0:
                continue

            amount = MoneyParser.ParseAmount(match.Value, context.Locale)
            if amount is None or amount <= 0 or amount >= 10_000_000:
                continue

            line_text = self._get_line_text(lines, match.ValuePosition.Line)
            line_bonus = self._get_anchor_line_bonus(anchor_lines, match.ValuePosition.Line)
            penalty = self._get_line_penalty(line_text)
            if match.AnchorBonus <= 0 and line_bonus == 0:
                continue

            if self._is_percent_token(line_text, match.ValuePosition.Column, match.ValuePosition.Length):
                continue

            if self._has_local_exclusion(line_text, match.ValuePosition.Column):
                continue

            bonus = self._get_currency_proximity_bonus(currency_tokens, match.ValuePosition)
            large_bonus = 1 if amount >= 1000 else 0
            votes = match.TotalVotes + bonus + line_bonus + large_bonus - penalty
            if votes <= 0:
                continue

            results.append(ExtractionResult(match.Value, votes, match.MatchedText or match.Value))

        return results

    @classmethod
    def _try_extract_total_due_from_block(cls, context) -> ExtractionResult | None:
        lines = context.Text.split("\n")
        candidates: list[tuple[Decimal, str, int, str]] = []

        for i, line in enumerate(lines):
            if not _TOTAL_DUE_LINE_PATTERN.search(line):
                continue

            if re.search(MoneyParser.AmountTokenPattern, line, re.IGNORECASE):
                inline_candidate = cls._extract_best_amount_from_line(line, context.Locale)
                if inline_candidate is not None:
                    amount, raw = inline_candidate
                    votes = 6 if amount >= 1000 else 5
                    return ExtractionResult(raw, votes, line.strip())

            for offset in range(1, cls.TotalDueSearchWindow + 1):
                cls._add_line_candidates(lines, i - offset, offset, context.Locale, candidates)
                cls._add_line_candidates(lines, i + offset, offset, context.Locale, candidates)

        if not candidates:
            return None

        filtered = [candidate for candidate in candidates if not cls._is_excluded_line(candidate[3])]
        if not filtered:
            filtered = candidates

        best = sorted(filtered, key=lambda candidate: (-candidate[0], candidate[2]))[0]
        best_votes = 6 if best[0] >= 1000 else 5
        return ExtractionResult(best[1], best_votes, best[3].strip())

    @classmethod
    def _add_line_candidates(
        cls,
        lines: list[str],
        line_index: int,
        line_distance: int,
        locale,
        candidates: list[tuple[Decimal, str, int, str]],
    ) -> None:
        if line_index < 0 or line_index >= len(lines):
            return

        line = lines[line_index]
        if cls._is_vat_percent_line(line):
            return

        currency_matches = list(re.finditer(MoneyParser.CurrencyTokenPattern, line, re.IGNORECASE))
        if not currency_matches and _DATE_LINE_PATTERN.search(line):
            return

        for match in re.finditer(MoneyParser.AmountTokenPattern, line, re.IGNORECASE):
            if cls._is_percent_token(line, match.start(), len(match.group(0))):
                continue

            amount = MoneyParser.ParseAmount(match.group(0), locale)
            if amount is None or amount <= 0 or amount >= 10_000_000:
                continue

            if currency_matches and cls._get_min_currency_distance(currency_matches, match.start(), len(match.group(0))) > cls.CurrencyProximityThreshold:
                continue

            if not currency_matches and cls._is_likely_year(amount):
                continue

            candidates.append((amount, match.group(0).strip(), line_distance, line))

    @classmethod
    def _extract_best_amount_from_line(cls, line: str, locale) -> tuple[Decimal, str] | None:
        if cls._is_vat_percent_line(line):
            return None

        currency_matches = list(re.finditer(MoneyParser.CurrencyTokenPattern, line, re.IGNORECASE))
        if not currency_matches and _DATE_LINE_PATTERN.search(line):
            return None

        candidates: list[tuple[Decimal, str, int]] = []

        for match in re.finditer(MoneyParser.AmountTokenPattern, line, re.IGNORECASE):
            if cls._is_percent_token(line, match.start(), len(match.group(0))):
                continue

            amount_text = match.group(0).strip()
            amount = MoneyParser.ParseAmount(amount_text, locale)
            if amount is None or amount <= 0 or amount >= 10_000_000:
                continue

            distance = 0 if not currency_matches else cls._get_min_currency_distance(currency_matches, match.start(), len(match.group(0)))
            if currency_matches and distance > cls.CurrencyProximityThreshold:
                continue

            if not currency_matches and cls._is_likely_year(amount):
                continue

            candidates.append((amount, amount_text, distance))

        if not candidates:
            return None

        best = sorted(candidates, key=lambda candidate: (-candidate[0], candidate[2]))[0]
        return best[0], best[1]

    @staticmethod
    def _get_min_currency_distance(currency_matches, value_index: int, value_length: int) -> int:
        value_start = value_index
        value_end = value_index + value_length
        min_distance = 2**31 - 1

        for match in currency_matches:
            token_start = match.start()
            token_end = match.start() + len(match.group(0))
            if token_end < value_start:
                distance = value_start - token_end
            elif token_start > value_end:
                distance = token_start - value_end
            else:
                distance = 0

            if distance < min_distance:
                min_distance = distance

        return min_distance

    @staticmethod
    def _is_percent_token(line_text: str, start_index: int, length: int) -> bool:
        if not line_text:
            return False

        end_index = start_index + length
        for i in range(end_index, min(end_index + 2, len(line_text))):
            if line_text[i].isspace():
                continue
            return line_text[i] == "%"

        for i in range(start_index - 1, max(-1, start_index - 3), -1):
            if line_text[i].isspace():
                continue
            return line_text[i] == "%"

        return False

    @staticmethod
    def _is_likely_year(amount: Decimal) -> bool:
        return amount >= 1900 and amount <= 2100 and amount == amount.to_integral_value()

    @staticmethod
    def _find_anchor_lines(lines: list[str], anchors: list[Anchor]) -> list[int]:
        anchor_lines: list[int] = []
        for i, line in enumerate(lines):
            for anchor in anchors:
                if re.search(anchor.Pattern, line, re.IGNORECASE):
                    anchor_lines.append(i)
                    break
        return anchor_lines

    @staticmethod
    def _get_line_text(lines: list[str], line_index: int) -> str:
        if line_index < 0 or line_index >= len(lines):
            return ""
        return lines[line_index]

    @staticmethod
    def _get_anchor_line_bonus(anchor_lines: list[int], line_index: int) -> int:
        if not anchor_lines:
            return 0

        min_distance = min(abs(anchor_line - line_index) for anchor_line in anchor_lines)
        if min_distance == 0:
            return 3
        if min_distance in (1, 2):
            return 2
        if min_distance in (3, 4):
            return 1
        return 0

    @classmethod
    def _get_line_penalty(cls, line_text: str) -> int:
        if not line_text or not line_text.strip():
            return 0

        if cls._is_vat_percent_line(line_text):
            return 4

        if _VAT_LINE_PATTERN.search(line_text):
            return 3

        if _EXCLUDING_LINE_PATTERN.search(line_text):
            return 2

        if _ROUNDING_LINE_PATTERN.search(line_text):
            return 2

        return 0

    @classmethod
    def _is_excluded_line(cls, line_text: str) -> bool:
        return (
            cls._is_vat_percent_line(line_text)
            or _VAT_LINE_PATTERN.search(line_text)
            or _EXCLUDING_LINE_PATTERN.search(line_text)
            or _ROUNDING_LINE_PATTERN.search(line_text)
        )

    @classmethod
    def _is_vat_percent_line(cls, line_text: str) -> bool:
        return bool(line_text and "%" in line_text and _VAT_LINE_PATTERN.search(line_text))

    @staticmethod
    def _has_local_exclusion(line_text: str, value_column: int) -> bool:
        if not line_text or not line_text.strip():
            return False

        safe_column = min(value_column, len(line_text))
        prefix = line_text[:safe_column]
        last_index = -1

        for match in _EXCLUDING_LINE_PATTERN.finditer(prefix):
            last_index = max(last_index, match.start())

        for match in _VAT_LINE_PATTERN.finditer(prefix):
            last_index = max(last_index, match.start())

        for match in _ROUNDING_LINE_PATTERN.finditer(prefix):
            last_index = max(last_index, match.start())

        if last_index < 0:
            return False

        return safe_column - last_index <= 25

    @classmethod
    def _get_currency_proximity_bonus(
        cls,
        currency_tokens,
        value_position: TextPosition,
    ) -> int:
        if not currency_tokens:
            return 0

        value_start = value_position.CharIndex
        value_end = value_position.CharIndex + value_position.Length
        min_distance = 2**31 - 1

        for token in currency_tokens:
            if token.Index < value_start:
                distance = value_start - token.Index
            elif token.Index > value_end:
                distance = token.Index - value_end
            else:
                distance = 0

            if distance < min_distance:
                min_distance = distance

        if min_distance <= cls.CurrencyProximityThreshold:
            return 2

        if min_distance <= cls.CurrencyProximityThreshold * 2:
            return 1

        return 0
