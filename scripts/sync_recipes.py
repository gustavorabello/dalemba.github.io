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
        metadata[key.strip().lower()] = html.unescape(
            value.strip().strip("'").strip('"')
        )
    return metadata, parts[2].strip()


def strip_hyde_markup(body: str) -> str:
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
    return content.strip()


def summarize_text(value: str, limit: int = 180) -> str:
    cleaned = html.unescape(value)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = re.sub(r"^\s*#{1,6}\s+", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^\s*(?:[-*+] |\d+\.\s+)", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return ""

    sentence_ends = [match.end() for match in re.finditer(r"[.!?](?:\s|$)", cleaned)]
    useful_ends = [end for end in sentence_ends if 60 <= end <= limit]
    if useful_ends:
        return cleaned[: useful_ends[-1]].strip()
    if len(cleaned) <= limit:
        return cleaned

    shortened = cleaned[: limit - 1].rsplit(" ", 1)[0].rstrip(" ,;:-")
    return f"{shortened}…"


def extract_summary(content: str) -> str:
    if "## Modo de preparo" in content:
        mode_text = content.split("## Modo de preparo", 1)[1].strip()
        summary = summarize_text(mode_text)
        if summary:
            return summary

    for block in re.split(r"\n\s*\n", content):
        summary = summarize_text(block)
        if summary:
            return summary
    return "Receita guardada com carinho."


def render_recipe_listing(recipes: list[dict[str, str]]) -> None:
    cards = []
    for recipe in recipes:
        image_block = (
            f'<img src="{recipe["image"]}" alt="{html.escape(recipe["title"])}" loading="lazy">'
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
subtitle: Sabores guardados com carinho, para voltar quando a fome pedir memória.

<p class="meta-note">Receitas para dias lentos, mesas cheias e alguma saudade boa.</p>
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

        content = strip_hyde_markup(body)
        summary = extract_summary(content)
        slug = slugify(source_path.stem)
        page_path = RECIPES_OUTPUT_DIR / f"{slug}.md"
        url = f"receitas/{slug}/"
        recipe_image = f"/static/images/recipes/{image_name}" if image_name else ""
        image_metadata = f"recipe_image: {recipe_image}" if recipe_image else ""

        page = f"""
Title: {title}
Slug: {slug}
Url: {url}
Save_As: {url}index.html
page_type: recipe
section_label: Receitas
subtitle: Para fazer a casa cheirar a afeto.
summary: {summary}
{image_metadata}

{content}
"""
        write_text(page_path, page)
        recipes.append(
            {
                "title": title,
                "slug": slug,
                "url": f"/{url}",
                "summary": summary,
                "image": recipe_image,
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
