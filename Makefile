# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2010             mk@mathias-kettner.de |
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
VERSION        	= 1.1.4a3
NAME           	= check_mk
RPM_TOPDIR     	= rpm.topdir
RPM_BUILDROOT  	= rpm.buildroot
WWWROOT        	= /srv/www/htdocs
PREFIX         	= /usr
BINDIR         	= $(PREFIX)/bin
CONFDIR	       	= /etc/$(NAME)
LIBDIR	       	= $(PREFIX)/lib/$(NAME)
DISTNAME       	= $(NAME)-$(VERSION)
TAROPTS        	= --owner=root --group=root --exclude=.svn --exclude=*~ 
DOWNLOADURL     = http://mathias-kettner.de/download/$(DISTNAME).tar.gz
CHECKMANDIR	= /home/mk/svn/mkde/htdocs/checkmk
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

dist: mk-livestatus
	@echo "--------------------------------------------------------------------------"
	@echo -n "Checking permissions... with find -not -perm -444..." && [ -z "$$(find -not -perm -444)" ] && echo OK
	@echo "Making $(DISTNAME)"
	rm -rf $(DISTNAME)
	mkdir -p $(DISTNAME)
	tar czf $(DISTNAME)/checks.tar.gz $(TAROPTS) -C checks $$(cd checks ; ls)
	tar czf $(DISTNAME)/checkman.tar.gz $(TAROPTS) -C checkman $$(cd checkman ; ls)
	tar czf $(DISTNAME)/htdocs.tar.gz $(TAROPTS) -C htdocs $$(cd htdocs ; ls *.php *.css *.png *.gif)
	tar czf $(DISTNAME)/web.tar.gz $(TAROPTS) -C web $$(cd web ; ls htdocs/*/*.{jpg,png,gif} htdocs/*.{py,css,js} plugins/*/*.py)
	tar czf $(DISTNAME)/livestatus.tar.gz $(TAROPTS) -C livestatus  $$(cd livestatus ; echo $(LIVESTATUS_SOURCES) )
	tar czf $(DISTNAME)/pnp-templates.tar.gz $(TAROPTS) -C pnp-templates $$(cd pnp-templates ; ls *.php)
	tar cf $(DISTNAME)/doc.tar $(TAROPTS) -C doc --exclude .svn --exclude "*~" \
			check_mk_templates.cfg check_mk.1 \
			check_mk.css screenshot1.png README helpers \
			check_mk{,.trans}.200.png windows \
			df_magic_number.py livestatus
	tar rf $(DISTNAME)/doc.tar $(TAROPTS) COPYING AUTHORS ChangeLog
	tar rf $(DISTNAME)/doc.tar $(TAROPTS) livestatus/api --exclude "*~" --exclude "*.pyc" --exclude ".gitignore" --exclude .f12 
	gzip $(DISTNAME)/doc.tar
	tar czf $(DISTNAME)/modules.tar.gz $(TAROPTS) -C modules $$(cd modules ; ls *.py)

	cp main.mk main.mk-$(VERSION)
	cp multisite.mk multisite.mk-$(VERSION)
	tar  czf $(DISTNAME)/conf.tar.gz $(TAROPTS) main.mk-$(VERSION) multisite.mk-$(VERSION)
	rm -f main.mk-$(VERSION) multisite.mk-$(VERSION)
	tar  cf $(DISTNAME)/agents.tar $(TAROPTS) -C agents --exclude "*~" $$(cd agents ; ls | grep -v windows )
	tar  rf $(DISTNAME)/agents.tar $(TAROPTS) -C agents windows/{check_mk_agent.exe,check_mk_agent.cc,Makefile}
	gzip $(DISTNAME)/agents.tar
	install -m 755 scripts/*.{sh,py} $(DISTNAME)
	install -m 644 COPYING AUTHORS ChangeLog $(DISTNAME)
	echo "$(VERSION)" > $(DISTNAME)/VERSION
	tar czf $(DISTNAME).tar.gz $(DISTNAME)
	rm -rf $(DISTNAME)
	@echo "=============================================================================="
	@echo "   FINISHED. "
	@echo "=============================================================================="

mk-livestatus:
	if [ ! -e livestatus/configure ] ; then \
		cd livestatus && aclocal && autoheader && automake && autoconf ; \
	fi
	rm -rf mk-livestatus-$(VERSION)
	mkdir -p mk-livestatus-$(VERSION)
	cd livestatus ; tar cf - $(LIVESTATUS_SOURCES) | tar xf - -C ../mk-livestatus-$(VERSION)
	mkdir -p mk-livestatus-$(VERSION)/nagios
	cp livestatus/nagios/*.h mk-livestatus-$(VERSION)/nagios/
	tar czf mk-livestatus-$(VERSION).tar.gz mk-livestatus-$(VERSION)
	rm -rf mk-livestatus-$(VERSION)


version:
	@newversion=$$(dialog --stdout --inputbox "New Version:" 0 0 "$(VERSION)") ; \
	if [ -n "$$newversion" ] ; then \
	    sed -ri 's/^(VERSION[[:space:]]*= *).*/\1'"$$newversion/" Makefile ; \
	    for agent in agents/* ; do \
	        if [ "$$agent" != agents/windows ] ; then \
	            sed -i 's/echo Version: [0-9.a-z]*/'"echo Version: $$newversion/g" $$agent; \
	        fi ; \
	    done ; \
	    sed -i 's/#define CHECK_MK_VERSION .*/#define CHECK_MK_VERSION "'$$newversion'"/' agents/windows/check_mk_agent.cc ; \
	    sed -i 's/^AC_INIT.*/AC_INIT([MK Livestatus], ['"$$newversion"'], [mk@mathias-kettner.de])/' livestatus/configure.ac ; \
	    sed -i 's/^VERSION=.*/VERSION='"$$newversion"'/' scripts/setup.sh ; \
	    echo 'check-mk_$$newversion-1_all.deb net optional' > debian/files ; \
	    sed -i 's/^CHECK_MK_VERSION=.*/CHECK_MK_VERSION='$$newversion/ scripts/install_nagios.sh ; \
	fi ; \

headers:
	./headrify

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
	rpmbuild -ba --target=noarch --buildroot "$$(pwd)/$(RPM_BUILDROOT)" --define "_topdir $$(pwd)/$(RPM_TOPDIR)" $(NAME)-$(VERSION).spec
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

deb-agent: $(NAME)-agent-$(VERSION)-1.noarch.rpm $(NAME)-agent-logwatch-$(VERSION)-1.noarch.rpm 
	@echo "Sorry. Debian packages currently via alien"
	@for pac in $^ ; do \
	  fakeroot alien --scripts -d $$pac ; \
	done
	@for p in agent agent-logwatch ; do \
	   pac="check-mk-$${p}_$(VERSION)-2_all.deb" ; \
	   echo "Repackaging $$pac" ; \
	   rm -rf deb-unpack && \
	   mkdir -p deb-unpack && \
	   cd deb-unpack && \
	   ar x ../$$pac && \
	   mkdir ctrl && \
	   tar xzf control.tar.gz -C ctrl && \
	   sed -i -e '/^Depends:/d' -e 's/^Maintainer:.*/Maintainer: mk@mathias-kettner.de/' ctrl/control && \
	   tar czf control.tar.gz -C ctrl . && \
	   ar r ../$$pac debian-binary control.tar.gz data.tar.gz && \
	   cd .. && \
	   rm -rf deb-unpack || exit 1 ; \
	done


clean:
	rm -rf dist.tmp rpm.topdir *.rpm *.deb mk-livestatus-*.tar.gz $(NAME)-*.tar.gz *~ counters autochecks precompiled cache
	find -name "*~" | xargs rm -f

mrproper:
	git clean -xfd

check:
	@set -e ; for checkfile in *.HS ; do \
	  echo -n "Checking config output of $${checkfile%.HS}..." ; \
	  diff -u <(./check_mk -c $${checkfile%.HS} -HS | grep -v 'created by check_mk') \
	          <(grep -v 'created by check_mk' < $$checkfile) && echo OK || { \
	    echo "ERROR. Update reference with:" ; \
	    echo "./check_mk -c $${checkfile%.HS} -HS > $$checkfile" ; \
            exit 1 ; } ; \
	done 

setup:
	$(MAKE) dist
	rm -rf $(DISTNAME)
	tar xzf $(DISTNAME).tar.gz
	cd $(DISTNAME) && ./setup.sh --yes
	/etc/init.d/nagios restart
	/etc/init.d/apache2 reload


-include Makefile.private
