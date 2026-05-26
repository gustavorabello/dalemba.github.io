# misc-site

Projeto Pelican minimalista para dois acervos:

- tablaturas geradas a partir de `../pyTabs/txt2html.py`
- livro de receitas mantido localmente em `source_data/recipes`

## Estrutura

- `content/generated`: páginas geradas automaticamente
- `content/static`: CSS, JS e imagens copiadas das receitas
- `source_data/recipes`: fontes locais das receitas em HTML
- `source_data/recipe_images`: imagens locais das receitas
- `source_data/legacy_tabs_html`: acervo HTML antigo usado apenas para recuperação de tabs ausentes
- `scripts/sync_tabs.py`: sincroniza tablaturas a partir da lista de arquivos `../pyTabs/tabs_txt`
- `scripts/sync_recipes.py`: recria as receitas a partir das fontes locais em `source_data`
- `scripts/sync_content.py`: orquestra ambos e recria a home
- `scripts/recover_tabs_from_html.py`: recupera tabs antigas a partir do acervo HTML legado
- `theme/templates`: tema próprio do Pelican

## Uso

```bash
cd "/Users/gustavo/Library/Mobile Documents/com~apple~CloudDocs/projects/python/misc-site"
make html
```

Comandos úteis:

- `python3 scripts/sync_tabs.py`: recria as tablaturas e a página de listagem
- `python3 scripts/sync_recipes.py`: recria as receitas e a página de listagem
- `python3 scripts/sync_content.py`: roda tudo e atualiza também a home
- `python3 scripts/recover_tabs_from_html.py`: converte tabs ausentes do acervo HTML antigo para `.txt`
- `make html`: executa a sincronização completa e gera o site Pelican
- `make publish`: executa a sincronização completa e gera o site com `publishconf.py`

## GitHub Pages

O projeto foi preparado para publicar em `https://dalemba.github.io` com o workflow
[`pages.yml`](./.github/workflows/pages.yml).

Pontos importantes:

- o workflow do GitHub Pages compila apenas o conteúdo já presente neste repositório
- a sincronização com `../pyTabs` e com `source_data/recipes` continua sendo feita localmente
- antes de subir mudanças de tablaturas ou receitas, rode `make publish` localmente para atualizar:
  - `content/generated`
  - `content/static/images/recipes`

Fluxo sugerido:

```bash
cd "/Users/gustavo/Library/Mobile Documents/com~apple~CloudDocs/projects/python/misc-site"
make publish
git add .
git commit -m "Publica dalemba.github.io"
git push origin main
```
