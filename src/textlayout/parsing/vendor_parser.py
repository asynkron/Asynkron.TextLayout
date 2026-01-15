from __future__ import annotations

import re
from dataclasses import dataclass

from .locale import Locale
from .extractors.extraction_context import ExtractionContext
from .extractors.extractor_aggregator import ExtractorAggregator
from .extractors.extractor_registry import ExtractorRegistry

_EXCLUDE_PHRASES = ["thanks for", "thank you", "questions", "visit", "contact", "support"]
_COMPANY_FULL_PATTERN = r"([A-Z][A-Za-z0-9&\-\.,]*(?:[ \t]+[A-Z][A-Za-z0-9&\-\.,]*){0,4})[ \t]+(s\.?r\.?o|Ltd|LLC|Inc|AB|AS|Oy|GmbH|Corp|Limited|PLC|PBC)\b\.?"

_FORWARDED_REGEX = re.compile(r"^(Fwd?|Fw|Vidarebefordrat|Weitergeleitet):\s*", re.IGNORECASE)
_FORWARDED_REGEX2 = re.compile(r"[-]+\s*(Forwarded|Original)\s+(message|Message)[-]+", re.IGNORECASE)
_QUOTED_EMAIL_FROM_PATTERN = re.compile(r"^>\s*From:", re.MULTILINE)
_QUOTED_NAME_PATTERN = re.compile(r"\"([^\"]+)\"")
_NAME_BEFORE_ANGLE_PATTERN = re.compile(r"^([^<]+)<")
_INVOICE_SUBJECT_PREFIX_PATTERN = re.compile(
    r"^(Invoice|Invoices|Receipt|Billing|Payment|Order)\s+(from\s+)?",
    re.IGNORECASE,
)
_GENERIC_EMAIL_SUFFIX_PATTERN = re.compile(
    r"[-_\s]?(Billing|Payments|Invoice|Invoices|Support|Noreply|NOREPLY|Sales)\s*$",
    re.IGNORECASE,
)
_TRAILING_DASHES_PATTERN = re.compile(r"[-_]+$")
_DOMAIN_FROM_EMAIL_PATTERN = re.compile(r"@([\w\-\.]+\.\w+)")
_TRAILING_PUNCTUATION_PATTERN = re.compile(r"[\.,]+$")
_ACCOUNT_PREFIX_PATTERN = re.compile(r"^account\b", re.IGNORECASE)
_COMPANY_WITH_SUFFIX_PATTERN = re.compile(_COMPANY_FULL_PATTERN)
_CUSTOMER_ANCHOR_REGEX = re.compile(r"\s+")
_CUSTOMER_FIELD_ANCHOR_PATTERN = re.compile(
    r"(bill\s*to|buyer|customer|sold\s*to|ship\s*to)[:\s]*$",
    re.IGNORECASE,
)
_FAKTURA_REGEX = re.compile(r"^\d+[\s\-/]|^\d{4,}")
_CUSTOMER_REGEX = re.compile(
    r"invoice|faktura|receipt|kvitto|page\s+\d|^(tel|phone|fax|email|www\.|http|bill\s+to)",
    re.IGNORECASE,
)
_COMPANY_SUFFIX = re.compile(
    r"(sold\s+to|bill\s+to|customer|buyer|fakturaadress|billing\s+address|account\s+information)",
    re.IGNORECASE,
)
_COMPANY_SUFFIX2 = re.compile(
    r"\b(s\.?r\.?o|Ltd|LLC|Inc|AB|AS|Oy|GmbH|Corp|Limited|PLC|PBC)\b\.?\s*$",
    re.IGNORECASE,
)
_COMPANY_SUFFIX_PATTERN = re.compile(
    r"\b(s\.?r\.?o|Ltd|LLC|Inc|AB|AS|Oy|GmbH|Corp|Limited|PLC|PBC)\b\.?\s*$"
)
_INVOICE_DOCUMENT_PREFIX_PATTERN = re.compile(r"^(invoice|receipt|payment|bill|faktura|kvitto)\b\s*", re.IGNORECASE)
_CURRENCY_PREFIX_PATTERN = re.compile(r"^(eur|usd|sek|nok|dkk|gbp)\b\s+", re.IGNORECASE)
_ACCOUNT_WORD_PREFIX_PATTERN = re.compile(r"^account\b\s+", re.IGNORECASE)
_CUSTOMER_SECTION_HEADER_PATTERN = re.compile(
    r"\b(bill\s*to|billed\s*to|sold\s*to|ship\s*to|invoice\s*to|customer|buyer|faktureringsadress|billing\s+address|account\s+information)\b",
    re.IGNORECASE,
)
_ANGLE_BRACKET_CONTENT_PATTERN = re.compile(r"<([^>]+)>")
_URL_REGEX = re.compile(r"([\w.+-]+@[\w.-]+)")
_ALPHA_NUMERIC_REGEX = re.compile(r"[^a-z0-9]+")

_SENDER_HINT_STOP_TOKENS = {
    "ab",
    "ag",
    "as",
    "co",
    "company",
    "companies",
    "corp",
    "gmbh",
    "group",
    "holdings",
    "inc",
    "limited",
    "llc",
    "ltd",
    "oy",
    "pbc",
    "plc",
    "sa",
    "sro",
    "billing",
    "invoice",
    "invoices",
    "payment",
    "payments",
    "noreply",
    "no",
    "reply",
    "mail",
    "email",
    "notification",
    "notifications",
    "support",
    "services",
    "solutions",
    "systems",
    "technologies",
    "technology",
    "communications",
}

_COMMON_SECOND_LEVEL_DOMAINS = {"co", "com", "net", "org"}


class VendorParser:
    @staticmethod
    def Extract(
        text: str,
        lines: list[str],
        sender_hint: str | None = None,
        email_body_hint: str | None = None,
        email_subject: str | None = None,
    ) -> str | None:
        is_forwarded = VendorParser.IsForwardedEmail(email_subject, email_body_hint)

        original_sender = None
        if is_forwarded and email_body_hint:
            original_sender = VendorParser.ExtractOriginalSenderFromForward(email_body_hint)

        effective_sender_hint = original_sender if is_forwarded else sender_hint

        pdf_vendor = VendorParser._extract_from_text(text, effective_sender_hint)
        if pdf_vendor is not None:
            return pdf_vendor

        if effective_sender_hint:
            vendor = VendorParser.ExtractFromSender(effective_sender_hint, text)
            if vendor is not None:
                return vendor

        line_vendor = VendorParser.ExtractFromLines(lines)
        if line_vendor is not None:
            return line_vendor

        if email_body_hint:
            vendor = VendorParser._extract_from_text(email_body_hint, effective_sender_hint)
            if vendor is not None:
                return vendor

        return None

    @staticmethod
    def IsForwardedEmail(subject: str | None, body: str | None) -> bool:
        if subject and _FORWARDED_REGEX.search(subject):
            return True

        if body:
            if _FORWARDED_REGEX2.search(body):
                return True

            if _QUOTED_EMAIL_FROM_PATTERN.search(body):
                return True

        return False

    @staticmethod
    def ExtractOriginalSenderFromForward(body: str) -> str | None:
        forward_markers = [
            r"-+\s*Forwarded message\s*-+",
            r"-+\s*Original Message\s*-+",
            r"-+\s*Vidarebefordrat meddelande\s*-+",
            r"-+\s*Weitergeleitete Nachricht\s*-+",
            r"Begin forwarded message:",
        ]

        search_text = body
        for marker in forward_markers:
            marker_match = re.search(marker, body, re.IGNORECASE)
            if marker_match:
                search_text = body[marker_match.start() + len(marker_match.group(0)) :]
                break

        from_patterns = [
            r"From:\s*(.+?)\s*<([^>]+)>",
            r"From:\s*([^<\r\n]+@[^\s\r\n]+)",
            r"Från:\s*(.+?)\s*<([^>]+)>",
            r"Von:\s*(.+?)\s*<([^>]+)>",
        ]

        for pattern in from_patterns:
            match = re.search(pattern, search_text, re.IGNORECASE)
            if match:
                if match.lastindex and match.lastindex > 1 and match.group(1).strip():
                    name = match.group(1).strip()
                    email = match.group(2).strip()
                    return f"{name} <{email}>"
                return match.group(1).strip()

        return None

    @staticmethod
    def ExtractFromSender(sender: str, pdf_text: str | None = None) -> str | None:
        quoted_match = _QUOTED_NAME_PATTERN.search(sender)
        if quoted_match:
            quoted = quoted_match.group(1).strip()
            if len(quoted) >= 3:
                return quoted

        name_match = _NAME_BEFORE_ANGLE_PATTERN.search(sender)
        if name_match:
            name = name_match.group(1).strip()
            name = _INVOICE_SUBJECT_PREFIX_PATTERN.sub("", name)
            name = _GENERIC_EMAIL_SUFFIX_PATTERN.sub("", name)
            name = _TRAILING_DASHES_PATTERN.sub("", name).strip()
            if len(name) >= 3:
                return name

        full_domain_match = _DOMAIN_FROM_EMAIL_PATTERN.search(sender)
        if full_domain_match:
            full_domain = full_domain_match.group(1).lower().strip()
            domain_parts = full_domain.split(".")
            skip_subdomains = {
                "mail",
                "email",
                "smtp",
                "noreply",
                "no-reply",
                "billing",
                "invoices",
                "notifications",
                "alerts",
            }

            if len(domain_parts) >= 2:
                candidate_index = len(domain_parts) - 2
                domain = domain_parts[candidate_index]
                if domain in skip_subdomains and candidate_index > 0:
                    domain = domain_parts[candidate_index - 1]
            else:
                domain = domain_parts[0]

            if pdf_text:
                company_pattern = rf"({re.escape(domain)}[A-Za-z\s&\-\.,]*\b(?:s\.?r\.?o|Ltd|LLC|Inc|AB|AS|Oy|GmbH|Corp|Limited|PLC|PBC))\b"
                domain_company_match = re.search(company_pattern, pdf_text, re.IGNORECASE)
                if domain_company_match:
                    vendor = domain_company_match.group(1).strip()
                    vendor = _TRAILING_PUNCTUATION_PATTERN.sub("", vendor).strip()
                    if 5 <= len(vendor) <= 50:
                        return vendor

            if domain:
                return domain[0].upper() + domain[1:]

        return None

    @staticmethod
    def _extract_from_text(text: str, sender_hint: str | None = None) -> str | None:
        context = ExtractionContext(text, [], Locale.US, sender_hint)
        candidates = ExtractorAggregator.ExtractAll([text], context, ExtractorRegistry.VendorNameExtractors)

        ordered_candidates = sorted(
            (
                {
                    "value": candidate[0],
                    "total_votes": candidate[1],
                    "bonus_votes": VendorParser._get_sender_hint_bonus(candidate[0], sender_hint),
                }
                for candidate in candidates
            ),
            key=lambda candidate: (
                candidate["total_votes"] + candidate["bonus_votes"],
                len([token for token in candidate["value"].split(" ") if token]),
                len(candidate["value"]),
            ),
            reverse=True,
        )

        for candidate in ordered_candidates:
            if _ACCOUNT_PREFIX_PATTERN.search(candidate["value"]):
                continue

            vendor = VendorParser._normalize_vendor(candidate["value"])
            if not vendor:
                continue

            if not VendorParser._is_customer_context(text, vendor):
                return vendor

        matches = list(_COMPANY_WITH_SUFFIX_PATTERN.finditer(text))
        for match in matches:
            name = match.group(1).strip()
            suffix = match.group(2).strip()

            vendor = f"{name} {suffix}"
            vendor = _CUSTOMER_ANCHOR_REGEX.sub(" ", vendor)
            vendor = _TRAILING_PUNCTUATION_PATTERN.sub("", vendor).strip()
            vendor = VendorParser._normalize_vendor(vendor)

            if not vendor:
                continue

            if any(phrase in vendor.lower() for phrase in _EXCLUDE_PHRASES):
                continue

            match_index = match.start()
            text_before = text[:match_index]
            if _CUSTOMER_FIELD_ANCHOR_PATTERN.search(text_before):
                continue

            if 5 <= len(vendor) <= 50:
                if VendorParser._is_customer_context(text, vendor):
                    continue

                return vendor

        return None

    @staticmethod
    def ExtractFromLines(lines: list[str]) -> str | None:
        skip_lines = 0
        for line in lines[:30]:
            if skip_lines > 0:
                skip_lines -= 1
                continue

            if not line or len(line) < 5 or len(line) > 60:
                continue

            if _FAKTURA_REGEX.search(line):
                continue

            if _CUSTOMER_REGEX.search(line):
                continue

            if any(phrase in line.lower() for phrase in _EXCLUDE_PHRASES):
                continue

            if _COMPANY_SUFFIX.search(line):
                skip_lines = 4
                continue

            if _COMPANY_SUFFIX2.search(line):
                suffix_match = _COMPANY_SUFFIX_PATTERN.search(line)
                if suffix_match:
                    suffix = suffix_match.group(1)
                    if (
                        suffix.lower() in {"ab", "as"}
                        and not (suffix.lower() == suffix.lower())
                    ):
                        continue

                vendor = VendorParser._normalize_vendor(line.strip())
                if vendor:
                    return vendor

        return None

    @staticmethod
    def _normalize_vendor(vendor: str) -> str:
        if not vendor or not vendor.strip():
            return vendor

        vendor = _INVOICE_DOCUMENT_PREFIX_PATTERN.sub("", vendor)
        vendor = _CURRENCY_PREFIX_PATTERN.sub("", vendor)
        vendor = _ACCOUNT_WORD_PREFIX_PATTERN.sub("", vendor)
        return vendor.strip()

    @staticmethod
    def _is_customer_context(text: str, vendor: str) -> bool:
        if not text or not vendor:
            return False

        matches = list(re.finditer(re.escape(vendor), text, re.IGNORECASE))
        if not matches:
            return False

        lines = text.split("\n")
        line_starts = [0]
        for i, char in enumerate(text):
            if char == "\n":
                line_starts.append(i + 1)

        for match in matches:
            line_index = VendorParser._find_line_index(line_starts, match.start())
            start_line = max(0, line_index - 12)
            has_anchor = False

            for i in range(line_index, start_line - 1, -1):
                line = lines[i]
                if _CUSTOMER_SECTION_HEADER_PATTERN.search(line):
                    has_anchor = True
                    break

            if not has_anchor:
                return False

        return True

    @staticmethod
    def _get_sender_hint_bonus(vendor: str, sender_hint: str | None) -> int:
        if not vendor or not sender_hint:
            return 0

        sender_tokens = VendorParser._get_sender_hint_tokens(sender_hint)
        if not sender_tokens:
            return 0

        vendor_tokens = VendorParser._tokenize_hint(vendor)
        overlap_count = len([token for token in vendor_tokens if token in sender_tokens])
        if overlap_count <= 0:
            return 0

        return 3 if overlap_count >= 2 else 2

    @staticmethod
    def _get_sender_hint_tokens(sender_hint: str) -> set[str]:
        tokens: set[str] = set()

        email = VendorParser._extract_email_address(sender_hint)
        if email:
            domain = VendorParser._get_company_domain_from_email(email)
            if domain:
                tokens.add(domain)

        display_name = VendorParser._extract_display_name(sender_hint)
        if display_name:
            for token in VendorParser._tokenize_hint(display_name):
                tokens.add(token)

        return tokens

    @staticmethod
    def _extract_email_address(sender_hint: str) -> str | None:
        angle_match = _ANGLE_BRACKET_CONTENT_PATTERN.search(sender_hint)
        if angle_match:
            return angle_match.group(1).strip()

        email_match = _URL_REGEX.search(sender_hint)
        return email_match.group(1).strip() if email_match else None

    @staticmethod
    def _extract_display_name(sender_hint: str) -> str | None:
        quoted_match = _QUOTED_NAME_PATTERN.search(sender_hint)
        if quoted_match:
            return quoted_match.group(1).strip()

        name_match = _NAME_BEFORE_ANGLE_PATTERN.search(sender_hint)
        return name_match.group(1).strip() if name_match else None

    @staticmethod
    def _get_company_domain_from_email(email: str) -> str | None:
        at_index = email.rfind("@")
        if at_index < 0 or at_index == len(email) - 1:
            return None

        domain = email[at_index + 1 :].lower().strip()
        if not domain:
            return None

        parts = [part for part in domain.split(".") if part]
        if not parts:
            return None

        if len(parts) == 1:
            return parts[0]

        index = len(parts) - 2
        if len(parts) >= 3 and parts[-2] in _COMMON_SECOND_LEVEL_DOMAINS:
            index = len(parts) - 3

        if index < 0:
            index = 0

        return parts[index]

    @staticmethod
    def _tokenize_hint(value: str) -> list[str]:
        tokens: list[str] = []
        for token in _ALPHA_NUMERIC_REGEX.split(value.lower()):
            if len(token) < 3:
                continue

            if token in _SENDER_HINT_STOP_TOKENS:
                continue

            tokens.append(token)

        return tokens

    @staticmethod
    def _find_line_index(line_starts: list[int], char_index: int) -> int:
        low = 0
        high = len(line_starts) - 1

        while low <= high:
            mid = (low + high) // 2
            if line_starts[mid] <= char_index:
                low = mid + 1
            else:
                high = mid - 1

        return max(0, high)
