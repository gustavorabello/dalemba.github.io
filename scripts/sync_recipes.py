#!/usr/bin/env python3

from __future__ import annotations

import html
import json
import re

from site_sync_common import (
    CONTENT_DIR,
    LOCAL_RECIPE_IMAGES_DIR,
    LOCAL_RECIPES_DIR,
    RECIPES_MANIFEST,
    RECIPES_OUTPUT_DIR,
    STATIC_RECIPES_DIR,
    ensure_clean_dir,
    finalize_status_line,
    read_text,
    slugify,
    update_status_line,
    write_text,
)


def parse_metadata_block(raw_text: str) -> tuple[dict[str, str], str]:
    if not raw_text.startswith("---"):
        return {}, raw_text
    parts = raw_text.split("---", 2)
    if len(parts) < 3:
        return {}, raw_text
    metadata: dict[str, str] = {}
    for line in parts[1].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip().lower()] = value.strip().strip("'").strip('"')
    return metadata, parts[2].strip()


def strip_hyde_markup(body: str, title: str, image_name: str | None) -> str:
    content = body.replace("\u2028", "\n").replace("\u00a0", " ")
    content = re.sub(r"{%\s*mark\s+\w+\s*-?%}", "", content)
    content = re.sub(r"{%-?\s*endmark\s*%}", "", content)
    content = re.sub(r"!\[[^\]]*\]\(\[\[!!images/recipes/([^)]+)\]\]\)", "", content)
    content = html.unescape(content)
    content = re.sub(r"<br\s*/?>", "", content, flags=re.IGNORECASE)
    content = re.sub(r"\n{3,}", "\n\n", content)
    content = content.strip()
    content = re.sub(r"^\s*INGREDIENTES:\s*$", "## Ingredientes", content, flags=re.MULTILINE)
    content = re.sub(r"^\s*MODO DE PREPARO:\s*$", "## Modo de preparo", content, flags=re.MULTILINE)
    content = re.sub(r"^\s*Modo de preparo:\s*$", "## Modo de preparo", content, flags=re.MULTILINE)
    if image_name:
        image_block = (
            f'<p class="recipe-hero"><img src="/static/images/recipes/{image_name}" '
            f'alt="{html.escape(title)}"></p>'
        )
        content = image_block + "\n\n" + content
    return content.strip()


def extract_summary(content: str) -> str:
    if "## Modo de preparo" in content:
        mode_text = content.split("## Modo de preparo", 1)[1].strip()
        first_block = re.split(r"\n\s*\n", mode_text, maxsplit=1)[0]
        cleaned = re.sub(r"<[^>]+>", "", first_block).strip()
        if cleaned:
            return cleaned[:180]

    for block in re.split(r"\n\s*\n", content):
        cleaned = re.sub(r"<[^>]+>", "", block).strip()
        cleaned = re.sub(r"^##\s+[^\n]+\n?", "", cleaned, flags=re.MULTILINE).strip()
        if cleaned:
            return cleaned[:180]
    return "Receita importada do acervo Hyde."


def render_recipe_listing(recipes: list[dict[str, str]]) -> None:
    cards = []
    for recipe in recipes:
        image_block = (
            f'<img src="{recipe["image"]}" alt="{html.escape(recipe["title"])}">'
            if recipe["image"]
            else ""
        )
        cards.append(
            f"""
<article class="recipe-card">
  {image_block}
  <h2>{html.escape(recipe["title"])}</h2>
  <p>{html.escape(recipe["summary"])}</p>
  <a class="card-link" href="{recipe["url"]}">Ler receita</a>
</article>
"""
        )

    listing_page = f"""
Title: Receitas
Slug: receitas
Url: receitas/
Save_As: receitas/index.html
page_type: listing
section_label: Livro de receitas
subtitle: Receitas antigas reorganizadas em um catálogo claro, simples e agradável de percorrer.

<p class="meta-note">Todas as receitas foram importadas do projeto Hyde original e reorganizadas em Pelican.</p>
<div class="recipe-grid">
  {''.join(cards)}
</div>
"""
    write_text(CONTENT_DIR / "pages" / "receitas.md", listing_page)


def sync_recipes() -> list[dict[str, str]]:
    ensure_clean_dir(RECIPES_OUTPUT_DIR)
    ensure_clean_dir(STATIC_RECIPES_DIR)

    recipes: list[dict[str, str]] = []
    source_files = [
        path
        for path in sorted(LOCAL_RECIPES_DIR.glob("*.html"))
        if path.name not in {"index.html", "atom.xml", "excerpts.xml", "meta.yaml"}
    ]
    total = len(source_files)

    for index, source_path in enumerate(source_files, start=1):
        if source_path.name in {"index.html", "atom.xml", "excerpts.xml", "meta.yaml"}:
            continue

        raw_text = read_text(source_path)
        metadata, body = parse_metadata_block(raw_text)
        title = metadata.get("title", source_path.stem)
        update_status_line(f"[receitas {index}/{total}] {title}", tone="amber")
        image_match = re.search(r"\[\[!!images/recipes/([^\]]+)\]\]", raw_text)
        image_name = image_match.group(1) if image_match else None

        if image_name:
            image_source = LOCAL_RECIPE_IMAGES_DIR / image_name
            if image_source.exists():
                image_target = STATIC_RECIPES_DIR / image_name
                image_target.parent.mkdir(parents=True, exist_ok=True)
                image_target.write_bytes(image_source.read_bytes())

        content = strip_hyde_markup(body, title, image_name)
        summary = extract_summary(content)
        slug = slugify(source_path.stem)
        page_path = RECIPES_OUTPUT_DIR / f"{slug}.md"
        url = f"receitas/{slug}/"

        page = f"""
Title: {title}
Slug: {slug}
Url: {url}
Save_As: {url}index.html
page_type: recipe
section_label: Receitas
subtitle: Receitas importadas do acervo Hyde com o conteúdo original preservado.
summary: {summary}

{content}
"""
        write_text(page_path, page)
        recipes.append(
            {
                "title": title,
                "slug": slug,
                "url": f"/{url}",
                "summary": summary,
                "image": f"/static/images/recipes/{image_name}" if image_name else "",
            }
        )

    RECIPES_MANIFEST.write_text(
        json.dumps(recipes, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    render_recipe_listing(recipes)
    finalize_status_line(f"Receitas sincronizadas: {len(recipes)}", tone="green")
    return recipes


def main() -> None:
    sync_recipes()


if __name__ == "__main__":
    main()
