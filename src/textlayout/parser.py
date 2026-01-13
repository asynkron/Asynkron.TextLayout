"""
Core parsing logic for extracting text blocks from documents.
"""

from __future__ import annotations

import subprocess


def text_to_matrix(text: str) -> list[list[str]]:
    """Convert text to a 2D character matrix, padding lines to equal length."""
    lines = text.split("\n")
    max_width = max((len(line) for line in lines), default=0)
    return [list(line.ljust(max_width)) for line in lines]


def is_blank_row(matrix: list[list[str]], row: int) -> bool:
    """Check if a row is entirely whitespace."""
    return all(c in (" ", "") for c in matrix[row])


def is_blank_col(
    matrix: list[list[str]], col: int, start_row: int, end_row: int
) -> bool:
    """Check if a column is entirely whitespace within the row range."""
    return all(matrix[r][col] in (" ", "") for r in range(start_row, end_row + 1))


def split_horizontal(matrix: list[list[str]]) -> list[tuple[int, int]]:
    """Split matrix into horizontal sections based on blank rows."""
    if not matrix:
        return []

    sections = []
    in_section = False
    section_start = 0

    for r in range(len(matrix)):
        if is_blank_row(matrix, r):
            if in_section:
                sections.append((section_start, r - 1))
                in_section = False
        elif not in_section:
            section_start = r
            in_section = True

    if in_section:
        sections.append((section_start, len(matrix) - 1))

    return sections


def find_vertical_gaps(
    matrix: list[list[str]], start_row: int, end_row: int, min_gap: int
) -> list[tuple[int, int]]:
    """Find vertical whitespace gaps within a row range."""
    if not matrix or not matrix[0]:
        return []

    width = len(matrix[0])
    gaps = []
    in_gap = False
    gap_start = 0

    for c in range(width):
        if is_blank_col(matrix, c, start_row, end_row):
            if not in_gap:
                gap_start = c
                in_gap = True
        elif in_gap:
            if c - gap_start >= min_gap:
                gaps.append((gap_start, c - 1))
            in_gap = False

    return gaps


def find_text_bounds(
    matrix: list[list[str]], start_row: int, end_row: int, start_col: int, end_col: int
) -> tuple[int, int] | None:
    """Find actual text bounds within a region. Returns (min_col, max_col) or None."""
    min_c, max_c = end_col + 1, start_col - 1
    for r in range(start_row, end_row + 1):
        for c in range(start_col, end_col):
            if matrix[r][c] not in (" ", ""):
                min_c = min(min_c, c)
                max_c = max(max_c, c)
    return (min_c, max_c) if max_c >= min_c else None


def split_vertical(
    matrix: list[list[str]], start_row: int, end_row: int, min_gap: int
) -> list[tuple[int, int]]:
    """Split a section into vertical columns based on whitespace gaps."""
    if not matrix or not matrix[0]:
        return []

    width = len(matrix[0])
    gaps = find_vertical_gaps(matrix, start_row, end_row, min_gap)

    if not gaps:
        bounds = find_text_bounds(matrix, start_row, end_row, 0, width)
        return [bounds] if bounds else []

    columns = []
    prev_end = 0

    for gap_start, gap_end in gaps:
        bounds = find_text_bounds(matrix, start_row, end_row, prev_end, gap_start)
        if bounds:
            columns.append(bounds)
        prev_end = gap_end + 1

    # Last column
    if prev_end < width:
        bounds = find_text_bounds(matrix, start_row, end_row, prev_end, width)
        if bounds:
            columns.append(bounds)

    return columns


def normalize_block(lines: list[str]) -> str:
    """
    Normalize extracted lines:
    - Join label: value pairs
    - Pull up numbers after separators
    - Unwrap word-wrapped lines
    """
    # If exactly 2 non-empty lines and first looks like a label, add ':'
    non_empty = [line for line in lines if line]
    if len(non_empty) == 2:
        first = non_empty[0]
        if not first.endswith(":") and ":" not in first and not first[0].isdigit():
            lines = [f"{first}:", non_empty[1]]

    # Join lines where previous ends with ':'
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.endswith(":") and i + 1 < len(lines) and lines[i + 1]:
            result.append(f"{line} {lines[i + 1]}")
            i += 2
        else:
            result.append(line)
            i += 1

    # Pull up lines starting with number/minus if prev ends with separator
    final = []
    separators = (":", ")", "]", "}", ",")
    for line in result:
        if (
            line
            and final
            and final[-1]
            and (line[0].isdigit() or line[0] == "-")
            and final[-1].rstrip().endswith(separators)
        ):
            final[-1] = f"{final[-1]} {line}"
        else:
            final.append(line)

    # Join wrapped lines (line doesn't end with sentence-ending punctuation,
    # and next line starts with lowercase or is a continuation)
    unwrapped = []
    end_punctuation = (".", "!", "?", ":", ";")
    for line in final:
        if (
            line
            and unwrapped
            and unwrapped[-1]
            and not unwrapped[-1].rstrip().endswith(end_punctuation)
            and (line[0].islower() or line[0].isdigit())
        ):
            unwrapped[-1] = f"{unwrapped[-1]} {line}"
        else:
            unwrapped.append(line)

    return "\n".join(unwrapped)


def extract_block(
    matrix: list[list[str]], start_row: int, end_row: int, start_col: int, end_col: int
) -> str:
    """Extract and normalize text from a rectangular region."""
    lines = []
    for r in range(start_row, end_row + 1):
        line = "".join(matrix[r][start_col : end_col + 1]).strip()
        lines.append(line)

    # Trim blank lines
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()

    return normalize_block(lines)


def detect_blocks(matrix: list[list[str]], min_gap: int = 2) -> list[str]:
    """
    Detect text blocks using XY-Cut algorithm.
    Returns list of normalized text blocks.
    """
    blocks = []

    for start_row, end_row in split_horizontal(matrix):
        for start_col, end_col in split_vertical(matrix, start_row, end_row, min_gap):
            content = extract_block(matrix, start_row, end_row, start_col, end_col)
            if content.strip():
                blocks.append(content)

    return blocks


def process_document(text: str, min_gap: int = 2) -> list[str]:
    """
    Process a document and return extracted text blocks.

    Args:
        text: The raw text content with preserved spacing
        min_gap: Minimum whitespace column width to split on (default: 2)

    Returns:
        List of normalized text blocks
    """
    matrix = text_to_matrix(text)
    return detect_blocks(matrix, min_gap)


def extract(text: str, min_gap: int = 2) -> str:
    """
    Extract text blocks from raw text input.

    Args:
        text: The raw text content with preserved spacing
        min_gap: Minimum whitespace column width to split on (default: 2)

    Returns:
        Formatted text output from detected blocks
    """
    from .formatter import format_output

    blocks = process_document(text, min_gap)
    return format_output(blocks)


def extract_pdf(pdf_file_path: str, min_gap: int = 2) -> str:
    """
    Extract text blocks from a PDF using Poppler's pdftotext.

    Args:
        pdf_file_path: Path to the PDF file
        min_gap: Minimum whitespace column width to split on (default: 2)

    Returns:
        Formatted text output from detected blocks
    """
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", pdf_file_path, "-"],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("pdftotext is not installed or not on PATH") from exc

    if result.returncode != 0:
        error = result.stderr.strip() or "Unknown pdftotext error"
        raise RuntimeError(f"pdftotext failed: {error}")

    from .formatter import format_output

    blocks = process_document(result.stdout, min_gap)
    return format_output(blocks)
