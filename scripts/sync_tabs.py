#!/usr/bin/env python3

from __future__ import annotations

import html
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

from site_sync_common import (
    CONTENT_DIR,
    TABS_MANIFEST,
    TABS_OUTPUT_DIR,
    TABS_SCRIPT,
    TABS_SOURCE_DIR,
    ensure_clean_dir,
    normalize_label,
    read_text,
    slugify,
    write_text,
)


def run_tabs_generator() -> list[dict[str, str]]:
    ensure_clean_dir(TABS_OUTPUT_DIR)
    command = [
        sys.executable,
        str(TABS_SCRIPT),
        "--input-dir",
        str(TABS_SOURCE_DIR),
        "--output-dir",
        str(TABS_OUTPUT_DIR),
        "--manifest",
        str(TABS_MANIFEST),
        "--section",
        "musicas",
    ]
    subprocess.run(command, check=True)
    return json.loads(TABS_MANIFEST.read_text(encoding="utf-8"))


def build_lookup_keys(tab: dict[str, str]) -> set[str]:
    source_path = Path(tab["source"])
    raw_keys = {
        tab["title"],
        source_path.stem,
        source_path.with_suffix("").as_posix(),
        f'{source_path.parent.name}/{source_path.stem}',
        tab["url"].strip("/"),
        f'{tab["group_slug"]}/{tab["song_slug"]}',
    }
    keys: set[str] = set()
    for key in raw_keys:
        normalized = key.strip()
        if not normalized:
            continue
        keys.add(slugify(normalized))
        keys.add(normalize_label(normalized.replace(".txt", "").replace("\\", "/")))
    return keys


def order_tabs_for_listing(tabs: list[dict[str, str]]) -> list[dict[str, str]]:
    groups: dict[str, dict[str, object]] = {}
    for tab in tabs:
        bucket = groups.setdefault(
            tab["group_slug"],
            {
                "group_name": tab["group_name"],
                "songs": [],
            },
        )
        bucket["songs"].append(tab)

    ordered: list[dict[str, str]] = []
    item_index = 1
    for _, payload in sorted(groups.items(), key=lambda item: item[1]["group_name"]):
        songs = sorted(payload["songs"], key=lambda song: song["title"])
        for song in songs:
            song["listing_index"] = item_index
            ordered.append(song)
            item_index += 1
    return ordered


def resolve_explicit_next(
    tab: dict[str, str],
    lookup: dict[str, list[dict[str, str]]],
) -> dict[str, str] | None:
    hint = tab.get("next_hint", "").strip()
    if not hint:
        return None

    variants = {
        hint,
        hint.replace(".txt", ""),
        hint.replace("\\", "/"),
        hint.replace(".txt", "").replace("\\", "/"),
    }
    candidates: dict[str, dict[str, str]] = {}
    for variant in variants:
        for key in (slugify(variant), normalize_label(variant)):
            for candidate in lookup.get(key, []):
                if candidate["url"] != tab["url"]:
                    candidates[candidate["url"]] = candidate

    if len(candidates) == 1:
        return next(iter(candidates.values()))

    source = tab.get("source", tab["title"])
    if not candidates:
        raise ValueError(
            f'Sugestão "{hint}" em "{source}" não corresponde a nenhuma música. '
            'Use "Próxima: grupo/arquivo.txt".'
        )

    matches = ", ".join(sorted(candidate["source"] for candidate in candidates.values()))
    raise ValueError(
        f'Sugestão ambígua "{hint}" em "{source}"; correspondências: {matches}. '
        'Use "Próxima: grupo/arquivo.txt".'
    )


def update_tab_page_metadata(tab: dict[str, str]) -> None:
    page_path = TABS_OUTPUT_DIR / tab["output_file"]
    raw_text = read_text(page_path)
    header, separator, body = raw_text.partition("\n\n")
    header_lines = [
        line
        for line in header.splitlines()
        if not line.startswith("next_tab_url:")
        and not line.startswith("next_tab_title:")
        and not line.startswith("next_tab_artist:")
        and not line.startswith("listing_index:")
    ]
    if tab.get("listing_index"):
        header_lines.append(f'listing_index: {tab["listing_index"]}')
    if tab.get("next_tab_url") and tab.get("next_tab_title"):
        header_lines.append(f'next_tab_url: {tab["next_tab_url"]}')
        header_lines.append(f'next_tab_title: {tab["next_tab_title"]}')
        header_lines.append(f'next_tab_artist: {tab["next_tab_artist"]}')
    write_text(page_path, "\n".join(header_lines) + separator + body)


def apply_next_links(tabs: list[dict[str, str]]) -> list[dict[str, str]]:
    ordered_tabs = order_tabs_for_listing(tabs)
    lookup: dict[str, list[dict[str, str]]] = defaultdict(list)
    for tab in tabs:
        for key in build_lookup_keys(tab):
            lookup[key].append(tab)

    for index, tab in enumerate(ordered_tabs):
        default_next = ordered_tabs[index + 1] if index + 1 < len(ordered_tabs) else None
        has_explicit_next = bool(tab.get("next_hint", "").strip())
        next_tab = resolve_explicit_next(tab, lookup) if has_explicit_next else default_next
        if next_tab:
            tab["next_tab_url"] = next_tab["url"]
            tab["next_tab_title"] = next_tab["title"]
            tab["next_tab_artist"] = next_tab["artist"]
        else:
            tab["next_tab_url"] = ""
            tab["next_tab_title"] = ""
            tab["next_tab_artist"] = ""
        update_tab_page_metadata(tab)

    TABS_MANIFEST.write_text(json.dumps(tabs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return ordered_tabs


def render_tabs_listing(tabs: list[dict[str, str]]) -> None:
    groups: dict[str, dict[str, object]] = {}
    for tab in tabs:
        bucket = groups.setdefault(
            tab["group_slug"],
            {
                "group_name": tab["group_name"],
                "songs": [],
            },
        )
        bucket["songs"].append(tab)

    sections = []
    item_index = 1
    for group_slug, payload in sorted(groups.items(), key=lambda item: item[1]["group_name"]):
        songs = sorted(payload["songs"], key=lambda song: song["title"])
        artist_counts = Counter(song["artist"] for song in songs)
        top_artist, top_count = artist_counts.most_common(1)[0]
        display_name = (
            top_artist
            if top_count >= (len(songs) // 2 + len(songs) % 2)
            else payload["group_name"]
        )
        group_label = normalize_label(display_name)
        start_index = item_index
        song_links = "\n".join(
            (
                f'<li value="{index}"><a href="{song["url"]}">{html.escape(song["title"])}</a>'
                + (
                    f' <span class="song-artist">— {html.escape(song["artist"])}</span>'
                    if normalize_label(song["artist"]) != group_label
                    else ""
                )
                + "</li>"
            )
            for index, song in enumerate(songs, start=start_index)
        )
        sections.append(
            f"""
<section class="tab-group" id="{group_slug}">
  <div class="tab-group-header">
    <h2>{html.escape(display_name)}</h2>
    <span class="count-pill">{len(songs)} músicas</span>
  </div>
  <ol class="tab-directory" start="{start_index}">
    {song_links}
  </ol>
</section>
"""
        )
        item_index += len(songs)

    listing_page = f"""
Title: Músicas
Slug: musicas
Url: musicas/
Save_As: musicas/index.html
page_type: listing
section_label: Acervo musical
subtitle: Uma travessia de canções em ordem serena, para achar cada lembrança pelo nome.

<p class="meta-note">{len(tabs)} músicas espalhadas em {len(groups)} caminhos de escuta.</p>
<div class="tab-directory-shell" data-default-list-columns="2" style="--list-columns: 2;">
  {''.join(sections)}
</div>
"""
    old_listing = CONTENT_DIR / "pages" / "tablaturas.md"
    if old_listing.exists():
        old_listing.unlink()
    write_text(CONTENT_DIR / "pages" / "musicas.md", listing_page)


def sync_tabs() -> list[dict[str, str]]:
    tabs = run_tabs_generator()
    ordered_tabs = apply_next_links(tabs)
    render_tabs_listing(tabs)
    return ordered_tabs


def main() -> None:
    tabs = sync_tabs()
    print(f"Músicas sincronizadas: {len(tabs)}")


if __name__ == "__main__":
    main()
