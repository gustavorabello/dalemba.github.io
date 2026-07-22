# dalemba-site

Site estático em Pelican para `https://dalembinha.github.io`, reunindo dois acervos:

- `Músicas`: páginas geradas a partir dos `.txt` em `/Users/gustavo/Documents/brazil/musica/tabs`
- `Receitas`: páginas migradas para `source_data/recipes`, independentes do projeto antigo

O objetivo do projeto é manter um fluxo simples:

1. atualizar as fontes locais
2. gerar o conteúdo do site
3. publicar o diretório `dalembinha.github.io/`

## Visão geral

O projeto é dividido em quatro camadas:

- `source_data/`
  Fontes locais permanentes das receitas e suas imagens.
- `content/`
  Conteúdo consumido pelo Pelican. Inclui páginas fixas, conteúdo gerado e assets estáticos.
- `scripts/`
  Automação de sincronização, saneamento do iCloud, preparo de publicação e deploy.
- `dalembinha.github.io/`
  Saída final publicada no GitHub Pages. Este é o diretório que deve virar o repositório publicado.

## Estrutura

```text
dalemba-site/
├── content/
│   ├── generated/
│   │   ├── recipes/
│   │   └── tabs/
│   ├── pages/
│   └── static/
│       ├── css/
│       ├── images/
│       └── js/
├── dalembinha.github.io/
├── scripts/
├── source_data/
│   ├── recipe_images/
│   └── recipes/
├── theme/
├── Makefile
├── pelicanconf.py
└── publishconf.py
```

## Como o conteúdo nasce

### Músicas

As músicas não são escritas diretamente dentro do Pelican.

Fonte principal:

- `/Users/gustavo/Documents/brazil/musica/tabs`

Fluxo:

1. `scripts/sync_tabs.py` chama o conversor local `scripts/generate_tabs.py`
2. o gerador converte cada `.txt` em uma página Pelican em `content/generated/tabs/`
3. o script recria a página de listagem em `content/pages/musicas.md`
4. o site final sai em `/musicas/...`

Recursos embutidos nas páginas:

- numeração contínua da lista
- sugestão da próxima música
- respeito a `Próxima:` ou `Next:` no `.txt`
- transposição de tom no navegador
- análise harmônica expansível, com escala e caminhos de resolução
- cores distintas para acordes diatônicos e acordes fora da escala
- graus em algarismos romanos exibidos junto às cifras durante a análise
- ajuste de fonte

O gerador estima automaticamente a tonalidade pelas cifras. Para informar o tom
com precisão, inclua uma linha como `Tom: C`, `Tom: F#` ou `Tom: Gm` depois do
título e do artista. A linha funciona como metadado e não aparece na letra.

Para escolher manualmente a sugestão exibida depois de uma música, acrescente uma
linha após o título e o artista. O caminho relativo é a forma recomendada, pois
evita ambiguidades entre músicas com o mesmo nome:

```text
Próxima: chicoBuarque/aBanda.txt
```

Também são aceitos `Próximo:`, `Próxima música:` e `Next:`. Sem esse campo, a
sugestão continua sendo a música seguinte na ordem da listagem. Se o caminho não
existir ou for ambíguo, a sincronização termina com uma mensagem de erro para que
o TXT possa ser corrigido.

O diretório pode ser sobrescrito temporariamente com a variável de ambiente
`DALEMBA_TABS_DIR`, o que é útil para testes:

```bash
DALEMBA_TABS_DIR="/outro/diretorio/tabs" python3 scripts/sync_tabs.py
```

### Receitas

As receitas já vivem localmente neste projeto.

Fontes principais:

- `source_data/recipes`
- `source_data/recipe_images`

Fluxo:

1. `scripts/sync_recipes.py` converte o conteúdo antigo em páginas Pelican
2. as imagens são copiadas para `content/static/images/recipes`
3. a listagem é recriada em `content/pages/receitas.md`

Para incluir uma receita nova:

1. crie o arquivo-fonte em `source_data/recipes/`, por exemplo
   `source_data/recipes/lasanhaDaTata.html`
2. coloque a imagem em `source_data/recipe_images/`, por exemplo
   `source_data/recipe_images/lasanha.png`
3. dentro da receita, referencie a imagem como
   `[[!!images/recipes/lasanha.png]]`
4. execute `python3 scripts/sync_recipes.py`

O sincronizador gera a página em `content/generated/recipes/`, copia a imagem
para `content/static/images/recipes/` e atualiza a listagem de receitas.

## Scripts principais

- `scripts/sync_content.py`
  Orquestra tudo: receitas, músicas e home.
- `scripts/sync_tabs.py`
  Gera as páginas das músicas e a listagem `/musicas/`.
- `scripts/sync_recipes.py`
  Gera as páginas das receitas e a listagem `/receitas/`.
- `scripts/cleanup_icloud_duplicates.py`
  Remove duplicatas do iCloud, como `arquivo 2`, `arquivo 3` e `.icloud`.
- `scripts/prepare_output_directory.py`
  Limpa `dalembinha.github.io/` preservando `.git` e `.gitignore`.
- `scripts/deploy_github_pages.py`
  Faz o preflight e o deploy do diretório publicado.

## Comandos do Makefile

### Build local

```bash
cd "/Users/gustavo/Library/Mobile Documents/com~apple~CloudDocs/projects/python/dalemba-site"
make html
```

Esse comando:

1. sincroniza receitas e músicas
2. remove duplicatas de iCloud em `content/`
3. prepara `dalembinha.github.io/` preservando `.git`
4. roda o Pelican

### Servir localmente

```bash
make serve
```

Abre um servidor local em `http://localhost:8000`.

### Build de publicação

```bash
make publish
```

Usa `publishconf.py` e gera a versão pronta para produção em `dalembinha.github.io/`.

### Saneamento isolado

```bash
make sanitize-content
```

Remove artefatos duplicados do iCloud em `content/`.

### Deploy manual

```bash
make commit
```

Esse alvo foi configurado no estilo do `personal-site-pelican`:

1. faz preflight do repositório publicado
2. gera o site em `dalembinha.github.io/`
3. executa commit e `git push` no repositório publicado

## Fluxo de publicação recomendado

Há dois repositórios possíveis no seu dia a dia:

- repositório-fonte: `dalemba-site/`
- repositório publicado: `dalembinha.github.io/`

O diretório `dalembinha.github.io/` deve conter o repositório Git usado para publicação do GitHub Pages.

### Primeira configuração do repositório publicado

Na primeira vez, `dalembinha.github.io/` precisa virar um repositório Git real.

Exemplo:

```bash
cd "/Users/gustavo/Library/Mobile Documents/com~apple~CloudDocs/projects/python/dalemba-site"
rm -rf dalembinha.github.io
git clone git@github.com:dalembinha/dalembinha.github.io.git dalembinha.github.io
```

Depois disso, o fluxo com `make commit` passa a funcionar no estilo do `personal-site-pelican`.

Fluxo típico:

```bash
cd "/Users/gustavo/Library/Mobile Documents/com~apple~CloudDocs/projects/python/dalemba-site"
make commit
```

Se quiser só validar antes:

```bash
make preflight-publish
make html
```

## GitHub Pages

O projeto também possui workflow em:

- `.github/workflows/pages.yml`

Mas o fluxo principal deste projeto continua sendo local, porque a geração das músicas depende do acervo em `/Users/gustavo/Documents/brazil/musica/tabs`.

Em outras palavras:

- o GitHub Actions funciona bem para publicar o que já está dentro deste repositório
- a sincronização completa das músicas continua mais confiável quando feita localmente

## Cuidados importantes

- `pelicanconf.py` usa `DELETE_OUTPUT_DIRECTORY = False`
  Isso é intencional para não apagar o `.git` dentro de `dalembinha.github.io/`.
- `make clean` limpa o diretório publicado preservando `.git` e `.gitignore`.
- o conteúdo em `content/generated/` é reconstruído automaticamente; evite editar esses arquivos manualmente.
- as fontes reais das músicas ficam em `/Users/gustavo/Documents/brazil/musica/tabs`.

## Exemplos úteis

Gerar só músicas:

```bash
python3 scripts/sync_tabs.py
```

Gerar só receitas:

```bash
python3 scripts/sync_recipes.py
```

## Resultado final

Depois do build, o site sai em:

- `dalembinha.github.io/index.html`
- `dalembinha.github.io/musicas/`
- `dalembinha.github.io/receitas/`

Esse diretório é a publicação final do projeto.

## Financeiro protegido

O build também pode gerar `/financeiro/` a partir de `~/projects/financeiroDB`.
O fluxo roda `make` no projeto financeiro, lê os CSVs gerados e publica apenas um
`vault.json` criptografado em `content/static/financeiro/`. A página usa as categorias automáticas `mercado`, `farmacia`, `material` e `outros`.

A senha deve ter pelo menos 6 caracteres e não deve ser commitada. Configure de uma destas formas:

```bash
FINANCEIRO_PASSWORD="sua senha" make html
```

ou crie localmente `.financeiro-password`, que está no `.gitignore`.

Sem a senha, os dados financeiros não ficam legíveis no HTML, no JavaScript nem no
JSON publicado. Os PDFs e CSVs originais não são copiados para o site.

## AcademicDB protegido

O build também gera `/academicdb/` a partir do projeto AcademicDB em
`/Users/gustavo/Library/Mobile Documents/com~apple~CloudDocs/projects/academicDB`.
O fluxo roda apenas `make html` nesse projeto, lê a pasta `site/` gerada pelo
AcademicDB e publica um `vault.json` criptografado em `content/static/academicdb/`,
usando a mesma senha do financeiro (`FINANCEIRO_PASSWORD` ou `.financeiro-password`).

Por padrão, o vault inclui o HTML, os YAMLs e os gráficos. PDFs são omitidos para
manter o site leve, pois a exportação completa passa de centenas de MB. Para incluir
PDFs também, rode explicitamente:

```bash
ACADEMICDB_INCLUDE_PDFS=1 FINANCEIRO_PASSWORD="sua senha" make html
```

Para apontar para outro checkout do AcademicDB, defina `ACADEMICDB_ROOT`. Para usar
uma pasta de site já existente, defina `ACADEMICDB_SITE_DIR`. Para usar uma
exportação já existente sem rodar `make html` no AcademicDB, use
`ACADEMICDB_SKIP_REBUILD=1`.

O relatório de progressão/carreira não é gerado nem publicado pelo site
`dalembinha.github.io`; esse PDF continua sendo uma saída local explícita do
AcademicDB via `make report`.
