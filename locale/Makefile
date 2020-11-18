# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Relies on the following environment variables:
# CHECKMK_DIR -- name of the clone of the Checkmk git repository, e.g. check_mk
# WEBLATE_DIR -- name of the clone of the Weblate git repository, e.g. weblate_git
# WEBLATE_COMMIT_MSG -- string used to identify commits from Weblate, e.g. "[Weblate] Updated translation files"
# WEBLATE_API_URL -- URL of Weblate API used to send commit command, e.g. "https://translate.checkmk.com/api/components/checkmk/some_component/repository/"
# WEBLATE_API_TOKEN -- Token for authenticating with the Weblate API

LANGUAGES := de ro
SHELL 	  := /bin/bash -e -o pipefail
PIPENV    := ../scripts/run-pipenv
MULTISITE_POT = multisite.pot

.PHONY: $(LANGUAGES)

help:
	@echo "setup          - Ubuntu/Debian für das Lokalisieren vorbereiten"
	@echo
	@echo "de             - Dies aufrufen, wenn man lokalisieren möchte"
	@echo "test-[de|ro]   - Gibt aus wer noch was lokalisieren muss"
	@echo "update-[de|ro] - Aktualisiert die PO-Datei mit neuen Texten"
	@echo "update-pot - Update multisite.pot"
	@echo "update-pos - Commit changes in po-files in Weblate, pull and apply them to Checkmk repository"

setup:
	sudo apt-get install gettext poedit python3-polib

all:
	for lang in $(LANGUAGES) ; do \
           msgfmt -v -o $$lang/LC_MESSAGES/multisite.mo $$lang/LC_MESSAGES/multisite.po ; \
        done

# Update po file from checked out source and then call poedit. Remove warnings
# about not-reorderable message strings.
update-%:
	@L=$@ ; \
	cd $${L#*-}/LC_MESSAGES ; \
	unset LANG ; \
	xgettext -w 80 --sort-output --force-po \
	         -L python --from-code=utf-8 --omit-header \
		 -o scanned.po \
		 ../../../web/app/index.wsgi \
		 ../../../livestatus/api/python/livestatus.py \
		 $$(find -L ../../../cmk -type f -name "*.py") 2>&1 < /dev/null | \
		 sed '/format string with unnamed arguments cannot be properly localized/,/and a mapping instead of a tuple for the arguments./d' ; \
	cat ../../header scanned.po > new.po ; \
	msgmerge -w 80 -q -U -v multisite.po new.po 2>&1 < /dev/null | grep -v "reference, merged" || true ; \
	rm -f new.po scanned.po

cleanup-%:
	@L=$@ ; L=$${L#*-}; \
	sed -i '/^#[:.]/d' $$L/LC_MESSAGES/multisite.po ; \
	sed -i '/"POT-Creation-Date:/d' $$L/LC_MESSAGES/multisite.po ; \
	sed -i '/"PO-Revision-Date:/d' $$L/LC_MESSAGES/multisite.po ; \
	sed -i '/"Last-Translator:/d' $$L/LC_MESSAGES/multisite.po ; \

de:
	$(MAKE) update-$@
	$(PIPENV) run ./add-authors $@
	POEDITOR=$$(which poedit 2>/dev/null || which virtaal 2>/dev/null) ; \
	if [ -z "$$POEDITOR" ]; then \
	    echo "ERROR: Unable to find PO file editor (poedit or virtual)" ; \
	    exit 1 ; \
	fi ; \
	$$POEDITOR $@/LC_MESSAGES/multisite.po
	$(MAKE) update-$@ # Sorgt für standardisierten Zeilenumbruch!
	$(MAKE) cleanup-$@

ro:
	$(MAKE) update-$@
	poedit $@/LC_MESSAGES/multisite.po
	sed -i '/^#:/d' $@/LC_MESSAGES/multisite.po


test-%:
	@L=$@ ; L=$${L#*-} ; $(PIPENV) run ./blame $$L


# Update multisite.pot by running xgettext on our code, commit and push. This is executed in a cronjob on the VM
# webdeploy. See https://wiki.lan.tribe29.com/link/898#bkmrk-backend.
update-pot:
	git pull
	xgettext -w 80 --sort-output --force-po -L python --from-code=utf-8 --omit-header -o scanned.pot \
	../web/app/index.wsgi \
	../livestatus/api/python/livestatus.py \
        $$(find -L ../cmk -type f -name "*.py") 2>&1 | \
	sed "/format string with unnamed arguments cannot be properly localized/,/and a mapping instead of a tuple for the arguments./d"
	cat header scanned.pot > new.pot
	mv new.pot $(MULTISITE_POT)
	rm scanned.pot
	if [[ $$(git diff $(MULTISITE_POT) | wc -l) -gt 0 ]]; then \
	    git commit $(MULTISITE_POT) -m "Updated $(MULTISITE_POT)"; \
	    git push; \
	fi


# 1) Tell Weblate to commit current changes
# 2) Pull committed changes from Weblate git
# 3) Create a patch file for each new commit
# 4) Apply patches to Checkmk repo
# 5) Push
# This is executed in a cronjob on the VM webdeploy. See https://wiki.lan.tribe29.com/link/898#bkmrk-backend.
update-pos:
	curl -d operation=commit -H "Authorization: Token $$WEBLATE_API_TOKEN" $$WEBLATE_API_URL
	cd ../../$$WEBLATE_DIR; \
	git pull --rebase; # Weblate repo \
	counter=0; \
	(git rev-list HEAD || true) | while read commit_id; do # || true is needed to avoid error 141 when breaking in the very first iteration \
	     commit_msg=$$(git log --format=%B -n 1 $$commit_id); \
	     if [[ $$commit_msg == *"$$WEBLATE_COMMIT_MSG"* ]]; then # only look at commits from Weblate \
		 if [[ $$commit_msg == *"Change-Id"* ]]; then # if the commit message contains a Change-Id, were are done (we have processed this commit before) \
		      break; \
		 fi; \
		 counter_str=$$( printf '%04d' $$counter ); \
		 patch_fn="../$$CHECKMK_DIR/$${counter_str}.patch"; \
		 git format-patch -1 -k --stdout $$commit_id > $$patch_fn; \
		 counter=$$((counter + 1)); \
	     fi; \
	done
	git pull # Checkmk repo
	patch_files=(../[0-9]*.patch); \
	for (( i=$${#patch_files[@]}-1; i>=0; i-- )); do # apply commits from oldest to newest \
	     patch_file="$${patch_files[$$i]}"; \
	     if ! [[ -f $$patch_file ]]; then # first check if file exists (only relevant in case there are no patches) \
      	          break; \
  	     fi; \
	     git am -k $$patch_file; \
	     git commit --amend --no-edit; # add Change-Id \
	     rm $$patch_file; \
	done
	git push # Checkmk repo
