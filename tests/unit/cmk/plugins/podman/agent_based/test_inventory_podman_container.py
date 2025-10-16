#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.agent_based.v2 import Attributes, InventoryResult
from cmk.plugins.podman.agent_based.cee.inventory_podman_container import inventory_podman_container
from cmk.plugins.podman.agent_based.cee.lib import SectionPodmanContainerInspect

from .lib import SECTION_RUNNING


@pytest.mark.parametrize(
    "section, expected_result",
    [
        pytest.param(
            SECTION_RUNNING,
            [
                Attributes(
                    path=["software", "applications", "podman", "container"],
                    inventory_attributes={
                        "hostname": "test-hostname",
                        "pod": "",
                        "labels": "key1=value1,key2=value2",
                    },
                    status_attributes={},
                ),
                Attributes(
                    path=["software", "applications", "podman", "network"],
                    inventory_attributes={
                        "ip_address": "192.168.1.100",
                        "gateway": "192.168.1.1",
                        "mac_address": "00:11:22:33:44:55",
                    },
                    status_attributes={},
                ),
            ],
            id="Everything present -> Attributes yielded",
        )
    ],
)
def test_inventory_podman(
    section: SectionPodmanContainerInspect,
    expected_result: InventoryResult,
) -> None:
    assert list(inventory_podman_container(section)) == expected_result
