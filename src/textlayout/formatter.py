"""
Output formatting utilities for processed text blocks.
"""


def is_label_line(line: str) -> bool:
    """Check if a line is a label:value pair (not a URL or other colon usage)."""
    if ":" not in line or not line.strip():
        return False
    # Skip URLs
    if line.startswith("http://") or line.startswith("https://"):
        return False
    # Skip if colon is preceded by // (URL scheme)
    colon_pos = line.index(":")
    if colon_pos >= 2 and line[colon_pos - 1] == "/" and line[colon_pos - 2] == "/":
        return False
    return True


def align_key_value_groups(text: str) -> str:
    """
    Align key:value pairs in consecutive labeled lines.
    Pads after ':' so values line up.
    """
    lines = text.split("\n")
    result = []
    i = 0

    while i < len(lines):
        # Find consecutive label:value lines
        group = []

        while i < len(lines) and is_label_line(lines[i]):
            group.append(lines[i])
            i += 1

        if len(group) >= 2:
            # Find max label width (part before first ':')
            max_label_width = 0
            for line in group:
                colon_pos = line.index(":")
                max_label_width = max(max_label_width, colon_pos)

            # Reformat with aligned values
            for line in group:
                colon_pos = line.index(":")
                label = line[:colon_pos]
                value = line[colon_pos + 1 :].lstrip()
                padding = " " * (max_label_width - len(label))
                result.append(f"{label}{padding}: {value}")
        elif group:
            result.extend(group)
        else:
            result.append(lines[i])
            i += 1

    return "\n".join(result)


def collapse_blank_lines(text: str) -> str:
    """Collapse multiple blank lines to single blank line."""
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text


def collapse_between_labels(text: str) -> str:
    """Remove blank lines between consecutive labeled lines."""
    lines = text.split("\n")
    result = []
    i = 0

    while i < len(lines):
        line = lines[i]
        # Check if this is a blank line between two labeled lines
        if (
            not line.strip()
            and result
            and i + 1 < len(lines)
            and ":" in result[-1]
            and ":" in lines[i + 1]
        ):
            # Skip the blank line
            i += 1
            continue
        result.append(line)
        i += 1

    return "\n".join(result)


def format_output(blocks: list[str]) -> str:
    """
    Format a list of text blocks into final output.

    Applies:
    - Joining blocks with blank lines
    - Collapsing multiple blank lines
    - Collapsing blanks between labeled lines
    - Aligning key:value groups
    """
    output = "\n\n".join(blocks)
    output = collapse_blank_lines(output)
    output = collapse_between_labels(output)
    output = align_key_value_groups(output)
    return output
