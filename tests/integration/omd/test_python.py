#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# flake8: noqa

import os
import subprocess
from typing import List

import pkg_resources as pkg  # type: ignore[import]
import pytest  # type: ignore[import]
from pipfile import Pipfile  # type: ignore[import]

from tests.testlib import repo_path


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

    parsed_pipfile = Pipfile.load(filename=repo_path() + "/Pipfile")
    import_names = []
    for dist_name in parsed_pipfile.data["default"].keys():
        import_names.extend(_get_import_names_from_dist_name(dist_name))
    assert import_names
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
    assert version.startswith("Python 3.9.8")


def test_03_python_path(site):
    p = site.execute(["python3", "-c", "import sys ; print(sys.path)"], stdout=subprocess.PIPE)
    sys_path = eval(p.stdout.read())
    assert sys_path[0] == ""
    assert site.root + "/local/lib/python3" in sys_path
    assert site.root + "/lib/python3" in sys_path
    assert site.root + "/lib/python3.9" in sys_path

    for p in sys_path:
        if p != "" and not p.startswith(site.root):
            raise Exception("Found non site path %s in sys.path" % p)


def test_01_pip_exists(site):
    assert os.path.exists(site.root + "/bin/pip3")


def test_02_pip_path(site):
    p = site.execute(["which", "pip3"], stdout=subprocess.PIPE)
    path = p.stdout.read().strip()
    assert path == "/omd/sites/%s/bin/pip3" % site.id


def test_03_pip_interpreter_version(site):
    p = site.execute(["pip3", "-V"], stdout=subprocess.PIPE)
    version = p.stdout.read()
    assert version.startswith("pip 21.2.4")


@pytest.mark.parametrize("module_name", _get_import_names_from_pipfile())
def test_python_modules(site, module_name):
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


def test_python_preferred_encoding():
    import locale  # pylint: disable=import-outside-toplevel

    assert locale.getpreferredencoding() == "UTF-8"
