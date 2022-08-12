#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# flake8: noqa

import json
import os
import re
import subprocess
from typing import List

import pkg_resources as pkg  # type: ignore[import]
import pytest  # type: ignore[import]
from pipfile import Pipfile  # type: ignore[import]
from semver import VersionInfo  # type: ignore[import]

from tests.testlib import repo_path
from tests.testlib.site import Site


def _load_pipfile_data() -> dict:
    return Pipfile.load(filename=repo_path() + "/Pipfile").data


def _get_import_names_from_dist_name(dist_name: str) -> List[str]:

    # We still have some exceptions to the rule...
    dist_renamings = {
        "repoze-profile": "repoze.profile",
    }

    metadata_dir = pkg.get_distribution(
        dist_renamings.get(dist_name, dist_name)
    ).egg_info  # type: ignore[attr-defined]
    with open("%s/%s" % (metadata_dir, "top_level.txt")) as top_level:
        import_names = top_level.read().rstrip().split("\n")
        # Skip the private modules (starting with an underscore)
        return [name.replace("/", ".") for name in import_names if not name.startswith("_")]


def _get_import_names_from_pipfile() -> List[str]:

    # TODO: There are packages which are currently missing the top_level.txt, so we're hardcoding the import names
    static_import_names = ["typing_extensions"]

    import_names = []
    for dist_name in _load_pipfile_data()["default"].keys():
        if dist_name not in static_import_names:
            import_names.extend(_get_import_names_from_dist_name(dist_name))
    assert import_names
    import_names.extend(static_import_names)
    return import_names


def _get_python_version_from_defines_make() -> VersionInfo:
    with open(repo_path() + "/defines.make") as defines:
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
        site.root + f"/lib/python{python_version.major}/plus",
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
    p = site.execute(["pip3", "-V"], stdout=subprocess.PIPE)
    version = p.stdout.read() if p.stdout else "<NO STDOUT>"
    assert version.startswith("pip 22.0.4")


@pytest.mark.parametrize("module_name", _get_import_names_from_pipfile())
def test_python_modules(site: Site, module_name) -> None:  # type:ignore[no-untyped-def]
    # TODO: Clarify and remove skipping of obscure modules
    # Skip those modules for now, they throw:
    # >       found = self._search_paths(context.pattern, context.path)
    # E       AttributeError: 'Context' object has no attribute 'pattern'
    if module_name in ("jsonschema", "openapi_spec_validator"):
        return
    import importlib  # pylint: disable=import-outside-toplevel

    module = importlib.import_module(module_name)

    # Skip namespace modules, they don't have __file__
    if module.__file__:
        assert module.__file__.startswith(site.root)


def test_python_preferred_encoding() -> None:
    import locale  # pylint: disable=import-outside-toplevel

    assert locale.getpreferredencoding() == "UTF-8"
