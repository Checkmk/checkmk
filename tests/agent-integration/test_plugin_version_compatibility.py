#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name

from pathlib import Path

import pytest

import tests.testlib as testlib
from tests.testlib.pylint_cmk import is_python_file

import docker  # type: ignore[import]


@pytest.fixture(scope="module")
def docker_client():
    return docker.DockerClient()


@pytest.fixture(scope="module")
def python_container(request, docker_client):
    c = docker_client.containers.run(
        image="shimizukawa/python-all",
        command=["python2.5", "-c", "import time; time.sleep(9999)"],
        detach=True,
        volumes={
            testlib.cmk_path(): {"bind": "/cmk", "mode": "ro"},
        },
    )
    yield c
    c.remove(force=True)


def _get_python_plugins():
    return [
        "agents/plugins/%s" % p.name
        for p in Path(testlib.cmk_path(), "agents", "plugins").iterdir()
        if is_python_file(str(p), "python") or is_python_file(str(p), "python3")
    ]


@pytest.mark.parametrize("plugin_path", _get_python_plugins())
@pytest.mark.parametrize("python_version", ["2.5", "2.6", "2.7", "3.7"])
def test_agent_plugin_syntax_compatibility(python_container, plugin_path, python_version) -> None:
    if plugin_path.endswith(".py2") and not python_version.startswith("2"):
        pytest.skip(
            "Do not test .py2 with Python 3 "
            "(Plugins are needed for compatibilit with 2.5 and newer)"
        )

    if not plugin_path.endswith(".py2") and python_version in ["2.5", "2.6"]:
        pytest.skip(
            "Do not test .py with Python 2 "
            "(Plugins are needed for compatibilit with 2.5 and newer)"
        )

    _exit_code, output = python_container.exec_run(
        ["python%s" % python_version, ("/cmk/%s" % plugin_path)],
        workdir="/cmk",
    )

    assert "SyntaxError: " not in output.decode("utf-8")
