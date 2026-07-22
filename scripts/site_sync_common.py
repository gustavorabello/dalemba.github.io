#!/usr/bin/env python3

from __future__ import annotations

import html
import os
import re
import shutil
import sys
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTENT_DIR = ROOT / "content"
GENERATED_DIR = CONTENT_DIR / "generated"
RECIPES_OUTPUT_DIR = GENERATED_DIR / "recipes"
TABS_OUTPUT_DIR = GENERATED_DIR / "tabs"
STATIC_RECIPES_DIR = CONTENT_DIR / "static" / "images" / "recipes"

SOURCE_DATA_DIR = ROOT / "source_data"
LOCAL_RECIPES_DIR = SOURCE_DATA_DIR / "recipes"
LOCAL_RECIPE_IMAGES_DIR = SOURCE_DATA_DIR / "recipe_images"

DEFAULT_TABS_SOURCE_DIR = Path("/Users/gustavo/Documents/brazil/musica/tabs")
TABS_SOURCE_DIR = Path(
    os.environ.get("DALEMBA_TABS_DIR", str(DEFAULT_TABS_SOURCE_DIR))
).expanduser()
TABS_SCRIPT = ROOT / "scripts" / "generate_tabs.py"
TABS_MANIFEST = GENERATED_DIR / "tabs_manifest.json"
RECIPES_MANIFEST = GENERATED_DIR / "recipes_manifest.json"
NUMBERED_DUPLICATE_PATTERN = re.compile(r"^(?P<name>.+) (?P<index>[2-9]\d*)$")

ANSI_RESET = "\033[0m"
ANSI_COLORS = {
    "blue": "\033[38;5;33m",
    "cyan": "\033[38;5;37m",
    "green": "\033[38;5;71m",
    "amber": "\033[38;5;179m",
    "magenta": "\033[38;5;170m",
    "muted": "\033[38;5;245m",
}


def ensure_clean_dir(path: Path) -> None:
    remove_numbered_duplicates(path)
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def remove_numbered_duplicates(path: Path) -> None:
    parent = path.parent
    if not parent.exists():
        return

    for sibling in parent.iterdir():
        if sibling == path:
            continue
        match = NUMBERED_DUPLICATE_PATTERN.match(sibling.name)
        if not match or match.group("name") != path.name:
            continue
        if sibling.is_dir():
            shutil.rmtree(sibling)
        else:
            sibling.unlink()


def slugify(value: str) -> str:
    normalized = html.unescape(value).strip()
    normalized = unicodedata.normalize("NFKD", normalized)
    normalized = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
    normalized = normalized.lower()
    normalized = re.sub(r"[^\w\s-]", "", normalized, flags=re.UNICODE)
    normalized = re.sub(r"[\s_]+", "-", normalized)
    normalized = re.sub(r"-{2,}", "-", normalized)
    return normalized.strip("-") or "item"


def normalize_label(value: str) -> str:
    return slugify(value).replace("-", "")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def terminal_supports_ansi() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return sys.stdout.isatty()


def style_text(text: str, tone: str = "blue") -> str:
    if not terminal_supports_ansi():
        return text
    return f'{ANSI_COLORS.get(tone, "")}{text}{ANSI_RESET}'


def truncate_for_status(text: str, width: int = 78) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= width:
        return compact
    return compact[: max(0, width - 1)].rstrip() + "…"


def render_status_line(text: str, tone: str = "blue") -> str:
    return style_text(truncate_for_status(text), tone=tone)


def update_status_line(text: str, tone: str = "blue") -> None:
    message = render_status_line(text, tone=tone)
    if terminal_supports_ansi():
        print(f"\r\033[2K{message}", end="", flush=True)
        return


def finalize_status_line(text: str, tone: str = "green") -> None:
    message = render_status_line(text, tone=tone)
    if terminal_supports_ansi():
        print(f"\r\033[2K{message}", flush=True)
        return
    print(message, flush=True)


def print_sync_step(title: str, detail: str = "", tone: str = "cyan") -> None:
    suffix = f" - {detail}" if detail else ""
    print(style_text(f"==> {title}{suffix}", tone=tone), flush=True)


def print_sync_result(title: str, detail: str, tone: str = "green") -> None:
    print(style_text(f"OK  {title}: {detail}", tone=tone), flush=True)


def render_home_page(
    recipes: list[dict[str, str]],
    tabs: list[dict[str, str]],
    financeiro: dict[str, int] | None = None,
    academicdb: dict[str, int] | None = None,
) -> None:
    group_count = len({tab["group_slug"] for tab in tabs})
    home_page = f"""
Title: Dalembinha's Site
Slug: index
Url: /
Save_As: index.html
page_type: home
subtitle: Um canto de canções, panelas e pequenas memórias felizes.

<div class="section-grid">
  <section class="section-card">
    <span class="count-pill">{len(tabs)} músicas</span>
    <h2>Lista de músicas</h2>
    <p>{group_count} trilhas para abrir a janela, afinar a tarde e deixar a casa cantar.</p>
    <a class="card-link" href="/musicas/">Entrar nas músicas</a>
  </section>
  <section class="section-card">
    <span class="count-pill">{len(recipes)} receitas</span>
    <h2>Livro de receitas</h2>
    <p>Receitas guardadas com carinho, dessas que perfumam a cozinha antes da primeira panela.</p>
    <a class="card-link" href="/receitas/">Entrar nas receitas</a>
  </section>
  <section class="section-card">
    <span class="count-pill">Área protegida</span>
    <h2>Financeiro</h2>
    <p>Compras e preços ficam criptografados e só abrem no navegador com a sua senha.</p>
    <a class="card-link" href="/financeiro/">Entrar no financeiro</a>
  </section>
  <section class="section-card">
    <span class="count-pill">AcademicDB</span>
    <h2>Produção acadêmica</h2>
    <p>Catálogo acadêmico criptografado com YAMLs, gráficos e navegação filtrável.</p>
    <a class="card-link" href="/academicdb/">Entrar no AcademicDB</a>
  </section>
</div>
"""
    write_text(CONTENT_DIR / "pages" / "index.md", home_page)
