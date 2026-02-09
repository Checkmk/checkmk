#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui import sites
from cmk.gui.utils.labels import _get_labels_from_livestatus, Label, LabelType
from cmk.livestatus_client.testing import MockLiveStatusConnection


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


@pytest.mark.parametrize(
    "label_string, negate, expected_key, expected_value, expected_negate",
    [
        pytest.param(
            "cmk/docker_image:filebrowser",
            None,
            "cmk/docker_image",
            "filebrowser",
            False,
            id="No colon value, negate=None",
        ),
        pytest.param(
            "cmk/docker_image:filebrowser",
            False,
            "cmk/docker_image",
            "filebrowser",
            False,
            id="No colon value, negate=False",
        ),
        pytest.param(
            "cmk/docker_image:filebrowser",
            True,
            "cmk/docker_image",
            "filebrowser",
            True,
            id="No colon value, negate=True",
        ),
        pytest.param(
            "cmk/docker_image:filebrowser/filebrowser:latest",
            True,
            "cmk/docker_image",
            "filebrowser/filebrowser:latest",
            True,
            id="Single colon value, negate=True",
        ),
        pytest.param(
            "cmk/docker_image:filebrowser/filebrowser:latest",
            False,
            "cmk/docker_image",
            "filebrowser/filebrowser:latest",
            False,
            id="Single colon value, negate=False",
        ),
        pytest.param(
            "cmk/docker_image:filebrowser/filebrowser:very:latest",
            False,
            "cmk/docker_image",
            "filebrowser/filebrowser:very:latest",
            False,
            id="Multi colon (2) value, negate=False",
        ),
        pytest.param(
            "cmk/docker_image:filebrowser/filebrowser:very:very:very:very:very:latest",
            None,
            "cmk/docker_image",
            "filebrowser/filebrowser:very:very:very:very:very:latest",
            False,
            id="Multi colon (6) value, negate=None",
        ),
        pytest.param(
            "cmk/docker_image:filebrowser/filebrowser:very:very:very:very:very:latest",
            False,
            "cmk/docker_image",
            "filebrowser/filebrowser:very:very:very:very:very:latest",
            False,
            id="Multi colon (6) value, negate=False",
        ),
    ],
)
def test_label_from_str(
    label_string: str,
    negate: None | bool,
    expected_key: str,
    expected_value: str,
    expected_negate: bool,
) -> None:
    label = Label.from_str(label_string, negate is not None and negate)
    assert label.id == expected_key
    assert label.value == expected_value
    assert label.negate == expected_negate
