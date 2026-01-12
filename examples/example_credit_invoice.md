# Text Layout Parser Example: Credit Invoice

This example shows how the XY-Cut text layout parser transforms a columnar PDF invoice into structured, readable text.

## Before (Raw Poppler pdftotext output)

The raw output preserves spatial layout but is difficult to parse programmatically:

```
KREDITFAKTURA                                        Pg 1 (1)

                                                                                            Kund nr             Fakturanr          Fakturadatum
                                                                                            1234567890          005512340          2021-12-03
Box 9999, 131 27 Nacka Strand

       Leveransadress:                                                                      Fakturaadress:
       Acme Tech AB                                                                         Acme Tech AB
       C/O Anders Andersson, Storgatan                                                      Kund-id WIN5977, FE nr 160
       12B                                                                                  10569 Stockholm
       123 45 STORSTAD



        Vårt order nr:           205812345                                                   Förfallodag:             2021-12-13
        Ert Inköpsnr:                                                                        Vår ref:                 Erika Svensson
                                                                                             Leveranssätt:            Budbil pall
        Er ref:                                                                              Leveransvillkor:         Fritt vårt lager
                                                                                             Orderdatum:              2021-12-03
        Godsmärke:               CAS-312345-X7Y8                                             Ert Org-nr:              5591234567




                                                                                                                                                                      SE_INV_247F_A_1_STD
       Artikelnr              Beskrivning                                                                    Antal           á pris        MOMS             Belopp
       5012345678             FREIGHT COMPENSATION                                                            -1,00         479,00         -119.75          -479,00




                    MOMS:                 Exkl moms:            Momsbelopp:                     OCR/Betalningsref:          Förfallodag:        Er tillgodo: (SEK)
                  25,00 %                    -479,00                -119,75                 1071234567890123             2021-12-13                        -599,00



     Villkor:                                                  Meddelande:
     Enligt TechSupplys försäljningsvillkor vid tidpunkten för
     köpet.
     https://www.techsupply.se/service/forsaljningsvillkor




    Adress:                             Telefon:                      Org nr:                   Bankgiro:                       Info:
    TechSupply Sverige AB                                             5512341234                255-9334                        Önskar du kvitta fakturan mot
    Box 9999,                           E-post:                       VAT nr:                   SWIFT/BIC:
    131 27 Nacka Strand                 se.faktura@example.com        SE551234123401            NDEASESS                        kreditfaktura så ber vi er
                                        Internet:                     Säte:                     IBAN:                           kontakta oss på +46 8 553 440 00
                                        www.techsupply.se             Nacka Strand              SE9212345678901234567890        eller se.faktura@example.com.
                                                                      F-skatt:
                                                                      Godkänd för F-skatt 
```

### Problems with raw output:
- Data spans multiple columns but appears on same line
- Labels are separated from values by whitespace
- Address wraps across lines (`Storgatan` / `12B`)
- Table headers and values are misaligned
- Footer information is scattered across columns

---

## After (Processed with XY-Cut parser)

After processing with `detect_blocks.py` (min_gap=3):

```
KREDITFAKTURA

Pg 1 (1)

Box 9999, 131 27 Nacka Strand

Kund nr       : 1234567890
Fakturanr     : 005512340
Fakturadatum  : 2021-12-03
Leveransadress: Acme Tech AB
C/O Anders Andersson, Storgatan 12B 123 45 STORSTAD

Fakturaadress: Acme Tech AB
Kund-id WIN5977, FE nr 160 10569 Stockholm

Vårt order nr: Ert Inköpsnr:
Er ref       : 
Godsmärke    : 

205812345

CAS-312345-X7Y8

Förfallodag : Vår ref:
Leveranssätt: Leveransvillkor:
Orderdatum  : Ert Org-nr:

2021-12-13
Erika Svensson
Budbil pall
Fritt vårt lager 2021-12-03 5591234567

Artikelnr  : 5012345678
Beskrivning: FREIGHT COMPENSATION
Antal      : -1,00
á pris     : 479,00
MOMS       : -119.75
Belopp     : -479,00

SE_INV_247F_A_1_STD

MOMS             : 25,00 %
Exkl moms        : -479,00
Momsbelopp       : -119,75
OCR/Betalningsref: 1071234567890123
Förfallodag      : 2021-12-13
Er tillgodo      : (SEK) -599,00
Villkor          : Meddelande: Enligt TechSupplys försäljningsvillkor vid tidpunkten för köpet.
https://www.techsupply.se/service/forsaljningsvillkor
Adress: TechSupply Sverige AB
Box 9999, 131 27 Nacka Strand

Telefon  : 
E-post   : se.faktura@example.com
Internet : www.techsupply.se
Org nr   : 5512341234
VAT nr   : SE551234123401
Säte     : Nacka Strand
F-skatt  : Godkänd för F-skatt
Bankgiro : 255-9334
SWIFT/BIC: NDEASESS
IBAN     : SE9212345678901234567890
Info     : Önskar du kvitta fakturan mot

kreditfaktura så ber vi er kontakta oss på +46 8 553 440 00 eller se.faktura@example.com.
```

### Improvements:
- **Column separation**: Left and right columns are now separate blocks
- **Label alignment**: Key:value pairs have aligned colons for readability
- **Line unwrapping**: Wrapped text like addresses are joined
- **Structured data**: Each field is on its own line with clear label:value format
- **Blank line collapsing**: Excessive whitespace is removed

---

## Algorithm Applied

1. **Horizontal split**: Document split on blank rows into sections
2. **Vertical split**: Each section split on 3+ character whitespace columns
3. **Normalization**:
   - Two-line blocks with label-like first line get `:` added
   - Lines ending with `:` joined with next line
   - Wrapped lines unwrapped (lowercase continuation)
4. **Formatting**:
   - Consecutive label:value lines get aligned colons
   - Multiple blank lines collapsed
