EXTERNAL_PYPI_MIRROR := https://pypi.python.org

INTERNAL_PYPI_MIRROR := https://artifacts.lan.tribe29.com/repository/pip-mirror-$(BRANCH_VERSION)

#ifeq (true,${USE_EXTERNAL_PIPENV_MIRROR})
PIPENV_PYPI_MIRROR  := $(EXTERNAL_PYPI_MIRROR)
#else
#PIPENV_PYPI_MIRROR  := $(INTERNAL_PYPI_MIRROR)
#endif

requirements.txt: Pipfile.lock
	@( \
	    echo "Creating $@" ; \
	    $(PIPENV) lock --dev -r > $@; \
            sed -i "1s|-i.*|-i https://pypi.python.org/simple/|" $@ \
	)

.PHONY: pip-mirror-update pip-mirror-update-internal

pip-mirror-update:
	@USE_EXTERNAL_PIPENV_MIRROR=true $(MAKE) --no-print-directory pip-mirror-update-internal

pip-mirror-update-internal: requirements.txt
	set -x; \
	PIP_MIRROR_FOLDER=./pip-mirror-tmp; \
	$(PIPENV) run pip download -r $< -d $${PIP_MIRROR_FOLDER}; \
	$(PIPENV) run twine upload -r pypi --repository-url $(INTERNAL_PYPI_MIRROR)/ $${PIP_MIRROR_FOLDER}/*;
