#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v1 import HostLabel
from cmk.plugins.omd.agent_based import omd_info


def test_parse_omd_info_doctest() -> None:
    assert omd_info.parse_omd_info(
        [
            ["[versions]"],
            ["version", "number", "edition", "demo"],
            ["v1.edition", "v1", "edition", "0"],
            ["v2.edition", "v2", "edition", "0"],
            ["[sites]"],
            ["site", "used_version", "autostart"],
            ["heute", "v1.edition", "0"],
            ["beta", "v2.edition", "0"],
        ]
    ) == {
        "sites": {
            "beta": {
                "autostart": "0",
                "site": "beta",
                "used_version": "v2.edition",
            },
            "heute": {
                "autostart": "0",
                "site": "heute",
                "used_version": "v1.edition",
            },
        },
        "versions": {
            "v1.edition": {
                "demo": "0",
                "edition": "edition",
                "number": "v1",
                "version": "v1.edition",
            },
            "v2.edition": {
                "demo": "0",
                "edition": "edition",
                "number": "v2",
                "version": "v2.edition",
            },
        },
    }


def test_label_with_sites() -> None:
    section = {"sites": {"a": {"foo": "bar"}}}
    assert list(omd_info.host_label_omd_info(section)) == [HostLabel("cmk/check_mk_server", "yes")]


def test_no_label_without_sites() -> None:
    assert not list(omd_info.host_label_omd_info({"sites": {}}))
