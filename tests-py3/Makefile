SHELL    := /bin/bash -e
PIPENV3  := ../scripts/run-pipenv 3
PYTEST   := $(PIPENV3) run py.test -vv

.PHONY: help test-docker test-pylint test-unit

help:
	@echo "test-docker               - Run docker tests"
	@echo "test-pylint               - Run pylint based tests"
	@echo "test-unit                 - Run unit tests"

test-docker:
	$(MAKE) -C $(REPO_PATH)/docker test-lint-dockerfile test-lint-entrypoint
	$(PYTEST) -T docker docker

test-pylint:
	$(PYTEST) -T pylint pylint

test-unit:
	$(PYTEST) -T unit unit
