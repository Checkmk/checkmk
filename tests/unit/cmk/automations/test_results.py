#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from typing import Mapping, Sequence

from cmk.automations.results import ABCAutomationResult, result_type_registry

from cmk.base.automations import automations


def test_result_type_registry_completeness():
    # ensures that all automation calls registered in cmk.base have a corresponding result type
    # registered in cmk.automations
    assert sorted(result_type_registry) == sorted(automations._automations)


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


def test_serialization():
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
