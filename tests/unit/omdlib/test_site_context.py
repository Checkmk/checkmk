#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

import os

import pytest

from omdlib.contexts import RootContext, SiteContext


# Explicitly don't patch the base path here
@pytest.fixture(autouse=True)
def omd_base_path() -> None:
    pass


def test_root_context() -> None:
    site = RootContext()
    assert site.name is None
    assert site.dir == "/"
    assert site.real_dir == "/"
    assert not site.is_site_context()


def test_site_context(monkeypatch: pytest.MonkeyPatch) -> None:
    site = SiteContext("dingeling")
    assert site.name == "dingeling"
    assert site.dir == "/omd/sites/dingeling"
    assert site.real_dir == "/opt/omd/sites/dingeling"
    assert site.tmp_dir == "/omd/sites/dingeling/tmp"
    assert site.version_meta_dir == "/omd/sites/dingeling/.version_meta"
    assert site.is_site_context()


def test_site_context_version(monkeypatch: pytest.MonkeyPatch) -> None:
    site = SiteContext("dingeling")
    monkeypatch.setattr(os, "readlink", lambda x: "../2018.08.11.cee")
    assert site.version == "2018.08.11.cee"


def test_site_context_replacements(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(os, "readlink", lambda x: "../2018.08.11.cee")
    site = SiteContext("dingeling")

    assert site.replacements["###SITE###"] == "dingeling"
    assert site.replacements["###ROOT###"] == "/omd/sites/dingeling"
    assert site.replacements["###EDITION###"] in ("raw", "enterprise", "cloud", "managed")
    assert len(site.replacements) == 3


def test_site_context_exists(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(os.path, "exists", lambda p: p == "/omd/sites/dingeling")

    site = SiteContext("dingeling")
    assert site.exists()

    site = SiteContext("dingelang")
    assert not site.exists()


def test_site_context_is_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        os, "listdir", lambda p: [] if p == "/omd/sites/dingeling" else ["abc", "version"]
    )

    site = SiteContext("dingeling")
    assert site.is_empty()

    site = SiteContext("dingelang")
    assert not site.is_empty()


def test_site_context_is_autostart(monkeypatch: pytest.MonkeyPatch) -> None:
    site = SiteContext("dingeling")

    with pytest.raises(Exception) as e:
        site.is_autostart()
    assert "not loaded yet" in str(e)

    site._config = {}
    site._config_loaded = True
    assert site.is_autostart()

    site._config = {"AUTOSTART": "on"}
    assert site.is_autostart()

    site._config = {"AUTOSTART": "off"}
    assert not site.is_autostart()


def test_site_context_is_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(os.path, "exists", lambda p: p == "/omd/apache/dingeling.conf")
    site = SiteContext("dingeling")
    assert not site.is_disabled()

    site = SiteContext("dingelang")
    assert site.is_disabled()
