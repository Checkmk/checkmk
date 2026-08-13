#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Smoke test for the mk_docker agent plug-in.

The plug-in has to stay importable on every Python version listed in
bootstrap.sh. Nothing else imports it, so without this test a construct like an
f-string slips in unnoticed and only blows up on an old monitored system.

Keep this module compatible with the oldest Python we support here, too: no
f-strings, no variable annotations, no typing imports.
"""

import sys
import types

import pytest


def _install_docker_stub():
    # type: () -> None
    """mk_docker imports docker at import time, but it is not installed here."""
    docker = types.ModuleType("docker")
    setattr(docker, "__version__", "7.0.0")
    setattr(docker, "DockerClient", type("DockerClient", (object,), {}))

    errors = types.ModuleType("docker.errors")
    for name in ("APIError", "ImageNotFound", "NotFound"):
        setattr(errors, name, type(name, (Exception,), {}))
    setattr(docker, "errors", errors)

    utils = types.ModuleType("docker.utils")
    socket = types.ModuleType("docker.utils.socket")
    setattr(utils, "socket", socket)
    setattr(docker, "utils", utils)

    sys.modules["docker"] = docker
    sys.modules["docker.errors"] = errors
    sys.modules["docker.utils"] = utils
    sys.modules["docker.utils.socket"] = socket


def _mk_docker():
    # type: () -> types.ModuleType
    """Import the plug-in with a stubbed out docker library.

    We always stub, so that this behaves the same no matter whether the real
    docker library happens to be installed.
    """
    _install_docker_stub()

    import agents.plugins.mk_docker

    return agents.plugins.mk_docker


def test_plugin_is_importable():
    # type: () -> None
    """Guards against syntax and imports that are too new for old agents."""
    assert _mk_docker().__version__


def test_get_config_falls_back_to_the_defaults():
    # type: () -> None
    mk_docker = _mk_docker()
    config = mk_docker.get_config("/does/not/exist.cfg")
    assert config == mk_docker.DEFAULT_CFG_SECTION


def test_is_disabled_section():
    # type: () -> None
    mk_docker = _mk_docker()
    config = {"skip_sections": "docker_node_images, docker_node_network"}
    assert mk_docker.is_disabled_section(config, "docker_node_images")
    # entries are stripped of surrounding whitespace
    assert mk_docker.is_disabled_section(config, "docker_node_network")
    assert not mk_docker.is_disabled_section(config, "docker_node_info")
    # a section is only skipped on a full match, not on a prefix of an entry
    assert not mk_docker.is_disabled_section(config, "docker_node")


def test_is_disabled_section_skips_nothing_by_default():
    # type: () -> None
    mk_docker = _mk_docker()
    config = mk_docker.get_config("/does/not/exist.cfg")
    for name, _section in mk_docker.NODE_SECTIONS:
        assert not mk_docker.is_disabled_section(config, name)


def test_time_it_keeps_the_wrapped_function_intact():
    # type: () -> None
    mk_docker = _mk_docker()

    def sample(a, b=2):
        # type: (int, int) -> int
        """the docstring"""
        return a + b

    timed = mk_docker.time_it(sample)
    assert timed.__name__ == "sample"
    assert timed.__doc__ == "the docstring"
    assert timed(1) == 3
    assert timed(1, b=4) == 5


def test_time_it_propagates_exceptions():
    # type: () -> None
    mk_docker = _mk_docker()

    def boom():
        # type: () -> None
        raise ValueError("kaboom")

    with pytest.raises(ValueError, match="kaboom"):
        mk_docker.time_it(boom)()
