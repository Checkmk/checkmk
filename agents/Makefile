# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

include ../defines.make

RPM_VERSION := $(subst -,_,$(VERSION))
NEW_VERSION_MAJOR := $(shell echo $(NEW_VERSION) | sed 's/\([0-9]*\.[0-9]*\)\.\(.*\)/\1/g')
NAME := check-mk-agent
DISTNAME := $(NAME)-$(VERSION)
RPM_TOPDIR := $$(pwd)/.rpm.topdir
RPM_BUILDROOT := $$(pwd)/.rpm.buildroot
RPM_PACKAGE := $(DISTNAME)-1.noarch.rpm
DEB_PACKAGE := check-mk-agent_$(VERSION)-1_all.deb

usage:
	@echo "make waitmax       -- compile waitmax.c"
	@echo "make build         -- create all files needed for \"make dist\" of Check_MK"
	@echo "make rpm           -- create RPM package of Linux agent"
	@echo "make deb           -- create DEB package of Linux agent"
	@echo "make packages      -- create RPM and DEB package of Linux agent"
	@echo "make controller    -- build the agent controller binary"

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
	sed -i 's/$$CMK_VERSION = ".*/$$CMK_VERSION = "$(NEW_VERSION)"\r/' windows/plugins/*.ps1 ; \
	sed -i 's/^set CMK_VERSION=".*/set CMK_VERSION="$(NEW_VERSION)"\r/' windows/plugins/*.bat ; \
	sed -i 's/^Const CMK_VERSION = ".*/Const CMK_VERSION = "$(NEW_VERSION)"\r/' windows/plugins/*.vbs ; \
	sed -i \
	-e 's/^CMK_VERSION=".*/CMK_VERSION="$(NEW_VERSION)"/' \
	-e 's/^__version__ = ".*/__version__ = "$(NEW_VERSION)"/' \
	-e 's/^$$CMK_VERSION=".*/$$CMK_VERSION="$(NEW_VERSION)"/' \
	-e 's/^$$CMK_VERSION = ".*/$$CMK_VERSION = "$(NEW_VERSION)"/' \
	$(shell find plugins/ -maxdepth 1 -type f ! -name \*_2.py ! -name \*.checksum) ; \
	sed -i 's/say "Version: .*"/say "Version: $(NEW_VERSION)"/' check_mk_agent.openvms
	sed -i 's/^Version: .*/Version: $(NEW_VERSION)/' check_mk_agent.linux
	sed -i 's/echo "Version: [0-9.a-z-]*"/echo "Version: $(NEW_VERSION)"/g' \
	    check_mk_agent.aix \
	    check_mk_agent.freebsd \
	    check_mk_agent.hpux \
	    check_mk_agent.macosx \
	    check_mk_agent.netbsd \
	    check_mk_agent.openbsd \
	    check_mk_agent.openwrt \
	    check_mk_agent.solaris
	sed -i "s/^#define CMK_WIN_AGENT_VERSION .*/#define CMK_WIN_AGENT_VERSION \"$(NEW_VERSION)\"/" wnx/src/common/wnx_version.h

build: $(DEB_PACKAGE) $(RPM_PACKAGE) $(WIN_PACKAGE) controller

controller:
	rm -f linux/cmk-agent-ctl
	(cd cmk-agent-ctl; ../../scripts/run-cargo-command build --release) \
	&& mkdir -p linux \
	&& cp cmk-agent-ctl/target/x86_64-unknown-linux-musl/release/cmk-agent-ctl linux

packages: $(DEB_PACKAGE) $(RPM_PACKAGE)

deb: $(DEB_PACKAGE)

rpm: $(RPM_PACKAGE)

$(RPM_PACKAGE): controller waitmax
	rm -f *.rpm
	rm -rf "$(RPM_TOPDIR)" "$(RPM_BUILDROOT)"
	#
	# create build root (as tree would show it)
	mkdir -p "$(RPM_BUILDROOT)/etc/check_mk"
	install -m 644 "conffiles/super-server.cfg" "$(RPM_BUILDROOT)/etc/check_mk/super-server.cfg"
	mkdir -p "$(RPM_BUILDROOT)/usr/bin"
	mkdir -p "$(RPM_BUILDROOT)/var/lib/cmk-agent"
	install -m 755 check_mk_agent.linux "$(RPM_BUILDROOT)/usr/bin/check_mk_agent"
	install -m 755 check_mk_caching_agent.linux "$(RPM_BUILDROOT)/usr/bin/check_mk_caching_agent"
	install -m 755 linux/cmk-agent-ctl "$(RPM_BUILDROOT)/usr/bin/cmk-agent-ctl"
	install -m 755 mk-job "$(RPM_BUILDROOT)/usr/bin/mk-job"
	install -m 755 waitmax "$(RPM_BUILDROOT)/usr/bin/waitmax"
	mkdir -p "$(RPM_BUILDROOT)/usr/lib/check_mk_agent/local"
	mkdir -p "$(RPM_BUILDROOT)/usr/lib/check_mk_agent/plugins"
	mkdir -p "$(RPM_BUILDROOT)/var/lib/check_mk_agent/cache"
	mkdir -p "$(RPM_BUILDROOT)/var/lib/check_mk_agent/job"
	mkdir -p "$(RPM_BUILDROOT)/var/lib/check_mk_agent/spool"
	cp -r scripts "$(RPM_BUILDROOT)/var/lib/cmk-agent"
	mv "$(RPM_BUILDROOT)/var/lib/cmk-agent/scripts/super-server/1_xinetd/check-mk-agent" "$(RPM_BUILDROOT)/etc/check_mk/xinetd-service-template.cfg"
	# use this build root, and build
	rpmbuild -bb --buildroot "$(RPM_BUILDROOT)" \
	    --define "_topdir $(RPM_TOPDIR)" \
	    --define "_version $(VERSION)" \
	    --define "_rpm_version $(RPM_VERSION)" \
	    $(NAME).spec
	mv -v $(RPM_TOPDIR)/RPMS/*/* $(RPM_PACKAGE)
	rm -rf $(RPM_TOPDIR) $(RPM_BUILDROOT)


# TODO: Replace alien usage. Debian packages should be created just like the bakery does
#       Keep in mind that we still need to use gz compression by default for the agent
#       packages.
$(DEB_PACKAGE): $(RPM_PACKAGE)
	@echo "Sorry. Debian packages currently via alien"
	rm -f *.deb
	set -e ; \
	if [ -z "$$FAKEROOTKEY" ]; then \
	    FAKEROOT=fakeroot ; \
	else \
	    FAKEROOT= ; \
	fi ; \
	$$FAKEROOT alien --scripts -k --to-deb $(RPM_PACKAGE)
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
	tar czf control.tar.gz $(TAROPTS) -C ctrl . && \
	xz --decompress data.tar.xz && \
	gzip data.tar && \
	ar r ../$(DEB_PACKAGE) debian-binary control.tar.gz data.tar.gz
	rm -rf deb-unpack

clean:
	rm -rf *~ waitmax *.rpm *.deb linux/cmk-agent-ctl
