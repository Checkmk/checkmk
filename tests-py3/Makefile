SHELL    := /bin/bash -e
PIPENV3  := ../scripts/run-pipenv 3
PYTEST   := $(PIPENV3) run py.test -vv
MYPY     := ../scripts/run-mypy

.PHONY: help test-docker test-pylint test-unit \
	test-mypy test-mypy-raw test-mypy3 test-mypy3-raw \
	clean test-packaging test-gui-crawl test-gui-crawl-docker

help:
	@echo "test-mypy                 - Run mypy tests"
	@echo "test-mypy-raw             - Run mypy tests with raw edition config"
	@echo "test-mypy3                - Run mypy tests for Python 3"
	@echo "test-mypy3-raw            - Run mypy tests for Python 3 with raw edition config"
	@echo "test-docker               - Run docker tests"
	@echo "test-pylint               - Run pylint based tests"
	@echo "test-unit                 - Run unit tests"
	@echo "test-packaging            - Run packaging tests"
	@echo "test-gui-crawl            - Run GUI crawl locally"
	@echo "test-gui-crawl-docker     - Run GUI crawl in container"

$(NODE_MODULES):
	$(MAKE) -C $(dir $(NODE_MODULES)) $(notdir $(NODE_MODULES))

test-docker:
	$(MAKE) -C ../docker test-lint-dockerfile test-lint-entrypoint
	$(PYTEST) -T docker docker

test-pylint:
	$(PYTEST) -T pylint pylint

test-unit:
	$(PYTEST) -T unit unit

MYPY3_FILES=$(shell \
    ../scripts/find-python-files 3 | \
    `: filter out plugins, they are not real modules` \
    grep -v $$(realpath '../checks') | \
    grep -v $$(realpath '../inventory') | \
    if test -d ../enterprise; then \
        grep -v $$(realpath '../agents')/bakery; \
    else \
        cat; \
    fi)

test-mypy3:
	$(MYPY) $(MYPY3_FILES)

test-mypy3-raw:
	$(MYPY) --config-file=$(realpath ../mypy-raw.ini) $(MYPY3_FILES)

MYPY2_FILES=$(shell \
    ../scripts/find-python-files 2 | \
    `: filter out plugins, they are not real modules` \
    grep -v $$(realpath '../agents/plugins') | \
    grep -v $$(realpath '../checks') | \
    grep -v $$(realpath '../doc/skeleton_check') | \
    grep -v $$(realpath '../doc/predictive') | \
    grep -v $$(realpath '../doc/bi-example-oracle.mk') | \
    grep -v $$(realpath '../doc/bi-example.mk') | \
    if test -d ../enterprise; then \
        grep -v $$(realpath '../agents')/bakery | \
        grep -v $$(realpath '../enterprise/agents/plugins'); \
    else \
        cat; \
    fi | \
    grep -v $$(realpath '../inventory') | \
    `: We should really check these, but currently there are too many errors. :-/` \
    grep -v $$(realpath '../active_checks') | \
    grep -v $$(realpath '../agents/special') | \
    grep -v $$(realpath '../agents/windows') | \
    grep -v $$(realpath '../agents/wnx') | \
    grep -v $$(realpath '../doc/treasures') | \
    grep -v $$(realpath '../livestatus/api/python') | \
    grep -v $$(realpath '../notifications/sms') | \
    grep -v $$(realpath '../omd/packages') | \
    grep -v $$(realpath '../tests')) | \
    `: This is currently a base+GUI and py2/py3 mix. Reenable when GUI is py3` \
    grep -v $$(realpath '../bin/cmk-update-config')

test-mypy:
	$(MYPY) $(MYPY2_FILES)

test-mypy-raw:
	$(MYPY) --config-file=$(realpath ../mypy-raw.ini)  $(MYPY2_FILES)

test-packaging:
	$(PYTEST) -T packaging packaging

test-gui-crawl: $(NODE_MODULES)
	$(PYTEST) -T gui_crawl $(realpath gui_crawl/test_gui_crawl.py)

test-gui-crawl-docker:
	$(PIPENV3) run gui_crawl/run-gui-crawl.py

clean:
	rm -rf .mypy_cache
