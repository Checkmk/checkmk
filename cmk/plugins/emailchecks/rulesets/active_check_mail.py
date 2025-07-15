#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from typing import Literal

from cmk.ccc.version import Edition, edition
from cmk.gui.mkeventd import syslog_facilities  # pylint: disable=cmk-module-layer-violation
from cmk.plugins.emailchecks.forwarding_option import ECForwarding
from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    Integer,
    MatchingScope,
    RegularExpression,
    SingleChoice,
    SingleChoiceElement,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import ActiveCheck, Topic
from cmk.utils import paths

from .options import fetching, timeout


def _valuespec_active_checks_mail() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "The basic function of this check is to log in into an IMAP, POP3 or EWS mailbox "
            "to monitor whether or not the login is possible. An extended feature is, that the "
            "check can fetch all (or just some) from the mailbox and forward them as events "
            "to the Event Console."
        ),
        elements={
            "service_description": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Service name"),
                    help_text=Help(
                        "Please make sure that this is unique per host "
                        "and does not collide with other services."
                    ),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                    prefill=DefaultValue("Email"),
                ),
            ),
            "fetch": DictElement(
                required=True,
                parameter_form=fetching({"IMAP", "POP3", "EWS"}),
            ),
            "connect_timeout": DictElement(
                parameter_form=timeout(),
            ),
            **(
                {}
                if edition(paths.omd_root) is Edition.CSE
                else {"forward": DictElement(parameter_form=_forward_to_ec_form())}
            ),
        },
    )


def _migrate_method(
    value: object,
) -> tuple[Literal["ec"], ECForwarding] | tuple[Literal["syslog"], Mapping[str, object]]:
    match value:
        # already migrated cases:
        case "ec", ("local", ""):
            return "ec", ("local", "")
        case "ec", ("socket", str(socket)):
            return "ec", ("socket", socket)
        case "ec", ("spool_local", ""):
            return "ec", ("spool_local", "")
        case "ec", ("spool", str(spooldir)):
            return "ec", ("spool", spooldir)
        case "syslog", dict() as syslog_forwarding:
            return "syslog", syslog_forwarding
        # actual migration:
        case ("udp" | "tcp" as protocol, str(address), int(port)):
            return "syslog", {"protocol": protocol, "address": address, "port": port}
        case "":
            return "ec", ("local", "")
        case "spool:":
            return "ec", ("spool_local", "")
        case str(spooldir) if spooldir.startswith("spool:"):
            return "ec", ("spool", spooldir[6:])
        case str(socket):
            return "ec", ("socket", socket)

    raise ValueError(f"Invalid method value: {value!r}")


def _ec_forwarding() -> CascadingSingleChoice:
    return CascadingSingleChoice(
        title=Title("Send events to local event console"),
        prefill=DefaultValue("local"),
        elements=(
            CascadingSingleChoiceElement(
                name="local",
                title=Title("Send events to local event console in same OMD site"),
                parameter_form=FixedValue(value=""),
            ),
            CascadingSingleChoiceElement(
                name="socket",
                title=Title("Send events to local event console into unix socket"),
                parameter_form=String(
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
            CascadingSingleChoiceElement(
                name="spool_local",
                title=Title("Spooling: Send events to local event console in same OMD site"),
                parameter_form=FixedValue(value=""),
            ),
            CascadingSingleChoiceElement(
                name="spool",
                title=Title(
                    "Spooling: Send events to local event console into given spool directory"
                ),
                parameter_form=String(
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
        ),
    )


def _syslog_forwarding() -> Dictionary:
    return Dictionary(
        elements={
            "protocol": DictElement(
                required=True,
                parameter_form=SingleChoice(
                    title=Title("Protocol"),
                    elements=(
                        SingleChoiceElement(name="udp", title=Title("UDP")),
                        SingleChoiceElement(name="tcp", title=Title("TCP")),
                    ),
                ),
            ),
            "address": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Address"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
            "port": DictElement(
                required=True,
                parameter_form=Integer(
                    title=Title("Port"),
                    prefill=DefaultValue(514),
                    custom_validate=(validators.NetworkPort(),),
                ),
            ),
        },
    )


def _migrate_facility(value: object) -> tuple[str, int]:
    match value:
        case tuple((str(s), int(i))):
            return (s, i)
        case int(i):
            return next((name, facility) for facility, name in syslog_facilities if facility == i)
    raise ValueError(f"Invalid facility value: {value!r}")


def _migrate_application(
    value: object,
) -> tuple[Literal["subject"], None] | tuple[Literal["spec"], str]:
    return ("subject", None) if value is None else ("spec", str(value))


def _forward_to_ec_form() -> Dictionary:
    return Dictionary(
        title=Title("Forward mails as events to Event Console"),
        elements={
            "method": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Title("Forwarding Method"),
                    prefill=DefaultValue("ec"),
                    elements=(
                        CascadingSingleChoiceElement(
                            name="ec",
                            title=Title("Send events to local event console"),
                            parameter_form=_ec_forwarding(),
                        ),
                        CascadingSingleChoiceElement(
                            name="syslog",
                            title=Title("Send events to remote syslog host"),
                            parameter_form=_syslog_forwarding(),
                        ),
                    ),
                    migrate=_migrate_method,
                ),
            ),
            "match_subject": DictElement(
                parameter_form=RegularExpression(
                    title=Title("Only process mails with matching subject"),
                    help_text=Help(
                        "Use this option to not process all messages found in the inbox, "
                        "but only the those whose subject matches the given regular expression."
                    ),
                    predefined_help_text=MatchingScope.PREFIX,
                ),
            ),
            "facility": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Title("Events: Syslog facility"),
                    help_text=Help("Use this syslog facility for all created events"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name=name,
                            title=Title(  # pylint: disable=localization-of-non-literal-string  # we have no choice here.
                                name
                            ),
                            parameter_form=FixedValue(value=value),
                        )
                        for value, name in syslog_facilities
                    ],
                    # our tests will fail if this is no longer found in syslog_facilities
                    prefill=DefaultValue("mail"),
                    migrate=_migrate_facility,
                ),
            ),
            "application": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Title("Events: Syslog application"),
                    help_text=Help("Use this syslog application for all created events"),
                    prefill=DefaultValue("subject"),
                    elements=(
                        CascadingSingleChoiceElement(
                            name="subject",
                            title=Title("Use the mail subject as syslog application"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="spec",
                            title=Title("Specify the application"),
                            parameter_form=String(
                                help_text=Help(
                                    "Use this text as application. You can use macros like <tt>\\1</tt>, <tt>\\2</tt>, ... "
                                    "here when you configured <i>subject matching</i> in this rule with a regular expression "
                                    "that declares match groups (using braces)."
                                ),
                                custom_validate=(validators.LengthInRange(min_value=1),),
                            ),
                        ),
                    ),
                    migrate=_migrate_application,
                ),
            ),
            "host": DictElement(
                parameter_form=String(
                    title=Title("Events: Host name"),
                    help_text=Help(
                        "Use this host name for all created events instead of the name of the mailserver"
                    ),
                )
            ),
            "body_limit": DictElement(
                parameter_form=Integer(
                    title=Title("Limit length of mail body"),
                    help_text=Help(
                        "When forwarding mails from the mailbox to the event console, the "
                        "body of the mail is limited to the given number of characters."
                    ),
                    prefill=DefaultValue(1000),
                )
            ),
            "cleanup": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Title("Cleanup messages"),
                    help_text=Help(
                        "The handled messages (see <i>subject matching</i>) can be cleaned up by either "
                        "deleting them or moving them to a subfolder. By default nothing is cleaned up."
                    ),
                    elements=(
                        CascadingSingleChoiceElement(
                            name="delete",
                            title=Title("Delete all processed messages belonging to this check"),
                            parameter_form=FixedValue(value="delete"),
                        ),
                        CascadingSingleChoiceElement(
                            name="move",
                            title=Title("Move all processed messages to subfolder"),
                            parameter_form=String(
                                title=Title("Move to subfolder"),
                                help_text=Help(
                                    "Specify the destination path in the format "
                                    "<tt>Path/To/Folder</tt>, for example "
                                    "<tt>INBOX/Processed_Mails</tt>. Note that the maximum "
                                    "depth of folder trees might be limited by your mail "
                                    "provider."
                                ),
                                custom_validate=(validators.LengthInRange(min_value=1),),
                            ),
                        ),
                    ),
                    migrate=lambda value: (
                        ("delete", "delete") if value is True else ("move", str(value))
                    ),
                ),
            ),
        },
    )


rule_spec_mail = ActiveCheck(
    title=Title("Check email"),
    topic=Topic.APPLICATIONS,
    name="mail",
    parameter_form=_valuespec_active_checks_mail,
)
