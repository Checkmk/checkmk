#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v1 import HostLabel
from cmk.agent_based.v1.type_defs import StringTable
from cmk.plugins.azure.agent_based.azure_section_labels import (
    _parse_host_labels,
    host_labels,
    LabelsSection,
)


@pytest.mark.parametrize(
    "string_table, expected_section",
    [
        pytest.param(
            [['{"group_name": "rg-pm-weu"}'], ["{}"]],
            LabelsSection(
                host_labels={"group_name": "rg-pm-weu"},
                tags={},
            ),
            id="Only labels",
        ),
        pytest.param(
            [
                ['{"group_name": "rg-dev-weu", "vm_instance": true}'],
                [
                    '{"tag-test-name": "tag-test-value", "the:tag": "the:value", "rg-tag-key": "rg-tag-value"}'
                ],
            ],
            LabelsSection(
                host_labels={"group_name": "rg-dev-weu", "vm_instance": True},
                tags={
                    "tag-test-name": "tag-test-value",
                    "the:tag": "the:value",
                    "rg-tag-key": "rg-tag-value",
                },
            ),
            id="Labels and tags",
        ),
    ],
)
def test_parse_host_labels(
    string_table: StringTable,
    expected_section: LabelsSection,
) -> None:
    assert _parse_host_labels(string_table) == expected_section


@pytest.mark.parametrize(
    "section, expected_labels",
    [
        pytest.param(
            LabelsSection(
                host_labels={"group_name": "rg-pm-weu"},
                tags={},
            ),
            [HostLabel("cmk/azure/resource_group", "rg-pm-weu")],
            id="Simple recognized label",
        ),
        pytest.param(
            LabelsSection(
                host_labels={"group_name": "rg-pm-weu", "another_label": "value"},
                tags={},
            ),
            [
                HostLabel("cmk/azure/resource_group", "rg-pm-weu"),
                HostLabel("cmk/azure/another_label", "value"),
            ],
            id="Recognized and unrecognized labels",
        ),
        pytest.param(
            LabelsSection(
                host_labels={"entity_subscription": "true", "subscription": "subscription_name"},
                tags={},
            ),
            [
                HostLabel("cmk/azure/entity_subscription", "true"),
                HostLabel("cmk/azure/subscription", "subscription_name"),
            ],
            id="Subscription labels",
        ),
        pytest.param(
            LabelsSection(
                host_labels={"vm_instance": True},
                tags={},
            ),
            [HostLabel("cmk/azure/vm", "instance")],
            id="Vm instance label",
        ),
        pytest.param(
            LabelsSection(
                host_labels={"group_name": "rg-pm-weu", "another_label": "value"},
                tags={
                    "tag-test-name": "tag-test-value",
                    "the:tag": "the:value",
                    "rg-tag-key": "rg-tag-value",
                },
            ),
            [
                HostLabel("cmk/azure/resource_group", "rg-pm-weu"),
                HostLabel("cmk/azure/another_label", "value"),
                HostLabel("cmk/azure/tag/tag-test-name", "tag-test-value"),
                HostLabel("cmk/azure/tag/the_tag", "the_value"),
                HostLabel("cmk/azure/tag/rg-tag-key", "rg-tag-value"),
            ],
            id="Labels and tags",
        ),
        pytest.param(
            LabelsSection(
                host_labels={
                    "key:with:colons": "rg-pm-weu",
                    "another_label": "value:with:colons",
                    "empty_value": "",
                },
                tags={},
            ),
            [
                HostLabel("cmk/azure/key_with_colons", "rg-pm-weu"),
                HostLabel("cmk/azure/another_label", "value_with_colons"),
                HostLabel("cmk/azure/empty_value", "true"),
            ],
            id="Labels with special characters",
        ),
    ],
)
def test_host_labels(
    section: LabelsSection,
    expected_labels: Sequence[HostLabel],
) -> None:
    assert list(host_labels(section)) == expected_labels
