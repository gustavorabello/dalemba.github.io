#!/usr/bin/env python3

from __future__ import annotations

import html
import re
import unicodedata
from pathlib import Path


HTML_TABS_DIR = (
    Path(__file__).resolve().parents[1]
    / "source_data"
    / "legacy_tabs_html"
)
TXT_TABS_DIR = Path(__file__).resolve().parents[2] / "pyTabs" / "tabs_txt"


PRE_BLOCK_PATTERN = re.compile(r"<pre>(.*?)</pre>", flags=re.IGNORECASE | re.DOTALL)
TAG_PATTERN = re.compile(r"<[^>]+>")
TITLE_PATTERN = re.compile(r'<div class="title">(.*?)</div>', flags=re.IGNORECASE | re.DOTALL)
AUTHOR_PATTERN = re.compile(r'<a class="author-link"[^>]*>(.*?)</a>', flags=re.IGNORECASE | re.DOTALL)
SUGGEST_PATTERN = re.compile(
    r'<a class="suggest-btn"[^>]*href="[^"]*/tabs/([^"]+?)\.html"',
    flags=re.IGNORECASE | re.DOTALL,
)


def normalize_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    normalized = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
    normalized = normalized.lower().replace("&", " e ")
    normalized = re.sub(r"[^\w\s-]", " ", normalized)
    normalized = re.sub(r"[\s_-]+", "", normalized)
    return normalized


def prettify_identifier(value: str) -> str:
    text = value.replace("-", " ").replace("_", " ").strip()
    text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text[:1].upper() + text[1:] if text else "Item"


def extract_text(pattern: re.Pattern[str], raw_html: str) -> str:
    match = pattern.search(raw_html)
    if not match:
        return ""
    content = TAG_PATTERN.sub("", match.group(1))
    return html.unescape(content).strip()


def extract_pre_blocks(raw_html: str) -> list[str]:
    blocks: list[str] = []
    for match in PRE_BLOCK_PATTERN.finditer(raw_html):
        content = match.group(1)
        content = re.sub(r'<span class="chord">(.*?)</span>', r"\1", content)
        content = TAG_PATTERN.sub("", content)
        content = html.unescape(content)
        content = content.replace("\r", "")
        content = content.strip("\n")
        if content.strip():
            blocks.append(content)
    return blocks


def existing_stems() -> set[str]:
    stems: set[str] = set()
    for path in TXT_TABS_DIR.rglob("*.txt"):
        stems.add(normalize_key(path.stem))
    return stems


def should_use_stem_as_title(parsed_title: str, stem: str, known_stems: set[str]) -> bool:
    title_key = normalize_key(parsed_title)
    stem_key = normalize_key(stem)
    if not parsed_title:
        return True
    if stem_key == title_key:
        return False
    return title_key in known_stems and stem_key not in known_stems


def parse_html_tab(path: Path, known_stems: set[str]) -> tuple[str, str, str | None, list[str]]:
    raw_html = path.read_text(encoding="utf-8", errors="ignore")
    title = extract_text(TITLE_PATTERN, raw_html)
    artist = extract_text(AUTHOR_PATTERN, raw_html).strip()
    artist = artist.strip("()").strip()
    suggestion = None
    suggestion_match = SUGGEST_PATTERN.search(raw_html)
    if suggestion_match:
        suggestion = suggestion_match.group(1)

    if should_use_stem_as_title(title, path.stem, known_stems):
        title = prettify_identifier(path.stem)
        artist = prettify_identifier(path.parent.name).replace(" E ", " e ")

    return title or prettify_identifier(path.stem), artist or prettify_identifier(path.parent.name), suggestion, extract_pre_blocks(raw_html)


def recover_missing_tabs() -> list[Path]:
    known_stems = existing_stems()
    created: list[Path] = []

    for html_path in sorted(HTML_TABS_DIR.rglob("*.html")):
        if normalize_key(html_path.stem) in known_stems:
            continue

        title, artist, suggestion, blocks = parse_html_tab(html_path, known_stems)
        if not blocks:
            continue

        target_path = TXT_TABS_DIR / html_path.relative_to(HTML_TABS_DIR).with_suffix(".txt")
        target_path.parent.mkdir(parents=True, exist_ok=True)

        parts = [title, f"({artist})", ""]
        if suggestion:
            parts.extend([f"Próxima: {suggestion}", ""])
        for index, block in enumerate(blocks):
            if index:
                parts.append("")
            parts.extend(block.splitlines())

        target_path.write_text("\n".join(parts).strip() + "\n", encoding="utf-8")
        created.append(target_path)

    return created


def main() -> None:
    created = recover_missing_tabs()
    for path in created:
        print(path)
    print(f"Tabs recuperadas: {len(created)}")


if __name__ == "__main__":
    main()
