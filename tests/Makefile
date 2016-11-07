SHELL=/bin/bash

help:
	@echo "test        - Run all tests"
	@echo "test-pylint - Run pylint based tests"
	@echo "test-bandit - Run bandit (security) tests"
	@echo "setup       - Install dependencies"

test:
	py.test

test-pylint:
	py.test -k pylint

test-bandit:
	# Currently only care about high severity reported issues. Once this is
	# reached, go and enable the medium/low checks.
	bandit \
		-c ../bandit.yaml \
		-r \
		-f xml -o $$WORKDIR/bandit_results.xml \
		-lll \
		$(realpath ..) \
		$(realpath ..)/{checks,inventory}/* \
		$(realpath ../cmc/)


test-pylint-ci:
	export TERM="linux" ; \
	export PYLINT_ARGS="--output-format=cmk_parseable" ; \
	export PYLINT_OUTPUT="$$WORKDIR/pylint.log" ; \
	echo -n > $$WORKDIR/pylint.log ; \
	$(MAKE) test-pylint


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
