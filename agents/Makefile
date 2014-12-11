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

VERSION         = 1.2.6b2
NAME            = check_mk_agent
DISTNAME       	= $(NAME)-$(VERSION)
RPM_TOPDIR     	= $$(pwd)/.rpm.topdir
RPM_BUILDROOT  	= $$(pwd)/.rpm.buildroot
RPM_PACKAGE     = $(DISTNAME)-1.noarch.rpm
DEB_PACKAGE     = check-mk-agent_$(VERSION)-2_all.deb

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

packages: rpm deb

rpm $(RPM_PACKAGE):
	rm -rf $(RPM_TOPDIR)
	mkdir -p $(RPM_TOPDIR)/RPMS
	mkdir -p $(RPM_TOPDIR)/SRPMS
	mkdir -p $(RPM_TOPDIR)/SOURCES
	mkdir -p $(RPM_TOPDIR)/BUILD
	mkdir -p $(RPM_TOPDIR)/SPECS
	tar czf $(RPM_TOPDIR)/SOURCES/$(NAME)-$(VERSION).tar.gz --transform='s@^@$(DISTNAME)/@' *
	sed "s/^Version:.*/Version: $(VERSION)/" $(NAME).spec > $(NAME)-$(VERSION).spec
	rm -f *.rpm
	rpmbuild -ba --buildroot "$(RPM_BUILDROOT)" --define "_topdir $(RPM_TOPDIR)" $(DISTNAME).spec
	rm -f $(DISTNAME).spec
	mv -v $(RPM_TOPDIR)/RPMS/*/* .
	rm -rf $(RPM_TOPDIR) $(RPM_BUILDROOT)


deb $(DEB_PACKAGE): $(RPM_PACKAGE)
	@echo "Sorry. Debian packages currently via alien"
	fakeroot alien --scripts --to-deb $(RPM_PACKAGE)
	echo "Repackaging $(DEB_PACKAGE)"
	rm -rf deb-unpack
	mkdir -p deb-unpack
	cd deb-unpack && \
	ar x ../$(DEB_PACKAGE) && \
	mkdir ctrl && \
	tar xzf control.tar.gz -C ctrl && \
	sed -i -e '/^Depends:/d' -e 's/^Maintainer:.*/Maintainer: feedback@check-mk.org/' ctrl/control && \
	tar czf control.tar.gz $(TAROPTS) -C ctrl . && \
	ar r ../$(DEB_PACKAGE) debian-binary control.tar.gz data.tar.*
	rm -rf deb-unpack


clean:
	rm -rf *~ waitmax
