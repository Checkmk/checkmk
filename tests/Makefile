help:
	@echo "test        - Run all tests"
	@echo "test-pylint - Run pylint based tests"
	@echo "setup       - Install dependencies"

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


setup:
	sudo pip install \
	    pytest \
	    requests \
	    beautifulsoup4 \
	    pytest-stepwise
	sudo apt-get install \
	    python-lxml
	$(MAKE) -C pylint setup
