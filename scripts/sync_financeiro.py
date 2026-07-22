#!/usr/bin/env python3

from __future__ import annotations

import base64
import getpass
import json
import mimetypes
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from site_sync_common import CONTENT_DIR, ROOT, print_sync_result, write_text


DEFAULT_FINANCEIRO_ROOT = Path.home() / "projects" / "financeiroDB"
FINANCEIRO_ROOT = Path(
    os.environ.get("FINANCEIRO_DB_DIR", str(DEFAULT_FINANCEIRO_ROOT))
).expanduser()
FINANCEIRO_SITE_DIR = Path(os.environ.get("FINANCEIRO_SITE_DIR", FINANCEIRO_ROOT / "site")).expanduser()
FINANCEIRO_STATIC_DIR = CONTENT_DIR / "static" / "financeiro"
FINANCEIRO_VAULT = FINANCEIRO_STATIC_DIR / "vault.json"
FINANCEIRO_PAGE = CONTENT_DIR / "pages" / "financeiro.md"
PBKDF2_ITERATIONS = 310_000


def rebuild_financeiro(root: Path) -> None:
    if os.environ.get("FINANCEIRO_SKIP_REBUILD") == "1":
        return
    if not (root / "Makefile").exists():
        raise SystemExit(f"Makefile do financeiroDB nao encontrado em {root}")
    subprocess.run(["make"], cwd=root, check=True)


def validate_password(password: str, source: str) -> str:
    if len(password) < 6:
        raise SystemExit(f"Senha de {source} precisa ter pelo menos 6 caracteres.")
    return password


def get_password() -> str:
    env_password = os.environ.get("FINANCEIRO_PASSWORD")
    if env_password:
        return validate_password(env_password.strip(), "FINANCEIRO_PASSWORD")

    password_file = ROOT / ".financeiro-password"
    if password_file.exists():
        password = password_file.read_text(encoding="utf-8").strip()
        if password:
            return validate_password(password, ".financeiro-password")

    if sys.stdin.isatty():
        password = getpass.getpass("Senha das areas protegidas: ").strip()
        return validate_password(password, "senha digitada")

    raise SystemExit(
        "Defina FINANCEIRO_PASSWORD ou crie .financeiro-password no diretorio do Pelican "
        "para gerar a area financeira criptografada."
    )


def encrypt_payload(payload: dict[str, Any], password: str) -> dict[str, Any]:
    node_program = r"""
const crypto = require("crypto").webcrypto;

function b64(bytes) {
  return Buffer.from(bytes).toString("base64");
}

(async () => {
  const chunks = [];
  for await (const chunk of process.stdin) chunks.push(chunk);
  const input = JSON.parse(Buffer.concat(chunks).toString("utf8"));
  const encoder = new TextEncoder();
  const salt = crypto.getRandomValues(new Uint8Array(16));
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const keyMaterial = await crypto.subtle.importKey(
    "raw",
    encoder.encode(input.password),
    "PBKDF2",
    false,
    ["deriveKey"]
  );
  const key = await crypto.subtle.deriveKey(
    { name: "PBKDF2", salt, iterations: input.iterations, hash: "SHA-256" },
    keyMaterial,
    { name: "AES-GCM", length: 256 },
    false,
    ["encrypt"]
  );
  const encrypted = new Uint8Array(await crypto.subtle.encrypt(
    { name: "AES-GCM", iv },
    key,
    encoder.encode(input.payload)
  ));
  process.stdout.write(JSON.stringify({
    version: 1,
    cipher: "AES-GCM",
    kdf: "PBKDF2",
    hash: "SHA-256",
    iterations: input.iterations,
    salt: b64(salt),
    iv: b64(iv),
    data: b64(encrypted)
  }));
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
"""
    process = subprocess.run(
        ["node", "-e", node_program],
        input=json.dumps(
            {
                "password": password,
                "iterations": PBKDF2_ITERATIONS,
                "payload": json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            },
            ensure_ascii=False,
        ),
        capture_output=True,
        check=True,
        text=True,
    )
    return json.loads(process.stdout)


def b64_file(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def asset_mime(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


def build_payload(site_dir: Path) -> dict[str, Any]:
    index_file = site_dir / "index.html"
    if not index_file.exists():
        raise SystemExit(f"Site do financeiroDB nao encontrado em {index_file}")

    pages: list[dict[str, str]] = []
    assets: list[dict[str, Any]] = []
    for path in sorted(site_dir.rglob("*")):
        if not path.is_file() or any(part.startswith(".") for part in path.relative_to(site_dir).parts):
            continue
        relative = path.relative_to(site_dir).as_posix()
        if path.suffix.lower() == ".html":
            pages.append({"path": relative, "html": path.read_text(encoding="utf-8")})
        else:
            assets.append(
                {
                    "path": relative,
                    "mime": asset_mime(path),
                    "encoding": "base64",
                    "size": path.stat().st_size,
                    "data": b64_file(path),
                }
            )

    return {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source": "financeiroDB",
        "entry_path": "index.html",
        "pages": pages,
        "assets": assets,
        "page_count": len(pages),
        "asset_count": len(assets),
    }


def render_financeiro_page() -> None:
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    page = f"""
Title: Financeiro
Slug: financeiro
page_type: financeiro
subtitle: O site completo do financeiroDB, atualizado e protegido por senha.


<div id="financeiro-app" class="financeiro-app" data-vault-url="https://dalembinha.github.io/static/financeiro/vault.json?v={stamp}">
  <section class="financeiro-lock" data-lock-screen>
    <div>
      <p class="financeiro-eyebrow">Área protegida</p>
      <h2>Financeiro</h2>
      <p>Digite a senha para abrir a versão atualizada do financeiroDB no seu navegador.</p>
    </div>
    <form class="financeiro-login" data-login-form>
      <label>
        <span>Senha</span>
        <input type="password" name="password" autocomplete="current-password" required>
      </label>
      <button type="submit">Entrar</button>
      <p class="financeiro-status" data-login-status></p>
    </form>
  </section>

  <section class="financeiro-private" data-private-area hidden>
    <div class="financeiro-shell-header">
      <div>
        <p class="financeiro-eyebrow">Site descriptografado</p>
        <h2>financeiroDB</h2>
      </div>
      <p data-financeiro-summary></p>
    </div>
    <iframe data-financeiro-frame title="financeiroDB protegido"></iframe>
  </section>
</div>

<script src="../static/js/financeiro.js?v={stamp}" defer></script>
"""
    write_text(FINANCEIRO_PAGE, page)


def sync_financeiro(password: str | None = None) -> dict[str, int]:
    rebuild_financeiro(FINANCEIRO_ROOT)
    payload = build_payload(FINANCEIRO_SITE_DIR)
    password = password or get_password()
    vault = encrypt_payload(payload, password)

    FINANCEIRO_STATIC_DIR.mkdir(parents=True, exist_ok=True)
    FINANCEIRO_VAULT.write_text(json.dumps(vault, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    render_financeiro_page()
    return {
        "paginas": payload["page_count"],
        "assets": payload["asset_count"],
        "produtos": sum(page["path"].startswith("produtos/") for page in payload["pages"]),
    }


if __name__ == "__main__":
    counts = sync_financeiro()
    print_sync_result(
        "Financeiro",
        f"{counts['paginas']} paginas no vault, {counts['produtos']} produtos",
    )
