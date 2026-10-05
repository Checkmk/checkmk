# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

include ../defines.make
include ../artifacts.make

AGENTS_DIR := $(REPO_PATH)/agents
NEW_VERSION_MAJOR := $(shell echo $(NEW_VERSION) | sed 's/\([0-9]*\.[0-9]*\)\.\(.*\)/\1/g')

HOST_PACKAGES_DIR := $(REPO_PATH)/packages

AGENT_CTL := $(AGENTS_DIR)/linux/cmk-agent-ctl
AGENT_CTL_GZ := $(AGENT_CTL).gz
AGENT_CTL_DIR := $(HOST_PACKAGES_DIR)/cmk-agent-ctl

usage:
	@echo "make waitmax       -- compile waitmax.c"

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
	$(shell find plugins/ -maxdepth 1 -type f) ; \
	#
	# This really has to stop. But for now we need to make it work, so this is what is going on:
	# Plugin families in the cmk.plugins _namespace_ can contain windows *and* linux agent plugins,
	# special agents and active checks. While we know their entry points, the implementation
	# (including the version definition) could be anywhere, so we have to check *a lot* of files.
	# We combine the sed expressions for linux and windows plugins, and run them on these 3 folders.
	# To limit the number of files, we use grep rather than find (otherwise we'll hit the
	# limit on the length of the argument list).
	sed -i \
	-e 's/$$CMK_VERSION = ".*/$$CMK_VERSION = "$(NEW_VERSION)"\r/' \
	-e 's/\$$CMK_VERSION = ".*/\$$CMK_VERSION = "$(NEW_VERSION)"\r/' \
	-e 's/^set CMK_VERSION *=".*/set CMK_VERSION="$(NEW_VERSION)"\r/' \
	-e 's/^Const CMK_VERSION = ".*/Const CMK_VERSION = "$(NEW_VERSION)"\r/' \
	-e 's/^CMK_VERSION=".*/CMK_VERSION="$(NEW_VERSION)"/' \
	-e 's/^__version__ = ".*/__version__ = "$(NEW_VERSION)"/' \
	-e 's/^$$CMK_VERSION=".*/$$CMK_VERSION="$(NEW_VERSION)"/' \
	-e 's/^$$CMK_VERSION = ".*/$$CMK_VERSION = "$(NEW_VERSION)"/' \
	$(shell grep -rl -e CMK_VERSION -e __version__ $(REPO_PATH)/cmk/plugins) \
	$(shell grep -rl -e CMK_VERSION -e __version__ $(REPO_PATH)/packages/cmk-plugins/cmk/plugins) \
	$(shell grep -rl -e CMK_VERSION -e __version__ $(REPO_PATH)/non-free/packages/cmk-plugins-nonfree/cmk/plugins) ; \
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
	sed -i "s/^#define CMK_WIN_AGENT_VERSION .*/#define CMK_WIN_AGENT_VERSION \"$(NEW_VERSION)\"/" wnx/include/common/wnx_version.h
	sed -i 's/std::wstring_view kAgentProductName.*;/std::wstring_view kAgentProductName{L"Checkmk Agent $(NEW_VERSION_MAJOR)"};/' wnx/include/wnx/install_api.h
	sed -i 's/define ProductName = "Checkmk Agent [^"]*"/define ProductName = "Checkmk Agent $(NEW_VERSION_MAJOR)"/' wnx/install/version.wxi
	sed -i 's/define ServiceDescription = "Checkmk monitoring agent service - [^"]*"/define ServiceDescription = "Checkmk monitoring agent service - $(NEW_VERSION_MAJOR)"/' wnx/install/Product.wxs

.PHONY: $(AGENT_CTL)
$(AGENT_CTL):
	bazel build //packages/cmk-agent-ctl:cmk-agent-ctl-musl --cmk_version=$(NEW_VERSION)
	mkdir -p linux
	install -m 755 $(REPO_PATH)/bazel-bin/packages/cmk-agent-ctl/cmk-agent-ctl-musl $(AGENT_CTL)

$(AGENT_CTL_GZ): $(AGENT_CTL)
	gzip --best --keep --force $(AGENT_CTL)

clean:
	rm -rf *~ waitmax $(AGENT_CTL) $(AGENT_CTL_GZ)
