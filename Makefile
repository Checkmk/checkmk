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

SHELL              := /bin/bash
VERSION            := 1.4.0i1
NAME               := check_mk
PREFIX             := /usr
BINDIR             := $(PREFIX)/bin
CONFDIR            := /etc/$(NAME)
LIBDIR             := $(PREFIX)/lib/$(NAME)
DISTNAME           := $(NAME)-$(VERSION)
TAROPTS            := --owner=root --group=root --exclude=.svn --exclude=*~ \
                      --exclude=.gitignore --exclude=*.swp --exclude=.f12
CXX_FLAGS          := -g -O3 -Wall -Wextra

CLANG_VERSION      := 3.9
CLANG_FORMAT       := clang-format-$(CLANG_VERSION)
CLANG_TIDY         := clang-tidy-$(CLANG_VERSION)
SCAN_BUILD         := scan-build-$(CLANG_VERSION)
CPPCHECK           := cppcheck
DOXYGEN            := doxygen
IWYU_TOOL          := iwyu_tool.py
BEAR               := bear

# File to pack into livestatus-$(VERSION).tar.gz
LIVESTATUS_AUTO    := aclocal.m4 ar-lib compile config.h.in configure depcomp \
                      install-sh Makefile.in missing src/Makefile.in
LIVESTATUS_SOURCES := $(LIVESTATUS_AUTO) config.guess config.sub configure.ac \
                      ltmain.sh Makefile.am nagios/README nagios/*.h \
                      nagios4/README m4/* nagios4/*.h src/*.{h,cc} \
                      src/Makefile.am api/python/{*.py,README} api/perl/*

# Files that are checked for trailing spaces
HEAL_SPACES_IN     := checkman/* modules/* checks/* notifications/* inventory/* \
                      $$(find -name Makefile) livestatus/src/*.{cc,h} \
                      agents/windows/*.cc \
                      web/htdocs/*.{py,css} web/htdocs/js/*.js web/plugins/*/*.py \
                      doc/helpers/* scripts/setup.sh scripts/autodetect.py \
                      $$(find pnp-templates -type f -name "*.php") \
                      bin/mkeventd bin/*.c doc/treasures/active_checks/* \
                      check_mk_templates.cfg \
                      agents/check_mk_*agent* agents/*.c \
                      $$(find agents/cfg_examples -type f) \
                      agents/special/* \
                      $$(find agents/plugins -type f)

FILES_TO_FORMAT    := $(wildcard $(addprefix agents/,*.cc *.c *.h)) \
                      $(wildcard $(addprefix agents/windows/,*.cc *.c *.h)) \
                      $(wildcard $(addprefix livestatus/api/c++/,*.cc *.h)) \
                      $(wildcard $(addprefix livestatus/src/,*.cc *.h)) \
                      $(wildcard $(addprefix bin/,*.cc *.c *.h))

.PHONY: all analyze check check-binaries check-permissions check-spaces \
        check-version clean cppcheck dist documentation format git-clean \
        GTAGS headers healspaces help iwyu minify-js mk-livestatus mrproper \
        optimize-images packages setup setversion tidy version

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

check-permissions:
	@echo -n "Checking permissions... with find -not -perm -444..." && [ -z "$$(find -not -perm -444)" ] && echo OK

check-binaries:
	@if [ -z "$(SKIP_SANITY_CHECKS)" ]; then \
	    echo -n "Checking precompiled binaries..." && file agents/waitmax | grep 32-bit >/dev/null && echo OK ; \
	fi

check: check-spaces check-permissions check-binaries check-version

dist: mk-livestatus
	@echo "Making $(DISTNAME)"
	rm -rf $(DISTNAME)
	mkdir -p $(DISTNAME)
	tar czf $(DISTNAME)/bin.tar.gz $(TAROPTS) -C bin $$(cd bin ; ls)
	pycompile lib ; \
	  tar czf $(DISTNAME)/lib.tar.gz $(TAROPTS) -C lib \
	    --transform 's|^|cmk/|g' $$(cd lib ; ls) ; \
	  rm lib/*.pyc
	tar czf $(DISTNAME)/share.tar.gz $(TAROPTS) check_mk_templates.cfg
	tar czf $(DISTNAME)/werks.tar.gz $(TAROPTS) -C .werks $$(cd .werks ; ls [0-9]*)
	tar czf $(DISTNAME)/checks.tar.gz $(TAROPTS) -C checks $$(cd checks ; ls)
	tar czf $(DISTNAME)/notifications.tar.gz $(TAROPTS) -C notifications $$(cd notifications ; ls)
	tar czf $(DISTNAME)/inventory.tar.gz $(TAROPTS) -C inventory $$(cd inventory ; ls)
	tar czf $(DISTNAME)/checkman.tar.gz $(TAROPTS) -C checkman $$(cd checkman ; ls)
	$(MAKE) minify-js
	tar czf $(DISTNAME)/web.tar.gz $(TAROPTS) -C web htdocs plugins

	tar cf $(DISTNAME)/livestatus.tar $(TAROPTS) -C livestatus  $$(cd livestatus ; echo $(LIVESTATUS_SOURCES) )
	gzip $(DISTNAME)/livestatus.tar

	tar czf $(DISTNAME)/pnp-templates.tar.gz $(TAROPTS) -C pnp-templates $$(cd pnp-templates ; ls *.php)
	tar cf $(DISTNAME)/doc.tar $(TAROPTS) -C doc $$(cd doc ; ls)
	tar rf $(DISTNAME)/doc.tar $(TAROPTS) COPYING AUTHORS ChangeLog
	tar rf $(DISTNAME)/doc.tar $(TAROPTS) livestatus/api --exclude "*~" --exclude "*.pyc" --exclude ".gitignore" --exclude .f12
	gzip $(DISTNAME)/doc.tar
	tar czf $(DISTNAME)/modules.tar.gz $(TAROPTS) -C modules $$(cd modules ; ls *.py)

	cp main.mk main.mk-$(VERSION)
	cp multisite.mk multisite.mk-$(VERSION)
	tar  czf $(DISTNAME)/conf.tar.gz $(TAROPTS) main.mk-$(VERSION) multisite.mk-$(VERSION)
	rm -f main.mk-$(VERSION) multisite.mk-$(VERSION)
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
		--exclude "Makefile" \
		--exclude "crash.exe" \
		--exclude "openhardwaremonitor" \
		--exclude .f12 $$(cd agents ; ls)
	cd $(DISTNAME) ; ../make_package_info $(VERSION) > package_info
	install -m 755 scripts/*.{sh,py} $(DISTNAME)
	install -m 644 COPYING AUTHORS ChangeLog $(DISTNAME)
	echo "$(VERSION)" > $(DISTNAME)/VERSION
	tar czf $(DISTNAME).tar.gz $(TAROPTS) $(DISTNAME)
	rm -rf $(DISTNAME)
	@echo "=============================================================================="
	@echo "   FINISHED. "
	@echo "=============================================================================="

packages:
	$(MAKE) -C agents packages

mk-livestatus: $(addprefix livestatus/,$(LIVESTATUS_AUTO))
	rm -rf mk-livestatus-$(VERSION)
	mkdir -p mk-livestatus-$(VERSION)
	cd livestatus ; tar cf - $(LIVESTATUS_SOURCES) | tar xf - -C ../mk-livestatus-$(VERSION)
	mkdir -p mk-livestatus-$(VERSION)/nagios
	cp livestatus/nagios/*.h mk-livestatus-$(VERSION)/nagios/
	mkdir -p mk-livestatus-$(VERSION)/nagios4
	cp livestatus/nagios4/*.h mk-livestatus-$(VERSION)/nagios4/
	tar czf mk-livestatus-$(VERSION).tar.gz $(TAROPTS) mk-livestatus-$(VERSION)
	rm -rf mk-livestatus-$(VERSION)


check-version:
	@sed -n 1p ChangeLog | fgrep -qx '$(VERSION):' || { \
	    echo "Version $(VERSION) not listed at top of ChangeLog!" ; \
	    false ; }

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
          -o "$$(head -c 20 /etc/issue)" = "Debian GNU/Linux 6.0" ] \
          || { echo 'You are not on the reference system!' ; exit 1; }
	@newversion=$$(dialog --stdout --inputbox "New Version:" 0 0 "$(VERSION)") ; \
	if [ -n "$$newversion" ] ; then $(MAKE) NEW_VERSION=$$newversion setversion ; fi

setversion:
	sed -ri 's/^(VERSION[[:space:]]*:?= *).*/\1'"$(NEW_VERSION)/" Makefile ; \
	sed -i 's/^AC_INIT.*/AC_INIT([MK Livestatus], ['"$(NEW_VERSION)"'], [mk@mathias-kettner.de])/' livestatus/configure.ac ; \
	sed -i 's/^VERSION=".*/VERSION="$(NEW_VERSION)"/' bin/mkeventd bin/mkbackup ; \
	sed -i 's/^__version__ = ".*"$$/__version__ = "$(NEW_VERSION)"/' lib/__init__.py ; \
	sed -i 's/^VERSION=.*/VERSION='"$(NEW_VERSION)"'/' scripts/setup.sh ; \
	echo 'check-mk_$(NEW_VERSION)-1_all.deb net optional' > debian/files
	$(MAKE) -C agents NEW_VERSION=$(NEW_VERSION) setversion

headers:
	doc/helpers/headrify

check-spaces:
	@echo -n "Checking for trailing spaces..."
	@if grep -q '[[:space:]]$$' $(HEAL_SPACES_IN) ; then echo $$? ; figlet "Space error" \
          ; echo "Aborting due to trailing spaces. Please use 'make healspaces' to repair." \
          ; echo "Affected files: " \
          ; grep -l '[[:space:]]$$' $(HEAL_SPACES_IN) \
          ; exit 1 ; fi
	@echo OK


healspaces:
	@echo "Removing trailing spaces from code lines..."
	@sed -ri 's/[[:space:]]+$$//g' $(HEAL_SPACES_IN)

optimize-images:
	@if type pngcrush >/dev/null 2>&1; then \
	    for F in web/htdocs/images/*.png web/htdocs/images/icons/*.png; do \
	        echo "Optimizing $$F..." ; \
	        pngcrush -q -rem alla -brute $$F $$F.opt ; \
	        mv $$F.opt $$F; \
	    done ; \
	else \
	    echo "Missing pngcrush, not optimizing images! (run \"make setup\" to fix this)" ; \
	fi

minify-js:
	@if type slimit >/dev/null 2>&1; then \
	    [ -n "$(DESTDIR)" ] && DESTDIR="$(DESTDIR)/" ; \
	    for F in $$(cd web/htdocs/js ; ls *.js); do \
	        if [ $${F/_min/} == $$F ] ; then \
	            NAME=$${F%.*} ; \
	            SRC=web/htdocs/js/$$F ; \
	            DST=$${DESTDIR}web/htdocs/js/$${NAME}_min.js ; \
	            if [ ! -f $$DST ] || [ $$(stat -c%Y $$SRC) -gt $$(stat -c%Y $$DST) ]; then \
	                echo "Minifying $$F..." ; \
	                cat $$SRC | slimit > $$DST ; \
	            fi ; \
	        fi ; \
	    done ; \
	else \
	    echo "Missing slimit, not minifying javascript files! (run \"make setup\" to fix this)" ; \
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
               $(addprefix livestatus/,$(LIVESTATUS_AUTO))
	find -name "*~" | xargs rm -f

mrproper:
	git clean -d --force -x \
            --exclude='\.bugs/.last' \
            --exclude='\.bugs/.my_ids' \
            --exclude='\.werks/.last' \
            --exclude='\.werks/.my_ids'

setup:
	sudo apt-get install figlet pngcrush slimit bear dietlibc-dev

$(addprefix %/,$(LIVESTATUS_AUTO)): $(addprefix %/,configure.ac m4/* Makefile.am src/Makefile.am)
	@echo "making $@: $? is newer"
	cd livestatus && autoreconf --install --include=m4

livestatus/config.h: livestatus/configure livestatus/config.h.in
	@echo "making $@: $? is newer"
	cd livestatus && ./configure CXXFLAGS="$(CXX_FLAGS)"

GTAGS: livestatus/config.h
	@echo "making $@: $? is newer"
	$(MAKE) -C livestatus distclean-tags
	$(MAKE) -C livestatus GTAGS

compile_commands.json: livestatus/config.h $(FILES_TO_FORMAT)
	@echo "making $@: $? is newer"
	$(MAKE) -C livestatus clean
	$(BEAR) $(MAKE) -C livestatus -j8

tidy: compile_commands.json
	@./compiled_sources | xargs $(CLANG_TIDY) --extra-arg=-D__clang_analyzer__

# Not really perfect rules, but better than nothing
iwyu: compile_commands.json
	@$(IWYU_TOOL) -p .

# Not really perfect rules, but better than nothing
analyze: livestatus/config.h
	$(MAKE) -C livestatus clean
	cd livestatus && $(SCAN_BUILD) -o ../clang-analyzer $(MAKE) CXXFLAGS="-std=c++14"

# TODO: Repeating the include paths in the cppcheck targets below is ugly and
# fragile.

# GCC-like output on stderr intended for human consumption.
cppcheck: compile_commands.json
	@./compiled_sources | \
	sed 's/^"\(.*\)"$$/\1/' | \
	$(CPPCHECK) --max-configs=16 -UCMC --enable=all --suppress=missingIncludeSystem --inline-suppr -I livestatus/src -I livestatus --file-list=- --quiet --template=gcc

# XML output into file intended for machine processing.
cppcheck-xml: compile_commands.json
	@./compiled_sources | \
	sed 's/^"\(.*\)"$$/\1/' | \
	$(CPPCHECK) --max-configs=16 -UCMC --enable=all --suppress=missingIncludeSystem --inline-suppr -I livestatus/src -I livestatus --file-list=- --quiet --template=gcc --xml --xml-version=2 2> cppcheck-result.xml

# TODO: We should probably handle this rule via AM_EXTRA_RECURSIVE_TARGETS in
# src/configure.ac, but this needs at least automake-1.13, which in turn is only
# available from e.g. Ubuntu Saucy (13) onwards, so some magic is needed.
format:
	$(CLANG_FORMAT) -style=file -i $(FILES_TO_FORMAT)

# Note: You need the doxygen and graphviz packages.
documentation: livestatus/config.h
	$(DOXYGEN) doc/Doxyfile
