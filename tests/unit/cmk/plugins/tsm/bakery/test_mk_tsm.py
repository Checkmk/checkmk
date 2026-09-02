#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.bakery.v2_unstable import OS, Plugin, PluginConfig, Secret
from cmk.plugins.tsm.bakery.mk_tsm import bakery_plugin_mk_tsm

_CONFIG_LINES = ["# Credentials for dsmadmc:", "TSM_USER=admin", "TSM_PASSWORD=mysecret"]


def _auth(password: Secret) -> dict[str, object]:
    return {"user": "admin", "password": password}


def test_deploy_sync_explicit_password() -> None:
    conf = bakery_plugin_mk_tsm.parameter_parser(
        {
            "deployment": ("sync", None),
            "auth": _auth(Secret("mysecret", "explicit_password", "****")),
        }
    )
    assert list(bakery_plugin_mk_tsm.files_function(conf)) == [
        artifact
        for base_os in (OS.LINUX, OS.AIX, OS.SOLARIS)
        for artifact in (
            Plugin(base_os=base_os, source=Path("mk_tsm"), interval=None),
            PluginConfig(
                base_os=base_os,
                lines=_CONFIG_LINES,
                target=Path("tsm.cfg"),
                include_header=True,
            ),
        )
    ]


def test_deploy_cached_sets_interval() -> None:
    conf = bakery_plugin_mk_tsm.parameter_parser(
        {
            "deployment": ("cached", 300.0),
            "auth": _auth(Secret("mysecret", "explicit_password", "****")),
        }
    )
    plugins = [a for a in bakery_plugin_mk_tsm.files_function(conf) if isinstance(a, Plugin)]
    assert [p.interval for p in plugins] == [300.0, 300.0, 300.0]


def test_stored_password_is_written_through() -> None:
    """The backend resolves the password store lookup and hands us a Secret."""
    conf = bakery_plugin_mk_tsm.parameter_parser(
        {
            "deployment": ("sync", None),
            "auth": _auth(Secret("looked_up_secret", "stored_password", "pw_id_1")),
        }
    )
    configs = [a for a in bakery_plugin_mk_tsm.files_function(conf) if isinstance(a, PluginConfig)]
    assert configs
    for config in configs:
        assert "TSM_PASSWORD=looked_up_secret" in config.lines


def test_password_needing_shell_quoting() -> None:
    conf = bakery_plugin_mk_tsm.parameter_parser(
        {
            "deployment": ("sync", None),
            "auth": _auth(Secret("pass;rm -rf /", "explicit_password", "****")),
        }
    )
    (_plugin, config, *_rest) = bakery_plugin_mk_tsm.files_function(conf)
    assert isinstance(config, PluginConfig)
    assert "TSM_PASSWORD='pass;rm -rf /'" in config.lines


def test_do_not_deploy() -> None:
    conf = bakery_plugin_mk_tsm.parameter_parser(
        {
            "deployment": ("do_not_deploy", None),
            "auth": _auth(Secret("mysecret", "explicit_password", "****")),
        }
    )
    assert not list(bakery_plugin_mk_tsm.files_function(conf))


def test_deployment_defaults_to_do_not_deploy() -> None:
    conf = bakery_plugin_mk_tsm.parameter_parser(
        {"auth": _auth(Secret("mysecret", "explicit_password", "****"))}
    )
    assert not list(bakery_plugin_mk_tsm.files_function(conf))


def test_missing_auth() -> None:
    conf = bakery_plugin_mk_tsm.parameter_parser({"deployment": ("sync", None)})
    with pytest.raises(ValueError, match="Missing 'auth' configuration"):
        list(bakery_plugin_mk_tsm.files_function(conf))
