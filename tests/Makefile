# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

include ../defines.make

SHELL    := /bin/bash -e
PIPENV2  := ../scripts/run-pipenv 2
BANDIT   := $(PIPENV2) run bandit
PYTEST   := $(PIPENV2) run py.test
FUTURIZE := $(PIPENV2) run ./test-futurize

.PHONY: help pipenv-check test-bandit \
        test-format-shell test-agent-integration \
        test-pylint test-python-futurize test-shellcheck test-unit \
        list-unit-tests test-unit-one-by-one test-unit-sh

help:
	@echo "pipenv-check              - Checks for security vulnerabilities/PEP 508 markers"
	@echo "test-bandit               - Run bandit (security) tests"
	@echo "test-format-shell         - Run the shell formatting"
	@echo "test-agent-integration    - Run agent (plugin) related integration tests"
	@echo "test-pylint               - Run pylint based tests"
	@echo "test-python-futurize      - Run python futurize tests"
	@echo "test-shellcheck           - Run shellcheck tests"
	@echo "test-unit                 - Run Python unit tests"
	@echo "test-unit-one-by-one      - Run unit tests one by one"
	@echo "test-unit-sh              - Run shell unit tests"

$(NODE_MODULES):
	$(MAKE) -C $(dir $(NODE_MODULES)) $(notdir $(NODE_MODULES))

bandit.ini:
	echo -e "[bandit]\ntargets: $$(../scripts/find-python-files 2 | tr '\n' ',' | sed 's/,$$//')" > bandit.ini

pipenv-check:
	$(PIPENV2) check

test-bandit: bandit.ini
# Currently only care about high severity reported issues. Once this is reached,
# go and enable the medium/low checks.
	$(BANDIT) -c ../bandit.yaml -r -lll --ini bandit.ini $(BANDIT_OUTPUT_ARGS)

test-format-shell:
	docker run --rm -v "$(realpath ..):/sh" -w /sh peterdavehello/shfmt shfmt -d -i 4 -ci $(SHELL_FILES)

test-agent-integration:
	$(PYTEST) -T agent-integration $(realpath agent-integration)

test-pylint:
	$(PYTEST) -T pylint pylint

test-python-futurize:
	$(FUTURIZE)

test-shellcheck:
	@CMK_DIR="$(realpath ..)" ; \
	ENTERPRISE_DIR="$(realpath ../enterprise)" ; \
	shellcheck \
		$(SHELLCHECK_OUTPUT_ARGS) \
		$$(grep -l '^#!/.*sh' $$CMK_DIR/agents/* $$CMK_DIR/agents/plugins/* $$CMK_DIR/agents/special/* 2>/dev/null) \
		"$$ENTERPRISE_DIR/agents/mk-remote-alert-handler"

test-integration: $(NODE_MODULES)
	$(PIPENV2) run ../tests-py3/scripts/run-integration-test.py $(realpath ../tests/integration)

test-unit:
	$(PYTEST) -T unit unit

# Probably a noteworthy entry for any "obfuscated bash/make/sed contest"...
list-unit-tests:
	@$(PYTEST) -T unit unit --collect-only  `# list tests in tree form` | \
	  grep '^\(<Module\|  <Function\) '         `# remove docstring lines` | \
	  sed 's/\[.*\]>/>/'                        `# remove test parameters` | \
	  uniq                                      `# keep only one line from parameterized tests` | \
	  sed 's,^<Module tests/\(.*\)>$$,#\1,'     `# keep file name plus a leading marker` | \
	  sed 's,^  <Function \(.*\)>$$,\1,'        `# keep function name` | \
	  sed -e '/^#/{h;d};G'                      `# precede every function name line with a file name line` \
	      -e 's/^\(.*\)\n#\(.*\)/\2::\1/'       `# glue the line pairs together`

test-unit-one-by-one:
	@set -e ; \
	for i in $$($(MAKE) --silent --no-print-directory list-unit-tests); do \
	  $(PYTEST) -T unit $$i ; \
	done

test-unit-sh:
	./sh_test_runner.sh
