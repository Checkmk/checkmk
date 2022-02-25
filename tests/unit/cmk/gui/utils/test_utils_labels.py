#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from livestatus import SiteId

from cmk.utils.type_defs import Dict, List, Mapping, Tuple

from cmk.gui.utils.labels import LabelsCache

DISTRIBUTED_ROWS: List[Tuple[str, Dict[str, str], Dict[str, str]]] = [
    (
        "heute",
        {
            "cmk/os_family": "linux",
            "cmk/docker_object": "node",
            "hstlabel": "hstvalue1",
            "cmk/check_mk_server": "yes",
            "cmk/site": "heute",
        },
        {"svclabel": "svcvalue1"},
    ),
    (
        "heute",
        {
            "cmk/os_family": "linux",
            "cmk/docker_object": "node",
            "hstlabel": "hstvalue2",
            "cmk/check_mk_server": "yes",
            "cmk/site": "heute",
        },
        {"svclabel": "svcvalue2"},
    ),
    (
        "heute_remote_1",
        {
            "cmk/os_family": "linux",
            "cmk/docker_object": "node",
            "hstlabel": "hstvalue3",
            "cmk/check_mk_server": "yes",
            "cmk/site": "heute_remote_1",
        },
        {"svclabel": "svcvalue3"},
    ),
    (
        "heute_remote_2",
        {
            "cmk/os_family": "linux",
            "cmk/docker_object": "node",
            "hstlabel": "hstvalue4",
            "cmk/check_mk_server": "yes",
            "cmk/site": "heute_remote_2",
        },
        {},
    ),
]

SINGLE_SETUP_ROWS: List[Tuple[str, Dict[str, str], Dict[str, str]]] = [
    (
        "heute",
        {
            "cmk/os_family": "linux",
            "cmk/docker_object": "node",
            "label1": "value1",
            "cmk/check_mk_server": "yes",
            "cmk/site": "heute",
        },
        {},
    ),
    ("heute", {"cmk/site": "heute", "label1": "value2"}, {}),
]


@pytest.mark.parametrize(
    "rows, expected",
    [
        [
            DISTRIBUTED_ROWS,
            (
                {
                    "heute": {
                        "cmk/os_family": "['linux']",
                        "cmk/docker_object": "['node']",
                        "hstlabel": "['hstvalue1', 'hstvalue2']",
                        "cmk/check_mk_server": "['yes']",
                        "cmk/site": "['heute']",
                    },
                    "heute_remote_1": {
                        "cmk/os_family": "['linux']",
                        "cmk/docker_object": "['node']",
                        "hstlabel": "['hstvalue3']",
                        "cmk/check_mk_server": "['yes']",
                        "cmk/site": "['heute_remote_1']",
                    },
                    "heute_remote_2": {
                        "cmk/os_family": "['linux']",
                        "cmk/docker_object": "['node']",
                        "hstlabel": "['hstvalue4']",
                        "cmk/check_mk_server": "['yes']",
                        "cmk/site": "['heute_remote_2']",
                    },
                },
                {
                    "heute": {"svclabel": "['svcvalue1', 'svcvalue2']"},
                    "heute_remote_1": {"svclabel": "['svcvalue3']"},
                    "heute_remote_2": {},
                },
            ),
        ],
        [
            SINGLE_SETUP_ROWS,
            (
                {
                    "heute": {
                        "cmk/os_family": "['linux']",
                        "cmk/docker_object": "['node']",
                        "label1": "['value1', 'value2']",
                        "cmk/check_mk_server": "['yes']",
                        "cmk/site": "['heute']",
                    },
                },
                {"heute": {}},
            ),
        ],
    ],
)
def test_collect_labels_from_livestatus_rows(
    rows: List[Tuple[SiteId, Dict[str, str], Dict[str, str]]],
    expected: Tuple[Mapping[str, Mapping[str, str]], Mapping[str, Mapping[str, str]]],
):
    assert LabelsCache()._collect_labels_from_livestatus_rows(rows) == expected


DISTRIBUTED_RESULT: List[Dict[str, str]] = [
    {
        "cmk/os_family": "['linux']",
        "cmk/docker_object": "['node']",
        "label1": "['value1', 'value2']",
        "cmk/check_mk_server": "['yes']",
        "cmk/site": "['heute']",
    },
    {},
    {
        "cmk/site": "['heute_remote_1']",
        "label1": "['value3', 'value4']",
        "cmk/os_family": "['linux']",
        "cmk/docker_object": "['node']",
        "cmk/check_mk_server": "['yes']",
    },
    {},
]


@pytest.mark.parametrize(
    "redis_result, expected",
    [
        [
            DISTRIBUTED_RESULT,
            [
                ("cmk/os_family", "linux"),
                ("cmk/docker_object", "node"),
                ("label1", "value1"),
                ("label1", "value2"),
                ("cmk/check_mk_server", "yes"),
                ("cmk/site", "heute"),
                ("cmk/site", "heute_remote_1"),
                ("label1", "value3"),
                ("label1", "value4"),
                ("cmk/os_family", "linux"),
                ("cmk/docker_object", "node"),
                ("cmk/check_mk_server", "yes"),
            ],
        ]
    ],
)
def test_get_deserialized_labels(
    redis_result: List[Dict[str, str]],
    expected: List[Tuple[str, str]],
):
    assert LabelsCache()._get_deserialized_labels(redis_result) == expected
