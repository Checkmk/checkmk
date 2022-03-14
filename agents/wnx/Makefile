# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

#
# Patch MSI file with new production code
# Expects, that any Python 3 installed
#
# Usage:
#  make msi_patch

ARTE_PATH = ..\..\artefacts

MSI_STATE_FILE = $(ARTE_PATH)\msi_state_data.yml
MSI_AGENT_FILE = $(ARTE_PATH)\check_mk_agent.msi
MSI_PATCH_FILE = ..\..\cmk\utils\msi_patch.py


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
	@python patch_windows_agent_version.py src\common\wnx_version.h $(NEW_VERSION)

