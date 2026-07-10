#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

import cmk.utils.paths
from cmk.ccc.version import Edition
from cmk.plugins.checkmk.rulesets import cmk_update_agent


@pytest.fixture(name="config_dir")
def _config_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    config_dir = tmp_path / "conf.d"
    config_dir.mkdir()
    monkeypatch.setattr(cmk.utils.paths, "check_mk_config_dir", config_dir)
    return config_dir


def _set_edition(monkeypatch: pytest.MonkeyPatch, edition: Edition) -> None:
    monkeypatch.setattr(cmk_update_agent, "edition", lambda _omd_root: edition)


def test_returns_false_when_edition_is_not_ultimatemt(
    monkeypatch: pytest.MonkeyPatch, config_dir: Path
) -> None:
    _set_edition(monkeypatch, Edition.COMMUNITY)
    # Even with a remote-site marker present, a non-ULTIMATEMT edition short-circuits.
    (config_dir / "distributed_wato.mk").write_text("is_distributed_setup_remote_site = True\n")

    assert cmk_update_agent._is_ultimatemt_remote_site() is False


def test_returns_false_when_distributed_wato_file_is_missing(
    monkeypatch: pytest.MonkeyPatch, config_dir: Path
) -> None:
    _set_edition(monkeypatch, Edition.ULTIMATEMT)
    assert not (config_dir / "distributed_wato.mk").exists()

    assert cmk_update_agent._is_ultimatemt_remote_site() is False


def test_returns_false_when_distributed_wato_file_is_empty(
    monkeypatch: pytest.MonkeyPatch, config_dir: Path
) -> None:
    _set_edition(monkeypatch, Edition.ULTIMATEMT)
    (config_dir / "distributed_wato.mk").write_text("")

    assert cmk_update_agent._is_ultimatemt_remote_site() is False


def test_returns_true_when_is_distributed_setup_remote_site_flag_set(
    monkeypatch: pytest.MonkeyPatch, config_dir: Path
) -> None:
    _set_edition(monkeypatch, Edition.ULTIMATEMT)
    (config_dir / "distributed_wato.mk").write_text("is_distributed_setup_remote_site = True\n")

    assert cmk_update_agent._is_ultimatemt_remote_site() is True


def test_returns_true_when_legacy_is_wato_slave_site_flag_set(
    monkeypatch: pytest.MonkeyPatch, config_dir: Path
) -> None:
    # On 2.4 sites the flag is still named `is_wato_slave_site`.
    _set_edition(monkeypatch, Edition.ULTIMATEMT)
    (config_dir / "distributed_wato.mk").write_text("is_wato_slave_site = True\n")

    assert cmk_update_agent._is_ultimatemt_remote_site() is True


def test_returns_false_when_remote_site_flags_are_false(
    monkeypatch: pytest.MonkeyPatch, config_dir: Path
) -> None:
    _set_edition(monkeypatch, Edition.ULTIMATEMT)
    (config_dir / "distributed_wato.mk").write_text(
        "is_distributed_setup_remote_site = False\nis_wato_slave_site = False\n"
    )

    assert cmk_update_agent._is_ultimatemt_remote_site() is False


def test_migrate_proxy_old_format_none() -> None:
    assert cmk_update_agent._migrate_proxy_old_format(None) == ("no_proxy", None)


def test_migrate_proxy_old_format_env() -> None:
    assert cmk_update_agent._migrate_proxy_old_format("env") == ("env_proxy", "env")


def test_migrate_proxy_old_format_http_without_credentials() -> None:
    # 2.4.0 stores an empty dict here when the (optional) credentials sub-dictionary
    # is not filled in, rather than omitting the "proxy_protocol" tuple's second element.
    old_value = {
        "server": "proxy.example.com",
        "port": 8080,
        "proxy_protocol": ("http", {}),
    }

    assert cmk_update_agent._migrate_proxy_old_format(old_value) == (
        "explicit_proxy",
        {
            "server": "proxy.example.com",
            "port": 8080,
            "proxy_protocol": "http",
        },
    )


def test_migrate_proxy_old_format_socks5_without_credentials() -> None:
    old_value = {
        "server": "proxy.example.com",
        "port": 1080,
        "proxy_protocol": ("socks5", {}),
    }

    assert cmk_update_agent._migrate_proxy_old_format(old_value) == (
        "explicit_proxy",
        {
            "server": "proxy.example.com",
            "port": 1080,
            "proxy_protocol": "socks5",
        },
    )


def test_migrate_proxy_old_format_http_with_credentials() -> None:
    old_value = {
        "server": "proxy.example.com",
        "port": 8080,
        "proxy_protocol": ("http", {"credentials": ("user", "password")}),
    }

    assert cmk_update_agent._migrate_proxy_old_format(old_value) == (
        "explicit_proxy",
        {
            "server": "proxy.example.com",
            "port": 8080,
            "proxy_protocol": "http",
            "credentials": {"user": "user", "password": "password"},
        },
    )


def test_migrate_proxy_old_format_socks4() -> None:
    old_value = {
        "server": "proxy.example.com",
        "port": 1080,
        "proxy_protocol": ("socks4", None),
    }

    assert cmk_update_agent._migrate_proxy_old_format(old_value) == (
        "explicit_proxy",
        {
            "server": "proxy.example.com",
            "port": 1080,
            "proxy_protocol": "socks4",
        },
    )


def test_migrate_proxy_old_format_new_format_passthrough() -> None:
    new_value = ("explicit_proxy", {"server": "proxy.example.com", "port": 8080})

    assert cmk_update_agent._migrate_proxy_old_format(new_value) == new_value
