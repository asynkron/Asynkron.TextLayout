from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from .parsed_invoice import ParsedInvoice
from .unified_invoice_parser import UnifiedInvoiceParser


@dataclass(frozen=True)
class EmailContext:
    From: str | None
    Subject: str | None
    Body: str | None
    Date: datetime | date | None


class InvoiceParsingFacade:
    @staticmethod
    def ParseInvoice(extraction, email_context: EmailContext | None = None, logger=None) -> ParsedInvoice:
        if extraction is None or not getattr(extraction, "Variants", None):
            if logger:
                logger.warning("Invoice parsing skipped: no extraction variants")
            return ParsedInvoice(Confidence=0)

        try:
            email_date = None
            if email_context and email_context.Date is not None:
                email_date = email_context.Date.strftime("%Y-%m-%d")

            return UnifiedInvoiceParser.Parse(
                extraction,
                email_subject=email_context.Subject if email_context else None,
                email_from=email_context.From if email_context else None,
                email_date=email_date,
                email_body=email_context.Body if email_context else None,
            )
        except Exception as exc:
            if logger:
                logger.error("Invoice parsing failed", exc_info=exc)
            return ParsedInvoice(
                RawText=getattr(extraction, "BestText", None),
                Confidence=0,
                Warnings=["ParsingError"],
            )
