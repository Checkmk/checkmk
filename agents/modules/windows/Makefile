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

# commandline
PY_VER             ?= 3.8
PY_SUBVER          ?= 7
MSBUILD            ?= C:\Program Files (x86)\Microsoft Visual Studio\2017\BuildTools\MSBuild\15.0\Bin\MSBuild.exe

# internal dirs:
PYTHON_SRC_DIR     := python\$(PY_VER)
PYTHON_TMP_DIR     := tmp\$(PY_VER)
PYTHON_SYSTEM_EXE  := python.exe

PYTHON_INSTALL_DIR := $(PYTHON_TMP_DIR)\to_install
PYTHON_SAVE_DIR    := $(PYTHON_TMP_DIR)\to_save

# external paths
ROOT_CMK_PATH      := ..\..\..
OMD_PACKAGES_DIR   := $(ROOT_CMK_PATH)\omd\packages\Python3
ARTEFACTS_DIR      := $(ROOT_CMK_PATH)\artefacts
SRC_PIPFILE_DIR    := $(ROOT_CMK_PATH)\virtual-envs\windows\$(PY_VER)

# names
OMD_PYTHON_NAME    := Python-$(PY_VER).$(PY_SUBVER)
PYTHON_MODULE_NAME := python-$(PY_VER).zip

# files
PYTHON_TIMESTAMP   := $(PYTHON_SRC_DIR)\$(OMD_PYTHON_NAME).timestamp
OMD_PYTHON_PACKAGE := $(OMD_PACKAGES_DIR)\$(OMD_PYTHON_NAME).tar.xz

PYTHON_INSTALLER   := $(PYTHON_TMP_DIR)\out\win32\python-$(PY_VER).$(PY_SUBVER).exe
SRC_PIPFILE        := $(SRC_PIPFILE_DIR)\Pipfile

PYTHON_PIPFILE     := $(PYTHON_SAVE_DIR)\Pipfile
PYTHON_PIPFILE_LOCK:= $(PYTHON_PIPFILE).lock

ARTEFACT_MODULE    := $(ARTEFACTS_DIR)\$(PYTHON_MODULE_NAME)
PYTHON_MODULE      := $(PYTHON_TMP_DIR)\$(PYTHON_MODULE_NAME)



.PHONY: clean venv 7zip unpack build python_install

.DEFAULT_GOAL = usage

usage:
	@powershell Write-Host "Define build parameters, for example:"
	@powershell Write-Host "make build PY_VER=3.8 PY_SUVBER=7" -foreground Green 
	@powershell Write-Host "make python_344 PY_VER=3.4 PY_SUVBER=4" -foreground Green 

$(PYTHON_TIMESTAMP): $(OMD_PYTHON_PACKAGE) ## deploying python sources
	@powershell Write-Host "$@ is to be processed" -foreground White
	@if not exist "$(MSBUILD)" powershell Write-Host -foreground Red "MS Build 2017 must be installed" && exit 1
	@if not exist $< powershell Write-Host -foreground Red "$< absent" && exit 1
	@powershell Write-Host -foreground Green "Unpacking $< ..."
	7z x -y -mmt4 -o$(PYTHON_SRC_DIR) $< 
	7z x -y -o$(PYTHON_SRC_DIR) $(PYTHON_SRC_DIR)\$(OMD_PYTHON_NAME).tar && del /S $(PYTHON_SRC_DIR)\$(OMD_PYTHON_NAME).tar
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
	@call exec_cmd.bat build_python.cmd $(PY_VER) $(PY_SUBVER)
	@powershell Write-Host -foreground Green "Python is built"

python_install: $(PYTHON_INSTALLER)    ## python installation
	@powershell Write-Host "Target $@" -foreground white
	exec_cmd.bat uninstall_python.cmd $(PY_VER) $(PY_SUBVER)
	exec_cmd.bat install_python.cmd $(PY_VER) $(PY_SUBVER)
	exec_cmd.bat upgrade_pip.cmd $(PY_VER) $(PY_SUBVER)
	exec_cmd.bat install_pipenv.cmd $(PY_VER) $(PY_SUBVER)
	exec_cmd.bat save_python.cmd $(PY_VER) $(PY_SUBVER)
	exec_cmd.bat uninstall_python.cmd $(PY_VER) $(PY_SUBVER)
	@powershell Write-Host -foreground Green "Python is saved"


$(PYTHON_PIPFILE): $(SRC_PIPFILE) ## pifile copy and patch
	@powershell Write-Host "Making pipfile on target $@" -foreground white
	@if not exist $(PYTHON_SAVE_DIR) powershell Write-Host "$(PYTHON_SAVE_DIR) absent" && exit 3
	@powershell Write-Host "Patch pipfile: $@" -foreground cyan
	@copy /Y $< $@
	@$(PYTHON_SYSTEM_EXE) patch_pipfile.py $@

$(PYTHON_PIPFILE_LOCK): $(PYTHON_PIPFILE) ## piplock building
	@powershell Write-Host "Target $@" -foreground white
	@call exec_cmd.bat build_pipfile_lock.cmd $(PY_VER) $(PY_SUBVER)

venv: python_install $(PYTHON_PIPFILE_LOCK) ## venv building
	@powershell Write-Host "Target '$@'" -foreground white
	exec_cmd.bat build_environment.cmd $(PY_VER) $(PY_SUBVER)
	exec_cmd.bat clean_environment.cmd $(PY_VER) $(PY_SUBVER)
	exec_cmd.bat patch_environment.cmd $(PY_VER) $(PY_SUBVER)
	
	
$(PYTHON_MODULE): venv ## zipping venv
	@powershell Write-Host "+Target $@" -foreground white
	@powershell Write-Host "*CAB*" -foreground white
	python_to_cab.cmd $(PYTHON_TMP_DIR) $(PYTHON_MODULE_NAME) to_save

$(ARTEFACT_MODULE): $(PYTHON_MODULE) ## copy to artefacts
	@powershell Write-Host "+Target $@" -foreground white
	@if not exist $(ARTEFACTS_DIR) mkdir $(ARTEFACTS_DIR) 2> nul
	@copy /Y $< $@ 

build: unpack $(ARTEFACT_MODULE) ## building all
	@powershell Write-Host -foreground Green "Build finished, uninstalling python"
	@echo NOT REQUIRED call exec_cmd.bat uninstall_python.cmd $(PY_VER) $(PY_SUBVER)
	

clean:
	@powershell Write-Host -foreground Green "Cleaninn..."
	@call exec_cmd.bat uninstall.cmd
	@rmdir /s/q .\$(PYTHON_TMP_DIR)
	@rmdir /s/q .\$(PYTHON_SRC_DIR) 

python_344:
	@powershell Write-Host "Building Legacy Python 3.4.4 ..." -foreground white
	exec_cmd.bat uninstall_legacy.cmd 3.4 4
	exec_cmd.bat install_legacy.cmd 3.4 4
	exec_cmd.bat build_environment_legacy.cmd 3.4 4
	exec_cmd.bat uninstall_legacy.cmd 3.4 4
	exec_cmd.bat clean_environment.cmd 3.4 4
	exec_cmd.bat patch_environment.cmd 3.4 4
	python_to_cab.cmd tmp\3.4 python-3.4.zip to_save
	@if not exist $(ARTEFACTS_DIR) mkdir $(ARTEFACTS_DIR) 2> nul
	@copy /Y tmp\3.4\python-3.4.zip $(ARTEFACTS_DIR)\python-3.4.zip
	@powershell Write-Host -foreground Green "Python 3.4.4 is saved"

integration:
	@make -C "tests" test-integration

integration-force:
	@make -C "tests" test-integration-force
