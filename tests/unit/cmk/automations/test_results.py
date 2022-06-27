#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from typing import Mapping, Sequence

from cmk.utils.type_defs import DiscoveryResult as SingleHostDiscoveryResult
from cmk.utils.version import is_raw_edition

from cmk.automations.results import (
    ABCAutomationResult,
    CheckPreviewEntry,
    DiscoveryResult,
    result_type_registry,
    TryDiscoveryResult,
)

from cmk.base.automations import automations


def test_result_type_registry_completeness() -> None:
    # ensures that all automation calls registered in cmk.base have a corresponding result type
    # registered in cmk.automations
    automations_missing = {"bake-agents"} if is_raw_edition() else set()
    assert sorted(set(result_type_registry) - automations_missing) == sorted(
        automations._automations
    )


@dataclass
class AutomationResultTest(ABCAutomationResult):
    a: int
    b: str
    c: bool
    d: Sequence[None]
    e: Mapping[str, str]

    @staticmethod
    def automation_call() -> str:
        return "test"


def test_serialization() -> None:
    automation_res_test = AutomationResultTest(
        a=1,
        b="string",
        c=True,
        d=(
            None,
            None,
        ),
        e={
            "a": "test",
            "123": "456",
        },
    )
    assert automation_res_test == AutomationResultTest.deserialize(automation_res_test.serialize())


class TestDiscoveryResult:
    HOSTS = {
        "host_1": SingleHostDiscoveryResult(
            clustered_new=0,
            clustered_old=0,
            clustered_vanished=0,
            diff_text=None,
            error_text="",
            self_kept=0,
            self_new=0,
            self_new_host_labels=0,
            self_removed=0,
            self_total=0,
            self_total_host_labels=0,
        ),
        "host_2": SingleHostDiscoveryResult(
            clustered_new=1,
            clustered_old=2,
            clustered_vanished=3,
            diff_text="something changed",
            error_text="error",
            self_kept=4,
            self_new=5,
            self_new_host_labels=6,
            self_removed=7,
            self_total=8,
            self_total_host_labels=9,
        ),
    }

    def test_serialization(self) -> None:
        assert DiscoveryResult.deserialize(
            DiscoveryResult(self.HOSTS).serialize()
        ) == DiscoveryResult(self.HOSTS)


class TestTryDiscoveryResult:
    def test_serialization(self) -> None:
        result = TryDiscoveryResult(
            output="output",
            check_table=[
                CheckPreviewEntry(
                    check_source="check_source",
                    check_plugin_name="check_plugin_name",
                    ruleset_name=None,
                    item=None,
                    discovered_parameters=None,
                    effective_parameters=None,
                    description="description",
                    state=0,
                    output="output",
                    metrics=[],
                    labels={},
                    found_on_nodes=[],
                )
            ],
            host_labels={},
            new_labels={},
            vanished_labels={},
            changed_labels={},
        )
        assert TryDiscoveryResult.deserialize(result.serialize()) == result
