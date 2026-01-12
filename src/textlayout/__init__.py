"""
TextLayout - Extract structured text from documents with columnar layouts.

Uses XY-Cut algorithm to detect blocks and post-processing to normalize text.
"""

from .parser import (
    process_document,
    detect_blocks,
    text_to_matrix,
    extract_block,
)
from .formatter import format_output, align_key_value_groups

__version__ = "0.1.0"
__all__ = [
    "process_document",
    "detect_blocks",
    "text_to_matrix",
    "extract_block",
    "format_output",
    "align_key_value_groups",
]
