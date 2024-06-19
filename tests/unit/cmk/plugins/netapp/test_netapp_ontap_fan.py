#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from polyfactory.factories.pydantic_factory import ModelFactory

from cmk.agent_based.v2 import Result, State
from cmk.plugins.netapp.agent_based.netapp_ontap_fan import (
    check_netapp_ontap_fan,
    check_netapp_ontap_fan_summary,
)
from cmk.plugins.netapp.models import ShelfFanModel


class ShelfFanModelFactory(ModelFactory):
    __model__ = ShelfFanModel


_FAN_MODELS = [
    ShelfFanModelFactory.build(list_id="10", id="1", state="ok"),
    ShelfFanModelFactory.build(list_id="10", id="2", state="ok"),
    ShelfFanModelFactory.build(list_id="10", id="3", state="error"),
]


def test_check_netapp_ontap_fan() -> None:
    section = {model.item_name(): model for model in _FAN_MODELS}

    result = check_netapp_ontap_fan(item="10/1", section=section)

    assert list(result) == [Result(state=State.OK, summary="Operational state OK")]


def test_check_netapp_ontap_fan_summary() -> None:
    section = {model.item_name(): model for model in _FAN_MODELS}

    result = check_netapp_ontap_fan_summary(item="summary", section=section)

    assert list(result) == [
        Result(state=State.OK, summary="OK: 2 of 3"),
        Result(state=State.CRIT, summary="Failed: 1 (10/3)"),
    ]
