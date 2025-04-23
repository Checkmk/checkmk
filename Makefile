# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

#
include defines.make
include artifacts.make

DIST_ARCHIVE       := check-mk-$(EDITION)-$(OMD_VERSION).tar.gz
TAROPTS            := --owner=root --group=root --exclude=.svn --exclude=*~ \
                      --exclude=.gitignore --exclude=*.swp --exclude=.f12 \
                      --exclude=__pycache__ --exclude=*.pyc
ARTIFACT_STORAGE   := https://artifacts.lan.tribe29.com
# TODO: Prefixing the command with the environment variable breaks xargs usage below!
PIPENV             := PIPENV_PYPI_MIRROR=$(PIPENV_PYPI_MIRROR) scripts/run-pipenv

JAVASCRIPT_SOURCES := $(filter-out %_min.js, \
                          $(wildcard \
                              $(foreach subdir,* */* */*/* */*/*/* */*/*/*/*,web/htdocs/js/$(subdir).[jt]s)))

SCSS_SOURCES := $(wildcard $(foreach subdir,* */* */*/*,web/htdocs/themes/$(subdir)/*.scss))


WEBPACK_MODE       ?= production

OPENAPI_SPEC       := web/htdocs/openapi/checkmk.yaml

LOCK_FD := 200
LOCK_PATH := .venv.lock
PY_PATH := .venv/bin/python
ifneq ("$(wildcard $(PY_PATH))","")
  PY_VIRT_MAJ_MIN := $(shell "${PY_PATH}" -c "from sys import version_info as v; print(f'{v.major}.{v.minor}')")
else
  PY_VIRT_MAJ_MIN := "unknown"
endif

# The CI environment variable should only be set by Jenkins
CI ?= false

.PHONY: announcement all build check-setup \
        clean css dist documentation \
        format format-c test-format-c format-python format-shell \
        format-js help install mrproper mrclean \
        packages setup setversion version openapi \
        protobuf-files

help:
	@echo "setup                          --> Prepare system for development and building"
	@echo "make dist                      --> Create source tgz for later building of rpm/deb and livestatus tgz"
	@echo "make rpm                       --> Create rpm package"
	@echo "make deb                       --> Create deb package"
	@echo "make cma                       --> Create cma package"
	@echo "make version                   --> Switch to new version"

rpm:
	$(MAKE) -C omd rpm

deb:
	$(MAKE) -C omd deb

cma:
	$(MAKE) -C omd cma

check-setup:
	echo "From here on we check the successful setup of some parts ..."
	@if [[ ":$(PATH):" != *":$(HOME)/.local/bin:"* ]]; then \
	  echo "Your PATH is missing '~/.local/bin' to work properly with pipenv."; \
	  exit 1; \
	else \
		echo "Checks passed"; \
	fi

$(SOURCE_BUILT_LINUX_AGENTS):
	$(MAKE) -C agents $@

ifeq ($(ENTERPRISE),yes)
$(SOURCE_BUILT_AGENT_UPDATER):
	@echo "ERROR: Should have already been built by artifact providing jobs"
	@echo "If you don't need the artifacts, you can use "
	@echo "'scripts/fake-windows-artifacts' to continue with stub files"
	@exit 1
endif

$(SOURCE_BUILT_OHM) $(SOURCE_BUILT_WINDOWS):
	@echo "ERROR: Should have already been built by Windows node jobs"
	@echo "If you don't need the windows artifacts, you can use "
	@echo "'scripts/fake-windows-artifacts' to continue with stub files"
	@exit 1

# Is executed by our build environment from a "git archive" snapshot and during
# RPM building to create the source tar.gz for the RPM build process.
# Would use --exclude-vcs-ignores but that's available from tar 1.29 which
# is currently not used by most distros
# Would also use --exclude-vcs, but this is also not available
# And --transform is also missing ...
dist: $(SOURCE_BUILT_AGENTS) $(SOURCE_BUILT_AGENT_UPDATER) protobuf-files $(JAVASCRIPT_MINI) $(THEME_RESOURCES)
	$(MAKE) -C agents/plugins
	set -e -o pipefail ; EXCLUDES= ; \
	if [ -d .git ]; then \
	    git rev-parse HEAD > COMMIT ; \
	    for X in $$(git ls-files --directory --others -i --exclude-standard) ; do \
	    if [[ ! "$(DIST_DEPS)" =~ (^|[[:space:]])$$X($$|[[:space:]]) && $$X != omd/packages/mk-livestatus/mk-livestatus-$(VERSION).tar.gz && $$X != livestatus/* && $$X != enterprise/* ]]; then \
		    EXCLUDES+=" --exclude $${X%*/}" ; \
		fi ; \
	    done ; \
	else \
	    for F in $(DIST_ARCHIVE) non-free/cmk-update-agent/{build,build-32,src} non-free/cmk-update-agent/{build,build-32,src} enterprise/agents/winbuild; do \
		EXCLUDES+=" --exclude $$F" ; \
	    done ; \
	fi ; \
	if [ -d check-mk-$(EDITION)-$(OMD_VERSION) ]; then \
	    rm -rf check-mk-$(EDITION)-$(OMD_VERSION) ; \
	fi ; \
	mkdir check-mk-$(EDITION)-$(OMD_VERSION) ; \
	tar -c --wildcards \
	    $(TAROPTS) \
	    --exclude check-mk-$(EDITION)-$(OMD_VERSION) \
	    --exclude .git \
	    --exclude .gitignore \
	    --exclude .gitmodules \
	    --exclude .gitattributes \
	    $$EXCLUDES \
	    * .werks | tar x -C check-mk-$(EDITION)-$(OMD_VERSION)
	if [ -f COMMIT ]; then \
	    rm COMMIT ; \
	fi
	tar -cz --wildcards -f $(DIST_ARCHIVE) \
	    $(TAROPTS) \
	    check-mk-$(EDITION)-$(OMD_VERSION)
	rm -rf check-mk-$(EDITION)-$(OMD_VERSION)

announcement:
	mkdir -p $(CHECK_MK_ANNOUNCE_FOLDER)
	PYTHONPATH=${PYTHONPATH}:$(REPO_PATH) $(PIPENV) run python -m cmk.utils.werks announce .werks $(VERSION) --format=md > $(CHECK_MK_ANNOUNCE_MD)
	PYTHONPATH=${PYTHONPATH}:$(REPO_PATH) $(PIPENV) run python -m cmk.utils.werks announce .werks $(VERSION) --format=txt > $(CHECK_MK_ANNOUNCE_TXT)
	tar -czf $(CHECK_MK_ANNOUNCE_TAR) -C $(CHECK_MK_ANNOUNCE_FOLDER) .

packages:
	$(MAKE) -C agents packages


version:
	[ "$$(head -c 6 /etc/issue)" = "Ubuntu" \
          -o "$$(head -c 16 /etc/issue)" = "Debian GNU/Linux" ] \
          || { echo 'You are not on the reference system!' ; exit 1; }
	@newversion=$$(dialog --stdout --inputbox "New Version:" 0 0 "$(VERSION)") ; \
	if [ -n "$$newversion" ] ; then $(MAKE) NEW_VERSION=$$newversion setversion ; fi

# NOTE: CMake accepts only up to 4 non-negative integer version parts, so we
# replace any character (like 'p' or 'b') with a dot. Not completely correct,
# but better than nothing. We have to rethink this setversion madness, anyway.
setversion:
	sed -ri 's/^(VERSION[[:space:]]*:?= *).*/\1'"$(NEW_VERSION)/" defines.make
	sed -i 's/^__version__ = ".*"$$/__version__ = "$(NEW_VERSION)"/' cmk/utils/version.py bin/livedump
	sed -i 's/^set(CMK_VERSION .*)/set(CMK_VERSION ${NEW_VERSION})/' packages/neb/CMakeLists.txt
	$(MAKE) -C agents NEW_VERSION=$(NEW_VERSION) setversion
	sed -i 's/^ARG CMK_VERSION=.*$$/ARG CMK_VERSION="$(NEW_VERSION)"/g' docker_image/Dockerfile
ifeq ($(ENTERPRISE),yes)
	sed -i 's/^__version__ = ".*/__version__ = "$(NEW_VERSION)"/' non-free/cmk-update-agent/cmk_update_agent.py
	sed -i 's/^VERSION = ".*/VERSION = "$(NEW_VERSION)"/' omd/packages/enterprise/bin/cmcdump
	sed -i 's/^set(CMK_VERSION .*)/set(CMK_VERSION ${NEW_VERSION})/' packages/cmc/CMakeLists.txt
endif

$(OPENAPI_SPEC): $(shell find cmk/gui/openapi $(wildcard cmk/gui/cee/plugins/openapi) -name "*.py")
	@export PYTHONPATH=${REPO_PATH} ; \
	export TMPFILE=$$(mktemp);  \
	$(PIPENV) run python -m cmk.gui.openapi > $$TMPFILE && \
	mv $$TMPFILE $@


openapi-clean:
	rm -f $(OPENAPI_SPEC)
openapi: $(OPENAPI_SPEC)


# TODO: The --unsafe-perm was added because the CI executes this as root during
# tests and building versions. Once we have the then build system this should not
# be necessary anymore.
#
# NOTE 1: What we actually want are grouped targets, but this would require GNU
# make >= 4.3, so we use the common workaround of an intermediate target.
#
# NOTE 2: NPM people have a totally braindead idea about reproducible builds
# which almost all other people consider a bug, so we have to touch our target
# files. Read https://github.com/npm/npm/issues/20439 and be amazed...
#
# NOTE 3: NPM sometimes terminates with a very unhelpful "npm ERR! cb() never
# called!" message, where the underlying reason seems to be quite obscure, see
# https://npm.community/t/crash-npm-err-cb-never-called/858.
#
# NOTE 4: The sed call is to get the same "resolved" entries independent of the
# used registry. The resolved entry is only a hint for npm.
.INTERMEDIATE: .ran-npm
node_modules/.bin/webpack: .ran-npm
node_modules/.bin/prettier: .ran-npm
.ran-npm: package.json package-lock.json
	@echo "npm version: $$(npm --version)"
	npm --version | grep "^$(NPM_VERSION)\." >/dev/null 2>&1
	@echo "node version: $$(node --version)"
	node --version | grep "^v$(NODEJS_VERSION)\." >/dev/null 2>&1
	@echo "open file descriptor limit (soft): $$(ulimit -Sn)"
	@echo "open file descriptor limit (hard): $$(ulimit -Hn)"
	@if curl --silent --output /dev/null --head '${ARTIFACT_STORAGE}/#browse/browse:npm-proxy'; then \
	    REGISTRY=--registry=${ARTIFACT_STORAGE}/repository/npm-proxy/ ; \
            export SASS_BINARY_SITE='${ARTIFACT_STORAGE}/repository/archives/'; \
	    echo "Installing from local registry ${ARTIFACT_STORAGE}" ; \
	else \
	    REGISTRY= ; \
	    echo "Installing from public registry" ; \
        fi ; \
	npm ci --yes --audit=false --unsafe-perm $$REGISTRY
	sed -i 's#"resolved": "https://artifacts.lan.tribe29.com/repository/npm-proxy/#"resolved": "https://registry.npmjs.org/#g' package-lock.json
	touch node_modules/.bin/webpack node_modules/.bin/prettier

# NOTE 1: Match anything patterns % cannot be used in intermediates. Therefore, we
# list all targets separately.
#
# NOTE 2: For the touch command refer to the notes above.
#
# NOTE 3: The cma_facelift.scss target is used to generate a css file for the virtual
# appliance. It is called from the cma git's makefile and the built css file is moved
# to ~/git/cma/skel/usr/share/cma/webconf/htdocs/
.INTERMEDIATE: .ran-webpack
$(JAVASCRIPT_MINI): .ran-webpack
$(THEME_CSS_FILES): .ran-webpack
.ran-webpack: node_modules/.bin/webpack webpack.config.js postcss.config.js $(JAVASCRIPT_SOURCES) $(SCSS_SOURCES)
	WEBPACK_MODE=$(WEBPACK_MODE) ENTERPRISE=$(ENTERPRISE) node_modules/.bin/webpack --mode=$(WEBPACK_MODE:quick=development)
	touch $(JAVASCRIPT_MINI) $(THEME_CSS_FILES)

# TODO(sp) The target below is not correct, we should not e.g. remove any stuff
# which is needed to run configure, this should live in a separate target. In
# fact, we should really clean up all this cleaning-chaos and finally follow the
# GNU standards here (see "Standard Targets for Users",
# https://www.gnu.org/prep/standards/html_node/Standard-Targets.html).
clean:
	$(MAKE) -C omd clean
	rm -rf *.rpm *.deb *.exe \
	       *~ counters autochecks \
	       precompiled cache web/htdocs/js/*_min.js \
	       web/htdocs/themes/*/theme.css announce*

css: .ran-webpack

EXCLUDE_PROPER= \
	    --exclude="**/.vscode" \
	    --exclude="**/.idea" \
	    --exclude=".werks/.last" \
	    --exclude=".werks/.my_ids"

EXCLUDE_CLEAN=$(EXCLUDE_PROPER) \
	    --exclude=".venv" \
	    --exclude=".venv.lock" \
	    --exclude=".cargo" \
	    --exclude="node_modules"

# The list of files and folders to be protected from remove after "buildclean" is called
# Rust dirs are kept due to heavy load when compiled: .cargo, controller
AGENT_CTL_TARGET_PATH=packages/cmk-agent-ctl/target
MK_SQL_TARGET_PATH=packages/mk-sql/target
EXCLUDE_BUILD_CLEAN=$(EXCLUDE_CLEAN) \
	    --exclude="doc/plugin-api/build" \
	    --exclude=".cargo" \
	    --exclude=$(AGENT_CTL_TARGET_PATH) \
	    --exclude=$(MK_SQL_TARGET_PATH) \
	    --exclude="agents/plugins/*_2.py" \
	    --exclude="agents/plugins/*.py.checksum"

mrproper:
	git clean -d --force -x $(EXCLUDE_PROPER)

mrclean:
	git clean -d --force -x $(EXCLUDE_CLEAN)

# Used by our version build (buildscripts/scripts/build-cmk-version.jenkins)
# for cleaning up while keeping some build artifacts between version builds.
# This helps to speed up "make dist"
buildclean:
	git clean -d --force -x $(EXCLUDE_BUILD_CLEAN)


setup:
# librrd-dev is still needed by the python rrd package we build in our virtual environment
	sudo apt-get install \
	    build-essential \
	    clang-$(CLANG_VERSION) \
	    clang-format-$(CLANG_VERSION) \
	    clang-tidy-$(CLANG_VERSION) \
	    clang-tools-$(CLANG_VERSION) \
	    clangd-$(CLANG_VERSION) \
	    cmake \
	    curl \
	    direnv \
	    doxygen \
	    figlet \
	    gawk \
	    git \
	    ksh \
	    libclang-$(CLANG_VERSION)-dev \
	    libjpeg-dev \
	    libkrb5-dev \
	    libldap2-dev \
	    libmariadb-dev-compat \
	    libpango1.0-dev \
	    libpcap-dev \
	    librrd-dev \
	    libsasl2-dev \
	    libsqlite3-dev \
	    libtool-bin \
	    libxml2-dev \
	    libreadline-dev \
	    libxml2-dev \
	    libxslt-dev \
	    libpq-dev \
	    libreadline-dev \
	    lld-$(CLANG_VERSION) \
	    lldb-$(CLANG_VERSION) \
	    musl-tools \
	    p7zip-full \
	    patchelf \
	    python3-pip \
	    python3-venv \
	    shellcheck \
	    valgrind \
	    zlib1g-dev
	if type pyenv >/dev/null 2>&1 && pyenv shims --short | grep '^pipenv$$'; then \
	    CMD="pyenv exec" ; \
	else \
	    CMD="" ; \
	fi ; \
	$$CMD pip3 install --user --upgrade \
	    pip \
	    pipenv=="$(PIPENV_VERSION)" \
	    virtualenv=="$(VIRTUALENV_VERSION)" \
	    wheel
	if ! type rustup >/dev/null 2>&1; then \
		curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh; \
		source $$HOME/.cargo/env; \
	fi ; \
	rustup target add x86_64-unknown-linux-musl
	$(MAKE) -C web setup
	curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
	sudo add-apt-repository \
        "deb [arch=amd64] https://download.docker.com/linux/ubuntu $$(lsb_release -cs) stable"
	sudo apt-get update
	sudo apt-get install docker-ce
	sudo bash -c 'usermod -a -G docker $$SUDO_USER'
	$(MAKE) -C locale setup
	$(MAKE) check-setup

linesofcode:
	@wc -l $$(find -type f -name "*.py" -o -name "*.js" -o -name "*.cc" -o -name "*.h" -o -name "*.css" | grep -v openhardwaremonitor | grep -v jquery ) | sort -n

protobuf-files:
ifeq ($(ENTERPRISE),yes)
	$(MAKE) -C non-free/cmc-protocols protobuf-files
endif

format: format-python format-c format-shell format-js format-css format-bazel

format-c:
	packages/livestatus/run --format
	packages/unixcat/run --format
	packages/neb/run --format
ifeq ($(ENTERPRISE),yes)
	packages/cmc/run --format
endif

test-format-c:
	packages/livestatus/run --check-format
	packages/unixcat/run --check-format
	packages/neb/run --check-format
ifeq ($(ENTERPRISE),yes)
	packages/cmc/run --check-format
endif

format-python:
	./scripts/run-pipenv run ruff check --select I --fix
	./.venv/bin/ruff format

format-shell:
	$(MAKE)	-C tests format-shell

what-gerrit-makes:
	$(MAKE)	-C tests what-gerrit-makes

format-js:
	scripts/run-prettier --no-color --ignore-path ./.prettierignore --write "{{enterprise/web,web}/htdocs/js/**/,}*.{js,ts,vue}"

format-css:
	scripts/run-prettier --no-color --ignore-path ./.prettierignore --write "web/htdocs/themes/**/*.scss"

format-bazel:
	scripts/run-buildifier --lint=fix --mode=fix

documentation:
	echo Nothing to do here remove this target

sw-documentation-docker:
	scripts/run-in-docker.sh scripts/run-pipenv run make -C doc/documentation html

.python-$(PYTHON_MAJOR_DOT_MINOR)-stamp:
	$(RM) .python-*-stamp
	touch $@

# TODO: pipenv and make don't really cooperate nicely: Locking alone already
# creates a virtual environment with setuptools/pip/wheel. This could lead to a
# wrong up-to-date status of it later, so let's remove it here. What we really
# want is a check if the contents of .venv match the contents of Pipfile.lock.
# We should do this via some move-if-change Kung Fu, but for now rm suffices.
Pipfile.lock: Pipfile
	@if [ "${CI}" == "true" ]; then \
		echo "A locking of Pipfile.lock is needed, but we're executed in the CI, where this should not be done."; \
		echo "It seems you forgot to commit the new Pipfile.lock. Regenerate Pipfile.lock with e.g.:"; \
		echo "make --what-if Pipfile Pipfile.lock"; \
		exit 1; \
	fi

	@( \
		echo "Locking Python requirements..." ; \
		flock $(LOCK_FD); \
		( SKIP_MAKEFILE_CALL=1 PIP_CONSTRAINT=temporary_pipenv_constraints.txt $(PIPENV) lock --python $(PYTHON_MAJOR_DOT_MINOR) ) || ( $(RM) -r .venv ; exit 1 ) \
	) $(LOCK_FD)>$(LOCK_PATH); \

# Remake .venv everytime Pipfile or Pipfile.lock are updated. Using the 'sync'
# mode installs the dependencies exactly as specified in the Pipfile.lock.
# This is extremely fast since the dependencies do not have to be resolved.
# Cleanup partially created pipenv. This makes us able to automatically repair
# broken virtual environments which may have been caused by network issues.
# SETUPTOOLS_ENABLE_FEATURES="legacy-editable" is needed for mypy being able to
# type check a package that's installed editable:
# https://github.com/python/mypy/issues/13392
.venv: Pipfile.lock .python-$(PYTHON_MAJOR_DOT_MINOR)-stamp
	@( \
	    echo "Creating .venv..." ; \
	    flock $(LOCK_FD); \
	    if [ "$(CI)" == "true" ] || [ "$(PY_VIRT_MAJ_MIN)" != "$(PYTHON_VERSION_MAJOR).$(PYTHON_VERSION_MINOR)" ]; then \
	      echo "INFO: Runs on CI: $(CI), Python version of .venv: $(PY_VIRT_MAJ_MIN), Target python version: $(PYTHON_VERSION_MAJOR).$(PYTHON_VERSION_MINOR)"; \
	      echo "Cleaning up .venv before sync..."; \
	      $(RM) -r .venv; \
	    fi; \
	    ( PIP_CONSTRAINT=temporary_pipenv_constraints.txt SKIP_MAKEFILE_CALL=1 SETUPTOOLS_ENABLE_FEATURES="legacy-editable" VIRTUAL_ENV="" $(PIPENV) sync --python $(PYTHON_MAJOR_DOT_MINOR) --dev && touch .venv ) || ( $(RM) -r .venv ; exit 1 ) \
	) $(LOCK_FD)>$(LOCK_PATH)
