# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

#
# Builds CPython for Windows as zip file
# Expected some Python installed, used by python build toolchain
# Expected python.exe is python3 reasonably updated
#
# Usage:
#  make 

# internal dirs:
PYTHON_SRC_DIR     := python
PYTHON_TMP_DIR     := tmp
PYTHON_SYSTEM_EXE  := python.exe

PYTHON_INSTALL_DIR := $(PYTHON_TMP_DIR)\to_install
PYTHON_SAVE_DIR    := $(PYTHON_TMP_DIR)\to_save

# external paths
ROOT_CMK_PATH      := ..\..\..
OMD_PACKAGES_DIR   := $(ROOT_CMK_PATH)\omd\packages\cpython
ARTEFACTS_DIR      := $(ROOT_CMK_PATH)\artefacts
SRC_PIPFILE_DIR    := $(ROOT_CMK_PATH)\virtual-envs\windows\3.8

# names
OMD_PYTHON_NAME    := cpython-3.8
PYTHON_MODULE_NAME := python-3.8.zip

# files
PYTHON_TIMESTAMP   := $(PYTHON_SRC_DIR)\$(OMD_PYTHON_NAME).timestamp
OMD_PYTHON_PACKAGE := $(OMD_PACKAGES_DIR)\$(OMD_PYTHON_NAME).zip

PYTHON_INSTALLER   := $(PYTHON_TMP_DIR)\out\win32\python-3.8.5.exe
SRC_PIPFILE        := $(SRC_PIPFILE_DIR)\Pipfile

PYTHON_PIPFILE     := $(PYTHON_SAVE_DIR)\Pipfile
PYTHON_PIPFILE_LOCK:= $(PYTHON_PIPFILE).lock

ARTEFACT_MODULE    := $(ARTEFACTS_DIR)\$(PYTHON_MODULE_NAME)
PYTHON_MODULE      := $(PYTHON_TMP_DIR)\$(PYTHON_MODULE_NAME)



.PHONY: clean venv 7zip unpack build python_install

.DEFAULT_GOAL = build

$(PYTHON_TIMESTAMP): $(OMD_PYTHON_PACKAGE) ## deploying python sources
	@powershell Write-Host "$@ is to be processed" -foreground White
	@if not exist $< powershell Write-Host -foreground Red "$< absent" && exit 1
	@powershell Write-Host -foreground Green "Unpacking $< ..."
	@7z x -y -mmt4 -o$(PYTHON_SRC_DIR) $< 
	@type nul >>$@ && powershell (ls $@).LastWriteTime = Get-Date   # windows touch
	@powershell Write-Host -foreground Green "Done"


7zip: ## checking for 7 zip
	@powershell Write-Host "Target $@" -foreground white
	@7z -? > nul
	@if "%errorlevel%" NEQ "0" powershell Write-Host "7zip must be installed: use choco or windows_setup" -Foreground Red && exit /b 1
	@powershell Write-Host "7zip is installed. This is good" -Foreground Green
	
unpack: 7zip $(PYTHON_TIMESTAMP) ## unpacking python sources
	@powershell Write-Host "Target $@" -foreground white
	@powershell Write-Host -foreground Green "cpython is ready to build"

$(PYTHON_INSTALLER): $(PYTHON_TIMESTAMP)    ## python installer
	@powershell Write-Host "Target $@" -foreground white
	@call exec_cmd.bat build_python.cmd
	@powershell Write-Host -foreground Green "Python is built"

python_install: $(PYTHON_INSTALLER)    ## python installation
	@powershell Write-Host "Target $@" -foreground white
	@call exec_cmd.bat uninstall_python.cmd
	@call exec_cmd.bat install_python.cmd
	@call exec_cmd.bat upgrade_pip.cmd
	@call exec_cmd.bat install_pipenv.cmd
	@call exec_cmd.bat save_python.cmd
	@call exec_cmd.bat uninstall_python.cmd
	@powershell Write-Host -foreground Green "Python is saved"


$(PYTHON_PIPFILE): $(SRC_PIPFILE) ## pifile copy and patch
	@powershell Write-Host "Making pipfile on target $@" -foreground white
	@if not exist $(PYTHON_SAVE_DIR) powershell "$(PYTHON_SAVE_DIR) absent" && exit 3
	@copy /Y $< $@
	@$(PYTHON_SYSTEM_EXE) patch_pipfile.py $@

$(PYTHON_PIPFILE_LOCK): $(PYTHON_PIPFILE) ## piplock building
	@powershell Write-Host "Target $@" -foreground white
	@call exec_cmd.bat build_pipfile_lock.cmd

venv: python_install $(PYTHON_PIPFILE_LOCK) ## venv building
	@powershell Write-Host "Target '$@'" -foreground white
	@call exec_cmd.bat build_environment.cmd
	@call exec_cmd.bat clean_environment.cmd
	@call exec_cmd.bat patch_environment.cmd
	
	
$(PYTHON_MODULE): venv ## zipping venv
	@powershell Write-Host "+Target $@" -foreground white
	@cd $(PYTHON_SAVE_DIR) && 7z a -r -tzip -y -stl -mmt4 ..\$(PYTHON_MODULE_NAME) *.*

$(ARTEFACT_MODULE): $(PYTHON_MODULE) ## copy to artefacts
	@powershell Write-Host "+Target $@" -foreground white
	@if not exist $(ARTEFACTS_DIR) mkdir $(ARTEFACTS_DIR) 2> nul
	@copy /Y $< $@ 

build: unpack $(ARTEFACT_MODULE) ## building all
	@powershell Write-Host -foreground Green "Build finished, uninstalling python"
	@echo NOT REQUIRED call exec_cmd.bat uninstall_python.cmd
	

clean:
	@powershell Write-Host -foreground Green "Cleaninn..."
	@call exec_cmd.bat uninstall.cmd
	@rmdir /s/q .\$(PYTHON_TMP_DIR)
	@rmdir /s/q .\$(PYTHON_SRC_DIR) 

