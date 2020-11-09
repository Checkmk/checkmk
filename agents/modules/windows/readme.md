# Windows Modules to deploy wint Windows Agent 1.7 and later

## Python 3.8

### Source

CPYTHON, 3.8.5, git.

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

4. You must increase value in file BUILD_NUM to rebuild in master(master can't use git and 
must be informed about changes)

### PROCESS

#### Execution

make

#### Steps

1. Deploy package from the *omd/packages*
2. Build  and copy results t the *out*
3. Uninstall from backuped python-3.8.exe in *uninstall*
4. Install to the *to_install*
5. Upgrade pip 
6. Install pipenv
7. Save whole folder to the *to_save*
8. Uninstall python from *to_install*
9. copy ~check_mk/virtual-envs/Windows/3.8/Pipfile~ in *to_save*
10. Build virtual environemtn *to_save* and copy correct *pyvenv.cfg* into *tO-save/.venv*
11. Clean virtual environemtn *to_save*
12. Zip *tmp/to_save* into *tmp/python-3.8.zip*
13. Copy to *artefacts*



### TREE

.
|
|-- tmp/
|    |   python-3.8.zip
|    |
|    |-- work/		    * to produce module *
|    |    |
|    |    +-- .venv/	* virtual environment *
|    |
|    |-- out/		    * output from the Python build *
|    |
|    |-- uninstall/	    * backed up installer *
|    |
|    +-- to_install/	* installation of the Python *
|
|-- lhm/                * future use *
|
|-- python/
     |
     |-- cpython-3.8.timestamp
     |
     +-- cpython-3.8/

