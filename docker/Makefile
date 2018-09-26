# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
#

include ../defines.make

CREDENTIALS_FILE   := $$HOME/.cmk-credentials
DOCKER_REPO_NAME   := checkmk
SHELL              := /bin/bash -e -o pipefail

.PHONY: help setup setversion image image-daily clean test-lint-dockerfile test-lint-entrypoint

help:
	@echo "make setup                - Prepare local (Ubuntu) system for building"
	@echo "make image                - Build container image for current edition, branch, version"
	@echo "make image-daily          - Build container image for current edition, branch, daily"
	@echo "make clean                - Cleanup docker images on current docker node"
	@echo "make test-lint-dockerfile - Execute linter tests on docker specific files"
	@echo "make test-lint-entrypoint - Execute linter tests on docker entrypoint script"

setup:
	curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
	sudo add-apt-repository \
	    "deb [arch=amd64] https://download.docker.com/linux/ubuntu $$(lsb_release -cs) stable"
	sudo apt-get update
	    sudo apt-get install docker-ce

setversion:
	sed -i 's/^ARG CMK_VERSION=.*$$/ARG CMK_VERSION="$(NEW_VERSION)"/g' Dockerfile

needed-packages: ../omd/distros/DEBIAN_9.mk
	echo -e 'needed-packages:\n\t@echo \$$(OS_PACKAGES) > needed-packages\n' | \
	    make -f - -f ../omd/distros/DEBIAN_9.mk --no-print-directory needed-packages

check-mk-$(EDITION)-docker-$(VERSION).tar.gz: image
	docker save $(DOCKER_REPO_NAME)/check-mk-$(EDITION):$(VERSION) | gzip > check-mk-$(EDITION)-docker-$(VERSION).tar.gz

image: needed-packages
	docker build \
	    --build-arg CMK_VERSION="$(VERSION)" \
	    --build-arg CMK_EDITION="$(EDITION)" \
	    --build-arg CMK_DL_CREDENTIALS="$$(cat "$(CREDENTIALS_FILE)")" \
	    -t $(DOCKER_REPO_NAME)/check-mk-$(EDITION):$(VERSION) \
	    .

image-daily: needed-packages
	BRANCH_PREFIX="$$(git rev-parse --abbrev-ref HEAD)" ; \
	if [[ "$$BRANCH_PREFIX" == "master" || "$$BRANCH_PREFIX" =~ "/" ]]; then \
	    BRANCH_PREFIX="" ; \
	else \
	    BRANCH_PREFIX="$${BRANCH_PREFIX}-" ; \
	fi ; \
	VERSION="$$(date +%F)" ; \
	VERSION="$${BRANCH_PREFIX}$${VERSION//-/.}" ; \
	CREDENTIALS="$$(cat "$(CREDENTIALS_FILE)")" ; \
	docker build \
	    --build-arg CMK_VERSION="$${VERSION}" \
	    --build-arg CMK_EDITION=$(EDITION) \
	    --build-arg CMK_DL_CREDENTIALS="$$CREDENTIALS" \
	    -t $(DOCKER_REPO_NAME)/check-mk-$(EDITION):$${VERSION} \
	    -t $(DOCKER_REPO_NAME)/check-mk-$(EDITION):$${BRANCH_PREFIX}daily \
	    .

test-lint-dockerfile:
	sudo docker run --rm -i hadolint/hadolint < Dockerfile

test-lint-entrypoint:
	shellcheck $(SHELLCHECK_OUTPUT_ARGS) docker-entrypoint.sh

clean:
	-docker rmi $(DOCKER_REPO_NAME)/check-mk-$(EDITION):latest || true
	-docker rmi $(DOCKER_REPO_NAME)/check-mk-$(EDITION):$(VERSION) || true
	[ -e needed-packages ] && rm needed-packages || true
	ls check-mk-*-docker-*.tar.gz >/dev/null 2>&1 && rm check-mk-*-docker-*.tar.gz || true
