SHELL    := /bin/bash -e
PIPENV3  := ../scripts/run-pipenv 3
PYTEST   := $(PIPENV3) run py.test -vv
MYPY     := ../scripts/run-mypy

.PHONY: help test-docker test-pylint test-unit \
	test-mypy test-mypy-raw test-mypy3 test-mypy3-raw \
	clean test-packaging

help:
	@echo "test-mypy                 - Run mypy tests"
	@echo "test-mypy-raw             - Run mypy tests with raw edition config"
	@echo "test-mypy3                - Run mypy tests for Python 3"
	@echo "test-mypy3-raw            - Run mypy tests for Python 3 with raw edition config"
	@echo "test-docker               - Run docker tests"
	@echo "test-pylint               - Run pylint based tests"
	@echo "test-unit                 - Run unit tests"
	@echo "test-packaging            - Run packaging tests"

test-docker:
	$(MAKE) -C ../docker test-lint-dockerfile test-lint-entrypoint
	$(PYTEST) -T docker docker

test-pylint:
	$(PYTEST) -T pylint pylint

test-unit:
	$(PYTEST) -T unit unit

test-mypy3:
	$(MYPY) $$(../scripts/find-python-files 3)

test-mypy3-raw:
	$(MYPY) --config-file=$(realpath ../mypy-raw.ini) $$(../scripts/find-python-files 3)

# TODO: This is a real hack caused by our dubious directory structure plus the
# use of --scripts-are-modules. Is this really the right flag to use?
MYPY2_FILES=$$(../scripts/find-python-files 2 | grep -v '/agents/special/\|/agents/plugins/\|/active_checks/\|/bin/check_mk\|/bin/mkbackup\|/agents/wnx/integration/local.py')

test-mypy:
	$(MYPY) $(MYPY2_FILES)

test-mypy-raw:
	$(MYPY) --config-file=$(realpath ../mypy-raw.ini)  $(MYPY2_FILES)

test-packaging:
	$(PYTEST) -T packaging packaging

clean:
	rm -rf .mypy_cache
