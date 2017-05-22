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

ifneq (,$(wildcard enterprise))
ENTERPRISE         := yes
else
ENTERPRISE         := no
endif

ifneq (,$(wildcard managed))
MANAGED            := yes
else
MANAGED            := no
endif

SHELL              := /bin/bash
VERSION            := 1.4.0b9
NAME               := check_mk
PREFIX             := /usr
BINDIR             := $(PREFIX)/bin
CONFDIR            := /etc/$(NAME)
LIBDIR             := $(PREFIX)/lib/$(NAME)
DISTNAME           := $(NAME)-$(VERSION)
TAROPTS            := --owner=root --group=root --exclude=.svn --exclude=*~ \
                      --exclude=.gitignore --exclude=*.swp --exclude=.f12
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

LIVESTATUS_SOURCES := Makefile.am api/c++/{Makefile,*.{h,cc}} api/perl/* \
                      api/python/{README,*.py} {nagios,nagios4}/{README,*.h} \
                      src/{Makefile.am,*.{cc,h}} standalone/config_files.m4

# Files that are checked for trailing spaces
HEAL_SPACES_IN     := checkman/* modules/* checks/* notifications/* inventory/* \
                      $$(find -name Makefile) livestatus/src/*.{cc,h} \
                      agents/windows/*.cc \
                      web/htdocs/*.{py,css} web/htdocs/js/*.js web/plugins/*/*.py \
                      doc/helpers/* scripts/setup.sh scripts/autodetect.py \
                      $$(find pnp-templates -type f -name "*.php") \
                      bin/mkeventd bin/*.cc active_checks/* \
                      check_mk_templates.cfg \
                      agents/check_mk_*agent* agents/*.c \
                      $$(find agents/cfg_examples -type f) \
                      agents/special/* \
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
        check-version clean cppcheck dist documentation format \
        GTAGS headers healspaces help install iwyu mrproper \
        optimize-images packages setup setversion tidy version \
	am--refresh

all: dist packages

help:
	@echo "make                           --> dist, rpm and deb"
	@echo "make dist                      --> create TGZ package"
	@echo "make packages                  --> create packages of agents"
	@echo "make DESTDIR=/tmp/hirn install --> install directly"
	@echo "make version                   --> switch to new version"
	@echo "make headers                   --> create/update fileheades"
	@echo "make healspaces                --> remove trailing spaces in code"
	@echo "setup			      --> prepare system for development"

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

dist: $(DISTNAME).tar.gz

$(DISTNAME).tar.gz: mk-livestatus-$(VERSION).tar.gz .werks/werks $(JAVASCRIPT_MINI) ChangeLog packages
	@echo "Making $(DISTNAME)"
	rm -rf $(DISTNAME)
	mkdir -p $(DISTNAME)
	tar czf $(DISTNAME)/bin.tar.gz $(TAROPTS) -C bin $$(cd bin ; ls)
	pycompile lib ; \
	  tar czf $(DISTNAME)/lib.tar.gz $(TAROPTS) -C lib \
	    --transform 's|^|cmk/|g' $$(cd lib ; ls) ; \
	  rm lib/*.pyc
	pycompile cmk_base ; \
	  tar czf $(DISTNAME)/base.tar.gz $(TAROPTS) cmk_base/*.py* ; \
	  rm cmk_base/*.pyc
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
	tar czf $(DISTNAME)/modules.tar.gz $(TAROPTS) -C modules $$(cd modules ; ls *.py)

	tar  czf $(DISTNAME)/agents.tar.gz $(TAROPTS) -C agents \
		--exclude "msibuild" \
		--exclude "build_version" \
		--exclude "*.rc" \
		--exclude "*.rc.in" \
		--exclude "bin_replace" \
		--exclude "*.nsi" \
		--exclude "*.ico" \
		--exclude "endless.bat" \
		--exclude "logstate.txt" \
		--exclude "*.unversioned.exe" \
		--exclude "*.res" \
		--exclude "*~" \
		--exclude "*.c" \
		--exclude "Makefile" \
		--exclude "windows/README" \
		--exclude "windows/crash.exe" \
		--exclude "windows/*.cc" \
		--exclude "windows/*.h" \
		--exclude "windows/openhardwaremonitor" \
		--exclude "windows/sections" \
		--exclude "windows/frozen_binaries" \
		--exclude .f12 $$(cd agents ; ls)
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

ifeq ($(ENTERPRISE),yes)

enterprise/werks: $(WERKS)
	PYTHONPATH=. python scripts/precompile-werks.py .werks enterprise/werks cee

enterprise/ChangeLog: enterprise/werks
	PYTHONPATH=. python scripts/create-changelog.py enterprise/ChangeLog enterprise/werks

dist: cmc-$(VERSION).tar.gz

# We currently fake a package for cmc. Ugly...
cmc-$(VERSION).tar.gz: config.h enterprise/werks enterprise/ChangeLog
	$(MAKE) -C livestatus distclean
	$(MAKE) -C enterprise/core distclean
	rm -rf cmc-$(VERSION)
	mkdir cmc-$(VERSION)
	tar cf - $(TAROPTS) \
          aclocal.m4 \
          ar-lib \
          compile \
          config.guess \
          config.h.in \
          config.sub \
          configure \
          depcomp \
          install-sh \
          missing \
          stamp-h1 \
          .bugs \
          Makefile \
          configure.ac \
          enterprise \
          livestatus \
          m4 | tar xf - -C cmc-$(VERSION)
	mv cmc-$(VERSION)/enterprise/skel{,.permissions} cmc-$(VERSION)
	mv cmc-$(VERSION)/enterprise/LIVEPROXYD.hook cmc-$(VERSION)
	cp enterprise/werks cmc-$(VERSION)/werks
	cp enterprise/ChangeLog cmc-$(VERSION)/ChangeLog-cmc
	sed -i '1 i\include ../../Makefile.omd' cmc-$(VERSION)/Makefile
	cd cmc-$(VERSION) \
	    && tar czf ../cmc-$(VERSION).tar.gz $(TAROPTS) .bugs *
	rm -rf cmc-$(VERSION)

build: config.h
	LANG=C $(MAKE) -C livestatus -j3
	LANG=C $(MAKE) -C enterprise/core -j3
	$(MAKE) -C enterprise/locale all

install:
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/check_mk/web
	cp -rv enterprise/web/* $(DESTDIR)$(OMD_ROOT)/share/check_mk/web
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/check_mk/modules
	install -m 644 enterprise/modules/* $(DESTDIR)$(OMD_ROOT)/share/check_mk/modules
	mkdir -p $(DESTDIR)$(OMD_ROOT)/lib/python/cmk_base/cee
	install -m 644 enterprise/cmk_base/cee/* $(DESTDIR)$(OMD_ROOT)/lib/python/cmk_base/cee
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/check_mk/alert_handlers
	install -m 755 enterprise/alert_handlers/* $(DESTDIR)$(OMD_ROOT)/share/check_mk/alert_handlers
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/check_mk/agents/bakery
	install -m 644 enterprise/agents/bakery/* $(DESTDIR)$(OMD_ROOT)/share/check_mk/agents/bakery
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/check_mk/agents/plugins
	install -m 755 enterprise/agents/mk-remote-alert-handler $(DESTDIR)$(OMD_ROOT)/share/check_mk/agents
	install -m 755 enterprise/agents/plugins/* $(DESTDIR)$(OMD_ROOT)/share/check_mk/agents/plugins
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/check_mk/agents/windows/plugins
	install -m 755 enterprise/agents/windows/plugins/*.exe $(DESTDIR)$(OMD_ROOT)/share/check_mk/agents/windows/plugins
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/check_mk/reporting/images
	install -m 644 enterprise/reporting/images/* $(DESTDIR)$(OMD_ROOT)/share/check_mk/reporting/images
	mkdir -p $(DESTDIR)$(OMD_ROOT)/bin
	install -m 755 enterprise/core/src/cmc $(DESTDIR)$(OMD_ROOT)/bin
	install -m 755 enterprise/bin/* $(DESTDIR)$(OMD_ROOT)/bin
	mkdir -p $(DESTDIR)$(OMD_ROOT)/lib/cmc
	install -m 755 enterprise/core/src/checkhelper/checkhelper $(DESTDIR)$(OMD_ROOT)/lib/cmc
	install -m 755 enterprise/core/src/checkhelper/icmpsender $(DESTDIR)$(OMD_ROOT)/lib/cmc
	install -m 755 enterprise/core/src/checkhelper/icmpreceiver $(DESTDIR)$(OMD_ROOT)/lib/cmc
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/check_mk/locale/de/LC_MESSAGES
	install -m 644 enterprise/locale/de/LC_MESSAGES/multisite.mo $(DESTDIR)$(OMD_ROOT)/share/check_mk/locale/de/LC_MESSAGES
	install -m 644 enterprise/locale/de/alias $(DESTDIR)$(OMD_ROOT)/share/check_mk/locale/de
	mkdir -p $(DESTDIR)$(OMD_ROOT)/lib/nagios/plugins
	install -m 755 enterprise/active_checks/check_lql_service $(DESTDIR)$(OMD_ROOT)/lib/nagios/plugins
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/doc/check_mk_enterprise
	install -m 644 enterprise/EULA-* $(DESTDIR)$(OMD_ROOT)/share/doc/check_mk_enterprise
	install -m 644 ChangeLog-cmc $(DESTDIR)$(OMD_ROOT)/share/doc/check_mk_enterprise/ChangeLog
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/diskspace
	install -m 644 enterprise/diskspace $(DESTDIR)$(OMD_ROOT)/share/diskspace/check_mk_enterprise
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/check_mk/werks
	install -m 644 werks $(DESTDIR)$(OMD_ROOT)/share/check_mk/werks/werks-cmc
endif

ifeq ($(MANAGED),yes)
managed/werks: $(WERKS)
	PYTHONPATH=. python scripts/precompile-werks.py .werks managed/werks cme

managed/ChangeLog: managed/werks
	PYTHONPATH=. python scripts/create-changelog.py managed/ChangeLog managed/werks

dist: cme-$(VERSION).tar.gz

cme-$(VERSION).tar.gz: managed/werks managed/ChangeLog
	rm -rf cme-$(VERSION)
	mkdir cme-$(VERSION)
	cp -pr managed cme-$(VERSION)/managed
	mv cme-$(VERSION)/managed/ChangeLog cme-$(VERSION)/ChangeLog-cme
	mv cme-$(VERSION)/managed/Makefile.omd cme-$(VERSION)/Makefile
	cd cme-$(VERSION) \
	    && tar czf ../cme-$(VERSION).tar.gz $(TAROPTS) *
	rm -rf cme-$(VERSION)

endif

packages:
	$(MAKE) -C agents packages

version:
	[ "$$(head -c 12 /etc/issue)" = "Ubuntu 10.10" \
          -o "$$(head -c 12 /etc/issue)" = "Ubuntu 11.04" \
          -o "$$(head -c 12 /etc/issue)" = "Ubuntu 11.10" \
          -o "$$(head -c 12 /etc/issue)" = "Ubuntu 12.04" \
          -o "$$(head -c 12 /etc/issue)" = "Ubuntu 12.10" \
          -o "$$(head -c 12 /etc/issue)" = "Ubuntu 13.04" \
          -o "$$(head -c 12 /etc/issue)" = "Ubuntu 13.10" \
          -o "$$(head -c 12 /etc/issue)" = "Ubuntu 14.04" \
          -o "$$(head -c 12 /etc/issue)" = "Ubuntu 15.04" \
          -o "$$(head -c 12 /etc/issue)" = "Ubuntu 15.10" \
          -o "$$(head -c 12 /etc/issue)" = "Ubuntu 16.04" \
          -o "$$(head -c 20 /etc/issue)" = "Debian GNU/Linux 6.0" \
          -o "$$(head -c 18 /etc/issue)" = "Debian GNU/Linux 7" ] \
          || { echo 'You are not on the reference system!' ; exit 1; }
	@newversion=$$(dialog --stdout --inputbox "New Version:" 0 0 "$(VERSION)") ; \
	if [ -n "$$newversion" ] ; then $(MAKE) NEW_VERSION=$$newversion setversion ; fi

setversion:
	sed -ri 's/^(VERSION[[:space:]]*:?= *).*/\1'"$(NEW_VERSION)/" Makefile ; \
	sed -i 's/^AC_INIT.*/AC_INIT([MK Livestatus], ['"$(NEW_VERSION)"'], [mk@mathias-kettner.de])/' configure.ac ; \
	sed -i 's/^VERSION=".*/VERSION="$(NEW_VERSION)"/' bin/mkeventd bin/mkbackup ; \
	sed -i 's/^__version__ = ".*"$$/__version__ = "$(NEW_VERSION)"/' lib/__init__.py bin/mkbench ; \
	sed -i 's/^VERSION=.*/VERSION='"$(NEW_VERSION)"'/' scripts/setup.sh ; \
	echo 'check-mk_$(NEW_VERSION)-1_all.deb net optional' > debian/files
	$(MAKE) -C agents NEW_VERSION=$(NEW_VERSION) setversion
ifeq ($(ENTERPRISE),yes)
	sed -i 's/^VERSION=".*/VERSION="$(NEW_VERSION)"/' enterprise/bin/liveproxyd
	sed -i 's/^VERSION=".*/VERSION="$(NEW_VERSION)"/' enterprise/bin/cmcdump
	sed -i 's/^__version__ = ".*/__version__ = "$(NEW_VERSION)"/' enterprise/agents/plugins/cmk-update-agent
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
	rm -rf api clang-analyzer compile_commands.json dist.tmp rpm.topdir *.rpm *.deb *.exe \
	       mk-livestatus-*.tar.gz \
	       $(NAME)-*.tar.gz *~ counters autochecks \
	       precompiled cache web/htdocs/js/*_min.js \
	       .werks/werks \
	       .werks/cme-werks \
	       enterprise/.werks/werks \
	       ChangeLog \
	       enterprise/ChangeLog \
	       managed/ChangeLog
	find -name "*~" | xargs rm -f

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
	    libpcap-dev \
	    librrd-dev \
	    pngcrush \
	    slimit

ar-lib compile config.guess config.sub install-sh missing depcomp: configure.ac
	  autoreconf --install --include=m4

config.status: ar-lib compile config.guess config.sub install-sh missing depcomp configure
	@if test -f config.status; then \
	  echo "update config.status by reconfiguring in the same conditions" ; \
	  ./config.status --recheck; \
	else \
	  if test -d ../boost/local ; then \
	    BOOST_OPT="--with-boost=$(abspath ../boost/local)" ; \
	  elif test -d ../cmk-omd/packages/boost/local ; then \
	    BOOST_OPT="--with-boost=$(abspath ../cmk-omd/packages/boost/local)" ; \
	  elif test ! -d /usr/include/boost -a -d /usr/include/boost141/boost ; then \
	    BOOST_OPT="CPPFLAGS=-I/usr/include/boost141" ; \
	  else \
	    BOOST_OPT="DUMMY1=" ; \
	  fi ; \
	  if test -d "../rrdtool/rrdtool-1.5.4/src/.libs"; then \
	    RRD_OPT="LDFLAGS=-L$(realpath ../rrdtool/rrdtool-1.5.4/src/.libs)" ; \
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
	( cd livestatus && $(CPPCHECK) -DHAVE_CONFIG_H -UCMC --enable=all --suppress=missingIncludeSystem --suppress=unusedFunction --inline-suppr -I src -I .. -I . --file-list=- --quiet --template=gcc )
ifeq ($(ENTERPRISE),yes)
	@scripts/compiled_sources | \
	grep /enterprise/core/ |\
	sed 's/^"\(.*\)"$$/\1/' | \
	( cd enterprise/core/src && $(CPPCHECK) -DHAVE_CONFIG_H -DCMC --enable=all --suppress=missingIncludeSystem --suppress=unusedFunction --inline-suppr -I . -I ../../.. -I livestatus -I checkhelper --file-list=- --quiet --template=gcc )
endif

# XML output into file intended for machine processing.
cppcheck-xml: compile_commands.json
	scripts/compiled_sources | \
	grep /livestatus/src/ |\
	sed 's/^"\(.*\)"$$/\1/' | \
	( cd livestatus && $(CPPCHECK) -DHAVE_CONFIG_H -UCMC --enable=all --suppress=missingIncludeSystem --suppress=unusedFunction --inline-suppr -I src -I .. -I . --file-list=- --quiet --template=gcc --xml --xml-version=2 2> cppcheck-result.xml )
ifeq ($(ENTERPRISE),yes)
	scripts/compiled_sources | \
	grep /enterprise/core/ |\
	sed 's/^"\(.*\)"$$/\1/' | \
	( cd enterprise/core/src && $(CPPCHECK) -DHAVE_CONFIG_H -DCMC --enable=all --suppress=missingIncludeSystem --suppress=unusedFunction --inline-suppr -I . -I ../../.. -I livestatus -I checkhelper --file-list=- --quiet --template=gcc --xml --xml-version=2 2> cppcheck-result.xml )
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
