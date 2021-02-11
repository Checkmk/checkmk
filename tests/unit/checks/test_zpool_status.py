#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from testlib import Check

from checktestlib import assertEqual


@pytest.mark.parametrize("info, expected_parse_result", [
    ([
        ["all", "pools", "are", "healthy"],
    ], (0, "All pools are healthy")),
    ([
        ["no", "pools", "available"],
    ], (3, "No pools available")),
    ([
        ["c0t5000C5004176685Fd0", "ONLINE", "0", "0", "0"],
        ["spare-4", "FAULTED", "0", "0", "0"],
        ["c0t5000C500417668A3d0", "FAULTED", "0", "0", "0", "too", "many", "errors"],
    ], (0, "No critical errors")),
    ([
        ["state:", "ONLINE"],
        ["state:", "DEGRADED"],
        ["state:", "UNKNOWN"],
    ], (1, "DEGRADED State, Unknown State")),
    ([
        ["state:", "FAULTED"],
        ["state:", "UNAVIL"],
        ["state:", "REMOVED"],
    ], (2, "FAULTED State, UNAVIL State, REMOVED State")),
    ([
        ["pool:", "test"],
        ["state:", "ONLINE"],
        [
            "status:", "One", "or", "more", "devices", "has", "experienced", "an", "unrecoverable",
            "error."
        ],
        ["Applications", "are", "unaffected."],
        ["pool:", "test2"],
        [
            "status:", "One", "or", "more", "devices", "has", "experienced", "an", "unrecoverable",
            "error."
        ],
    ],
     (1,
      "test: One or more devices has experienced an unrecoverable error. Applications are unaffected., test2: One or more devices has experienced an unrecoverable error."
     )),
    ([
        ["state:", "DEGRADED"],
        ["state:", "OFFLINE"],
    ], (0, "DEGRADED State")),
    ([
        ["NAME", "STATE", "READ", "WRITE", "CKSUM"],
        ["snapshots", "OFFLINE", "0", "0", "0"],
        ["raidz1", "ONLINE", "0", "0", "0"],
    ], (2, "snapshots state: OFFLINE")),
    ([
        ["config:"],
        ["NAME", "STATE", "READ", "WRITE", "CKSUM"],
        ["snapshots", "ONLINE", "0", "0", "0"],
        ["raidz1", "ONLINE", "0", "0", "1"],
        ["spares", "OFFLINE", "0", "0", "0"],
    ], (1, "raidz1 CKSUM: 1")),
    ([
        ["pool:", "test3"],
        ["errors:", "Device", "experienced", "an", "error."],
    ], (1, "test3: Device experienced an error.")),
])
def test_zypper_check(info, expected_parse_result):
    assertEqual(Check("zpool_status").run_check(None, {}, info), expected_parse_result)
