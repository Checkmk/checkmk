SHELL    := /bin/bash -e
VENV     := ../.venv-3.7
PIPENV   := PIPENV_VENV_IN_PROJECT=true pipenv
PYTEST   := $(PIPENV) run py.test -vv

include ../defines.make

.PHONY: help test-docker test-pylint test-unit

help:
	echo $(MAKE) -C $(dir $(VENV)) $(notdir $(VENV))
	@echo "test-docker               - Run docker tests"
	@echo "test-pylint               - Run pylint based tests"
	@echo "test-unit                 - Run unit tests"

# These target need to be phony so it is run every time because only the other
# makefile can determine that there's nothing to be done.
# TODO: Move everything to top level makefile?
.PHONY: $(VENV)

$(VENV):
	$(MAKE) -C $(dir $(VENV)) $(notdir $(VENV))

test-docker: $(VENV)
	$(MAKE) -C ../docker test-lint-dockerfile test-lint-entrypoint
	$(PYTEST) -T docker docker

test-pylint: $(VENV)
	$(PYTEST) -T pylint pylint

test-unit: $(VENV)
	$(PYTEST) -T unit unit
