#
# Deploy/Clean CPython for Windows
# Expected Python 3.7 installed
#
# Usage:
#  make unpack

# internal dirs:
PYTHON_SRC_DIR = python
PYTHON_TMP_DIR = tmp
PYTHON_DISTRO_DIR = distro
PYTHON_INSTALL_DIR = $(PYTHON_TMP_DIR)\to_install


PYTHON_SRC_NAME = cpython-3.8
PYTHON_MODULE_NAME = python-3.8.zip
PYTHON_DISTRO = $(PYTHON_DISTRO_DIR)\$(PYTHON_MODULE_NAME)
PYTHON_ARTE = $(ARTE_PATH)\$(PYTHON_MODULE_NAME)

PACKAGE_PATH = ..\..\..\omd\packages\cpython
ARTE_PATH = ..\..\..\artefacts

PYTHON_TIMESTAMP = $(PYTHON_SRC_DIR)\$(PYTHON_SRC_NAME).timestamp
PYTHON_PACKAGE = $(PACKAGE_PATH)\$(PYTHON_SRC_NAME).zip




.PHONY: clean

$(PYTHON_TIMESTAMP): $(PYTHON_PACKAGE)
	@if not exist $< powershell Write-Host -foreground Red "$< absent" && exit 1
	@powershell Write-Host -foreground Green "Unpacking $< ..."
	@7z x -y -mmt4 -o$(PYTHON_SRC_DIR) $< 
	@type nul >>$@ & copy $@ +,, > nul
	@powershell Write-Host -foreground Green "Done"


7zip:
	@7z -? > nul
	@if "%errorlevel%" NEQ "0" powershell Write-Host "7zip must be installed: use choco or windows_setup" -Foreground Red && exit /b 1
	@powershell Write-Host "7zip is installed. This is good" -Foreground Green
	
unpack: 7zip $(PYTHON_TIMESTAMP)
	@powershell Write-Host -foreground Green "cpython is Ready to build"

$(PYTHON_DISTRO): $(PYTHON_TIMESTAMP)
	@call build.cmd
	@call install.cmd
	@if exist $@ del $@ 2> nul
	@cd $(PYTHON_INSTALL_DIR) && 7z a -r -tzip -y -stl -mmt4 ..\..\$@ *.*
	@call uninstall.cmd
	@powershell Write-Host -foreground Green "Done"



$(PYTHON_ARTE): $(PYTHON_DISTRO)
	@copy /Y $< $@

build: unpack $(PYTHON_ARTE)
	@powershell Write-Host -foreground Green "Build finished"
	

clean:
	@call uninstall.cmd
	@rmdir /s/q .\$(PYTHON_TMP_DIR)
	@rmdir /s/q .\$(PYTHON_SRC_DIR) 
	@rmdir /s/q .\$(PYTHON_DISTRO_DIR) 




#build: mk_logwatch.exe

#mk_logwatch.exe:  