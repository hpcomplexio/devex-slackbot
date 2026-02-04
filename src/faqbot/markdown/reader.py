"""Markdown file reader and parser."""
import re
from pathlib import Path
from typing import Dict, List


def read_markdown_file(file_path: str) -> str:
    """Read markdown file and return content.

    Args:
        file_path: Path to the markdown file

    Returns:
        The file content as a string

    Raises:
        FileNotFoundError: If the file doesn't exist
        IOError: If the file can't be read
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Markdown file not found: {file_path}")

    return path.read_text(encoding='utf-8')


def parse_markdown_blocks(content: str) -> List[Dict]:
    """Parse markdown into blocks (headings + content).

    Splits the markdown content by headings and returns a list of blocks.
    Each block contains a heading and all content until the next heading.

    Args:
        content: Markdown file content

    Returns:
        List of dicts with:
            - type: 'heading' or 'text'
            - level: heading level (1-6) for headings, None for text
            - text: the actual content
            - line_number: line number in the file (1-indexed)
    """
    blocks = []
    lines = content.split('\n')

    for line_num, line in enumerate(lines, start=1):
        # Check if line is a heading (# ## ### etc.)
        heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)

        if heading_match:
            level = len(heading_match.group(1))
            text = heading_match.group(2).strip()
            blocks.append({
                'type': 'heading',
                'level': level,
                'text': text,
                'line_number': line_num
            })
        elif line.strip():  # Non-empty text line
            blocks.append({
                'type': 'text',
                'level': None,
                'text': line,
                'line_number': line_num
            })
        else:  # Empty line
            blocks.append({
                'type': 'text',
                'level': None,
                'text': '',
                'line_number': line_num
            })

    return blocks
