# Windows Modules to deploy wint Windows Agent 1.7 and later

## Python 3.8

### Source

CPYTHON, 3.8.1, git.

### Required Tools

1. Visual Studio 2019
2. Python 3.7 or newer
3. Normal make
4. 7zip
5. psexec

### IMPORTANT

You must uninstall Python before deleting folders and or building.
Normally this is done automatically by build scripts. Just do not forget this 
if you are modifying scripts

### PROCESS

#### Execution

run make

#### Steps

1. Deploy package from the ~omd/packages~
2. Build to the ~out~
3. Install to ~to_install~
4. Backup python-3.8.exe to ~uninstall~
5. Upgrade pip 
6. Install pipenv
7. Create .venv in ~ready~ using ~check_mk/virtual-envs/Windows/3.8/Pipfile~
8. Process Pipfile.lock in ~ready~
9. Zip ~ready/.venv~
10. Copy to artefacts
11. Uninstall python from ~to_install~



### TREE

.
|
|-- tmp/
|    |-- ready/		~ venv ~
|    |-- out/		~ output from the build ~
|    |-- uninstall/	~ backed up installer ~
|    +-- to_install/	~ installation of the Python ~
|
|-- lhm/
|
|-- python/
     |
     |-- cpython-3.8.timestamp
     |
     +-- cpython-3.8/

