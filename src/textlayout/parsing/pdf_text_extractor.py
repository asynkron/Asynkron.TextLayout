from __future__ import annotations

import io
import json
import os
import re
import shlex
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PdfExtractionVariant:
    Text: str
    ExtractorName: str
    QualityScore: float


@dataclass
class PdfExtractionResult:
    Variants: list[PdfExtractionVariant]

    @property
    def BestText(self) -> str | None:
        if not self.Variants:
            return None
        best_variant = max(self.Variants, key=lambda variant: variant.QualityScore)
        return best_variant.Text


class PdfTextExtractor:
    @staticmethod
    def ExtractText(pdf_bytes: bytes, logger=None) -> str | None:
        results = PdfTextExtractor.ExtractWithAllStrategies(pdf_bytes, logger)
        return results.BestText

    @staticmethod
    def ExtractWithAllStrategies(pdf_bytes: bytes, logger=None) -> PdfExtractionResult:
        variants: list[PdfExtractionVariant] = []

        try:
            text = PdfTextExtractor._extract_default(pdf_bytes)
            if text and text.strip():
                variants.append(PdfExtractionVariant(text, "PdfPig-Default", PdfTextExtractor._calculate_quality(text)))
        except Exception as exc:
            if logger:
                logger.warning("PDF extraction failed: %s", "PdfPig-Default", exc_info=exc)

        try:
            text = PdfTextExtractor._extract_with_nearest_neighbour(pdf_bytes)
            if text and text.strip():
                variants.append(
                    PdfExtractionVariant(text, "PdfPig-NearestNeighbour", PdfTextExtractor._calculate_quality(text))
                )
        except Exception as exc:
            if logger:
                logger.warning("PDF extraction failed: %s", "PdfPig-NearestNeighbour", exc_info=exc)

        try:
            text = PdfTextExtractor._extract_with_poppler(pdf_bytes)
            if text and text.strip():
                variants.append(
                    PdfExtractionVariant(text, "Poppler-pdftotext", PdfTextExtractor._calculate_quality(text))
                )
        except Exception as exc:
            if logger:
                logger.warning("PDF extraction failed: %s", "Poppler-pdftotext", exc_info=exc)

        markitdown_text = PdfTextExtractor._extract_with_markitdown(pdf_bytes, logger)
        if markitdown_text and markitdown_text.strip():
            variants.append(
                PdfExtractionVariant(markitdown_text, "Python-MarkItDown", PdfTextExtractor._calculate_quality(markitdown_text))
            )

        pdf_plumber_text = PdfTextExtractor._extract_with_pdfplumber(pdf_bytes, logger)
        if pdf_plumber_text and pdf_plumber_text.strip():
            variants.append(
                PdfExtractionVariant(pdf_plumber_text, "Python-PdfPlumber", PdfTextExtractor._calculate_quality(pdf_plumber_text))
            )

        textlayout_text = PdfTextExtractor._extract_with_textlayout(pdf_bytes, logger)
        if textlayout_text and textlayout_text.strip():
            variants.append(
                PdfExtractionVariant(textlayout_text, "asynkron-textlayout", PdfTextExtractor._calculate_quality(textlayout_text))
            )

        return PdfExtractionResult(variants)

    @staticmethod
    def CalculateSimilarity(text1: str, text2: str) -> float:
        if not text1 or not text2 or not text1.strip() or not text2.strip():
            return 0

        words1 = PdfTextExtractor._extract_words(text1)
        words2 = PdfTextExtractor._extract_words(text2)

        if not words1 or not words2:
            return 0

        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        return 0 if union == 0 else intersection / union

    @staticmethod
    def _extract_words(text: str) -> set[str]:
        separators = [" ", "\n", "\r", "\t", ".", ",", ":", ";", "-", "_"]
        for sep in separators:
            text = text.replace(sep, " ")
        return {word for word in text.lower().split(" ") if len(word) >= 3}

    @staticmethod
    def FromText(text: str, extractor_name: str = "inline") -> PdfExtractionResult:
        if not text or not text.strip():
            return PdfExtractionResult([])

        variants = [PdfExtractionVariant(text, extractor_name, PdfTextExtractor._calculate_quality(text))]
        return PdfExtractionResult(variants)

    @staticmethod
    def _extract_with_markitdown(pdf_bytes: bytes, logger=None) -> str | None:
        return PdfTextExtractor._extract_with_python(
            pdf_bytes,
            logger,
            extractor_name="Python-MarkItDown",
            arguments_builder=lambda pdf_path: ["-m", "markitdown", pdf_path],
        )

    @staticmethod
    def _extract_with_pdfplumber(pdf_bytes: bytes, logger=None) -> str | None:
        script = "import pdfplumber,sys;print('\\n'.join((page.extract_text() or '') for page in pdfplumber.open(sys.argv[1]).pages))"
        return PdfTextExtractor._extract_with_python(
            pdf_bytes,
            logger,
            extractor_name="Python-PdfPlumber",
            arguments_builder=lambda pdf_path: ["-c", script, pdf_path],
        )

    @staticmethod
    def _extract_with_textlayout(pdf_bytes: bytes, logger=None) -> str | None:
        script = "from textlayout import extract_pdf;import sys;print(extract_pdf(sys.argv[1], min_gap=2))"
        return PdfTextExtractor._extract_with_python(
            pdf_bytes,
            logger,
            extractor_name="asynkron-textlayout",
            arguments_builder=lambda pdf_path: ["-c", script, pdf_path],
        )

    @staticmethod
    def _extract_with_python(pdf_bytes: bytes, logger, extractor_name: str, arguments_builder) -> str | None:
        python_path = PdfTextExtractor._resolve_python_executable()
        if python_path is None:
            return None

        temp_file = Path(tempfile.gettempdir()) / f"matcha-{os.urandom(8).hex()}.pdf"
        try:
            temp_file.write_bytes(pdf_bytes)

            args = [python_path] + arguments_builder(str(temp_file))
            result = subprocess.run(args, capture_output=True, text=True)

            if result.returncode != 0:
                if logger:
                    logger.warning("PDF extraction failed: %s %s", extractor_name, result.stderr)
                return None

            output = result.stdout
            return output.strip() if output and output.strip() else None
        except Exception as exc:
            if logger:
                logger.warning("PDF extraction failed: %s", extractor_name, exc_info=exc)
            return None
        finally:
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except OSError:
                    pass

    @staticmethod
    def _resolve_python_executable() -> str | None:
        override_path = os.getenv("MATCHA_SANDBOX_PYTHON_PATH")
        if override_path and os.path.exists(override_path):
            return override_path

        repo_root = Path(__file__).resolve().parents[3]
        python_path = repo_root / "src" / "Matcha.Sandbox" / ".venv" / "bin" / "python"
        return str(python_path) if python_path.exists() else None

    @staticmethod
    def _extract_default(pdf_bytes: bytes) -> str:
        try:
            import pdfplumber
        except ImportError as exc:
            raise RuntimeError("pdfplumber not available") from exc

        with pdfplumber.open(io.BytesIO(pdf_bytes)) as document:
            lines = []
            for page in document.pages:
                if lines:
                    lines.append("")
                lines.append(f"--- Page {page.page_number} ---")
                lines.append(page.extract_text() or "")
        return "\n".join(lines)

    @staticmethod
    def _extract_with_nearest_neighbour(pdf_bytes: bytes, line_spacing_threshold: float = 5) -> str:
        try:
            import pdfplumber
        except ImportError as exc:
            raise RuntimeError("pdfplumber not available") from exc

        with pdfplumber.open(io.BytesIO(pdf_bytes)) as document:
            output_lines = []
            for page in document.pages:
                if output_lines:
                    output_lines.append("")
                output_lines.append(f"--- Page {page.page_number} ---")

                words = page.extract_words()
                sorted_words = sorted(words, key=lambda word: (word.get("top", 0), word.get("x0", 0)))

                last_top = None
                current_line = ""
                for word in sorted_words:
                    top = word.get("top", 0)
                    text = word.get("text", "")

                    if last_top is not None and abs(top - last_top) > line_spacing_threshold:
                        output_lines.append(current_line.rstrip())
                        current_line = text
                    else:
                        if current_line and not current_line.endswith(" "):
                            current_line += " "
                        current_line += text

                    last_top = top

                if current_line:
                    output_lines.append(current_line.rstrip())

        return "\n".join(output_lines)

    @staticmethod
    def _extract_with_poppler(pdf_bytes: bytes) -> str | None:
        pdftotext_path = PdfTextExtractor._find_pdftotext()
        if pdftotext_path is None:
            return None

        temp_path = Path(tempfile.gettempdir()) / f"matcha_{os.urandom(8).hex()}.pdf"
        try:
            temp_path.write_bytes(pdf_bytes)
            text = PdfTextExtractor._run_process(pdftotext_path, f"-layout \"{temp_path}\" -")

            if not text or not text.strip():
                return None

            return "--- Page 1 ---\n" + text
        finally:
            try:
                temp_path.unlink()
            except OSError:
                pass

    @staticmethod
    def _run_process(file_name: str, arguments: str) -> str | None:
        try:
            result = subprocess.run(
                [file_name] + shlex.split(arguments),
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.stdout if result.returncode == 0 else None
        except Exception:
            return None

    @staticmethod
    def _find_pdftotext() -> str | None:
        paths = [
            "/opt/homebrew/bin/pdftotext",
            "/usr/local/bin/pdftotext",
            "/usr/bin/pdftotext",
        ]

        for path in paths:
            if os.path.exists(path):
                return path

        which_result = PdfTextExtractor._run_process("which", "pdftotext")
        return which_result.strip() if which_result and which_result.strip() else None

    @staticmethod
    def _calculate_quality(text: str) -> float:
        if not text or not text.strip():
            return 0

        score = 0.0
        lines = [line for line in text.split("\n") if line]

        if 5 < len(lines) < 500:
            score += 0.2

        space_ratio = text.count(" ") / len(text)
        if 0.1 < space_ratio < 0.3:
            score += 0.3

        keywords = ["invoice", "total", "amount", "date", "vat", "tax"]
        keyword_matches = sum(1 for keyword in keywords if re.search(rf"\b{keyword}\b", text, re.IGNORECASE))
        score += keyword_matches * 0.05

        if re.search(r"\d+[.,]\d{2}\s*(EUR|USD|SEK|€|\$)", text):
            score += 0.2

        if re.search(r"(EUR|USD|SEK|€|\$)\s*\d+[.,]\d{2}", text):
            score += 0.2

        long_words = len([word for word in text.split(" ") if len(word) > 30])
        score -= long_words * 0.05

        return max(0, min(1, score))

    @staticmethod
    def SerializeVariants(extraction: PdfExtractionResult) -> str | None:
        if not extraction.Variants:
            return None

        variant_map = {}
        for variant in extraction.Variants:
            if variant.ExtractorName not in variant_map:
                variant_map[variant.ExtractorName] = variant.Text

        return json.dumps(variant_map)

    @staticmethod
    def DeserializeVariants(json_value: str | None) -> PdfExtractionResult | None:
        if not json_value or not json_value.strip():
            return None

        try:
            data = json.loads(json_value)
        except json.JSONDecodeError:
            return None

        if not isinstance(data, dict) or not data:
            return None

        variants = [PdfExtractionVariant(text, name, 0) for name, text in data.items()]
        return PdfExtractionResult(variants)
