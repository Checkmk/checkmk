#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    Integer,
    List,
    MultipleChoice,
    MultipleChoiceElement,
    String,
    TimeMagnitude,
    TimeSpan,
    validators,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def _migrate_entry(value: object) -> tuple[str, Mapping[str, object]]:
    match value:
        case (str() as path, list() as operations):
            return "folder", {"path": path, "operations": operations}
        case (str() as path, list() as files, list() as operations):
            return "files", {"path": path, "files": files, "operations": operations}
        case _:
            raise ValueError(f"Unexpected value: {value!r}")


def migrate(value: object) -> Mapping[str, object]:
    if isinstance(value, dict) and "deployment" in value:
        return value
    match value:
        case None:
            return {"deployment": ("do_not_deploy", None)}
        case (
            int() | float() as heartbeat_timeout,
            int() | float() as write_interval,
            int() as max_messages,
            int() | float() as stats_retention,
            list() as entries,
        ):
            return {
                "deployment": ("sync", None),
                "heartbeat_timeout": float(heartbeat_timeout),
                "write_interval": float(write_interval),
                "max_messages_per_interval": max_messages,
                "stats_retention": float(stats_retention),
                "entries": [_migrate_entry(e) for e in entries],
            }
        case _:
            raise ValueError(f"Unexpected value: {value!r}")


def _operations() -> Sequence[MultipleChoiceElement]:
    return [
        MultipleChoiceElement(name="create", title=Title("File created")),
        MultipleChoiceElement(name="delete", title=Title("File deleted")),
        MultipleChoiceElement(name="open", title=Title("File opened")),
        MultipleChoiceElement(name="modify", title=Title("File modified")),
        MultipleChoiceElement(name="access", title=Title("File accessed")),
        MultipleChoiceElement(name="movedfrom", title=Title("File moved from")),
        MultipleChoiceElement(name="movedto", title=Title("File moved to")),
        MultipleChoiceElement(name="moveself", title=Title("File move self")),
    ]


def _path_element() -> DictElement[str]:
    return DictElement(
        required=True,
        parameter_form=String(title=Title("Folder path")),
    )


def _operations_element() -> DictElement[Sequence[str]]:
    return DictElement(
        required=True,
        parameter_form=MultipleChoice(title=Title("Operation"), elements=_operations()),
    )


def _entry_form() -> CascadingSingleChoice:
    return CascadingSingleChoice(
        elements=(
            CascadingSingleChoiceElement(
                name="folder",
                title=Title("Monitor all files in folder"),
                parameter_form=Dictionary(
                    elements={"path": _path_element(), "operations": _operations_element()}
                ),
            ),
            CascadingSingleChoiceElement(
                name="files",
                title=Title("Monitor specific files in folder"),
                parameter_form=Dictionary(
                    elements={
                        "path": _path_element(),
                        "files": DictElement(
                            required=True,
                            parameter_form=List(
                                title=Title("File name"),
                                element_template=String(
                                    custom_validate=(validators.LengthInRange(min_value=1),)
                                ),
                            ),
                        ),
                        "operations": _operations_element(),
                    }
                ),
            ),
        ),
        prefill=DefaultValue("folder"),
    )


def _seconds(title: Title, help_text: Help, default: float) -> TimeSpan:
    return TimeSpan(
        title=title,
        help_text=help_text,
        displayed_magnitudes=(TimeMagnitude.MINUTE, TimeMagnitude.SECOND),
        prefill=DefaultValue(default),
    )


def _form_spec() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "The Inotify (Inode notify) is a Linux kernel subsystem that acts to extend "
            "file systems to notice changes to the file system. The Inotify plug-in collects these "
            "changes and reports them back to the monitoring system. You also need to install the "
            "pyinotify Python plug-in onto the target system."
        ),
        migrate=migrate,
        elements={
            "deployment": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Deployment type"),
                    elements=(
                        CascadingSingleChoiceElement(
                            name="sync",
                            title=Title("Deploy the plug-in"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="do_not_deploy",
                            title=Title("Do not deploy the plug-in"),
                            parameter_form=FixedValue(value=None),
                        ),
                    ),
                    prefill=DefaultValue("sync"),
                ),
            ),
            "heartbeat_timeout": DictElement(
                parameter_form=_seconds(
                    Title("Plug-in heartbeat timeout"),
                    Help(
                        "The Inotify is running permanently on the target system "
                        "and expects regular heartbeats to "
                        "continue running. If no heartbeat is received over this "
                        "time period, the plug-in simply stops. It starts again, the "
                        "next time the check_mk_agent is triggered."
                    ),
                    120.0,
                ),
            ),
            "write_interval": DictElement(
                parameter_form=_seconds(
                    Title("Save interval"),
                    Help("The time interval statistical data is saved to disk"),
                    10.0,
                ),
            ),
            "max_messages_per_interval": DictElement(
                parameter_form=Integer(
                    title=Title("Maximum messages per save interval"),
                    help_text=Help("The maximum number of messages per time interval"),
                    prefill=DefaultValue(100),
                ),
            ),
            "stats_retention": DictElement(
                parameter_form=_seconds(
                    Title("Statistic file retention time"),
                    Help(
                        "How long statistics files are kept on the target system. "
                        "This time should be at least double the check interval."
                    ),
                    120.0,
                ),
            ),
            "entries": DictElement(
                required=True,
                parameter_form=List(
                    title=Title("Files and folders to be monitored"),
                    element_template=_entry_form(),
                    add_element_label=Label("Add files to be monitored"),
                ),
            ),
        },
    )


rule_spec_mk_inotify = AgentConfig(
    title=Title("Monitor file operations with Inotify (Linux)"),
    name="mk_inotify",
    topic=Topic.LINUX,
    parameter_form=_form_spec,
)
