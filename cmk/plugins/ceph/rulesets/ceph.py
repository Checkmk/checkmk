#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="exhaustive-match"


from collections.abc import Mapping

from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    String,
    TimeMagnitude,
    TimeSpan,
    validators,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def migrate_bakery_rule(value: object) -> Mapping[str, object]:
    match value:
        case bool(deploy):  # old mkp format
            return {"deploy": deploy, "interval": ("cached", 58.0)}
        case None:
            return {"deploy": False, "interval": ("cached", 58.0)}
        case {"interval": int(seconds), **rest}:
            return {
                **{str(k): v for k, v in rest.items()},
                "deploy": True,
                "interval": ("cached", float(seconds)),
            }
        case dict():
            return {"deploy": True, **value}
    raise ValueError(value)


def _form_spec_agent_config_ceph() -> Dictionary:
    return Dictionary(
        migrate=migrate_bakery_rule,
        help_text=Help(
            "This will deploy the agent plugin <tt>ceph</tt> for monitoring the status of Ceph."
            " This plug-in will be run asynchronously in the background."
        ),
        elements={
            "deploy": DictElement(
                required=True,
                parameter_form=BooleanChoice(
                    label=Label("Deploy plugin for Ceph"),
                    prefill=DefaultValue(True),
                ),
            ),
            "interval": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Synchronicity / caching"),
                    prefill=DefaultValue("uncached"),
                    elements=(
                        CascadingSingleChoiceElement(
                            name="uncached",
                            title=Title("Run synchronously"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="cached",
                            title=Title("Run asynchronously"),
                            parameter_form=TimeSpan(
                                label=Label("Interval for collecting data from Ceph"),
                                displayed_magnitudes=[TimeMagnitude.MINUTE, TimeMagnitude.SECOND],
                                prefill=DefaultValue(58.0),
                            ),
                        ),
                    ),
                ),
            ),
            "config": DictElement(
                parameter_form=String(
                    prefill=DefaultValue("/etc/ceph/ceph.conf"),
                    title=Title("Path to ceph.conf"),
                    custom_validate=(
                        validators.MatchRegex("^/.*", Message("Please enter an absolute path.")),
                    ),
                ),
            ),
            "client": DictElement(
                parameter_form=String(
                    prefill=DefaultValue("client.admin"),
                    title=Title("Client name"),
                ),
            ),
        },
    )


rule_spec_ceph = AgentConfig(
    title=Title("Ceph (Linux)"),
    name="ceph",
    topic=Topic.STORAGE,
    parameter_form=_form_spec_agent_config_ceph,
)
