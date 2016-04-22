help:
	@echo "all     - Run ALL checks"
	@echo "modules - Run Check_MK modules checks"
	@echo "web     - Run Check_MK web checks"
	@echo "checks  - Run Check_MK check checks"
	@echo
	@echo "build   - Run all checks from build system"

all: modules web checks

modules:
	./pylint-modules

web:
	./pylint-web

checks:
	./pylint-checks


build:
	export TERM="linux" ; \
	$(MAKE) all > pylint.log
