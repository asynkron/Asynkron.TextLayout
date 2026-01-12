"""
Command-line interface for TextLayout.
"""

import sys
from .parser import process_document
from .formatter import format_output


def main():
    if len(sys.argv) < 2:
        print("Usage: textlayout <filename> [min_gap]")
        print("  min_gap: minimum whitespace column width to split on (default: 2)")
        sys.exit(1)

    filename = sys.argv[1]
    min_gap = int(sys.argv[2]) if len(sys.argv) > 2 else 2

    try:
        with open(filename, "r", encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found")
        sys.exit(1)

    blocks = process_document(text, min_gap)
    output = format_output(blocks)
    print(output)


if __name__ == "__main__":
    main()
