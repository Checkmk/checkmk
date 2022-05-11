#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from livestatus import LivestatusResponse, LivestatusRow, SiteId

from cmk.utils.type_defs import Dict, List, Tuple

from cmk.gui.utils.labels import _LivestatusLabelResponse, _MergedLabels, LabelsCache

DISTRIBUTED_ROWS = _LivestatusLabelResponse(
    LivestatusResponse([
        LivestatusRow([
            "heute",
            {
                "cmk/os_family": "linux",
                "cmk/docker_object": "node",
                "hstlabel": "hstvalue1",
                "cmk/check_mk_server": "yes",
                "cmk/site": "heute",
            },
        ]),
        LivestatusRow([
            "heute",
            {
                "cmk/os_family": "linux",
                "cmk/docker_object": "node",
                "hstlabel": "hstvalue2",
                "cmk/check_mk_server": "yes",
                "cmk/site": "heute",
            },
        ]),
        LivestatusRow([
            "heute_remote_1",
            {
                "cmk/os_family": "linux",
                "cmk/docker_object": "node",
                "hstlabel": "hstvalue3",
                "cmk/check_mk_server": "yes",
                "cmk/site": "heute_remote_1",
            },
        ]),
        LivestatusRow([
            "heute_remote_2",
            {
                "cmk/os_family": "linux",
                "cmk/docker_object": "node",
                "hstlabel": "hstvalue4",
                "cmk/check_mk_server": "yes",
                "cmk/site": "heute_remote_2",
            },
        ]),
    ]),
    LivestatusResponse([
        LivestatusRow([
            "heute",
            {
                "svclabel": "svcvalue1"
            },
        ]),
        LivestatusRow([
            "heute",
            {
                "svclabel": "svcvalue2"
            },
        ]),
        LivestatusRow([
            "heute_remote_1",
            {
                "svclabel": "svcvalue3"
            },
        ]),
        LivestatusRow([
            "heute_remote_2",
            {},
        ]),
    ]),
)

SINGLE_SETUP_ROWS = _LivestatusLabelResponse(
    LivestatusResponse([
        LivestatusRow([
            "heute",
            {
                "cmk/os_family": "linux",
                "cmk/docker_object": "node",
                "label1": "value1",
                "cmk/check_mk_server": "yes",
                "cmk/site": "heute",
            },
        ]),
    ]),
    LivestatusResponse([
        LivestatusRow(["heute", {
            "cmk/site": "heute",
            "label1": "value2"
        }]),
    ]),
)


@pytest.mark.parametrize(
    "livestatus_label_response, expected",
    [
        [
            DISTRIBUTED_ROWS,
            _MergedLabels(
                {
                    SiteId("heute"): {
                        "cmk/os_family": "['linux']",
                        "cmk/docker_object": "['node']",
                        "hstlabel": "['hstvalue1', 'hstvalue2']",
                        "cmk/check_mk_server": "['yes']",
                        "cmk/site": "['heute']",
                    },
                    SiteId("heute_remote_1"): {
                        "cmk/os_family": "['linux']",
                        "cmk/docker_object": "['node']",
                        "hstlabel": "['hstvalue3']",
                        "cmk/check_mk_server": "['yes']",
                        "cmk/site": "['heute_remote_1']",
                    },
                    SiteId("heute_remote_2"): {
                        "cmk/os_family": "['linux']",
                        "cmk/docker_object": "['node']",
                        "hstlabel": "['hstvalue4']",
                        "cmk/check_mk_server": "['yes']",
                        "cmk/site": "['heute_remote_2']",
                    },
                },
                {
                    SiteId("heute"): {
                        "svclabel": "['svcvalue1', 'svcvalue2']"
                    },
                    SiteId("heute_remote_1"): {
                        "svclabel": "['svcvalue3']"
                    },
                    SiteId("heute_remote_2"): {},
                },
            ),
        ],
        [
            SINGLE_SETUP_ROWS,
            _MergedLabels(
                {
                    SiteId("heute"): {
                        "cmk/os_family": "['linux']",
                        "cmk/docker_object": "['node']",
                        "label1": "['value1']",
                        "cmk/check_mk_server": "['yes']",
                        "cmk/site": "['heute']",
                    },
                },
                {SiteId("heute"): {
                     "cmk/site": "['heute']",
                     "label1": "['value2']"
                 }},
            ),
        ],
    ],
)
def test_collect_labels_from_livestatus_rows(livestatus_label_response: _LivestatusLabelResponse,
                                             expected: _MergedLabels):
    assert (
        LabelsCache()._collect_labels_from_livestatus_labels(livestatus_label_response) == expected)


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
    [[
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
    ]],
)
def test_get_deserialized_labels(
    redis_result: List[Dict[str, str]],
    expected: List[Tuple[str, str]],
):
    assert LabelsCache()._get_deserialized_labels(redis_result) == expected
