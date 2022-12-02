#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disallow_untyped_defs

from collections.abc import Sequence
from dataclasses import dataclass

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable
from cmk.base.plugins.agent_based.gcp_exceptions import _ExceptionSection, check, discover, parse


@dataclass(frozen=True)
class GCPException:
    section: _ExceptionSection
    results: Sequence[Result]


EXCEPTIONS = [
    pytest.param(
        GCPException(
            section=_ExceptionSection(
                type="PermissionDenied",
                message="""403 Cloud Asset API has not been used in project 1074106860578 before or it is disabled. Enable it by visiting https://console.developers.google.com/apis/api/cloudasset.googleapis.com/overview?project=1074106860578 then retry. If you enabled this API recently, wait a few minutes for the action to propagate to our systems and retry. [links {  description: "Google developers console API activation"  url: "https://console.developers.google.com/apis/api/cloudasset.googleapis.com/overview?project=1074106860578"}, reason: "SERVICE_DISABLED"domain: "googleapis.com"metadata {  key: "consumer"  value: "projects/1074106860578"}metadata {  key: "service"  value: "cloudasset.googleapis.com"}]""",
            ),
            results=[
                Result(
                    state=State.CRIT,
                    notice="The Google Cloud API reported an error. Please read the error message on how to fix it:, PermissionDenied: 403 Cloud Asset API has not been used in project 1074106860578 before or it is disabled. Enable it by visiting https://console.developers.google.com/apis/api/cloudasset.googleapis.com/overview?project=1074106860578 then retry. If you enabled this API recently, wait a few minutes for the action to propagate to our systems and retry.",
                    details="The Google Cloud API reported an error. Please read the error message on how to fix it:\nPermissionDenied: 403 Cloud Asset API has not been used in project 1074106860578 before or it is disabled. Enable it by visiting https://console.developers.google.com/apis/api/cloudasset.googleapis.com/overview?project=1074106860578 then retry. If you enabled this API recently, wait a few minutes for the action to propagate to our systems and retry.",
                )
            ],
        ),
        id="permission denied",
    ),
    pytest.param(
        GCPException(
            section=_ExceptionSection(type=None, message=None),
            results=[Result(state=State.OK, notice="No exceptions")],
        ),
        id="no exceptions",
    ),
]


@pytest.mark.parametrize(
    "string_table,expected_section",
    [
        pytest.param(
            [["ExceptionType: ExceptionMessage"]],
            _ExceptionSection(type="ExceptionType", message="ExceptionMessage"),
            id="exception exists",
        ),
        pytest.param([], _ExceptionSection(type=None, message=None), id="no exceptions"),
    ],
)
def test_parse_exception(string_table: StringTable, expected_section: _ExceptionSection) -> None:
    assert parse(string_table) == expected_section


@pytest.mark.parametrize("exception", EXCEPTIONS)
def test_discover_exception(exception: GCPException) -> None:
    assert len(list(discover(exception.section))) == 1


@pytest.mark.parametrize("exception", EXCEPTIONS)
def test_check_exception(exception: GCPException) -> None:
    assert list(check(exception.section)) == exception.results
