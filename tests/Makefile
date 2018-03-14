SHELL=/bin/bash -e

.PHONY: help test-pylint test-integration test-gui-crawl \
	test-bandit test-shellcheck setup format test-mypy \
        test-pylint-simple

help:
	@echo "setup              - Install dependencies"
	@echo "test-integration   - Run integration tests"
	@echo "test-pylint        - Run pylint based tests"
	@echo "test-gui-crawl     - Run GUI crawl test"
	@echo "test-bandit        - Run bandit (security) tests"
	@echo "test-shellcheck    - Run shellcheck tests"


test-integration:
	py.test \
	    -m "not pylint and not packaging and not git and not html_gentest and not gui_crawl" \
	    -s \
	    -vv


test-gui-crawl:
	py.test -s -m gui_crawl


test-pylint:
	py.test -m pylint


test-bandit:
# Currently only care about high severity reported issues. Once this is reached,
# go and enable the medium/low checks.
	CMK_DIR="$(realpath ..)" ; \
	ENTERPRISE_DIR="$(realpath ../enterprise)" ; \
	bandit \
		-c "$$CMK_DIR/bandit.yaml" \
		-r \
		-lll \
		$(BANDIT_OUTPUT_ARGS) \
		"$$CMK_DIR" \
		$$(grep -l python "$$CMK_DIR"/bin/*) \
		"$$CMK_DIR"/{checks,inventory}/* \
		$$(grep -l python "$$ENTERPRISE_DIR"/bin/*) \
		"$$ENTERPRISE_DIR"/agents/plugins/*.py \
		"$$ENTERPRISE_DIR"/agents/bakery/*


test-shellcheck:
	@CMK_DIR="$(realpath ..)" ; \
	ENTERPRISE_DIR="$(realpath ../enterprise)" ; \
	shellcheck \
		$(SHELLCHECK_OUTPUT_ARGS) \
		$$(grep -l '^#!/.*sh' $$CMK_DIR/agents/* $$CMK_DIR/agents/plugins/* $$CMK_DIR/agents/special/* 2>/dev/null) \
		"$$ENTERPRISE_DIR/agents/mk-remote-alert-handler"


setup:
	sudo apt-get install \
	    python-pip \
	    chrpath \
	    cabal-install
	sudo pip install --upgrade pip
	sudo pip install --upgrade --ignore-installed -r requirements.txt
	$(MAKE) -C pylint setup

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
