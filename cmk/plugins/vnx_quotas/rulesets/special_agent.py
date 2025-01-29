#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    migrate_to_password,
    Password,
    String,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _paramater_form() -> Dictionary:
    return Dictionary(
        title=Title("VNX quotas and filesystems"),
        elements={
            "user": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("NAS DB user name"),
                ),
            ),
            "password": DictElement(
                required=True,
                parameter_form=Password(
                    title=Title("Password"),
                    migrate=migrate_to_password,
                ),
            ),
            "nas_db": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("NAS DB path"),
                ),
            ),
        },
    )


rule_spec_special_agent_vnx_quotas = SpecialAgent(
    name="vnx_quotas",
    title=Title("VNX quotas and filesystems"),
    topic=Topic.STORAGE,
    parameter_form=_paramater_form,
)
