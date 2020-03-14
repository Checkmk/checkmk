#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name

from pathlib import Path

import pytest  # type: ignore[import]
import docker  # type: ignore[import]

import testlib
import testlib.pylint_cmk


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
            testlib.cmk_path(): {
                'bind': '/cmk',
                'mode': 'ro'
            },
        },
    )
    yield c
    c.remove(force=True)


def _get_python_plugins():
    return [
        "agents/plugins/%s" % p.name
        for p in Path(testlib.cmk_path(), "agents", "plugins").iterdir()
        if testlib.pylint_cmk.is_python_file(str(p), "python") or
        testlib.pylint_cmk.is_python_file(str(p), "python3")
    ]


@pytest.mark.parametrize("plugin_path", _get_python_plugins())
@pytest.mark.parametrize("python_version", ["2.5", "2.6", "2.7"])
def test_agent_plugin_syntax_compatibility(python_container, plugin_path, python_version):
    _exit_code, output = python_container.exec_run(
        ["python%s" % python_version, ("%s/%s" % (testlib.cmk_path(), plugin_path))],
        workdir="/cmk",
    )

    assert "SyntaxError: " not in output.decode("utf-8")
