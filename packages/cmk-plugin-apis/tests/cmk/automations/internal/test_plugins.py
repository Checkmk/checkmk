#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import override

import pytest

from cmk.automations.internal import (
    Automation,
    AutomationID,
    AutomationResult,
    NoState,
)


class _Result(AutomationResult):
    def __init__(self, text: str) -> None:
        self.text = text

    @override
    def serialize(self, _for_cmk_version: str) -> str:
        return repr(self.text)

    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("greet")


def _handler(_state: NoState, args: list[str]) -> _Result:
    return _Result(" ".join(args))


def test_wrong_result_type_raises() -> None:
    with pytest.raises(TypeError):
        _ = Automation(
            name=AutomationID("other"), state_factory=NoState, handler=_handler, result=_Result
        )
