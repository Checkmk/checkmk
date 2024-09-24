# Windows Modules to deploy with Windows Agent 2.0 and later

## Python 3.12

### Source

Python 3.12, provided as source tarball by standard Checkmk development process

### Changing or updating Python

1. _mandatory_   Add new file in `omd/packages/Python` with a name `Python-Version.Subversion.tar.xz`, align with the Python version in `package_versions.bzl`
2. _recommended_ Update documentation
3. _optional_    Update `agents/modules/windows/Makefile` (for default parameters)
4. _optional_    Add line `del /Q python-<Version>.cab` to the `agents/modules/windows/clean_environment.cmd` script

### Required Tools

- Visual Studio 2022 and v143 toolchain for ARM, x86 and ARM64. This is IMPORTANT.
- Python 3.7 or newer on the path
- Normal make
- 7zip

### IMPORTANT

1. You must always uninstall Python before deleting folders and or building.
Normally this is done automatically by build scripts. Just do not forget this
if you are modifying scripts.
2. Patch the registry with the `agents/modules/windows/WindowsServerPatch.reg` if you are using Windows Server.
Windows Server by default disables MSI installation even on per-user basis.
We must set registry value `MsiDisable = 0` as in Windows 10.
3. You must switch jenkins slave to real user-admin account (use `services.msc`), otherwise
installation is not possible. The error is `cannot install` or similar.
4. You must increase value in `agents/modules/windows/BUILD_NUM` to get a rebuild binary.
5. You may need to unpack `agents/modules/windows/libffi-7.zip` into correspoding python source directory.

### Changes of the files and names

This procedure may be quite annoying, you have to check next points:

- Check scripts in this folder `agents/modules/windows/`
- `buildscripts/scripts/utils/windows.groovy`: from windows node to jenkins
- `buildscripts/scripts/build-cmk-packages.groovy`: from jenkins to packaging
- Checkmk root `Makefile`. Packaging self
- Add to integration tests new file name:

   `cd agents/modules/windows/tests/integration/* && grep -R "python-*"`

   Usually it is `agents/modules/windows/tests/integration/conftest.py` and `agents/modules/windows/Makefile`.

- Check `build_the_module.cmd` for 3.12 and et cetera
- Check the Windows node builds artifacts succesfully

### Process

#### Execution local

##### Building

```
make build PY_VER=3.12 PY_SUBVER=6
```

##### Testing

```
make integration
make integration-force
```

#### Execution CI

Main entry:

```
build_the_module cached <CREDENTIALS> <CACHE_URL>
```

In one turn the script makes two calls:

```bat
:: build_the_cached.cmd <ARTEFACT_DIR> <CREDENTIALS> <CACHE_URL> <PYTHON_VERSION> <PYTHON_SUBVERSION>
build_the_cached.cmd artefact_dir credentials url 3.12 6
```

#### Caching

All builds of the Python are cached.

Name of the cached file `python-%version%.%subversion%_%git_hash%_%BUILD_NUM%.cab`

This means that you didn't get a new build till you increase value in the file `agents/modules/windows/BUILD_NUM`.
Just a commit is not enough, because some builds can't get data about current git hash.
In latter case the `git_hash` is replaced by `latest`.

#### Steps 3.12 and newer

1. Deploy package from the `omd/packages`
2. Build and copy results to the `out` folder
3. Uninstall from backuped `python-3.12.exe` in `uninstall`
4. Install Python to the `to_install` folder
5. Upgrade pip
6. Install pipenv
7. Save whole folder to the `to_save`
8. Uninstall python from `to_install`
9. copy `~pipfiles/3/Pipfile~` in `to_save`
10. Build virtual environment `to_save`
11. Copy correct `pyvenv.cfg` into `to-save/.venv`
12. Copy runtime from runtime to DLL
13. Clean virtual environment `to_save`
14. Compress `tmp/to_save` into `tmp/python-3.cab`
15. Copy cab to `artefacts`

### TREE

```
.
|
|-- tmp/
|    |
|    +-- 3.12/
|           |   python-3.cab    * resulting module file
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
```

## Login

The login details are stored in [bitwarden](passwords.lan.checkmk.net) under `collections/development/CI`.

### Remmina

- Server: See bitwarden
- Username: See bitwarden
- Password: See bitwarden

### xfreerdp

```bash
apt-get install freerdp2-x11
xfreerdp /u:<SEE BITWARDEN> /v:<SEE BITWARDEN>
```

## Troubleshooting

### Failing Windows Builds

Possible error messages you might encounter are:
- `WARNING: Operation did not complete successfully because the file contains a virus or potentially unwanted software.`
- `ModuleNotFoundError: No module named <module name>`

One possible problem is that the builds are not properly created.

Make sure that the Windows build system is up-to-date in regards of updates, especially the Windows Defender because it
might block the creation of artifacts containing files it finds malicious - this is nearly always a false positive.
To do so go to the Windows Update overview, check for updates and install the updates that are presented to you.
If Windows asks for a restart, perform this restart. Afterwards try to rebuild.
