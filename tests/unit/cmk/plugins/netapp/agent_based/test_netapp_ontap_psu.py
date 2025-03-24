#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from polyfactory.factories.pydantic_factory import ModelFactory

from cmk.plugins.netapp.agent_based.netapp_ontap_psu import _get_section_single_instance
from cmk.plugins.netapp.models import ShelfPsuModel


class ShelfPsuModelFactory(ModelFactory):
    __model__ = ShelfPsuModel


_PSU_MODELS = [
    ShelfPsuModelFactory.build(list_id="10", id="0", state="ok"),
    ShelfPsuModelFactory.build(list_id="10", id="1", state="error"),
    ShelfPsuModelFactory.build(list_id="20", id="2", state="ok"),
]


def test_get_section_single_instance() -> None:
    section = {psu_model.item_name(): psu_model for psu_model in _PSU_MODELS}

    result = _get_section_single_instance(section)

    assert result == {
        "10/0": {"power-supply-is-error": "false", "power-supply-element-number": "10/0"},
        "10/1": {"power-supply-is-error": "true", "power-supply-element-number": "10/1"},
        "20/2": {"power-supply-is-error": "false", "power-supply-element-number": "20/2"},
    }
