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
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

SHELL           = /bin/bash
VERSION         = 1.2.7i1
RPM_VERSION     = $(subst -,_,$(VERSION))
NAME            = check-mk-agent
DISTNAME       	= $(NAME)-$(VERSION)
RPM_TOPDIR     	= $$(pwd)/.rpm.topdir
RPM_BUILDROOT  	= $$(pwd)/.rpm.buildroot
RPM_PACKAGE     = $(DISTNAME)-1.noarch.rpm
DEB_PACKAGE     = check-mk-agent_$(VERSION)-1_all.deb

usage:
	@echo "make waitmax  -- compile waitmax.c"
	@echo "make rpm      -- create RPM package of Linux agent"
	@echo "make deb      -- create DEB package of Linux agent"
	@echo "make packages -- create RPM and DEB package of Linux agent"

waitmax: waitmax.c
	@if type diet >/dev/null ; then \
	    echo "Compiling with diet (please ignore diet-warnings)..." ; \
	    diet gcc -s -o waitmax waitmax.c ; \
	else \
	    echo "WARNING: your binary is not portable. Please compile " ; \
	    echo "with dietlibc on 32-Bit to get portable statically " ; \
	    echo "linked binary." ; \
	    echo ; \
	    echo "Compiling with normal gcc..." ; \
	    gcc -s -o waitmax waitmax.c ; \
	fi
	@echo "Fine. Typing 'make install' as root now will install into /usr/bin"

setversion:
	if [ -d ../.git ]; then \
	    git rm -f *.rpm *.deb || true ; \
	fi
	sed -ri 's/^(VERSION[[:space:]]*= *).*/\1'"$(NEW_VERSION)/" Makefile ; \
	sed -i 's/say "Version: .*"/say "Version: $(NEW_VERSION)"/' check_mk_agent.openvms ; \
	for agent in check_mk_agent.*; do \
	    if [ "$$agent" != windows -a "$$agent" != plugins -a "$$agent" != hpux ] ; then \
	        sed -i 's/echo Version: [0-9.a-z-]*/'"echo Version: $(NEW_VERSION)/g" $$agent; \
	    fi ; \
	done ; \
	$(MAKE) packages
	if [ -d ../.git ]; then \
	    git add *.rpm *.deb ; \
	fi
	$(MAKE) -C windows NEW_VERSION=$(NEW_VERSION) setversion

packages: rpm deb

rpm $(RPM_PACKAGE):
	rm -rf $(RPM_TOPDIR)
	mkdir -p $(RPM_TOPDIR)/RPMS
	mkdir -p $(RPM_TOPDIR)/SRPMS
	mkdir -p $(RPM_TOPDIR)/SOURCES
	mkdir -p $(RPM_TOPDIR)/BUILD
	mkdir -p $(RPM_TOPDIR)/SPECS
	tar czf $(RPM_TOPDIR)/SOURCES/$(NAME)-$(VERSION).tar.gz --transform='s@^@$(DISTNAME)/@' *
	sed "s/^Version:.*/Version: $(RPM_VERSION)/" $(NAME).spec > $(NAME)-$(VERSION).spec
	rm -f *.rpm
	rpmbuild -ba --buildroot "$(RPM_BUILDROOT)" \
	    --define "_topdir $(RPM_TOPDIR)" \
	    --define "_version $(VERSION)" \
	    $(DISTNAME).spec
	rm -f $(DISTNAME).spec
	mv -v $(RPM_TOPDIR)/RPMS/*/* $(RPM_PACKAGE)
	rm -rf $(RPM_TOPDIR) $(RPM_BUILDROOT)


deb $(DEB_PACKAGE): $(RPM_PACKAGE)
	@echo "Sorry. Debian packages currently via alien"
	rm -f *.deb
	fakeroot alien --scripts -k --to-deb $(RPM_PACKAGE)
	DEB_PKG=$$(ls *.deb) ; \
	echo "Repackaging $$DEB_PKG" ; \
	rm -rf deb-unpack ; \
	mkdir -p deb-unpack ; \
	cd deb-unpack && \
	ar x ../$$DEB_PKG && \
	mkdir ctrl && \
	tar xzf control.tar.gz -C ctrl && \
	sed -i -e '/^Depends:/d' \
	       -e 's/^Version:.*/Version: $(VERSION)-1/' \
	       -e 's/^Maintainer:.*/Maintainer: feedback@check-mk.org/' ctrl/control && \
	tar czf control.tar.gz $(TAROPTS) -C ctrl . && \
	ar r ../$(DEB_PACKAGE) debian-binary control.tar.gz data.tar.*
	rm -rf deb-unpack

clean:
	rm -rf *~ waitmax
