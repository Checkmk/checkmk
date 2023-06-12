# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

#
include defines.make
include artifacts.make

NAME               := check_mk
PREFIX             := /usr
BINDIR             := $(PREFIX)/bin
CONFDIR            := /etc/$(NAME)
LIBDIR             := $(PREFIX)/lib/$(NAME)
DIST_ARCHIVE       := check-mk-$(EDITION)-$(OMD_VERSION).tar.gz
TAROPTS            := --owner=root --group=root --exclude=.svn --exclude=*~ \
                      --exclude=.gitignore --exclude=*.swp --exclude=.f12 \
                      --exclude=__pycache__ --exclude=*.pyc
# We could add clang's -Wshorten-64-to-32 and g++'c/clang's -Wsign-conversion here.
CXX_FLAGS          := -gdwarf-4 -O3 -Wall -Wextra
CLANG_FORMAT       := clang-format-$(CLANG_VERSION)
SCAN_BUILD         := scan-build-$(CLANG_VERSION)
export DOXYGEN     := doxygen
ARTIFACT_STORAGE   := https://artifacts.lan.tribe29.com
# TODO: Prefixing the command with the environment variable breaks xargs usage below!
PIPENV             := PIPENV_PYPI_MIRROR=$(PIPENV_PYPI_MIRROR) scripts/run-pipenv
BLACK              := scripts/run-black

M4_DEPS            := $(wildcard m4/*) configure.ac
CONFIGURE_DEPS     := $(M4_DEPS) aclocal.m4
CONFIG_DEPS        := ar-lib compile config.guess config.sub install-sh missing depcomp configure
DIST_DEPS          := $(CONFIG_DEPS)

LIVESTATUS_SOURCES := Makefile.am standalone/config_files.m4 \
                      api/c++/{Makefile,*.{h,cc}} \
                      api/perl/* \
                      api/python/{README,*.py} \
                      {nagios,nagios4}/{README,*.h} \
                      src/Makefile.am \
                      src/*.cc \
                      src/include/neb/*.h \
                      src/src/*.cc \
                      src/test/*.{cc,h}

FILES_TO_FORMAT_LINUX := \
                      $(filter-out %.pb.cc %.pb.h, \
                      $(wildcard $(addprefix livestatus/api/c++/,*.cc *.h)) \
                      $(wildcard livestatus/src/*.cc) \
                      $(wildcard livestatus/src/include/neb/*.h) \
                      $(wildcard livestatus/src/src/*.cc) \
                      $(wildcard $(addprefix livestatus/src/test/,*.cc *.h)) \
                      $(wildcard $(addprefix bin/,*.cc *.c *.h)) \
                      $(wildcard $(addprefix enterprise/core/src/,*.cc *.h)) \
                      $(wildcard $(addprefix enterprise/core/src/test/,*.cc *.h)))

CMAKE_FORMAT       := cmake-format
CMAKE_TXT_FILES    = $$(find packages -name CMakeLists.txt \! -path '*/build/*')


WERKS              := $(wildcard .werks/[0-9]*)

JAVASCRIPT_SOURCES := $(filter-out %_min.js, \
                          $(wildcard \
                              $(foreach edir,. enterprise managed, \
                                  $(foreach subdir,* */* */*/*,$(edir)/web/htdocs/js/$(subdir).[jt]s))))

SCSS_SOURCES := $(wildcard \
					$(foreach edir,. enterprise managed, \
						$(foreach subdir,* */*,$(edir)/web/htdocs/themes/$(subdir)/*.scss)))


PNG_FILES          := $(wildcard $(addsuffix /*.png,web/htdocs/images web/htdocs/images/icons enterprise/web/htdocs/images enterprise/web/htdocs/images/icons managed/web/htdocs/images managed/web/htdocs/images/icons))

RRDTOOL_VERS       := $(shell egrep -h "RRDTOOL_VERS\s:=\s" omd/packages/rrdtool/rrdtool.make | sed 's/RRDTOOL_VERS\s:=\s//')

WEBPACK_MODE       ?= production

OPENAPI_DOC        := web/htdocs/openapi/api-documentation.html
OPENAPI_SPEC       := web/htdocs/openapi/checkmk.yaml

LOCK_FD := 200
LOCK_PATH := .venv.lock
PY_PATH := .venv/bin/python
ifneq ("$(wildcard $(PY_PATH))","")
  PY_VIRT_MAJ_MIN := $(shell "${PY_PATH}" -c "from sys import version_info as v; print(f'{v.major}.{v.minor}')")
endif

.PHONY: all analyze build check check-binaries check-permissions check-version \
        clean compile-neb-cmc compile-neb-cmc-docker css dist documentation \
        format format-c test-format-c format-python format-shell \
        format-js GTAGS help install iwyu mrproper mrclean optimize-images \
        packages setup setversion tidy version am--refresh skel openapi openapi-doc \
        protobuf-files

help:
	@echo "setup			      --> Prepare system for development and building"
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

check: check-permissions check-binaries check-version

check-permissions:
	@echo -n "Checking permissions... with find -not -perm -444..." && [ -z "$$(find -not -perm -444)" ] && echo OK

check-binaries:
	@if [ -z "$(SKIP_SANITY_CHECKS)" ]; then \
	    echo -n "Checking precompiled binaries..." && file agents/waitmax | grep 32-bit >/dev/null && echo OK ; \
	fi

check-version:
	@sed -n 1p ChangeLog | fgrep -qx '$(VERSION):' || { \
	    echo "Version $(VERSION) not listed at top of ChangeLog!" ; \
	    false ; }

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
$(REPO_PATH)/agents/plugins/cmk-update-agent:
	$(MAKE) -C enterprise agents/plugins/cmk-update-agent

$(REPO_PATH)/agents/plugins/cmk-update-agent-32:
	$(MAKE) -C enterprise agents/plugins/cmk-update-agent-32
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
dist: $(LIVESTATUS_INTERMEDIATE_ARCHIVE) config.h.in $(SOURCE_BUILT_AGENTS) $(SOURCE_BUILT_AGENT_UPDATER) $(DIST_DEPS) protobuf-files $(JAVASCRIPT_MINI) $(THEME_RESOURCES)
	$(MAKE) -C agents/plugins
	set -e -o pipefail ; EXCLUDES= ; \
	if [ -d .git ]; then \
	    git rev-parse --short HEAD > COMMIT ; \
	    for X in $$(git ls-files --directory --others -i --exclude-standard) ; do \
	    if [[ $$X != aclocal.m4 && $$X != config.h.in  && ! "$(DIST_DEPS)" =~ (^|[[:space:]])$$X($$|[[:space:]]) && $$X != omd/packages/mk-livestatus/mk-livestatus-$(VERSION).tar.gz && $$X != livestatus/* && $$X != enterprise/* ]]; then \
		    EXCLUDES+=" --exclude $${X%*/}" ; \
		fi ; \
	    done ; \
	else \
	    for F in $(DIST_ARCHIVE) enterprise/agents/plugins/{build,build-32,src} enterprise/agents/plugins/{build,build-32,src} enterprise/agents/winbuild; do \
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
	    * .werks .clang* | tar x -C check-mk-$(EDITION)-$(OMD_VERSION)
	if [ -f COMMIT ]; then \
	    rm COMMIT ; \
	fi
	tar -cz --wildcards -f $(DIST_ARCHIVE) \
	    $(TAROPTS) \
	    check-mk-$(EDITION)-$(OMD_VERSION)
	rm -rf check-mk-$(EDITION)-$(OMD_VERSION)

$(CHECK_MK_RAW_PRECOMPILED_WERKS): $(WERKS)
	PYTHONPATH=${PYTHONPATH}:$(REPO_PATH) $(PIPENV) run python -m cmk.utils.werks precompile .werks .werks/werks --filter-by-edition cre

$(REPO_PATH)/ChangeLog: $(CHECK_MK_RAW_PRECOMPILED_WERKS)
	PYTHONPATH=${PYTHONPATH}:$(REPO_PATH) $(PIPENV) run python -m cmk.utils.werks changelog ChangeLog .werks/werks


$(CHECK_MK_ANNOUNCE_FOLDER):
	mkdir -p $(CHECK_MK_ANNOUNCE_FOLDER)

$(CHECK_MK_ANNOUNCE_MD): $(CHECK_MK_ANNOUNCE_FOLDER)
	PYTHONPATH=${PYTHONPATH}:$(REPO_PATH) $(PIPENV) run python -m cmk.utils.werks announce .werks $(VERSION) --format=md > $(CHECK_MK_ANNOUNCE_MD)

$(CHECK_MK_ANNOUNCE_TXT): $(CHECK_MK_ANNOUNCE_FOLDER)
	PYTHONPATH=${PYTHONPATH}:$(REPO_PATH) $(PIPENV) run python -m cmk.utils.werks announce .werks $(VERSION) --format=txt > $(CHECK_MK_ANNOUNCE_TXT)

$(CHECK_MK_ANNOUNCE_TAR): $(CHECK_MK_ANNOUNCE_TXT) $(CHECK_MK_ANNOUNCE_MD)
	tar -czf $(CHECK_MK_ANNOUNCE_TAR) -C $(CHECK_MK_ANNOUNCE_FOLDER) .


packages:
	$(MAKE) -C agents packages


# NOTE: Old tar versions (e.g. on CentOS 5) don't have the --transform option,
# so we do things in a slightly complicated way.
$(LIVESTATUS_INTERMEDIATE_ARCHIVE):
	rm -rf mk-livestatus-$(VERSION)
	mkdir -p mk-livestatus-$(VERSION)
	set -o pipefail; tar chf - $(TAROPTS) -C livestatus $$(cd livestatus ; echo $(LIVESTATUS_SOURCES) ) | tar xf - -C mk-livestatus-$(VERSION)
	set -o pipefail; tar chf - $(TAROPTS) --exclude=build packages/livestatus third_party/re2 third_party/asio third_party/googletest third_party/rrdtool | tar xf - -C mk-livestatus-$(VERSION)
	cp -a configure.ac defines.make m4 mk-livestatus-$(VERSION)
	cd mk-livestatus-$(VERSION) && \
	    autoreconf --install --include=m4 && \
	    rm -rf autom4te.cache && \
	    touch ar-lib compile config.guess config.sub install-sh missing depcomp
	tar czf omd/packages/mk-livestatus/mk-livestatus-$(VERSION).tar.gz $(TAROPTS) mk-livestatus-$(VERSION)
	rm -rf mk-livestatus-$(VERSION)

version:
	[ "$$(head -c 6 /etc/issue)" = "Ubuntu" \
          -o "$$(head -c 16 /etc/issue)" = "Debian GNU/Linux" ] \
          || { echo 'You are not on the reference system!' ; exit 1; }
	@newversion=$$(dialog --stdout --inputbox "New Version:" 0 0 "$(VERSION)") ; \
	if [ -n "$$newversion" ] ; then $(MAKE) NEW_VERSION=$$newversion setversion ; fi

setversion:
	sed -ri 's/^(VERSION[[:space:]]*:?= *).*/\1'"$(NEW_VERSION)/" defines.make
	sed -i 's/^AC_INIT.*/AC_INIT([MK Livestatus], ['"$(NEW_VERSION)"'], [mk@mathias-kettner.de])/' configure.ac
	sed -i 's/^__version__ = ".*"$$/__version__ = "$(NEW_VERSION)"/' cmk/utils/version.py bin/livedump
	$(MAKE) -C agents NEW_VERSION=$(NEW_VERSION) setversion
	$(MAKE) -C docker_image NEW_VERSION=$(NEW_VERSION) setversion
ifeq ($(ENTERPRISE),yes)
	$(MAKE) -C enterprise NEW_VERSION=$(NEW_VERSION) setversion
endif

$(OPENAPI_SPEC): $(shell find cmk/gui/plugins/openapi $(wildcard cmk/gui/cee/plugins/openapi) -name "*.py")
	@export PYTHONPATH=${REPO_PATH} ; \
	export TMPFILE=$$(mktemp);  \
	$(PIPENV) run python -m cmk.gui.openapi > $$TMPFILE && \
	mv $$TMPFILE $@


$(OPENAPI_DOC): $(OPENAPI_SPEC) node_modules/.bin/redoc-cli
	node_modules/.bin/redoc-cli bundle -o $(OPENAPI_DOC) $(OPENAPI_SPEC) && \
		sed -i 's/\s\+$$//' $(OPENAPI_DOC) && \
		echo >> $(OPENAPI_DOC)  # fix trailing whitespaces and end of file newline

openapi-clean:
	rm -f $(OPENAPI_SPEC)
openapi: $(OPENAPI_SPEC)
openapi-doc: $(OPENAPI_DOC)


optimize-images:
	@if type pngcrush >/dev/null 2>&1; then \
	    for F in $(PNG_FILES); do \
	        echo "Optimizing $$F..." ; \
	        pngcrush -q -rem alla -brute $$F $$F.opt ; \
	        mv $$F.opt $$F; \
	    done ; \
	else \
	    echo "Missing pngcrush, not optimizing images! (run \"make setup\" to fix this)" ; \
	fi

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
node_modules/.bin/redoc-cli: .ran-npm
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
	touch node_modules/.bin/webpack node_modules/.bin/redoc-cli node_modules/.bin/prettier

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
	WEBPACK_MODE=$(WEBPACK_MODE) ENTERPRISE=$(ENTERPRISE) MANAGED=$(MANAGED) CLOUD=$(CLOUD) SAAS=$(SAAS) node_modules/.bin/webpack --mode=$(WEBPACK_MODE:quick=development)
	touch $(JAVASCRIPT_MINI) $(THEME_CSS_FILES)

# TODO(sp) The target below is not correct, we should not e.g. remove any stuff
# which is needed to run configure, this should live in a separate target. In
# fact, we should really clean up all this cleaning-chaos and finally follow the
# GNU standards here (see "Standard Targets for Users",
# https://www.gnu.org/prep/standards/html_node/Standard-Targets.html).
clean:
	$(MAKE) -C omd clean
	rm -rf clang-analyzer dist.tmp rpm.topdir *.rpm *.deb *.exe \
	       omd/packages/mk-livestatus/mk-livestatus-*.tar.gz \
	       $(NAME)-*.tar.gz *~ counters autochecks \
	       precompiled cache web/htdocs/js/*_min.js \
	       web/htdocs/themes/*/theme.css \
	       .werks/werks \
	       ChangeLog

css: .ran-webpack

EXCLUDE_PROPER= \
	    --exclude="**/.vscode" \
	    --exclude="**/.idea" \
	    --exclude=".werks/.last" \
	    --exclude=".werks/.my_ids"

EXCLUDE_CLEAN=$(EXCLUDE_PROPER) \
	    --exclude=".venv" \
	    --exclude=".venv.lock" \
	    --exclude="node_modules"

AGENT_CTL_TARGET_PATH=packages/cmk-agent-ctl/target
EXCLUDE_BUILD_CLEAN=$(EXCLUDE_CLEAN) \
	    --exclude="doc/plugin-api/build" \
	    --exclude=".cargo" \
	    --exclude=$(AGENT_CTL_TARGET_PATH) \
	    --exclude="agents/plugins/*_2.py" \
	    --exclude="agents/plugins/*.py.checksum"

mrproper:
	git clean -d --force -x $(EXCLUDE_PROPER)

mrclean:
	git clean -d --force -x $(EXCLUDE_CLEAN)

# Used by gerrit jobs to cleanup workspaces *after* a gerrit job run.
# This should not clean up everything - just things which are *not* needed for the next job to run as fast as
# possible.
workspaceclean:
	# Cargo related things
	$(RM) -r $(AGENT_CTL_TARGET_PATH)/debug/ # This was the old target before "x86_64-unknown" and is deprecated now
	$(RM) $(AGENT_CTL_TARGET_PATH)/x86_64-unknown-linux-musl/debug/deps/cmk_agent_ctl-* # Compiling this *should* be fast anyway

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
	    gdebi \
	    git \
	    git-svn \
	    gitk \
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
	    pngcrush \
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
	$(MAKE) -C docker_image setup
	$(MAKE) -C locale setup
	$(MAKE) check-setup

linesofcode:
	@wc -l $$(find -type f -name "*.py" -o -name "*.js" -o -name "*.cc" -o -name "*.h" -o -name "*.css" | grep -v openhardwaremonitor | grep -v jquery | grep -v livestatus/src ) | sort -n

ar-lib compile config.guess config.sub install-sh missing depcomp: configure.ac
	autoreconf --install --include=m4
	touch ar-lib compile config.guess config.sub install-sh missing depcomp

# TODO(sp): We should really detect and use our own packages in a less hacky way...
config.status: $(CONFIG_DEPS)
	@echo "Build $@ (newer targets: $?)"
	@if test -f config.status; then \
	  echo "update config.status by reconfiguring in the same conditions" ; \
	  ./config.status --recheck; \
	else \
	  if test -d "omd/rrdtool-$(RRDTOOL_VERS)/src/.libs"; then \
	    RRD_OPT="LDFLAGS=-L$(realpath omd/rrdtool-$(RRDTOOL_VERS)/src/.libs)" ; \
	  else \
	    RRD_OPT="DUMMY2=" ; \
	  fi ; \
	  echo "configure CXXFLAGS=\"$(CXX_FLAGS)\" \"$$RRD_OPT\"" ; \
	  ./configure CXXFLAGS="$(CXX_FLAGS)" "$$RRD_OPT" ; \
	fi

protobuf-files:
ifeq ($(ENTERPRISE),yes)
	$(MAKE) -C enterprise protobuf-files
endif

configure: $(CONFIGURE_DEPS)
	autoconf

aclocal.m4: $(M4_DEPS)
	aclocal

config.h.in: $(CONFIGURE_DEPS)
	autoheader
	rm -f stamp-h1
	touch $@

config.h: stamp-h1
	@test -f $@ || rm -f stamp-h1
	@test -f $@ || $(MAKE) stamp-h1

stamp-h1: config.h.in config.status
	@rm -f stamp-h1
	./config.status config.h

GTAGS: config.h
# automake generates "gtags -i ...", but incremental updates seem to be a bit
# fragile, so let's start from scratch, gtags is quite fast.
	$(RM) GTAGS GRTAGS GSYMS GPATH
# Note: Even if we descend into livestatus, gtags is run on the top level (next
# to configure.ac).
	$(MAKE) -C livestatus GTAGS

compile-neb-cmc: config.status test-format-c
	$(MAKE) -C livestatus -j4
ifeq ($(ENTERPRISE),yes)
	$(MAKE) -C enterprise/core -j4
endif

compile-neb-cmc-docker:
	scripts/run-in-docker.sh make compile-neb-cmc

tidy: config.h
	$(MAKE) -C livestatus/src tidy
ifeq ($(ENTERPRISE),yes)
	$(MAKE) -C enterprise/core/src tidy
endif

iwyu: config.status
	$(MAKE) -C livestatus/src iwyu
ifeq ($(ENTERPRISE),yes)
	$(MAKE) -C enterprise/core/src iwyu
endif

# Not really perfect rules, but better than nothing
analyze: config.h
	$(MAKE) -C livestatus clean
	cd livestatus && $(SCAN_BUILD) -o ../clang-analyzer $(MAKE) CXXFLAGS="-std=c++17"

format: format-python format-c format-shell format-js format-css format-bazel

# TODO: We should probably handle this rule via AM_EXTRA_RECURSIVE_TARGETS in
# src/configure.ac, but this needs at least automake-1.13, which in turn is only
# available from e.g. Ubuntu Saucy (13) onwards, so some magic is needed.
clang-format-with = $(CLANG_FORMAT) -style=file $(1) $$(find $(FILES_TO_FORMAT_LINUX) -type f)

format-c:
	$(call clang-format-with,-i)
	packages/livestatus/run --format

test-format-c:
	@$(call clang-format-with,-Werror --dry-run)
	@packages/livestatus/run --check-format

format-python: format-python-isort format-python-black

format-python-isort:
	if test -z "$$PYTHON_FILES"; then ./scripts/find-python-files; else echo "$$PYTHON_FILES"; fi | \
	PIPENV_PYPI_MIRROR=$(PIPENV_PYPI_MIRROR)/simple xargs -n 1500 scripts/run-pipenv run isort --settings-path pyproject.toml

format-python-black:
	if test -z "$$PYTHON_FILES"; then ./scripts/find-python-files; else echo "$$PYTHON_FILES"; fi | \
	xargs -n 1500 $(BLACK)

format-shell:
	$(MAKE)	-C tests format-shell

what-gerrit-makes:
	$(MAKE)	-C tests what-gerrit-makes

format-js:
	scripts/run-prettier --no-color --ignore-path ./.prettierignore --write "{{enterprise/web,web}/htdocs/js/**/,}*.{j,t}s"

format-css:
	scripts/run-prettier --no-color --ignore-path ./.prettierignore --write "web/htdocs/themes/**/*.scss"

format-bazel:
	scripts/run-buildifier --lint=fix --mode=fix

# Note: You need the doxygen and graphviz packages.
documentation: config.h
	$(MAKE) -C livestatus/src documentation
ifeq ($(ENTERPRISE),yes)
	$(MAKE) -C enterprise/core/src documentation
endif

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
		( SKIP_MAKEFILE_CALL=1 $(PIPENV) lock --python $(PYTHON_MAJOR_DOT_MINOR) ) || ( $(RM) -r .venv ; exit 1 ) \
	) $(LOCK_FD)>$(LOCK_PATH); \

# Remake .venv everytime Pipfile or Pipfile.lock are updated. Using the 'sync'
# mode installs the dependencies exactly as specified in the Pipfile.lock.
# This is extremely fast since the dependencies do not have to be resolved.
# Cleanup partially created pipenv. This makes us able to automatically repair
# broken virtual environments which may have been caused by network issues.
.venv: Pipfile.lock .python-$(PYTHON_MAJOR_DOT_MINOR)-stamp
	@( \
	    echo "Creating .venv..." ; \
	    flock $(LOCK_FD); \
	    if [ "$(CI)" == "true" ] || [ "$(PY_VIRT_MAJ_MIN)" != "$(PYTHON_VERSION_MAJOR).$(PYTHON_VERSION_MINOR)" ]; then \
	      echo "CI is $(CI), Python version of .venv is $(PY_VIRT_MAJ_MIN), Target python version is $(PYTHON_VERSION_MAJOR).$(PYTHON_VERSION_MINOR)"; \
	      echo "Cleaning up .venv before sync..."; \
	      $(RM) -r .venv; \
	    fi; \
	    ( SKIP_MAKEFILE_CALL=1 VIRTUAL_ENV="" $(PIPENV) sync --python $(PYTHON_MAJOR_DOT_MINOR) --dev && touch .venv ) || ( $(RM) -r .venv ; exit 1 ) \
	) $(LOCK_FD)>$(LOCK_PATH)

# This dummy rule is called from subdirectories whenever one of the
# top-level Makefile's dependencies must be updated.  It does not
# need to depend on %MAKEFILE% because GNU make will always make sure
# %MAKEFILE% is updated before considering the am--refresh target.
am--refresh: config.status
	./config.status
