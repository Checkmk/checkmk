#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DefaultValue,
    DictElement,
    Dictionary,
    MultipleChoice,
    MultipleChoiceElement,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _parameter_form() -> Dictionary:
    return Dictionary(
        migrate=_migrate,
        help_text=Help(
            "This rule set selects the <tt>ibmsvc</tt> agent instead of the normal Checkmk Agent "
            "and allows monitoring of IBM SVC / V7000 storage systems by calling "
            "ls* commands there over SSH. "
            "Make sure you have SSH key authentication enabled for your monitoring user. "
            "That means: The user your monitoring is running under on the monitoring "
            "system must be able to ssh to the storage system as the user you gave below "
            "without password."
        ),
        elements={
            "user": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("IBM SVC / V7000 user name"),
                    help_text=Help(
                        "User name on the storage system. Read-only permissions are sufficient."
                    ),
                ),
            ),
            "accept_any_hostkey": DictElement(
                required=True,
                parameter_form=BooleanChoice(
                    title=Title("Accept any SSH Host Key"),
                    label=Label("Accept any SSH Host Key"),
                    prefill=DefaultValue(False),
                    help_text=Help(
                        "Accepts any SSH Host Key presented by the storage device. "
                        "Please note: This might be a security issue because man-in-the-middle "
                        "attacks are not recognized! Better solution would be to add the "
                        "SSH Host Key of the monitored storage devices to the .ssh/known_hosts "
                        "file for the user your monitoring is running under (on OMD: the site user)"
                    ),
                ),
            ),
            "infos": DictElement(
                required=True,
                parameter_form=MultipleChoice(
                    title=Title("Retrieve information about..."),
                    elements=[
                        MultipleChoiceElement(
                            name="lshost",
                            title=Title("Hosts Connected"),
                        ),
                        MultipleChoiceElement(
                            name="lslicense",
                            title=Title("Licensing Status"),
                        ),
                        MultipleChoiceElement(
                            name="lsmdisk",
                            title=Title("MDisks"),
                        ),
                        MultipleChoiceElement(
                            name="lsmdiskgrp",
                            title=Title("MDisksGrps"),
                        ),
                        MultipleChoiceElement(
                            name="lsnode",
                            title=Title("IO Groups"),
                        ),
                        MultipleChoiceElement(
                            name="lsnodestats",
                            title=Title("Node Stats"),
                        ),
                        MultipleChoiceElement(
                            name="lssystem",
                            title=Title("System Info"),
                        ),
                        MultipleChoiceElement(
                            name="lssystemstats",
                            title=Title("System Stats"),
                        ),
                        MultipleChoiceElement(
                            name="lseventlog",
                            title=Title("Event Log"),
                        ),
                        MultipleChoiceElement(
                            name="lsportfc",
                            title=Title("FC Ports"),
                        ),
                        MultipleChoiceElement(
                            name="lsportsas",
                            title=Title("SAS Ports"),
                        ),
                        MultipleChoiceElement(
                            name="lsenclosure",
                            title=Title("Enclosures"),
                        ),
                        MultipleChoiceElement(
                            name="lsenclosurestats",
                            title=Title("Enclosure Stats"),
                        ),
                        MultipleChoiceElement(
                            name="lsarray",
                            title=Title("RAID Arrays"),
                        ),
                        MultipleChoiceElement(
                            name="disks",
                            title=Title("Physical Disks"),
                        ),
                    ],
                    prefill=DefaultValue(
                        [
                            "lshost",
                            "lslicense",
                            "lsmdisk",
                            "lsmdiskgrp",
                            "lsnode",
                            "lsnodestats",
                            "lssystem",
                            "lssystemstats",
                            "lsportfc",
                            "lsenclosure",
                            "lsenclosurestats",
                            "lsarray",
                            "disks",
                        ]
                    ),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
        },
    )


rule_spec_special_agent_ibmsvc = SpecialAgent(
    name="ibmsvc",
    title=Title("IBM SVC / V7000 storage systems"),
    topic=Topic.STORAGE,
    parameter_form=_parameter_form,
)


def _migrate(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(object)
    if "accept_any_hostkey" in value:
        return value
    return {k: v for k, v in value.items() if k != "accept-any-hostkey"} | {
        "accept_any_hostkey": value["accept-any-hostkey"]
    }
