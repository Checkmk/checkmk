# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

INTEGRATION_TIMESTAMP   := results\integration.timestamp

# Pythons for deploy
PYTHON_1		:= ..\..\..\..\artefacts\python-3.8.zip
PYTHON_2		:= ..\..\..\..\artefacts\python-3.4.zip

# Scripts to be compatible with pythons
SCRIPT_1		:= ..\..\..\..\enterprise\agents\plugins\cmk_update_agent.py
SCRIPT_2		:= ..\..\..\plugins\mk_logwatch.py
SCRIPT_3		:= ..\..\..\plugins\mk_jolokia.py

.PHONY: test-integration test-integration-force

$(INTEGRATION_TIMESTAMP): $(PYTHON_1) $(PYTHON_2) $(SCRIPT_1) $(SCRIPT_2) $(SCRIPT_3)
	@powershell Write-Host "Integration tests starting" -foreground cyan
	@cd integration && pytest.exe
	@powershell Write-Host "success" -foreground green
	@if not exist results mkdir results >nul 2>nul
	@type nul >>$(INTEGRATION_TIMESTAMP) && powershell (ls $@).LastWriteTime = Get-Date   # windows touch

test-integration: $(INTEGRATION_TIMESTAMP)
	@powershell Write-Host "Integration tests finished" -foreground green

test-integration-force:
	@del /Q $(INTEGRATION_TIMESTAMP)
	@make test-integration
