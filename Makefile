# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

#
include defines.make
include artifacts.make

TAROPTS            := --owner=root --group=root \
                      --wildcards \
                      --exclude .git --exclude .gitignore --exclude .gitmodules --exclude .gitattributes \
                      --exclude=.svn \
                      --exclude=~* --exclude=*~ --exclude=*.swp \
                      --exclude=.f12 --exclude=OWNERS \
                      --exclude=__pycache__ --exclude=*.pyc
UVENV              := scripts/run-uvenv

# The CI environment variable should only be set by Jenkins
CI ?= false

.PHONY: announcement all build \
        clean dist documentation \
        format \
        help install mrproper mrclean \
        packages setup setversion version openapi \
        requirements.txt .venv

help:
	@echo "setup                          --> Prepare system for development and building"
	@echo "make dist                      --> Create source tgz for later building of rpm/deb and livestatus tgz"
	@echo "make version                   --> Switch to new version"

$(SOURCE_BUILT_LINUX_AGENTS):
	$(MAKE) -C agents $@

ifneq ($(EDITION),community)
$(SOURCE_BUILT_AGENT_UPDATER):
	@echo "ERROR: Should have already been built by artifact providing jobs"
	@echo "If you don't need the artifacts, you can use "
	@echo "'scripts/fake-artifacts' to continue with stub files"
	@exit 1
endif

# Is executed by our build environment from a "git archive" snapshot and during
# RPM building to create the source tar.gz for the RPM build process.
# Would use --exclude-vcs-ignores but that's available from tar 1.29 which
# is currently not used by most distros
# Would also use --exclude-vcs, but this is also not available
# And --transform is also missing ...
dist: $(SOURCE_BUILT_AGENTS) $(SOURCE_BUILT_AGENT_UPDATER)
	if [ -z "$(EDITION)" ]; then \
	    echo "EDITION is not set!" ; exit 1 ; \
	fi ; \
	set -e -o pipefail ; EXCLUDES= ; \
	# COMMIT can be created in bazel via "//omd:hash_file_pkg"
	git rev-parse HEAD > COMMIT ; \
	for X in $$(git ls-files --directory --others -i --exclude-standard) ; do \
		EXCLUDES+=" --exclude $${X%*/}" ; \
	done ; \
	if [ -d check-mk-$(EDITION)-$(VERSION) ]; then \
	    rm -rf check-mk-$(EDITION)-$(VERSION) ; \
	fi ; \
	mkdir check-mk-$(EDITION)-$(VERSION) ; \
	# TODO: as soon as the source tar gz build is in bazel, filename_from_flag will handle this renaming
	# Safety net: ensure we use the correct version - should not be an issue tho because we start from a clean workspace
	rpm -qi agents/check-mk-agent.noarch.rpm | grep $$(echo $(VERSION) | tr '-' '_') || exit 1; \
	dpkg-deb -I agents/check-mk-agent_all.deb | grep $(VERSION) || exit 1; \
	mv agents/check-mk-agent.noarch.rpm agents/check-mk-agent-$(VERSION)-1.noarch.rpm ; \
	mv agents/check-mk-agent_all.deb agents/check-mk-agent_$(VERSION)-1_all.deb ; \
	tar -c \
	    $(TAROPTS) \
	    --exclude check-mk-$(EDITION)-$(VERSION) \
	    --exclude non-free \
	    --exclude tests/qa-test-data \
	    $$EXCLUDES \
	    * .werks | tar x -C check-mk-$(EDITION)-$(VERSION)
	if [ -f COMMIT ]; then \
	    rm COMMIT ; \
	fi
	bazel build //omd:license_info && tar xf "$$(bazel cquery --output=files //omd:license_info)" --strip 2 --touch -C check-mk-$(EDITION)-$(VERSION)/omd/
	tar -cz -f check-mk-$(EDITION)-$(VERSION).tar.gz \
	    $(TAROPTS) \
	    check-mk-$(EDITION)-$(VERSION)
	rm -rf check-mk-$(EDITION)-$(VERSION)

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
	# IMPORTANT do not version bazelized packages here.  Bazel can set the
	# version natively.
	sed -ri 's/^(VERSION[[:space:]]*:?= *).*/\1'"$(NEW_VERSION)/" defines.make
	sed -i 's/^__version__ = ".*"$$/__version__ = "$(NEW_VERSION)"/' packages/cmk-ccc/cmk/ccc/version.py bin/livedump
	$(MAKE) -C agents NEW_VERSION=$(NEW_VERSION) setversion
	sed -i 's/^ARG CMK_VERSION=.*$$/ARG CMK_VERSION="$(NEW_VERSION)"/g' docker_image/Dockerfile
ifneq ($(EDITION),community)
	sed -i 's/^__version__ = ".*/__version__ = "$(NEW_VERSION)"/' non-free/packages/cmk-update-agent/cmk_update_agent.py
endif

# TODO(sp) The target below is not correct, we should not e.g. remove any stuff
# which is needed to run configure, this should live in a separate target. In
# fact, we should really clean up all this cleaning-chaos and finally follow the
# GNU standards here (see "Standard Targets for Users",
# https://www.gnu.org/prep/standards/html_node/Standard-Targets.html).
clean:
	rm -rf *.rpm *.deb *.exe \
	       *~ counters autochecks \
	       precompiled cache announce*

EXCLUDE_PROPER= \
	    --exclude="**/.vscode" \
	    --exclude="**/*.code-workspace" \
	    --exclude="**/.idea" \
	    --exclude=".werks/.last" \
	    --exclude=".werks/.my_ids" \
	    --exclude="user.bazelrc" \
	    --exclude="remote.bazelrc"

EXCLUDE_CLEAN=$(EXCLUDE_PROPER) \
	    --exclude=".venv" \
	    --exclude=".cargo" \
	    --exclude="node_modules" \
	    --exclude=".cache"

# The list of files and folders to be protected from remove after "buildclean" is called
# Rust dirs are kept due to heavy load when compiled: .cargo, controller
HOST_PACKAGES_TARGET_PATH=packages/target
EXCLUDE_BUILD_CLEAN=$(EXCLUDE_CLEAN) \
	    --exclude=".cargo" \
	    --exclude=$(HOST_PACKAGES_TARGET_PATH)

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

format:
	bazel run //:format

what-gerrit-makes:
	$(MAKE)	-C tests what-gerrit-makes

lint-bazel:
	scripts/run-buildifier --lint=fix

documentation:
	echo Nothing to do here remove this target

sw-documentation:
	scripts/run-uvenv make -C doc/documentation html

update_venv:
	echo > requirements.txt
	bazel run //:lock_python_requirements > /dev/null

relock_venv:
	bazel run //:lock_python_requirements > /dev/null

ifeq ($(EDITION),community)
    # Bazel cannot `select()` tests in a `test_suite` and cannot `alias` tests.
    # See discussion under https://github.com/bazelbuild/bazel/issues/11458
    PYTHON_REQUIREMENTS_TEST = //:py_requirements_test_gpl
else
    PYTHON_REQUIREMENTS_TEST = //:py_requirements_test_nonfree
endif

check_python_requirements:
	@set -e; \
	if ! bazel test $(PYTHON_REQUIREMENTS_TEST); then \
		if [ "${CI}" == "true" ]; then \
			echo "A locking of python requirements is needed, but we're executed in the CI, where this should not be done."; \
			echo "It seems you forgot to commit the new lock file. Regenerate with: make relock_venv"; \
			exit 1; \
		fi; \
	fi;

# .venv is PHONY because the dependencies are resolved by bazel
.venv: check_python_requirements
	CC="gcc" bazel run //:create_venv
