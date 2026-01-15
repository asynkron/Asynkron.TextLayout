from __future__ import annotations

import re
from datetime import date

from .locale import Locale

_MONTH_NAMES: dict[str, str] = {
    # English full
    "january": "01",
    "february": "02",
    "march": "03",
    "april": "04",
    "may": "05",
    "june": "06",
    "july": "07",
    "august": "08",
    "september": "09",
    "october": "10",
    "november": "11",
    "december": "12",
    # English abbreviations
    "jan": "01",
    "feb": "02",
    "mar": "03",
    "apr": "04",
    "jun": "06",
    "jul": "07",
    "aug": "08",
    "sep": "09",
    "oct": "10",
    "nov": "11",
    "dec": "12",
    # Swedish full
    "januari": "01",
    "februari": "02",
    "mars": "03",
    "maj": "05",
    "juni": "06",
    "juli": "07",
    "augusti": "08",
    "oktober": "10",
    # Swedish abbreviations
    "sept": "09",
    "okt": "10",
    # German
    "januar": "01",
    "märz": "03",
    "mai": "05",
    "dezember": "12",
}


def _build_month_name_pattern() -> str:
    names = sorted({name for name in _MONTH_NAMES.keys()}, key=len, reverse=True)
    escaped = [re.escape(name) for name in names]
    return "|".join(escaped)


_MONTH_NAME_PATTERN = _build_month_name_pattern()

DateTokenPattern = (
    r"\d{4}-\d{2}-\d{2}(?!\d)|"
    r"\d{1,2}\.\d{1,2}\.\d{4}(?!\d)|"
    r"\d{1,2}/\d{1,2}/\d{4}(?!\d)|"
    rf"\b(?:{_MONTH_NAME_PATTERN})\.?\s+\d{{1,2}},?\s+\d{{4}}\b|"
    rf"\b\d{{1,2}}\s+(?:{_MONTH_NAME_PATTERN})\.?\s+\d{{4}}\b"
)

_ISO_DATE_PATTERN = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
_EUROPEAN_DATE_PATTERN = re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{4})")
_SLASH_DATE_PATTERN = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})")


class DateParser:
    @staticmethod
    def Parse(text: str, locale: Locale) -> date | None:
        iso_match = _ISO_DATE_PATTERN.search(text)
        if iso_match:
            try:
                year = int(iso_match.group(1))
                month = int(iso_match.group(2))
                day = int(iso_match.group(3))
                return date(year, month, day)
            except ValueError:
                pass

        dot_match = _EUROPEAN_DATE_PATTERN.search(text)
        if dot_match:
            first = int(dot_match.group(1))
            second = int(dot_match.group(2))
            year = int(dot_match.group(3))
            if locale != Locale.US and first <= 31 and second <= 12:
                try:
                    return date(year, second, first)
                except ValueError:
                    pass

        slash_match = _SLASH_DATE_PATTERN.search(text)
        if slash_match:
            first = int(slash_match.group(1))
            second = int(slash_match.group(2))
            year = int(slash_match.group(3))
            if locale == Locale.US:
                if first <= 12 and second <= 31:
                    try:
                        return date(year, first, second)
                    except ValueError:
                        pass
            else:
                if first <= 31 and second <= 12:
                    try:
                        return date(year, second, first)
                    except ValueError:
                        pass

        for month_name, month_num in _MONTH_NAMES.items():
            pattern1 = rf"{re.escape(month_name)}\.?\s+(\d{{1,2}}),?\s+(\d{{4}})"
            match1 = re.search(pattern1, text, re.IGNORECASE)
            if match1:
                try:
                    day = int(match1.group(1))
                    year = int(match1.group(2))
                    month = int(month_num)
                    return date(year, month, day)
                except ValueError:
                    pass

            pattern2 = rf"(\d{{1,2}})\s+{re.escape(month_name)}\.?\s+(\d{{4}})"
            match2 = re.search(pattern2, text, re.IGNORECASE)
            if match2:
                try:
                    day = int(match2.group(1))
                    year = int(match2.group(2))
                    month = int(month_num)
                    return date(year, month, day)
                except ValueError:
                    pass

        return None
