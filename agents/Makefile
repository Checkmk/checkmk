# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

include ../defines.make
include ../artifacts.make

AGENTS_DIR := $(REPO_PATH)/agents
RPM_VERSION := $(subst -,_,$(VERSION))
NEW_VERSION_MAJOR := $(shell echo $(NEW_VERSION) | sed 's/\([0-9]*\.[0-9]*\)\.\(.*\)/\1/g')
NAME := check-mk-agent
DISTNAME := $(NAME)-$(VERSION)
BUILDROOT := $(AGENTS_DIR)/.buildroot
BUILDROOT_STAMP := $(AGENTS_DIR)/.buildroot.stamp
RPM_TOPDIR := $(AGENTS_DIR)/.rpm.topdir
RPM_BUILDDIR := $(AGENTS_DIR)/.rpm.builddir
RPM_PACKAGE := $(AGENTS_DIR)/$(DISTNAME)-1.noarch.rpm
DEB_PACKAGE := $(AGENTS_DIR)/check-mk-agent_$(VERSION)-1_all.deb
DEB_TOPDIR := $(AGENTS_DIR)/debian
DEB_BUILDDIR := $(AGENTS_DIR)/debian/.build

AGENT_CTL := $(AGENTS_DIR)/linux/cmk-agent-ctl
AGENT_CTL_GZ := $(AGENTS_DIR)/linux/cmk-agent-ctl.gz
AGENT_CTL_CARGO_OUT := cmk-agent-ctl/target/x86_64-unknown-linux-musl/release/cmk-agent-ctl
AGENT_CTL_DEPS := cmk-agent-ctl/Cargo.lock \
	cmk-agent-ctl/Cargo.toml \
	$(wildcard cmk-agent-ctl/src/*.rs) \
	$(wildcard cmk-agent-ctl/src/configuration/*.rs) \
	$(wildcard cmk-agent-ctl/src/modes/*.rs) \
	$(wildcard cmk-agent-ctl/src/monitoring_data/*.rs)

BUILDROOT_DEPS := \
	conffiles/super-server.cfg \
	check_mk_agent.linux \
	check_mk_caching_agent.linux \
	$(AGENT_CTL_GZ) \
	mk-job \
	waitmax \
	$(shell find scripts/ -type f)

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
	sed -i 's/pub const VERSION: &str = "[^"]*";/pub const VERSION: \&str = "$(NEW_VERSION)";/' cmk-agent-ctl/src/constants.rs

build: $(DEB_PACKAGE) $(RPM_PACKAGE) $(WIN_PACKAGE) $(AGENT_CTL)

controller: $(AGENT_CTL_GZ)

$(AGENT_CTL_CARGO_OUT): $(AGENT_CTL_DEPS)
	(cd cmk-agent-ctl; ../../scripts/run-cargo-command build --release)
	touch $(AGENT_CTL_CARGO_OUT)

$(AGENT_CTL): $(AGENT_CTL_CARGO_OUT)
	mkdir -p linux
	install -m 755 $(AGENT_CTL_CARGO_OUT) $(AGENT_CTL)
	strip $(AGENT_CTL)

$(AGENT_CTL_GZ): $(AGENT_CTL)
	gzip --best --keep --force $(AGENT_CTL)

packages: $(DEB_PACKAGE) $(RPM_PACKAGE)
deb: $(DEB_PACKAGE)
rpm: $(RPM_PACKAGE)

$(RPM_PACKAGE): $(BUILDROOT_STAMP)
	rm -f *.rpm
	rm -rf "$(RPM_TOPDIR)"
	cp -pr $(BUILDROOT) $(RPM_BUILDDIR)
	rpmbuild -bb --buildroot "$(RPM_BUILDDIR)" \
	    --define "_topdir $(RPM_TOPDIR)" \
	    --define "_version $(VERSION)" \
	    --define "_rpm_version $(RPM_VERSION)" \
	    $(NAME).spec
	mv -v $(RPM_TOPDIR)/RPMS/*/* $(RPM_PACKAGE)
	rm -rf $(RPM_TOPDIR) $(RPM_BUILDDIR)

$(DEB_PACKAGE): $(BUILDROOT_STAMP)
	rm $(DEB_BUILDDIR) -rf
	mkdir -p $(DEB_BUILDDIR)/control
	cp -r $(DEB_TOPDIR)/control $(DEB_BUILDDIR)/
	touch "$(DEB_BUILDDIR)/control/md5sum"
	cd $(BUILDROOT); find . -type f | while read -r filename; do \
	    md5sum "$${filename}" | sed 's|./||' >> "$(DEB_BUILDDIR)/control/md5sum"; \
	done
	sed \
	    -e 's|\(Version:\).*|\1 $(VERSION)-1|' \
	    -e 's|\(Installed-Size:\).*|\1 '"$$(du $(BUILDROOT) -s -B1024 | cut -f1)"'|' \
	    "$(DEB_TOPDIR)/control/control" > "$(DEB_BUILDDIR)/control/control"
	# gnu formatted tar
	cd "$(BUILDROOT)"; tar -cz --group=0 --owner=0 -f "$(DEB_BUILDDIR)/data.tar.gz" *
	cd "$(DEB_BUILDDIR)/control"; tar -cz --group=0 --owner=0 -f "$(DEB_BUILDDIR)/control.tar.gz" *
	cd "$(DEB_TOPDIR)"; ar cr "$(DEB_PACKAGE)" "control/debian-binary" "$(DEB_BUILDDIR)/control.tar.gz" "$(DEB_BUILDDIR)/data.tar.gz"
	rm $(DEB_BUILDDIR) -rf

$(BUILDROOT_STAMP): $(BUILDROOT_DEPS)
	mkdir -p "$(BUILDROOT)/etc/check_mk"
	install -m 644 "conffiles/super-server.cfg" "$(BUILDROOT)/etc/check_mk/super-server.cfg"
	mkdir -p "$(BUILDROOT)/usr/bin"
	mkdir -p "$(BUILDROOT)/var/lib/cmk-agent"
	install -m 755 check_mk_agent.linux "$(BUILDROOT)/usr/bin/check_mk_agent"
	install -m 755 check_mk_caching_agent.linux "$(BUILDROOT)/usr/bin/check_mk_caching_agent"
	install -m 755 $(AGENT_CTL) "$(BUILDROOT)/usr/bin/cmk-agent-ctl"
	install -m 755 mk-job "$(BUILDROOT)/usr/bin/mk-job"
	install -m 755 waitmax "$(BUILDROOT)/usr/bin/waitmax"
	mkdir -p "$(BUILDROOT)/usr/lib/check_mk_agent/local"
	mkdir -p "$(BUILDROOT)/usr/lib/check_mk_agent/plugins"
	mkdir -p "$(BUILDROOT)/var/lib/check_mk_agent/cache"
	mkdir -p "$(BUILDROOT)/var/lib/check_mk_agent/job"
	mkdir -p "$(BUILDROOT)/var/lib/check_mk_agent/spool"
	cp -r scripts "$(BUILDROOT)/var/lib/cmk-agent"
	mv "$(BUILDROOT)/var/lib/cmk-agent/scripts/super-server/1_xinetd/check-mk-agent" "$(BUILDROOT)/etc/check_mk/xinetd-service-template.cfg"
	touch $@

clean:
	rm -rf *~ waitmax *.rpm *.deb $(AGENT_CTL) $(AGENT_CTL_GZ) "$(BUILDROOT)" "$(BUILDROOT_STAMP)" "$(DEB_BUILDDIR)" "$(RPM_BUILDDIR)" "$(RPM_TOPDIR)"
