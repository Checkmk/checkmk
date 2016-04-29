help:
	@echo "all     - Run ALL checks"
	@echo "modules - Check modules"
	@echo "web     - Check web"
	@echo "checks  - Check checks, inventory, bakery plugins"
	@echo "misc    - Check other files (mkeventd, active checks, agent plugins)"
	@echo
	@echo "build   - Run all checks from build system"
	@echo "setup   - Install required tools"

all:
	EXIT_CODE=0 ; \
	$(MAKE) modules ; EXIT_CODE=$$(($$EXIT_CODE | $$?)) ; \
	$(MAKE) web ; EXIT_CODE=$$(($$EXIT_CODE | $$?)) ; \
	$(MAKE) checks ; EXIT_CODE=$$(($$EXIT_CODE | $$?)) ; \
	$(MAKE) misc ; EXIT_CODE=$$(($$EXIT_CODE | $$?)) ; \
	exit $$EXIT_CODE

modules:
	./pylint-modules

web:
	./pylint-web

checks:
	./pylint-checks

misc:
	./pylint-misc

build:
	export TERM="linux" ; \
	export PYLINT_ARGS="--output-format=cmk_parseable" ; \
	export PYLINT_OUTPUT="$$WORKDIR/pylint.log" ; \
	echo -n > $$WORKDIR/pylint.log ; \
	$(MAKE) all

setup:
	sudo pip install --upgrade pylint
