from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class ParsedInvoiceDto:
    JsonOptions = {
        "property_naming_policy": "snake_case_lower",
        "dictionary_key_policy": "snake_case_lower",
    }

    VendorName: str | None = None
    VendorOrganizationNumber: str | None = None
    VendorLocale: str | None = None
    CustomerName: str | None = None
    CustomerOrganizationNumber: str | None = None
    InvoiceNumber: str | None = None
    InvoiceDate: str | None = None
    DueDate: str | None = None
    TotalAmount: Decimal | None = None
    Currency: str | None = None
    VatAmount: Decimal | None = None
    Confidence: float | None = None
    Missing: list[str] = field(default_factory=list)
    DocumentType: str | None = None
    StaticIdentificationAnchors: list[str] = field(default_factory=list)
