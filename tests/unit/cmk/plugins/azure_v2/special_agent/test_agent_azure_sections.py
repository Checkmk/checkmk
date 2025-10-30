#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from collections.abc import Sequence

import pytest

from cmk.plugins.azure_v2.special_agent.agent_azure_v2 import (
    AzureLabelsSection,
    AzureSubscription,
    AzureTenantLabelsSection,
    Section,
)


@pytest.mark.parametrize(
    "piggytarget, expected_piggytarget_header",
    [
        (["one"], "<<<<one>>>>"),
        (["piggy-back"], "<<<<piggy-back>>>>"),
    ],
)
def test_piggytarget_header(
    piggytarget: Sequence[str],
    expected_piggytarget_header: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    section = Section("testsection", piggytarget, 1, ["myopts"])
    section.add(["section data"])
    section.write()
    section_stdout = capsys.readouterr().out.split("\n")
    assert section_stdout[0] == expected_piggytarget_header


@pytest.mark.parametrize(
    "section_name, expected_section_header",
    [
        ("testsection", "<<<testsection:sep(1):myopts>>>"),
        ("test-section", "<<<test_section:sep(1):myopts>>>"),
    ],
)
def test_section_header(
    section_name: str,
    expected_section_header: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    section = Section(section_name, [""], 1, ["myopts"])
    section.add(["section data"])
    section.write()
    section_stdout = capsys.readouterr().out.split("\n")
    assert section_stdout[1] == expected_section_header


@pytest.mark.parametrize(
    "section_name, section_data, separator, expected_section",
    [
        ("testsection", (("section data",)), 0, ["section data"]),
        (
            "test-section",
            (("first line",), ("second line",)),
            124,
            ["first line", "second line"],
        ),
        (
            "test-section",
            (("first line a", "first line b"), ("second line",)),
            124,
            ["first line a|first line b", "second line"],
        ),
    ],
)
def test_section(
    section_name: str,
    section_data: Sequence[str],
    separator: int,
    expected_section: Sequence[str],
    capsys: pytest.CaptureFixture[str],
) -> None:
    section = Section(section_name, [""], separator, ["myopts"])
    section.add(section_data)
    section.write()
    section_stdout = capsys.readouterr().out.split("\n")
    assert section_stdout[2:-2] == expected_section


AZURE_SUBSCRIPTION = AzureSubscription(
    id="test-subscription-id-12345678",
    name="test-subscription",
    tags={"subscription-tag": "sub-value"},
    safe_hostnames=False,
    tenant_id="test-tenant-id",
)
AZURE_SUBSCRIPTION_SAFEHOSTNAME = AzureSubscription(
    id="test-subscription-id-12345678",
    name="test-subscription",
    tags={"subscription-tag": "sub-value"},
    safe_hostnames=True,
    tenant_id="test-tenant-id",
)


@pytest.mark.parametrize(
    "labels_section, section_result",
    [
        pytest.param(
            AzureLabelsSection(
                piggytarget="test-resource",
                subscription=AZURE_SUBSCRIPTION,
                labels={},
                tags={},
            ),
            [
                "<<<<test-resource>>>>",
                "<<<azure_v2_labels:sep(0)>>>",
                '{"cloud": "azure"}',
                "{}",
                "<<<<>>>>",
            ],
            id="basic test empty labels and tags",
        ),
        pytest.param(
            AzureLabelsSection(
                piggytarget="test-resource",
                subscription=AZURE_SUBSCRIPTION,
                labels={"key1": "value1", "key2": "value2"},
                tags={"tag1": "tagvalue1", "tag2": "tagvalue2"},
            ),
            [
                "<<<<test-resource>>>>",
                "<<<azure_v2_labels:sep(0)>>>",
                '{"cloud": "azure", "key1": "value1", "key2": "value2"}',
                '{"tag1": "tagvalue1", "tag2": "tagvalue2"}',
                "<<<<>>>>",
            ],
            id="basic test",
        ),
        pytest.param(
            AzureLabelsSection(
                piggytarget="test-resource",
                subscription=AZURE_SUBSCRIPTION_SAFEHOSTNAME,
                labels={"key1": "value1", "key2": "value2"},
                tags={"tag1": "tagvalue1", "tag2": "tagvalue2"},
            ),
            [
                "<<<<azr-test-resource-12345678>>>>",
                "<<<azure_v2_labels:sep(0)>>>",
                '{"cloud": "azure", "key1": "value1", "key2": "value2"}',
                '{"tag1": "tagvalue1", "tag2": "tagvalue2"}',
                "<<<<>>>>",
            ],
            id="basic test with safe hostnames",
        ),
    ],
)
def test_azure_labels_section(
    labels_section: AzureLabelsSection,
    section_result: Sequence[str],
    capsys: pytest.CaptureFixture[str],
) -> None:
    labels_section.write()
    output = capsys.readouterr().out
    lines = output.strip().split("\n")
    assert lines == section_result


@pytest.mark.parametrize(
    "labels_section, section_result",
    [
        pytest.param(
            AzureTenantLabelsSection(
                labels={},
                tags={},
            ),
            [
                "<<<<>>>>",
                "<<<azure_v2_labels:sep(0)>>>",
                '{"cloud": "azure", "entity": "tenant"}',
                "{}",
                "<<<<>>>>",
            ],
            id="basic test empty labels and tags",
        ),
        pytest.param(
            AzureTenantLabelsSection(
                labels={"key1": "value1", "key2": "value2"},
                tags={"tag1": "tagvalue1", "tag2": "tagvalue2"},
            ),
            [
                "<<<<>>>>",
                "<<<azure_v2_labels:sep(0)>>>",
                '{"cloud": "azure", "entity": "tenant", "key1": "value1", "key2": "value2"}',
                '{"tag1": "tagvalue1", "tag2": "tagvalue2"}',
                "<<<<>>>>",
            ],
            id="basic test",
        ),
    ],
)
def test_azure_tenant_labels_section(
    labels_section: AzureTenantLabelsSection,
    section_result: Sequence[str],
    capsys: pytest.CaptureFixture[str],
) -> None:
    labels_section.write()
    output = capsys.readouterr().out
    lines = output.strip().split("\n")
    assert lines == section_result
