#!/usr/bin/env python3

from __future__ import annotations

import base64
import json
import mimetypes
import os
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from site_sync_common import CONTENT_DIR, ROOT, print_sync_result, write_text
from sync_financeiro import encrypt_payload, get_password


ACADEMICDB_ROOT = Path(
    os.environ.get(
        "ACADEMICDB_ROOT",
        "/Users/gustavo/Library/Mobile Documents/com~apple~CloudDocs/projects/academicDB",
    )
).expanduser()
ACADEMICDB_SITE_DIR = Path(os.environ.get("ACADEMICDB_SITE_DIR", ACADEMICDB_ROOT / "site")).expanduser()
ACADEMICDB_STATIC_DIR = CONTENT_DIR / "static" / "academicdb"
ACADEMICDB_VAULT = ACADEMICDB_STATIC_DIR / "vault.json"
ACADEMICDB_PAGE = CONTENT_DIR / "pages" / "academicdb.md"
DEFAULT_INCLUDE_PDFS = "0"
CAREER_REPORT_NAMES = {
    "MODELO_RELATORIO_PROGRE_PROMO-compressed.pdf",
    "relatorio-progressao-carreira.pdf",
}


def include_pdfs() -> bool:
    return os.environ.get("ACADEMICDB_INCLUDE_PDFS", DEFAULT_INCLUDE_PDFS).strip() == "1"


def rebuild_academicdb(root: Path) -> None:
    if os.environ.get("ACADEMICDB_SKIP_REBUILD") == "1":
        return
    if not (root / "Makefile").exists():
        raise SystemExit(f"Makefile do academicDB nao encontrado em {root}")
    subprocess.run(["make", "html"], cwd=root, check=True)


def should_include_asset(path: Path, include_pdf_files: bool) -> bool:
    if any(part.startswith(".") for part in path.parts):
        return False
    if any(part in {"career", "progressao-carreira"} for part in path.parts):
        return False
    if path.name in CAREER_REPORT_NAMES:
        return False
    if path.suffix.lower() == ".pdf" and not include_pdf_files:
        return False
    return True


def b64_file(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def asset_mime(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(path.name)
    if guessed:
        return guessed
    if path.suffix.lower() in {".yaml", ".yml"}:
        return "text/yaml"
    return "application/octet-stream"


def build_payload(site_dir: Path) -> dict[str, Any]:
    index_file = site_dir / "index.html"
    if not index_file.exists():
        raise SystemExit(f"Site do academicDB nao encontrado em {index_file}")

    include_pdf_files = include_pdfs()
    assets: list[dict[str, Any]] = []
    omitted: list[dict[str, Any]] = []
    included_roots: Counter[str] = Counter()
    omitted_roots: Counter[str] = Counter()

    for path in sorted(site_dir.rglob("*")):
        if not path.is_file() or path == index_file:
            continue
        relative = path.relative_to(site_dir).as_posix()
        size = path.stat().st_size
        root_name = relative.split("/", 1)[0]
        if should_include_asset(Path(relative), include_pdf_files):
            assets.append(
                {
                    "path": relative,
                    "mime": asset_mime(path),
                    "encoding": "base64",
                    "size": size,
                    "data": b64_file(path),
                }
            )
            included_roots[root_name] += 1
        else:
            omitted.append({"path": relative, "size": size, "suffix": path.suffix.lower()})
            omitted_roots[root_name] += 1

    omitted_suffixes = Counter(item["suffix"] or "sem extensao" for item in omitted)
    return {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source": "academicDB",
        "source_root": ACADEMICDB_ROOT.as_posix(),
        "site_root": site_dir.as_posix(),
        "include_pdfs": include_pdf_files,
        "index_html": index_file.read_text(encoding="utf-8"),
        "assets": assets,
        "asset_count": len(assets),
        "included_roots": dict(sorted(included_roots.items())),
        "omitted": {
            "count": len(omitted),
            "bytes": sum(item["size"] for item in omitted),
            "roots": dict(sorted(omitted_roots.items())),
            "suffixes": dict(sorted(omitted_suffixes.items())),
        },
    }


def render_academicdb_page() -> None:
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    page = f"""
Title: AcademicDB
Slug: academicdb
page_type: academicdb
subtitle: Catalogo academico protegido, gerado a partir dos sources em YAML.


<div id="academicdb-app" class="academicdb-app" data-vault-url="../static/academicdb/vault.json?v={stamp}">
  <section class="academicdb-lock" data-lock-screen>
    <div>
      <p class="academicdb-eyebrow">Area protegida</p>
      <h2>AcademicDB</h2>
      <p>Digite a mesma senha do financeiro para descriptografar o catalogo academico no seu navegador.</p>
    </div>
    <form class="academicdb-login" data-login-form>
      <label>
        <span>Senha</span>
        <input type="password" name="password" autocomplete="current-password" required>
      </label>
      <button type="submit">Entrar</button>
      <p class="academicdb-status" data-login-status></p>
    </form>
  </section>

  <section class="academicdb-private" data-private-area hidden>
    <div class="academicdb-shell-header">
      <div>
        <p class="academicdb-eyebrow">Catalogo descriptografado</p>
        <h2>AcademicDB</h2>
      </div>
      <p data-academicdb-summary></p>
    </div>
    <iframe data-academicdb-frame title="AcademicDB protegido" loading="lazy"></iframe>
  </section>
</div>

<script src="../static/js/academicdb.js?v={stamp}" defer></script>
"""
    write_text(ACADEMICDB_PAGE, page)


def sync_academicdb(password: str | None = None) -> dict[str, int]:
    rebuild_academicdb(ACADEMICDB_ROOT)
    payload = build_payload(ACADEMICDB_SITE_DIR)
    password = password or get_password()
    vault = encrypt_payload(payload, password)

    ACADEMICDB_STATIC_DIR.mkdir(parents=True, exist_ok=True)
    ACADEMICDB_VAULT.write_text(json.dumps(vault, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    render_academicdb_page()
    return {
        "assets": payload["asset_count"],
        "omitted": payload["omitted"]["count"],
        "omitted_bytes": payload["omitted"]["bytes"],
        "include_pdfs": 1 if payload["include_pdfs"] else 0,
    }


if __name__ == "__main__":
    counts = sync_academicdb()
    omitted_mb = counts["omitted_bytes"] / (1024 * 1024)
    print_sync_result(
        "AcademicDB",
        f"{counts['assets']} arquivos no vault, "
        f"{counts['omitted']} omitidos ({omitted_mb:.1f} MiB)",
    )
