#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.testlib.site import Site

import cmk.utils.werks


def test_load(site: Site) -> None:
    werks = cmk.utils.werks.load()
    assert len(werks) > 1000


def test_make_sure_werks_have_mandatory_fields(site: Site) -> None:
    mandatory_werk_fields = {
        # ATTENTION! If you have to change this list, you have to talk
        # to the website team first! They rely on those fields.
        "class",
        "compatible",
        "component",
        "date",
        "description",
        "edition",
        "id",
        "level",
        "title",
        "version",
    }
    werks = cmk.utils.werks.load()
    for werk in werks.values():
        missing_fields = mandatory_werk_fields - set(werk.keys())
        if missing_fields:
            assert False, f"werk {werk} has missing fields: {missing_fields}"


def test_regular_werks(site: Site) -> None:
    werks = cmk.utils.werks.load()

    regular_werks = [werk for werk in werks.values() if werk["edition"] == "cre"]

    assert len(regular_werks) > 1000


def test_enterprise_werks(site: Site) -> None:
    werks = cmk.utils.werks.load()

    enterprise_werks = [werk for werk in werks.values() if werk["edition"] == "cee"]

    if site.version.is_raw_edition():
        assert not enterprise_werks
    else:
        assert enterprise_werks


def test_managed_werks(site: Site) -> None:
    werks = cmk.utils.werks.load()

    managed_werks = [werk for werk in werks.values() if werk["edition"] == "cme"]

    if site.version.is_managed_edition():
        assert managed_werks
    else:
        assert not managed_werks


def test_plus_werks(site: Site) -> None:
    werks = cmk.utils.werks.load()

    plus_werks = [werk for werk in werks.values() if werk["edition"] == "cpe"]

    if site.version.is_plus_edition():
        assert plus_werks
    else:
        assert not plus_werks
