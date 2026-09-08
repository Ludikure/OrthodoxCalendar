#!/usr/bin/env python3
"""Turn a fragment of scraped HTML into the plain text stored in a bio.

Every source (azbyka.ru saint pages, orthocal.info stories, holytrinityorthodox
life pages) needs the same sequence — drop scripts and boilerplate, turn <br>
and block ends into newlines, strip the remaining tags, decode entities, then
collapse runs of spaces and blank lines. Keeping one implementation means a fix
to entity or whitespace handling lands in every pool at once.
"""
import re
import unicodedata
from html import unescape

SCRIPT_RE = re.compile(r'<script[^>]*>.*?</script>|<style[^>]*>.*?</style>', re.DOTALL)
BR_RE = re.compile(r'<br\s*/?>')
BLOCK_END_RE = re.compile(r'</(p|div|h[1-6]|li|tr|blockquote)>', re.IGNORECASE)
TAG_RE = re.compile(r'<[^>]+>')
SPACES_RE = re.compile(r'[ \t\xa0]+')


def strip_accents(text: str) -> str:
    """Drop combining marks (azbyka.ru prints Russian stress accents)."""
    return ''.join(c for c in text if unicodedata.category(c) != 'Mn')


def to_text(fragment: str, *, drop: tuple = (), accents: bool = True) -> str:
    """Plain text of an HTML fragment.

    `drop` holds extra compiled patterns to remove before the tags come out
    (sidebars, "read more" links). `accents=False` strips combining marks.
    """
    text = SCRIPT_RE.sub('', fragment)
    for pattern in drop:
        text = pattern.sub('', text)
    text = BR_RE.sub('\n', text)
    text = BLOCK_END_RE.sub('\n', text)
    text = unescape(TAG_RE.sub('', text))
    if not accents:
        text = strip_accents(text)
    lines = (SPACES_RE.sub(' ', line).strip() for line in text.split('\n'))
    return '\n'.join(line for line in lines if line).strip()
