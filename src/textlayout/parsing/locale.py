from __future__ import annotations

import re
from enum import Enum


class Locale(Enum):
    Unknown = "Unknown"
    US = "US"
    European = "European"


_DOLLAR_SIGN_WITH_DIGIT_PATTERN = re.compile(r"\$\s*\d")
_USD_CURRENCY_CODE_PATTERN = re.compile(r"USD", re.IGNORECASE)
_EURO_CURRENCY_PATTERN = re.compile(r"€|EUR\b", re.IGNORECASE)
_NORDIC_AND_SWISS_CURRENCY_PATTERN = re.compile(r"SEK|NOK|DKK|CHF\b", re.IGNORECASE)
_KRONA_SYMBOL_PATTERN = re.compile(r"\bkr\b")
_POUND_CURRENCY_PATTERN = re.compile(r"£|GBP\b", re.IGNORECASE)
_SWEDISH_INVOICE_TERMS_PATTERN = re.compile(
    r"\b(faktura|moms|summa|belopp|förfallodatum|betala)\b",
    re.IGNORECASE,
)
_GERMAN_INVOICE_TERMS_PATTERN = re.compile(
    r"\b(Rechnung|Mehrwertsteuer|Betrag|Summe)\b",
    re.IGNORECASE,
)
_FRENCH_INVOICE_TERMS_PATTERN = re.compile(
    r"\b(facture|TVA|montant)\b",
    re.IGNORECASE,
)
_SWEDISH_LOCATION_PATTERN = re.compile(
    r"\b(Sweden|Sverige|Stockholm|Göteborg|Malmö)\b",
    re.IGNORECASE,
)
_GERMAN_LOCATION_PATTERN = re.compile(
    r"\b(Germany|Deutschland|Berlin|München)\b",
    re.IGNORECASE,
)
_FRENCH_LOCATION_PATTERN = re.compile(
    r"\b(France|Paris|Frankreich)\b",
    re.IGNORECASE,
)
_DUTCH_LOCATION_PATTERN = re.compile(
    r"\b(Netherlands|Nederland|Amsterdam)\b",
    re.IGNORECASE,
)
_CZECH_LOCATION_PATTERN = re.compile(r"\b(Czech|Česko|Praha|Prague)\b", re.IGNORECASE)
_US_LOCATION_PATTERN = re.compile(r"\bUSA\b|United States|California|New York|Texas", re.IGNORECASE)
_EU_VAT_NUMBER_PATTERN = re.compile(r"\b(SE|DE|FR|NL|CZ|AT|BE|IT|ES)\d{8,12}\b")
_SWEDISH_POSTAL_CODE_PATTERN = re.compile(r"\b\d{3}\s?\d{2}\b")
_US_ZIP_PLUS_FOUR_PATTERN = re.compile(r"\b\d{5}-\d{4}\b")
_EUROPEAN_NUMBER_FORMAT_PATTERN = re.compile(r"\d{1,3}[\s\.]\d{3},\d{2}")
_US_NUMBER_FORMAT_PATTERN = re.compile(r"\d{1,3},\d{3}\.\d{2}")


class LocaleDetector:
    @staticmethod
    def Detect(text: str) -> Locale:
        us_score = 0
        euro_score = 0

        if _DOLLAR_SIGN_WITH_DIGIT_PATTERN.search(text):
            us_score += 3

        if _USD_CURRENCY_CODE_PATTERN.search(text):
            us_score += 2

        if _EURO_CURRENCY_PATTERN.search(text):
            euro_score += 3

        if _NORDIC_AND_SWISS_CURRENCY_PATTERN.search(text):
            euro_score += 3

        if _KRONA_SYMBOL_PATTERN.search(text):
            euro_score += 2

        if _POUND_CURRENCY_PATTERN.search(text):
            us_score += 1

        if _SWEDISH_INVOICE_TERMS_PATTERN.search(text):
            euro_score += 3

        if _GERMAN_INVOICE_TERMS_PATTERN.search(text):
            euro_score += 3

        if _FRENCH_INVOICE_TERMS_PATTERN.search(text):
            euro_score += 3

        if _SWEDISH_LOCATION_PATTERN.search(text):
            euro_score += 4

        if _GERMAN_LOCATION_PATTERN.search(text):
            euro_score += 4

        if _FRENCH_LOCATION_PATTERN.search(text):
            euro_score += 4

        if _DUTCH_LOCATION_PATTERN.search(text):
            euro_score += 4

        if _CZECH_LOCATION_PATTERN.search(text):
            euro_score += 4

        if _US_LOCATION_PATTERN.search(text):
            us_score += 4

        if _EU_VAT_NUMBER_PATTERN.search(text):
            euro_score += 3

        if _SWEDISH_POSTAL_CODE_PATTERN.search(text):
            euro_score += 2

        if _US_ZIP_PLUS_FOUR_PATTERN.search(text):
            us_score += 2

        if _EUROPEAN_NUMBER_FORMAT_PATTERN.search(text):
            euro_score += 4

        if _US_NUMBER_FORMAT_PATTERN.search(text):
            us_score += 4

        if euro_score > us_score:
            return Locale.European

        if us_score > euro_score:
            return Locale.US

        return Locale.Unknown
