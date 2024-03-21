#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

import importlib
import subprocess

import pytest
from pytest import MonkeyPatch

from tests.testlib.base import Scenario

from cmk.utils.config_path import VersionedConfigPath
from cmk.utils.hostaddress import HostName

from cmk.checkengine.checking import CheckPluginName

import cmk.base.config as config
import cmk.base.core_nagios as core_nagios


@pytest.fixture(name="config_path")
def fixture_config_path() -> VersionedConfigPath:
    return VersionedConfigPath(42)


def test_compile_delayed_host_check(
    monkeypatch: MonkeyPatch, config_path: VersionedConfigPath
) -> None:
    hostname = HostName("localhost")
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_option("delay_precompile", True)
    config_cache = ts.apply(monkeypatch)

    # Ensure a host check is created
    monkeypatch.setattr(
        core_nagios,
        "_get_needed_plugin_names",
        lambda *args, **kw: (set(), {CheckPluginName("uptime")}, set()),
    )

    source_file = core_nagios.HostCheckStore.host_check_source_file_path(
        config_path,
        hostname,
    )
    compiled_file = core_nagios.HostCheckStore.host_check_file_path(config_path, hostname)

    assert config.delay_precompile is True
    assert not source_file.exists()
    assert not compiled_file.exists()

    # Write the host check source file
    host_check = core_nagios._dump_precompiled_hostcheck(
        config_cache,
        config_path,
        hostname,
        verify_site_python=False,
    )
    assert host_check is not None
    core_nagios.HostCheckStore().write(config_path, hostname, host_check)

    # The compiled file path links to the source file until it has been executed for the first
    # time. Then the symlink is replaced with the compiled file
    assert source_file.exists()
    assert compiled_file.exists()
    assert compiled_file.resolve() == source_file

    # Expect the command to fail: We don't have the correct environment to execute it.
    # But this is no problem for our test, we only want to see the result of the compilation.
    assert (
        subprocess.run(
            ["python3", str(compiled_file)],
            shell=False,
            close_fds=True,
            check=False,
        ).returncode
        == 1
    )
    assert compiled_file.resolve() != source_file
    with compiled_file.open("rb") as f:
        assert f.read().startswith(importlib.util.MAGIC_NUMBER)
