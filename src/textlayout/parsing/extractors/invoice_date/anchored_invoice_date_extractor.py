from __future__ import annotations

import re

from ..anchored_extractor import Anchor, AnchoredExtractor
from ..extraction_result import ExtractionResult
from ..i_invoice_date_extractor import IInvoiceDateExtractor
from ...date_parser import DateTokenPattern

_RANGE_DASH_REGEX = re.compile(r"\s[-–]\s")
_RANGE_WORD_REGEX = re.compile(r"\bto\b", re.IGNORECASE)
_INVOICE_DATE_REGEX = re.compile(r"invoice\s+date", re.IGNORECASE)
_DUE_DATE_REGEX = re.compile(r"due\s+date", re.IGNORECASE)
_ISO_DATE_REGEX = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_RANGE_TOKEN_REGEX = re.compile(r"[-–]|to", re.IGNORECASE)


class AnchoredInvoiceDateExtractor(IInvoiceDateExtractor):
    @property
    def Name(self) -> str:
        return "Anchored invoice date"

    def Extract(self, context):
        results = self.ExtractAll(context)
        return ExtractionResult.NoMatch if not results else max(results, key=lambda result: result.Votes)

    def ExtractAll(self, context):
        results: list[ExtractionResult] = []
        results.extend(self._extract_paired_iso_dates(context))
        results.extend(self._extract_anchored_dates_from_lines(context, AnchoredExtractor.InvoiceDateAnchors))

        matches = AnchoredExtractor.FindAnchored(
            context.Text,
            DateTokenPattern,
            AnchoredExtractor.InvoiceDateAnchors,
            base_votes=1,
        )

        for match in matches:
            if match.Value and match.Value.strip():
                results.append(ExtractionResult(match.Value, match.TotalVotes, match.MatchedText or match.Value))

        return results

    @classmethod
    def _extract_anchored_dates_from_lines(cls, context, anchors: list[Anchor]):
        results: list[ExtractionResult] = []
        for line_index, line in enumerate(context.Lines):
            if not line or not line.strip():
                continue

            for anchor in anchors:
                anchor_matches = list(re.finditer(anchor.Pattern, line, re.IGNORECASE))
                if not anchor_matches:
                    continue

                date_matches = list(re.finditer(DateTokenPattern, line, re.IGNORECASE))
                if date_matches:
                    cls._add_date_matches_with_anchors(results, line, anchor_matches, date_matches, 1 + anchor.BonusVotes)
                    continue

                cls._add_neighbor_date_matches(results, context.Lines, line_index, 1 + anchor.BonusVotes)

        return results

    @staticmethod
    def _add_neighbor_date_matches(results, lines, line_index: int, anchor_votes: int) -> None:
        max_offset = 6
        for offset in range(1, max_offset + 1):
            AnchoredInvoiceDateExtractor._add_date_matches_for_line(results, lines, line_index - offset, anchor_votes, offset)
            AnchoredInvoiceDateExtractor._add_date_matches_for_line(results, lines, line_index + offset, anchor_votes, offset)

    @staticmethod
    def _add_date_matches_for_line(results, lines, line_index: int, anchor_votes: int, offset: int) -> None:
        if line_index < 0 or line_index >= len(lines):
            return

        line = lines[line_index]
        if not line or not line.strip():
            return

        date_matches = list(re.finditer(DateTokenPattern, line, re.IGNORECASE))
        if not date_matches:
            return

        AnchoredInvoiceDateExtractor._add_date_matches(results, line, date_matches, anchor_votes, offset)

    @staticmethod
    def _add_date_matches(results, line: str, date_matches, anchor_votes: int, offset: int) -> None:
        for match in date_matches:
            if AnchoredInvoiceDateExtractor._is_range_token(line, match):
                continue

            votes = max(1, anchor_votes - offset)
            results.append(ExtractionResult(match.group(0), votes, match.group(0)))

    @staticmethod
    def _add_date_matches_with_anchors(results, line: str, anchor_matches, date_matches, anchor_votes: int) -> None:
        anchors = [match.start() for match in anchor_matches]
        if not anchors:
            AnchoredInvoiceDateExtractor._add_date_matches(results, line, date_matches, anchor_votes, 0)
            return

        for match in date_matches:
            if AnchoredInvoiceDateExtractor._is_range_token(line, match):
                continue

            distance = min(abs(match.start() - anchor_index) for anchor_index in anchors)
            distance_penalty = min(3, distance // 20)
            votes = max(1, anchor_votes - distance_penalty)
            results.append(ExtractionResult(match.group(0), votes, match.group(0)))

    @staticmethod
    def _is_range_token(line: str, date_match) -> bool:
        start = max(0, date_match.start() - 6)
        end = min(len(line), date_match.start() + len(date_match.group(0)) + 6)
        window = line[start:end]

        return bool(_RANGE_DASH_REGEX.search(window) or _RANGE_WORD_REGEX.search(window))

    @staticmethod
    def _extract_paired_iso_dates(context) -> list[ExtractionResult]:
        results: list[ExtractionResult] = []
        if not _INVOICE_DATE_REGEX.search(context.Text) or not _DUE_DATE_REGEX.search(context.Text):
            return results

        for line in context.Lines:
            trimmed_line = line.strip()
            if len(trimmed_line) > 40:
                continue

            matches = list(_ISO_DATE_REGEX.finditer(trimmed_line))
            if len(matches) != 2:
                continue

            between_start = matches[0].start() + len(matches[0].group(0))
            between = trimmed_line[between_start:matches[1].start()]
            if _RANGE_TOKEN_REGEX.search(between):
                continue

            results.append(ExtractionResult(matches[0].group(0), 3, trimmed_line))

        return results
