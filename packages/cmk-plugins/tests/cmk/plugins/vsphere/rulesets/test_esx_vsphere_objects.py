#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.vsphere.rulesets.esx_vsphere_objects import rule_spec_esx_vsphere_objects
from cmk.rulesets.v1.form_specs import String
from cmk.rulesets.v1.form_specs.validators import ValidationError
from cmk.rulesets.v1.rule_specs import HostAndItemCondition


def _validate_item(item: str) -> None:
    condition = rule_spec_esx_vsphere_objects.condition
    assert isinstance(condition, HostAndItemCondition)
    assert isinstance(condition.item_form, String)
    assert condition.item_form.custom_validate is not None
    for validate in condition.item_form.custom_validate:
        validate(item)


def _rejection_message(item: str) -> str:
    with pytest.raises(ValidationError) as rejection:
        _validate_item(item)
    return rejection.value.message.localize(lambda text: text)


def test_items_naming_a_vm_are_accepted() -> None:
    _validate_item("VM web-01")


def test_items_naming_a_host_system_are_accepted() -> None:
    _validate_item("HostSystem esx01.example.com")


def test_items_without_an_object_type_prefix_are_rejected() -> None:
    assert "must begin with" in _rejection_message("web-01")


def test_template_items_are_rejected() -> None:
    assert "must begin with" in _rejection_message("Template golden-image")
