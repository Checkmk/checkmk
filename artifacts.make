# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

CHECK_MK_ANNOUNCE_VERSION=$(VERSION)-$(shell git rev-parse --short=12 HEAD)
CHECK_MK_ANNOUNCE_TAR_FILE := announce-$(CHECK_MK_ANNOUNCE_VERSION).tar.gz
CHECK_MK_ANNOUNCE_TAR := $(REPO_PATH)/$(CHECK_MK_ANNOUNCE_TAR_FILE)
CHECK_MK_ANNOUNCE_FOLDER := $(REPO_PATH)/announce
CHECK_MK_ANNOUNCE_MD := $(CHECK_MK_ANNOUNCE_FOLDER)/announce-$(CHECK_MK_ANNOUNCE_VERSION).md
CHECK_MK_ANNOUNCE_TXT := $(CHECK_MK_ANNOUNCE_FOLDER)/announce-$(CHECK_MK_ANNOUNCE_VERSION).txt

# These artifacts are created independent of the distro the Checkmk package is
# built on either by an "upstream job" or while creating the source package
SOURCE_BUILT_LINUX_AGENTS := \
	$(REPO_PATH)/agents/check-mk-agent-$(VERSION)-1.noarch.rpm \
	$(REPO_PATH)/agents/check-mk-agent_$(VERSION)-1_all.deb \
	$(REPO_PATH)/agents/linux/mk-sql \
	$(REPO_PATH)/agents/linux/cmk-agent-ctl \
	$(REPO_PATH)/agents/linux/cmk-agent-ctl.gz
ifeq ($(ENTERPRISE),yes)
SOURCE_BUILT_AGENT_UPDATER := \
	$(REPO_PATH)/non-free/packages/cmk-update-agent/cmk-update-agent \
	$(REPO_PATH)/non-free/packages/cmk-update-agent/cmk-update-agent-32
else
SOURCE_BUILT_AGENT_UPDATER :=
endif
SOURCE_BUILT_OHM := \
	$(REPO_PATH)/agents/windows/OpenHardwareMonitorCLI.exe \
	$(REPO_PATH)/agents/windows/OpenHardwareMonitorLib.dll
SOURCE_BUILT_EXT := $(REPO_PATH)/agents/windows/robotmk_ext.exe
SOURCE_BUILT_MK_SQL := $(REPO_PATH)/agents/windows/mk-sql.exe
SOURCE_BUILT_WINDOWS := \
	$(REPO_PATH)/agents/windows/check_mk_agent.msi \
	$(REPO_PATH)/agents/windows/python-3.cab \
	$(REPO_PATH)/agents/windows/windows_files_hashes.txt \
	$(REPO_PATH)/agents/windows/check_mk.user.yml \
	$(REPO_PATH)/agents/windows/unsign-msi.patch
SOURCE_BUILT_AGENTS := \
	$(SOURCE_BUILT_LINUX_AGENTS) \
	$(SOURCE_BUILT_OHM) \
	$(SOURCE_BUILT_EXT) \
	$(SOURCE_BUILT_MK_SQL) \
	$(SOURCE_BUILT_WINDOWS)
SOURCE_BUILT_ARTIFACTS := \
	$(SOURCE_BUILT_AGENTS) \
	$(SOURCE_BUILT_AGENT_UPDATER)
print-artifacts-%:
	@echo '$($*)'
