SHELL    := /bin/bash -e
VENV     := ../.venv
NODE_MODULES := ../node_modules
PIPENV   := PIPENV_VENV_IN_PROJECT=true pipenv
BANDIT   := $(PIPENV) run bandit
COVERAGE := $(PIPENV) run coverage
PYTEST   := $(PIPENV) run py.test -vv
YAPF     := $(PIPENV) run yapf
FUTURIZE := $(PIPENV) run ./test-futurize

include ../defines.make

.PHONY: help pipenv-check test-bandit test-docker test-format-python \
        test-format-shell test-gui-crawl test-integration test-packaging \
        test-pylint test-python-futurize test-shellcheck test-unit \
        list-unit-tests test-unit-one-by-one test-unit-coverage-html

help:
	echo $(MAKE) -C $(dir $(VENV)) $(notdir $(VENV))
	@echo "pipenv-check              - Checks for security vulnerabilities/PEP 508 markers"
	@echo "test-bandit               - Run bandit (security) tests"
	@echo "test-docker               - Run docker tests"
	@echo "test-format-python        - Test the python formatting"
	@echo "test-format-shell         - Run the shell formatting"
	@echo "test-gui-crawl            - Run GUI crawl test"
	@echo "test-integration          - Run integration tests"
	@echo "test-packaging            - Run packaging tests"
	@echo "test-pylint               - Run pylint based tests"
	@echo "test-python-futurize      - Run python futurize tests"
	@echo "test-shellcheck           - Run shellcheck tests"
	@echo "test-unit                 - Run unit tests"
	@echo "test-unit-one-by-one      - Run unit tests one by one"
	@echo "test-unit-coverage-html   - Create HTML coverage report for unit tests"

# These target need to be phony so it is run every time because only the other
# makefile can determine that there's nothing to be done.
# TODO: Move everything to top level makefile?
.PHONY: $(VENV) bandit.ini

$(VENV):
	$(MAKE) -C $(dir $(VENV)) $(notdir $(VENV))

$(NODE_MODULES):
	$(MAKE) -C $(dir $(NODE_MODULES)) $(notdir $(NODE_MODULES))

bandit.ini:
	echo -e "[bandit]\ntargets: $$(./find-python-files | tr '\n' ',' | sed 's/,$$//')" > bandit.ini

pipenv-check: $(VENV)
	$(PIPENV) check

test-bandit: $(VENV) bandit.ini
# Currently only care about high severity reported issues. Once this is reached,
# go and enable the medium/low checks.
	$(BANDIT) -c ../bandit.yaml -r -lll --ini bandit.ini $(BANDIT_OUTPUT_ARGS)

test-docker: $(VENV)
	$(MAKE) -C ../docker test-lint-dockerfile test-lint-entrypoint
	$(PYTEST) -T docker docker

test-format-python: $(VENV) ../.style.yapf
# Explicitly specify --style [FILE] to prevent costly searching in parent directories
# for each file specified via command line
#
# There are some mixed up lines on stdout caused by the --parallel option.
# Nevertheless, we keep that option to get a big performance boost. GitHub issue
# opened for this problem: https://github.com/google/yapf/issues/644.
	@PYTHON_FILES=$${PYTHON_FILES-$$(./find-python-files)} ; \
	$(YAPF) --parallel --style ../.style.yapf --verbose --diff $$PYTHON_FILES | \
	grep '^+++ .*(reformatted)$$' | \
	sed -e 's/^+++ //' -e 's/[[:blank:]]*(reformatted)$$/:1:1: error: file needs formatting/'

test-format-shell:
	sudo docker run --rm -v "$(realpath ..):/sh" -w /sh peterdavehello/shfmt shfmt -d -i 4 -ci $(SHELL_FILES)

test-gui-crawl: $(VENV) $(NODE_MODULES)
	$(PYTEST) -T gui_crawl $(realpath integration/cmk/gui/test_crawl.py)

test-integration: $(VENV) $(NODE_MODULES)
	$(PYTEST) -T integration $(realpath integration)

test-packaging: $(VENV)
	$(PYTEST) -T packaging packaging

test-pylint: $(VENV)
	$(PYTEST) -T pylint pylint

test-python-futurize: $(VENV)
	$(FUTURIZE)

test-shellcheck:
	@CMK_DIR="$(realpath ..)" ; \
	ENTERPRISE_DIR="$(realpath ../enterprise)" ; \
	shellcheck \
		$(SHELLCHECK_OUTPUT_ARGS) \
		$$(grep -l '^#!/.*sh' $$CMK_DIR/agents/* $$CMK_DIR/agents/plugins/* $$CMK_DIR/agents/special/* 2>/dev/null) \
		"$$ENTERPRISE_DIR/agents/mk-remote-alert-handler"

test-unit: $(VENV)
	$(PYTEST) -T unit git unit

# Probably a noteworthy entry for any "obfuscated bash/make/sed contest"...
list-unit-tests: $(VENV)
	@$(PYTEST) -T unit git unit --collect-only  `# list tests in tree form` | \
	  grep '^\(<Module\|  <Function\) '         `# remove docstring lines` | \
	  sed 's/\[.*\]>/>/'                        `# remove test parameters` | \
	  uniq                                      `# keep only one line from parameterized tests` | \
	  sed 's,^<Module tests/\(.*\)>$$,#\1,'     `# keep file name plus a leading marker` | \
	  sed 's,^  <Function \(.*\)>$$,\1,'        `# keep function name` | \
	  sed -e '/^#/{h;d};G'                      `# precede every function name line with a file name line` \
	      -e 's/^\(.*\)\n#\(.*\)/\2::\1/'       `# glue the line pairs together`

test-unit-one-by-one: $(VENV)
	@set -e ; \
	for i in $$($(MAKE) --silent --no-print-directory list-unit-tests); do \
	  $(PYTEST) -T unit $$i ; \
	done

# TODO: We should perhaps use the pytest --cov/--cov-report options, which the
# pytest-cov plugin package adds to pyttest.
test-unit-coverage-html: $(VENV)
	$(COVERAGE) run --rcfile=.coveragerc_unit -m pytest -T unit git unit
	$(COVERAGE) html
