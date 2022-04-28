# Windows Modules to deploy wint Windows Agent 2.0 and later

## Python 3.8 & Python 3.4.4

### Source

PYTHON 3.9.10, provided as source tarball by standard Checkmk development process
PYTHON 3.4.4, downloaded as msi installer from the python.org

### Changing or Updating the Python

1. _mandatory_   Add new file in omd/packages/Python with a name Python-Version.Subversion.tar.xz
2. _mandatory_   Update build_the_module.cmd script to set new version
3. _recommended_ Update documentation
4. _optional_    Update root Makefile(for default parameters)
5. _optional_    Add line 'del /Q python-<Version>.cab' to the clean_environment.cmd script

### Required Tools

1. Visual Studio 2019 and v140 toolchain.
2. Python 3.7 or newer on the path
3. Normal make.
4. 7zip.

### IMPORTANT

1. You must always uninstall Python before deleting folders and or building.
Normally this is done automatically by build scripts. Just do not forget this
if you are modifying scripts

2. Patch the registry with the *WindowsServerPatch.reg* if you are using Windows Server.
Windows Server by default disables MSI installation even on per-user basis.
We must set registry value MsiDisable = 0 as in Windows 10

3. You must switch jenkins slave to real user-admin account(use services.msc), otherwise
installation is not possible. The error is "cannot install" or similar

4. You must increase value in file BUILD_NUM to get a rebuild binary

5. You may need to unpack libffi-7.zip into correspoding python source directory.

6. Python 3.8 can't be built with Windows 11 SDK
Check this path:
HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\Microsoft\Microsoft SDKs\Windows\v10.0
and set to crrect value 10586


### Changes of the files and names

This procedure may quite annoying, you have to check next points:

1. Check scripts in the folder.
2. **buildscripts/scripts/lib/windows.groovy** : from windows node to jenkins
3. **buildscripts/scripts/build-cmk-version.jenkins** : from enkins to packaging
4. Checkmk root **Makefile**. Packaging self
5. Add to integration tests new file name:

   *grep agents\modules\windows\tests\integration\* for "python-"*

   Usually it is conftest.py and Makefile.

6. Check build_the_module.cmd for 3.9, 3.4 and et cetera
7. Check the Windows node builds artifacts succesfully.

### PROCESS

#### Execution local

##### Building
make build PY_VER=3.9 PY_SUBVER=8
make python_344 PY_VER=3.4 PY_SUBVER=4

##### Testing
make integration
make integration-force


#### Execution CI

Main entry:
build_the_module cached

In a turn the script makes two calls:
build_the_cached artefact_dir credentials url 3.4 4
build_the_cached artefact_dir credentials url 3.9 8

#### Caching

All builds of the Python are cached.
Name of the cached file
python-%version%.%subversion%_%git_hash%_%BUILD_NUM%.cab

This mean that you didn't get a new build till you increase valeu in the file *BUILD_NUM*.
Just a commit is not enough, because some builds can't get data about current git hash.
In latter case the git_hash is replaced with string "latest".


#### Steps 3.8 and newer

1. Deploy package from the *omd/packages*
2. Build  and copy results t the *out*.
3. Uninstall from backuped python-3.8.exe in *uninstall*
4. Install to the *to_install*
5. Upgrade pip
6. Install pipenv
7. Save whole folder to the *to_save*
8. Uninstall python from *to_install*
9. copy ~pipfiles/3/Pipfile~ in *to_save*
10. Build virtual environemtn *to_save*
11. Copy correct *pyvenv.cfg* into *tO-save/.venv*
12. Copy runtime from runtime to DLL
13. Clean virtual environemtn *to_save*
14. Compress *tmp/to_save* into *tmp/python-3.8.cab*.
15. Copy cab to *artefacts*

#### Steps 3.4.4

1. Uninstall omd/packages/Python/windows/python-3.4.4.msi
2. install omd/packages/Python/windows/python-3.4.4.msi to the *to_install*
3. Build virtual environment and copy files into *to_save*
4. Uninstall omd/packages/Python/windows/python-3.4.4.msi
5. Upgradepip and install packages
6. Copy correct *pyvenv.cfg* into *tO-save/.venv*
7. Clean virtual environemtn *to_save*
8. Compress *tmp/to_save* into *tmp/python-3.4.cab*.
9. Copy cab to *artefacts*

IMPORTANT: You need Visual Studio 10 to build 3.4.4.
This can be difficult to obtain, you have to ask a person having Visual Studio Professional license to download.

### TREE

.
|
|-- tmp/
|    |
|    |-- 3.9/
|    |      |   python-3.9.cab  * resulting module file
|    |      |
|    |      |-- to_save/		* to produce module *
|    |      |
|    |      |-- Libs/           * libraries from the install
|    |      |    |-- Libs/      * libraries from the install
|    |      |    |
|    |      |    |
|    |      |    +-- .venv/	    * virtual environment *
|    |      |
|    |      |-- out/		    * output from the Python build *
|    |      |
|    |      |-- uninstall/	    * backed up installer *
|    |      |
|    |      +-- to_install/	    * installation of the Python *
|    |
|    +-- 3.4/
|           |   python-3.4.cab  * resulting module file
|           |
|           |-- to_save/		* to produce module *
|           |    |
|           |    |-- Libs/      * libraries from the install
|           |    |
|           |    +-- .venv/	    * virtual environment *
|           |
|           +-- to_install/	    * installation of the Python *
|
|-- lhm/                * future use *
|
|-- runtime/            * This files are from Windows KB Update https://www.microsoft.com/en-us/download/details.aspx?id=49091
|                         Those files are required for some old OS or for Windows Core.
|                         Should be packaged to the Python installation
|
|-- python/
     |
     |-- 3.9/
     |       |
     |       |-- python-3.9.timestamp
     |       |
     |       +-- python-3.9/
     |
     |-- 3.4/
             |
             |-- python-3.4.timestamp
             |
             +-- python-3.4/
