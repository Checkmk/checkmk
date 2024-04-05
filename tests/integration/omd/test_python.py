#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import os
import subprocess
from collections.abc import Iterable
from pathlib import Path
from subprocess import check_output
from typing import NamedTuple, NewType

import pkg_resources as pkg
import pytest
from pipfile import Pipfile  # type: ignore[import]
from semver import VersionInfo

from tests.testlib import repo_path
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


def _get_import_names_from_dist_name(dist_name: str) -> list[ImportName]:
    metadata_dir = pkg.get_distribution(dist_name).egg_info
    with open("{}/{}".format(metadata_dir, "top_level.txt")) as top_level:
        import_names = top_level.read().rstrip().split("\n")
        # Skip the private modules (starting with an underscore)
        return [
            ImportName(name.replace("/", ".")) for name in import_names if not name.startswith("_")
        ]


def _get_import_names_from_pipfile() -> Iterable[ImportName]:
    # TODO: There are packages which are currently missing the top_level.txt,
    # so we need to hardcode the import names for those packages.
    # We couldn't find a better way to get from Pipfile package name to import name.
    # What we've tried:
    # * pip show <package_name> -> use the "Name" attribute
    # --> fails e.g already for "docstring_parser" (Name: docstring-parser)
    # --> pip show is really slow
    # * listing *all* import names explicit
    # --> huge maintenance effort...
    packagename_to_importname = {
        "black": "black",
        "docstring-parser": "docstring_parser",
        "idna": "idna",
        "jsonschema": "jsonschema",
        "pyparsing": "pyparsing",
        "uvicorn": "uvicorn",
        "more-itertools": "more_itertools",
        "ordered-set": "ordered_set",
        "openapi-spec-validator": "openapi_spec_validator",
        "pysaml2": "saml2",
        "pysmi_lextudio": "pysmi-lextudio",
    }

    for dist_name in _load_pipfile_data()["default"].keys():
        if dist_name in packagename_to_importname:
            yield ImportName(packagename_to_importname[dist_name])
            continue
        yield from _get_import_names_from_dist_name(dist_name)


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
        [f"python{python_version.major}", "-c", "import sys,json; json.dump(sys.path, sys.stdout)"],
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
    assert version.startswith("pip 23.2.1")


@pytest.mark.skip(
    reason="CMK-15485 Re-enable when ibm_db is 3.12 ready"
    "https://github.com/ibmdb/python-ibmdb/issues/890"
    "or replace with"
)
def test_04_pip_user_can_install_non_wheel_packages(site: Site) -> None:
    # Choose here a package which needs to be compiled from source to ensure that
    # the Python headers are found. Switch back to ibm_db when it is 3.12 ready:
    # https://github.com/ibmdb/python-ibmdb/issues/890
    package_name = "psutil"

    # We're testing this only for one supported pip command as building from source just takes too long
    pip_cmd = PipCommand(["pip3"], False)

    assert_install_package(
        pip_cmd.command + ["install", '--nobinary=":all:"', package_name], package_name, site
    )
    assert_local_package_install_path(site, package_name, _local_package_installation_path(site))
    assert_uninstall_and_purge_cache(pip_cmd, package_name, site)


@pytest.mark.parametrize("pip_cmd", SUPPORTED_PIP_CMDS)
def test_05_pip_user_can_install_wheel_packages(site: Site, pip_cmd: PipCommand) -> None:
    # We're using here another package which is needed for check_sql but not deployed by us
    package_name = "cx_Oracle"
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


@pytest.mark.skip(
    """
   Test relies on deprectated top_level.txt mechanism and yields too many false positives.
   TODO: We need a general rework of this test.
   """
)
def test_import_python_packages_which_are_defined_in_pipfile(site: Site) -> None:
    for import_name in _get_import_names_from_pipfile():
        module_file = import_module_and_get_file_path(site, import_name)
        # Skip namespace modules, they don't have __file__
        if module_file:
            assert module_file.startswith(site.root)


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
        ["python3", "-c", "import sysconfig; print(sysconfig.get_config_vars('CONFIG_ARGS'));"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    ).communicate()[0]
    assert "--enable-optimizations" in output
    assert "--with-lto" in output
