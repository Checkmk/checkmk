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

include ../defines.make

RPM_VERSION := $(subst -,_,$(VERSION))
NEW_VERSION_MAJOR := $(shell echo $(NEW_VERSION) | sed 's/\([0-9]*\.[0-9]*\)\.\(.*\)/\1/g')
NAME := check-mk-agent
DISTNAME := $(NAME)-$(VERSION)
RPM_TOPDIR := $$(pwd)/.rpm.topdir
RPM_BUILDROOT := $$(pwd)/.rpm.buildroot
RPM_PACKAGE := $(DISTNAME)-1.noarch.rpm
DEB_PACKAGE := check-mk-agent_$(VERSION)-1_all.deb
WIN_PACKAGE := windows/check_mk_agent.msi
usage:
	@echo "make waitmax  -- compile waitmax.c"
	@echo "make build    -- create all files needed for \"make dist\" of Check_MK"
	@echo "make rpm      -- create RPM package of Linux agent"
	@echo "make deb      -- create DEB package of Linux agent"
	@echo "make packages -- create RPM and DEB package of Linux agent"

waitmax: waitmax.c
	@if type diet >/dev/null ; then \
	    echo "Compiling with diet..." ; \
	    diet gcc -s -Wall -Wextra -O3 -o waitmax waitmax.c ; \
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
	sed -i 's/say "Version: .*"/say "Version: $(NEW_VERSION)"/' check_mk_agent.openvms ; \
	for agent in check_mk_agent.*; do \
	    if [ "$$agent" != windows -a "$$agent" != plugins -a "$$agent" != hpux ] ; then \
	        sed -i 's/echo "Version: [0-9.a-z-]*"/echo "Version: $(NEW_VERSION)"/g' $$agent; \
	    fi ; \
	done
	package="Check_MK Windows Agent" ; \
	mail=feedback@checkmk.com; \
	sed -i "s/^AC_INIT.*/AC_INIT([$$package], [$(NEW_VERSION)], [$$mail])/" \
	    windows/configure.ac
	sed -i "s/^#define CMK_WIN_AGENT_VERSION .*/#define CMK_WIN_AGENT_VERSION \"$(NEW_VERSION)\"/"\
		wnx/src/common/wnx_version.h

build: $(DEB_PACKAGE) $(RPM_PACKAGE) $(WIN_PACKAGE)

$(WIN_PACKAGE):
	cd windows && sudo \
		CHROOT_NAME=$$CHROOT_NAME \
		CHROOT_BASE_PATH=$$CHROOT_BASE_PATH \
		CHROOT_BUILD_DIR=$$CHROOT_BUILD_DIR \
		./make-agent

packages: $(DEB_PACKAGE) $(RPM_PACKAGE)

deb: $(DEB_PACKAGE)

rpm: $(RPM_PACKAGE)

$(RPM_PACKAGE): waitmax
	rm -rf $(RPM_TOPDIR)
	mkdir -p $(RPM_TOPDIR)/RPMS
	mkdir -p $(RPM_TOPDIR)/SRPMS
	mkdir -p $(RPM_TOPDIR)/SOURCES
	mkdir -p $(RPM_TOPDIR)/BUILD
	mkdir -p $(RPM_TOPDIR)/SPECS
	tar czf \
	    $(RPM_TOPDIR)/SOURCES/$(NAME)-$(VERSION).tar.gz \
	    --transform='s@^@$(DISTNAME)/@' \
	    cfg_examples \
	    check_mk_agent.linux \
	    check_mk_caching_agent.linux \
	    waitmax \
	    mk-job
	sed "s/^Version:.*/Version: $(RPM_VERSION)/" $(NAME).spec > $(NAME)-$(VERSION).spec
	rm -f *.rpm
	rpmbuild -ba --buildroot "$(RPM_BUILDROOT)" \
	    --define "_topdir $(RPM_TOPDIR)" \
	    --define "_version $(VERSION)" \
	    $(DISTNAME).spec
	rm -f $(DISTNAME).spec
	mv -v $(RPM_TOPDIR)/RPMS/*/* $(RPM_PACKAGE)
	rm -rf $(RPM_TOPDIR) $(RPM_BUILDROOT)


# TODO: Replace alien usage. Debian packages should be created just like the bakery does
#       Keep in mind that we still need to use gz compression by default for the agent
#       packages.
$(DEB_PACKAGE): $(RPM_PACKAGE)
	@echo "Sorry. Debian packages currently via alien"
	rm -f *.deb
	fakeroot alien --scripts -k --to-deb $(RPM_PACKAGE)
	DEB_PKG=$$(ls *.deb) ; \
	echo "Repackaging $$DEB_PKG" ; \
	rm -rf deb-unpack ; \
	mkdir -p deb-unpack ; \
	cd deb-unpack && \
	ar x ../$$DEB_PKG && \
	rm ../$$DEB_PKG && \
	mkdir ctrl && \
	tar xf control.tar.* -C ctrl && \
	sed -i -e '/^Depends:/d' \
	       -e 's/^Version:.*/Version: $(VERSION)-1/' \
	       -e 's/^Maintainer:.*/Maintainer: feedback@checkmk.com/' ctrl/control && \
	tar czf control.tar.gz $(TAROPTS) --group=0 --owner=0 -C ctrl . && \
	xz --decompress data.tar.xz && \
	gzip data.tar && \
	ar r ../$(DEB_PACKAGE) debian-binary control.tar.gz data.tar.gz
	rm -rf deb-unpack

clean:
	rm -rf *~ waitmax *.rpm *.deb
