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
UVENV              := scripts/run-uvenv

PY_PATH := .venv/bin/python
ifneq ("$(wildcard $(PY_PATH))","")
  PY_VIRT_MAJ_MIN := $(shell "${PY_PATH}" -c "from sys import version_info as v; print(f'{v.major}.{v.minor}')")
else
  PY_VIRT_MAJ_MIN := "unknown"
endif

# The CI environment variable should only be set by Jenkins
CI ?= false

.PHONY: announcement all build \
        clean dist documentation \
        format format-c test-format-c format-python format-shell \
        help install mrproper mrclean \
        packages setup setversion version openapi \
        requirements_all_lock.txt protobuf-files frontend-vue .venv

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
dist: $(SOURCE_BUILT_AGENTS) $(SOURCE_BUILT_AGENT_UPDATER) protobuf-files cmk-frontend frontend-vue
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

cmk-frontend:
	packages/cmk-frontend/run --clean --all

frontend-vue:
	packages/cmk-frontend-vue/run --clean --all

announcement:
	mkdir -p $(CHECK_MK_ANNOUNCE_FOLDER)
	PYTHONPATH=${PYTHONPATH}:$(REPO_PATH) $(UVENV) python -m cmk.utils.werks announce .werks $(VERSION) --format=md > $(CHECK_MK_ANNOUNCE_MD)
	PYTHONPATH=${PYTHONPATH}:$(REPO_PATH) $(UVENV) python -m cmk.utils.werks announce .werks $(VERSION) --format=txt > $(CHECK_MK_ANNOUNCE_TXT)
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
	sed -i 's/^__version__ = ".*"$$/__version__ = "$(NEW_VERSION)"/' packages/cmk-ccc/cmk/ccc/version.py bin/livedump
	$(MAKE) -C agents NEW_VERSION=$(NEW_VERSION) setversion
	sed -i 's/^ARG CMK_VERSION=.*$$/ARG CMK_VERSION="$(NEW_VERSION)"/g' docker_image/Dockerfile
ifeq ($(ENTERPRISE),yes)
	sed -i 's/^__version__ = ".*/__version__ = "$(NEW_VERSION)"/' non-free/cmk-update-agent/cmk_update_agent.py
	sed -i 's/^VERSION = ".*/VERSION = "$(NEW_VERSION)"/' omd/packages/enterprise/bin/cmcdump
endif

# TODO(sp) The target below is not correct, we should not e.g. remove any stuff
# which is needed to run configure, this should live in a separate target. In
# fact, we should really clean up all this cleaning-chaos and finally follow the
# GNU standards here (see "Standard Targets for Users",
# https://www.gnu.org/prep/standards/html_node/Standard-Targets.html).
clean:
	$(MAKE) -C omd clean
	rm -rf *.rpm *.deb *.exe \
	       *~ counters autochecks \
	       precompiled cache announce*

EXCLUDE_PROPER= \
	    --exclude="**/.vscode" \
	    --exclude="**/*.code-workspace" \
	    --exclude="**/.idea" \
	    --exclude=".werks/.last" \
	    --exclude=".werks/.my_ids" \
	    --exclude="user.bazelrc"

EXCLUDE_CLEAN=$(EXCLUDE_PROPER) \
	    --exclude=".venv" \
	    --exclude=".cargo" \
	    --exclude="node_modules" \
	    --exclude=".cache"

# The list of files and folders to be protected from remove after "buildclean" is called
# Rust dirs are kept due to heavy load when compiled: .cargo, controller
HOST_PACKAGES_TARGET_PATH=packages/host/target
EXCLUDE_BUILD_CLEAN=$(EXCLUDE_CLEAN) \
	    --exclude="doc/plugin-api/build" \
	    --exclude=".cargo" \
	    --exclude=$(HOST_PACKAGES_TARGET_PATH) \
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
	sudo buildscripts/infrastructure/build-nodes/scripts/install-development.sh --profile all
	sudo bash -c 'usermod -a -G docker $$SUDO_USER'

linesofcode:
	@wc -l $$(find -type f -name "*.py" -o -name "*.js" -o -name "*.cc" -o -name "*.h" -o -name "*.css" | grep -v openhardwaremonitor | grep -v jquery ) | sort -n

protobuf-files:
ifeq ($(ENTERPRISE),yes)
	$(MAKE) -C non-free/packages/cmc-protocols protobuf-files
endif

format: format-python format-c format-shell format-bazel

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
	./scripts/run-uvenv ruff check --select I --fix
	./.venv/bin/ruff format


format-shell:
	$(MAKE)	-C tests format-shell

what-gerrit-makes:
	$(MAKE)	-C tests what-gerrit-makes

format-bazel:
	scripts/run-buildifier --mode=fix

lint-bazel:
	scripts/run-buildifier --lint=fix

documentation:
	echo Nothing to do here remove this target

sw-documentation-docker:
	scripts/run-in-docker.sh scripts/run-uvenv make -C doc/documentation html

# Use this target to update the requirements_*_lock.txt files
# TODO: Find a _way_ better ways to handle this
relock_venv:
	for type in runtime all; do \
	    filename=requirements_$${type}_lock.txt; \
	    > $${filename}; \
	done; \
	bazel mod deps --lockfile_mode=update; \
	bazel run //:requirements_runtime.update; bazel mod deps --lockfile_mode=update; \
	bazel run //:requirements_all.update; bazel mod deps --lockfile_mode=update; \

# .venv is PHONY because the dependencies are resolved by bazel
.venv:
	@set -e; \
	if ! bazel test //:requirements_test > /dev/null; then \
		if [ "${CI}" == "true" ]; then \
			echo "A locking of python requirements is needed, but we're executed in the CI, where this should not be done."; \
			echo "It seems you forgot to commit the new lock file. Regenerate with e.g.:"; \
			echo "bazel run //:requirements.update"; \
			exit 1; \
		fi; \
		# TODO: We currently need to first have an updated runtime lock file as this is the input for the all_lock file. \
		# Therefore execution order matters! \
		bazel run //:requirements_runtime.update; bazel mod deps --lockfile_mode=update; \
		bazel run //:requirements_all.update; bazel mod deps --lockfile_mode=update; \
	fi; \
	CC="gcc" $(REPO_PATH)/scripts/run-bazel.sh run //:create_venv
