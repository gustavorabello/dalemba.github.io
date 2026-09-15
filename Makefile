PYTHON ?= /Users/gustavo/miniforge3/envs/pelican/bin/python
PELICAN ?= /Users/gustavo/miniforge3/envs/pelican/bin/pelican
INPUTDIR ?= content
OUTPUTDIR ?= dalembinha.github.io
CONFFILE ?= pelicanconf.py
PUBLISHCONF ?= publishconf.py
PRESERVE ?= .git .gitignore
export PYTHONDONTWRITEBYTECODE := 1

announce = @if [ -t 1 ]; then printf '\033[1;36m==> %s\033[0m\n' "$(1)"; else printf '==> %s\n' "$(1)"; fi

.PHONY: html publish clean sync sync-tabs sync-recipes sync-financeiro sync-academicdb sanitize-content prepare-output preflight-publish serve commit

html: sync sanitize-content prepare-output
	$(call announce,Pelican build)
	$(PELICAN) $(INPUTDIR) -o $(OUTPUTDIR) -s $(CONFFILE)

publish: sync sanitize-content prepare-output
	$(call announce,Pelican publish build)
	$(PELICAN) $(INPUTDIR) -o $(OUTPUTDIR) -s $(PUBLISHCONF)

clean:
	$(call announce,Clean output)
	@$(PYTHON) scripts/prepare_output_directory.py --target "$(OUTPUTDIR)" --create-if-missing --preserve $(PRESERVE)

sync:
	$(PYTHON) scripts/sync_content.py

sync-tabs:
	$(PYTHON) scripts/sync_tabs.py

sync-recipes:
	$(PYTHON) scripts/sync_recipes.py

sync-financeiro:
	$(PYTHON) scripts/sync_financeiro.py

sync-academicdb:
	$(PYTHON) scripts/sync_academicdb.py

sanitize-content:
	$(call announce,Sanitize content tree)
	@$(PYTHON) scripts/cleanup_icloud_duplicates.py --target "content" --apply

prepare-output:
	$(call announce,Prepare output directory)
	@$(PYTHON) scripts/prepare_output_directory.py --target "$(OUTPUTDIR)" --create-if-missing --preserve $(PRESERVE)

preflight-publish:
	$(call announce,Preflight publish repository)
	@$(PYTHON) scripts/deploy_github_pages.py --deploy-repo "$(OUTPUTDIR)" --preflight

serve: html
	$(call announce,Serve output)
	@$(PYTHON) -m http.server 8000 --directory $(OUTPUTDIR)

commit: preflight-publish html
	$(call announce,Deploy GitHub Pages)
	@$(PYTHON) scripts/deploy_github_pages.py --source "$(OUTPUTDIR)" --deploy-repo "$(OUTPUTDIR)"
