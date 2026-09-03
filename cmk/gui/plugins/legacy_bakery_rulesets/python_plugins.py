#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    SingleChoice,
    SingleChoiceElement,
    String,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def migrate(value: object) -> Mapping[str, object]:
    match value:
        case {"python_version": _}:
            return value  # type: ignore[return-value]
        case {"version": version, **rest}:
            # Old rule ("first matching rule wins"): make all parameters explicit so that merging
            # with other rules does not change the outcome. An empty command means "default".
            return {"python_version": version, "command": rest.get("command", "")}
        case _:
            raise ValueError(f"Unexpected value: {value!r}")


def _form_spec() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "By default, Python agent plug-ins are written in Python 3. However,"
            " since Python 2 is still often seen on many machines, we provide a"
            " fallback Python 2 version alongside the Python 3 version of the"
            " plug-ins, that is used as a fallback if there is no Python 3 version"
            " available on the host.<br>"
            "With this rule, you can enforce the usage of either the Python 2 or"
            " Python 3 version.<br>"
            "Additionally, you can provide a command, that will be used for Python"
            " plug-in execution."
        ),
        migrate=migrate,
        elements={
            # Renamed from "version" to tell rules stored before the migration to the
            # rulesets v1 API from rules stored afterwards.
            "python_version": DictElement(
                required=True,
                parameter_form=SingleChoice(
                    title=Title("Python version for execution of Python agent plug-ins"),
                    help_text=Help(
                        "The Checkmk agent Unix will detect a Python 3 installation by looking for"
                        " the command <tt>python3</tt>, and a Python 2 installation by looking for"
                        " the commands <tt>python2</tt> or <tt>python</tt>. If this doesn't match"
                        " to your host's Python installation, e.g., if Python 3 is available via"
                        " <tt>python</tt>, you can enforce the right version by setting this rule"
                        " entry."
                    ),
                    elements=[
                        SingleChoiceElement(
                            name="auto",
                            title=Title("Automatic detection (Python 3 > Python 2)"),
                        ),
                        SingleChoiceElement(
                            name="python2",
                            title=Title("Enforce Python 2 version"),
                        ),
                        SingleChoiceElement(
                            name="python3",
                            title=Title("Enforce Python 3 version"),
                        ),
                    ],
                    prefill=DefaultValue("auto"),
                ),
            ),
            "command": DictElement(
                parameter_form=String(
                    title=Title("Provide command for python script execution"),
                    help_text=Help(
                        "By default, the Checkmk Unix agent will execute Python 3 plug-ins with"
                        " <tt>python3</tt> and Python 2 plug-ins with <tt>python2</tt> or"
                        " <tt>python</tt> (depending on the command found on the host system)."
                        " Here you can specify a specific command, independent of the script"
                        " that will be executed. An empty command means the default."
                    ),
                ),
            ),
        },
    )


rule_spec_python_plugins = AgentConfig(
    title=Title("Python agent plug-in execution (Linux, Unix)"),
    name="python_plugins",
    topic=Topic.LINUX,
    parameter_form=_form_spec,
)
