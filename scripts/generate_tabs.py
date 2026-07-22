#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import unicodedata
from pathlib import Path

ACORDE_REGEX = (
    r"(?<![\w>/])"
    r"("
    r"[A-G](?:#|b)?"
    r"(?:m|M)?"
    r"(?:dim7|dim|aug|add|º7|º|°7|°|\+)?"
    r"(?:7\+|M\+|9\+|13\+|11\+|6\+|5\+|7M|M7|maj7|7|9|13|11|6|5|4|sus[24]?|add9)?"
    r"(?:5-/7|5\-/7|7/5-)?"
    r"(?:/[A-G](?:#|b)?)?"
    r"(?:/(?:b|#)?[0-9]{1,2}[b#]?)*"
    r"(?:\([^\)]+\))?"
    r")"
    r"(?!\w)"
)

LINHAS_PARA_DUAS_COLUNAS = 34
ANSI_RESET = "\033[0m"
ANSI_COLORS = {
    "blue": "\033[38;5;33m",
    "green": "\033[38;5;71m",
}
NEXT_HINT_PATTERN = re.compile(
    r"^\s*(?:proxima|próxima|proximo|próximo|next)(?:\s+m[uú]sica)?\s*:\s*(.+?)\s*$",
    flags=re.IGNORECASE,
)
KEY_PATTERN = re.compile(
    r"^\s*(?:tom|tonalidade|key)\s*:\s*([A-G](?:#|b)?)(m)?\s*$",
    flags=re.IGNORECASE,
)
NOTE_PITCHES = {
    "C": 0,
    "C#": 1,
    "Db": 1,
    "D": 2,
    "D#": 3,
    "Eb": 3,
    "E": 4,
    "F": 5,
    "F#": 6,
    "Gb": 6,
    "G": 7,
    "G#": 8,
    "Ab": 8,
    "A": 9,
    "A#": 10,
    "Bb": 10,
    "B": 11,
}
PITCH_NAMES = ("C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B")
SCALE_INTERVALS = {
    "major": (0, 2, 4, 5, 7, 9, 11),
    "minor": (0, 2, 3, 5, 7, 8, 10),
}
SCALE_TRIADS = {
    "major": ("major", "minor", "minor", "major", "major", "minor", "diminished"),
    "minor": ("minor", "diminished", "major", "minor", "minor", "major", "major"),
}

def build_parser() -> argparse.ArgumentParser:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="Converte tablaturas TXT em páginas compatíveis com Pelican."
    )
    parser.add_argument(
        "--input-dir",
        required=True,
        help="Diretório com as tablaturas em TXT.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(script_dir / "tabs_pelican"),
        help="Diretório de saída das páginas geradas.",
    )
    parser.add_argument(
        "--manifest",
        default=str(script_dir / "tabs_manifest.json"),
        help="Arquivo JSON com a lista das tablaturas geradas.",
    )
    parser.add_argument(
        "--section",
        default="tablaturas",
        help="Prefixo de URL usado nas páginas geradas.",
    )
    return parser


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    normalized = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
    normalized = normalized.lower()
    normalized = re.sub(r"[^\w\s-]", "", normalized)
    normalized = re.sub(r"[\s_]+", "-", normalized)
    normalized = re.sub(r"-{2,}", "-", normalized)
    return normalized.strip("-") or "item"


def terminal_supports_ansi() -> bool:
    return sys.stdout.isatty()


def style_text(text: str, tone: str = "blue") -> str:
    if not terminal_supports_ansi():
        return text
    return f'{ANSI_COLORS.get(tone, "")}{text}{ANSI_RESET}'


def compact_status_text(text: str, width: int = 84) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= width:
        return compact
    return compact[: max(0, width - 1)].rstrip() + "…"


def update_status_line(text: str, tone: str = "blue") -> None:
    message = style_text(compact_status_text(text), tone=tone)
    if terminal_supports_ansi():
        print(f"\r\033[2K{message}", end="", flush=True)
        return


def finalize_status_line(text: str, tone: str = "green") -> None:
    message = style_text(compact_status_text(text), tone=tone)
    print(f"\r\033[2K{message}" if terminal_supports_ansi() else message, flush=True)


def prettify_identifier(value: str) -> str:
    text = value.replace("-", " ").replace("_", " ").strip()
    text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text[:1].upper() + text[1:] if text else "Item"


def strip_parenthetical_artist(artist: str) -> str:
    artist = artist.strip()
    match = re.fullmatch(r"\(([^)]+)\)", artist)
    if match:
        return match.group(1).strip()
    without_parentheses = re.sub(r"\(.*?\)", "", artist).strip()
    return without_parentheses or artist


def artista_to_cifraclub_url(artist: str) -> str:
    artist = strip_parenthetical_artist(artist)
    artist_ascii = "".join(
        c for c in unicodedata.normalize("NFD", artist)
        if unicodedata.category(c) != "Mn"
    )
    artist_ascii = re.sub(r"[^a-zA-Z0-9\s-]", "", artist_ascii)
    artist_ascii = re.sub(r"\s+", " ", artist_ascii).strip()
    if not artist_ascii:
        return "https://www.cifraclub.com.br/"
    return f'https://www.cifraclub.com.br/{artist_ascii.lower().replace(" ", "-")}/'


def escape_and_colorize(line: str) -> str:
    normalized = line.rstrip("\r\n").replace("\xa0", " ")
    matches = list(re.finditer(ACORDE_REGEX, normalized))
    sanitized = html.escape(normalized)

    if not matches:
        return sanitized

    residual = normalized
    for match in reversed(matches):
        residual = residual[:match.start()] + (" " * len(match.group(1))) + residual[match.end():]
    residual_letters = re.findall(r"[^\W\d_]", residual, flags=re.UNICODE)
    if len(matches) == 1 and residual_letters:
        return sanitized

    def replacer(match: re.Match[str]) -> str:
        chord = match.group(1)
        return f'<span class="chord">{chord}</span>'

    return re.sub(ACORDE_REGEX, replacer, sanitized)


def clean_content(lines: list[str]) -> list[str]:
    processed = [escape_and_colorize(line) for line in lines]
    cleaned: list[str] = []
    for line in processed:
        if line.strip() == "" and (not cleaned or cleaned[-1].strip() == ""):
            continue
        cleaned.append(line)
    return cleaned


def extract_inline_metadata(lines: list[str]) -> tuple[dict[str, str], list[str]]:
    metadata: dict[str, str] = {}
    content_lines: list[str] = []
    for line in lines:
        match = NEXT_HINT_PATTERN.match(line)
        if match:
            metadata["next_hint"] = match.group(1).strip()
            continue
        key_match = KEY_PATTERN.match(line)
        if key_match:
            metadata["harmonic_key"] = key_match.group(1)[0].upper() + key_match.group(1)[1:]
            metadata["harmonic_mode"] = "minor" if key_match.group(2) else "major"
            metadata["harmonic_key_source"] = "declared"
            continue
        content_lines.append(line)
    return metadata, content_lines


def chord_quality(chord: str) -> str:
    match = re.match(r"^[A-G](?:#|b)?(.*)$", chord)
    suffix = match.group(1) if match else ""
    lowered = suffix.lower()
    if "dim" in lowered or "º" in suffix or "°" in suffix:
        return "diminished"
    if re.search(r"m7(?:\(b5\)|/5-)", lowered):
        return "diminished"
    if lowered.startswith("m") and not lowered.startswith("maj"):
        return "minor"
    return "major"


def chord_root(chord: str) -> int | None:
    match = re.match(r"^([A-G](?:#|b)?)", chord)
    return NOTE_PITCHES.get(match.group(1)) if match else None


def extract_chords(lines: list[str]) -> list[str]:
    chords: list[str] = []
    for line in lines:
        normalized = line.rstrip("\r\n").replace("\xa0", " ")
        matches = list(re.finditer(ACORDE_REGEX, normalized))
        if not matches:
            continue
        residual = normalized
        for match in reversed(matches):
            residual = residual[:match.start()] + (" " * len(match.group(1))) + residual[match.end():]
        residual_letters = re.findall(r"[^\W\d_]", residual, flags=re.UNICODE)
        if len(matches) == 1 and residual_letters:
            continue
        chords.extend(match.group(1) for match in matches)
    return chords


def infer_harmonic_key(chords: list[str]) -> tuple[str, str]:
    parsed = [
        (root, chord_quality(chord), "7" in chord and "7M" not in chord and "maj7" not in chord.lower())
        for chord in chords
        if (root := chord_root(chord)) is not None
    ]
    if not parsed:
        return "C", "major"

    best: tuple[float, int, str] | None = None
    for tonic in range(12):
        for mode in ("major", "minor"):
            scale = tuple((tonic + interval) % 12 for interval in SCALE_INTERVALS[mode])
            triads = dict(zip(scale, SCALE_TRIADS[mode]))
            score = 0.0
            for position, (root, quality, is_dominant) in enumerate(parsed):
                if root in scale:
                    score += 1.5
                    if triads[root] == quality:
                        score += 3.0
                if root == tonic and quality == ("minor" if mode == "minor" else "major"):
                    score += 2.5
                    if position in (0, len(parsed) - 1):
                        score += 2.0
                if root == (tonic + 7) % 12 and is_dominant:
                    score += 3.5
            for current, following in zip(parsed, parsed[1:]):
                if current[0] == (following[0] + 7) % 12 and current[2]:
                    score += 2.0
                if current[0] == (tonic + 7) % 12 and following[0] == tonic:
                    score += 4.0
            candidate = (score, -tonic, mode)
            if best is None or candidate > best:
                best = candidate

    assert best is not None
    return PITCH_NAMES[-best[1]], best[2]


def build_display_units(lines: list[str]) -> list[list[str]]:
    units: list[list[str]] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.strip() == "":
            units.append([""])
            index += 1
            continue

        if '<span class="chord">' in line:
            if index + 1 < len(lines):
                next_line = lines[index + 1]
                if next_line.strip() != "" and '<span class="chord">' not in next_line:
                    units.append([line, next_line])
                    index += 2
                    continue
        units.append([line])
        index += 1

    return units


def trim_blank_units(units: list[list[str]]) -> list[list[str]]:
    start = 0
    end = len(units)
    while start < end and all(line.strip() == "" for line in units[start]):
        start += 1
    while end > start and all(line.strip() == "" for line in units[end - 1]):
        end -= 1
    return units[start:end]


def split_units_for_columns(units: list[list[str]]) -> tuple[list[list[str]], list[list[str]]]:
    if len(units) < 2:
        return units, []

    weighted_lengths = [len(unit) for unit in units]
    total_lines = sum(weighted_lengths)
    best_index = 1
    best_difference = total_lines
    left_lines = 0

    for index in range(1, len(units)):
        left_lines += weighted_lengths[index - 1]
        right_lines = total_lines - left_lines
        difference = abs(left_lines - right_lines)
        if difference < best_difference:
            best_difference = difference
            best_index = index

    left = trim_blank_units(units[:best_index])
    right = trim_blank_units(units[best_index:])

    if not left or not right:
        midpoint = max(1, len(units) // 2)
        left = trim_blank_units(units[:midpoint])
        right = trim_blank_units(units[midpoint:])

    return left, right


def flatten_units(units: list[list[str]]) -> list[str]:
    merged: list[str] = []
    for unit in units:
        merged.extend(unit)
    return merged


def render_sheet(lines: list[str]) -> str:
    content = "\n".join(lines)
    return f'<pre class="tab-sheet">{content}</pre>'


def should_use_two_columns(content: list[str], units: list[list[str]]) -> bool:
    if len(units) < 2:
        return False

    non_empty_lines = sum(1 for line in content if line.strip())
    return len(content) >= LINHAS_PARA_DUAS_COLUNAS or non_empty_lines >= 30


def render_tab_content(content: list[str]) -> str:
    units = build_display_units(content)
    if should_use_two_columns(content, units):
        left, right = split_units_for_columns(units)
        left_markup = render_sheet(flatten_units(left))
        right_markup = render_sheet(flatten_units(right))
        return f"""
<div class="tab-layout columns">
  <div class="tab-column">
    {left_markup}
  </div>
  <div class="tab-column">
    {right_markup}
  </div>
</div>
""".strip()

    block_markup = render_sheet(content)
    return f"""
<div class="tab-layout singlecol">
  {block_markup}
</div>
""".strip()


def render_pelican_page(
    *,
    title: str,
    slug: str,
    artist: str,
    artist_url: str,
    page_url: str,
    body: str,
    harmonic_key: str,
    harmonic_mode: str,
    harmonic_key_source: str,
) -> str:
    summary = f"{title}, canção de {artist}."
    return f"""
Title: {title}
Slug: {slug}
Url: {page_url}
Save_As: {page_url}index.html
page_type: tab
artist: {artist}
artist_url: {artist_url}
harmonic_key: {harmonic_key}
harmonic_mode: {harmonic_mode}
harmonic_key_source: {harmonic_key_source}
section_label: Músicas
summary: {summary}

{body}
""".strip()


def collect_tabs(input_dir: Path) -> list[Path]:
    files = sorted(input_dir.rglob("*.txt"))
    if not files:
        raise FileNotFoundError(f"Nenhum arquivo .txt encontrado em '{input_dir}'")
    return files


def convert_tab(source_path: Path, input_dir: Path, output_dir: Path, section: str) -> dict[str, str]:
    lines = source_path.read_text(encoding="utf-8").splitlines()
    title = lines[0].strip() if lines else "Título desconhecido"
    artist_raw = lines[1].strip() if len(lines) > 1 else source_path.parent.name
    artist = strip_parenthetical_artist(artist_raw)
    inline_metadata, content_lines = extract_inline_metadata(lines[2:] if len(lines) > 2 else [])
    harmonic_key = inline_metadata.get("harmonic_key")
    harmonic_mode = inline_metadata.get("harmonic_mode")
    harmonic_key_source = inline_metadata.get("harmonic_key_source", "inferred")
    if not harmonic_key or not harmonic_mode:
        harmonic_key, harmonic_mode = infer_harmonic_key(extract_chords(content_lines))
    content = clean_content(content_lines)
    body = render_tab_content(content)
    group_slug = slugify(source_path.parent.name)
    group_name = prettify_identifier(source_path.parent.name)
    artist_slug = slugify(artist)
    song_slug = slugify(source_path.stem)
    page_url = f"{section}/{group_slug}/{song_slug}/"
    target_path = output_dir / group_slug / f"{song_slug}.md"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(
        render_pelican_page(
            title=title,
            slug=f"{artist_slug}-{song_slug}",
            artist=artist,
            artist_url=artista_to_cifraclub_url(artist_raw),
            page_url=page_url,
            body=body,
            harmonic_key=harmonic_key,
            harmonic_mode=harmonic_mode,
            harmonic_key_source=harmonic_key_source,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "title": title,
        "artist": artist,
        "artist_slug": artist_slug,
        "artist_url": artista_to_cifraclub_url(artist_raw),
        "group_slug": group_slug,
        "group_name": group_name,
        "song_slug": song_slug,
        "url": f"/{page_url}",
        "output_file": str(Path(group_slug) / f"{song_slug}.md"),
        "source": str(source_path.relative_to(input_dir)),
        "next_hint": inline_metadata.get("next_hint", ""),
        "harmonic_key": harmonic_key,
        "harmonic_mode": harmonic_mode,
        "harmonic_key_source": harmonic_key_source,
    }


def main() -> None:
    args = build_parser().parse_args()
    input_dir = Path(args.input_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    manifest_path = Path(args.manifest).resolve()

    if not input_dir.is_dir():
        raise SystemExit(f'Pasta "{input_dir}" não existe.')

    output_dir.mkdir(parents=True, exist_ok=True)
    source_tabs = collect_tabs(input_dir)
    total = len(source_tabs)
    tabs: list[dict[str, str]] = []
    for index, path in enumerate(source_tabs, start=1):
        update_status_line(f"[tabs {index}/{total}] {path.parent.name} / {path.stem}", tone="blue")
        tabs.append(convert_tab(path, input_dir, output_dir, args.section))
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(tabs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    finalize_status_line(f"Músicas convertidas: {len(tabs)}", tone="green")


if __name__ == "__main__":
    main()
