#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.utils.version as cmk_version


def test_version():
    assert isinstance(cmk_version.__version__, str)


@pytest.fixture(scope="function")
def cache_clear() -> None:
    cmk_version._edition.cache_clear()


_TEST_VERSIONS = ("1.4.0i1.cre", "1.4.0i1.cee", "2016.09.22.cee", "2016.09.22.cfe", "2.1.0p3.cpe")


@pytest.mark.parametrize(
    "omd_version_str,expected",
    list(zip(_TEST_VERSIONS, (False, True, True, False, False))),
)
def test_is_enterprise_edition(monkeypatch, omd_version_str: str, expected: bool) -> None:
    monkeypatch.setattr(cmk_version, "omd_version", lambda: omd_version_str)
    assert cmk_version.is_enterprise_edition() is expected


@pytest.mark.parametrize(
    "omd_version_str,expected",
    list(zip(_TEST_VERSIONS, (True, False, False, False, False))),
)
def test_is_raw_edition(monkeypatch, omd_version_str: str, expected: bool) -> None:
    monkeypatch.setattr(cmk_version, "omd_version", lambda: omd_version_str)
    assert cmk_version.is_raw_edition() is expected


@pytest.mark.parametrize(
    "omd_version_str,expected",
    list(zip(_TEST_VERSIONS, (False, False, False, True, False))),
)
def test_is_free_edition(monkeypatch, omd_version_str: str, expected: bool) -> None:
    monkeypatch.setattr(cmk_version, "omd_version", lambda: omd_version_str)
    assert cmk_version.is_free_edition() is expected


@pytest.mark.parametrize(
    "omd_version_str,expected",
    list(zip(_TEST_VERSIONS, (False, False, False, False, True))),
)
def test_is_plus_edition(monkeypatch, omd_version_str: str, expected: bool) -> None:
    monkeypatch.setattr(cmk_version, "omd_version", lambda: omd_version_str)
    assert cmk_version.is_plus_edition() is expected
