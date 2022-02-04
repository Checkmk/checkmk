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
    cmk_version.edition.cache_clear()


@pytest.mark.parametrize(
    "omd_version_str, expected",
    [
        ("1.4.0i1.cre", cmk_version.Edition.CRE),
        ("1.4.0i1.cee", cmk_version.Edition.CEE),
        ("2016.09.22.cee", cmk_version.Edition.CEE),
        ("2016.09.22.cfe", cmk_version.Edition.CFE),
        ("2.1.0p3.cme", cmk_version.Edition.CME),
        ("2.1.0p3.cpe", cmk_version.Edition.CPE),
    ],
)
def test_is_enterprise_edition(
    monkeypatch,
    omd_version_str: str,
    expected: cmk_version.Edition,
) -> None:
    monkeypatch.setattr(cmk_version, "omd_version", lambda: omd_version_str)
    assert cmk_version.edition() is expected
