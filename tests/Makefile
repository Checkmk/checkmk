SHELL    := /bin/bash -e
PIPENV   := PIPENV_VENV_IN_PROJECT=true pipenv
PYTEST   := $(PIPENV) run py.test -s -vv
BANDIT   := $(PIPENV) run bandit

.PHONY: help pipenv-check test-unit test-integration test-gui-crawl test-pylint \
        test-packaging test-docker test-bandit test-shellcheck sanitize format \
        test-mypy test-pylint-simple

help:
	@echo "setup                     - Install dependencies"
	@echo "test-unit                 - Run unit tests"
	@echo "test-integration          - Run integration tests"
	@echo "test-gui-crawl            - Run GUI crawl test"
	@echo "test-pylint               - Run pylint based tests"
	@echo "test-bandit               - Run bandit (security) tests"
	@echo "test-shellcheck           - Run shellcheck tests"
	@echo "test-docker               - Run docker tests"

# This target needs to be phony so it is run every time because only the other
# makefile can determine that there's nothing to be done.
# TODO: Move everything to top level makefile?
.PHONY: ../.venv

../.venv:
	$(MAKE) -C .. .venv

pipenv-check: ../.venv
	$(PIPENV) check

test-unit: ../.venv
	$(PYTEST) -T unit

test-integration: ../.venv
	$(PYTEST) -T integration

test-gui-crawl: ../.venv
	$(PYTEST) -T gui_crawl

test-pylint: ../.venv
	$(PYTEST) -T pylint

test-packaging: ../.venv
	$(PYTEST) -T packaging

test-docker: ../.venv
	$(MAKE) -C ../docker test-lint-dockerfile test-lint-entrypoint
	$(PYTEST) -T docker

test-bandit: ../.venv
# Finding all the Python stuff in our project is a bit tricky/ugly...
	( cd .. ; \
	  echo '[bandit]'; \
	  echo -n 'targets: '; \
	  for i in $$(find $$(realpath active_checks \
	                               agents \
	                               bin \
	                               checks \
	                               cmk \
	                               cmk_base \
	                               doc \
	                               enterprise \
	                               inventory \
	                               livestatus \
	                               managed \
	                               notifications \
	                               omd/packages/cma \
	                               omd/packages/maintenance \
	                               omd/packages/omd \
	                               scripts \
	                               tests \
	                               web \
	                               werk ) \
	                   -type f | sort ); do \
	      { [[ "$$i" == *.py ]] || { head -n 1 "$$i" | grep -q '^#!.*python$$'; } ; } && echo -n "$$i,"; \
	  done ) | sed 's/,$$//' > bandit.ini
# Currently only care about high severity reported issues. Once this is reached,
# go and enable the medium/low checks.
	$(BANDIT) -c ../bandit.yaml -r -lll --ini bandit.ini $(BANDIT_OUTPUT_ARGS)

test-shellcheck:
	@CMK_DIR="$(realpath ..)" ; \
	ENTERPRISE_DIR="$(realpath ../enterprise)" ; \
	shellcheck \
		$(SHELLCHECK_OUTPUT_ARGS) \
		$$(grep -l '^#!/.*sh' $$CMK_DIR/agents/* $$CMK_DIR/agents/plugins/* $$CMK_DIR/agents/special/* 2>/dev/null) \
		"$$ENTERPRISE_DIR/agents/mk-remote-alert-handler"


# TODO(sp): Proof of concept only for now, do this in a more general way
PYTHONPATH := $(realpath ..)
MYPYPATH := $(realpath typeshed)
FILES_TO_CHECK := $(realpath $(addprefix ../cmk/ec/,defaults.py export.py settings.py))

sanitize: format test-mypy test-pylint-simple

format:
	autopep8 -i $(FILES_TO_CHECK)

test-mypy:
	MYPYPATH="$(MYPYPATH)" mypy --py2 --follow-imports=silent --strict-optional $(FILES_TO_CHECK)

test-pylint-simple:
	PYTHONPATH="$(PYTHONPATH)" pylint $(FILES_TO_CHECK)
