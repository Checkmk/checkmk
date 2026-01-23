# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

include ../defines.make
include ../artifacts.make

AGENTS_DIR := $(REPO_PATH)/agents
SPECIAL_AGENTS_DIR := $(REPO_PATH)/cmk/special_agents
RPM_VERSION := $(subst -,_,$(VERSION))
NEW_VERSION_MAJOR := $(shell echo $(NEW_VERSION) | sed 's/\([0-9]*\.[0-9]*\)\.\(.*\)/\1/g')
NAME := check-mk-agent
BUILDROOT := $(AGENTS_DIR)/.buildroot
BUILDROOT_STAMP := $(AGENTS_DIR)/.buildroot.stamp
RPM_TOPDIR := $(AGENTS_DIR)/.rpm.topdir
RPM_BUILDDIR := $(AGENTS_DIR)/.rpm.builddir
RPM_PACKAGE := $(AGENTS_DIR)/check-mk-agent.noarch.rpm
DEB_PACKAGE := $(AGENTS_DIR)/check-mk-agent_all.deb
DEB_TOPDIR := $(AGENTS_DIR)/debian
DEB_BUILDDIR := $(AGENTS_DIR)/debian/.build

HOST_PACKAGES_DIR := $(REPO_PATH)/packages

AGENT_CTL := $(AGENTS_DIR)/linux/cmk-agent-ctl
AGENT_CTL_GZ := $(AGENT_CTL).gz
AGENT_CTL_AARCH64 := $(AGENTS_DIR)/linux/cmk-agent-ctl-aarch64
AGENT_CTL_AARCH64_GZ := $(AGENT_CTL_AARCH64).gz

AGENT_CTL_DIR := $(HOST_PACKAGES_DIR)/cmk-agent-ctl

MK_SQL := $(AGENTS_DIR)/linux/mk-sql
MK_SQL_DIR := $(HOST_PACKAGES_DIR)/mk-sql

BUILDROOT_DEPS := \
	conffiles/super-server.cfg \
	check_mk_agent.linux \
	check_mk_caching_agent.linux \
	$(MK_SQL) \
	$(AGENT_CTL_GZ) \
	$(AGENT_CTL_AARCH64) \
	$(AGENT_CTL_AARCH64_GZ) \
	mk-job \
	waitmax \
	$(shell find scripts/ -type f)

usage:
	@echo "make waitmax       -- compile waitmax.c"
	@echo "make build         -- create all files needed for \"make dist\" of Check_MK"
	@echo "make rpm           -- create RPM package of Linux agent"
	@echo "make deb           -- create DEB package of Linux agent"
	@echo "make packages      -- create RPM and DEB package of Linux agent"

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
	# IMPORTANT do not version bazelized packages here.  Bazel can set the
	# version natively.
	sed -i \
	-e 's/$$CMK_VERSION = ".*/$$CMK_VERSION = "$(NEW_VERSION)"\r/' \
	-e 's/\$$CMK_VERSION = ".*/\$$CMK_VERSION = "$(NEW_VERSION)"\r/' \
	-e 's/^set CMK_VERSION *=".*/set CMK_VERSION="$(NEW_VERSION)"\r/' \
	-e 's/^Const CMK_VERSION = ".*/Const CMK_VERSION = "$(NEW_VERSION)"\r/' \
	-e 's/\(^[[:space:]]*\)Version: [0-9.a-z-]*/\1Version: $(NEW_VERSION)/' \
	$(shell find $(REPO_PATH)/agents/windows/plugins -type f) \
	$(shell find $(REPO_PATH)/cmk/plugins -path "*/cmk/plugins/*/agents/*" -type f) ;
	sed -i \
	-e 's/^CMK_VERSION=".*/CMK_VERSION="$(NEW_VERSION)"/' \
	-e 's/^__version__ = ".*/__version__ = "$(NEW_VERSION)"/' \
	-e 's/^$$CMK_VERSION=".*/$$CMK_VERSION="$(NEW_VERSION)"/' \
	-e 's/^$$CMK_VERSION = ".*/$$CMK_VERSION = "$(NEW_VERSION)"/' \
	$(shell find plugins/ -maxdepth 1 -type f) \
	$(shell find $(REPO_PATH)/cmk/plugins -path "*/cmk/plugins/*/agents/*" -type f) \
	$(shell find $(REPO_PATH)/packages/cmk-plugins/cmk/plugins -type f) ; \
	sed -i 's/say "Version: .*"/say "Version: $(NEW_VERSION)"/' check_mk_agent.openvms
	sed -i 's/echo "Version: [0-9.a-z-]*"/echo "Version: $(NEW_VERSION)"/g' \
	    check_mk_agent.aix \
	    check_mk_agent.linux \
	    check_mk_agent.freebsd \
	    check_mk_agent.hpux \
	    check_mk_agent.macosx \
	    check_mk_agent.netbsd \
	    check_mk_agent.openbsd \
	    check_mk_agent.openwrt \
	    check_mk_agent.solaris
	sed -i 's/__version__ = \"[0-9.a-z-]*\"/__version__ = \"$(NEW_VERSION)\"/g' \
		$(shell find $(SPECIAL_AGENTS_DIR) -name "*agent_*.py" -type f) \
		$(shell find $(REPO_PATH)/cmk/plugins -name "agent*.py" -type f)
	sed -i "s/^#define CMK_WIN_AGENT_VERSION .*/#define CMK_WIN_AGENT_VERSION \"$(NEW_VERSION)\"/" wnx/include/common/wnx_version.h
	sed -i 's/std::wstring_view kAgentProductName.*;/std::wstring_view kAgentProductName{L"Checkmk Agent $(NEW_VERSION_MAJOR)"};/' wnx/include/wnx/install_api.h
	sed -i 's/define ProductName = "Checkmk Agent [^"]*"/define ProductName = "Checkmk Agent $(NEW_VERSION_MAJOR)"/' wnx/install/version.wxi
	sed -i 's/define ServiceDescription = "Checkmk monitoring agent service - [^"]*"/define ServiceDescription = "Checkmk monitoring agent service - $(NEW_VERSION_MAJOR)"/' wnx/install/Product.wxs

build: $(DEB_PACKAGE) $(RPM_PACKAGE) $(WIN_PACKAGE) $(AGENT_CTL) $(AGENT_CTL_AARCH64) $(MK_SQL)

.PHONY: $(AGENT_CTL)
$(AGENT_CTL):
	bazel build //packages/cmk-agent-ctl:cmk-agent-ctl-musl --compilation_mode=opt --cmk_version=$(NEW_VERSION)
	mkdir -p linux
	install -m 755 $(REPO_PATH)/bazel-bin/packages/cmk-agent-ctl/cmk-agent-ctl-musl $(AGENT_CTL)

$(AGENT_CTL_GZ): $(AGENT_CTL)
	gzip --best --keep --force $(AGENT_CTL)

.PHONY: $(AGENT_CTL_AARCH64)
$(AGENT_CTL_AARCH64):
	bazel build //packages/cmk-agent-ctl:cmk-agent-ctl-musl-aarch64 --compilation_mode=opt --cmk_version=$(NEW_VERSION)
	mkdir -p linux
	install -m 755 $(REPO_PATH)/bazel-bin/packages/cmk-agent-ctl/cmk-agent-ctl-musl-aarch64 $(AGENT_CTL_AARCH64)

$(AGENT_CTL_AARCH64_GZ): $(AGENT_CTL_AARCH64)
	gzip --best --keep --force $(AGENT_CTL_AARCH64)

$(MK_SQL):
	bazel build //packages/mk-sql:mk-sql-musl --compilation_mode=opt --cmk_version=$(NEW_VERSION)
	mkdir -p linux
	install -m 755 $(REPO_PATH)/bazel-bin/packages/mk-sql/mk-sql-musl $(MK_SQL)

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
	rm "$(DEB_BUILDDIR)" -rf
	mkdir -p "$(DEB_BUILDDIR)/control"
	install -m 644 "$(DEB_TOPDIR)/control/conffiles" "$(DEB_BUILDDIR)/control"
	install -m 644 "$(DEB_TOPDIR)/control/control" "$(DEB_BUILDDIR)/control"
	install -m 644 "$(DEB_TOPDIR)/control/debian-binary" "$(DEB_BUILDDIR)/control"
	install -m 755 "$(DEB_TOPDIR)/control/postinst" "$(DEB_BUILDDIR)/control"
	install -m 755 "$(DEB_TOPDIR)/control/preinst" "$(DEB_BUILDDIR)/control"
	install -m 755 "$(DEB_TOPDIR)/control/prerm" "$(DEB_BUILDDIR)/control"
	install -m 644 /dev/null "$(DEB_BUILDDIR)/control/md5sum"
	cd $(BUILDROOT); find . -type f | while read -r filename; do \
	    md5sum "$${filename}" | sed 's|./||' >> "$(DEB_BUILDDIR)/control/md5sum"; \
	done
	sed \
	    -e 's|\(Version:\).*|\1 $(VERSION)-1|' \
	    -e 's|\(Installed-Size:\).*|\1 '"$$(du $(BUILDROOT) -s -B1024 | cut -f1)"'|' \
	    "$(DEB_TOPDIR)/control/control" > "$(DEB_BUILDDIR)/control/control"
	# gnu formatted tar
	cd "$(BUILDROOT)"; tar -cz --group=0 --owner=0 -f "$(DEB_BUILDDIR)/data.tar.gz" .
	cd "$(DEB_BUILDDIR)/control"; tar -cz --group=0 --owner=0 -f "$(DEB_BUILDDIR)/control.tar.gz" .
	cd "$(DEB_TOPDIR)"; ar cr "$(DEB_PACKAGE)" "control/debian-binary" "$(DEB_BUILDDIR)/control.tar.gz" "$(DEB_BUILDDIR)/data.tar.gz"
	rm $(DEB_BUILDDIR) -rf

$(BUILDROOT_STAMP): $(BUILDROOT_DEPS)
	mkdir -p "$(BUILDROOT)/etc/check_mk"
	install -m 644 "conffiles/super-server.cfg" "$(BUILDROOT)/etc/check_mk/super-server.cfg"
	mkdir -p "$(BUILDROOT)/usr/bin"
	mkdir -p "$(BUILDROOT)/var/lib/cmk-agent"
	install -m 755 check_mk_agent.linux "$(BUILDROOT)/usr/bin/check_mk_agent"
	install -m 755 check_mk_caching_agent.linux "$(BUILDROOT)/usr/bin/check_mk_caching_agent"
	install -m 640 $(AGENT_CTL_GZ) "$(BUILDROOT)/var/lib/cmk-agent/cmk-agent-ctl.gz"
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
	rm -rf *~ waitmax *.rpm *.deb $(AGENT_CTL) $(AGENT_CTL_GZ) $(AGENT_CTL_AARCH64) "$(BUILDROOT)" "$(BUILDROOT_STAMP)" "$(DEB_BUILDDIR)" "$(RPM_BUILDDIR)" "$(RPM_TOPDIR)"
