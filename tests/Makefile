SHELL=/bin/bash -e

help:
	@echo "test               - Run integration and git tests"
	@echo "test-pylint        - Run pylint based tests"
	@echo "test-pylint-ci     - Run pylint based tests from Jenkins"
	@echo "test-bandit        - Run bandit (security) tests"
	@echo "test-bandit-ci     - Run bandit (security) tests from Jenkins"
	@echo "test-shellcheck    - Run shellcheck tests"
	@echo "test-shellcheck-ci - Run shellcheck tests from Jenkins"
	@echo "setup              - Install dependencies"

test:
	py.test


test-pylint:
	py.test -m pylint


test-pylint-ci:
	export TERM="linux" ; \
	export PYLINT_ARGS="--output-format=cmk_parseable" ; \
	$(MAKE) test-pylint


test-bandit:
	# Currently only care about high severity reported issues. Once this is
	# reached, go and enable the medium/low checks.
	CMK_DIR="$(realpath ..)" ; \
	ENTERPRISE_DIR="$(realpath ../enterprise)" ; \
	bandit \
		-c "$$CMK_DIR/bandit.yaml" \
		-r \
		-lll \
		$(OUTPUT_ARGS) \
		"$$CMK_DIR" \
		$$(grep -l python "$$CMK_DIR"/bin/*) \
		"$$CMK_DIR"/{checks,inventory}/* \
		$$(grep -l python "$$ENTERPRISE_DIR"/bin/*) \
		"$$ENTERPRISE_DIR"/agents/{plugins,bakery}/*


test-bandit-ci:
	OUTPUT_ARGS="-f xml -o \"$$WORKDIR/bandit_results.xml\"" \
	    $(MAKE) test-bandit || true


test-shellcheck:
	@CMK_DIR="$(realpath ..)" ; \
	ENTERPRISE_DIR="$(realpath ../enterprise)" ; \
	shellcheck \
		$(OUTPUT_ARGS) \
		$$(grep -l '^#!/.*sh' $$CMK_DIR/agents/* $$CMK_DIR/agents/plugins/* $$CMK_DIR/agents/special/* 2>/dev/null) \
		"$$ENTERPRISE_DIR/agents/mk-remote-alert-handler" | tee $$REDIRECT


test-shellcheck-ci:
	OUTPUT_ARGS="-f checkstyle" \
	REDIRECT="$$WORKDIR/results.xml" \
	    $(MAKE) test-shellcheck || true



setup:
	sudo apt-get install \
	    python-pip \
	    chrpath
	    cabal-install
	sudo pip install --upgrade pip
	sudo pip install --upgrade --ignore-installed -r requirements.txt
	$(MAKE) -C pylint setup
