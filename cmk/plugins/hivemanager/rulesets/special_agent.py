#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    migrate_to_password,
    Password,
    String,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _parameter_form() -> Dictionary:
    return Dictionary(
        migrate=_migrate,
        help_text=Help("Activate monitoring of host via a HTTP connect to the HiveManager"),
        elements={
            "username": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Username"),
                ),
            ),
            "password": DictElement(
                required=True,
                parameter_form=Password(
                    title=Title("Password"),
                    migrate=migrate_to_password,
                ),
            ),
        },
    )


rule_spec_special_agent_hivemanager = SpecialAgent(
    name="hivemanager",
    title=Title("Aerohive HiveManager"),
    topic=Topic.SERVER_HARDWARE,
    parameter_form=_parameter_form,
)


def _migrate(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return value
    if isinstance(value, tuple):
        return {
            "username": value[0],
            "password": value[1],
        }
    raise TypeError(value)
