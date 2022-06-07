# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Relies on the following environment variables:
# CHECKMK_DIR -- name of the clone of the Checkmk git repository, e.g. check_mk
# CHECKMK_LOCALE_DIR -- name of the clone of the Checkmk localization git repository, e.g. checkmk-locale
# PO_COMMIT_MSG -- commit message used commit changes in po files in Checkmk repository
# MSGFMT_OUT -- file for storing output of msgfmt during update-pos

# Note: the language files which are *installed* are set by CHECK_MK_LANGUAGES in check_mk.make
LANGUAGES := de ro nl fr it ja pt_PT es
SHELL 	  := /bin/bash -e -o pipefail
MULTISITE_POT = multisite.pot

help:
	@echo "setup      - Install gettext (needed to build mo-files)"
	@echo "mo         - Build mo-files from po-files for all languages"
	@echo "update-pot - Pull in Checkmk repository, update, commit and push multisite.pot in Checkmk localization repository accordingly"
	@echo "update-pos - Pull changes in Checkmk localization repository, update, commit and push po-files in Checkmk repository accordingly"

setup:
	sudo apt-get install gettext

mo:
	for lang in $(LANGUAGES) ; do \
		   msgfmt -v -o $$lang/LC_MESSAGES/multisite.mo $$lang/LC_MESSAGES/multisite.po ; \
		done

# Update multisite.pot (in Checkmk localization repository) by running xgettext on our code, commit and push. This is
# executed in a cronjob on the VM webdeploy. See https://wiki.lan.tribe29.com/link/898#bkmrk-backend.
# Note: we cannot use the option --omit-header here, because:
# https://www.gnu.org/software/gettext/manual/html_node/xgettext-Invocation.html
# "Note that using this option will lead to an error if the resulting file would not entirely be in ASCII."
update-pot:
	# pull in CHECKMK_LOCALE_DIR
	cd ../../$$CHECKMK_LOCALE_DIR; \
	git pull --rebase
	# back in CHECKMK_DIR
	git pull --rebase
	xgettext -w 80 --sort-output --force-po -L python --from-code=utf-8 -o scanned.pot \
	../web/app/index.wsgi \
	../livestatus/api/python/livestatus.py \
		$$(find -L ../cmk -type f -name "*.py") 2>&1 | \
	sed "/format string with unnamed arguments cannot be properly localized/,/and a mapping instead of a tuple for the arguments./d"
	sed -i "0,/^$$/d" scanned.pot # Remove default header, i.e. everything before first empty line
	cat header scanned.pot > ../../$$CHECKMK_LOCALE_DIR/$(MULTISITE_POT) # Add our header and write to Checkmk localization repo
	rm scanned.pot
	cd ../../$$CHECKMK_LOCALE_DIR; \
	if [[ $$(git diff | wc -l) -gt 0 ]]; then \
		git commit $(MULTISITE_POT) -m "Updated $(MULTISITE_POT)"; \
		git push; \
	fi

# 1) Pull in Checkmk and Checkmk localization repo
# 2) Check for issues concerning Python formatters.
# 3) Remove code comments from .po files and write to Checkmk repo.
# 4) Commit and push in Checkmk repo.
# This is executed in a cronjob on the VM webdeploy. See https://wiki.lan.tribe29.com/link/898#bkmrk-backend.
update-pos:
	rm -f $$MSGFMT_OUT
	git pull --rebase
	cd ../../$$CHECKMK_LOCALE_DIR; \
	git pull --rebase; \
	for lang in $(LANGUAGES); do \
		(msgfmt --check-format -o temp.mo $$lang/multisite.po &>> $$MSGFMT_OUT) || true; \
	done; \
	rm -f temp.mo; \
	if [[ -s $$MSGFMT_OUT ]]; then \
		echo "ERROR: Non-empty msgfmt output"; \
		exit 1; \
	fi; \
	for lang in $(LANGUAGES); do \
		sed '/^#[.:|]/d' $$lang/multisite.po > ../$$CHECKMK_DIR/locale/$$lang/LC_MESSAGES/multisite.po; \
	done
	# We are back in the Checkmk repo
	if [[ $$(git diff | wc -l) -gt 0 ]]; then \
		git commit ./ -m "$$PO_COMMIT_MSG"; \
		git push; \
	fi
