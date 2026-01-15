from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from .locale import Locale, LocaleDetector
from .money_parser import MoneyParser
from .parsed_invoice import InvoiceLineItem, ParsedInvoice
from .vendor_parser import VendorParser
from .extractors.extraction_context import ExtractionContext
from .extractors.extractor_aggregator import ExtractorAggregator
from .extractors.extractor_registry import ExtractorRegistry

_LINE_ITEM_REGEX = re.compile(r"^(.{10,}?)\s+([\d\s]*\d[,\.]\d{2})\s*(?:€|\$|£|kr|SEK|EUR|USD)?\s*$")


@dataclass(frozen=True)
class PdfExtractionSection:
    Name: str
    Text: str


class UnifiedInvoiceParser:
    @staticmethod
    def Parse(
        pdf_extraction,
        email_subject: str | None = None,
        email_from: str | None = None,
        email_date: str | None = None,
        email_body: str | None = None,
    ) -> ParsedInvoice:
        sections = []
        if pdf_extraction is not None:
            sections = [
                PdfExtractionSection(variant.ExtractorName, variant.Text)
                for variant in pdf_extraction.Variants
            ]

        return UnifiedInvoiceParser._parse_internal(
            sections,
            pdf_extraction.BestText if pdf_extraction is not None else None,
            email_subject,
            email_from,
            email_date,
            email_body,
        )

    @staticmethod
    def _parse_internal(
        sections: list[PdfExtractionSection],
        raw_pdf_text: str | None,
        email_subject: str | None,
        email_from: str | None,
        email_date: str | None,
        email_body: str | None,
    ) -> ParsedInvoice:
        text_documents: list[str] = []
        pdf_documents: list[str] = []

        email_document = UnifiedInvoiceParser._build_email_document(email_from, email_subject, email_body)
        if email_document:
            text_documents.append(email_document)

        for section in sections:
            if section.Text and section.Text.strip():
                text_documents.append(section.Text)
                pdf_documents.append(section.Text)

        preferred_pdf_documents = UnifiedInvoiceParser._select_preferred_pdf_documents(sections)

        if not text_documents:
            return ParsedInvoice(RawText=raw_pdf_text, Confidence=0)

        combined_text = "\n".join(text_documents)
        lines = [line.strip() for line in combined_text.split("\n") if line != ""]
        if preferred_pdf_documents:
            pdf_combined_text = "\n".join(preferred_pdf_documents)
        else:
            pdf_combined_text = "\n".join(pdf_documents) if pdf_documents else combined_text
        pdf_lines = [line.strip() for line in pdf_combined_text.split("\n") if line != ""]
        pdf_primary_text = (
            preferred_pdf_documents[0]
            if preferred_pdf_documents
            else (pdf_documents[0] if pdf_documents else combined_text)
        )
        pdf_primary_lines = [line.strip() for line in pdf_primary_text.split("\n") if line != ""]
        locale = LocaleDetector.Detect(combined_text)
        context = ExtractionContext(combined_text, lines, locale)
        pdf_locale = LocaleDetector.Detect(pdf_combined_text) if (preferred_pdf_documents or pdf_documents) else locale
        pdf_context = ExtractionContext(pdf_combined_text, pdf_lines, pdf_locale)
        pdf_preferred_documents = preferred_pdf_documents or (pdf_documents if pdf_documents else text_documents)

        invoice = ParsedInvoice(RawText=raw_pdf_text or pdf_combined_text, Confidence=0.0)

        invoice.InvoiceNumber = ExtractorAggregator.ExtractBest(
            text_documents,
            context,
            ExtractorRegistry.InvoiceNumberExtractors,
        )

        invoice.Currency = ExtractorAggregator.ExtractBest(
            pdf_preferred_documents,
            pdf_context,
            ExtractorRegistry.CurrencyExtractors,
        )

        total_amount_raw = ExtractorAggregator.ExtractBest(
            pdf_preferred_documents,
            pdf_context,
            ExtractorRegistry.TotalAmountExtractors,
        )
        invoice.TotalAmount = UnifiedInvoiceParser._parse_amount(total_amount_raw, pdf_context.Locale)

        invoice.InvoiceDateRaw = ExtractorAggregator.ExtractBest(
            pdf_preferred_documents,
            pdf_context,
            ExtractorRegistry.InvoiceDateExtractors,
        )

        invoice.DueDateRaw = ExtractorAggregator.ExtractBest(
            pdf_preferred_documents,
            pdf_context,
            ExtractorRegistry.DueDateExtractors,
        )

        vat_amount_raw = ExtractorAggregator.ExtractBest(
            pdf_preferred_documents,
            pdf_context,
            ExtractorRegistry.VatAmountExtractors,
        )
        invoice.VatAmount = UnifiedInvoiceParser._parse_amount(vat_amount_raw, pdf_context.Locale)

        vat_rate_raw = ExtractorAggregator.ExtractBest(
            pdf_preferred_documents,
            pdf_context,
            ExtractorRegistry.VatRateExtractors,
        )
        invoice.VatRate = UnifiedInvoiceParser._parse_rate(vat_rate_raw)

        total_excluding_vat_raw = ExtractorAggregator.ExtractBest(
            pdf_preferred_documents,
            pdf_context,
            ExtractorRegistry.SubtotalExtractors,
        )
        invoice.TotalExcludingVat = UnifiedInvoiceParser._parse_amount(total_excluding_vat_raw, pdf_context.Locale)

        invoice.VendorName = VendorParser.Extract(
            pdf_primary_text,
            pdf_primary_lines,
            email_from,
            email_body,
            email_subject,
        )

        UnifiedInvoiceParser._calculate_missing_vat_values(invoice)

        if not invoice.Currency:
            invoice.Currency = MoneyParser.DetectCurrency(combined_text)

        invoice.LineItems = UnifiedInvoiceParser._extract_line_items(lines, locale)
        invoice.Confidence = UnifiedInvoiceParser._calculate_confidence(invoice)

        if (not invoice.InvoiceDateRaw or not invoice.InvoiceDateRaw.strip()) and email_date:
            invoice.InvoiceDateRaw = email_date

        return invoice

    @staticmethod
    def _select_preferred_pdf_documents(sections: list[PdfExtractionSection]) -> list[str]:
        if not sections:
            return []

        preferred_order = [
            "asynkron-textlayout",
            "Docnet-PDFium",
            "PdfPig-Default",
            "PdfPig-Layout",
            "PdfPig-NearestNeighbour",
            "default",
        ]

        preferred: list[str] = []
        for name in preferred_order:
            for section in sections:
                if section.Name.lower() == name.lower():
                    preferred.append(section.Text)

        if not preferred:
            preferred.extend(section.Text for section in sections)

        return preferred

    @staticmethod
    def _build_email_document(from_value: str | None, subject: str | None, body: str | None) -> str | None:
        parts: list[str] = []

        if from_value and from_value.strip():
            parts.append(f"From: {from_value}")

        if subject and subject.strip():
            parts.append(f"Subject: {subject}")

        if body and body.strip():
            parts.append(body)

        if not parts:
            return None

        return "\n".join(parts)

    @staticmethod
    def _calculate_missing_vat_values(invoice: ParsedInvoice) -> None:
        if invoice.TotalAmount is not None and invoice.VatAmount is not None and invoice.TotalExcludingVat is None:
            invoice.TotalExcludingVat = invoice.TotalAmount - invoice.VatAmount
        elif invoice.TotalExcludingVat is not None and invoice.VatAmount is not None and invoice.TotalAmount is None:
            invoice.TotalAmount = invoice.TotalExcludingVat + invoice.VatAmount
        elif invoice.TotalExcludingVat is not None and invoice.VatRate is not None and invoice.TotalAmount is None:
            invoice.VatAmount = invoice.TotalExcludingVat * invoice.VatRate / Decimal("100")
            invoice.TotalAmount = invoice.TotalExcludingVat + invoice.VatAmount
        elif invoice.TotalAmount is not None and invoice.TotalExcludingVat is not None and invoice.VatAmount is None:
            invoice.VatAmount = invoice.TotalAmount - invoice.TotalExcludingVat

        if invoice.VatAmount is not None and invoice.TotalAmount is not None and invoice.VatAmount >= invoice.TotalAmount:
            invoice.VatAmount = None

    @staticmethod
    def _extract_line_items(lines: list[str], locale: Locale) -> list[InvoiceLineItem]:
        items: list[InvoiceLineItem] = []

        skip_patterns = [
            r"^(invoice|faktura|total|subtotal|vat|moms|tax|date|page|from:|to:|bill\s*to|ship\s*to)",
            r"\b(california|new york|texas|florida|washington|georgia|illinois|massachusetts)\b",
            r"\b(san francisco|los angeles|seattle|atlanta|chicago|boston|buford|palo alto)\b",
            r"\b(stockholm|göteborg|malmö|huddinge|oslo|copenhagen|berlin|münchen|paris|amsterdam|praha|prague)\b",
            r"\bCA\s+\d{5}\b",
            r"\bGA\s+\d{5}\b",
            r"\b\d{5}-\d{4}\b",
            r"\bwww\.|http|@.*\.(com|org|se|io|net)",
            r"thank|receipt|payment.*method|paid.*on|ending|mastercard|visa|card",
            r"^\s*\d+\s+\d+\s*$",
            r"GST|HST|PST|VAT\s*:",
            r"australia|canada|india|united kingdom|uk:|eu:",
        ]

        for line in lines:
            if len(line) < 10 or len(line) > 100:
                continue

            if any(re.search(pattern, line, re.IGNORECASE) for pattern in skip_patterns):
                continue

            match = _LINE_ITEM_REGEX.match(line)
            if match:
                desc = match.group(1).strip()
                amount_str = match.group(2)

                raw_amount = amount_str.replace(" ", "").replace(",", "").replace(".", "")
                if len(raw_amount) <= 5:
                    try:
                        int_val = int(raw_amount)
                    except ValueError:
                        int_val = None

                    if int_val is not None:
                        if len(raw_amount) == 5 or 2020 <= int_val <= 2099:
                            continue

                amount = MoneyParser.ParseAmount(amount_str, locale)

                if amount is not None and amount > Decimal("0.50") and amount < Decimal("100000") and desc:
                    items.append(InvoiceLineItem(Description=desc, Amount=amount))

        return items

    @staticmethod
    def _parse_amount(raw: str | None, locale: Locale) -> Decimal | None:
        if not raw or not raw.strip():
            return None
        return MoneyParser.ParseAmount(raw, locale)

    @staticmethod
    def _parse_rate(raw: str | None) -> Decimal | None:
        if not raw or not raw.strip():
            return None

        normalized = raw.replace(",", ".")
        try:
            return Decimal(normalized)
        except (InvalidOperation, ValueError):
            return None

    @staticmethod
    def _calculate_confidence(invoice: ParsedInvoice) -> float:
        score = 0.0
        max_score = 8.0

        if invoice.InvoiceNumber:
            score += 1.0

        if invoice.VendorName:
            score += 1.0

        if invoice.InvoiceDateRaw and invoice.InvoiceDateRaw.strip():
            score += 1.5

        if invoice.DueDateRaw and invoice.DueDateRaw.strip():
            score += 0.5

        if invoice.TotalAmount is not None:
            score += 2.0

        if invoice.VatAmount is not None:
            score += 1.0

        if invoice.Currency:
            score += 0.5

        if invoice.LineItems:
            score += 0.5

        return score / max_score
