# TextLayout

Extract structured text from documents with columnar layouts.

## Overview

TextLayout uses an XY-Cut algorithm to detect text blocks in documents that have been extracted from PDFs or other sources with preserved character spacing. It's particularly effective for:

- Invoices with multiple columns
- Forms with label:value pairs
- Documents with side-by-side content
- Any text where spatial positioning matters

## Installation

```bash
pip install git+https://github.com/asynkron/Asynkron.TextLayout.git
```

## Usage

### Command Line

```bash
textlayout document.txt
textlayout document.txt 3  # min_gap=3 for tighter column detection
```

### Python API

```python
from textlayout import process_document, format_output

# Read your document
with open("invoice.txt") as f:
    text = f.read()

# Extract blocks
blocks = process_document(text, min_gap=2)

# Format output
output = format_output(blocks)
print(output)
```

## How It Works

1. **Text to Matrix**: Converts text into a 2D character grid
2. **Horizontal Split**: Divides document into sections at blank lines
3. **Vertical Split**: Divides each section into columns at whitespace gaps
4. **Normalization**: 
   - Joins `label:` with following value
   - Unwraps word-wrapped lines
   - Pulls up numbers after separators
5. **Formatting**:
   - Collapses multiple blank lines
   - Aligns key:value pairs in groups

## Example

Input (raw PDF text with spacing):
```
Kund nr             Fakturanr          Fakturadatum
4601691270          005597910          2021-12-03
```

Output:
```
Kund nr     : 4601691270
Fakturanr   : 005597910
Fakturadatum: 2021-12-03
```

## License

MIT
