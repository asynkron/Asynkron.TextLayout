from __future__ import annotations

import re

from ..anchored_extractor import AnchoredExtractor
from ..extraction_result import ExtractionResult
from ..i_vendor_name_extractor import IVendorNameExtractor

_VALUE_PATTERN = (
    r"\b(?!(?:Your|The|From|von|från|Bill|Invoice|Receipt|Payment|Sent|Kvitto|Faktura|Rechnung|Thank|Thanks)\b)"
    r"([A-Z][A-Za-z0-9&\-\.,]*(?:[ \t&\-](?!from\b|von\b|från\b)[A-Z][A-Za-z0-9&\-\.,]*){0,3})"
    r"[ \t]+(s\.?r\.?o|Ltd|LLC|Inc|AB|AS|Oy|GmbH|Corp|Limited|PLC|PBC)\b\.?"
)
_COMPANY_WITH_SUFFIX_PATTERN = re.compile(_VALUE_PATTERN)
_WHITESPACE_PATTERN = re.compile(r"\s+")
_TRAILING_PUNCTUATION_PATTERN = re.compile(r"[\.,]+$")


class CompanyWithSuffixExtractor(IVendorNameExtractor):
    @property
    def Name(self) -> str:
        return "Company with legal suffix"

    def Extract(self, context):
        results = self.ExtractAll(context)
        return ExtractionResult.NoMatch if not results else max(results, key=lambda result: result.Votes)

    def ExtractAll(self, context):
        matches = list(_COMPANY_WITH_SUFFIX_PATTERN.finditer(context.Text))
        if not matches:
            return []

        results: list[ExtractionResult] = []

        for match in matches:
            company_name = match.group(1).strip()
            suffix = match.group(2).strip()
            vendor = f"{company_name} {suffix}"
            vendor = _WHITESPACE_PATTERN.sub(" ", vendor)
            vendor = _TRAILING_PUNCTUATION_PATTERN.sub("", vendor).strip()

            if len(vendor) < 5 or len(vendor) > 50:
                continue

            match_text = match.group(0)
            temp_result = AnchoredExtractor.FindAnchored(
                context.Text,
                re.escape(match_text),
                AnchoredExtractor.VendorNameAnchors,
                base_votes=2,
            )

            votes = temp_result[0].TotalVotes if temp_result else 2
            results.append(ExtractionResult(vendor, votes, match_text))

        return results
