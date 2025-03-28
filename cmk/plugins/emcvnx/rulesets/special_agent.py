#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    migrate_to_password,
    MultipleChoice,
    MultipleChoiceElement,
    Password,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _parameter_form() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "The special agent is deprecated and will be removed in Checkmk 2.5.0. "
            "If you still require it, will be made available on the Checkmk Exchange "
            "(exchange.checkmk.com). Dell EMC VNX has been replaced in 2016 by Dell "
            "EMC Unity and is not supported anymore. Thus, naviseccli, the tool required "
            "for monitoring Dell EMC VNX is not maintained as well anymore, with potentially "
            "insecure dependencies."
            "This rule selects the EMC VNX agent instead of the normal Checkmk Agent "
            "and allows monitoring of EMC VNX storage systems by calling naviseccli "
            "commandline tool locally on the monitoring system. Make sure it is installed "
            "and working. You can configure your connection settings here."
        ),
        elements={
            "user": DictElement(
                parameter_form=String(
                    title=Title("EMC VNX admin user name"),
                    help_text=Help(
                        "If you don't configure the user name and password, the special agent "
                        "tries to authenticate against the EMC VNX device by Security Files. "
                        "These need to be created manually before using. Therefor run as "
                        "instance user (if using OMD) or Nagios user (if not using OMD) "
                        "a command like "
                        "<tt>naviseccli -AddUserSecurity -scope 0 -password PASSWORD -user USER</tt>. "
                        "This creates <tt>SecuredCLISecurityFile.xml</tt> and "
                        "<tt>SecuredCLIXMLEncrypted.key</tt> in the home directory of the user "
                        "and these files are used then."
                    ),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
            "password": DictElement(
                parameter_form=Password(
                    title=Title("EMC VNX admin user password"),
                    migrate=migrate_to_password,
                ),
            ),
            "infos": DictElement(
                required=True,
                parameter_form=MultipleChoice(
                    title=Title("Retrieve information about..."),
                    elements=[
                        MultipleChoiceElement(
                            name="disks",
                            title=Title("Disks"),
                        ),
                        MultipleChoiceElement(
                            name="hba",
                            title=Title("iSCSI HBAs"),
                        ),
                        MultipleChoiceElement(
                            name="hwstatus",
                            title=Title("Hardware status"),
                        ),
                        MultipleChoiceElement(
                            name="raidgroups",
                            title=Title("RAID groups"),
                        ),
                        MultipleChoiceElement(
                            name="agent",
                            title=Title("Model and revsion"),
                        ),
                        MultipleChoiceElement(
                            name="sp_util", title=Title("Storage processor utilization")
                        ),
                        MultipleChoiceElement(
                            name="writecache",
                            title=Title("Write cache state"),
                        ),
                        MultipleChoiceElement(
                            name="mirrorview",
                            title=Title("Mirror views"),
                        ),
                        MultipleChoiceElement(
                            name="storage_pools",
                            title=Title("Storage pools"),
                        ),
                    ],
                    prefill=DefaultValue(
                        [
                            "disks",
                            "hba",
                            "hwstatus",
                        ]
                    ),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
        },
        migrate=_migrate,
    )


def _migrate(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(value)

    migrated = {"infos": value["infos"]}

    if user := value.get("user"):
        migrated["user"] = user

    match password := value.get("password"):
        case None:
            return migrated
        case ("password", ""):
            return migrated
        case _:
            migrated["password"] = password

    return migrated


rule_spec_special_agent_emcvnx = SpecialAgent(
    name="emcvnx",
    title=Title("EMC VNX storage systems"),
    topic=Topic.STORAGE,
    parameter_form=_parameter_form,
    is_deprecated=True,
)
