# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Relies on the following environment variables:
# CHECKMK_DIR -- name of the clone of the Checkmk git repository, e.g. check_mk
# CHECKMK_LOCALE_DIR -- name of the clone of the Checkmk localization git repository, e.g. checkmk-locale
# PO_COMMIT_MSG -- commit message used commit changes in po files in Checkmk repository

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
	@echo "update-pot - Pull in Checkmk repository, update, commit and push multisite.pot in Checkmk localization repository accordingly"
	@echo "update-pos - Pull changes in Checkmk localization repository, update, commit and push po-files in Checkmk repository accordingly"

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


# Update multisite.pot (in Checkmk localization repository) by running xgettext on our code, commit and push. This is
# executed in a cronjob on the VM webdeploy. See https://wiki.lan.tribe29.com/link/898#bkmrk-backend.
# Note: we cannot use the option --omit-header here, because:
# https://www.gnu.org/software/gettext/manual/html_node/xgettext-Invocation.html
# "Note that using this option will lead to an error if the resulting file would not entirely be in ASCII."
update-pot:
	git pull
	xgettext -w 80 --sort-output --force-po -L python --from-code=utf-8 -o scanned.pot \
	../web/app/index.wsgi \
	../livestatus/api/python/livestatus.py \
        $$(find -L ../cmk -type f -name "*.py") 2>&1 | \
	sed "/format string with unnamed arguments cannot be properly localized/,/and a mapping instead of a tuple for the arguments./d"
	sed -i "0,/^$$/d" scanned.pot # Remove default header, i.e. everything before first empty line
	cat header scanned.pot > ../../$$CHECKMK_LOCALE_DIR/$(MULTISITE_POT) # Add our header and write to Checkmk localization repo
	rm scanned.pot
	cd ../../$$CHECKMK_LOCALE_DIR; \
	git pull; \
	if [[ $$(git diff | wc -l) -gt 0 ]]; then \
	    git commit $(MULTISITE_POT) -m "Updated $(MULTISITE_POT)"; \
	    git push; \
	fi


# 1) Pull in Checkmk localization repo
# 2) Remove code comments from .po files and write to Checkmk repo
# 3) Commit and push in Checkmk repo
# This is executed in a cronjob on the VM webdeploy. See https://wiki.lan.tribe29.com/link/898#bkmrk-backend.
update-pos:
	git pull
	cd ../../$$CHECKMK_LOCALE_DIR; \
	git pull; \
	for lang in $(LANGUAGES); do \
	    sed '/^#[.:|]/d' $$lang/multisite.po > ../$$CHECKMK_DIR/locale/$$lang/LC_MESSAGES/multisite.po; \
	done
	if [[ $$(git diff | wc -l) -gt 0 ]]; then # Checkmk repo \
	    git commit ./ -m "$$PO_COMMIT_MSG"; \
	    git push; \
	fi
