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
CLANG_VERSION      := 6.0
CLANG_FORMAT       := clang-format-$(CLANG_VERSION)
CLANG_TIDY         := clang-tidy-$(CLANG_VERSION)
export RUN_CLANG_TIDY := run-clang-tidy-$(CLANG_VERSION).py
SCAN_BUILD         := scan-build-$(CLANG_VERSION)
export CPPCHECK    := cppcheck
export DOXYGEN     := doxygen
export IWYU_TOOL   := iwyu_tool
PIPENV             := PIPENV_NO_INHERIT=true PIPENV_VENV_IN_PROJECT=true pipenv

# The Bear versions have a slightly tragic history: Due to the clang bug
# https://llvm.org/bugs/show_bug.cgi?id=24710 we need absolute paths in our
# compilation database. Furthermore, gcc and clang have slightly different
# behavior regarding include paths when the -I flag contains a relative path and
# symlinks are involved, so this is yet another reason to use absolute paths.
#
# Consequently, we upstreamed a fix for this to the Bear project, see
# https://github.com/rizsotto/Bear/commit/fb1645de9. This fix lived happily in
# the Bear releases 2.1.4, 2.1.5, and 2.2.0, but after that, some "improvements"
# broke the fix again. :-/ Until a new fix has been upstreamed, make sure that
# that you use the right Bear.
#
# To install a working version locally, just do:
#    git clone https://github.com/rizsotto/Bear.git && cd Bear && git checkout 2.2.0 && cmake -DCMAKE_INSTALL_PREFIX=$HOME/local/Bear-2.2.0 && make install
# and put $HOME/local/Bear-2.2.0/bin into your PATH or set the make variable
# below accordingly.
export BEAR        := bear

M4_DEPS            := $(wildcard m4/*) configure.ac
CONFIGURE_DEPS     := $(M4_DEPS) aclocal.m4
DIST_DEPS          := ar-lib compile config.guess config.sub install-sh missing depcomp configure omd/packages/openhardwaremonitor/OpenHardwareMonitorCLI.exe omd/packages/openhardwaremonitor/OpenHardwareMonitorLib.dll


LIVESTATUS_SOURCES := Makefile.am api/c++/{Makefile,*.{h,cc}} api/perl/* \
                      api/python/{README,*.py} {nagios,nagios4}/{README,*.h} \
                      src/{Makefile.am,*.{cc,h}} standalone/config_files.m4

# Files that are checked for trailing spaces
HEAL_SPACES_IN     := checkman/* cmk_base/* checks/* notifications/* inventory/* \
                      $$(find -name Makefile) livestatus/src/*.{cc,h} \
                      web/htdocs/*.{py,css} web/htdocs/js/*.js web/plugins/*/*.py \
                      doc/helpers/* scripts/setup.sh scripts/autodetect.py \
                      $$(find pnp-templates -type f -name "*.php") \
                      bin/mkeventd bin/*.cc active_checks/* \
                      agents/check_mk_*agent* agents/*.c \
                      $$(find agents/cfg_examples -type f) \
                      agents/special/agent_* \
                      agents/special/lib/cmk_special_agents.py \
                      $$(find agents/plugins -type f) \
                      $(wildcard enterprise/cmk_base/cee/*.py \
                                 enterprise/modules/*.py \
                                 enterprise/web/htdocs/*.py \
                                 enterprise/web/plugins/*/*/*.py) \
                      $(wildcard managed/web/htdocs/*.py \
                                 managed/web/plugins/*/*/*.py)

FILES_TO_FORMAT    := $(wildcard $(addprefix agents/,*.cc *.c *.h)) \
                      $(wildcard $(addprefix agents/windows/,*.cc *.h)) \
                      $(wildcard $(addprefix agents/windows/sections/,*.cc *.h)) \
                      $(wildcard $(addprefix agents/windows/test/,*.cc *.h)) \
                      $(wildcard $(addprefix agents/windows/test/sections,*.cc *.h)) \
                      $(wildcard $(addprefix livestatus/api/c++/,*.cc *.h)) \
                      $(wildcard $(addprefix livestatus/src/,*.cc *.h)) \
                      $(wildcard $(addprefix bin/,*.cc *.c *.h)) \
                      $(wildcard $(addprefix enterprise/core/src/,*.cc *.h)) \
                      $(wildcard $(addprefix enterprise/core/src/checkhelper/,*.cc *.h))

WERKS              := $(wildcard .werks/[0-9]*)

JAVASCRIPT_SOURCES := $(filter-out %_min.js,$(wildcard $(addsuffix /web/htdocs/js/*.js,. enterprise managed)))
JAVASCRIPT_MINI    := $(patsubst %.js,%_min.js,$(JAVASCRIPT_SOURCES))

PNG_FILES          := $(wildcard $(addsuffix /*.png,web/htdocs/images web/htdocs/images/icons enterprise/web/htdocs/images enterprise/web/htdocs/images/icons managed/web/htdocs/images managed/web/htdocs/images/icons))


.PHONY: all analyze build check check-binaries check-permissions check-spaces \
        check-version clean compile-neb-cmc cppcheck dist documentation format \
        GTAGS headers healspaces help install iwyu mrproper \
        optimize-images packages setup setversion tidy version \
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

check: check-spaces check-permissions check-binaries check-version

check-spaces:
	@echo -n "Checking for trailing spaces..."
	@if grep -q '[[:space:]]$$' $(HEAL_SPACES_IN) ; then \
          echo FAILED ; \
          figlet "Space error"; \
          echo "Aborting due to trailing spaces. Please use 'make healspaces' to repair."; \
          echo "Affected files: "; \
          grep -l '[[:space:]]$$' $(HEAL_SPACES_IN); \
          exit 1; \
        fi
	@echo OK

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
dist: mk-livestatus-$(VERSION).tar.gz $(DISTNAME).tar.gz config.h.in $(DIST_DEPS)
ifeq ($(ENTERPRISE),yes)
	$(MAKE) -C enterprise agents/plugins/cmk-update-agent
	$(MAKE) -C enterprise agents/plugins/cmk-update-agent-32
	$(MAKE) -C enterprise agents/windows/plugins/cmk-update-agent.exe
endif
	@set -e -o pipefail ; EXCLUDES= ; \
	if [ -d .git ]; then \
	    git rev-parse --short HEAD > COMMIT ; \
	    for X in $$(git ls-files --directory --others -i --exclude-standard) ; do \
	    if [[ $$X != aclocal.m4 && $$X != config.h.in  && ! "$(DIST_DEPS)" =~ (^|[[:space:]])$$X($$|[[:space:]]) && $$X != $(DISTNAME).tar.gz ]]; then \
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
$(DISTNAME).tar.gz: mk-livestatus-$(VERSION).tar.gz .werks/werks $(JAVASCRIPT_MINI) ChangeLog
	@echo "Making $(DISTNAME)"
	rm -rf $(DISTNAME)
	mkdir -p $(DISTNAME)
	$(MAKE) -C agents build
	tar cf $(DISTNAME)/bin.tar $(TAROPTS) -C bin $$(cd bin ; ls)
	tar rf $(DISTNAME)/bin.tar $(TAROPTS) -C agents/windows/msibuild msi-update
	gzip $(DISTNAME)/bin.tar
	python -m compileall cmk ; \
	  tar czf $(DISTNAME)/lib.tar.gz $(TAROPTS) \
	    --exclude "cee" \
	    --exclude "cee.py*" \
	    --exclude "cme" \
	    --exclude "cme.py*" \
	    cmk/* ; \
	  rm cmk/*.pyc
	python -m compileall cmk_base ; \
	  tar czf $(DISTNAME)/base.tar.gz \
	    $(TAROPTS) \
	    --exclude "cee" \
	    --exclude "cee.py*" \
	    --exclude "cme" \
	    --exclude "cme.py*" \
	    cmk_base/* ; \
	  rm cmk_base/*.pyc
	python -m compileall agents/special/lib ; \
	  tar czf $(DISTNAME)/special_agent_api.tar.gz $(TAROPTS) -C agents/special/lib cmk_special_agent_api.py \
	    --exclude ".f12"
	  rm agents/special/lib/*.pyc
	tar czf $(DISTNAME)/werks.tar.gz $(TAROPTS) -C .werks werks
	tar czf $(DISTNAME)/checks.tar.gz $(TAROPTS) -C checks $$(cd checks ; ls)
	tar czf $(DISTNAME)/active_checks.tar.gz $(TAROPTS) -C active_checks $$(cd active_checks ; ls)
	tar czf $(DISTNAME)/notifications.tar.gz $(TAROPTS) -C notifications $$(cd notifications ; ls)
	tar czf $(DISTNAME)/inventory.tar.gz $(TAROPTS) -C inventory $$(cd inventory ; ls)
	tar czf $(DISTNAME)/checkman.tar.gz $(TAROPTS) -C checkman $$(cd checkman ; ls)
	tar czf $(DISTNAME)/web.tar.gz $(TAROPTS) -C web htdocs plugins

	tar xzf mk-livestatus-$(VERSION).tar.gz
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

omd/packages/openhardwaremonitor/OpenHardwareMonitorCLI.exe omd/packages/openhardwaremonitor/OpenHardwareMonitorLib.dll:
	make -C omd/packages/openhardwaremonitor dist

.werks/werks: $(WERKS)
	PYTHONPATH=. python scripts/precompile-werks.py .werks .werks/werks cre

ChangeLog: .werks/werks
	PYTHONPATH=. python scripts/create-changelog.py ChangeLog .werks/werks

packages:
	$(MAKE) -C agents packages

# NOTE: Old tar versions (e.g. on CentOS 5) don't have the --transform option,
# so we do things in a slightly complicated way.
mk-livestatus-$(VERSION).tar.gz:
	rm -rf mk-livestatus-$(VERSION)
	mkdir -p mk-livestatus-$(VERSION)
	tar cf -  $(TAROPTS) -C livestatus $$(cd livestatus ; echo $(LIVESTATUS_SOURCES) ) | tar xf - -C mk-livestatus-$(VERSION)
	cp -a configure.ac m4 mk-livestatus-$(VERSION)
	cd mk-livestatus-$(VERSION) && autoreconf --install --include=m4 && rm -rf autom4te.cache
	tar czf mk-livestatus-$(VERSION).tar.gz $(TAROPTS) mk-livestatus-$(VERSION)
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

healspaces:
	@echo "Removing trailing spaces from code lines..."
	@sed -ri 's/[[:space:]]+$$//g' $(HEAL_SPACES_IN)

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

install-minified-js: $(JAVASCRIPT_MINI)
	cp $? $(DESTDIR)/web/htdocs/js

%_min.js: %.js
	@if type slimit >/dev/null 2>&1; then \
	  cat $< | slimit > $@ ; \
	else \
	    echo "missing slimit: $< not minified, run \"make setup\" to fix this" ; \
	fi

# TODO(sp) The target below is not correct, we should not e.g. remove any stuff
# which is needed to run configure, this should live in a separate target. In
# fact, we should really clean up all this cleaning-chaos and finally follow the
# GNU standards here (see "Standard Targets for Users",
# https://www.gnu.org/prep/standards/html_node/Standard-Targets.html).
clean:
	rm -rf clang-analyzer dist.tmp rpm.topdir *.rpm *.deb *.exe \
	       mk-livestatus-*.tar.gz \
	       $(NAME)-*.tar.gz *~ counters autochecks \
	       precompiled cache web/htdocs/js/*_min.js \
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
	    clang-6.0 \
	    clang-format-6.0 \
	    clang-tidy-6.0 \
	    doxygen \
	    figlet \
	    g++ \
	    libboost-dev \
	    libboost-system-dev \
	    libclang-6.0-dev \
	    libpcap-dev \
	    librrd-dev \
	    llvm-6.0-dev \
	    libsasl2-dev \
	    pngcrush \
	    slimit \
	    valgrind \
	    direnv \
	    python-pip \
	    chrpath \
	    enchant
	sudo pip install pipenv
	$(MAKE) -C omd setup
	$(MAKE) -C omd/packages/openhardwaremonitor setup
ifeq ($(ENTERPRISE),yes)
	$(MAKE) -C enterprise/locale setup
endif

linesofcode:
	@wc -l $$(find -type f -name "*.py" -o -name "*.js" -o -name "*.cc" -o -name "*.h" -o -name "*.css" | grep -v openhardwaremonitor | grep -v jquery | grep -v livestatus/src ) | sort -n

ar-lib compile config.guess config.sub install-sh missing depcomp: configure.ac
	autoreconf --install --include=m4
	touch ar-lib compile config.guess config.sub install-sh missing depcomp

# TODO(sp): We should really detect and use our own packages in a less hacky way...
config.status: $(DIST_DEPS)
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
	  if test -d "omd/packages/rrdtool/rrdtool-1.7.0/src/.libs"; then \
	    RRD_OPT="LDFLAGS=-L$(realpath omd/packages/rrdtool/rrdtool-1.7.0/src/.libs)" ; \
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

# TODO: We should probably handle this rule via AM_EXTRA_RECURSIVE_TARGETS in
# src/configure.ac, but this needs at least automake-1.13, which in turn is only
# available from e.g. Ubuntu Saucy (13) onwards, so some magic is needed.
format:
	$(CLANG_FORMAT) -style=file -i $(FILES_TO_FORMAT)

# Note: You need the doxygen and graphviz packages.
documentation: config.h
	$(MAKE) -C livestatus/src documentation
ifeq ($(ENTERPRISE),yes)
	$(MAKE) -C enterprise/core/src documentation
endif

Pipfile.lock: Pipfile
	$(PIPENV) lock
# TODO: pipenv and make don't really cooperate nicely: Locking alone already
# creates a virtual environment with setuptools/pip/wheel. This could lead to a
# wrong up-to-date status of it later, so let's remove it here. What we really
# want is a check if the contents of .venv match the contents of Pipfile.lock.
# We should do this via some move-if-change Kung Fu, but for now rm suffices.
	rm -rf .venv

.venv: Pipfile.lock
	$(PIPENV) install --dev
	$(PIPENV) clean
# TODO: Part 2 of the hack for the Pipfile.lock target.
	touch .venv

# This dummy rule is called from subdirectories whenever one of the
# top-level Makefile's dependencies must be updated.  It does not
# need to depend on %MAKEFILE% because GNU make will always make sure
# %MAKEFILE% is updated before considering the am--refresh target.
am--refresh:
	@:
