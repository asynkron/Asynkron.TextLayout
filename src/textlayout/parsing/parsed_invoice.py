from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


@dataclass
class InvoiceLineItem:
    Description: str | None = None
    Quantity: Decimal | None = None
    UnitPrice: Decimal | None = None
    Amount: Decimal | None = None


@dataclass
class ParsedInvoice:
    InvoiceNumber: str | None = None
    VendorName: str | None = None
    VendorAddress: str | None = None
    OrganizationId: str | None = None
    VatNumber: str | None = None
    Customer: str | None = None
    InvoiceDate: date | None = None
    DueDate: date | None = None
    InvoiceDateRaw: str | None = None
    DueDateRaw: str | None = None
    TotalAmount: Decimal | None = None
    TotalExcludingVat: Decimal | None = None
    VatAmount: Decimal | None = None
    VatRate: Decimal | None = None
    Currency: str | None = None
    LineItems: list[InvoiceLineItem] = field(default_factory=list)
    RawText: str | None = None
    Confidence: float = 0.0
    Warnings: list[str] = field(default_factory=list)
