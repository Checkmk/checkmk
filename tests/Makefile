SHELL=/bin/bash

help:
	@echo "test           - Run all tests"
	@echo "test-pylint    - Run pylint based tests"
	@echo "test-pylint-ci - Run pylint based tests within Jenkins"
	@echo "test-bandit    - Run bandit (security) tests"
	@echo "test-bandit-ci - Run bandit (security) tests within Jenkins"
	@echo "setup          - Install dependencies"

test:
	py.test


test-pylint:
	py.test -k pylint


test-pylint-ci:
	export TERM="linux" ; \
	export PYLINT_ARGS="--output-format=cmk_parseable" ; \
	export PYLINT_OUTPUT="$$WORKDIR/pylint.log" ; \
	echo -n > $$WORKDIR/pylint.log ; \
	$(MAKE) test-pylint


test-bandit:
	# Currently only care about high severity reported issues. Once this is
	# reached, go and enable the medium/low checks.
	CMK_DIR="$(realpath ..)" ; \
	CMC_DIR="$(realpath ../../cmc/)" ; \
	bandit \
		-c "$$CMK_DIR/bandit.yaml" \
		-r \
		-lll \
		$(OUTPUT_ARGS) \
		"$$CMK_DIR" \
		"$$CMK_DIR/bin/*" \
		"$$CMK_DIR"/{checks,inventory}/* \
		"$$CMC_DIR" \
		"$$CMC_DIR/bin/*" \
		"$$CMC_DIR"/agents/{plugins,bakery}/*


test-bandit-ci:
	OUTPUT_ARGS="-f xml -o \"$$WORKDIR/bandit_results.xml\"" \
	    $(MAKE) test-bandit


setup:
	sudo apt-get install \
	    python-pip \
	    python-lxml
	pip install --upgrade pip
	pip install --upgrade \
	    pytest \
	    requests \
	    beautifulsoup4 \
	    pytest-stepwise \
	    dill \
	    html5lib \
	    bandit
	$(MAKE) -C pylint setup
