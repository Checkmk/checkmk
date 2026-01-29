#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-any-return"

import json
import subprocess
from importlib.util import cache_from_source
from pathlib import Path
from subprocess import check_output
from typing import NamedTuple, NewType

import pytest
from semver import VersionInfo

from tests.testlib.common.repo import repo_path
from tests.testlib.site import Site

ImportName = NewType("ImportName", "str")


def _get_python_version_from_defines_make() -> VersionInfo:
    return VersionInfo.parse(
        check_output(["make", "--no-print-directory", "print-PYTHON_VERSION"], cwd=repo_path())
        .decode()
        .rstrip()
    )


class PipCommand(NamedTuple):
    command: list[str]
    needs_target_as_commandline: bool


PYVER = _get_python_version_from_defines_make()

SUPPORTED_PIP_CMDS: tuple[PipCommand, ...] = (
    PipCommand(["python3", "-m", "pip"], True),
    PipCommand([f"pip{PYVER.major}"], False),  # Target is set in the wrapper script as cmd line
    PipCommand(
        [f"pip{PYVER.major}.{PYVER.minor}"], False
    ),  # Target is set in the wrapper script as cmd line
)


def _local_package_installation_path(site: Site) -> Path:
    return Path(f"{site.root}", "local/lib/python3")


def assert_local_package_install_path(
    site: Site, package_name: str, local_package_installation_path: Path
) -> None:
    module_file = import_module_and_get_file_path(site, package_name)
    assert module_file

    # We only want to install into local as mkp will search there
    assert local_package_installation_path in Path(module_file).parents


def assert_install_package(cmd: list[str], package_name: str, site: Site) -> None:
    p = site.execute(cmd, stdout=subprocess.PIPE)
    install_stdout, _ = p.communicate()

    assert "Successfully installed" in install_stdout, install_stdout
    p = site.execute(["python3", "-c", f"import {package_name}"], stdout=subprocess.PIPE)
    p.communicate()
    assert p.returncode == 0


def assert_uninstall_and_purge_cache(pip_cmd: PipCommand, package_name: str, site: Site) -> None:
    for cmd in (
        pip_cmd.command + ["uninstall", "-y", package_name],
        pip_cmd.command + ["cache", "purge"],
    ):
        p = site.execute(cmd, stdout=subprocess.PIPE)
        p.communicate()
        assert p.returncode == 0


def test_01_python_interpreter_exists(site: Site) -> None:
    assert site.path(f"bin/python{_get_python_version_from_defines_make().major}").exists()


def test_02_python_interpreter_path(site: Site) -> None:
    major = _get_python_version_from_defines_make().major
    p = site.execute(["which", f"python{major}"], stdout=subprocess.PIPE)
    path = p.stdout.read().strip() if p.stdout else "<NO STDOUT>"
    assert path == f"/omd/sites/{site.id}/bin/python{major}"


def test_03_python_interpreter_version(site: Site) -> None:
    python_version = _get_python_version_from_defines_make()
    p = site.execute([f"python{python_version.major}", "-V"], stdout=subprocess.PIPE)
    version = p.stdout.read() if p.stdout else "<NO STDOUT>"
    assert version.startswith(f"Python {str(python_version)}")


def test_03_python_path(site: Site) -> None:
    python_version = _get_python_version_from_defines_make()
    p = site.execute(
        [f"python{python_version.major}", "-c", "import sys,json; json.dump(sys.path, sys.stdout)"],
        stdout=subprocess.PIPE,
    )
    sys_path = json.loads(p.stdout.read()) if p.stdout else "<NO STDOUT>"

    assert sys_path[0] == ""

    ordered_path_elements = [
        # there may be more, but these have to occur in this order:
        site.root.as_posix() + f"/local/lib/python{python_version.major}",
        site.root.as_posix() + f"/lib/python{python_version.major}.{python_version.minor}",
        site.root.as_posix() + f"/lib/python{python_version.major}",
    ]
    assert [s for s in sys_path if s in ordered_path_elements] == ordered_path_elements

    for path in sys_path[1:]:
        assert path.startswith(site.root.as_posix()), f"Found non site path {path!r} in sys.path"


def test_01_pip_exists(site: Site) -> None:
    assert site.path("bin/pip3").exists()


def test_02_pip_path(site: Site) -> None:
    p = site.execute(["which", "pip3"], stdout=subprocess.PIPE)
    path = p.stdout.read().strip() if p.stdout else "<NO STDOUT>"
    assert path == "/omd/sites/%s/bin/pip3" % site.id


@pytest.mark.parametrize(
    "pip_cmd",
    SUPPORTED_PIP_CMDS,
)
def test_03_pip_interpreter_version(site: Site, pip_cmd: PipCommand) -> None:
    p = site.execute(pip_cmd.command + ["-V"], stdout=subprocess.PIPE)
    version = p.stdout.read() if p.stdout else "<NO STDOUT>"
    assert version.startswith("pip 25.2")


def test_04_pip_user_can_install_non_wheel_packages(site: Site) -> None:
    # ibm_db must be compiled from source, so choosing this also ensures that the Python headers
    # can be found by pip
    package_name = "ibm_db"

    # We're testing this only for one supported pip command as building from source just takes too long
    pip_cmd = PipCommand(["pip3"], False)

    assert_install_package(pip_cmd.command + ["install", package_name], package_name, site)
    assert_local_package_install_path(site, package_name, _local_package_installation_path(site))
    assert_uninstall_and_purge_cache(pip_cmd, package_name, site)


@pytest.mark.parametrize("pip_cmd", SUPPORTED_PIP_CMDS)
def test_05_pip_user_can_install_wheel_packages(site: Site, pip_cmd: PipCommand) -> None:
    package_name = "trickkiste"
    if pip_cmd.needs_target_as_commandline:
        command = pip_cmd.command + [
            "install",
            "--target",
            str(_local_package_installation_path(site)),
            package_name,
        ]
    else:
        command = pip_cmd.command + ["install", package_name]

    assert_install_package(command, package_name, site)
    assert_local_package_install_path(site, package_name, _local_package_installation_path(site))
    assert_uninstall_and_purge_cache(pip_cmd, package_name, site)


def import_module_and_get_file_path(site: Site, import_name: str) -> str:
    p = site.execute(
        ["python3", "-c", f"import {import_name} as m; print(m.__file__ or '')"],
        stdout=subprocess.PIPE,
    )
    return p.communicate()[0].rstrip()


def test_avoids_symlink_attacks(site: Site) -> None:
    # _clear_site_home relies on this assertion to be true for `omd restore` to be safe. See the
    # change with ID: If3c50a40af55a516c2d8539c0fc48515e30e0760
    # This test is also covered by the `omd restore` integration test, but this one is more focused.
    site.check_output(
        ["python3", "-c", "import shutil; assert shutil.rmtree.avoids_symlink_attacks"]
    )


def test_python_preferred_encoding(site: Site) -> None:
    p = site.execute(
        ["python3", "-c", "import locale; print(locale.getpreferredencoding())"],
        stdout=subprocess.PIPE,
    )
    assert p.communicate()[0].rstrip() == "UTF-8"


def test_python_optimized_and_lto_enable(site: Site) -> None:
    output = site.execute(
        ["python3", "-c", "import sysconfig; print(sysconfig.get_config_vars('CONFIG_ARGS'));"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    ).communicate()[0]
    assert "--enable-optimizations" in output
    assert "--with-lto" in output


@pytest.mark.parametrize(
    "import_path,expected_source_file,expected_pyc_file",
    [
        pytest.param(
            "cmk.base.config",
            f"lib/python{PYVER.major}/cmk/base/config.py",
            f"lib/python{PYVER.major}/cmk/base/__pycache__/config.cpython-{PYVER.major}{PYVER.minor}.pyc",
            id="pyc for imports from the big monolith cmk namespace",
        ),
        pytest.param(
            "cmk.werks.config",
            f"lib/python{PYVER.major}.{PYVER.minor}/site-packages/cmk/werks/config.py",
            f"lib/python{PYVER.major}.{PYVER.minor}/site-packages/cmk/werks/__pycache__/config.cpython-{PYVER.major}{PYVER.minor}.pyc",
            id="pyc for imports from cmk packages namespace",
        ),
        pytest.param(
            "omdlib.main",
            f"lib/python{PYVER.major}/omdlib/main.py",
            f"lib/python{PYVER.major}/omdlib/__pycache__/main.cpython-{PYVER.major}{PYVER.minor}.pyc",
            id="pyc for imports from omdlib",
        ),
        pytest.param(
            "requests.sessions",
            f"lib/python{PYVER.major}.{PYVER.minor}/site-packages/requests/sessions.py",
            f"lib/python{PYVER.major}.{PYVER.minor}/site-packages/requests/__pycache__/sessions.cpython-{PYVER.major}{PYVER.minor}.pyc",
            id="pyc for imports from third party packages",
        ),
    ],
)
def test_python_is_bytecode_compiled(
    import_path: str,
    expected_source_file: str,
    expected_pyc_file: str,
    site: Site,
) -> None:
    # This tests sample-tests some well known (and hopefully long existing) modules regarding pre-compiled pyc files
    # !!! IMPORTANT !!!
    # in case any tested module does not exist anymore, please replace it with an existing one!

    output = site.check_output(
        ["python3", "-v", "-c", f"import {import_path}"], stderr=subprocess.STDOUT
    )
    assert (
        f"{site.root}/{expected_pyc_file} matches {site.root}/{expected_source_file}" in output
    ), f"No matching pyc file for '{import_path}' found"


def test_all_bytecode_files_exist(site: Site) -> None:
    # see CMK-24370 - pyc files will be generated as a postinst step. In contrast to before, `compileall` will
    # be executed on _all_ files below `site.root`, so we simply check for an 1on1 existence.
    for py_path in Path(site.root).rglob("*.py"):
        if "check_mk/agents/plugins" in py_path.as_posix():
            continue
        if "/skel/" in py_path.as_posix():
            continue
        pyc_path = Path(cache_from_source(py_path))
        expected_pyc_path = (
            py_path.parent / f"__pycache__/{py_path.stem}.cpython-{PYVER.major}{PYVER.minor}.pyc"
        )
        assert pyc_path == expected_pyc_path, (pyc_path, expected_pyc_path)
        assert pyc_path.exists(), f"{pyc_path} for {py_path} does not exist"
