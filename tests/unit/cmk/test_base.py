#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.utils.version as cmk_version


def test_version():
    assert isinstance(cmk_version.__version__, str)


def test_is_enterprise_edition(monkeypatch):
    monkeypatch.setattr(cmk_version, "omd_version", lambda: "1.4.0i1.cre")
    cmk_version.edition_short.cache_clear()
    assert cmk_version.is_enterprise_edition() is False
    monkeypatch.setattr(cmk_version, "omd_version", lambda: "1.4.0i1.cee")
    cmk_version.edition_short.cache_clear()
    assert cmk_version.is_enterprise_edition() is True
    monkeypatch.setattr(cmk_version, "omd_version", lambda: "2016.09.22.cee")
    cmk_version.edition_short.cache_clear()
    assert cmk_version.is_enterprise_edition() is True
    monkeypatch.setattr(cmk_version, "omd_version", lambda: "2016.09.22.cfe")
    cmk_version.edition_short.cache_clear()
    assert cmk_version.is_enterprise_edition() is False
    cmk_version.edition_short.cache_clear()


def test_is_raw_edition(monkeypatch):
    monkeypatch.setattr(cmk_version, "omd_version", lambda: "1.4.0i1.cre")
    cmk_version.edition_short.cache_clear()
    assert cmk_version.is_raw_edition() is True
    monkeypatch.setattr(cmk_version, "omd_version", lambda: "1.4.0i1.cee")
    cmk_version.edition_short.cache_clear()
    assert cmk_version.is_raw_edition() is False
    monkeypatch.setattr(cmk_version, "omd_version", lambda: "2016.09.22.cee")
    cmk_version.edition_short.cache_clear()
    assert cmk_version.is_raw_edition() is False
    monkeypatch.setattr(cmk_version, "omd_version", lambda: "2016.09.22.cfe")
    cmk_version.edition_short.cache_clear()
    assert cmk_version.is_raw_edition() is False
    cmk_version.edition_short.cache_clear()


def test_is_free_edition(monkeypatch):
    monkeypatch.setattr(cmk_version, "omd_version", lambda: "1.4.0i1.cre")
    cmk_version.edition_short.cache_clear()
    assert cmk_version.is_free_edition() is False
    monkeypatch.setattr(cmk_version, "omd_version", lambda: "1.4.0i1.cee")
    cmk_version.edition_short.cache_clear()
    assert cmk_version.is_free_edition() is False
    monkeypatch.setattr(cmk_version, "omd_version", lambda: "2016.09.22.cee")
    cmk_version.edition_short.cache_clear()
    assert cmk_version.is_free_edition() is False
    monkeypatch.setattr(cmk_version, "omd_version", lambda: "2016.09.22.cfe")
    cmk_version.edition_short.cache_clear()
    assert cmk_version.is_free_edition() is True
    cmk_version.edition_short.cache_clear()
