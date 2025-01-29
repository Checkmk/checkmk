#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.base.legacy_checks import jolokia_jvm_garbagecollectors as jvm_gc

Section = Mapping  # sorry. no better typing in plugin


def _section() -> Section:
    return jvm_gc.parse_jolokia_jvm_garbagecollectors(
        [
            [
                "MyJIRA",
                "java.lang:name=*,type=GarbageCollector/CollectionCount,CollectionTime,Name",
                '{"java.lang:name=MyName,type=GarbageCollector": {"CollectionTime": 13800,'
                ' "Name": "MyName", "CollectionCount": 25200}, "java.lang:name=My undiscovered,'
                'type=GarbageCollector": {"Name": "My undiscovered"}}',
            ]
        ]
    )


def test_discovery() -> None:
    assert list(jvm_gc.discover_jolokia_jvm_garbagecollectors(_section())) == [
        ("MyJIRA GC MyName", {}),
    ]


def test_check() -> None:
    assert list(
        jvm_gc.check_jolokia_jvm_garbagecollectors_testable(
            "MyJIRA GC MyName",
            {
                "collection_count": (400.0, 500.0),
                "collection_time": (22.0, 24.0),
            },
            _section(),
            {
                "MyJIRA GC MyName.time": (0, 0),
                "MyJIRA GC MyName.count": (0, 0),
            },
            60,
        )
    ) == [
        (
            1,
            "Garbage collections: 420.00/s (warn/crit at 400.00/s/500.00/s)",
            [("jvm_garbage_collection_count", 420.0, 400.0, 500.0)],
        ),
        (
            1,
            "Time spent collecting garbage: 23.00 % (warn/crit at 22.00 %/24.00 %)",
            [("jvm_garbage_collection_time", 23.0, 22.0, 24.0)],
        ),
    ]
