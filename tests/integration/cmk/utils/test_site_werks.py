#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from tests.testlib.site import Site

import cmk.utils.werks
from cmk.utils.werks.werk import Edition, Werk


@pytest.fixture(name="werks")
def fixture_werks(site: Site) -> dict[int, Werk]:
    return cmk.utils.werks.load(Path(site.version.version_path(), "share/check_mk/werks"))


def test_load(werks: dict[int, Werk]) -> None:
    assert len(werks) > 1000


def test_regular_werks(werks: dict[int, Werk]) -> None:
    regular_werks = [werk for werk in werks.values() if werk.edition == Edition.CRE]
    assert len(regular_werks) > 1000


def test_enterprise_werks(site: Site, werks: dict[int, Werk]) -> None:
    enterprise_werks = [werk for werk in werks.values() if werk.edition == Edition.CEE]

    if site.version.is_raw_edition():
        assert not enterprise_werks
    else:
        assert enterprise_werks


def test_managed_werks(site: Site, werks: dict[int, Werk]) -> None:
    managed_werks = [werk for werk in werks.values() if werk.edition == Edition.CME]

    if site.version.is_managed_edition():
        assert managed_werks
    else:
        assert not managed_werks


def test_cloud_werks(site: Site, werks: dict[int, Werk]) -> None:
    cloud_werks = [werk for werk in werks.values() if werk.edition == Edition.CCE]

    if site.version.is_cloud_edition():
        assert cloud_werks
    else:
        assert not cloud_werks
