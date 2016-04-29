help:
	@echo "all     - Run ALL checks"
	@echo "modules - Check modules"
	@echo "web     - Check web"
	@echo "checks  - Check checks, inventory, bakery plugins"
	@echo "misc    - Check other files (mkeventd, active checks, agent plugins)"
	@echo
	@echo "build   - Run all checks from build system"
	@echo "setup   - Install required tools"

all: modules web checks misc

modules:
	./pylint-modules || true

web:
	./pylint-web || true

checks:
	./pylint-checks || true

misc:
	./pylint-misc || true

build:
	export TERM="linux" ; \
	export PYLINT_ARGS="--output-format=cmk_parseable" ; \
	export PYLINT_OUTPUT="$$WORKDIR/pylint.log" ; \
	echo -n > pylint.log ; \
	$(MAKE) all

setup:
	sudo pip install --upgrade pylint
