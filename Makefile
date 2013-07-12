# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
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
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

SHELL           = /bin/bash
VERSION        	= 1.2.3i1
NAME           	= check_mk
RPM_TOPDIR     	= rpm.topdir
RPM_BUILDROOT  	= rpm.buildroot
PREFIX         	= /usr
BINDIR         	= $(PREFIX)/bin
CONFDIR	       	= /etc/$(NAME)
LIBDIR	       	= $(PREFIX)/lib/$(NAME)
DISTNAME       	= $(NAME)-$(VERSION)
TAROPTS        	= --owner=root --group=root --exclude=.svn --exclude=*~ \
		  --exclude=.gitignore --exclude=.*.swp --exclude=.f12
LIVESTATUS_SOURCES = configure aclocal.m4 config.guess config.h.in config.sub \
		     configure.ac ltmain.sh Makefile.am Makefile.in missing \
		     nagios/README nagios/*.h src/*.{h,c,cc} src/Makefile.{in,am} \
		     depcomp install-sh api/python/{*.py,README} api/perl/*


.PHONY: help install clean

all: dist rpm deb

help:
	@echo "make                           --> dist, rpm and deb"
	@echo "make dist                      --> create TGZ package"
	@echo "make deb                       --> create DEB package"
	@echo "make rpm                       --> create RPM package"
	@echo "make DESTDIR=/tmp/hirn install --> install directly"
	@echo "make version                   --> switch to new version"
	@echo "make headers                   --> create/update fileheades"
	@echo "make healspaces                --> remove trailing spaces in code"

check-spaces:
	@echo -n "Checking for trailing spaces..."
	@if grep -q '[[:space:]]$$' $(SOURCE_FILES) ; then echo $$? ; figlet "Space error" \
          ; echo "Aborting due to trailing spaces. Please use 'make healspaces' to repair." \
          ; echo "Affected files: " \
          ; grep -l '[ 	]$$' $(SOURCE_FILES) \
          ; exit 1 ; fi
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


check: check-spaces check-permissions check-binaries check-version

dist: mk-livestatus mk-eventd
	@echo "Making $(DISTNAME)"
	rm -rf $(DISTNAME)
	mkdir -p $(DISTNAME)
	tar czf $(DISTNAME)/share.tar.gz $(TAROPTS) check_mk_templates.cfg
	tar czf $(DISTNAME)/checks.tar.gz $(TAROPTS) -C checks $$(cd checks ; ls)
	tar czf $(DISTNAME)/notifications.tar.gz $(TAROPTS) -C notifications $$(cd notifications ; ls)
	tar czf $(DISTNAME)/checkman.tar.gz $(TAROPTS) -C checkman $$(cd checkman ; ls)
	tar czf $(DISTNAME)/web.tar.gz $(TAROPTS) -C web htdocs plugins
	tar czf $(DISTNAME)/livestatus.tar.gz $(TAROPTS) -C livestatus  $$(cd livestatus ; echo $(LIVESTATUS_SOURCES) )
	tar czf $(DISTNAME)/mkeventd.tar.gz $(TAROPTS) -C mkeventd  $$(cd mkeventd ; echo * )
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
	tar  czf $(DISTNAME)/agents.tar.gz $(TAROPTS) -C agents --exclude "*~" --exclude .f12 $$(cd agents ; ls)
	cd $(DISTNAME) ; ../make_package_info $(VERSION) > package_info
	install -m 755 scripts/*.{sh,py} $(DISTNAME)
	install -m 644 COPYING AUTHORS ChangeLog $(DISTNAME)
	echo "$(VERSION)" > $(DISTNAME)/VERSION
	tar czf $(DISTNAME).tar.gz $(TAROPTS) $(DISTNAME)
	rm -rf $(DISTNAME)
	@echo "=============================================================================="
	@echo "   FINISHED. "
	@echo "=============================================================================="

mk-eventd:
	tar -c $(TAROPTS) --exclude=.f12 \
	    --transform 's,^mkeventd,mkeventd-$(VERSION),' \
	    -zf mkeventd-$(VERSION).tar.gz mkeventd

mk-livestatus:
	if [ ! -e livestatus/configure ] ; then \
		cd livestatus && aclocal && autoheader && automake -a && autoconf ; \
	fi
	rm -rf mk-livestatus-$(VERSION)
	mkdir -p mk-livestatus-$(VERSION)
	cd livestatus ; tar cf - $(LIVESTATUS_SOURCES) | tar xf - -C ../mk-livestatus-$(VERSION)
	mkdir -p mk-livestatus-$(VERSION)/nagios
	cp livestatus/nagios/*.h mk-livestatus-$(VERSION)/nagios/
	tar czf mk-livestatus-$(VERSION).tar.gz $(TAROPTS) mk-livestatus-$(VERSION)
	rm -rf mk-livestatus-$(VERSION)


version:
	[ "$$(head -c 12 /etc/issue)" = "Ubuntu 10.10" \
          -o "$$(head -c 12 /etc/issue)" = "Ubuntu 11.04" \
          -o "$$(head -c 12 /etc/issue)" = "Ubuntu 11.10" \
          -o "$$(head -c 12 /etc/issue)" = "Ubuntu 12.04" \
          -o "$$(head -c 12 /etc/issue)" = "Ubuntu 12.10" \
          -o "$$(head -c 12 /etc/issue)" = "Ubuntu 13.04" \
          -o "$$(head -c 20 /etc/issue)" = "Debian GNU/Linux 6.0" ] \
          || { echo 'You are not on the reference system!' ; exit 1; }
	@newversion=$$(dialog --stdout --inputbox "New Version:" 0 0 "$(VERSION)") ; \
	if [ -n "$$newversion" ] ; then $(MAKE) NEW_VERSION=$$newversion setversion ; fi

setversion:
	sed -ri 's/^(VERSION[[:space:]]*= *).*/\1'"$(NEW_VERSION)/" Makefile ; \
	for agent in agents/* ; do \
	    if [ "$$agent" != agents/windows -a "$$agent" != agents/plugins -a "$$agent" != agents/hpux ] ; then \
	        sed -i 's/echo Version: [0-9.a-z]*/'"echo Version: $(NEW_VERSION)/g" $$agent; \
	    fi ; \
	done ; \
        sed -i 's/say "Version: .*"/say "Version: $(NEW_VERSION)"/' agents/check_mk_agent.openvms
	sed -i 's/#define CHECK_MK_VERSION .*/#define CHECK_MK_VERSION "'$(NEW_VERSION)'"/' agents/windows/check_mk_agent.cc ; \
	sed -i 's/!define CHECK_MK_VERSION .*/!define CHECK_MK_VERSION "'$(NEW_VERSION)'"/' agents/windows/installer.nsi ; \
	sed -i 's/^AC_INIT.*/AC_INIT([MK Livestatus], ['"$(NEW_VERSION)"'], [mk@mathias-kettner.de])/' livestatus/configure.ac ; \
	sed -i 's/^VERSION=".*/VERSION="$(NEW_VERSION)"/' mkeventd/bin/mkeventd ; \
	sed -i 's/^VERSION=".*/VERSION="$(NEW_VERSION)"/' doc/treasures/mknotifyd ; \
	sed -i 's/^VERSION=.*/VERSION='"$(NEW_VERSION)"'/' scripts/setup.sh ; \
	echo 'check-mk_$(NEW_VERSION)-1_all.deb net optional' > debian/files ; \
	cd agents/windows ; rm *.exe ; make ; cd ../.. ; \
	cp agents/windows/install_agent.exe check-mk-agent-$(NEW_VERSION).exe

headers:
	doc/helpers/headrify

rpm $(DISTNAME)-1.noarch.rpm:
	rm -rf $(RPM_TOPDIR)
	mkdir -p $(RPM_TOPDIR)/RPMS
	mkdir -p $(RPM_TOPDIR)/SRPMS
	mkdir -p $(RPM_TOPDIR)/SOURCES
	mkdir -p $(RPM_TOPDIR)/BUILD
	mkdir -p $(RPM_TOPDIR)/SPECS
	$(MAKE) dist
	cp $(DISTNAME).tar.gz $(RPM_TOPDIR)/SOURCES
	sed "s/^Version:.*/Version: $(VERSION)/" $(NAME).spec > $(NAME)-$(VERSION).spec
	rpmbuild -ba --buildroot "$$(pwd)/$(RPM_BUILDROOT)" --define "_topdir $$(pwd)/$(RPM_TOPDIR)" $(NAME)-$(VERSION).spec
	rm -f $(DISTNAME).spec
	mv -v $(RPM_TOPDIR)/RPMS/*/* .
	mv -v $(RPM_TOPDIR)/SRPMS/* .
	rm -rf $(RPM_TOPDIR)


deb: deb-agent

deb-base:
	rm -rf deb.bauen
	mkdir -p deb.bauen
	tar xzf $(DISTNAME).tar.gz -C deb.bauen
	mv deb.bauen/check_mk-$(VERSION) deb.bauen/check-mk-$(VERSION)
	cp -prv debian deb.bauen/check-mk-$(VERSION)/
	cd deb.bauen/check-mk-$(VERSION) ; dpkg-buildpackage -uc -us -rfakeroot
	mv -v deb.bauen/*.deb .
	rm -rf deb.bauen

deb-agent: $(NAME)-agent-$(VERSION)-1.noarch.rpm $(NAME)-agent-logwatch-$(VERSION)-1.noarch.rpm $(NAME)-agent-oracle-$(VERSION)-1.noarch.rpm
	@echo "Sorry. Debian packages currently via alien"
	@for pac in $^ ; do \
	  fakeroot alien --scripts -d $$pac ; \
	done
	@for p in agent agent-logwatch agent-oracle ; do \
	   pac="check-mk-$${p}_$(VERSION)-2_all.deb" ; \
	   echo "Repackaging $$pac" ; \
	   rm -rf deb-unpack && \
	   mkdir -p deb-unpack && \
	   cd deb-unpack && \
	   ar x ../$$pac && \
	   mkdir ctrl && \
	   tar xzf control.tar.gz -C ctrl && \
	   sed -i -e '/^Depends:/d' -e 's/^Maintainer:.*/Maintainer: mk@mathias-kettner.de/' ctrl/control && \
	   tar czf control.tar.gz $(TAROPTS) -C ctrl . && \
	   ar r ../$$pac debian-binary control.tar.gz data.tar.gz && \
	   cd .. && \
	   rm -rf deb-unpack || exit 1 ; \
	done


clean:
	rm -rf dist.tmp rpm.topdir *.rpm *.deb *.exe \
	       mkeventd-*.tar.gz mk-livestatus-*.tar.gz \
	       $(NAME)-*.tar.gz *~ counters autochecks \
	       precompiled cache
	find -name "*~" | xargs rm -f

mrproper:
	git clean -xfd -e .bugs 2>/dev/null || git clean -xfd


SOURCE_FILES = checkman/* modules/* checks/* notifications/* $$(find -name Makefile) \
          livestatus/src/*{cc,c,h} web/htdocs/*.{py,css} web/htdocs/js/*.js web/plugins/*/*.py \
          doc/helpers/* scripts/setup.sh scripts/autodetect.py $(find -type f pnp-templates/*.php) \
          mkeventd/bin/mkeventd mkeventd/web/htdocs/*.py mkeventd/web/plugins/*/*.py mkeventd/src/*.c \
          mkeventd/checks/*

healspaces:
	@echo "Removing trailing spaces from code lines..."
	@sed -ri 's/[ 	]+$$//g' $(SOURCE_FILES)

setup:

	$(MAKE) dist
	rm -rf $(DISTNAME)
	tar xzf $(DISTNAME).tar.gz
	cd $(DISTNAME) && ./setup.sh --yes
	rm -rf $(DISTNAME)
	check_mk -R
	/etc/init.d/apache2 reload


-include Makefile.private
