#!/usr/bin/env python3
"""Rename fixture files to anonymize company names in filenames."""

import os
import sys

# Map: original prefix -> anonymized prefix
# These are applied to the first part of filename (before first _)
COMPANY_MAP = {
    "abion": "domainco",
    "apexbpm": "processco",
    "asynkron": "acmetech",
    "eaccounting": "bookkeep",
    "etteplan": "engineerco",
    "fortnox": "invoiceco",
    "github": "codehub",
    "gmail": "mailservice",
    "google": "searchcorp",
    "gritstep": "consultco",
    "hogia": "softwareco",
    "info": "infoco",
    "intrum": "debtco",
    "jetbrains": "devtools",
    "portsgroup": "logisticsco",
    "stripe": "payflow",
    "wahlinlaw": "lawfirm",
    "wint": "invoiceapp",
    "xsolla": "gamepay",
}

# Map for second part (after first _)
SUBPART_MAP = {
    "roger": "user1",
    "sara": "user2",
    "david": "user3",
    "lidia": "user4",
    "julia": "user5",
    "karolina": "user6",
    "sangani": "user7",
    "rogeralsing": "user1b",
    "kkokosa": "user8",
    "fakturanoreply": "invoicebot",
    "paymentsnoreply": "paymentbot",
    "noreply": "autobot",
    "sales": "salesbot",
    "mail": "mailbot",
    "invoice": "invoices",
    "hej": "hello",
    "mailer": "mailerbot",
    "se": "nordic",
}


def rename_file(filepath: str) -> str:
    """Rename a file, replacing company names."""
    dirname = os.path.dirname(filepath)
    filename = os.path.basename(filepath)

    parts = filename.split("_")
    if len(parts) < 2:
        return filepath

    # Replace first part (company)
    if parts[0] in COMPANY_MAP:
        parts[0] = COMPANY_MAP[parts[0]]

    # Replace second part (subpart like user/department)
    if parts[1] in SUBPART_MAP:
        parts[1] = SUBPART_MAP[parts[1]]

    # Handle stripe's long account names
    if "invoicestatementsacct" in parts[1]:
        parts[1] = "statements"

    new_filename = "_".join(parts)

    if new_filename != filename:
        new_path = os.path.join(dirname, new_filename)
        os.rename(filepath, new_path)
        return new_path
    return filepath


def main():
    fixtures_dir = sys.argv[1] if len(sys.argv) > 1 else "fixtures"

    count = 0
    for filename in os.listdir(fixtures_dir):
        if not filename.endswith(".txt"):
            continue
        filepath = os.path.join(fixtures_dir, filename)
        new_path = rename_file(filepath)
        if new_path != filepath:
            print(f"{filename} -> {os.path.basename(new_path)}")
            count += 1

    print(f"\nRenamed {count} files")


if __name__ == "__main__":
    main()
