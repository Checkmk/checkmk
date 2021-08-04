# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

#

include ../defines.make

CREDENTIALS_FILE         := $$HOME/.cmk-credentials
DOCKER_REPO_NAME         := checkmk
SHELL                    := /bin/bash -e -o pipefail
RESOLVE_CMD              := ../buildscripts/docker_image_aliases/resolve.sh
SECRET_CONTAINER_ID_CMD  := docker run -d --rm \
    --volume $(CREDENTIALS_FILE):/files/secret \
    $$($(RESOLVE_CMD) IMAGE_BUSYBOX_LATEST) timeout 180 httpd -f -p 8000 -h /files

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
	sudo bash -c 'usermod -a -G docker $$SUDO_USER'

setversion:
	sed -i 's/^ARG CMK_VERSION=.*$$/ARG CMK_VERSION="$(NEW_VERSION)"/g' Dockerfile

needed-packages: ../omd/distros/DEBIAN_10.mk
	echo -e '.PHONY: needed-packages\nneeded-packages:\n\t@echo \$$(OS_PACKAGES) > needed-packages\n' | \
	    make -f - -f ../omd/distros/DEBIAN_10.mk --no-print-directory needed-packages

check-mk-$(EDITION)-docker-$(VERSION).tar.gz: image
	docker save $(DOCKER_REPO_NAME)/check-mk-$(EDITION):$(VERSION) | gzip > check-mk-$(EDITION)-docker-$(VERSION).tar.gz

check-mk-$(EDITION)-docker-$(VERSION).demo.tar.gz: image-demo
	docker save $(DOCKER_REPO_NAME)/check-mk-$(EDITION):$(VERSION).demo | gzip > check-mk-$(EDITION)-docker-$(VERSION).demo.tar.gz

image: needed-packages
	SECRET_CONTAINER_ID=$$($(SECRET_CONTAINER_ID_CMD)) ; \
	docker build \
	    --network=container:$$SECRET_CONTAINER_ID \
	    --build-arg CMK_VERSION="$(VERSION)" \
	    --build-arg CMK_EDITION="$(EDITION)" \
	    --build-arg IMAGE_CMK_BASE=$$($(RESOLVE_CMD) IMAGE_CMK_BASE) \
	    -t $(DOCKER_REPO_NAME)/check-mk-$(EDITION):$(VERSION) \
	    . ; \
	docker stop $$SECRET_CONTAINER_ID

image-demo: needed-packages
	SECRET_CONTAINER_ID=$$($(SECRET_CONTAINER_ID_CMD)) ; \
	docker build \
	    --network=container:$$SECRET_CONTAINER_ID \
	    --build-arg CMK_VERSION="$(VERSION).demo" \
	    --build-arg CMK_EDITION="$(EDITION)" \
	    --build-arg IMAGE_CMK_BASE=$$($(RESOLVE_CMD) IMAGE_CMK_BASE) \
	    -t $(DOCKER_REPO_NAME)/check-mk-$(EDITION):$(VERSION).demo \
	    . ; \
	docker stop $$SECRET_CONTAINER_ID

image-daily: needed-packages
	SECRET_CONTAINER_ID=$$($(SECRET_CONTAINER_ID_CMD)) ; \
	BRANCH_PREFIX="$$(git rev-parse --abbrev-ref HEAD)" ; \
	if [[ "$$BRANCH_PREFIX" == "master" || "$$BRANCH_PREFIX" =~ "/" ]]; then \
	    BRANCH_PREFIX="" ; \
	else \
	    BRANCH_PREFIX="$${BRANCH_PREFIX}-" ; \
	fi ; \
	VERSION="$${VERSION:-$$(date +%F)}" ; \
	VERSION="$${BRANCH_PREFIX}$${VERSION//-/.}" ; \
	docker build \
	    --network=container:$$SECRET_CONTAINER_ID \
	    --build-arg CMK_VERSION="$${VERSION}" \
	    --build-arg CMK_EDITION=$(EDITION) \
	    --build-arg IMAGE_CMK_BASE=$$($(RESOLVE_CMD) IMAGE_CMK_BASE) \
	    -t $(DOCKER_REPO_NAME)/check-mk-$(EDITION):$${VERSION} \
	    -t $(DOCKER_REPO_NAME)/check-mk-$(EDITION):$${BRANCH_PREFIX}daily \
	    . ; \
	docker stop $$SECRET_CONTAINER_ID

test-lint-dockerfile:
	docker run --rm -i $$($(RESOLVE_CMD) IMAGE_HADOLINT) < Dockerfile

test-lint-entrypoint:
	shellcheck $(SHELLCHECK_OUTPUT_ARGS) docker-entrypoint.sh

clean:
	-docker rmi $(DOCKER_REPO_NAME)/check-mk-$(EDITION):latest || true
	-docker rmi $(DOCKER_REPO_NAME)/check-mk-$(EDITION):$(VERSION) || true
	[ -e needed-packages ] && rm needed-packages || true
	ls check-mk-*-docker-*.tar.gz >/dev/null 2>&1 && rm check-mk-*-docker-*.tar.gz || true
