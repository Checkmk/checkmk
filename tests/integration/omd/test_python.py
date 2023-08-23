#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# flake8: noqa

import os
import subprocess
from pathlib import Path
import importlib

import pytest  # type: ignore[import]
import pkg_resources as pkg
from typing import List, NamedTuple
from pipfile import Pipfile  # type: ignore[import]
from testlib import repo_path
from tests.testlib.site import Site  # type: ignore[import]


class PipCommand(NamedTuple):
    command: List[str]
    needs_target_as_commandline: bool


SUPPORTED_PIP_CMDS = (
    PipCommand(["python3", "-m", "pip"], True),
    PipCommand(["pip3"], False),  # Target is set in the wrapper script as cmd line
    PipCommand(["pip3.8"], False),  # Target is set in the wrapper script as cmd line
)


def _local_package_installation_path(site: Site) -> Path:
    return Path(f"{site.root}", "local/lib/python3")


def assert_local_package_install_path(package_name: str,
                                      local_package_installation_path: Path) -> None:
    module = importlib.import_module(package_name)
    assert module.__file__

    # We only want to install into local as mkp will search there
    assert local_package_installation_path in Path(module.__file__).parents


def assert_install_package(cmd: List[str], package_name: str, site: Site) -> None:
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


def _get_import_names_from_dist_name(dist_name: str) -> List[str]:

    # We still have some exceptions to the rule...
    dist_renamings = {
        'repoze-profile': 'repoze.profile',
    }

    metadata_dir = pkg.get_distribution(dist_renamings.get(
        dist_name, dist_name)).egg_info  # type: ignore[attr-defined]
    with open('%s/%s' % (metadata_dir, 'top_level.txt')) as top_level:
        import_names = top_level.read().rstrip().split("\n")
        # Skip the private modules (starting with an underscore)
        return [name for name in import_names if not name.startswith("_")]


def _get_import_names_from_pipfile() -> List[str]:

    static_import_names = ["typing_extensions", "rsa"]

    parsed_pipfile = Pipfile.load(filename=repo_path() + "/Pipfile")
    import_names = []
    for dist_name in parsed_pipfile.data["default"].keys():
        if dist_name not in static_import_names:
            import_names.extend(_get_import_names_from_dist_name(dist_name))
    assert import_names
    import_names.extend(static_import_names)
    return import_names


def test_01_python_interpreter_exists(site):
    assert os.path.exists(site.root + "/bin/python3")


def test_02_python_interpreter_path(site):
    p = site.execute(["which", "python3"], stdout=subprocess.PIPE)
    path = p.stdout.read().strip()
    assert path == "/omd/sites/%s/bin/python3" % site.id


def test_03_python_interpreter_version(site):
    p = site.execute(["python3", "-V"], stdout=subprocess.PIPE)
    version = p.stdout.read()
    assert version.startswith("Python 3.8.17")


def test_03_python_path(site):
    p = site.execute(["python3", "-c", "import sys ; print(sys.path)"], stdout=subprocess.PIPE)
    sys_path = eval(p.stdout.read())
    assert sys_path[0] == ""
    assert site.root + "/local/lib/python3" in sys_path
    assert site.root + "/lib/python3" in sys_path
    assert site.root + "/lib/python3.8" in sys_path

    for p in sys_path:
        if p != "" and not p.startswith(site.root):
            raise Exception("Found non site path %s in sys.path" % p)


def test_01_pip_exists(site):
    assert os.path.exists(site.root + "/bin/pip3")


def test_02_pip_path(site):
    p = site.execute(["which", "pip3"], stdout=subprocess.PIPE)
    path = p.stdout.read().strip()
    assert path == "/omd/sites/%s/bin/pip3" % site.id


@pytest.mark.parametrize(
    "pip_cmd",
    SUPPORTED_PIP_CMDS,
)
def test_03_pip_interpreter_version(site: Site, pip_cmd):
    p = site.execute(pip_cmd.command + ["-V"], stdout=subprocess.PIPE)
    version = p.stdout.read() if p.stdout else "<NO STDOUT>"
    assert version.startswith("pip 23.0.1")


def test_04_pip_user_can_install_non_wheel_packages(site):
    # ibm_db must be compiled from source, so choosing this also ensures that the Python headers
    # can be found by pip
    package_name = "ibm_db"

    # We're testing this only for one supported pip command as building from source just takes too long
    pip_cmd = PipCommand(["pip3"], False)

    assert_install_package(pip_cmd.command + ["install", package_name], package_name, site)
    assert_local_package_install_path(package_name, _local_package_installation_path(site))
    assert_uninstall_and_purge_cache(pip_cmd, package_name, site)


@pytest.mark.parametrize("pip_cmd", SUPPORTED_PIP_CMDS)
def test_05_pip_user_can_install_wheel_packages(site: Site, pip_cmd: PipCommand):
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
    assert_local_package_install_path(package_name, _local_package_installation_path(site))
    assert_uninstall_and_purge_cache(pip_cmd, package_name, site)


@pytest.mark.parametrize("module_name", _get_import_names_from_pipfile())
def test_python_modules(site, module_name):
    # TODO: Clarify and remove skipping of obscure modules
    # Skip those modules for now, they throw:
    # >       found = self._search_paths(context.pattern, context.path)
    # E       AttributeError: 'Context' object has no attribute 'pattern'
    if module_name in ("jsonschema", "openapi_spec_validator"):
        return
    module = importlib.import_module(module_name)

    # Skip namespace modules, they don't have __file__
    if module.__file__:
        assert module.__file__.startswith(site.root)


def test_python_preferred_encoding():
    import locale  # pylint: disable=import-outside-toplevel
    assert locale.getpreferredencoding() == "UTF-8"
