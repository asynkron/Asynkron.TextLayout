"""
Command-line interface for TextLayout.
"""

import sys
from pathlib import Path

from .parser import extract, extract_pdf


def main():
    if len(sys.argv) < 2:
        print("Usage: textlayout <filename> [min_gap]")
        print("  filename: text file or PDF (requires pdftotext)")
        print("  min_gap: minimum whitespace column width to split on (default: 2)")
        sys.exit(1)

    filename = sys.argv[1]
    min_gap = int(sys.argv[2]) if len(sys.argv) > 2 else 2

    try:
        if Path(filename).suffix.lower() == ".pdf":
            output = extract_pdf(filename, min_gap)
        else:
            with open(filename, "r", encoding="utf-8") as f:
                text = f.read()
            output = extract(text, min_gap)
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found")
        sys.exit(1)
    except RuntimeError as exc:
        print(f"Error: {exc}")
        sys.exit(1)

    print(output)


if __name__ == "__main__":
    main()
