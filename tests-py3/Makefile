SHELL    := /bin/bash -e
PIPENV3  := ../scripts/run-pipenv 3
PYTEST   := $(PIPENV3) run py.test -vv
MYPY     := ../scripts/run-mypy
# TODO: Use find-python-files helper to check same files as other tests?
MYPY_DIRS_TO_CHECK := \
	cmk/ec \
	cmk/cee/dcd \
	cmk/cee/dcd/connectors \
	cmk \
	cmk/utils \
	cmk/notification_plugins \
	cmk/special_agents \
	cmk_base \
	cmk_base/cee \
	cmk_base/automations \
	cmk_base/modes \
	cmk_base/data_sources \
	cmk/gui \
	cmk/gui/watolib \
	cmk/gui/plugins/userdb \
	cmk/gui/plugins/wato/utils

# Horrible hack: Massage paths to make our symlinks "invisible". :-P
MYPY_FILES_TO_CHECK := \
	$(subst $(realpath ..)/managed,$(realpath ..), \
	  $(subst $(realpath ..)/enterprise,$(realpath ..), \
	    $(foreach dir,$(MYPY_DIRS_TO_CHECK), \
	      $(realpath $(wildcard ../$(dir)/*.py)))))

.PHONY: help test-docker test-pylint test-unit \
	test-mypy test-mypy-raw clean test-packaging

help:
	@echo "test-mypy                 - Run mypy tests"
	@echo "test-mypy-raw             - Run mypy tests with raw edition config"
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

test-mypy:
	$(MYPY) --config-file=$(realpath ../mypy.ini) $(MYPY_FILES_TO_CHECK)

test-mypy-raw:
	$(MYPY) --config-file=$(realpath ../mypy-raw.ini) $(MYPY_FILES_TO_CHECK)

test-packaging:
	$(PYTEST) -T packaging packaging

clean:
	rm -rf .mypy_cache
