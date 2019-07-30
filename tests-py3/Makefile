SHELL    := /bin/bash -e
VENV     := ../.venv-3.7
NODE_MODULES := ../node_modules
PIPENV   := PIPENV_VENV_IN_PROJECT=true pipenv
PYTEST   := $(PIPENV) run py.test -vv

include ../defines.make

.PHONY: help pipenv-check test-bandit test-docker test-format-python \
        test-gui-crawl test-integration test-packaging test-pylint \
        test-shellcheck test-format-shell \
	test-unit test-unit-coverage-html

help:
	echo $(MAKE) -C $(dir $(VENV)) $(notdir $(VENV))
	@echo "test-pylint               - Run pylint based tests"
	@echo "test-unit                 - Run unit tests"

# These target need to be phony so it is run every time because only the other
# makefile can determine that there's nothing to be done.
# TODO: Move everything to top level makefile?
.PHONY: $(VENV) bandit.ini

$(VENV):
	$(MAKE) -C $(dir $(VENV)) $(notdir $(VENV))

test-pylint: $(VENV)
	$(PYTEST) -T pylint pylint

test-unit: $(VENV)
	$(PYTEST) -T unit git unit

