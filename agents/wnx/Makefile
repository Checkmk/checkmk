# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

#
# Patch MSI file with new production code
# Expects, that any Python 3 installed
#
# Usage:
#  make msi_patch


TOP_SRC_DIR     := ..\..
ARTE_PATH       = $(TOP_SRC_DIR)\artefacts

MSI_STATE_FILE 	= $(ARTE_PATH)\msi_state_data.yml
MSI_AGENT_FILE 	= $(ARTE_PATH)\check_mk_agent.msi
MSI_PATCH_FILE 	= $(TOP_SRC_DIR)\cmk\utils\msi_patch.py

EXTLIBS         := extlibs

PACKAGE_ASIO 	:= $(TOP_SRC_DIR)\third_party\asio
# ATTENTION: this value is hardcoded in the vcxproj files - fix it, please, too
ASIO_VERSION 	:= asio-1.24.0-patched

PACKAGE_FMT     := $(TOP_SRC_DIR)\third_party\fmt
# ATTENTION: this value is hardcoded in the vcxproj files - fix it, please, too
FMT_VERSION    := fmt-11.1.4

PACKAGE_OHM     := $(TOP_SRC_DIR)\third_party\openhardwaremonitor
# ATTENTION: this value is hardcoded in the vcxproj files - fix it, please, too
OHM_VERSION    := openhardwaremonitor-0.9.6

PACKAGE_SIMPLEINI     := $(TOP_SRC_DIR)\third_party\simpleini
# ATTENTION: this value is hardcoded in the vcxproj files - fix it, please, too
SIMPLEINI_VERSION     := simpleini-2af65fc

PACKAGE_YAML   := $(TOP_SRC_DIR)\third_party\yaml-cpp
# ATTENTION: this value is hardcoded in the vcxproj files - fix it, please, too
YAML_VERSION   := yaml-cpp-0.8.0

PACKAGE_GTEST   := $(TOP_SRC_DIR)\third_party\googletest
# ATTENTION: this value is hardcoded in the vcxproj files - fix it, please, too
GTEST_VERSION   := googletest-e90fe24856-patched



$(MSI_STATE_FILE): $(MSI_AGENT_FILE) $(MSI_PATCH_FILE)
	@powershell Write-Host "Patching '$(MSI_AGENT_FILE)'" -Foreground Green
	@del $(MSI_STATE_FILE)  2> nul
	@python.exe --version
	python.exe $(MSI_PATCH_FILE) 1033 $(MSI_AGENT_FILE) $(MSI_STATE_FILE)

msi_patch: $(MSI_STATE_FILE)
	@if NOT exist "$(MSI_STATE_FILE)" powershell Write-Host "Patch of '$(MSI_AGENT_FILE)' failed" -Foreground Red && exit /b 1
	@powershell Write-Host "Patch of '$(MSI_AGENT_FILE)' success" -Foreground Green
	@type $(MSI_STATE_FILE)
	@exit /b 0

clean_artifacts:
	@set arte=$(ARTE_PATH)&& call scripts\clean_artifacts.cmd


setversion:
	@python patch_windows_agent_version.py include\common\wnx_version.h $(NEW_VERSION)

install_extlibs: $(EXTLIBS)\$(ASIO_VERSION) $(EXTLIBS)\$(FMT_VERSION) $(EXTLIBS)\$(OHM_VERSION) $(EXTLIBS)\$(SIMPLEINI_VERSION) $(EXTLIBS)\$(YAML_VERSION) $(EXTLIBS)\$(GTEST_VERSION)

$(EXTLIBS)\$(ASIO_VERSION): $(PACKAGE_ASIO)/$(ASIO_VERSION).tar.gz
	@if "$(EXTLIBS)" == "" echo bad extlibs && exit 1
	@if "$(ASIO_VERSION)" == "" echo bad asio_version && exit 1
	@rmdir /s /q .\$@ 2> nul || echo "directory $@ is absent, ok!"
	@scripts\unpack_package.cmd 7z $(PACKAGE_ASIO) $(ASIO_VERSION) $(EXTLIBS) $(ASIO_VERSION) *
	@powershell (Get-Item $@).LastWriteTime = (Get-Date)

$(EXTLIBS)\$(FMT_VERSION): $(PACKAGE_FMT)/$(FMT_VERSION).tar.gz
	@if "$(EXTLIBS)" == "" echo bad extlibs && exit 1
	@if "$(FMT_VERSION)" == "" echo bad fmt_version && exit 1
	@rmdir /s /q .\$@ 2> nul || echo "directory $@ is absent, ok!"
	@scripts\unpack_package.cmd 7z $(PACKAGE_FMT) $(FMT_VERSION) $(EXTLIBS) $(FMT_VERSION) *
	@powershell (Get-Item $@).LastWriteTime = (Get-Date)

$(EXTLIBS)\$(OHM_VERSION): $(PACKAGE_OHM)/$(OHM_VERSION).zip
	@if "$(EXTLIBS)" == "" echo bad extlibs && exit 1
	@if "$(OHM_VERSION)" == "" echo bad ohm_version && exit 1
	@rmdir /s /q .\$@ 2> nul || echo "directory $@ is absent, ok!"
	@7z x $? -o$(EXTLIBS) > nul 2>&1
	@powershell (Get-Item $@).LastWriteTime = (Get-Date)

$(EXTLIBS)\$(SIMPLEINI_VERSION): $(PACKAGE_SIMPLEINI)/$(SIMPLEINI_VERSION).tar.gz
	@if "$(EXTLIBS)" == "" echo bad extlibs && exit 1
	@if "$(SIMPLEINI_VERSION)" == "" echo bad simpleini_version && exit 1
	@rmdir /s /q .\$@ 2> nul || echo "directory $@ is absent, ok!"
	@scripts\unpack_package.cmd 7z $(PACKAGE_SIMPLEINI) $(SIMPLEINI_VERSION) $(EXTLIBS) $(SIMPLEINI_VERSION) $(SIMPLEINI_VERSION)
	@powershell (Get-Item $@).LastWriteTime = (Get-Date)

$(EXTLIBS)\$(YAML_VERSION): $(PACKAGE_YAML)/$(YAML_VERSION).tar.gz
	@if "$(EXTLIBS)" == "" echo bad extlibs && exit 1
	@if "$(YAML_VERSION)" == "" echo bad yaml-cpp && exit 1
	@rmdir /s /q .\$@ 2> nul || echo "directory $@ is absent, ok!"
	@scripts\unpack_package.cmd 7z $(PACKAGE_YAML) $(YAML_VERSION) $(EXTLIBS) $(YAML_VERSION) *
	@powershell (Get-Item $@).LastWriteTime = (Get-Date)

$(EXTLIBS)\$(GTEST_VERSION): $(PACKAGE_GTEST)/$(GTEST_VERSION).tar.gz
	@if "$(EXTLIBS)" == "" echo bad extlibs && exit 1
	@if "$(GTEST_VERSION)" == "" echo bad yaml-cpp && exit 1
	@rmdir /s /q .\$@ 2> nul || echo "directory $@ is absent, ok!"
	@scripts\unpack_package.cmd 7z $(PACKAGE_GTEST) $(GTEST_VERSION) $(EXTLIBS) $(GTEST_VERSION) *
	@powershell (Get-Item $@).LastWriteTime = (Get-Date)



