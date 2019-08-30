# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
#

include defines.make

NAME               := check_mk
PREFIX             := /usr
BINDIR             := $(PREFIX)/bin
CONFDIR            := /etc/$(NAME)
LIBDIR             := $(PREFIX)/lib/$(NAME)
DISTNAME           := $(NAME)-$(VERSION)
DIST_ARCHIVE       := check-mk-$(EDITION)-$(OMD_VERSION).tar.gz
TAROPTS            := --owner=root --group=root --exclude=.svn --exclude=*~ \
                      --exclude=.gitignore --exclude=*.swp --exclude=.f12
# We could add clang's -Wshorten-64-to-32 and g++'c/clang's -Wsign-conversion here.
CXX_FLAGS          := -g -O3 -Wall -Wextra
CLANG_VERSION      := 8
CLANG_FORMAT       := clang-format-$(CLANG_VERSION)
SCAN_BUILD         := scan-build-$(CLANG_VERSION)
export CPPCHECK    := cppcheck
export DOXYGEN     := doxygen
export IWYU_TOOL   := iwyu_tool
PIPENV             := PIPENV_NO_INHERIT=true PIPENV_VENV_IN_PROJECT=true pipenv

M4_DEPS            := $(wildcard m4/*) configure.ac
CONFIGURE_DEPS     := $(M4_DEPS) aclocal.m4
CONFIG_DEPS        := ar-lib compile config.guess config.sub install-sh missing depcomp configure
DIST_DEPS          := $(CONFIG_DEPS) \
                      omd/packages/openhardwaremonitor/OpenHardwareMonitorCLI.exe \
                      omd/packages/openhardwaremonitor/OpenHardwareMonitorLib.dll


LIVESTATUS_SOURCES := Makefile.am api/c++/{Makefile,*.{h,cc}} api/perl/* \
                      api/python/{README,*.py} {nagios,nagios4}/{README,*.h} \
                      src/{Makefile.am,*.{cc,h}} standalone/config_files.m4

FILES_TO_FORMAT_WINDOWS := \
                      $(wildcard $(addprefix agents/,*.cc *.c *.h)) \
                      $(wildcard $(addprefix agents/windows/,*.cc *.h)) \
                      $(wildcard $(addprefix agents/windows/sections/,*.cc *.h)) \
                      $(wildcard $(addprefix agents/windows/test/,*.cc *.h)) \
                      $(wildcard $(addprefix agents/windows/test/sections,*.cc *.h)) \

FILES_TO_FORMAT_LINUX := \
                      $(wildcard $(addprefix livestatus/api/c++/,*.cc *.h)) \
                      $(wildcard $(addprefix livestatus/src/,*.cc *.h)) \
                      $(wildcard $(addprefix livestatus/src/test/,*.cc *.h)) \
                      $(wildcard $(addprefix bin/,*.cc *.c *.h)) \
                      $(wildcard $(addprefix enterprise/core/src/,*.cc *.h)) \
                      $(wildcard $(addprefix enterprise/core/src/checkhelper/,*.cc *.h)) \
                      $(wildcard $(addprefix enterprise/core/src/test/,*.cc *.h))

WERKS              := $(wildcard .werks/[0-9]*)

JAVASCRIPT_SOURCES := $(filter-out %_min.js, \
                          $(wildcard \
                              $(foreach edir,. enterprise managed, \
                                  $(foreach subdir,* */* */*/*,$(edir)/web/htdocs/js/$(subdir).js))))

PNG_FILES          := $(wildcard $(addsuffix /*.png,web/htdocs/images web/htdocs/images/icons enterprise/web/htdocs/images enterprise/web/htdocs/images/icons managed/web/htdocs/images managed/web/htdocs/images/icons))

RRDTOOL_VERS       := $(shell egrep -h "RRDTOOL_VERS\s:=\s" omd/packages/rrdtool/rrdtool.make | sed 's/RRDTOOL_VERS\s:=\s//')

THEMES             := classic facelift modern-dark
THEME_CSS_FILES    := $(addprefix web/htdocs/themes/,$(addsuffix /theme.css,$(THEMES)))

.PHONY: all analyze build check check-binaries check-permissions check-version \
        clean compile-neb-cmc cppcheck dist documentation format format-c \
        format-windows format-linux format-python format-shell \
	GTAGS headers help install \
        iwyu mrproper optimize-images packages setup setversion tidy version \
        am--refresh skel

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
dist: $(DISTNAME).tar.gz config.h.in $(DIST_DEPS)
ifeq ($(ENTERPRISE),yes)
	$(MAKE) -C enterprise agents/plugins/cmk-update-agent
	$(MAKE) -C enterprise agents/plugins/cmk-update-agent-32
	$(MAKE) -C enterprise agents/windows/plugins/cmk-update-agent.exe
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
	    for F in $(DIST_ARCHIVE) enterprise/agents/plugins/{build,build-32,src} agents/windows/{build64,build} enterprise/agents/winbuild; do \
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
$(DISTNAME).tar.gz: .venv omd/packages/mk-livestatus/mk-livestatus-$(VERSION).tar.gz .werks/werks web/htdocs/js/main_min.js web/htdocs/js/mobile_min.js web/htdocs/js/side_min.js $(THEME_CSS_FILES) ChangeLog
	@echo "Making $(DISTNAME)"
	rm -rf $(DISTNAME)
	mkdir -p $(DISTNAME)
	$(MAKE) -C agents build
	tar cf $(DISTNAME)/bin.tar $(TAROPTS) -C bin $$(cd bin ; ls)
	tar rf $(DISTNAME)/bin.tar $(TAROPTS) -C agents/windows/msibuild msi-update
	tar rf $(DISTNAME)/bin.tar $(TAROPTS) -C agents/windows/msibuild msi-update-legacy
	gzip $(DISTNAME)/bin.tar
	$(PIPENV) run python -m compileall cmk ; \
	  tar czf $(DISTNAME)/lib.tar.gz $(TAROPTS) \
	    --exclude "cee" \
	    --exclude "cee.py*" \
	    --exclude "cme" \
	    --exclude "cme.py*" \
	    cmk/* ; \
	  rm cmk/*.pyc
	$(PIPENV) run python -m compileall cmk_base ; \
	  tar czf $(DISTNAME)/base.tar.gz \
	    $(TAROPTS) \
	    --exclude "cee" \
	    --exclude "cee.py*" \
	    --exclude "cme" \
	    --exclude "cme.py*" \
	    cmk_base/* ; \
	  rm cmk_base/*.pyc
	tar czf $(DISTNAME)/werks.tar.gz $(TAROPTS) -C .werks werks
	tar czf $(DISTNAME)/checks.tar.gz $(TAROPTS) -C checks $$(cd checks ; ls)
	tar czf $(DISTNAME)/active_checks.tar.gz $(TAROPTS) -C active_checks $$(cd active_checks ; ls)
	tar czf $(DISTNAME)/notifications.tar.gz $(TAROPTS) -C notifications $$(cd notifications ; ls)
	tar czf $(DISTNAME)/inventory.tar.gz $(TAROPTS) -C inventory $$(cd inventory ; ls)
	tar czf $(DISTNAME)/checkman.tar.gz $(TAROPTS) -C checkman $$(cd checkman ; ls)
	tar czf $(DISTNAME)/web.tar.gz $(TAROPTS) -C web htdocs app

	tar xzf omd/packages/mk-livestatus/mk-livestatus-$(VERSION).tar.gz
	tar czf $(DISTNAME)/livestatus.tar.gz $(TAROPTS) -C mk-livestatus-$(VERSION) $$(cd mk-livestatus-$(VERSION) ; ls -A )
	rm -rf mk-livestatus-$(VERSION)

	tar czf $(DISTNAME)/pnp-templates.tar.gz $(TAROPTS) -C pnp-templates $$(cd pnp-templates ; ls *.php)
	tar cf $(DISTNAME)/doc.tar $(TAROPTS) -C doc $$(cd doc ; ls)
	tar rf $(DISTNAME)/doc.tar $(TAROPTS) COPYING AUTHORS ChangeLog
	tar rf $(DISTNAME)/doc.tar $(TAROPTS) livestatus/api --exclude "*~" --exclude "*.pyc" --exclude ".gitignore" --exclude .f12
	gzip $(DISTNAME)/doc.tar

	cd agents ; tar czf ../$(DISTNAME)/agents.tar.gz $(TAROPTS) \
		--exclude check_mk_agent.spec \
		--exclude special/lib \
		cfg_examples \
		plugins \
		sap \
		special \
		z_os \
		check-mk-agent_*.deb \
		check-mk-agent-*.rpm \
		check_mk_agent.* \
		check_mk_caching_agent.linux \
		CONTENTS \
		mk-job* \
		waitmax \
		windows/cfg_examples \
		windows/check_mk_agent*.{exe,msi} \
		windows/check_mk.example.ini \
		windows/check_mk.user.yml \
		windows/CONTENTS \
		windows/mrpe \
		windows/plugins
	cd $(DISTNAME) ; ../scripts/make_package_info $(VERSION) > package_info
	install -m 755 scripts/*.{sh,py} $(DISTNAME)
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

.werks/werks: .venv $(WERKS)
	PYTHONPATH=${PYTHONPATH}:$(REPO_PATH) $(PIPENV) run scripts/precompile-werks.py .werks .werks/werks cre

ChangeLog: .venv .werks/werks
	PYTHONPATH=${PYTHONPATH}:$(REPO_PATH) $(PIPENV) run scripts/create-changelog.py ChangeLog .werks/werks

packages:
	$(MAKE) -C agents packages

# NOTE: Old tar versions (e.g. on CentOS 5) don't have the --transform option,
# so we do things in a slightly complicated way.
omd/packages/mk-livestatus/mk-livestatus-$(VERSION).tar.gz:
	rm -rf mk-livestatus-$(VERSION)
	mkdir -p mk-livestatus-$(VERSION)
	tar cf -  $(TAROPTS) -C livestatus $$(cd livestatus ; echo $(LIVESTATUS_SOURCES) ) | tar xf - -C mk-livestatus-$(VERSION)
	cp -a configure.ac m4 mk-livestatus-$(VERSION)
	cd mk-livestatus-$(VERSION) && autoreconf --install --include=m4 && rm -rf autom4te.cache
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
	sed -i 's/^VERSION=".*/VERSION="$(NEW_VERSION)"/' bin/mkbackup ; \
	sed -i 's/^__version__ = ".*"$$/__version__ = "$(NEW_VERSION)"/' cmk/__init__.py bin/mkbench bin/livedump; \
	sed -i 's/^VERSION=.*/VERSION='"$(NEW_VERSION)"'/' scripts/setup.sh ; \
	$(MAKE) -C agents NEW_VERSION=$(NEW_VERSION) setversion
	$(MAKE) -C docker NEW_VERSION=$(NEW_VERSION) setversion
ifeq ($(ENTERPRISE),yes)
	$(MAKE) -C enterprise NEW_VERSION=$(NEW_VERSION) setversion
endif

headers:
	doc/helpers/headrify

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
node_modules: package.json
	if curl --head 'http://nexus:8081/#browse/browse:npm-proxy' | grep '200\ OK'; then \
            npm config set registry http://nexus:8081/repository/npm-proxy/; \
        fi
	npm install --unsafe-perm

web/htdocs/js/%_min.js: node_modules webpack.config.js $(JAVASCRIPT_SOURCES)
	ENTERPRISE=$(ENTERPRISE) MANAGED=$(MANAGED) node_modules/.bin/webpack --mode=development

web/htdocs/themes/%/theme.css: node_modules webpack.config.js postcss.config.js web/htdocs/themes/%/theme.scss web/htdocs/themes/%/scss/*.scss
	ENTERPRISE=$(ENTERPRISE) MANAGED=$(MANAGED) node_modules/.bin/webpack --mode=development

# TODO(sp) The target below is not correct, we should not e.g. remove any stuff
# which is needed to run configure, this should live in a separate target. In
# fact, we should really clean up all this cleaning-chaos and finally follow the
# GNU standards here (see "Standard Targets for Users",
# https://www.gnu.org/prep/standards/html_node/Standard-Targets.html).
clean:
	make -C omd clean
	rm -rf clang-analyzer dist.tmp rpm.topdir *.rpm *.deb *.exe \
	       omd/packages/mk-livestatus/mk-livestatus-*.tar.gz \
	       $(NAME)-*.tar.gz *~ counters autochecks \
	       precompiled cache web/htdocs/js/*_min.js \
	       web/htdocs/themes/*/theme.css \
	       .werks/werks \
	       ChangeLog

mrproper:
	git clean -d --force -x --exclude='\.werks/.last' --exclude='\.werks/.my_ids'

setup:
	sudo apt-get install \
	    aptitude \
	    autoconf \
	    bear \
	    build-essential \
	    clang-7 \
	    clang-format-7 \
	    clang-tidy-7 \
	    doxygen \
	    figlet \
	    g++ \
	    libboost-dev \
	    libboost-system-dev \
	    libclang-7-dev \
	    libpcap-dev \
	    librrd-dev \
	    llvm-7-dev \
	    libsasl2-dev \
	    libldap2-dev \
	    libkrb5-dev \
	    libmysqlclient-dev \
	    pngcrush \
	    valgrind \
	    direnv \
	    python-pip \
	    chrpath \
	    enchant \
	    ksh \
	    p7zip-full
	sudo -H pip install -U pipenv
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
	  if test -d ../boost/destdir ; then \
	    BOOST_OPT="--with-boost=$(abspath ../boost/destdir)" ; \
	  elif test -d omd/packages/boost/destdir ; then \
	    BOOST_OPT="--with-boost=$(abspath omd/packages/boost/destdir)" ; \
	  else \
	    BOOST_OPT="DUMMY1=" ; \
	  fi ; \
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
	  echo "configure CXXFLAGS=\"$(CXX_FLAGS)\" \"$$BOOST_OPT\" \"$$RRD_OPT\" \"$$RE2_OPT\"" ; \
	  ./configure CXXFLAGS="$(CXX_FLAGS)" "$$BOOST_OPT" "$$RRD_OPT" "$$RE2_OPT" ; \
	fi

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

compile-neb-cmc: config.status
	$(MAKE) -C livestatus -j4
ifeq ($(ENTERPRISE),yes)
	$(MAKE) -C enterprise/core -j4
endif

tidy: config.h
	$(MAKE) -C livestatus/src tidy
ifeq ($(ENTERPRISE),yes)
	$(MAKE) -C enterprise/core/src tidy
endif

iwyu: config.h
	$(MAKE) -C livestatus/src iwyu
ifeq ($(ENTERPRISE),yes)
	$(MAKE) -C enterprise/core/src iwyu
endif

# Not really perfect rules, but better than nothing
analyze: config.h
	$(MAKE) -C livestatus clean
	cd livestatus && $(SCAN_BUILD) -o ../clang-analyzer $(MAKE) CXXFLAGS="-std=c++17"

# GCC-like output on stderr intended for human consumption.
cppcheck: config.h
	$(MAKE) -C livestatus/src cppcheck
ifeq ($(ENTERPRISE),yes)
	$(MAKE) -C enterprise/core/src cppcheck
endif

# XML output into file intended for machine processing.
cppcheck-xml: config.h
	$(MAKE) -C livestatus/src cppcheck-xml
ifeq ($(ENTERPRISE),yes)
	$(MAKE) -C enterprise/core/src cppcheck-xml
endif

format: format-python format-c format-shell

# TODO: We should probably handle this rule via AM_EXTRA_RECURSIVE_TARGETS in
# src/configure.ac, but this needs at least automake-1.13, which in turn is only
# available from e.g. Ubuntu Saucy (13) onwards, so some magic is needed.
format-c: format-windows format-linux

format-windows:
	$(CLANG_FORMAT) -style=file -i $(FILES_TO_FORMAT_WINDOWS)

format-linux:
	$(CLANG_FORMAT) -style=file -i $(FILES_TO_FORMAT_LINUX)

format-python: .venv
# Explicitly specify --style [FILE] to prevent costly searching in parent directories
# for each file specified via command line
#
# Saw some mixed up lines on stdout after adding the --parallel option. Leaving it on
# for the moment to get the performance boost this option brings.
	PYTHON_FILES=$${PYTHON_FILES-$$(tests/find-python-files)} ; \
	$(PIPENV) run yapf --parallel --style .style.yapf --verbose -i $$PYTHON_FILES

format-shell:
	sudo docker run --rm -v "$(realpath .):/sh" -w /sh peterdavehello/shfmt shfmt -w -i 4 -ci $(SHELL_FILES)


# Note: You need the doxygen and graphviz packages.
documentation: config.h
	$(MAKE) -C livestatus/src documentation
ifeq ($(ENTERPRISE),yes)
	$(MAKE) -C enterprise/core/src documentation
endif

Pipfile.lock: Pipfile
	$(PIPENV) lock
# TODO: Can be removed if pipenv fixes this issue.
# See: https://github.com/pypa/pipenv/issues/3140
#      https://github.com/pypa/pipenv/issues/3026
# The recent pipenv version 2018.10.13 has a bug that places wrong markers in the
# Pipfile.lock. This leads to an error when installing packages with this
# markers and prints an error message. Example:
# Ignoring pyopenssl: markers 'extra == "security"' don't match your environment
	sed -i "/\"markers\": \"extra == /d" Pipfile.lock
# TODO: pipenv and make don't really cooperate nicely: Locking alone already
# creates a virtual environment with setuptools/pip/wheel. This could lead to a
# wrong up-to-date status of it later, so let's remove it here. What we really
# want is a check if the contents of .venv match the contents of Pipfile.lock.
# We should do this via some move-if-change Kung Fu, but for now rm suffices.
	rm -rf .venv

.venv: Pipfile.lock
# Remake .venv everytime Pipfile or Pipfile.lock are updated. Using the 'sync'
# mode installs the dependencies exactly as speciefied in the Pipfile.lock.
# This is extremely fast since the dependencies do not have to be resolved.
	$(RM) -r .venv
# Cleanup partially created pipenv. This makes us able to automatically repair
# broken virtual environments which may have been caused by network issues.
	($(PIPENV) sync --dev) || ($(RM) -r .venv ; exit 1)
	touch .venv

# This dummy rule is called from subdirectories whenever one of the
# top-level Makefile's dependencies must be updated.  It does not
# need to depend on %MAKEFILE% because GNU make will always make sure
# %MAKEFILE% is updated before considering the am--refresh target.
am--refresh:
	@:
