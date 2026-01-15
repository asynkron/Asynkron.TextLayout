from __future__ import annotations

from .currency.anchored_currency_extractor import AnchoredCurrencyExtractor
from .currency.detected_currency_extractor import DetectedCurrencyExtractor
from .invoice_date.anchored_due_date_extractor import AnchoredDueDateExtractor
from .invoice_date.anchored_invoice_date_extractor import AnchoredInvoiceDateExtractor
from .invoice_date.any_date_extractor import AnyDateExtractor
from .invoice_number.alpha_numeric_hyphen_extractor import AlphaNumericHyphenExtractor
from .invoice_number.credit_note_number_extractor import CreditNoteNumberExtractor
from .invoice_number.invoice_hash_extractor import InvoiceHashExtractor
from .invoice_number.invoice_no_extractor import InvoiceNoExtractor
from .invoice_number.invoice_number_colon_extractor import InvoiceNumberColonExtractor
from .invoice_number.invoice_number_no_space_extractor import InvoiceNumberNoSpaceExtractor
from .invoice_number.invoice_space_extractor import InvoiceSpaceExtractor
from .invoice_number.inv_prefix_extractor import InvPrefixExtractor
from .invoice_number.receipt_hash_extractor import ReceiptHashExtractor
from .invoice_number.ref_no_extractor import RefNoExtractor
from .invoice_number.reference_number_extractor import ReferenceNumberExtractor
from .total.anchored_total_amount_extractor import AnchoredTotalAmountExtractor
from .vat.subtotal_extractor import SubtotalExtractor
from .vat.swedish_reverse_subtotal_extractor import SwedishReverseSubtotalExtractor
from .vat.swedish_reverse_vat_extractor import SwedishReverseVatExtractor
from .vat.vat_amount_extractor import VatAmountExtractor
from .vat.vat_rate_extractor import VatRateExtractor
from .vendor_name.company_with_suffix_extractor import CompanyWithSuffixExtractor


class ExtractorRegistry:
    InvoiceNumberExtractors = [
        InvoiceNumberColonExtractor(),
        InvoiceHashExtractor(),
        InvoiceNoExtractor(),
        InvPrefixExtractor(),
        AlphaNumericHyphenExtractor(),
        ReceiptHashExtractor(),
        InvoiceSpaceExtractor(),
        InvoiceNumberNoSpaceExtractor(),
        ReferenceNumberExtractor(),
        CreditNoteNumberExtractor(),
        RefNoExtractor(),
    ]

    CurrencyExtractors = [
        AnchoredCurrencyExtractor(),
        DetectedCurrencyExtractor(),
    ]

    TotalAmountExtractors = [
        AnchoredTotalAmountExtractor(),
    ]

    VendorNameExtractors = [
        CompanyWithSuffixExtractor(),
    ]

    InvoiceDateExtractors = [
        AnchoredInvoiceDateExtractor(),
        AnyDateExtractor(),
    ]

    DueDateExtractors = [
        AnchoredDueDateExtractor(),
    ]

    VatAmountExtractors = [
        VatAmountExtractor(),
        SwedishReverseVatExtractor(),
    ]

    VatRateExtractors = [
        VatRateExtractor(),
    ]

    SubtotalExtractors = [
        SubtotalExtractor(),
        SwedishReverseSubtotalExtractor(),
    ]
