#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os

import pytest

import omdlib.main


def test_root_context():
    site = omdlib.main.RootContext()
    assert site.name is None
    assert site.dir == "/"
    assert site.real_dir == "/"
    assert not site.is_site_context()


def test_site_context(monkeypatch):
    site = omdlib.main.SiteContext("dingeling")
    assert site.name == "dingeling"
    assert site.dir == "/omd/sites/dingeling"
    assert site.real_dir == "/opt/omd/sites/dingeling"
    assert site.tmp_dir == "/omd/sites/dingeling/tmp"
    assert site.version_meta_dir == "/omd/sites/dingeling/.version_meta"
    assert site.is_site_context()


def test_site_context_version(monkeypatch):
    site = omdlib.main.SiteContext("dingeling")
    monkeypatch.setattr(os, "readlink", lambda x: "../2018.08.11.cee")
    assert site.version == "2018.08.11.cee"


def test_site_context_replacements(monkeypatch):
    site = omdlib.main.SiteContext("dingeling")
    assert site.replacements["###SITE###"] == "dingeling"
    assert site.replacements["###ROOT###"] == "/omd/sites/dingeling"
    assert len(site.replacements) == 2


def test_site_context_exists(monkeypatch):
    monkeypatch.setattr(os.path, "exists", lambda p: p == "/omd/sites/dingeling")

    site = omdlib.main.SiteContext("dingeling")
    assert site.exists()

    site = omdlib.main.SiteContext("dingelang")
    assert not site.exists()


def test_site_context_is_empty(monkeypatch):
    monkeypatch.setattr(
        os, "listdir", lambda p: [] if p == "/omd/sites/dingeling" else ["abc", "version"]
    )

    site = omdlib.main.SiteContext("dingeling")
    assert site.is_empty()

    site = omdlib.main.SiteContext("dingelang")
    assert not site.is_empty()


def test_site_context_is_autostart(monkeypatch):
    site = omdlib.main.SiteContext("dingeling")

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


def test_site_context_is_disabled(monkeypatch):
    monkeypatch.setattr(os.path, "exists", lambda p: p == "/omd/apache/dingeling.conf")
    site = omdlib.main.SiteContext("dingeling")
    assert not site.is_disabled()

    site = omdlib.main.SiteContext("dingelang")
    assert site.is_disabled()
