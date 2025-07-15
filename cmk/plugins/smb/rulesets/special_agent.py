#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.ccc.hostaddress import HostAddress

from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DictElement,
    Dictionary,
    FieldSize,
    List,
    migrate_to_password,
    Password,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _parameter_form() -> Dictionary:
    return Dictionary(
        title=Title("SMB Share fileinfo"),
        elements={
            "hostname": DictElement(
                required=False,
                parameter_form=String(
                    title=Title("Host name"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                    help_text=Help(
                        "<p>Usually Checkmk will use the host name of the host it is attached to. "
                        "With this option you can override this parameter.</p>"
                    ),
                ),
            ),
            "ip_address": DictElement(
                required=False,
                parameter_form=String(
                    title=Title("IP address"),
                    custom_validate=(
                        validators.LengthInRange(min_value=1),
                        _validate_hostname,
                    ),
                    help_text=Help(
                        "<p>Usually Checkmk will use the primary IP address of the host it is "
                        "attached to. With this option you can override this parameter.</p>"
                    ),
                ),
            ),
            "authentication": DictElement(
                required=False,
                parameter_form=Dictionary(
                    title=Title("Authentication"),
                    elements={
                        "username": DictElement(
                            required=True,
                            parameter_form=String(
                                title=Title("Username"),
                                custom_validate=(validators.LengthInRange(min_value=1),),
                            ),
                        ),
                        "password": DictElement(
                            required=True,
                            parameter_form=Password(
                                title=Title("Password"),
                                custom_validate=(validators.LengthInRange(min_value=1),),
                                migrate=migrate_to_password,
                            ),
                        ),
                    },
                    migrate=_migrate_tuple_to_dict,
                ),
            ),
            "patterns": DictElement(
                required=True,
                parameter_form=List(
                    title=Title("File patterns"),
                    help_text=Help(
                        "<p>Here you can specify a list of filename patterns to be sent by the "
                        "agent in the section <tt>fileinfo</tt>. UNC paths with globbing patterns "
                        "are used here, e.g. <tt>\\\\hostname\\share name\\*\\foo\\*.log</tt>. "
                        "Wildcards are not allowed in host or share names. "
                        "Per default each found file will be monitored for size and age. "
                        "By building groups you can alternatively monitor a collection "
                        "of files as an entity and monitor the count, total size, the largest, "
                        "smallest oldest or newest file. Note: if you specify more than one matching rule, then "
                        "<b>all</b> matching rules will be used for defining pattern - not just the "
                        " first one.</p>"
                    ),
                    element_template=String(field_size=FieldSize.LARGE),
                    add_element_label=Label("Add pattern"),
                    remove_element_label=Label("Remove pattern"),
                    editable_order=False,
                ),
            ),
            "recursive": DictElement(
                required=False,
                parameter_form=BooleanChoice(
                    title=Title("Recursive pattern search"),
                    label=Label("Match multiple directories with **"),
                    help_text=Help(
                        "If ** is used in the pattern, the agent will recursively look into all the subfolders, "
                        "so use this carefully on a deeply nested filesystems."
                    ),
                ),
            ),
        },
    )


def _validate_hostname(value: str) -> None:
    try:
        HostAddress(value)
    except ValueError as exception:
        raise validators.ValidationError(
            message=Message(
                "Please enter a valid host name or IPv4 address. "
                "Only letters, digits, dash, underscore and dot are allowed."
            )
        ) from exception


def _migrate_tuple_to_dict(param: object) -> Mapping[str, object]:
    match param:
        case (username, password):
            return {"username": username, "password": password}
        case dict() as already_migrated:
            return already_migrated
    raise ValueError(param)


rule_spec_special_agent_smb_share = SpecialAgent(
    name="smb_share",
    title=Title("SMB Share fileinfo"),
    topic=Topic.GENERAL,
    parameter_form=_parameter_form,
)
