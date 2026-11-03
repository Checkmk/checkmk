#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.rulesets.v1 import Help, Message, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    List,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def migrate(value: object) -> Mapping[str, object]:
    if isinstance(value, dict) and "mode" in value:
        return value
    match value:
        case None:
            return {"mode": ("all_files", None)}
        case list() as suffixes:
            return {"mode": ("only", suffixes)}
        case _:
            raise ValueError(f"Unexpected value: {value!r}")


def _form_spec() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "If you want to run your own custom agent plug-ins on Windows, "
            "simply put them into the subdirectory <tt>plug-ins</tt> "
            "of your agent's installation directory. <i>Local checks</i> work just the "
            "same, but are installed in <tt>local</tt>. Plug-ins that are deployed "
            "with the Agent Bakery are installed by the MSI installer into the same "
            "directory. This rule set limits the file extensions that the agent "
            "will run. This for example avoids starting a notepad when a file with "
            "the extension <tt>.txt</tt> is found. <b>Note:</b> If you remove some "
            "of the default extensions, not all of the shipped agent plug-ins will "
            "continue to work!<br><br>Specify the extensions in lower case and without "
            "a leading dot. The agent's built-in list is <tt>exe bat vbs cmd ps1</tt>."
        ),
        migrate=migrate,
        elements={
            "mode": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Script types to execute"),
                    elements=(
                        CascadingSingleChoiceElement(
                            name="all_files",
                            title=Title("Use the agent's built-in list of extensions"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="only",
                            title=Title("Only execute plug-ins with the following extensions"),
                            parameter_form=List(
                                element_template=String(
                                    custom_validate=(
                                        validators.MatchRegex(
                                            "^[a-z0-9]{1,8}$",
                                            Message(
                                                "Please specify the extensions in lower case "
                                                "and without dot."
                                            ),
                                        ),
                                    ),
                                ),
                            ),
                        ),
                    ),
                    prefill=DefaultValue("all_files"),
                ),
            ),
        },
    )


rule_spec_win_exe_suffixes = AgentConfig(
    title=Title("Limit script types to execute"),
    name="win_exe_suffixes",
    topic=Topic.WINDOWS,
    parameter_form=_form_spec,
)
