#!/usr/bin/env python3
"""
Extract Poppler pdftotext sections from payload files and anonymize them.
"""

import os
import re
import sys
import hashlib

# Anonymization mappings - consistent replacements
NAMES = {
    "Roger": "Anders",
    "Sara": "Maria",
    "David": "Erik",
    "Therese": "Karin",
    "Erika": "Lisa",
    "Lidia": "Anna",
    "Julia": "Sofia",
    "Karolina": "Emma",
    "Johansson": "Andersson",
    "Alsing": "Bergstrom",
    "Åkerblom": "Lindqvist",
    "Sangani": "Svensson",
    "rogeralsing": "andersb",  # username/domain
    "rogerjohansson": "andersanderson",
}

COMPANIES = {
    "Asynkron": "Acme Tech",
    "Dustin": "TechSupply",
    "JetBrains": "DevTools Inc",
    "Fortnox": "BookKeep",
    "Stripe": "PayFlow",
    "Google": "SearchCorp",
    "GitHub": "CodeHub",
    "Intrum": "DebtCo",
    "Etteplan": "EngineerCo",
    "Abion": "DomainCo",
    "Hogia": "SoftwareCo",
    "Wahlin": "LawFirm",
    "Portsgroup": "LogisticsCo",
    "Gritstep": "ConsultCo",
    "Xsolla": "GamePay",
}


def anonymize_text(text: str) -> str:
    """Replace personal data with fake data."""
    result = text

    # Replace compound names first (before splitting on word boundaries)
    result = result.replace("rogeralsing", "andersb")
    result = result.replace("Rogeralsing", "Andersb")
    result = result.replace("rogerjohansson", "andersanderson")

    # Replace names
    for real, fake in NAMES.items():
        result = re.sub(rf"\b{real}\b", fake, result, flags=re.IGNORECASE)

    # Replace companies
    for real, fake in COMPANIES.items():
        result = re.sub(rf"\b{real}\b", fake, result, flags=re.IGNORECASE)

    # Replace Swedish org numbers (10 digits, often with dash: 556666-1012)
    result = re.sub(
        r"\b(\d{6})-?(\d{4})\b", lambda m: f"{anonymize_number(m.group(0), 10)}", result
    )

    # Replace customer IDs (various formats)
    result = re.sub(
        r"\b\d{7,10}\b", lambda m: anonymize_number(m.group(0), len(m.group(0))), result
    )

    # Replace phone numbers
    result = re.sub(r"\+46\s*\d[\d\s]{8,12}", "+46 8 123 456 78", result)
    result = re.sub(r"\b08-\d{3}\s*\d{2}\s*\d{2}\b", "08-123 45 67", result)

    # Replace Swedish addresses
    result = re.sub(r"\b\d{3}\s*\d{2}\b", "123 45", result)  # Postal codes

    # Replace email addresses (keep domain structure)
    result = re.sub(
        r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", "info@example.com", result
    )

    # Replace IBANs
    result = re.sub(r"\bSE\d{22}\b", "SE1234567890123456789012", result)

    # Replace VAT numbers
    result = re.sub(r"\bSE\d{10}01\b", "SE123456789001", result)

    # Replace order/invoice numbers (preserve format)
    result = re.sub(r"\b\d{9}\b", lambda m: anonymize_number(m.group(0), 9), result)

    # Replace URLs with example.com (but keep structure)
    result = re.sub(
        r"https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}[^\s]*",
        "https://example.com/page",
        result,
    )

    # Replace license IDs
    result = re.sub(r"\b[A-Z0-9]{10}\b", "ABCD123456", result)

    return result


def anonymize_number(num_str: str, length: int) -> str:
    """Generate a consistent fake number based on input."""
    # Use hash for consistency
    h = hashlib.md5(num_str.encode()).hexdigest()
    # Convert hex to digits
    digits = "".join(str(int(c, 16) % 10) for c in h)
    return digits[:length].zfill(length)


def extract_poppler_section(content: str) -> str | None:
    """Extract text between Poppler pdftotext and Python MarkItDown markers."""
    start_marker = "Poppler pdftotext**********"
    end_marker = "Python MarkItDown**********"

    start_idx = content.find(start_marker)
    if start_idx == -1:
        return None

    start_idx += len(start_marker)

    end_idx = content.find(end_marker, start_idx)
    if end_idx == -1:
        return None

    section = content[start_idx:end_idx].strip()

    # Remove "--- Page X ---" markers
    section = re.sub(r"---\s*Page\s*\d+\s*---\s*\n?", "", section)

    return section


def main():
    if len(sys.argv) < 3:
        print("Usage: python extract_fixtures.py <source_dir> <output_dir>")
        sys.exit(1)

    source_dir = sys.argv[1]
    output_dir = sys.argv[2]

    os.makedirs(output_dir, exist_ok=True)

    count = 0
    for root, dirs, files in os.walk(source_dir):
        # Skip masked files
        for filename in files:
            if not filename.endswith(".txt"):
                continue
            if "_masked" in filename:
                continue

            filepath = os.path.join(root, filename)

            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception as e:
                print(f"Error reading {filepath}: {e}")
                continue

            section = extract_poppler_section(content)
            if not section:
                continue

            # Skip very short sections
            if len(section) < 100:
                continue

            # Anonymize
            anonymized = anonymize_text(section)

            # Generate output filename from path
            rel_path = os.path.relpath(root, source_dir)
            safe_name = rel_path.replace(os.sep, "_").replace("/", "_")
            out_filename = f"{safe_name}_{filename}"
            out_path = os.path.join(output_dir, out_filename)

            with open(out_path, "w", encoding="utf-8") as f:
                f.write(anonymized)

            print(f"Extracted: {out_path}")
            count += 1

    print(f"\nExtracted {count} fixtures")


if __name__ == "__main__":
    main()
