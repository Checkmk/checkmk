LANGUAGES = de ro
SHELL=/bin/bash -e -o pipefail
PIPENV=pipenv

.PHONY: $(LANGUAGES)

help:
	@echo "setup          - Ubuntu/Debian für das Lokalisieren vorbereiten"
	@echo
	@echo "de             - Dies aufrufen, wenn man lokalisieren möchte"
	@echo "test-[de|ro]   - Gibt aus wer noch was lokalisieren muss"
	@echo "update-[de|ro] - Aktualisiert die PO-Datei mit neuen Texten"

setup:
	sudo apt-get install gettext poedit python-polib

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
	./add-authors $@
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


test-%: ../virtual-envs/3.7/.venv
	@L=$@ ; L=$${L#*-} ; $(PIPENV) run ./blame $$L
