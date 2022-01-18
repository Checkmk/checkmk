EXTERNAL_PYPI_MIRROR := https://pypi.python.org

INTERNAL_PYPI_MIRROR := https://artifacts.lan.tribe29.com/repository/pip-mirror-$(BRANCH_VERSION)

# Temporary fix to make nightly builds work again
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

# This will only work after exporting USE_EXTERNAL_PIPENV_MIRROR=true
pip-mirror-update: requirements.txt
	set -x; \
	PIP_MIRROR_FOLDER=./pip-mirror-tmp; \
	$(PIPENV) run pip download -r $< -d $${PIP_MIRROR_FOLDER}; \
	$(PIPENV) run twine upload -r pypi --repository-url $(INTERNAL_PYPI_MIRROR)/ $${PIP_MIRROR_FOLDER}/*;

