#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    SingleChoice,
    SingleChoiceElement,
    validators,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def _form_spec() -> Dictionary:
    return Dictionary(
        elements={
            "logging_level": DictElement(
                parameter_form=SingleChoice(
                    title=Title("Logging level"),
                    label=Label("Set the logging level for Windows agent"),
                    help_text=Help(
                        "This setting determines how detailed the log file of the Windows agent "
                        "will be."
                    ),
                    elements=[
                        SingleChoiceElement(
                            name="no",
                            title=Title("Write to log file only most important events"),
                        ),
                        SingleChoiceElement(
                            name="yes",
                            title=Title("Write to log file all important events and all warnings"),
                        ),
                        SingleChoiceElement(
                            name="all",
                            title=Title("Write to log file everything"),
                        ),
                    ],
                    prefill=DefaultValue("yes"),
                ),
            ),
            "max_log_file_count": DictElement(
                parameter_form=Integer(
                    title=Title("Maximal number of log files to backup"),
                    help_text=Help(
                        "Number of log files used during log rotation as a backup. "
                        "Once this number of log files is exceeded, "
                        "the oldest log file will be deleted."
                    ),
                    prefill=DefaultValue(5),
                    custom_validate=(validators.NumberInRange(min_value=0, max_value=64),),
                ),
            ),
            "max_log_file_size": DictElement(
                parameter_form=Integer(
                    title=Title("Maximal log file size"),
                    help_text=Help("Maximal size of a log file"),
                    unit_symbol="B",
                    prefill=DefaultValue(8000000),
                    custom_validate=(
                        validators.NumberInRange(min_value=256 * 1024, max_value=256 * 1024 * 1024),
                    ),
                ),
            ),
            "log_to_windbg": DictElement(
                parameter_form=BooleanChoice(
                    title=Title("Windows debugging"),
                    label=Label("write log messages to the Windows debugging interface"),
                    help_text=Help(
                        "Enable/disable logging to Windows debugging interface. Off by default. "
                        "View with <i>WinDbg</i>"
                    ),
                    prefill=DefaultValue(False),
                ),
            ),
        },
    )


rule_spec_logging = AgentConfig(
    title=Title("Windows agent logging"),
    name="logging",
    topic=Topic.WINDOWS,
    parameter_form=_form_spec,
)
