#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# flake8: noqa

import importlib
import json
import os
import re
import subprocess
from typing import NewType

import pkg_resources as pkg
import pytest
from pipfile import Pipfile  # type: ignore[import]
from semver import VersionInfo  # type: ignore[import]

from tests.testlib import repo_path
from tests.testlib.site import Site

ImportName = NewType("ImportName", "str")

# TODO: Currently we need to invoke pip as a module and cannot use pip3 only.
# This is most likley due to the fact, that we set "PIP_TARGET" in pip3 during intermediate install
# os.environ["PIP_TARGET"] = os.path.join(os.environ["OMD_ROOT"], "local/lib/python3")
PIP_CMD = ["python3", "-m", "pip"]


def _load_pipfile_data() -> dict:
    return Pipfile.load(filename=str(repo_path() / "Pipfile")).data


def _get_import_names_from_dist_name(dist_name: str) -> list[ImportName]:

    # We still have some exceptions to the rule...
    dist_renamings = {
        "repoze-profile": "repoze.profile",
    }

    metadata_dir = pkg.get_distribution(
        dist_renamings.get(dist_name, dist_name)
    ).egg_info  # type: ignore[attr-defined]
    with open("{}/{}".format(metadata_dir, "top_level.txt")) as top_level:
        import_names = top_level.read().rstrip().split("\n")
        # Skip the private modules (starting with an underscore)
        return [
            ImportName(name.replace("/", ".")) for name in import_names if not name.startswith("_")
        ]


def _get_import_names_from_pipfile() -> list[ImportName]:

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
        "docstring_parser": "docstring_parser",
        "idna": "idna",
        "jsonschema": "jsonschema",
        "pyparsing": "pyparsing",
        "typing_extensions": "typing_extensions",
        "uvicorn": "uvicorn",
        "more-itertools": "more_itertools",
        "ordered-set": "ordered_set",
        "openapi-spec-validator": "openapi_spec_validator",
    }

    import_names = []
    for dist_name in _load_pipfile_data()["default"].keys():
        if dist_name in packagename_to_importname:
            import_names.append(ImportName(packagename_to_importname[dist_name]))
            continue
        import_names.extend(_get_import_names_from_dist_name(dist_name))
    assert import_names
    return import_names


def _get_python_version_from_defines_make() -> VersionInfo:
    with (repo_path() / "defines.make").open() as defines:
        python_version = (
            [line for line in defines.readlines() if re.match(r"^PYTHON_VERSION .*:=", line)][0]
            .split(":=")[1]
            .strip()
        )
    return VersionInfo.parse(python_version)


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


def test_03_pip_interpreter_version(site: Site) -> None:
    p = site.execute(PIP_CMD + ["-V"], stdout=subprocess.PIPE)
    version = p.stdout.read() if p.stdout else "<NO STDOUT>"
    assert version.startswith("pip 22.0.4")


@pytest.mark.parametrize(
    "package_name",
    [
        # WARNING:
        # Installing from source takes a long time - and so does the test.
        # So be sure adding new packages here has a real benefit.
        "ibm_db",  # Needed by check_sql: no wheels, so pip must be able to find the Python headers
    ],
)
def test_04_pip_user_can_install_and_uninstall_packages_not_shipped_with_omd(site, package_name):
    p = site.execute(
        PIP_CMD + ["install", "--user", package_name],
        stdout=subprocess.PIPE,
    )
    install_stdout = p.stdout.read()

    assert "Successfully installed" in install_stdout, install_stdout

    for cmd in (
        ["python3", "-c", f"import {package_name}"],
        PIP_CMD + ["uninstall", "-y", package_name],
        PIP_CMD + ["cache", "purge"],
    ):
        p = site.execute(cmd, stdout=subprocess.PIPE)
        p.communicate()
        assert p.returncode == 0


@pytest.mark.parametrize("import_name", _get_import_names_from_pipfile())
def test_import_python_packages_which_are_defined_in_pipfile(
    site: Site,
    import_name: ImportName,
) -> None:

    module = importlib.import_module(import_name)

    # Skip namespace modules, they don't have __file__
    if module.__file__:
        assert module.__file__.startswith(site.root)


def test_python_preferred_encoding() -> None:
    import locale  # pylint: disable=import-outside-toplevel

    assert locale.getpreferredencoding() == "UTF-8"
