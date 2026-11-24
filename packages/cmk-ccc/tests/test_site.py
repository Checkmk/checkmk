#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from pathlib import Path

import pytest

from cmk.ccc.site import (
    get_agent_receiver_port,
    get_apache_port,
    get_omd_config,
    omd_site,
    url_prefix,
)


@pytest.fixture(name="uncached_omd_site")
def fixture_uncached_omd_site() -> Iterator[None]:
    """Clear omd_site()'s cache before and after the test"""
    omd_site.cache_clear()
    yield
    omd_site.cache_clear()


@pytest.mark.usefixtures("uncached_omd_site")
def test_omd_site_is_the_site_of_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OMD_SITE", "heute")

    assert omd_site() == "heute"


@pytest.mark.usefixtures("uncached_omd_site")
def test_omd_site_outside_of_a_site_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OMD_SITE", raising=False)

    with pytest.raises(RuntimeError, match="OMD_SITE"):
        omd_site()


@pytest.mark.usefixtures("uncached_omd_site")
def test_url_prefix_is_the_path_of_the_site(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OMD_SITE", "heute")

    assert url_prefix() == "/heute/"


def _omd_root(tmp_path: Path, site_conf: str) -> Path:
    (tmp_path / "etc" / "omd").mkdir(parents=True)
    (tmp_path / "etc" / "omd" / "site.conf").write_text(site_conf, encoding="utf-8")
    return tmp_path


def test_omd_config_has_the_settings_of_site_conf(tmp_path: Path) -> None:
    omd_root = _omd_root(
        tmp_path,
        "CONFIG_CORE='cmc'\nCONFIG_ADMIN_MAIL=''\nCONFIG_LIVESTATUS_TCP_ONLY_FROM='0.0.0.0 ::/0'\n",
    )

    assert get_omd_config(omd_root) == {
        "CONFIG_CORE": "cmc",
        "CONFIG_ADMIN_MAIL": "",
        "CONFIG_LIVESTATUS_TCP_ONLY_FROM": "0.0.0.0 ::/0",
    }


def test_apache_port_comes_from_site_conf(tmp_path: Path) -> None:
    omd_root = _omd_root(tmp_path, "CONFIG_APACHE_TCP_PORT='5002'\n")

    assert get_apache_port(omd_root) == 5002


def test_apache_port_defaults_to_80(tmp_path: Path) -> None:
    omd_root = _omd_root(tmp_path, "CONFIG_CORE='cmc'\n")

    assert get_apache_port(omd_root) == 80


def test_agent_receiver_port_comes_from_site_conf(tmp_path: Path) -> None:
    omd_root = _omd_root(tmp_path, "CONFIG_AGENT_RECEIVER_PORT='8001'\n")

    assert get_agent_receiver_port(omd_root) == 8001


def test_agent_receiver_port_defaults_to_8000(tmp_path: Path) -> None:
    omd_root = _omd_root(tmp_path, "CONFIG_CORE='cmc'\n")

    assert get_agent_receiver_port(omd_root) == 8000
