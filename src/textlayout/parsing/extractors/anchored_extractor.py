from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from .extraction_result import ExtractionResult


@dataclass(frozen=True)
class TextPosition:
    Line: int
    Column: int
    EndColumn: int
    CharIndex: int

    @property
    def Length(self) -> int:
        return self.EndColumn - self.Column


class AnchorPosition(Enum):
    None_ = "None"
    Left = "Left"
    Right = "Right"
    Above = "Above"
    Below = "Below"
    Any = "Any"


@dataclass(frozen=True)
class Anchor:
    Pattern: str
    BonusVotes: int
    Description: str | None = None


@dataclass(frozen=True)
class FoundAnchor:
    Anchor: Anchor
    Position: TextPosition
    MatchedText: str


@dataclass(frozen=True)
class FoundValue:
    Value: str
    Position: TextPosition
    MatchedText: str


@dataclass(frozen=True)
class AnchoredMatch:
    Value: str
    BaseVotes: int
    AnchorBonus: int
    AnchorMatched: str | None
    Position: AnchorPosition
    Distance: int
    MatchedText: str | None = None
    ValuePosition: TextPosition | None = None

    @property
    def TotalVotes(self) -> int:
        return self.BaseVotes + self.AnchorBonus


class AnchoredExtractor:
    MaxHorizontalDistance = 30
    MaxVerticalDistance = 2
    ColumnTolerance = 10

    InvoiceNumberAnchors = [
        Anchor(r"invoice\s*(?:number|#|no\.?)\s*[:：]?\s*", 4, "Invoice Number"),
        Anchor(r"invoice\s*#", 4, "Invoice #"),
        Anchor(r"inv\.?\s*(?:no\.?|#)\s*[:：]?", 3, "Inv No"),
        Anchor(r"fakturanummer\s*[:：]?", 4, "Fakturanummer"),
        Anchor(r"fakturanr\.?\s*[:：]?", 4, "Fakturanr"),
        Anchor(r"faktura\s*(?:nr|#)\s*[:：]?", 3, "Faktura nr"),
        Anchor(r"rechnungsnummer\s*[:：]?", 4, "Rechnungsnummer"),
        Anchor(r"rechnung\s*(?:nr|#)\s*[:：]?", 3, "Rechnung Nr"),
        Anchor(r"numéro\s*de\s*facture\s*[:：]?", 4, "Numéro de facture"),
        Anchor(r"facture\s*(?:n[°o]|#)\s*[:：]?", 3, "Facture n°"),
        Anchor(r"reference\s*(?:number|#|no\.?)?\s*[:：]?", 2, "Reference"),
        Anchor(r"order\s*(?:number|#|no\.?)?\s*[:：]?", 1, "Order Number"),
    ]

    TotalAmountAnchors = [
        Anchor(r"(?:grand\s+)?\btotal\b\s*[:：]", 4, "Total:"),
        Anchor(r"\btotal\s+due\b\s*[:：]?", 5, "Total Due"),
        Anchor(r"amount\s+due\s*[:：]?", 4, "Amount Due"),
        Anchor(r"\btotal\s+amount\b\s*[:：]?", 4, "Total Amount"),
        Anchor(r"amount\s+paid\s*[:：]?", 3, "Amount Paid"),
        Anchor(r"balance\s+due\s*[:：]?", 3, "Balance Due"),
        Anchor(r"\btotalt?\b(?!\s*(?:exkl|excl|exklusive|vat|moms|tax))\s*(?:i\s+sek)?\s*[:：]?", 4, "Totalt"),
        Anchor(r"\batt\s+betala\b\s*[:：]?", 4, "Att betala"),
        Anchor(r"\bsumma\b\s*[:：]?", 3, "Summa"),
        Anchor(r"\bbelopp\b\s*[:：]?", 2, "Belopp"),
        Anchor(r"\bgesamtbetrag\b\s*[:：]?", 4, "Gesamtbetrag"),
        Anchor(r"\bsumme\b\s*[:：]?", 3, "Summe"),
        Anchor(r"\bendbetrag\b\s*[:：]?", 3, "Endbetrag"),
        Anchor(r"\bmontant\s+total\b\s*[:：]?", 4, "Montant total"),
        Anchor(r"\btotal\s+ttc\b\s*[:：]?", 4, "Total TTC"),
        Anchor(r"\btotal\b(?=[€$£])", 2, "Total (no separator)"),
    ]

    InvoiceDateAnchors = [
        Anchor(r"invoice\s+date\s*[:：]?", 4, "Invoice Date"),
        Anchor(r"issue\s+date\s*[:：]?", 4, "Issue Date"),
        Anchor(r"tax\s+point\s+date\s*[:：]?", 4, "Tax point date"),
        Anchor(r"date\s+of\s+invoice\s*[:：]?", 4, "Date of Invoice"),
        Anchor(r"date\s+paid\s*[:：]?", 3, "Date Paid"),
        Anchor(r"paid\s+on\s*[:：]?", 2, "Paid on"),
        Anchor(r"fakturadatum\s*[:：]?", 4, "Fakturadatum"),
        Anchor(r"rechnungsdatum\s*[:：]?", 4, "Rechnungsdatum"),
    ]

    DueDateAnchors = [
        Anchor(r"due\s+date\s*[:：]?", 4, "Due Date"),
        Anchor(r"payment\s+due\s*[:：]?", 4, "Payment Due"),
        Anchor(r"förfallodatum\s*[:：]?", 4, "Förfallodatum"),
        Anchor(r"förfaller\s*[:：]?", 3, "Förfaller"),
        Anchor(r"fälligkeitsdatum\s*[:：]?", 4, "Fälligkeitsdatum"),
        Anchor(r"pay\s+by\s*[:：]?", 3, "Pay by"),
    ]

    VendorNameAnchors = [
        Anchor(r"(?:your\s+)?receipt\s+from\s+", 4, "Receipt from"),
        Anchor(r"(?:your\s+)?invoice\s+from\s+", 4, "Invoice from"),
        Anchor(r"bill\s+from\s+", 4, "Bill from"),
        Anchor(r"payment\s+to\s+", 3, "Payment to"),
        Anchor(r"sent\s+by\s+", 2, "Sent by"),
        Anchor(r"kvitto\s+från\s+", 4, "Kvitto från"),
        Anchor(r"faktura\s+från\s+", 4, "Faktura från"),
        Anchor(r"rechnung\s+von\s+", 4, "Rechnung von"),
        Anchor(r"beleg\s+von\s+", 3, "Beleg von"),
    ]

    @staticmethod
    def _build_line_index(text: str) -> list[int]:
        line_starts = [0]
        for idx, char in enumerate(text):
            if char == "\n":
                line_starts.append(idx + 1)
        return line_starts

    @staticmethod
    def _get_position(char_index: int, length: int, line_starts: list[int]) -> TextPosition:
        line = 0
        for i, start in enumerate(line_starts):
            if start > char_index:
                break
            line = i
        column = char_index - line_starts[line]
        return TextPosition(line, column, column + length, char_index)

    @staticmethod
    def _find_anchors(text: str, anchors: list[Anchor], line_starts: list[int]) -> list[FoundAnchor]:
        found: list[FoundAnchor] = []
        for anchor in anchors:
            for match in re.finditer(anchor.Pattern, text, re.IGNORECASE):
                pos = AnchoredExtractor._get_position(match.start(), match.end() - match.start(), line_starts)
                found.append(FoundAnchor(anchor, pos, match.group(0)))
        return found

    @staticmethod
    def _find_values(text: str, value_pattern: str, line_starts: list[int]) -> list[FoundValue]:
        found: list[FoundValue] = []
        for match in re.finditer(value_pattern, text, re.IGNORECASE):
            pos = AnchoredExtractor._get_position(match.start(), match.end() - match.start(), line_starts)
            found.append(FoundValue(match.group(0).strip(), pos, match.group(0)))
        return found

    @staticmethod
    def _get_relative_position(anchor: FoundAnchor, value: FoundValue) -> tuple[AnchorPosition, int]:
        a_pos = anchor.Position
        v_pos = value.Position

        if a_pos.Line == v_pos.Line:
            if a_pos.EndColumn <= v_pos.Column:
                distance = v_pos.Column - a_pos.EndColumn
                if distance <= AnchoredExtractor.MaxHorizontalDistance:
                    return (AnchorPosition.Left, distance)
            elif v_pos.EndColumn <= a_pos.Column:
                distance = a_pos.Column - v_pos.EndColumn
                if distance <= AnchoredExtractor.MaxHorizontalDistance:
                    return (AnchorPosition.Right, distance)

        line_diff = v_pos.Line - a_pos.Line
        if abs(line_diff) <= AnchoredExtractor.MaxVerticalDistance:
            columns_align = (
                abs(a_pos.Column - v_pos.Column) <= AnchoredExtractor.ColumnTolerance
                or abs(a_pos.EndColumn - v_pos.Column) <= AnchoredExtractor.ColumnTolerance
            )
            if columns_align:
                if line_diff > 0:
                    return (AnchorPosition.Above, line_diff)
                if line_diff < 0:
                    return (AnchorPosition.Below, -line_diff)

        char_distance = abs(v_pos.CharIndex - anchor.Position.CharIndex)
        if char_distance <= AnchoredExtractor.MaxHorizontalDistance * 3:
            return (AnchorPosition.Any, char_distance)

        return (AnchorPosition.None_, 2**31 - 1)

    @staticmethod
    def _calculate_bonus(anchor: Anchor, position: AnchorPosition, distance: int) -> int:
        if position == AnchorPosition.None_:
            return 0

        if position == AnchorPosition.Left:
            multiplier = 1.0 if distance <= 3 else max(0.5, 1.0 - distance / 30.0)
        elif position == AnchorPosition.Above:
            multiplier = 0.9 if distance == 1 else 0.7
        elif position == AnchorPosition.Right:
            multiplier = 0.4
        elif position == AnchorPosition.Below:
            multiplier = 0.3
        elif position == AnchorPosition.Any:
            multiplier = 0.3
        else:
            multiplier = 0

        return int(round(anchor.BonusVotes * multiplier))

    @staticmethod
    def FindAnchored(
        text: str,
        value_pattern: str,
        anchors: list[Anchor],
        base_votes: int = 1,
    ) -> list[AnchoredMatch]:
        line_starts = AnchoredExtractor._build_line_index(text)
        found_anchors = AnchoredExtractor._find_anchors(text, anchors, line_starts)
        found_values = AnchoredExtractor._find_values(text, value_pattern, line_starts)

        results: list[AnchoredMatch] = []

        for value in found_values:
            best_bonus = 0
            best_anchor_desc: str | None = None
            best_position = AnchorPosition.None_
            best_distance = 2**31 - 1

            for anchor in found_anchors:
                position, distance = AnchoredExtractor._get_relative_position(anchor, value)
                if position == AnchorPosition.None_:
                    continue

                bonus = AnchoredExtractor._calculate_bonus(anchor.Anchor, position, distance)
                if bonus > best_bonus or (bonus == best_bonus and distance < best_distance):
                    best_bonus = bonus
                    best_anchor_desc = anchor.Anchor.Description
                    best_position = position
                    best_distance = distance

            results.append(
                AnchoredMatch(
                    value.Value,
                    base_votes,
                    best_bonus,
                    best_anchor_desc,
                    best_position,
                    best_distance,
                    value.MatchedText,
                    value.Position,
                )
            )

        return results

    @staticmethod
    def ExtractBest(
        text: str,
        value_pattern: str,
        anchors: list[Anchor],
        base_votes: int = 1,
    ) -> ExtractionResult:
        matches = AnchoredExtractor.FindAnchored(text, value_pattern, anchors, base_votes)
        if not matches:
            return ExtractionResult.NoMatch

        best = max(matches, key=lambda match: match.TotalVotes)
        return ExtractionResult(best.Value, best.TotalVotes, best.MatchedText)
