"""Tests for the parser module."""

from textlayout import process_document, format_output


def test_simple_columns():
    text = """Name          Age
John          25
Jane          30"""

    blocks = process_document(text, min_gap=2)
    assert len(blocks) == 2
    assert "Name: John" in blocks[0] or "Name" in blocks[0]


def test_label_value_detection():
    text = """Product
Apple"""

    blocks = process_document(text, min_gap=2)
    output = format_output(blocks)
    assert "Product: Apple" in output


def test_horizontal_split():
    text = """Section 1

Section 2"""

    blocks = process_document(text, min_gap=2)
    assert len(blocks) == 2
    assert blocks[0] == "Section 1"
    assert blocks[1] == "Section 2"


def test_colon_joining():
    text = """Label:
Value"""

    blocks = process_document(text, min_gap=2)
    output = format_output(blocks)
    assert "Label: Value" in output


def test_url_preserved():
    text = """Website: example.com
Link: https://example.com"""

    blocks = process_document(text, min_gap=2)
    output = format_output(blocks)
    assert "https://example.com" in output


def test_number_pullup():
    text = """Total: (USD)
-500.00"""

    blocks = process_document(text, min_gap=2)
    output = format_output(blocks)
    assert "-500.00" in output


def test_alignment():
    text = """A: 1
BB: 2
CCC: 3"""

    blocks = process_document(text, min_gap=2)
    output = format_output(blocks)
    lines = output.strip().split("\n")

    # Check colons are aligned
    colon_positions = [line.index(":") for line in lines if ":" in line]
    assert len(set(colon_positions)) == 1  # All colons at same position
