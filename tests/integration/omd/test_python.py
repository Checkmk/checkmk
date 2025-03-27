#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import os
import re
import subprocess
from pathlib import Path
from subprocess import check_output
from typing import NamedTuple, NewType

import pytest
from pipfile import Pipfile  # type: ignore[import]
from semver import VersionInfo

from tests.testlib.repo import repo_path
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


PYTHON_VERSION = _get_python_version_from_defines_make()

SUPPORTED_PIP_CMDS: tuple[PipCommand, ...] = (
    PipCommand(["python3", "-m", "pip"], True),
    PipCommand(
        [f"pip{PYTHON_VERSION.major}"], False
    ),  # Target is set in the wrapper script as cmd line
    PipCommand(
        [f"pip{PYTHON_VERSION.major}.{PYTHON_VERSION.minor}"], False
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


def _load_pipfile_data() -> dict:
    return Pipfile.load(filename=str(repo_path() / "Pipfile")).data


def test_01_python_interpreter_exists(site: Site) -> None:
    assert os.path.exists(site.root + f"/bin/python{_get_python_version_from_defines_make().major}")


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
        [
            f"python{python_version.major}",
            "-c",
            "import sys,json; json.dump(sys.path, sys.stdout)",
        ],
        stdout=subprocess.PIPE,
    )
    sys_path = json.loads(p.stdout.read()) if p.stdout else "<NO STDOUT>"

    assert sys_path[0] == ""

    ordered_path_elements = [
        # there may be more, but these have to occur in this order:
        site.root + f"/local/lib/python{python_version.major}",
        site.root + f"/lib/python{python_version.major}/cloud",
        site.root + f"/lib/python{python_version.major}.{python_version.minor}",
        site.root + f"/lib/python{python_version.major}",
    ]
    assert [s for s in sys_path if s in ordered_path_elements] == ordered_path_elements

    for path in sys_path[1:]:
        assert path.startswith(site.root), f"Found non site path {path!r} in sys.path"


def test_01_pip_exists(site: Site) -> None:
    assert os.path.exists(site.root + "/bin/pip3")


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
    assert version.startswith("pip 24.3")


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


def test_python_preferred_encoding(site: Site) -> None:
    p = site.execute(
        ["python3", "-c", "import locale; print(locale.getpreferredencoding())"],
        stdout=subprocess.PIPE,
    )
    assert p.communicate()[0].rstrip() == "UTF-8"


def test_python_optimized_and_lto_enable(site: Site) -> None:
    output = site.execute(
        [
            "python3",
            "-c",
            "import sysconfig; print(sysconfig.get_config_vars('CONFIG_ARGS'));",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    ).communicate()[0]
    assert "--enable-optimizations" in output
    assert "--with-lto" in output


def test_all_cmk_gui_dependencies_are_loaded_from_byte_code(site: Site) -> None:
    imported_from = import_cmk_gui_and_get_import_code_object_sources(site)
    from_byte_code = [f for f in imported_from if f.endswith(".pyc")]
    from_source = [f for f in imported_from if not f.endswith(".pyc")]
    assert len(from_byte_code) > 700
    assert not from_source, f"Found {len(from_source)} modules loaded from source: {from_source!r}"


def import_cmk_gui_and_get_import_code_object_sources(site: Site) -> list[str]:
    imported_from = []
    for l in (
        site.execute(
            ["python3", "-v", "lib/python3/cmk/gui/wsgi/applications/checkmk.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        .communicate()[0]
        .splitlines()
    ):
        # Process these lines:
        # "# code object from '/omd/sites/beta/lib/python3.12/json/__pycache__/encoder.cpython-312.pyc'"
        # "# code object from /omd/sites/beta/lib/python3.12/site-packages/werkzeug/sansio/http.py"
        if match := re.match("^# code object from '?([^']+)'?$", l):
            imported_from.append(match.group(1))
    return imported_from
