SHELL=/bin/bash -e

help:
	@echo "test           - Run integration and git tests"
	@echo "test-pylint    - Run pylint based tests"
	@echo "test-pylint-ci - Run pylint based tests within Jenkins"
	@echo "test-bandit    - Run bandit (security) tests"
	@echo "test-bandit-ci - Run bandit (security) tests within Jenkins"
	@echo "setup          - Install dependencies"

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


setup:
	sudo apt-get install \
	    python-pip \
	    python-lxml \
	    python-enchant \
	    python-lockfile \
	    chrpath
	sudo pip install --upgrade pip
	sudo pip install --upgrade \
	    pytest \
	    requests \
	    beautifulsoup4 \
	    pytest-stepwise \
	    dill \
	    html5lib \
	    bandit
	$(MAKE) -C pylint setup
