#
# Build script for the Windows Frozen Binaries
# Expected 32-bits Python 2.7 installed in the certain folder
#
# Usage:
#  make frozen_binaries

PYTHON_DIR = c:\Python27.32
PYTHON_SCRIPTS_DIR = $(PYTHON_DIR)\Scripts
PYINSTALLER_EXE = $(PYTHON_SCRIPTS_DIR)\pyinstaller.exe 
SRC_PATH = ..\plugins
ARTE_PATH = ..\..\artefacts
BUILD_PATH = build\fb

# targets in artefacts directory
MKLOGWATCH_EXE = $(ARTE_PATH)\mk_logwatch.exe
MKJOLOKIA_EXE = $(ARTE_PATH)\mk_jolokia.exe
#targets in build directory
MKLOGWATCH_EXE_BUILD = $(BUILD_PATH)\dist\mk_logwatch.exe
MKJOLOKIA_EXE_BUILD = $(BUILD_PATH)\dist\mk_jolokia.exe

MSI_STATE_FILE = $(ARTE_PATH)\msi_state_data.yml
MSI_AGENT_FILE = $(ARTE_PATH)\check_mk_agent.msi
MSI_PATCH_FILE = ..\..\cmk\utils\msi_patch.py



.PHONY: clean

choco_check:
	@choco -v > nul
	@if "%errorlevel%" NEQ "0" powershell Write-Host "choco must be installed" -Foreground Red && exit /b 1
	@powershell Write-Host "choco is installed. This is good" -Foreground Green

setup_software: choco_check
	@call windows_setup.cmd
	@if "%errorlevel%" NEQ "0" powershell Write-Host "Failed Windows Software Installation" -Foreground Red && exit /b 1

setup_all: choco_check setup_software
	@if NOT exist "$(PYTHON_DIR)" powershell Write-Host "$(PYTHON_DIR) not found" -Foreground Red && exit /b 1
	@if NOT exist "$(PYTHON_SCRIPTS_DIR)" powershell Write-Host "$(PYTHON_SCRIPTS_DIR) not found" -Foreground Red && exit /b 1
	@call python_packages.cmd "$(PYTHON_DIR)"
	@powershell Write-Host "----- SETUP IS FINISHED SUCCESSFULLY -----" -Foreground Green

check_install:
	@if NOT exist "$(PYTHON_DIR)" powershell Write-Host "$(PYTHON_DIR) not found" -Foreground Red && exit /b 1
	@if NOT exist "$(PYTHON_SCRIPTS_DIR)" powershell Write-Host "$(PYTHON_SCRIPTS_DIR) not found" -Foreground Red && exit /b 1
	@if NOT exist "$(PYINSTALLER_EXE)" powershell Write-Host "$(PYINSTALLER_EXE) not found" -Foreground Red && exit /b 1
	@powershell Write-Host "Installation is OK" -Foreground Green
	@if NOT exist $(BUILD_PATH) powershell Write-Host "Creating output folder" && mkdir $(BUILD_PATH)
	@powershell Write-Host "Build Folder $(BUILD_PATH) exists" -Foreground Green

mklogwatch: $(MKLOGWATCH_EXE_BUILD)
	@copy $(MKLOGWATCH_EXE_BUILD) $(ARTE_PATH)

$(MSI_STATE_FILE): $(MSI_AGENT_FILE) $(MSI_PATCH_FILE)
	@powershell Write-Host "Patching '$(MSI_AGENT_FILE)'" -Foreground Green
	@del $(MSI_STATE_FILE)  2> nul
	py -2 $(MSI_PATCH_FILE) 1033 $(MSI_AGENT_FILE) $(MSI_STATE_FILE)

msi_patch: $(MSI_STATE_FILE)
	@if NOT exist "$(MSI_STATE_FILE)" powershell Write-Host "Patch of '$(MSI_AGENT_FILE)' failed" -Foreground Red && exit /b 1
	@powershell Write-Host "Patch of '$(MSI_AGENT_FILE)' success" -Foreground Green
	@type $(MSI_STATE_FILE)
	@exit /b 0

	

$(MKLOGWATCH_EXE_BUILD): $(SRC_PATH)\mk_logwatch .\bld_fb.cmd
	@powershell Write-Host "Starting the build of mklogwatch" -Foreground Green
	@call bld_fb.cmd $(SRC_PATH)\mk_logwatch
	@if NOT exist $(MKLOGWATCH_EXE_BUILD) powershell Write-Host "$(MKLOGWATCH_EXE_BUILD) not found" -Foreground Red && exit /b 1

mkjolokia: $(MKJOLOKIA_EXE_BUILD)
	@copy $(MKJOLOKIA_EXE_BUILD) $(ARTE_PATH)

$(MKJOLOKIA_EXE_BUILD): $(SRC_PATH)\mk_jolokia.py .\bld_fb.cmd
	@powershell Write-Host "Starting the build of mkjolokia" -Foreground Green
	@call bld_fb.cmd $(SRC_PATH)\mk_jolokia.py "--hidden-import=cffi"
	@if NOT exist $(MKJOLOKIA_EXE_BUILD) powershell Write-Host "$(MKJOLOKIA_EXE_BUILD) not found" -Foreground Red && exit /b 1

	
frozen_binaries: check_install mklogwatch mkjolokia 
	@powershell Write-Host "Finished" -Foreground Green

clean:
	@rmdir /s/q build\fb 
	@del $(MKJOLOKIA_EXE)
	@del $(MKLOGWATCH_EXE)




#build: mk_logwatch.exe

#mk_logwatch.exe:  