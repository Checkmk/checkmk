#!/usr/bin/env python3
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence
from typing import Any, Mapping

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName

from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.apt import Section

DEFAULT_PARAMS = {
    "normal": 1,
    "removals": 1,
    "security": 2,
}


@pytest.fixture(name="check")
def _apt_check_plugin(fix_register: FixRegister) -> CheckPlugin:
    return fix_register.check_plugins[CheckPluginName("apt")]


def test_apt_discovery(check: CheckPlugin) -> None:
    assert list(check.discovery_function(Section([], [], []))) == [Service()]


@pytest.mark.parametrize(
    "params, section, expected_result",
    [
        pytest.param(
            DEFAULT_PARAMS,
            Section([], [], []),
            [Result(state=State.OK, summary="No updates pending for installation")],
            id="Nothing pending for installation.",
        ),
        pytest.param(
            DEFAULT_PARAMS,
            Section([], [], [], no_esm_support=True),
            [
                Result(
                    state=State.CRIT,
                    summary="System could receive security updates, but needs extended support license",
                ),
            ],
            id="The system has no esm support and there are no updates.",
        ),
        pytest.param(
            DEFAULT_PARAMS,
            Section(["base-files"], [], []),
            [
                Result(state=State.WARN, summary="1 normal updates"),
                Metric("normal_updates", 1.0),
                Result(state=State.OK, summary="0 security updates"),
                Metric("security_updates", 0.0),
            ],
            id="Only normal updates are available.",
        ),
        pytest.param(
            DEFAULT_PARAMS,
            Section([], [], ["base-files"]),
            [
                Result(state=State.OK, summary="0 normal updates"),
                Metric("normal_updates", 0.0),
                Result(state=State.CRIT, summary="1 security updates (base-files)"),
                Metric("security_updates", 1.0),
            ],
            id="Only security updates are available.",
        ),
        pytest.param(
            DEFAULT_PARAMS,
            Section([], ["base-files"], []),
            [
                Result(state=State.OK, summary="0 normal updates"),
                Metric("normal_updates", 0.0),
                Result(state=State.WARN, summary="1 auto removals (base-files)"),
                Metric("removals", 1.0),
                Result(state=State.OK, summary="0 security updates"),
                Metric("security_updates", 0.0),
            ],
            id="Only auto-removals updates are available.",
        ),
        pytest.param(
            DEFAULT_PARAMS,
            Section(["normal-update"], ["auto-removal-update"], ["security-update"]),
            [
                Result(state=State.WARN, summary="1 normal updates"),
                Metric("normal_updates", 1.0),
                Result(state=State.WARN, summary="1 auto removals (auto-removal-update)"),
                Metric("removals", 1.0),
                Result(state=State.CRIT, summary="1 security updates (security-update)"),
                Metric("security_updates", 1.0),
            ],
            id="Everything can be updated",
        ),
        pytest.param(
            DEFAULT_PARAMS,
            Section(
                ["normal-update"],
                ["auto-removal-update"],
                ["security-update"],
                no_esm_support=True,
            ),
            [
                Result(
                    state=State.CRIT,
                    summary="System could receive security updates, but needs extended support license",
                ),
            ],
            id="Updates are available, but no esm support",
        ),
        pytest.param(
            {"normal": 0, "removals": 2, "security": 1},
            Section(["normal-update"], ["auto-removal-update"], ["security-update"]),
            [
                Result(state=State.OK, summary="1 normal updates"),
                Metric("normal_updates", 1.0),
                Result(state=State.CRIT, summary="1 auto removals (auto-removal-update)"),
                Metric("removals", 1.0),
                Result(state=State.WARN, summary="1 security updates (security-update)"),
                Metric("security_updates", 1.0),
            ],
            id="Changed severity",
        ),
    ],
)
def test_check_apt(
    check: CheckPlugin,
    params: Mapping[str, Any],
    section: Section,
    expected_result: Sequence[Result | Metric],
) -> None:
    assert (
        list(
            check.check_function(
                item=None,
                params=params,
                section=section,
            )
        )
        == expected_result
    )
