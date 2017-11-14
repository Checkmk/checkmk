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

EDITION            := raw
EDITION_SHORT      := cre

ifneq (,$(wildcard enterprise))
ENTERPRISE         := yes
EDITION            := enterprise
EDITION_SHORT      := cee
else
ENTERPRISE         := no
endif

ifneq (,$(wildcard managed))
MANAGED            := yes
EDITION            := managed
EDITION_SHORT      := cme
else
MANAGED            := no
endif

VERSION            := 1.5.0i1
DEMO_SUFFIX        :=
OMD_VERSION        := $(VERSION).$(EDITION_SHORT)$(DEMO_SUFFIX)

SHELL              := /bin/bash
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

# HACK: Starting with GCC 6.1, g++ defaults to C++14, but even clang++-4.0 still
# defaults to C++11. So when configure finds such a g++ first, the resulting
# compilation database does not contain a -std=c++14 flag, because it's simply
# not needed. But when we want to use our clang-based tools, it *is* needed. :-/
# To work around that issue, we hackily add that flag below. This is ugly and
# should be removed when the compiler defaults are in sync again.
CXX_FLAGS          += -std=c++14

CLANG_VERSION      := 4.0
CLANG_FORMAT       := clang-format-$(CLANG_VERSION)
CLANG_TIDY         := clang-tidy-$(CLANG_VERSION)
SCAN_BUILD         := scan-build-$(CLANG_VERSION)
CPPCHECK           := cppcheck
DOXYGEN            := doxygen
IWYU_TOOL          := tests/iwyu_tool_jenkins.py

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
BEAR               := bear

M4_DEPS            := $(wildcard m4/*) configure.ac
CONFIGURE_DEPS     := $(M4_DEPS) aclocal.m4
DIST_DEPS          := ar-lib compile config.guess config.sub install-sh missing depcomp configure


LIVESTATUS_SOURCES := Makefile.am api/c++/{Makefile,*.{h,cc}} api/perl/* \
                      api/python/{README,*.py} {nagios,nagios4}/{README,*.h} \
                      src/{Makefile.am,*.{cc,h}} standalone/config_files.m4

# Files that are checked for trailing spaces
HEAL_SPACES_IN     := checkman/* cmk_base/* checks/* notifications/* inventory/* \
                      $$(find -name Makefile) livestatus/src/*.{cc,h} \
                      agents/windows/*.cc \
                      web/htdocs/*.{py,css} web/htdocs/js/*.js web/plugins/*/*.py \
                      doc/helpers/* scripts/setup.sh scripts/autodetect.py \
                      $$(find pnp-templates -type f -name "*.php") \
                      bin/mkeventd bin/*.cc active_checks/* \
                      check_mk_templates.cfg \
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
                      $(wildcard $(addprefix agents/windows/,*.cc *.c *.h)) \
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
	$(MAKE) -C enterprise agents/windows/plugins/cmk-update-agent.exe
endif
	@EXCLUDES= ; \
	if [ -d .git ]; then \
	    git rev-parse --short HEAD > COMMIT ; \
	    for X in $$(git ls-files --directory --others -i --exclude-standard) ; do \
	    if [[ $$X != aclocal.m4 && $$X != config.h.in  && ! "$(DIST_DEPS)" =~ (^|[[:space:]])$$X($$|[[:space:]]) && $$X != $(DISTNAME).tar.gz ]]; then \
		    EXCLUDES+=" --exclude $${X%*/}" ; \
		fi ; \
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
	    --exclude $(DIST_ARCHIVE) \
	    --exclude enterprise/agents/plugins/{build,src} \
	    $$EXCLUDES \
	    * .werks .clang* | tar x -C check-mk-$(EDITION)-$(OMD_VERSION) ; \
	if [ -f COMMIT ]; then \
	    rm COMMIT ; \
	fi ; \
	tar -cz --wildcards -f $(DIST_ARCHIVE) \
	    $(TAROPTS) \
	    check-mk-$(EDITION)-$(OMD_VERSION) ; \
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
	python -m compileall lib ; \
	  tar czf $(DISTNAME)/lib.tar.gz $(TAROPTS) \
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
	tar czf $(DISTNAME)/share.tar.gz $(TAROPTS) check_mk_templates.cfg
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
	sed -ri 's/^(VERSION[[:space:]]*:?= *).*/\1'"$(NEW_VERSION)/" Makefile ; \
	sed -i 's/^AC_INIT.*/AC_INIT([MK Livestatus], ['"$(NEW_VERSION)"'], [mk@mathias-kettner.de])/' configure.ac ; \
	sed -i 's/^VERSION=".*/VERSION="$(NEW_VERSION)"/' bin/mkbackup ; \
	sed -i 's/^__version__ = ".*"$$/__version__ = "$(NEW_VERSION)"/' lib/__init__.py bin/mkbench bin/livedump; \
	sed -i 's/^VERSION=.*/VERSION='"$(NEW_VERSION)"'/' scripts/setup.sh ; \
	$(MAKE) -C agents NEW_VERSION=$(NEW_VERSION) setversion
	$(MAKE) -C omd NEW_VERSION=$(NEW_VERSION) setversion
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
	    done ; 
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
	rm -rf api clang-analyzer compile_commands.json dist.tmp rpm.topdir *.rpm *.deb *.exe \
	       mk-livestatus-*.tar.gz \
	       $(NAME)-*.tar.gz *~ counters autochecks \
	       precompiled cache web/htdocs/js/*_min.js \
	       .werks/werks \
	       ChangeLog

mrproper:
	git clean -d --force -x \
            --exclude='\.bugs/.last' \
            --exclude='\.bugs/.my_ids' \
            --exclude='\.werks/.last' \
            --exclude='\.werks/.my_ids'

setup:
	sudo apt-get install \
	    autoconf \
	    bear \
	    build-essential \
	    figlet \
	    libboost-dev \
	    libboost-system-dev \
	    libpcap-dev \
	    librrd-dev \
	    pngcrush \
	    slimit
	$(MAKE) -C tests setup
	$(MAKE) -C omd setup

linesofcode:
	@wc -l $$(find -type f -name "*.py" -o -name "*.js" -o -name "*.cc" -o -name "*.h" -o -name "*.css" | grep -v openhardwaremonitor | grep -v jquery | grep -v livestatus/src ) | sort -n

ar-lib compile config.guess config.sub install-sh missing depcomp: configure.ac
	autoreconf --install --include=m4
	touch ar-lib compile config.guess config.sub install-sh missing depcomp

config.status: $(DIST_DEPS)
	@echo "Build $@ (newer targets: $?)"
	@if test -f config.status; then \
	  echo "update config.status by reconfiguring in the same conditions" ; \
	  ./config.status --recheck; \
	else \
	  if test -d ../boost/local ; then \
	    BOOST_OPT="--with-boost=$(abspath ../boost/local)" ; \
	  elif test -d omd/packages/boost/local ; then \
	    BOOST_OPT="--with-boost=$(abspath omd/packages/boost/local)" ; \
	  elif test ! -d /usr/include/boost -a -d /usr/include/boost141/boost ; then \
	    BOOST_OPT="CPPFLAGS=-I/usr/include/boost141" ; \
	  else \
	    BOOST_OPT="DUMMY1=" ; \
	  fi ; \
	  if test -d "omd/packages/rrdtool/rrdtool-1.7.0/src/.libs"; then \
	    RRD_OPT="LDFLAGS=-L$(realpath omd/packages/rrdtool/rrdtool-1.7.0/src/.libs)" ; \
	  else \
	    RRD_OPT="DUMMY2=" ; \
	  fi ; \
	  echo "configure CXXFLAGS=\"$(CXX_FLAGS)\" \"$$BOOST_OPT\" \"$$RRD_OPT\"" ; \
	  ./configure CXXFLAGS="$(CXX_FLAGS)" "$$BOOST_OPT" "$$RRD_OPT" ; \
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

compile_commands.json: config.h $(FILES_TO_FORMAT)
	$(MAKE) -C livestatus clean
	$(BEAR) $(MAKE) -C livestatus -j4
ifeq ($(ENTERPRISE),yes)
	$(MAKE) -C enterprise/core clean
	$(BEAR) --append $(MAKE) -C enterprise/core -j4
endif

compile-neb-cmc: config.status
	$(MAKE) -C livestatus -j4
ifeq ($(ENTERPRISE),yes)
	$(MAKE) -C enterprise/core -j4
endif

tidy: compile_commands.json
	@scripts/compiled_sources | xargs $(CLANG_TIDY) --extra-arg=-D__clang_analyzer__

# Not really perfect rules, but better than nothing
iwyu: compile_commands.json
	@$(IWYU_TOOL) --output-format=clang -p . -- --mapping_file=$(realpath tests/check_mk.imp)

# Not really perfect rules, but better than nothing
analyze: config.h
	$(MAKE) -C livestatus clean
	cd livestatus && $(SCAN_BUILD) -o ../clang-analyzer $(MAKE) CXXFLAGS="-std=c++14"

# TODO: Repeating the include paths in the cppcheck targets below is ugly and
# fragile.

# GCC-like output on stderr intended for human consumption.
cppcheck: compile_commands.json
	@scripts/compiled_sources | \
	grep /livestatus/src/ |\
	sed 's/^"\(.*\)"$$/\1/' | \
	( cd livestatus && $(CPPCHECK) -DHAVE_CONFIG_H -UCMC --enable=all --suppress=missingIncludeSystem --suppress=unusedFunction --suppress=passedByValue --inline-suppr -I src -I .. -I . --file-list=- --quiet --template=gcc )
ifeq ($(ENTERPRISE),yes)
	@scripts/compiled_sources | \
	grep /enterprise/core/ |\
	sed 's/^"\(.*\)"$$/\1/' | \
	( cd enterprise/core/src && $(CPPCHECK) -DHAVE_CONFIG_H -DCMC --enable=all --suppress=missingIncludeSystem --suppress=unusedFunction --suppress=passedByValue --inline-suppr -I . -I ../../.. -I livestatus -I checkhelper --file-list=- --quiet --template=gcc )
endif

# XML output into file intended for machine processing.
cppcheck-xml: compile_commands.json
	scripts/compiled_sources | \
	grep /livestatus/src/ |\
	sed 's/^"\(.*\)"$$/\1/' | \
	( cd livestatus && $(CPPCHECK) -DHAVE_CONFIG_H -UCMC --enable=all --suppress=missingIncludeSystem --suppress=unusedFunction --suppress=passedByValue --inline-suppr -I src -I .. -I . --file-list=- --quiet --template=gcc --xml --xml-version=2 2> cppcheck-result.xml )
ifeq ($(ENTERPRISE),yes)
	scripts/compiled_sources | \
	grep /enterprise/core/ |\
	sed 's/^"\(.*\)"$$/\1/' | \
	( cd enterprise/core/src && $(CPPCHECK) -DHAVE_CONFIG_H -DCMC --enable=all --suppress=missingIncludeSystem --suppress=unusedFunction --suppress=passedByValue --inline-suppr -I . -I ../../.. -I livestatus -I checkhelper --file-list=- --quiet --template=gcc --xml --xml-version=2 2> cppcheck-result.xml )
endif

# TODO: We should probably handle this rule via AM_EXTRA_RECURSIVE_TARGETS in
# src/configure.ac, but this needs at least automake-1.13, which in turn is only
# available from e.g. Ubuntu Saucy (13) onwards, so some magic is needed.
format:
	$(CLANG_FORMAT) -style=file -i $(FILES_TO_FORMAT)

# Note: You need the doxygen and graphviz packages.
documentation: config.h
	$(DOXYGEN) doc/Doxyfile
ifeq ($(ENTERPRISE),yes)
	cd enterprise && $(DOXYGEN) doc/Doxyfile
endif

# This dummy rule is called from subdirectories whenever one of the
# top-level Makefile's dependencies must be updated.  It does not
# need to depend on %MAKEFILE% because GNU make will always make sure
# %MAKEFILE% is updated before considering the am--refresh target.
am--refresh: 
	@:
