#
# Deploy/Clean CPython for Windows
# Expected Python 3.7 installed
# build - creates python module
#
# Usage:
#  make 

# internal dirs:
PYTHON_SRC_DIR = python
PYTHON_TMP_DIR = tmp

PYTHON_INSTALL_DIR = $(PYTHON_TMP_DIR)\to_install
PYTHON_READY_DIR   = $(PYTHON_TMP_DIR)\ready
PYTHON_VENV_DIR    = $(PYTHON_READY_DIR)\.venv

# external paths
ROOT_CMK_PATH      = ..\..\..
OMD_PACKAGE_PATH   = $(ROOT_CMK_PATH)\omd\packages\cpython
ARTE_PATH          = $(ROOT_CMK_PATH)\artefacts
GIT_PIPFILE_PATH   = $(ROOT_CMK_PATH)\virtual-envs\windows\3.8

# names
OMD_PYTHON_NAME    = cpython-3.8

# files
PYTHON_MODULE_NAME = python-3.8.zip
PYTHON_ARTE        = $(ARTE_PATH)\$(PYTHON_MODULE_NAME)


PYTHON_TIMESTAMP   = $(PYTHON_SRC_DIR)\$(OMD_PYTHON_NAME).timestamp
OMD_PYTHON_PACKAGE = $(OMD_PACKAGE_PATH)\$(OMD_PYTHON_NAME).zip

GIT_PIPFILE        = $(GIT_PIPFILE_PATH)\Pipfile
PIPFILE            = $(PYTHON_READY_DIR)\Pipfile
PIPFILE_LOCK       = $(PYTHON_READY_DIR)\Pipfile.lock

PYTHON_MODULE      = $(PYTHON_READY_DIR)\$(PYTHON_MODULE_NAME)



.PHONY: clean venv 7zip unpack build python_install

.DEFAULT_GOAL = build

$(PYTHON_TIMESTAMP): $(OMD_PYTHON_PACKAGE) ## deploying python sources
	@echo "Target $@"
	@powershell Write-Host "$@ is to be processed" -foreground cyan
	@if not exist $< powershell Write-Host -foreground Red "$< absent" && exit 1
	@powershell Write-Host -foreground Green "Unpacking $< ..."
	@7z x -y -mmt4 -o$(PYTHON_SRC_DIR) $< 
	@type nul >>$@ && powershell (ls $@).LastWriteTime = Get-Date   # windows touch
	@powershell Write-Host -foreground Green "Done"


7zip: ## checking for 7 zip
	@echo "Target $@"
	@7z -? > nul
	@if "%errorlevel%" NEQ "0" powershell Write-Host "7zip must be installed: use choco or windows_setup" -Foreground Red && exit /b 1
	@powershell Write-Host "7zip is installed. This is good" -Foreground Green
	
unpack: 7zip $(PYTHON_TIMESTAMP) ## unpacking python sources
	@echo "Target $@"
	@powershell Write-Host -foreground Green "cpython is Ready to build"

python_install: $(PYTHON_TIMESTAMP)    ## python installation
	@echo "Target $@"
	@call exec_cmd.bat build_python.cmd
	@call exec_cmd.bat uninstall_python.cmd
	@call exec_cmd.bat install_python.cmd
	@call exec_cmd.bat upgrade_pip.cmd
	@call exec_cmd.bat install_pipenv.cmd
	@powershell Write-Host -foreground Green "Python is build and ready to use"


$(PIPFILE): $(GIT_PIPFILE) ## pifile copy and patch
	@echo "Target $@"
	@if not exist $(PYTHON_READY_DIR) mkdir $(PYTHON_READY_DIR) 2> nul
	@copy /Y $< $@
	@py -3 patch_pipfile.py $@

$(PIPFILE_LOCK): $(PIPFILE) ## piplock building
	@echo "Target $@"
	@call exec_cmd.bat build_piplock.cmd


venv: python_install $(PIPFILE_LOCK) ## venv building
	@echo "Target $@"
	@call exec_cmd.bat build_venv.cmd
	
	
$(PYTHON_MODULE): venv ## zipping venv
	@echo "Target $@"
	@cd $(PYTHON_VENV_DIR) && 7z a -r -tzip -y -stl -mmt4 ..\$(PYTHON_MODULE_NAME) *.*

$(PYTHON_ARTE): $(PYTHON_MODULE) ## copy to artefacts
	@echo "Target $@"
	@copy /Y $< $@ 

build: unpack $(PYTHON_ARTE) ## building all
	@powershell Write-Host -foreground Green "Build finished, uninstalling python"
	@call exec_cmd.bat uninstall_python.cmd
	

clean:
	@call exec_cmd.bat uninstall.cmd
	@rmdir /s/q .\$(PYTHON_TMP_DIR)
	@rmdir /s/q .\$(PYTHON_SRC_DIR) 




#build: mk_logwatch.exe

#mk_logwatch.exe:  