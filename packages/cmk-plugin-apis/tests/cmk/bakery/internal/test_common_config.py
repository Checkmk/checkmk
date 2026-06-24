#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

import os
import stat
from pathlib import Path

import pytest

from cmk.bakery.internal import (
    AgentConfig,
    DeploymentModeProvider,
    get_unix_agent_paths_keeper,
    LogicalPath,
    TargetPathsProvider,
    UnixSingleDirectoryKeeper,
)


def test_get_unix_agent_paths_keeper_multi_directory():
    agconf = {
        "agent_paths": {
            "bin": "/bin",
            "config": "/config",
            "lib": "/lib",
            "var": "/var",
            "tmp": "/tmp",
        }
    }
    keeper = get_unix_agent_paths_keeper(agconf)
    # Should be UnixMultipleDirectoryKeeper
    assert keeper.get_target_path(LogicalPath.BIN) == Path("/bin")
    assert keeper.get_target_path(LogicalPath.CONFIG) == Path("/config")
    assert keeper.get_target_path(LogicalPath.LIB) == Path("/lib")
    assert keeper.get_target_path(LogicalPath.VAR) == Path("/var")


def test_get_unix_agent_paths_keeper_single_directory():
    agconf = {
        "agent_paths": {
            "bin": "/irrelevant/bin",
            "config": "/irrelevant/config",
            "lib": "/irrelevant/lib",
            "var": "/irrelevant/var",
            "tmp": "/irrelevant/tmp",
        },
        "customize_agent_package": {"directory": {"installation_directory": "/custom/agent"}},
    }
    keeper = get_unix_agent_paths_keeper(agconf)
    # Should be UnixSingleDirectoryKeeper
    bin_path = keeper.get_target_path(LogicalPath.BIN)
    assert str(bin_path).startswith("/custom/agent/default/")


def test_multi_directory_all_paths():
    agconf = {
        "agent_paths": {
            "bin": "/opt/cmk/bin",
            "config": "/opt/cmk/config",
            "lib": "/opt/cmk/lib",
            "var": "/opt/cmk/var",
            "tmp": "/opt/cmk/tmp",
        }
    }
    provider = TargetPathsProvider(agconf)
    mapping = provider.get_target_path_mapping()
    assert mapping[LogicalPath.BIN] == Path("/opt/cmk/bin")
    assert mapping[LogicalPath.CONFIG] == Path("/opt/cmk/config")
    assert mapping[LogicalPath.LIB] == Path("/opt/cmk/lib")
    assert mapping[LogicalPath.VAR] == Path("/opt/cmk/var")
    assert provider.get_tmpdir() == "/opt/cmk/tmp"
    assert provider.get_installdir() is None


def test_single_directory_custom_install():
    agconf = {
        "agent_paths": {
            "bin": "/irrelevant/bin",
            "config": "/irrelevant/config",
            "lib": "/irrelevant/lib",
            "var": "/irrelevant/var",
            "tmp": "/irrelevant/tmp",
        },
        "customize_agent_package": {"directory": {"installation_directory": "/custom/agent"}},
    }
    provider = TargetPathsProvider(agconf)
    assert provider.get_installdir() == Path("/custom/agent/default")
    mapping = provider.get_target_path_mapping()
    # Check that each LogicalPath maps to the expected path
    expected = {
        LogicalPath.BIN: Path("/custom/agent/default/package/bin"),
        LogicalPath.CONFIG: Path("/custom/agent/default/package/config"),
        LogicalPath.LIB: Path("/custom/agent/default/package"),
        LogicalPath.LOCAL: Path("/custom/agent/default/package/local"),
        LogicalPath.PLUGINS: Path("/custom/agent/default/package/plugins"),
        LogicalPath.AGENT: Path("/custom/agent/default/package/agent"),
        LogicalPath.HOME: Path("/custom/agent/default/package"),
        LogicalPath.VAR: Path("/custom/agent/default/runtime"),
        LogicalPath.ROOT: Path("/"),
        LogicalPath.ETC: Path("/etc"),
    }
    for logical_path, expected_path in expected.items():
        assert mapping[logical_path] == expected_path, (
            f"{logical_path}: {mapping[logical_path]} != {expected_path}"
        )


def test_multi_directory_no_tmp():
    agconf = {
        "agent_paths": {
            "bin": "/bin",
            "config": "/config",
            "lib": "/lib",
            "var": "/var",
            # no tmp
        }
    }
    provider = TargetPathsProvider(agconf)
    assert provider.get_tmpdir() is None


def test_single_directory_custom_tmpdir():
    agconf = {
        "agent_paths": {
            "bin": "/bin",
            "config": "/config",
            "lib": "/lib",
            "var": "/var",
            "tmp": "/tmp",
        },
        "customize_agent_package": {
            "directory": {"installation_directory": "/foo/bar", "tmpdir": "/tmp/custom"}
        },
    }
    provider = TargetPathsProvider(agconf)
    assert provider.get_tmpdir() == "/tmp/custom"


def test_invalid_config_missing_agent_paths():
    agconf: AgentConfig = {}
    with pytest.raises(KeyError):
        TargetPathsProvider(agconf)


def test_deployment_mode_provider_legacy_agent_user():
    agconf = {"agent_user": {"user": "legacyuser"}}
    provider = DeploymentModeProvider(agconf)
    assert provider.get_agent_user() == "legacyuser"
    assert provider.get_agent_controller_user() == "cmk-agent"
    assert provider.get_agent_user_gid() is None
    assert provider.get_agent_controller_gid() is None


def test_deployment_mode_provider_new_agent_user():
    agconf = {"agent_user": {"user": "legacyuser"}}
    provider = DeploymentModeProvider(agconf)
    assert provider.get_agent_user() == "legacyuser"
    assert provider.get_agent_controller_user() == "cmk-agent"
    assert provider.get_agent_user_gid() is None
    assert provider.get_agent_controller_gid() is None


def test_deployment_mode_provider_root_mode():
    agconf: AgentConfig = {}
    provider = DeploymentModeProvider(agconf)
    assert provider.get_agent_user() == "root"
    assert provider.get_agent_controller_user() == "cmk-agent"
    assert provider.get_agent_user_gid() is None
    assert provider.get_agent_controller_gid() is None


def test_deployment_mode_provider_root_mode_custom_gid():
    agconf = {
        "customize_agent_package": {
            "deployment_mode": {
                "mode": "root",
                "user_deployment": {"user": "cmk-agent", "gid": 5678, "creation_options": "auto"},
            },
            "directory": {"installation_directory": "dummy"},
        }
    }
    provider = DeploymentModeProvider(agconf)
    assert provider.get_agent_user() == "root"
    assert provider.get_agent_controller_user() == "cmk-agent"
    # Agent user runs as root, so the GID customization applies only to the controller user.
    assert provider.get_agent_user_gid() is None
    assert provider.get_agent_controller_gid() == 5678


def test_deployment_mode_provider_non_root_mode():
    agconf = {
        "customize_agent_package": {
            "deployment_mode": {
                "mode": "non_root",
                "user_deployment": {"user": "nonrootuser", "gid": 1234, "creation_options": "auto"},
            },
            "directory": {"installation_directory": "dummy"},
        }
    }
    provider = DeploymentModeProvider(agconf)
    assert provider.get_agent_user() == "nonrootuser"
    assert provider.get_agent_controller_user() == "nonrootuser"
    assert provider.get_agent_user_gid() == 1234
    assert provider.get_agent_controller_gid() == 1234


def test_unix_single_directory_keeper_make_package_structure(tmp_path):
    # For whatever reason, the umask is set to 0o007 by default in all our unit tests.
    # We need 0o022 here to see the expected permissions in the created directories.
    # When executed in the agent bakery, the umask is explicitly set to 0o022.
    old_umask = os.umask(0o022)
    try:
        install_dir = "/foo/bar"
        package_name = "default"
        keeper = UnixSingleDirectoryKeeper(install_dir, package_name)
        keeper.make_package_structure(tmp_path)
        base = tmp_path / "foo" / "bar" / "default"

        def mode(path):
            return stat.S_IMODE(path.stat().st_mode)

        # Accessible for others (0o755)
        assert mode(base / "package") == 0o755
        assert mode(base / "package" / "bin") == 0o755
        assert mode(base / "package" / "plugins") == 0o755
        # Forbidden for others (0o750)
        assert mode(base / "package" / "agent") == 0o750
        assert mode(base / "package" / "local") == 0o750
        assert mode(base / "package" / "config") == 0o750
        assert mode(base / "package" / "scripts") == 0o750
        assert mode(base / "runtime") == 0o750
        assert mode(base / "runtime" / "log") == 0o750
        assert mode(base / "runtime" / "spool") == 0o750
        assert mode(base / "runtime" / "job") == 0o750
        assert mode(base / "runtime" / "controller") == 0o750
    finally:
        os.umask(old_umask)
