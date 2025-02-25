# Windows Modules to deploy wint Windows Agent 2.0 and later

## Python 3.12

### Source

PYTHON 3.12, provided as source tarball by standard Checkmk development process
=======
## Python 3.12

### Source

PYTHON 3.12, provided as source tarball by standard Checkmk development process

### Changing or Updating the Python

1. _mandatory_   Add new file in omd/packages/Python with a name Python-Version.Subversion.tar.xz
2. _recommended_ Update documentation
3. _optional_    Update root Makefile(for default parameters)
4. _optional_    Add line 'del /Q python-<Version>.cab' to the clean_environment.cmd script

### Required Tools

1. Visual Studio 2022 and v143 toolchain for ARM, x86 and ARM64. This is IMPORTANT.
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

### Changes of the files and names

This procedure may quite annoying, you have to check next points:

1. Check scripts in the folder.
2. **buildscripts/scripts/lib/windows.groovy** : from windows node to jenkins
3. **buildscripts/scripts/build-cmk-version.jenkins** : from enkins to packaging
4. Checkmk root **Makefile**. Packaging self
5. Add to integration tests new file name:

   *grep agents\modules\windows\tests\integration\* for "python-"*

   Usually it is conftest.py and Makefile.

6. Check build_the_module.cmd for 3.12 and et cetera
7. Check the Windows node builds artifacts succesfully.

### PROCESS

#### Execution local

##### Building
make build PY_VER=3.12 PY_SUBVER=9

##### Testing
make integration
make integration-force


#### Execution CI

Main entry:
build_the_module cached

In a turn the script makes two calls:
build_the_cached artefact_dir credentials url 3.12 9

#### Caching

All builds of the Python are cached.
Name of the cached file
python-%version%.%subversion%_%git_hash%_%BUILD_NUM%.cab

This mean that you didn't get a new build till you increase value in the file *BUILD_NUM*.
Just a commit is not enough, because some builds can't get data about current git hash.
In latter case the git_hash is replaced with string "latest".


#### Steps 3.12 and newer

1. Deploy package from the *omd/packages*
2. Build  and copy results t the *out*.
3. Uninstall from backuped python-3.12.exe in *uninstall*
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
14. Compress *tmp/to_save* into *tmp/python-3.cab*.
15. Copy cab to *artefacts*

### TREE

.
|
|-- tmp/
|    |
|    +-- 3.12/
|           |   python-3.cab  * resulting module file
|           |
|           |-- to_save/		* to produce module *
|           |
|           |-- Libs/           * libraries from the install
|           |    |-- Libs/      * libraries from the install
|           |    |
|           |    |
|           |    +-- .venv/	    * virtual environment *
|           |
|           |-- out/		    * output from the Python build *
|           |
|           |-- uninstall/	    * backed up installer *
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
     +-- 3.12/
             |
             |-- python-3.12.timestamp
             |
             +-- python-3.12/
