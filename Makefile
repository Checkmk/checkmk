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
VERSION            := 1.2.8p25
NAME               := check_mk
PREFIX             := /usr
BINDIR             := $(PREFIX)/bin
CONFDIR            := /etc/$(NAME)
LIBDIR             := $(PREFIX)/lib/$(NAME)
DISTNAME           := $(NAME)-$(VERSION)
TAROPTS            := --owner=root --group=root --exclude=.svn --exclude=*~ \
                      --exclude=.gitignore --exclude=*.swp --exclude=.f12

CLANG_VERSION      := 3.8
CLANG_FORMAT       := clang-format-$(CLANG_VERSION)
CLANG_TIDY         := clang-tidy-$(CLANG_VERSION)
SCAN_BUILD         := scan-build-$(CLANG_VERSION)
CPPCHECK           := cppcheck
DOXYGEN            := doxygen
IWYU               := include-what-you-use
BEAR               := bear-fixed

# File to pack into livestatus-$(VERSION).tar.gz
LIVESTATUS_SOURCES := configure aclocal.m4 config.guess config.h.in config.sub \
                      configure.ac ltmain.sh Makefile.{in,am} missing ar-lib \
                      nagios/README nagios/*.h nagios4/README nagios4/*.h \
                      src/*.{h,c,cc} src/mk/*.h src/Makefile.{in,am} \
                      depcomp install-sh api/python/{*.py,README} api/perl/*

# Files that are checked for trailing spaces
HEAL_SPACES_IN     := checkman/* modules/* checks/* notifications/* inventory/* \
                      $$(find -name Makefile) livestatus/src/*.{cc,c,h} \
                      livestatus/src/mk/*.h agents/windows/*.cc \
                      web/htdocs/*.{py,css} web/htdocs/js/*.js web/plugins/*/*.py \
                      doc/helpers/* scripts/setup.sh scripts/autodetect.py \
                      $$(find pnp-templates -type f -name "*.php") \
                      mkeventd/bin/mkeventd mkeventd/web/htdocs/*.py mkeventd/web/plugins/*/*.py \
                      mkeventd/src/*.c mkeventd/checks/* check_mk_templates.cfg \
                      agents/check_mk_*agent* agents/*.c \
                      $$(find agents/cfg_examples -type f) \
                      agents/special/* \
                      $$(find agents/plugins -type f)

FILES_TO_FORMAT    := $(wildcard $(addprefix agents/,*.cc *.c *.h)) \
                      $(wildcard $(addprefix agents/windows/,*.cc *.c *.h)) \
                      $(wildcard $(addprefix livestatus/api/c++/,*.cc *.c *.h)) \
                      $(wildcard $(addprefix livestatus/src/,*.cc *.c *.h)) \
                      $(wildcard $(addprefix livestatus/src/mk,*.cc *.c *.h)) \
                      $(wildcard $(addprefix mkeventd/src/,*.cc *.c *.h))

.PHONY: all analyze check check-binaries check-permissions check-spaces \
        check-version clean cppcheck dist documentation format GTAGS headers \
        healspaces help iwyu minify-js mk-eventd mk-livestatus mrproper \
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

dist: mk-livestatus mk-eventd
	@echo "Making $(DISTNAME)"
	rm -rf $(DISTNAME)
	mkdir -p $(DISTNAME)
	tar czf $(DISTNAME)/share.tar.gz $(TAROPTS) check_mk_templates.cfg
	tar czf $(DISTNAME)/werks.tar.gz $(TAROPTS) -C .werks $$(cd .werks ; ls [0-9]*)
	tar czf $(DISTNAME)/checks.tar.gz $(TAROPTS) -C checks $$(cd checks ; ls)
	tar czf $(DISTNAME)/notifications.tar.gz $(TAROPTS) -C notifications $$(cd notifications ; ls)
	tar czf $(DISTNAME)/inventory.tar.gz $(TAROPTS) -C inventory $$(cd inventory ; ls)
	tar czf $(DISTNAME)/checkman.tar.gz $(TAROPTS) -C checkman $$(cd checkman ; ls)
	$(MAKE) minify-js
	tar czf $(DISTNAME)/web.tar.gz $(TAROPTS) -C web htdocs plugins
	tar czf $(DISTNAME)/mkeventd.tar.gz $(TAROPTS) -C mkeventd  $$(cd mkeventd ; echo * )

	tar cf $(DISTNAME)/livestatus.tar $(TAROPTS) -C livestatus  $$(cd livestatus ; echo $(LIVESTATUS_SOURCES) )
	if [ -f livestatus/compile ]; then \
	    tar rf $(DISTNAME)/livestatus.tar $(TAROPTS) -C livestatus compile ; \
	fi
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

mk-eventd:
	tar -c $(TAROPTS) --exclude=.f12 \
	    --transform 's,^mkeventd,mkeventd-$(VERSION),' \
	    -zf mkeventd-$(VERSION).tar.gz mkeventd

mk-livestatus:
	cd livestatus ; \
	for i in aclocal.m4 ar-lib compile config.h.in configure depcomp install-sh Makefile.in missing; do \
	    if test ! -f $$i; then \
		autoreconf --install ; \
		break ; \
	    fi \
	done
	rm -rf mk-livestatus-$(VERSION)
	mkdir -p mk-livestatus-$(VERSION)
	cd livestatus ; tar cf - $(LIVESTATUS_SOURCES) | tar xf - -C ../mk-livestatus-$(VERSION)
	if [ -f livestatus/compile ]; then \
	    cp -p livestatus/compile mk-livestatus-$(VERSION)/ ; \
	fi
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
	sed -i 's/^VERSION=".*/VERSION="$(NEW_VERSION)"/' mkeventd/bin/mkeventd ; \
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

clean:
	rm -rf api clang-analyzer compile_commands.json dist.tmp rpm.topdir *.rpm *.deb *.exe \
	       mkeventd-*.tar.gz mk-livestatus-*.tar.gz \
	       $(NAME)-*.tar.gz *~ counters autochecks \
	       precompiled cache web/htdocs/js/*_min.js
	find -name "*~" | xargs rm -f

mrproper:
	git clean -xfd -e .bugs 2>/dev/null || git clean -xfd

setup:
	sudo apt-get install figlet pngcrush slimit bear

GTAGS:
	$(MAKE) -C livestatus distclean-tags
	$(MAKE) -C livestatus GTAGS

compile_commands.json: $(FILES_TO_FORMAT)
	$(MAKE) -C livestatus clean
	$(BEAR) $(MAKE) -C livestatus -j8

tidy: compile_commands.json
	./compiled_sources | xargs $(CLANG_TIDY)

# Not really perfect rules, but better than nothing
iwyu:
	$(MAKE) -C livestatus clean
	$(MAKE) -C livestatus CC=$(IWYU) CXX=$(IWYU) -k

# Not really perfect rules, but better than nothing
analyze:
	$(MAKE) -C livestatus clean
	cd livestatus && $(SCAN_BUILD) -o ../clang-analyzer $(MAKE)

cppcheck:
	$(CPPCHECK) --quiet --enable=all --max-configs=20 --inline-suppr --template=gcc -I livestatus/src -I livestatus livestatus

# TODO: We should probably handle this rule via AM_EXTRA_RECURSIVE_TARGETS in
# src/configure.ac, but this needs at least automake-1.13, which in turn is only
# available from e.g. Ubuntu Saucy (13) onwards, so some magic is needed.
format:
	$(CLANG_FORMAT) -style=file -i $(FILES_TO_FORMAT)

# Note: You need the doxygen and graphviz packages.
documentation:
	$(DOXYGEN) doc/Doxyfile
