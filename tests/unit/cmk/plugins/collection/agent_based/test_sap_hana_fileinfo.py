#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import CheckResult, IgnoreResultsError, Metric, Result, State
from cmk.checkengine.plugins import AgentBasedPlugins, CheckPluginName
from cmk.plugins.lib.fileinfo import Fileinfo, FileinfoItem


@pytest.mark.parametrize(
    "item, parsed, expected_result",
    [
        pytest.param(
            "file1234.txt",
            Fileinfo(),
            [Result(state=State.UNKNOWN, summary="Missing reference timestamp")],
            id="missing reference timestamp",
        ),
        pytest.param(
            "C:\\Datentransfer\\ORU\\KC\\KC_41135.hl7",
            Fileinfo(
                reftime=1563288717,
                files={
                    "C:\\Datentransfer\\ORU\\KC\\KC_41135.hl7": FileinfoItem(
                        name="C:\\Datentransfer\\ORU\\KC\\KC_41135.hl7",
                        missing=False,
                        failed=False,
                        size=2414,
                        time=1415625918,
                    ),
                },
            ),
            [
                Result(state=State.OK, summary="Size: 2.36 KiB"),
                Metric("size", 2414.0),
                Result(state=State.OK, summary="Age: 4 years 249 days"),
                Metric("age", 147662799.0),
            ],
            id="file found",
        ),
    ],
)
def test_sap_hana_fileinfo(
    agent_based_plugins: AgentBasedPlugins,
    item: str,
    parsed: Fileinfo,
    expected_result: CheckResult,
) -> None:
    plugin = agent_based_plugins.check_plugins[CheckPluginName("sap_hana_fileinfo")]
    result = list(plugin.check_function(item=item, params={}, section=parsed))

    assert result == expected_result


@pytest.mark.parametrize(
    "item, parsed",
    [
        (
            "file1234.txt",
            Fileinfo(reftime=1563288717, files={}),
        ),
    ],
)
def test_sap_hana_fileinfo_stale(
    agent_based_plugins: AgentBasedPlugins, item: str, parsed: Fileinfo
) -> None:
    plugin = agent_based_plugins.check_plugins[CheckPluginName("sap_hana_fileinfo")]
    with pytest.raises(IgnoreResultsError) as e:
        list(plugin.check_function(item=item, params={}, section=parsed))

    assert e.value.args[0] == "Login into database failed."


@pytest.mark.parametrize(
    "item, parsed, params, expected_result",
    [
        (
            "file1234.txt",
            Fileinfo(),
            {},
            [Result(state=State.UNKNOWN, summary="Missing reference timestamp")],
        ),
        (
            "C:\\Datentransfer\\ORU\\KC\\KC_41135.hl7",
            Fileinfo(
                reftime=1563288717,
                files={
                    "C:\\Datentransfer\\ORU\\KC\\KC_41135.hl7": FileinfoItem(
                        name="C:\\Datentransfer\\ORU\\KC\\KC_41135.hl7",
                        missing=False,
                        failed=False,
                        size=2414,
                        time=1415625918,
                    ),
                },
            ),
            {},
            [Result(state=State.UNKNOWN, summary="No group pattern found.")],
        ),
    ],
)
def test_sap_hana_fileinfo_groups(
    agent_based_plugins: AgentBasedPlugins,
    item: str,
    parsed: Fileinfo,
    params: Mapping[str, object],
    expected_result: CheckResult,
) -> None:
    plugin = agent_based_plugins.check_plugins[CheckPluginName("sap_hana_fileinfo_groups")]

    result = list(plugin.check_function(item=item, params=params, section=parsed))
    assert result == expected_result


@pytest.mark.parametrize(
    "item, parsed",
    [
        (
            "file1234.txt",
            Fileinfo(reftime=1563288717, files={}),
        ),
    ],
)
def test_sap_hana_fileinfo_groups_stale(
    agent_based_plugins: AgentBasedPlugins, item: str, parsed: Fileinfo
) -> None:
    plugin = agent_based_plugins.check_plugins[CheckPluginName("sap_hana_fileinfo_groups")]
    with pytest.raises(IgnoreResultsError) as e:
        list(plugin.check_function(item=item, params={}, section=parsed))

    assert e.value.args[0] == "Login into database failed."
