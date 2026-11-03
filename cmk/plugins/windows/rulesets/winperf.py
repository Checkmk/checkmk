#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    List,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def _migrate_counter(value: object) -> Mapping[str, object]:
    if isinstance(value, dict) and "section" in value:
        return value
    if isinstance(value, list | tuple) and len(value) == 2:
        section, counter = value
        return {"section": section, "counter": counter}
    raise ValueError(f"Unexpected value: {value!r}")


def migrate(value: object) -> Mapping[str, object]:
    if isinstance(value, dict) and "counters" in value:
        return value
    if isinstance(value, list):
        return {"counters": [_migrate_counter(v) for v in value]}
    raise ValueError(f"Unexpected value: {value!r}")


def _counter_form() -> Dictionary:
    return Dictionary(
        migrate=_migrate_counter,
        elements={
            "section": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Section name"),
                    help_text=Help(
                        "Choose a name here. If you choose <tt>foo</tt> then section header and thus "
                        "the name of the required check plug-in will be "
                        "&lt;&lt;&lt;winperf_foo&gt;&gt;&gt;."
                    ),
                    custom_validate=(
                        validators.MatchRegex(
                            "^[a-z]+[a-z0-9_]*$",
                            Message("Use only lower case letters, digits, and underscores here."),
                        ),
                    ),
                ),
            ),
            "counter": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Counter-object name or number"),
                    custom_validate=(
                        validators.LengthInRange(min_value=1),
                        validators.MatchRegex(
                            "^[^\\\\]*$", Message("Backslashes are not allowed here.")
                        ),
                    ),
                ),
            ),
        },
    )


def _form_spec() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "Here, you can configure which performance counter objects the Windows agent "
            "should extract and provide to the Checkmk server. You can either specify "
            "counter numbers or names. Note: numbers might be host-specific. Names are "
            "language-specific. Also note that you need to specify names of counter <i>objects</i>, "
            "not of single counters. In order to make use of the counters you need a "
            "matching check plug-in on the Checkmk server."
        ),
        migrate=migrate,
        elements={
            "counters": DictElement(
                required=True,
                parameter_form=List(
                    element_template=_counter_form(),
                    add_element_label=Label("Add counter object"),
                ),
            ),
        },
    )


rule_spec_winperf = AgentConfig(
    title=Title("Windows Performance-Counter objects"),
    name="winperf",
    topic=Topic.WINDOWS,
    parameter_form=_form_spec,
)
