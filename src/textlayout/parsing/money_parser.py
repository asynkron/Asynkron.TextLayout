from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from .locale import Locale

CurrencyTokenPattern = r"\b(?:USD|EUR|GBP|SEK|NOK|DKK|CHF|INR)\b|(?:USD|EUR|GBP|SEK|NOK|DKK|CHF|INR)(?=\d)|[€$£]|\bkr\b"
AmountTokenPattern = r"(?<!\d)(?:\d{1,3}(?:[ \t.,]\d{3})+|\d+)(?:[.,]\d{2})?(?!\d)"

_EUR_CODE_PATTERN = re.compile(r"\bEUR\b", re.IGNORECASE)
_USD_CODE_PATTERN = re.compile(r"\bUSD\b", re.IGNORECASE)
_GBP_CODE_PATTERN = re.compile(r"\bGBP\b", re.IGNORECASE)
_SEK_CODE_PATTERN = re.compile(r"\bSEK\b", re.IGNORECASE)
_KRONA_CODE_PATTERN = re.compile(r"\bkr\b")
_NOK_CODE_PATTERN = re.compile(r"\bNOK\b", re.IGNORECASE)
_DKK_CODE_PATTERN = re.compile(r"\bDKK\b", re.IGNORECASE)
_CHF_CODE_PATTERN = re.compile(r"\bCHF\b", re.IGNORECASE)
_ANY_CURRENCY_PATTERN = re.compile(r"[€$£]|EUR|USD|GBP|SEK|NOK|DKK|CHF|kr", re.IGNORECASE)
_EUROPEAN_FORMATTED_AMOUNT_PATTERN = re.compile(r"^(\d{1,3}(?:[\s\.]\d{3})*),(\d{1,2})$")
_SIMPLE_COMMA_DECIMAL_PATTERN = re.compile(r"^(\d+),(\d{1,2})$")
_US_FORMATTED_AMOUNT_PATTERN = re.compile(r"^(\d{1,3}(?:,\d{3})*)\.(\d{1,2})$")
_SIMPLE_DOT_DECIMAL_PATTERN = re.compile(r"^(\d+)\.(\d{1,2})$")
_COMMA_DECIMAL_WITH_SEPARATORS_PATTERN = re.compile(r"^(\d[\d\s\.]*)?,(\d{2})$")
_DOT_DECIMAL_WITH_SEPARATORS_PATTERN = re.compile(r"^(\d[\d,]*)\.(\d{2})$")


@dataclass(frozen=True)
class TokenMatch:
    Value: str
    Index: int
    Length: int


@dataclass(frozen=True)
class AmountResult:
    Total: Decimal | None
    ExcludingVat: Decimal | None
    Vat: Decimal | None
    VatRate: Decimal | None
    Currency: str | None


class MoneyParser:
    CurrencyTokenPattern = CurrencyTokenPattern
    AmountTokenPattern = AmountTokenPattern

    @staticmethod
    def DetectCurrency(text: str) -> str | None:
        if "€" in text or _EUR_CODE_PATTERN.search(text):
            return "EUR"

        if "$" in text or _USD_CODE_PATTERN.search(text):
            return "USD"

        if "£" in text or _GBP_CODE_PATTERN.search(text):
            return "GBP"

        if _SEK_CODE_PATTERN.search(text) or _KRONA_CODE_PATTERN.search(text):
            return "SEK"

        if _NOK_CODE_PATTERN.search(text):
            return "NOK"

        if _DKK_CODE_PATTERN.search(text):
            return "DKK"

        if _CHF_CODE_PATTERN.search(text):
            return "CHF"

        return None

    @staticmethod
    def FindCurrencyTokens(text: str) -> list[TokenMatch]:
        return [TokenMatch(m.group(0), m.start(), m.end() - m.start()) for m in re.finditer(CurrencyTokenPattern, text, re.IGNORECASE)]

    @staticmethod
    def FindAmountTokens(text: str) -> list[TokenMatch]:
        return [TokenMatch(m.group(0), m.start(), m.end() - m.start()) for m in re.finditer(AmountTokenPattern, text, re.IGNORECASE)]

    @staticmethod
    def ExtractAmounts(text: str, locale: Locale) -> AmountResult:
        currency = MoneyParser.DetectCurrency(text)
        vat_rate = MoneyParser._ExtractVatRate(text)
        total = MoneyParser._ExtractTotal(text, locale)
        vat = MoneyParser._ExtractVatAmount(text, locale, total)
        exc_vat = MoneyParser._ExtractSubtotal(text, locale)

        if total is not None and vat is not None and exc_vat is None:
            exc_vat = total - vat
        elif total is not None and exc_vat is not None and vat is None:
            vat = total - exc_vat
        elif exc_vat is not None and vat_rate is not None and total is None:
            vat = exc_vat * vat_rate / Decimal("100")
            total = exc_vat + vat
        elif exc_vat is not None and vat is not None and total is None:
            total = exc_vat + vat

        if vat is not None and total is not None and vat >= total:
            vat = None

        return AmountResult(total, exc_vat, vat, vat_rate, currency)

    @staticmethod
    def ParseAmount(text: str, locale: Locale) -> Decimal | None:
        text = _ANY_CURRENCY_PATTERN.sub("", text).strip()
        if not text:
            return None

        if locale == Locale.European:
            euro_match = _EUROPEAN_FORMATTED_AMOUNT_PATTERN.match(text)
            if euro_match:
                int_part = euro_match.group(1).replace(" ", "").replace(".", "")
                dec_part = euro_match.group(2)
                return MoneyParser._try_parse_decimal(f"{int_part}.{dec_part}")

            simple_euro = _SIMPLE_COMMA_DECIMAL_PATTERN.match(text)
            if simple_euro:
                int_part = simple_euro.group(1)
                dec_part = simple_euro.group(2)
                return MoneyParser._try_parse_decimal(f"{int_part}.{dec_part}")

        elif locale == Locale.US:
            us_match = _US_FORMATTED_AMOUNT_PATTERN.match(text)
            if us_match:
                int_part = us_match.group(1).replace(",", "")
                dec_part = us_match.group(2)
                return MoneyParser._try_parse_decimal(f"{int_part}.{dec_part}")

            simple_us = _SIMPLE_DOT_DECIMAL_PATTERN.match(text)
            if simple_us:
                int_part = simple_us.group(1)
                dec_part = simple_us.group(2)
                return MoneyParser._try_parse_decimal(f"{int_part}.{dec_part}")

        comma_decimal = _COMMA_DECIMAL_WITH_SEPARATORS_PATTERN.match(text)
        if comma_decimal:
            int_part = (comma_decimal.group(1) or "").replace(" ", "").replace(".", "")
            dec_part = comma_decimal.group(2)
            return MoneyParser._try_parse_decimal(f"{int_part}.{dec_part}")

        dot_decimal = _DOT_DECIMAL_WITH_SEPARATORS_PATTERN.match(text)
        if dot_decimal:
            int_part = dot_decimal.group(1).replace(",", "")
            dec_part = dot_decimal.group(2)
            return MoneyParser._try_parse_decimal(f"{int_part}.{dec_part}")

        return MoneyParser._try_parse_decimal(text)

    @staticmethod
    def _try_parse_decimal(value: str) -> Decimal | None:
        try:
            return Decimal(value)
        except (InvalidOperation, ValueError):
            return None

    @staticmethod
    def _ExtractVatRate(text: str) -> Decimal | None:
        patterns = [
            r"(?:vat|moms|tax)\s*[-–]?\s*[^0-9]*(\d+(?:[.,]\d+)?)\s*%",
            r"(\d+(?:[.,]\d+)?)\s*%\s*(?:vat|moms|tax)",
            r"vat\s+rate[:\s]*(\d+(?:[.,]\d+)?)\s*%",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                rate_str = match.group(1).replace(",", ".")
                rate = MoneyParser._try_parse_decimal(rate_str)
                if rate is not None and rate > 0 and rate <= 100:
                    return rate

        return None

    @staticmethod
    def _ExtractTotal(text: str, locale: Locale) -> Decimal | None:
        total: Decimal | None = None

        patterns: list[tuple[str, bool]] = [
            (r"(?:amount\s+)?paid[:\s]*", True),
            (r"total[:\s]+(?:USD|EUR|GBP|INR)[ \t]*", False),
            (r"total[:\s]*(?!excl|logged)", False),
            (r"totalt\s+i\s+[A-Za-z]+[:\s\n]*", False),
            (r"amount\s+due[:\s]*", False),
            (r"grand\s+total[:\s]*", False),
            (r"att\s+betala[:\s]*", False),
            (r"summa[:\s]*", False),
        ]

        for pattern, is_final in patterns:
            full_pattern = pattern + r"([€$£]?[ \t]*[\d \t\.,]+[ \t]*(?:€|EUR|USD|GBP|SEK|kr)?)"
            matches = re.finditer(full_pattern, text, re.IGNORECASE)
            for match in matches:
                amount_str = match.group(1)
                amount = MoneyParser.ParseAmount(amount_str, locale)
                if amount is not None and amount > 0 and amount < 10_000_000:
                    if is_final or total is None or amount > total:
                        total = amount
                        if is_final:
                            break
            if total is not None and is_final:
                break

        return total

    @staticmethod
    def _ExtractVatAmount(text: str, locale: Locale, total: Decimal | None) -> Decimal | None:
        patterns = [
            r"vat\s+amount[:\s]*([€$£]?\s*[\d\s\.,]+)",
            r"(?:moms|mva)[:\s]*([€$£]?\s*[\d\s\.,]+)",
            r"vat\s*[-–]\s*\w+\s*\d+%\s*(?:on\s*[€$£]?[\d\s\.,]+)?\s*([€$£]?\s*[\d\s\.,]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount = MoneyParser.ParseAmount(match.group(1), locale)
                if amount is not None and amount > 0 and amount < 10_000_000:
                    if total is None or amount < total:
                        return amount

        return None

    @staticmethod
    def _ExtractSubtotal(text: str, locale: Locale) -> Decimal | None:
        patterns = [
            r"total\s+excl(?:uding)?\s+(?:vat|tax)[:\s]*([€$£]?\s*[\d\s\.,]+)",
            r"subtotal[:\s]*([€$£]?\s*[\d\s\.,]+)",
            r"exc(?:l(?:uding)?)?\.?\s*(?:vat|moms|tax)[:\s]*([€$£]?\s*[\d\s\.,]+)",
            r"netto[:\s]*([€$£]?\s*[\d\s\.,]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if not match:
                continue

            amount = MoneyParser.ParseAmount(match.group(1), locale)
            if amount is not None and amount > 0:
                return amount

        return None
