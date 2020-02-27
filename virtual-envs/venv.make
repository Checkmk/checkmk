SHELL := /bin/bash -e -o pipefail
LOCK_FD := 200
LOCK_PATH := .venv.lock
MAKEFILE_DIR := $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
ROOT_DIR := $(shell realpath $(MAKEFILE_DIR)/..)
PIPENV := SKIP_MAKEFILE_CALL=1 $(ROOT_DIR)/scripts/run-pipenv $(PYTHON_VERSION)

# TODO: The line: sed -i "/\"markers\": \"extra == /d" Pipfile.lock; \
# can be removed if pipenv fixes this issue.
# See: https://github.com/pypa/pipenv/issues/3140
#      https://github.com/pypa/pipenv/issues/3026
# The recent pipenv version 2018.10.13 has a bug that places wrong markers in the
# Pipfile.lock. This leads to an error when installing packages with this
# markers and prints an error message. Example:
# Ignoring pyopenssl: markers 'extra == "security"' don't match your environment
# TODO: pipenv and make don't really cooperate nicely: Locking alone already
# creates a virtual environment with setuptools/pip/wheel. This could lead to a
# wrong up-to-date status of it later, so let's remove it here. What we really
# want is a check if the contents of .venv match the contents of Pipfile.lock.
# We should do this via some move-if-change Kung Fu, but for now rm suffices.
Pipfile.lock: Pipfile
	@( \
	    echo "Locking .venv for locking..." ; \
	    flock $(LOCK_FD); \
	    $(PIPENV) lock; \
	    sed -i "/\"markers\": \"extra == /d" Pipfile.lock; \
	    rm -rf .venv \
	) $(LOCK_FD)>$(LOCK_PATH)

# Remake .venv everytime Pipfile or Pipfile.lock are updated. Using the 'sync'
# mode installs the dependencies exactly as speciefied in the Pipfile.lock.
# This is extremely fast since the dependencies do not have to be resolved.
# Cleanup partially created pipenv. This makes us able to automatically repair
# broken virtual environments which may have been caused by network issues.
.venv: Pipfile.lock
	@type python$(PYTHON_VERSION) >/dev/null 2>&1 || ( \
	    echo "ERROR: python$(PYTHON_VERSION) can not be found. Execute: \"make setup\"" && \
	    exit 1 \
	)
	@( \
	    echo "Locking .venv for syncing..." ; \
	    flock $(LOCK_FD); \
	    $(RM) -r .venv; \
	    ($(PIPENV) sync --dev && \
			echo "export PYTHONPATH=$(ROOT_DIR)" >> .venv/bin/activate && \
			touch .venv) || \
	    ($(RM) -r .venv ; exit 1) \
	) $(LOCK_FD)>$(LOCK_PATH)
