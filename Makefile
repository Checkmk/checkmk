# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

#
include defines.make
include buildscripts/infrastructure/pypi_mirror/pypi_mirror.make

NAME               := check_mk
PREFIX             := /usr
BINDIR             := $(PREFIX)/bin
CONFDIR            := /etc/$(NAME)
LIBDIR             := $(PREFIX)/lib/$(NAME)
DISTNAME           := $(NAME)-$(VERSION)
DIST_ARCHIVE       := check-mk-$(EDITION)-$(OMD_VERSION).tar.gz
TAROPTS            := --owner=root --group=root --exclude=.svn --exclude=*~ \
                      --exclude=.gitignore --exclude=*.swp --exclude=.f12 \
                      --exclude=__pycache__ --exclude=*.pyc
# We could add clang's -Wshorten-64-to-32 and g++'c/clang's -Wsign-conversion here.
CXX_FLAGS          := -g -O3 -Wall -Wextra
CLANG_FORMAT       := clang-format-$(CLANG_VERSION)
SCAN_BUILD         := scan-build-$(CLANG_VERSION)
export DOXYGEN     := doxygen
export IWYU_TOOL   := python3 $(realpath scripts/iwyu_tool.py)
ARTIFACT_STORAGE   := https://artifacts.lan.tribe29.com
# TODO: Prefixing the command with the environment variable breaks xargs usage below!
PIPENV             := PIPENV_PYPI_MIRROR=$(PIPENV_PYPI_MIRROR)/simple scripts/run-pipenv
BLACK              := scripts/run-black

M4_DEPS            := $(wildcard m4/*) configure.ac
CONFIGURE_DEPS     := $(M4_DEPS) aclocal.m4
CONFIG_DEPS        := ar-lib compile config.guess config.sub install-sh missing depcomp configure
DIST_DEPS          := $(CONFIG_DEPS) \
                      omd/packages/openhardwaremonitor/OpenHardwareMonitorCLI.exe \
                      omd/packages/openhardwaremonitor/OpenHardwareMonitorLib.dll

LIVESTATUS_SOURCES := Makefile.am api/c++/{Makefile,*.{h,cc}} api/perl/* \
                      api/python/{README,*.py} {nagios,nagios4}/{README,*.h} \
                      src/{Makefile.am,{,test/}*.{cc,h}} standalone/config_files.m4

FILES_TO_FORMAT_LINUX := \
                      $(filter-out %.pb.cc %.pb.h, \
                      $(wildcard $(addprefix livestatus/api/c++/,*.cc *.h)) \
                      $(wildcard $(addprefix livestatus/src/,*.cc *.h)) \
                      $(wildcard $(addprefix livestatus/src/test/,*.cc *.h)) \
                      $(wildcard $(addprefix bin/,*.cc *.c *.h)) \
                      $(wildcard $(addprefix enterprise/core/src/,*.cc *.h)) \
                      $(wildcard $(addprefix enterprise/core/src/test/,*.cc *.h)))

WERKS              := $(wildcard .werks/[0-9]*)

JAVASCRIPT_SOURCES := $(filter-out %_min.js, \
                          $(wildcard \
                              $(foreach edir,. enterprise managed, \
                                  $(foreach subdir,* */* */*/*,$(edir)/web/htdocs/js/$(subdir).js))))

SCSS_SOURCES := $(wildcard \
					$(foreach edir,. enterprise managed, \
						$(foreach subdir,* */*,$(edir)/web/htdocs/themes/$(subdir)/*.scss)))

JAVASCRIPT_MINI    := $(foreach jmini,main mobile side,web/htdocs/js/$(jmini)_min.js)

PNG_FILES          := $(wildcard $(addsuffix /*.png,web/htdocs/images web/htdocs/images/icons enterprise/web/htdocs/images enterprise/web/htdocs/images/icons managed/web/htdocs/images managed/web/htdocs/images/icons))

RRDTOOL_VERS       := $(shell egrep -h "RRDTOOL_VERS\s:=\s" omd/packages/rrdtool/rrdtool.make | sed 's/RRDTOOL_VERS\s:=\s//')

WEBPACK_MODE       ?= production
THEMES             := facelift modern-dark
THEME_CSS_FILES    := $(addprefix web/htdocs/themes/,$(addsuffix /theme.css,$(THEMES)))
THEME_JSON_FILES   := $(addprefix web/htdocs/themes/,$(addsuffix /theme.json,$(THEMES)))
THEME_IMAGE_DIRS   := $(addprefix web/htdocs/themes/,$(addsuffix /images,$(THEMES)))
THEME_RESOURCES    := $(THEME_CSS_FILES) $(THEME_JSON_FILES) $(THEME_IMAGE_DIRS)

OPENAPI_DOC        := web/htdocs/openapi/api-documentation.html
OPENAPI_SPEC       := web/htdocs/openapi/checkmk.yaml

LOCK_FD := 200
LOCK_PATH := .venv.lock

.PHONY: all analyze build check check-binaries check-permissions check-version \
        clean compile-neb-cmc compile-neb-cmc-docker dist documentation \
        documentation-quick format format-c test-format-c format-python format-shell \
        format-js GTAGS headers help install iwyu mrproper mrclean optimize-images \
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

# Is executed by our build environment from a "git archive" snapshot and during
# RPM building to create the source tar.gz for the RPM build process.
# Would use --exclude-vcs-ignores but that's available from tar 1.29 which
# is currently not used by most distros
# Would also use --exclude-vcs, but this is also not available
# And --transform is also missing ...
dist: $(DISTNAME).tar.gz config.h.in $(DIST_DEPS) protobuf-files
ifeq ($(ENTERPRISE),yes)
	$(MAKE) -C enterprise agents/plugins/cmk-update-agent
	$(MAKE) -C enterprise agents/plugins/cmk-update-agent-32
endif
	set -e -o pipefail ; EXCLUDES= ; \
	if [ -d .git ]; then \
	    git rev-parse --short HEAD > COMMIT ; \
	    for X in $$(git ls-files --directory --others -i --exclude-standard) ; do \
	    if [[ $$X != aclocal.m4 && $$X != config.h.in  && ! "$(DIST_DEPS)" =~ (^|[[:space:]])$$X($$|[[:space:]]) && $$X != $(DISTNAME).tar.gz && $$X != omd/packages/mk-livestatus/mk-livestatus-$(VERSION).tar.gz && $$X != livestatus/* && $$X != enterprise/* ]]; then \
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

# This tar file is only used by "omd/packages/check_mk/Makefile"
$(DISTNAME).tar.gz: omd/packages/mk-livestatus/mk-livestatus-$(VERSION).tar.gz .werks/werks $(JAVASCRIPT_MINI) $(THEME_RESOURCES) ChangeLog
	@echo "Making $(DISTNAME)"
	rm -rf $(DISTNAME)
	mkdir -p $(DISTNAME)
	$(MAKE) -C agents build
	$(MAKE) -C doc/plugin-api html
	tar cf $(DISTNAME)/bin.tar $(TAROPTS) -C bin $$(cd bin ; ls)
	gzip $(DISTNAME)/bin.tar
	tar czf $(DISTNAME)/lib.tar.gz $(TAROPTS) \
	    --exclude "cee" \
	    --exclude "cee.py*" \
	    --exclude "cme" \
	    --exclude "cme.py*" \
	    --exclude "cpe" \
	    --exclude "cpe.py*" \
	    cmk/*
	tar czf $(DISTNAME)/werks.tar.gz $(TAROPTS) -C .werks werks
	tar czf $(DISTNAME)/checks.tar.gz $(TAROPTS) -C checks $$(cd checks ; ls)
	tar czf $(DISTNAME)/active_checks.tar.gz $(TAROPTS) -C active_checks $$(cd active_checks ; ls)
	tar czf $(DISTNAME)/notifications.tar.gz $(TAROPTS) -C notifications $$(cd notifications ; ls)
	tar czf $(DISTNAME)/inventory.tar.gz $(TAROPTS) -C inventory $$(cd inventory ; ls)
	tar czf $(DISTNAME)/checkman.tar.gz $(TAROPTS) -C checkman $$(cd checkman ; ls)
	tar czf $(DISTNAME)/web.tar.gz $(TAROPTS) -C web \
      app \
      htdocs/openapi \
      htdocs/css \
      htdocs/images \
      htdocs/jquery \
      $(patsubst web/%,%,$(JAVASCRIPT_MINI)) \
      $(patsubst web/%,%.map,$(JAVASCRIPT_MINI)) \
      htdocs/sounds \
      $(patsubst web/%,%,$(THEME_RESOURCES))

	tar xzf omd/packages/mk-livestatus/mk-livestatus-$(VERSION).tar.gz
	tar czf $(DISTNAME)/livestatus.tar.gz $(TAROPTS) -C mk-livestatus-$(VERSION) $$(cd mk-livestatus-$(VERSION) ; ls -A )
	rm -rf mk-livestatus-$(VERSION)

	tar cf $(DISTNAME)/doc.tar $(TAROPTS) -C doc --exclude plugin-api $$(cd doc ; ls)
	tar rf $(DISTNAME)/doc.tar $(TAROPTS) \
	    -C doc \
	    --transform "s/^plugin-api\/build/plugin-api/" \
	    plugin-api/build/html
	tar rf $(DISTNAME)/doc.tar $(TAROPTS) COPYING AUTHORS ChangeLog
	tar rf $(DISTNAME)/doc.tar $(TAROPTS) livestatus/api --exclude "*~" --exclude "*.pyc" --exclude ".gitignore" --exclude .f12
	gzip $(DISTNAME)/doc.tar

	make -C agents/plugins
	cd agents ; tar czf ../$(DISTNAME)/agents.tar.gz $(TAROPTS) \
		--exclude check_mk_agent.spec \
		--exclude special/lib \
		--exclude plugins/Makefile \
		--exclude plugins/*.checksum \
		cfg_examples \
		plugins \
		sap \
		scripts \
		special \
		z_os \
		check-mk-agent_*.deb \
		check-mk-agent-*.rpm \
		check_mk_agent.* \
		check_mk_caching_agent.linux \
		CONTENTS \
		mk-job* \
		waitmax \
		linux \
		windows/cfg_examples \
		windows/check_mk_agent.msi \
		windows/check_mk_agent_unsigned.msi \
		windows/python-3.cab \
		windows/python-3.4.cab \
		windows/check_mk.user.yml \
		windows/CONTENTS \
		windows/mrpe \
		windows/plugins
	install -m 644 COPYING AUTHORS ChangeLog standalone.make $(DISTNAME)
	echo "$(VERSION)" > $(DISTNAME)/VERSION
	tar czf $(DISTNAME).tar.gz $(TAROPTS) $(DISTNAME)
	rm -rf $(DISTNAME)

	@echo "=============================================================================="
	@echo "   FINISHED. "
	@echo "=============================================================================="

omd/packages/openhardwaremonitor/OpenHardwareMonitorCLI.exe:
	$(MAKE) -C omd openhardwaremonitor-dist

omd/packages/openhardwaremonitor/OpenHardwareMonitorLib.dll: omd/packages/openhardwaremonitor/OpenHardwareMonitorCLI.exe

ntop-mkp:
	PYTHONPATH=${PYTHONPATH}:$(REPO_PATH) $(PIPENV) run scripts/create-ntop-mkp.py

.werks/werks: $(WERKS)
	PYTHONPATH=${PYTHONPATH}:$(REPO_PATH) $(PIPENV) run scripts/precompile-werks.py .werks .werks/werks cre

ChangeLog: .werks/werks
	PYTHONPATH=${PYTHONPATH}:$(REPO_PATH) $(PIPENV) run scripts/create-changelog.py ChangeLog .werks/werks

packages:
	$(MAKE) -C agents packages

# NOTE: Old tar versions (e.g. on CentOS 5) don't have the --transform option,
# so we do things in a slightly complicated way.
omd/packages/mk-livestatus/mk-livestatus-$(VERSION).tar.gz:
	rm -rf mk-livestatus-$(VERSION)
	mkdir -p mk-livestatus-$(VERSION)
	tar cf -  $(TAROPTS) -C livestatus $$(cd livestatus ; echo $(LIVESTATUS_SOURCES) ) | tar xf - -C mk-livestatus-$(VERSION)
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
	$(MAKE) -C omd NEW_VERSION=$(NEW_VERSION) setversion
	sed -ri 's/^(VERSION[[:space:]]*:?= *).*/\1'"$(NEW_VERSION)/" defines.make ; \
	sed -i 's/^AC_INIT.*/AC_INIT([MK Livestatus], ['"$(NEW_VERSION)"'], [mk@mathias-kettner.de])/' configure.ac ; \
	sed -i 's/^VERSION = ".*/VERSION = "$(NEW_VERSION)"/' bin/mkbackup ; \
	sed -i 's/^__version__ = ".*"$$/__version__ = "$(NEW_VERSION)"/' cmk/utils/version.py bin/mkbench bin/livedump; \
	$(MAKE) -C agents NEW_VERSION=$(NEW_VERSION) setversion
	$(MAKE) -C docker NEW_VERSION=$(NEW_VERSION) setversion
ifeq ($(ENTERPRISE),yes)
	$(MAKE) -C enterprise NEW_VERSION=$(NEW_VERSION) setversion
endif

headers:
	doc/helpers/headrify


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
	npm install --yes --audit=false --unsafe-perm $$REGISTRY
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
web/htdocs/js/main_min.js: .ran-webpack
web/htdocs/js/side_min.js: .ran-webpack
web/htdocs/js/mobile_min.js: .ran-webpack
web/htdocs/themes/facelift/theme.css: .ran-webpack
web/htdocs/themes/modern-dark/theme.css: .ran-webpack
web/htdocs/themes/facelift/cma_facelift.css: .ran-webpack
.ran-webpack: node_modules/.bin/webpack webpack.config.js postcss.config.js $(JAVASCRIPT_SOURCES) $(SCSS_SOURCES)
	WEBPACK_MODE=$(WEBPACK_MODE) ENTERPRISE=$(ENTERPRISE) MANAGED=$(MANAGED) PLUS=$(PLUS) node_modules/.bin/webpack --mode=$(WEBPACK_MODE:quick=development)
	touch web/htdocs/js/*_min.js web/htdocs/themes/*/theme.css

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

EXCLUDE_PROPER= \
	    --exclude="**/.vscode" \
	    --exclude="**/.idea" \
	    --exclude=".werks/.last" \
	    --exclude=".werks/.my_ids"

EXCLUDE_CLEAN=$(EXCLUDE_PROPER) \
	    --exclude=".venv" \
	    --exclude=".venv.lock" \
	    --exclude="node_modules" \
	    --exclude="livestatus/src/doc/plantuml.jar" \
	    --exclude="enterprise/core/src/doc/plantuml.jar"

EXCLUDE_BUILD_CLEAN=$(EXCLUDE_CLEAN) \
	    --exclude="omd/packages/openhardwaremonitor/OpenHardwareMonitorCLI.exe" \
	    --exclude="omd/packages/openhardwaremonitor/OpenHardwareMonitorLib.dll" \
	    --exclude="doc/plugin-api/build" \
	    --exclude=".cargo" \
	    --exclude="agents/cmk-agent-ctl/target" \
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
	    libtool-bin \
	    libxml2-dev \
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
	curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
	source $$HOME/.cargo/env
	rustup target add x86_64-unknown-linux-musl
	$(MAKE) -C web setup
	$(MAKE) -C omd setup
	$(MAKE) -C omd openhardwaremonitor-setup
	$(MAKE) -C docker setup
	$(MAKE) -C locale setup

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
	  if test -d ../re2/destdir ; then \
	    RE2_OPT="--with-re2=$(abspath ../re2/destdir)" ; \
	  elif test -d omd/packages/re2/destdir ; then \
	    RE2_OPT="--with-re2=$(abspath omd/packages/re2/destdir)" ; \
	  else \
	    RE2_OPT="DUMMY3=" ; \
	  fi ; \
	  echo "configure CXXFLAGS=\"$(CXX_FLAGS)\" \"$$RRD_OPT\" \"$$RE2_OPT\"" ; \
	  ./configure CXXFLAGS="$(CXX_FLAGS)" "$$RRD_OPT" "$$RE2_OPT" ; \
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

format: format-python format-c format-shell format-js format-css

# TODO: We should probably handle this rule via AM_EXTRA_RECURSIVE_TARGETS in
# src/configure.ac, but this needs at least automake-1.13, which in turn is only
# available from e.g. Ubuntu Saucy (13) onwards, so some magic is needed.
clang-format-with = $(CLANG_FORMAT) -style=file $(1) $(FILES_TO_FORMAT_LINUX)

format-c:
	$(call clang-format-with,-i)

test-format-c:
	@$(call clang-format-with,-Werror --dry-run)

format-python: format-python-isort format-python-black

format-python-yapf:
# Explicitly specify --style [FILE] to prevent costly searching in parent directories
# for each file specified via command line
#
# Saw some mixed up lines on stdout after adding the --parallel option. Leaving it on
# for the moment to get the performance boost this option brings.
	if test -z "$$PYTHON_FILES"; then ./scripts/find-python-files; else echo "$$PYTHON_FILES"; fi | \
	PIPENV_PYPI_MIRROR=$(PIPENV_PYPI_MIRROR)/simple xargs -n 1500 scripts/run-pipenv run yapf --parallel --style .style.yapf --verbose -i

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
	scripts/run-prettier --no-color --ignore-path ./.prettierignore --write "{enterprise/,}web/htdocs/js/**/*.js"

format-css:
	scripts/run-prettier --no-color --ignore-path ./.prettierignore --write "web/htdocs/themes/**/*.scss"

# Note: You need the doxygen and graphviz packages.
documentation: config.h
	$(MAKE) -C livestatus/src documentation
ifeq ($(ENTERPRISE),yes)
	$(MAKE) -C enterprise/core/src documentation
endif

documentation-quick: config.h
	$(MAKE) -C livestatus/src documentation-quick
ifeq ($(ENTERPRISE),yes)
	$(MAKE) -C enterprise/core/src documentation-quick
endif

sw-documentation-docker:
	scripts/run-in-docker.sh scripts/run-pipenv run make -C doc/documentation html

# TODO: pipenv and make don't really cooperate nicely: Locking alone already
# creates a virtual environment with setuptools/pip/wheel. This could lead to a
# wrong up-to-date status of it later, so let's remove it here. What we really
# want is a check if the contents of .venv match the contents of Pipfile.lock.
# We should do this via some move-if-change Kung Fu, but for now rm suffices.
Pipfile.lock: Pipfile
	@( \
	    echo "Locking Python requirements..." ; \
	    flock $(LOCK_FD); \
	    SKIP_MAKEFILE_CALL=1 $(PIPENV) lock; RC=$$? ; \
	    rm -rf .venv ; \
	    exit $$RC \
	) $(LOCK_FD)>$(LOCK_PATH)

# Remake .venv everytime Pipfile or Pipfile.lock are updated. Using the 'sync'
# mode installs the dependencies exactly as specified in the Pipfile.lock.
# This is extremely fast since the dependencies do not have to be resolved.
# Cleanup partially created pipenv. This makes us able to automatically repair
# broken virtual environments which may have been caused by network issues.
.venv: Pipfile.lock
	@( \
	    echo "Creating .venv..." ; \
	    flock $(LOCK_FD); \
	    $(RM) -r .venv; \
	    ( PIPENV_COLORBLIND=1 SKIP_MAKEFILE_CALL=1 VIRTUAL_ENV="" $(PIPENV) sync --dev && touch .venv ) || ( $(RM) -r .venv ; exit 1 ) \
	) $(LOCK_FD)>$(LOCK_PATH)

# This dummy rule is called from subdirectories whenever one of the
# top-level Makefile's dependencies must be updated.  It does not
# need to depend on %MAKEFILE% because GNU make will always make sure
# %MAKEFILE% is updated before considering the am--refresh target.
am--refresh: config.status
	./config.status
