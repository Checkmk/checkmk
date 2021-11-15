#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
import time

import freezegun
import pytest

from tests.testlib import on_time

import cmk.gui.watolib as watolib


@pytest.mark.parametrize(
    "allowed,last_end,next_time",
    [
        (((0, 0), (24, 0)), None, 1515549600.0),
        (
            ((0, 0), (24, 0)),
            1515549600.0,
            1515549900.0,
        ),
        (((20, 0), (24, 0)), None, 1515610800.0),
        ([((0, 0), (2, 0)), ((20, 0), (22, 0))], None, 1515610800.0),
        ([((0, 0), (2, 0)), ((20, 0), (22, 0))], 1515621600.0, 1515625200.0),
    ],
)
def test_next_network_scan_at(allowed, last_end, next_time):
    folder = watolib.Folder(
        name="bla",
        title="Bla",
        attributes={
            "network_scan": {
                "exclude_ranges": [],
                "ip_ranges": [("ip_range", ("10.3.1.1", "10.3.1.100"))],
                "run_as": "cmkadmin",
                "scan_interval": 300,
                "set_ipaddress": True,
                "tag_criticality": "offline",
                "time_allowed": allowed,
            },
            "network_scan_result": {
                "end": last_end,
            },
        },
    )

    with on_time("2018-01-10 02:00:00", "CET"):
        assert folder.next_network_scan_at() == next_time


def test_folder_times(request_context):
    root = watolib.Folder.root_folder()

    with freezegun.freeze_time(datetime.datetime(2020, 2, 2, 2, 2, 2)):
        current = time.time()
        folder = watolib.Folder("test", parent_folder=root)
        folder.save()

    folder = watolib.Folder("test", "")
    meta_data = folder.attributes()["meta_data"]
    assert int(meta_data["created_at"]) == int(current)
    assert int(meta_data["updated_at"]) == int(current)

    folder.persist_instance()
    assert int(meta_data["updated_at"]) > int(current)
