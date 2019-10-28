#
# Build script for the Windows Frozen Binaries
# Expected Python 2.7 installed in certain folders(can be and must be done with choco)
#
# Usage:
#  make frozen_binaries

PYTHON_SCRIPTS_DIR = c:\Python27\Scripts
PYTHON_DIR = c:\Python27
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
	@call python_packages.cmd
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

$(MKLOGWATCH_EXE_BUILD): $(SRC_PATH)\mk_logwatch
	@powershell Write-Host "Starting the build of mklogwatch" -Foreground Green
	@call bld_fb.cmd $?
	@if NOT exist $(MKLOGWATCH_EXE_BUILD) powershell Write-Host "$(MKLOGWATCH_EXE_BUILD) not found" -Foreground Red && exit /b 1

mkjolokia: $(MKJOLOKIA_EXE_BUILD)
	@copy $(MKJOLOKIA_EXE_BUILD) $(ARTE_PATH)

$(MKJOLOKIA_EXE_BUILD): $(SRC_PATH)\mk_jolokia.py
	@powershell Write-Host "Starting the build of mkjolokia" -Foreground Green
	@call bld_fb.cmd $? "--hidden-import=cffi"
	@if NOT exist $(MKJOLOKIA_EXE_BUILD) powershell Write-Host "$(MKJOLOKIA_EXE_BUILD) not found" -Foreground Red && exit /b 1

	
frozen_binaries: check_install mklogwatch mkjolokia 
	@powershell Write-Host "Finished" -Foreground Green

clean:
	@rmdir /s/q build\fb 
	@del $(MKJOLOKIA_EXE)
	@del $(MKLOGWATCH_EXE)




#build: mk_logwatch.exe

#mk_logwatch.exe:  