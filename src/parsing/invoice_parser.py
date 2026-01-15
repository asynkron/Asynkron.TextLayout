#!/usr/bin/env python3
"""Generic invoice parser for Nordic/European invoices - well-rounded default template"""

import json
import re
import sys
from typing import Optional
from decimal import Decimal

# Optional imports with fallbacks
try:
    import dateparser
    HAS_DATEPARSER = True
except ImportError:
    HAS_DATEPARSER = False

try:
    from price_parser import Price
    HAS_PRICE_PARSER = True
except ImportError:
    HAS_PRICE_PARSER = False


class InvoiceParser:
    """
    Generic invoice parser targeting Swedish/Nordic/European invoice formats.
    Handles common patterns for:
    - Swedish invoices (Faktura, YYYY-MM-DD dates, SEK, Bankgiro)
    - Norwegian invoices (DD.MM.YYYY dates, NOK, IBAN)
    - US/International invoices (Month DD, YYYY dates, USD/EUR)
    """

    # Currency patterns - ISO codes take priority
    CURRENCY_MAP = {
        "sek": "SEK", "kr": "SEK", "kronor": "SEK",
        "eur": "EUR", "€": "EUR", "euro": "EUR",
        "usd": "USD", "$": "USD", "dollar": "USD",
        "nok": "NOK", "gbp": "GBP", "£": "GBP",
        "dkk": "DKK",
    }

    # Expected formats per locale (for validation)
    LOCALE_FORMATS = {
        "en-US": {
            "date_patterns": [
                r"^[A-Za-z]+\s+\d{1,2},?\s+\d{4}$",  # January 6, 2026
                r"^\d{1,2}/\d{1,2}/\d{4}$",          # 01/06/2026 (MM/DD/YYYY)
            ],
            "amount_pattern": r"^\d{1,3}(,\d{3})*\.\d{2}$",  # 1,234.56
            "expected_currencies": ["USD"],
            "common_currencies": ["USD", "EUR", "GBP"],  # Can bill in these
        },
        "sv-SE": {
            "date_patterns": [
                r"^\d{4}-\d{2}-\d{2}$",  # 2026-01-06 (ISO)
            ],
            "amount_pattern": r"^\d{1,3}(\s?\d{3})*,\d{2}$",  # 1 234,56 or 1234,56
            "expected_currencies": ["SEK"],
            "common_currencies": ["SEK", "EUR", "USD"],
        },
        "nb-NO": {
            "date_patterns": [
                r"^\d{2}\.\d{2}\.\d{4}$",  # 06.01.2026
            ],
            "amount_pattern": r"^\d{1,3}(\s?\d{3})*,\d{2}$",  # 1 234,56
            "expected_currencies": ["NOK"],
            "common_currencies": ["NOK", "SEK", "EUR"],
        },
        "de-DE": {
            "date_patterns": [
                r"^\d{2}\.\d{2}\.\d{4}$",  # 06.01.2026
            ],
            "amount_pattern": r"^\d{1,3}(\.\d{3})*,\d{2}$",  # 1.234,56
            "expected_currencies": ["EUR"],
            "common_currencies": ["EUR", "USD", "GBP"],
        },
        "en-GB": {
            "date_patterns": [
                r"^\d{2}/\d{2}/\d{4}$",  # 06/01/2026 (DD/MM/YYYY)
            ],
            "amount_pattern": r"^\d{1,3}(,\d{3})*\.\d{2}$",  # 1,234.56
            "expected_currencies": ["GBP"],
            "common_currencies": ["GBP", "EUR", "USD"],
        },
    }

    # Locale detection patterns
    LOCALE_SIGNALS = {
        "en-US": {
            "currency": [r"\$\s*[\d,]+\.\d{2}", r"\bUSD\b", r"\bdollars?\b"],
            "company": [r"\b(?:Inc|LLC|Corp|Corporation|PBC)\b\.?"],  # PBC = Public Benefit Corp
            "labels": [r"\bSales\s+tax\b", r"\bState\s+tax\b", r"\bBill\s+to\b", r"\bAmount\s+due\b"],
            "address": [r"\b(?:CA|NY|TX|FL|WA|MA|IL|PA|OH|GA|NC|NJ|VA|AZ|CO|TN|MI|MO|MD|WI|MN|SC|AL|LA|KY|OR|OK|CT|UT|IA|NV|AR|MS|KS|NM|NE|WV|ID|HI|NH|ME|MT|RI|DE|SD|ND|AK|VT|WY|DC)\s+\d{5}(?:-\d{4})?\b"],  # All US state codes
            "city": [r"\b(?:San\s+Francisco|New\s+York|Los\s+Angeles|Chicago|Houston|Phoenix|Philadelphia|San\s+Antonio|San\s+Diego|Dallas|Austin|Seattle|Denver|Boston|Washington|Atlanta)\b"],
            "date": [r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}"],
            "amount": [r"\$[\d,]+\.\d{2}"],  # $1,234.56
        },
        "sv-SE": {
            "currency": [r"\bSEK\b", r"\bkronor\b", r"\d+\s*kr\b"],
            "company": [r"\b[A-ZÅÄÖ][a-zåäö]+\s+AB\b", r"\bHB\b"],
            "labels": [r"\bFaktura\b", r"\bFakturanummer\b", r"\bFörfallodatum\b",
                      r"\bAtt\s+betala\b", r"\bMoms\b", r"\bBankgiro\b", r"\bPlusgiro\b",
                      r"\bOrg\.?\s*nr\b"],
            "address": [r"\b\d{3}\s*\d{2}\b"],  # Swedish postal: 141 32
            "date": [r"\b\d{4}-\d{2}-\d{2}\b"],  # YYYY-MM-DD
            "amount": [r"\d{1,3}(?:\s\d{3})*,\d{2}"],  # 1 234,56 (space thousands)
            "org_number": [r"\b\d{6}-\d{4}\b"],  # 556xxx-xxxx
        },
        "nb-NO": {
            "currency": [r"\bNOK\b", r"\bkr\b"],
            "company": [r"\b[A-ZÆØÅ][a-zæøå]+\s+AS\b", r"\bASA\b"],
            "labels": [r"\bMVA\b", r"\bForetaksregisteret\b", r"\bOrganisasjonsnummer\b"],
            "address": [r"\bNO-?\d{4}\b"],  # Norwegian postal: NO-3264
            "date": [r"\b\d{2}\.\d{2}\.\d{4}\b"],  # DD.MM.YYYY
            "org_number": [r"\bNO\s*\d{3}\s*\d{3}\s*\d{3}\s*MVA\b"],
        },
        "de-DE": {
            "currency": [r"\bEUR\b", r"€\s*[\d.,]+", r"\bEuro\b"],
            "company": [r"\bGmbH\b", r"\bAG\b", r"\bKG\b", r"\be\.?\s*K\.?\b"],
            "labels": [r"\bRechnung\b", r"\bRechnungsnummer\b", r"\bFälligkeitsdatum\b",
                      r"\bMwSt\b", r"\bNettobetrag\b", r"\bBruttobetrag\b"],
            "date": [r"\b\d{2}\.\d{2}\.\d{4}\b"],  # DD.MM.YYYY
            "amount": [r"\d{1,3}(?:\.\d{3})*,\d{2}"],  # 1.234,56 (dot thousands)
        },
        "en-GB": {
            "currency": [r"£\s*[\d,]+\.\d{2}", r"\bGBP\b"],
            "company": [r"\bLtd\b\.?", r"\bPLC\b", r"\bLLP\b"],
            "labels": [r"\bVAT\b", r"\bVAT\s+number\b"],
            "address": [r"\b[A-Z]{1,2}\d{1,2}\s*\d[A-Z]{2}\b"],  # UK postal: SW1A 1AA
            "date": [r"\b\d{2}/\d{2}/\d{4}\b"],  # DD/MM/YYYY
        },
    }

    def __init__(self, payload: str):
        self.text = payload
        # Use Poppler section if available (cleanest formatting)
        self.poppler = self._get_section("Poppler pdftotext")
        self.pdfplumber = self._get_section("Python PdfPlumber")
        self.best = self.poppler or self.pdfplumber or self.text

        # Detect locale early
        self.detected_locale, self.locale_scores = self._detect_locale_detailed()

    def _get_section(self, header: str) -> Optional[str]:
        """Extract a specific extractor section from the payload."""
        pattern = rf"{re.escape(header)}\*+\s*(.*?)(?=\n\w+[*]+|\Z)"
        m = re.search(pattern, self.text, re.DOTALL | re.IGNORECASE)
        return m.group(1).strip() if m else None

    def parse(self) -> dict:
        # Extract all fields (with raw values for confidence)
        vendor = self._extract_vendor()
        customer = self._extract_customer()
        invoice_num = self._extract_invoice_number()
        invoice_date, invoice_date_raw = self._extract_invoice_date()
        due_date, due_date_raw = self._extract_due_date()
        total, currency, total_raw = self._extract_total_amount()
        vat = self._extract_vat()

        # Get top locale signals for debugging
        top_signals = []
        if self.locale_scores.get(self.detected_locale):
            top_signals = self.locale_scores[self.detected_locale].get("matches", [])[:5]

        # Compute field confidence based on locale format matching
        raw_values = {
            "invoice_date_raw": invoice_date_raw,
            "due_date_raw": due_date_raw,
            "total_amount_raw": total_raw,
        }
        parsed_values = {
            "invoice_date": invoice_date,
            "due_date": due_date,
            "total_amount": total,
            "currency": currency,
        }
        field_confidence = self._compute_field_confidence(raw_values, parsed_values)

        result = {
            "document_type": "invoice",
            "vendor_locale": self.detected_locale,
            "locale_signals": top_signals,  # Debug: why this locale was chosen
            "vendor_name": vendor,
            "vendor_organization_number": self._extract_org_number(is_vendor=True),
            "customer_name": customer,
            "customer_organization_number": self._extract_org_number(is_vendor=False),
            "invoice_number": invoice_num,
            "invoice_date": invoice_date,
            "due_date": due_date,
            "total_amount": total,
            "currency": currency,
            "vat_amount": vat,
            "field_confidence": field_confidence,
            "static_identification_anchors": self._build_anchors(vendor),
        }

        # Add missing fields list
        missing = [k for k, v in result.items()
                   if v is None and k not in ("missing", "static_identification_anchors", "field_confidence", "locale_signals")]
        result["missing"] = missing

        return result

    def _extract_invoice_number(self) -> Optional[str]:
        """Extract invoice number using common label patterns."""
        patterns = [
            r"Invoice\s*number[:\s]+([A-Z0-9\-]+)",
            r"Fakturanummer[:\s]+([A-Z0-9\-]+)",
            r"Fakturanr[:\s]+([A-Z0-9\-]+)",
            r"Invoice\s*#[:\s]*([A-Z0-9\-]+)",
            r"Invoice[:\s]+([A-Z0-9\-]{4,})",  # At least 4 chars
        ]
        for p in patterns:
            m = re.search(p, self.best, re.IGNORECASE)
            if m and len(m.group(1).strip()) >= 3:
                return m.group(1).strip()
        return None

    def _extract_invoice_date(self) -> tuple[Optional[str], Optional[str]]:
        """Extract invoice date and normalize to YYYY-MM-DD.
        Returns (normalized_date, raw_date) tuple."""
        patterns = [
            r"Invoice\s*date\s+(\d{4}-\d{2}-\d{2})",  # YYYY-MM-DD
            r"Invoice\s*date\s+(\d{2}\.\d{2}\.\d{4})",  # DD.MM.YYYY
            r"Fakturadatum\s+(\d{4}-\d{2}-\d{2})",
            r"Date\s+of\s+issue\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4})",  # Month DD, YYYY with space
            r"Date\s+of\s+issue([A-Za-z]+\s+\d{1,2},?\s+\d{4})",  # Month DD, YYYY no space
            r"Invoice\s*date\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4})",
            r"Order\s+Date[:\s]+(\d{2}/\d{2}/\d{4})",  # US MM/DD/YYYY
            r"Transaction\s+Date[:\s]+(\d{2}/\d{2}/\d{4})",
            r"Date[:\s]+(\d{2}/\d{2}/\d{4})",  # Generic US date
            r"Date[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})",  # Date: Jan 06, 2022
            r"Datum[:\s]+(\d{4}-\d{2}-\d{2})",  # Swedish Datum: YYYY-MM-DD
        ]
        for p in patterns:
            m = re.search(p, self.best, re.IGNORECASE)
            if m:
                raw = m.group(1).strip()
                return self._normalize_date(raw), raw
        return None, None

    def _extract_due_date(self) -> tuple[Optional[str], Optional[str]]:
        """Extract due date and normalize to YYYY-MM-DD.
        Returns (normalized_date, raw_date) tuple."""
        patterns = [
            r"Due\s*date\s+(\d{4}-\d{2}-\d{2})",
            r"Due\s*date\s+(\d{2}\.\d{2}\.\d{4})",
            r"Date\s+due\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4})",  # with space
            r"Date\s+due([A-Za-z]+\s+\d{1,2},?\s+\d{4})",  # no space
            r"Förfallodatum\s+(\d{4}-\d{2}-\d{2})",
            r"Förfallodag\s+(\d{4}-\d{2}-\d{2})",
            r"Betala\s+senast\s+(\d{4}-\d{2}-\d{2})",
        ]
        for p in patterns:
            m = re.search(p, self.best, re.IGNORECASE)
            if m:
                raw = m.group(1).strip()
                return self._normalize_date(raw), raw
        return None, None

    def _extract_total_amount(self) -> tuple[Optional[float], Optional[str], Optional[str]]:
        """Extract total amount and currency.
        Returns (amount, currency, raw_amount) tuple."""
        patterns = [
            # "Total amount 20,907.00 SEK" or "Total amount                               20,907.00 SEK"
            r"Total\s+amount\s+([0-9,.\s]+)\s*(SEK|EUR|USD|NOK|DKK|GBP)",
            # "To pay SEK 171,000.00" or "To pay        SEK 171,000.00"
            r"To\s+pay\s+(SEK|EUR|USD|NOK|DKK|GBP)\s*([0-9,.\s]+)",
            # "Amount due €14.68"
            r"Amount\s+due[:\s]*([€$]?)([0-9,.\s]+)",
            # "Att betala 150 kr" or "Att betala: 150 kr"
            r"Att\s+betala[:\s]+([0-9,.\s]+)\s*(SEK|kr)?",
            # "Total price: $150.00 USD" - with $ prefix and currency suffix
            r"Total\s+price[:\s]+\$([0-9,.\s]+)\s*(USD)?",
            # "Total price: €14.68" or "Total price:                 $150.00"
            r"Total\s+price[:\s]+([€$]?)([0-9,.\s]+)",
            # "Total €14.68" at end of line
            r"Total\s*([€$]?)([0-9,.\s]+)\s*$",
            # "€14.68 due"
            r"([€$])([0-9,.\s]+)\s+due",
            # "$150.00 USD" standalone pattern
            r"\$([0-9,.\s]+)\s*(USD)",
            # "Total: 1537,50" with optional trailing whitespace
            r"Total:\s+([0-9][0-9,.\s]*[0-9])",
            # Fallback: "Total" followed by currency and amount
            r"Total[:\s]+(SEK|EUR|USD|NOK)\s*([0-9,.\s]+)",
            # "Summa: 1234,56" Swedish total
            r"Summa[:\s]+([0-9,.\s]+)",
            # "Belopp: 1234,56" Swedish amount
            r"Belopp[:\s]+([0-9,.\s]+)\s*(SEK|kr)?",
        ]

        for p in patterns:
            m = re.search(p, self.best, re.IGNORECASE)
            if m:
                groups = m.groups()
                amount_str = None
                currency = None

                for g in groups:
                    if g:
                        g = g.strip()
                        if re.match(r'^[0-9,.\s]+$', g):
                            amount_str = g
                        elif g.upper() in self.CURRENCY_MAP.values() or g in self.CURRENCY_MAP:
                            currency = self.CURRENCY_MAP.get(g.lower(), g.upper())

                if amount_str:
                    amount = self._parse_amount(amount_str)
                    if amount and amount > 0:
                        # Clean raw amount for pattern matching (remove spaces)
                        raw_clean = amount_str.replace(" ", "").replace("\xa0", "")
                        return amount, currency or self._find_currency(), raw_clean

        return None, None, None

    def _extract_vat(self) -> Optional[float]:
        """Extract VAT/Moms amount."""
        patterns = [
            # "VAT (0 %)                                                     0.00"
            r"VAT\s*\([^)]+\)\s+([0-9,.\s]+)",
            # "VAT - Sweden (25% on €11.74)                         €2.94"
            r"VAT\s*-\s*\w+\s*\([^)]+\)\s*([€$]?)([0-9,.\s]+)",
            # "Moms: 25.00" or "Moms 25.00"
            r"Moms[:\s]+([0-9,.\s]+)",
            # "MVA (25%): 500"
            r"MVA\s*\([^)]+\)[:\s]*([0-9,.\s]+)",
        ]
        for p in patterns:
            m = re.search(p, self.best, re.IGNORECASE)
            if m:
                for g in m.groups():
                    if g and re.match(r'^[0-9,.\s]+$', g.strip()):
                        return self._parse_amount(g.strip())
        return None

    def _extract_vendor(self) -> Optional[str]:
        """Extract vendor name from document content (NOT email metadata)."""
        # Look for company patterns - must be on single line, clean format
        patterns = [
            # "Invoice    Helleborg AS" pattern
            r"Invoice\s{2,}([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s]{1,30}(?:AB|AS|Inc|LLC|GmbH|Ltd|PBC|Oy))\s*$",
            # "From\nAsynkron AB" pattern
            r"From\n+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s]{1,30}(?:AB|AS|Inc|LLC|GmbH|Ltd|PBC|Oy))\s*$",
            # "Anthropic, PBC" at start of line
            r"^([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ,\s]{1,30}(?:AB|AS|Inc|LLC|GmbH|Ltd|PBC|Oy))\s*$",
            # Standalone company name line
            r"\n([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s]{2,25}\s(?:AB|AS|Inc|LLC|GmbH|Ltd|PBC|Oy))\n",
        ]
        for p in patterns:
            m = re.search(p, self.best or self.text, re.MULTILINE)
            if m:
                name = m.group(1).strip()
                # Validate: no newlines, reasonable length, not just suffix
                if "\n" not in name and 3 < len(name) < 50 and name.lower() not in ("ab", "as", "inc"):
                    return name
        return None

    def _extract_customer(self) -> Optional[str]:
        """Extract customer/bill-to name."""
        patterns = [
            r"Bill\s+to[:\s]+([A-Za-zÀ-ÿ\s]+(?:AB|AS|Inc|Organization)?)",
            r"Invoice\s+address\s+([A-Za-zÀ-ÿ\s]+(?:AB|AS|as))",
            r"Kund[:\s]+([A-Za-zÀ-ÿ\s]+(?:AB|AS))",
        ]
        for p in patterns:
            m = re.search(p, self.best, re.IGNORECASE)
            if m:
                name = m.group(1).strip()
                if len(name) > 2:
                    return name
        return None

    def _extract_org_number(self, is_vendor: bool) -> Optional[str]:
        """Extract organization number (Swedish, Norwegian, etc.)."""
        patterns = [
            r"(?:Org\.?\s*(?:nr|no|nummer)?|Corporate\s+identity\s+no\.?)[:\s]+([A-Z]{0,2}\s*[\d\s\-]+)",
            r"VAT\s+(?:identification\s+)?number[:\s]+([A-Z]{2}\d+)",
            r"(\d{6}-\d{4})",  # Swedish format
            r"(NO\s*\d{3}\s*\d{3}\s*\d{3}\s*MVA)",  # Norwegian format
        ]
        for p in patterns:
            m = re.search(p, self.best, re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return None

    # Month name to number mapping
    MONTHS = {
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12,
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
        # Swedish
        "januari": 1, "februari": 2, "mars": 3, "april": 4,
        "maj": 5, "juni": 6, "juli": 7, "augusti": 8,
        "september": 9, "oktober": 10, "november": 11, "december": 12,
    }

    def _normalize_date(self, date_str: str) -> Optional[str]:
        """Normalize date to YYYY-MM-DD format."""
        date_str = date_str.strip()

        # Already in correct format
        if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            return date_str

        # DD.MM.YYYY -> YYYY-MM-DD (European)
        m = re.match(r'^(\d{2})\.(\d{2})\.(\d{4})$', date_str)
        if m:
            return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"

        # MM/DD/YYYY -> YYYY-MM-DD (US format)
        m = re.match(r'^(\d{2})/(\d{2})/(\d{4})$', date_str)
        if m:
            return f"{m.group(3)}-{m.group(1)}-{m.group(2)}"

        # "Month DD, YYYY" or "Month DD YYYY" -> YYYY-MM-DD
        m = re.match(r'^([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})$', date_str)
        if m:
            month_name = m.group(1).lower()
            day = int(m.group(2))
            year = int(m.group(3))
            month = self.MONTHS.get(month_name)
            if month:
                return f"{year}-{month:02d}-{day:02d}"

        # "DD Month YYYY" -> YYYY-MM-DD
        m = re.match(r'^(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})$', date_str)
        if m:
            day = int(m.group(1))
            month_name = m.group(2).lower()
            year = int(m.group(3))
            month = self.MONTHS.get(month_name)
            if month:
                return f"{year}-{month:02d}-{day:02d}"

        # Use dateparser as fallback
        if HAS_DATEPARSER:
            dt = dateparser.parse(date_str, languages=["en", "sv", "no", "da"])
            if dt:
                return dt.strftime("%Y-%m-%d")

        return None

    def _parse_amount(self, amount_str: str) -> Optional[float]:
        """Parse amount string to float."""
        if HAS_PRICE_PARSER:
            price = Price.fromstring(amount_str)
            if price.amount:
                return float(price.amount)

        # Manual parsing
        clean = amount_str.replace(" ", "").replace("\xa0", "")

        # Handle different formats
        if "," in clean and "." in clean:
            # European: 1.234,56 (dot=thousands, comma=decimal)
            # US: 1,234.56 (comma=thousands, dot=decimal)
            if clean.index(",") > clean.index("."):
                # European format: 1.234,56
                clean = clean.replace(".", "").replace(",", ".")
            else:
                # US format: 1,234.56 - remove comma (thousands separator)
                clean = clean.replace(",", "")
        elif "," in clean:
            # Could be 1,234 (thousands) or 12,34 (decimal)
            parts = clean.split(",")
            if len(parts) == 2 and len(parts[1]) == 2:
                # Looks like decimal: 12,34
                clean = clean.replace(",", ".")
            else:
                # Thousands separator: 1,234
                clean = clean.replace(",", "")

        try:
            return float(clean)
        except ValueError:
            return None

    def _find_currency(self) -> Optional[str]:
        """Find currency mentioned in document."""
        for word, iso in self.CURRENCY_MAP.items():
            if re.search(rf'\b{re.escape(word)}\b', self.text, re.IGNORECASE):
                return iso
        return None

    def _detect_locale_detailed(self) -> tuple[str, dict]:
        """
        Detect document locale based on multiple signals.
        Returns (best_locale, scores_dict).
        """
        scores = {}
        text = self.best or self.text

        for locale, signals in self.LOCALE_SIGNALS.items():
            score = 0
            matches = []

            for category, patterns in signals.items():
                # Weight different categories
                weight = {
                    "currency": 2,      # Medium signal (can be different from locale)
                    "company": 4,       # Strong signal - company suffix is very telling
                    "labels": 2,        # Good signal
                    "org_number": 5,    # Very strong signal - definitive
                    "address": 3,       # Good signal for US (state + zip)
                    "city": 4,          # Strong signal - major US cities
                    "date": 1,          # Weak (formats overlap)
                    "amount": 1,        # Weak (formats overlap)
                }.get(category, 1)

                for pattern in patterns:
                    found = re.findall(pattern, text, re.IGNORECASE)
                    if found:
                        score += weight * len(found)
                        matches.append(f"{category}:{found[0][:20]}")

            scores[locale] = {"score": score, "matches": matches[:5]}

        # Find best locale
        best = max(scores.keys(), key=lambda k: scores[k]["score"])

        # Default to en-US if no strong signals
        if scores[best]["score"] < 2:
            best = "en-US"

        return best, scores

    def _detect_locale(self) -> str:
        """Return the detected locale."""
        return self.detected_locale

    def _compute_field_confidence(self, raw_values: dict, parsed_values: dict) -> dict:
        """
        Compute confidence for each extracted field based on locale format match.

        Returns dict with:
        - field_name: {"confidence": 0.0-1.0, "reason": "explanation"}
        """
        confidence = {}
        locale = self.detected_locale
        formats = self.LOCALE_FORMATS.get(locale, {})

        # Check amount format
        if raw_values.get("total_amount_raw"):
            raw = raw_values["total_amount_raw"]
            expected_pattern = formats.get("amount_pattern")
            if expected_pattern and re.match(expected_pattern, raw):
                confidence["total_amount"] = {
                    "confidence": 1.0,
                    "reason": f"Format matches {locale} pattern"
                }
            elif expected_pattern:
                # Check if it matches another locale's pattern
                other_match = None
                for other_locale, other_formats in self.LOCALE_FORMATS.items():
                    if other_locale != locale:
                        other_pattern = other_formats.get("amount_pattern")
                        if other_pattern and re.match(other_pattern, raw):
                            other_match = other_locale
                            break
                if other_match:
                    confidence["total_amount"] = {
                        "confidence": 0.6,
                        "reason": f"Format matches {other_match}, not {locale}"
                    }
                else:
                    confidence["total_amount"] = {
                        "confidence": 0.8,
                        "reason": "Non-standard format, but parsed successfully"
                    }

        # Check currency match
        if parsed_values.get("currency"):
            currency = parsed_values["currency"]
            expected = formats.get("expected_currencies", [])
            common = formats.get("common_currencies", [])

            if currency in expected:
                confidence["currency"] = {
                    "confidence": 1.0,
                    "reason": f"Expected currency for {locale}"
                }
            elif currency in common:
                confidence["currency"] = {
                    "confidence": 0.9,
                    "reason": f"Common currency for {locale} vendors"
                }
            else:
                confidence["currency"] = {
                    "confidence": 0.5,
                    "reason": f"Unusual currency for {locale}"
                }

        # Check date format
        for date_field in ["invoice_date", "due_date"]:
            raw_key = f"{date_field}_raw"
            if raw_values.get(raw_key):
                raw = raw_values[raw_key]
                date_patterns = formats.get("date_patterns", [])

                if any(re.match(p, raw) for p in date_patterns):
                    confidence[date_field] = {
                        "confidence": 1.0,
                        "reason": f"Date format matches {locale} pattern"
                    }
                else:
                    # Check if it matches another locale
                    other_match = None
                    for other_locale, other_formats in self.LOCALE_FORMATS.items():
                        if other_locale != locale:
                            other_patterns = other_formats.get("date_patterns", [])
                            if any(re.match(p, raw) for p in other_patterns):
                                other_match = other_locale
                                break
                    if other_match:
                        confidence[date_field] = {
                            "confidence": 0.7,
                            "reason": f"Date format matches {other_match}, not {locale}"
                        }
                    else:
                        confidence[date_field] = {
                            "confidence": 0.8,
                            "reason": "Parsed from non-standard format"
                        }

        return confidence

    def _build_anchors(self, vendor: Optional[str]) -> list[str]:
        """Build static identification anchors found verbatim in text."""
        candidates = [
            "Invoice number", "Invoice date", "Due date", "Total amount",
            "Fakturanummer", "Fakturadatum", "Förfallodatum", "Att betala",
            "Amount due", "Bill to", "VAT", "Moms", "Bankgiro", "IBAN",
            "Date of issue", "Date due", "Subtotal",
        ]

        anchors = []
        if vendor and vendor in self.text:
            anchors.append(vendor)

        for c in candidates:
            if c in self.text and c not in anchors:
                anchors.append(c)
                if len(anchors) >= 6:
                    break

        return anchors


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(json.dumps({"error": "Usage: parser.py <payload.txt>"}))
        sys.exit(1)

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        payload = f.read()

    result = InvoiceParser(payload).parse()
    print(json.dumps(result, indent=2, ensure_ascii=False))
