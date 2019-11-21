SHELL    := /bin/bash -e
PIPENV3  := ../scripts/run-pipenv 3
PYTEST   := $(PIPENV3) run py.test -vv
MYPY     := ../scripts/run-mypy
# TODO: Use find-python-files helper to check same files as other tests?
MYPY_DIRS_TO_CHECK := \
	cmk \
	cmk_base \
	cmk_base/automations \
	cmk_base/cee \
	cmk_base/data_sources \
	cmk_base/default_config \
	cmk_base/modes \
	cmk/cee \
	cmk/cee/dcd \
	cmk/cee/dcd/connectors \
	cmk/cee/mknotifyd \
	cmk/cee/notification_plugins \
	cmk/ec \
	cmk/gui \
	cmk/gui/cee \
	cmk/cee/liveproxy \
	cmk/gui/cee/plugins \
	cmk/gui/cee/plugins/config \
	cmk/gui/cee/plugins/cron \
	cmk/gui/cee/plugins/dashboard \
	cmk/gui/cee/plugins/main_modules \
	cmk/gui/cee/plugins/metrics \
	cmk/gui/cee/plugins/reporting \
	cmk/gui/cee/plugins/sidebar \
	cmk/gui/cee/plugins/sla \
	cmk/gui/cee/plugins/views \
	cmk/gui/cee/plugins/views/icons \
	cmk/gui/cee/plugins/visuals \
	cmk/gui/cee/plugins/wato \
	cmk/gui/cee/plugins/watolib \
	cmk/gui/cee/plugins/webapi \
	cmk/gui/cme \
	cmk/gui/cme/plugins \
	cmk/gui/cme/plugins/config \
	cmk/gui/cme/plugins/dashboard \
	cmk/gui/cme/plugins/main_modules \
	cmk/gui/cme/plugins/sidebar \
	cmk/gui/cme/plugins/views \
	cmk/gui/cme/plugins/visuals \
	cmk/gui/cme/plugins/wato \
	cmk/gui/plugins \
	cmk/gui/plugins/config \
	cmk/gui/plugins/cron \
	cmk/gui/plugins/dashboard \
	cmk/gui/plugins/main_modules \
	cmk/gui/plugins/metrics \
	cmk/gui/plugins/sidebar \
	cmk/gui/plugins/userdb \
	cmk/gui/plugins/views \
	cmk/gui/plugins/views/icons \
	cmk/gui/plugins/views/perfometers \
	cmk/gui/plugins/wato \
	cmk/gui/plugins/watolib \
	cmk/gui/plugins/wato/check_parameters \
	cmk/gui/plugins/wato/utils \
	cmk/gui/plugins/webapi \
	cmk/gui/wato \
	cmk/gui/watolib \
	cmk/gui/wato/pages \
	cmk/notification_plugins \
	cmk/special_agents \
	cmk/utils \
	cmk/utils/rulesets

# TODO: Directories with typing bugs
#	cmk/gui/plugins/visuals

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
