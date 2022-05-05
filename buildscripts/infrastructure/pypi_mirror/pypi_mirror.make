EXTERNAL_PYPI_MIRROR := https://pypi.python.org/simple

INTERNAL_PYPI_MIRROR :=  https://$(DEVPI_SERVER):$(DEVPI_PORT)/$(BRANCH_VERSION)/prod/+simple/

ifeq (true,${USE_EXTERNAL_PIPENV_MIRROR})
PIPENV_PYPI_MIRROR  := $(EXTERNAL_PYPI_MIRROR)
else
PIPENV_PYPI_MIRROR  := $(INTERNAL_PYPI_MIRROR)
endif

REPO_DIR := "$(git rev-parse --show-toplevel)"
TMP_MIRROR := tmp-mirror-1
TMP_DIR := tmp_devpi_pkg

.PHONY: pip-mirror-verify pip-mirror-update pip-mirror-update-internal

# Create requirements.txt containing all dependencies.
# This includes runtime and dev dependencies.
requirements.txt: Pipfile.lock
	@( \
	    echo "Creating $@" ; \
	    USE_EXTERNAL_PIPENV_MIRROR=true $(PIPENV) lock --dev -r > $@; \
            sed -i "1s|-i.*|-i https://pypi.python.org/simple/|" $@ \
	)

# Create requirements.txt containing only runtime dependencies.
runtime-requirements.txt: Pipfile.lock
	@( \
	    echo "Creating $@" ; \
	    USE_EXTERNAL_PIPENV_MIRROR=true $(PIPENV) lock -r > $@; \
            sed -i "/^-i.*\|^-e.*/d" $@ \
	)

# 1-i Create a temporariy mirror and download source and wheel packages
# Makefile internal, as not dockerized
pip-mirror-dl-pkgs-internal: runtime-requirements.txt
	set -x; \
	rm -rf .venv ; \
	make PIPENV_PYPI_MIRROR='https://$(DEVPI_SERVER)/$(BRANCH_VERSION)/$(TMP_MIRROR)/+simple/' .venv ; \
	$(PIPENV) run devpi use https://$(DEVPI_SERVER); \
	$(PIPENV) run devpi login $(DEVPI_USER) --password $(DEVPI_PWD); \
	$(PIPENV) run devpi index -c "$(BRANCH_VERSION)"/${TMP_MIRROR} type=mirror mirror_url=https://pypi.org/simple/ ; \
	pip3 install \
	--ignore-installed  \
	--no-binary=":all:" \
	--no-deps \
	--compile \
        --progress-bar off \
	-i https://$(DEVPI_SERVER)/$(BRANCH_VERSION)/$(TMP_MIRROR)/+simple/ \
	-r $< ; \

# 1. Dockerizes pip-mirror-dl-pkgs-internal
pip-mirror-dl-pkgs:
	scripts/run-in-docker.sh make DEVPI_USER=$(DEVPI_USER) DEVPI_PWD=$(DEVPI_PWD) pip-mirror-dl-pkgs-internal

# 2. Downlaod all packages from mirror created in pip-mirror-dl-pkgs to local machime
# Cannot be easily dockerized in Make, since passing the key is not trivial
pip-mirror-scp-pkgs-internal: 
	mkdir -p ${TMP_DIR} ; \
	scp -o StrictHostKeyChecking=no -i $(DEVPI_KEY) -r devpi@${DEVPI_SERVER}:/var/devpi/+files/$(BRANCH_VERSION)/$(TMP_MIRROR)/+f/ ${TMP_DIR}

# 3-i Populate or update the production mirror with the previously downloaded packages 
pip-mirror-ul-pkgs-internal:
	$(PIPENV) run devpi use https://$(DEVPI_SERVER); \
        $(PIPENV) run devpi login $(DEVPI_USER) --password $(DEVPI_PWD); \
	$(PIPENV) run devpi index -c $(BRANCH_VERSION)/prod; \
	$(PIPENV) run devpi use $(BRANCH_VERSION)/prod; \
	$(PIPENV) run devpi upload --from-dir $(TMP_DIR)

# 3. Dockerize pip-mirror-ul-pkgs-internal
pip-mirror-ul-pkgs:
	scripts/run-in-docker.sh make DEVPI_USER=$(DEVPI_USER) DEVPI_PWD=$(DEVPI_PWD) pip-mirror-ul-pkgs-internal

# 4-i Make sure the mirror is working
pip-mirror-verify-internal: runtime-requirements.txt
	set -x; scripts/run-in-docker.sh pip3 install \
	--ignore-installed  \
	--no-binary=":all:" \
	--no-deps \
	--compile \
        --progress-bar off \
	-i $(INTERNAL_PYPI_MIRROR) \
	-r $<

# 4. Dockerize pip-mirror-verify-internal
pip-mirror-verify:
	scripts/run-in-docker.sh make pip-mirror-verify-internal
