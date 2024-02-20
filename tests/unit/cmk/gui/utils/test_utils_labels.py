#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection

from cmk.gui import sites
from cmk.gui.utils.labels import _get_labels_from_livestatus, LabelType


@pytest.fixture(name="live")
def fixture_livestatus_test_config(
    mock_livestatus: MockLiveStatusConnection,
) -> MockLiveStatusConnection:
    live = mock_livestatus
    live.set_sites(["NO_SITE"])
    live.add_table(
        "hosts",
        [
            {
                "host_name": "testhost",
                "labels": {
                    "cmk/os_family": "linux",
                    "cmk/docker_object": "node",
                    "cmk/check_mk_server": "yes",
                    "cmk/site": "heute",
                },
            }
        ],
    )
    live.add_table(
        "services",
        [
            {
                "host_name": "testhost",
                "labels": {"test": "servicelabel", "test2": "servicelabel"},
            }
        ],
    )
    live.add_table(
        "labels",
        [
            {"name": "cmk/os_family", "value": "linux"},
            {"name": "cmk/docker_object", "value": "node"},
            {"name": "cmk/check_mk_server", "value": "yes"},
            {"name": "servicelabel", "value": "servicelabel"},
        ],
    )

    # Initiate status query here to make it not trigger in the tests
    with live(expect_status_query=True):
        sites.live()

    return live


@pytest.mark.parametrize(
    "label_type, expected_query, expected_labels",
    [
        pytest.param(
            LabelType.ALL,
            "GET labels\nColumns: name value",
            {
                ("cmk/os_family", "linux"),
                ("cmk/docker_object", "node"),
                ("cmk/check_mk_server", "yes"),
                ("servicelabel", "servicelabel"),
            },
            id="All labels",
        ),
        pytest.param(
            LabelType.HOST,
            "GET hosts\nColumns: labels",
            {
                ("cmk/os_family", "linux"),
                ("cmk/docker_object", "node"),
                ("cmk/check_mk_server", "yes"),
                ("cmk/site", "heute"),
            },
            id="Host labels",
        ),
        pytest.param(
            LabelType.SERVICE,
            "GET services\nColumns: labels",
            {
                ("test", "servicelabel"),
                ("test2", "servicelabel"),
            },
            id="Service labels",
        ),
    ],
)
def test_collect_labels_from_livestatus_rows(
    label_type: LabelType,
    expected_query: str,
    expected_labels: set[tuple[str, str]],
    request_context: None,
    live: MockLiveStatusConnection,
) -> None:
    with live(expect_status_query=False):
        live.expect_query(expected_query)
        all_labels = _get_labels_from_livestatus(label_type)

    assert all_labels == expected_labels
