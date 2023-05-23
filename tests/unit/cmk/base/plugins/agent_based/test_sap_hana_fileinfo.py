#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping

import pytest

from tests.unit.conftest import FixRegister

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    IgnoreResultsError,
    Metric,
    Result,
    State,
)
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult
from cmk.base.plugins.agent_based.utils.fileinfo import Fileinfo, FileinfoItem

from cmk.checkengine.checking import CheckPluginName


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
    fix_register: FixRegister, item: str, parsed: Fileinfo, expected_result: CheckResult
) -> None:
    plugin = fix_register.check_plugins[CheckPluginName("sap_hana_fileinfo")]
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
def test_sap_hana_fileinfo_stale(fix_register: FixRegister, item: str, parsed: Fileinfo) -> None:
    plugin = fix_register.check_plugins[CheckPluginName("sap_hana_fileinfo")]
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
    fix_register: FixRegister,
    item: str,
    parsed: Fileinfo,
    params: Mapping[str, object],
    expected_result: CheckResult,
) -> None:
    plugin = fix_register.check_plugins[CheckPluginName("sap_hana_fileinfo_groups")]

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
    fix_register: FixRegister, item: str, parsed: Fileinfo
) -> None:
    plugin = fix_register.check_plugins[CheckPluginName("sap_hana_fileinfo_groups")]
    with pytest.raises(IgnoreResultsError) as e:
        list(plugin.check_function(item=item, params={}, section=parsed))

    assert e.value.args[0] == "Login into database failed."
