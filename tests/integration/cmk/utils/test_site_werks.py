#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.testlib.site import Site

import cmk.utils.werks
from cmk.utils.werks.werk import Edition


def test_load(site: Site) -> None:
    werks = cmk.utils.werks.load()
    assert len(werks) > 1000


def test_make_sure_werks_can_be_loaded(site: Site) -> None:
    # (this test once made sure, that all werk dictionaries have have a fixed
    # list of fields, as we switched to pydantic models for writing and parsing
    # werks, pydantic will already make sure that the fields exists)
    cmk.utils.werks.load()


def test_regular_werks(site: Site) -> None:
    werks = cmk.utils.werks.load()

    regular_werks = [werk for werk in werks.values() if werk.edition == Edition.CRE]

    assert len(regular_werks) > 1000


def test_enterprise_werks(site: Site) -> None:
    werks = cmk.utils.werks.load()

    enterprise_werks = [werk for werk in werks.values() if werk.edition == Edition.CEE]

    if site.version.is_raw_edition():
        assert not enterprise_werks
    else:
        assert enterprise_werks


def test_managed_werks(site: Site) -> None:
    werks = cmk.utils.werks.load()

    managed_werks = [werk for werk in werks.values() if werk.edition == Edition.CME]

    if site.version.is_managed_edition():
        assert managed_werks
    else:
        assert not managed_werks


def test_cloud_werks(site: Site) -> None:
    werks = cmk.utils.werks.load()

    cloud_werks = [werk for werk in werks.values() if werk.edition == Edition.CCE]

    if site.version.is_cloud_edition():
        assert cloud_werks
    else:
        assert not cloud_werks
