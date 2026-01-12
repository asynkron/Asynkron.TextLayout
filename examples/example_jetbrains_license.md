# Text Layout Parser Example: JetBrains License Certificate

This example shows how the XY-Cut text layout parser processes a license certificate PDF.

## Before (Raw Poppler pdftotext output)

The raw Poppler output already has reasonable structure, but has some issues:

```
                                                                                                  https://www.jetbrains.com




                              JetBrains Toolbox Subscription Certificate
IMPORTANT: THIS IS TO CERTIFY THE RIGHT TO USE THE JETBRAINS SOFTWARE PRODUCT GRANTED BY JETBRAINS S.R.O.
PURSUANT TO CONDITIONS OF THE TERMS OF USE. PLEASE SAVE A COPY OF THIS DOCUMENT FOR FUTURE REFERENCE.


LICENSE DETAILS
Type:               Personal License
Reference No*:      R12345678
Date of issue:      24 December 2023
Billing period:     Monthly
Valid through:      20 January 2024
Number of authorized users: 1

* Please quote this order reference or License ID when contacting JetBrains


SOFTWARE ACTIVATION
Please follow the link https://account.jetbrains.com/order/assets/xxxxxxxxxxxxxxxxxxxx to proceed with software
activation.


LICENSEE
Name: Anders Bengtsson
Customer ID: 1234567


SOFTWARE PRODUCT
Product name: All Products Pack
Licensed version: any product(s) release made available during usage term

The software is shipped electronically and is available for download from: https://www.jetbrains.com/all/download


LICENSE ID
License ID identifies the license across renewals, conversions, upgrades etc. License ID can be used to search for a
particular license on JetBrains Account website as well as to communicate with JetBrains sales representatives.
License ID is NOT a license key and will not allow activation of the product.

License ID: XXXXX00XXX
```

### Issues with raw output:
- URL appears at top right with lots of leading whitespace
- Excessive blank lines between sections
- Inconsistent label alignment (some have large gaps, some small)
- Wrapped text ("to proceed with software" / "activation.")
- Long paragraph lines wrap mid-sentence

---

## After (Processed with XY-Cut parser)

After processing with `detect_blocks.py` (min_gap=3):

```
https://www.jetbrains.com

JetBrains Toolbox Subscription Certificate
IMPORTANT: THIS IS TO CERTIFY THE RIGHT TO USE THE JETBRAINS SOFTWARE PRODUCT GRANTED BY JETBRAINS S.R.O.
PURSUANT TO CONDITIONS OF THE TERMS OF USE. PLEASE SAVE A COPY OF THIS DOCUMENT FOR FUTURE REFERENCE.

LICENSE DETAILS
Type                      : Personal License
Reference No*             : R12345678
Date of issue             : 24 December 2023
Billing period            : Monthly
Valid through             : 20 January 2024
Number of authorized users: 1

* Please quote this order reference or License ID when contacting JetBrains

SOFTWARE ACTIVATION
Please follow the link https://account.jetbrains.com/order/assets/xxxxxxxxxxxxxxxxxxxx to proceed with software activation.

LICENSEE
Name       : Anders Bengtsson
Customer ID: 1234567

SOFTWARE PRODUCT
Product name                                                             : All Products Pack
Licensed version                                                         : any product(s) release made available during usage term
The software is shipped electronically and is available for download from: https://www.jetbrains.com/all/download

LICENSE ID
License ID identifies the license across renewals, conversions, upgrades etc. License ID can be used to search for a particular license on JetBrains Account website as well as to communicate with JetBrains sales representatives.
License ID is NOT a license key and will not allow activation of the product.

License ID: XXXXX00XXX
```

### Improvements:
- **Whitespace trimmed**: Leading spaces removed from URL line
- **Blank lines normalized**: Excessive blank lines collapsed
- **Label alignment**: Within each section, colons are aligned for readability
- **Line unwrapping**: "to proceed with software activation." joined into one line
- **Paragraph unwrapping**: Long paragraphs wrapped by PDF are rejoined

---

## Comparison: Different PDF Extractors

The same document extracted with different tools shows why Poppler pdftotext is preferred:

### PdfPig Default (concatenates everything)
```
JetBrains Toolbox Subscription CertificateIMPORTANT: THIS IS TO CERTIFY THE RIGHT...LICENSE DETAILSType:Personal LicenseReference No*:R12345678...
```
No structure preserved - everything on one line.

### PdfPig NearestNeighbour (scrambled order)
```
ID: XXXXX00XXX License
a not ID NOT License is license key and will allow activation the product. of
on as as to Account JetBrains communicate JetBrains representatives...
```
Words reordered incorrectly.

### MarkItDown (loses column alignment)
```
Type:

Personal License

Reference No*:

R12345678
```
Each label and value on separate lines - loses the key:value relationship.

### PdfPlumber (single column, loses spacing)
```
Type: Personal License
Reference No*: R12345678
```
Better, but all whitespace collapsed.

### Poppler pdftotext (best for layout)
Preserves spatial layout including columns and whitespace, making it ideal input for the XY-Cut parser.

---

## Algorithm Details

For this document:
1. **Horizontal split**: Sections separated by blank lines (header, LICENSE DETAILS, etc.)
2. **Vertical split**: Not much columnar data in this doc, so blocks stay intact
3. **Normalization**:
   - Wrapped lines like "software" + "activation." joined
   - Long paragraphs unwrapped
4. **Formatting**:
   - Label:value pairs aligned within each section
   - Multiple blank lines collapsed to single blank line
