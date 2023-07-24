#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "ceph_status"

mock_item_state = {
    "": {
        "ceph_status.epoch.rate" : (0, 108),
    },
}

info = [
    ["{"],
    ['"fsid":', '"123-abc-456",'],
    ['"health":', "{"],
    ['"checks":', "{},"],
    ['"status":', '"HEALTH_OK",'],
    ['"summary":', "["],
    ["{"],
    ['"severity":', '"HEALTH_WARN",'],
    [
        '"summary":',
        "\"'ceph",
        "health'",
        "JSON",
        "format",
        "has",
        "changed",
        "in",
        "luminous.",
        "If",
        "you",
        "see",
        "this",
        "your",
        "monitoring",
        "system",
        "is",
        "scraping",
        "the",
        "wrong",
        "fields.",
        "Disable",
        "this",
        "with",
        "'mon",
        "health",
        "preluminous",
        "compat",
        "warning",
        "=",
        "false'\"",
    ],
    ["}"],
    ["],"],
    ['"overall_status":', '"HEALTH_WARN"'],
    ["},"],
    ['"election_epoch":', "2020"],
    ["}"],
]


discovery = {"": [(None, {})], "mgrs": [], "osds": [], "pgs": []}


checks = {
    "": [
        (
            None,
            {"epoch": (1, 3, 30)},
            [(0, "Health: OK", []), (0, "Epoch rate (30 minutes 0 seconds average): 0.00", [])],
        )
    ]
}
