SHELL    := /bin/bash -e
PIPENV3  := ../scripts/run-pipenv 3
PYTEST   := $(PIPENV3) run py.test -vv
MYPY     := ../scripts/run-mypy
# TODO: Use find-python-files helper to check same files as other tests?
MYPY_FILES_TO_CHECK := \
	$(realpath $(addprefix ../cmk/ec/,defaults.py export.py main.py settings.py)) \
	$(realpath $(wildcard ../cmk/cee/dcd/*.py)) \
	$(realpath $(wildcard ../cmk/cee/dcd/connectors/*.py)) \
	$(realpath $(wildcard ../cmk/*.py)) \
	$(realpath $(wildcard ../cmk/utils/*.py)) \
	$(realpath $(wildcard ../cmk/notification_plugins/*.py)) \
	$(realpath $(wildcard ../cmk/special_agents/*.py)) \
	$(realpath $(wildcard ../cmk_base/*.py)) \
	$(wildcard $(realpath ..)/cmk_base/cee/*.py) \
	$(wildcard $(realpath ..)/cmk_base/automations/*.py) \
	$(wildcard $(realpath ..)/cmk_base/modes/*.py) \
	$(wildcard $(realpath ..)/cmk_base/data_sources/*.py) \
	$(realpath $(addprefix ../cmk/gui/,dashboard.py exceptions.py globals.py htmllib.py \
	                                   i18n.py sidebar.py sites.py table.py visuals.py permissions.py)) \
	$(realpath $(addprefix ../cmk/gui/watolib/,rulespecs.py)) \
	$(realpath $(addprefix ../cmk/gui/plugins/userdb/,htpasswd.py utils.py)) \
	$(realpath $(wildcard ../cmk/gui/plugins/wato/utils/*.py))

.PHONY: help test-docker test-pylint test-unit \
	test-mypy test-mypy-raw clean

help:
	@echo "test-mypy                 - Run mypy tests"
	@echo "test-mypy-raw             - Run mypy tests with raw edition config"
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

test-mypy:
	$(MYPY) --config-file=$(realpath ../mypy.ini) $(MYPY_FILES_TO_CHECK)

test-mypy-raw:
	$(MYPY) --config-file=$(realpath ../mypy-raw.ini) $(MYPY_FILES_TO_CHECK)

clean:
	rm -rf .mypy_cache
