#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.tcp.lib.models import ConnectionState
from cmk.plugins.tcp.lib.validators import IPAddress
from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    LevelDirection,
    LevelsType,
    migrate_to_integer_simple_levels,
    SimpleLevels,
    SingleChoice,
    SingleChoiceElement,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import EnforcedService, HostAndItemCondition, Topic


def _make_form() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "This rule allows to monitor the existence of specific TCP connections or "
            "TCP/UDP listeners."
        ),
        elements={
            "proto": DictElement(
                required=False,
                parameter_form=SingleChoice(
                    title=Title("Protocol"),
                    prefill=DefaultValue("TCP"),
                    elements=[
                        SingleChoiceElement(
                            name="TCP",
                            title=Title("TCP"),
                        ),
                        SingleChoiceElement(
                            name="UDP",
                            title=Title("UDP"),
                        ),
                    ],
                ),
            ),
            "state": DictElement(
                required=False,
                parameter_form=SingleChoice(
                    title=Title("State"),
                    elements=[
                        SingleChoiceElement(
                            name=state,
                            title=Title(state),  # pylint: disable=localization-of-non-literal-string
                        )
                        for state in sorted(ConnectionState)
                    ],
                ),
            ),
            "local_ip": DictElement(
                required=False,
                parameter_form=String(title=Title("Local IP"), custom_validate=[IPAddress()]),
            ),
            "local_port": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Local port number"), custom_validate=[validators.NetworkPort()]
                ),
            ),
            "remote_ip": DictElement(
                required=False,
                parameter_form=String(title=Title("Remote IP"), custom_validate=[IPAddress()]),
            ),
            "remote_port": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Remote port number"), custom_validate=[validators.NetworkPort()]
                ),
            ),
            "max_states": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Maximum number of connections or listeners"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(),
                    prefill_levels_type=DefaultValue(LevelsType.NONE),
                    prefill_fixed_levels=DefaultValue((50, 100)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "min_states": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Minimum number of connections or listeners"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Integer(),
                    prefill_levels_type=DefaultValue(LevelsType.NONE),
                    prefill_fixed_levels=DefaultValue((5, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
        },
    )


rule_spec_tcp_connections = EnforcedService(
    name="tcp_connections",
    topic=Topic.NETWORKING,
    parameter_form=_make_form,
    title=Title("Monitor specific TCP/UDP connections and listeners"),
    condition=HostAndItemCondition(item_title=Title("Connection name")),
)
