help:
	@echo "all     - Run ALL checks"
	@echo "modules - Run Check_MK modules checks"
	@echo "web     - Run Check_MK web checks"
	@echo "checks  - Run Check_MK check checks"
	@echo
	@echo "build   - Run all checks from build system"

all: modules web checks

modules:
	./pylint-modules || true

web:
	./pylint-web || true

checks:
	./pylint-checks || true

build:
	export TERM="linux" ; \
	export PYLINT_ARGS="--output-format=cmk_parseable" ; \
	export PYLINT_OUTPUT="$$WORKDIR/pylint.log" ; \
	echo -n > pylint.log ; \
	$(MAKE) all
