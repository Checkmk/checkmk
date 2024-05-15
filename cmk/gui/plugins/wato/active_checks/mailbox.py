#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable, Mapping

from cmk.utils.rulesets.definition import RuleGroup
from cmk.utils.version import edition, Edition

from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.mkeventd import syslog_facilities
from cmk.gui.valuespec import (
    Age,
    Alternative,
    CascadingDropdown,
    Checkbox,
    Dictionary,
    DictionaryEntry,
    DropdownChoice,
    EmailAddress,
    FixedValue,
    HostAddress,
    Integer,
    ListOfStrings,
    NetworkPort,
    RegExp,
    TextInput,
    Transform,
    Tuple,
)
from cmk.gui.wato import MigrateToIndividualOrStoredPassword, RulespecGroupActiveChecks
from cmk.gui.watolib.rulespecs import HostRulespec, rulespec_registry


# Note: already migrated as `cmk.plugins.email.rulesets.options.smtp`
def _smtp_email_parameters() -> Dictionary:
    return Dictionary(
        title="SMTP",
        optional_keys=["server", "auth"],
        elements=[
            (
                "server",
                TextInput(
                    title=_("SMTP server"),
                    allow_empty=False,
                    help=_(
                        "You can specify a host name or IP address different from the IP address "
                        "of the host this check will be assigned to."
                    ),
                ),
            ),
            (
                "connection",
                Dictionary(
                    required_keys=[],
                    title=_("Connection settings"),
                    elements=[
                        (
                            "tls",
                            FixedValue(
                                value=True,
                                title=_("Use TLS over SMTP"),
                                totext=_("Encrypt SMTP communication using TLS"),
                            ),
                        ),
                        (
                            "port",
                            NetworkPort(
                                title=_("SMTP TCP Port to connect to"),
                                help=_(
                                    "The TCP Port the SMTP server is listening on. Defaulting to <tt>25</tt>."
                                ),
                                default_value=25,
                            ),
                        ),
                    ],
                ),
            ),
            (
                "auth",
                Tuple(
                    title=_("SMTP Authentication"),
                    elements=[
                        TextInput(title=_("Username"), allow_empty=False, size=24),
                        MigrateToIndividualOrStoredPassword(
                            title=_("Password"), allow_empty=False, size=12
                        ),
                    ],
                ),
            ),
        ],
    )


# Note: already migrated as `cmk.plugins.email.rulesets.options.common`
def _common_email_parameters(protocol: str, port_defaults: str) -> Dictionary:
    credentials_basic: tuple[str, str, Tuple] = (
        "basic",
        _("Username/Password"),
        Tuple(
            title=_("Authentication"),
            elements=[
                TextInput(title=_("Username"), allow_empty=False),
                MigrateToIndividualOrStoredPassword(
                    title=_("Password"), allow_empty=False, size=12
                ),
            ],
        ),
    )
    credentials_oauth2: tuple[str, str, Tuple] = (
        "oauth2",
        _("OAuth2 (ClientID/TenantID)"),
        Tuple(
            title=_("Authentication"),
            elements=[
                TextInput(title=_("ClientID"), allow_empty=False),
                MigrateToIndividualOrStoredPassword(
                    title=_("Client Secret"), allow_empty=False, size=12
                ),
                TextInput(title=_("TenantID"), allow_empty=False),
            ],
        ),
    )

    return Dictionary(
        title=protocol,
        optional_keys=["server", "email_address"],
        elements=[
            (
                "server",
                Alternative(
                    title=f"{protocol} server",
                    elements=[
                        TextInput(
                            title=("Unvalidated string (for use with makros)"),
                            help=_(
                                "Use a makro as (part of) server name. "
                                "Macros must be in capital letters and start and end with '$'."
                            ),
                        ),
                        HostAddress(
                            title=f"{protocol} server",
                            allow_empty=False,
                            help=_(
                                "You can specify a host name or IP address different from the IP "
                                "address of the host this check will be assigned to."
                            ),
                        ),
                    ],
                ),
            ),
            (
                "connection",
                Dictionary(
                    required_keys=[],
                    title=_("Connection settings"),
                    elements=[
                        (
                            "disable_tls",
                            Checkbox(
                                title=_("Disable TLS/SSL"),
                                label=_("Force unencrypted communication"),
                            ),
                        ),
                        (
                            "disable_cert_validation",
                            Checkbox(
                                title=_("Disable certificate validation"),
                                label=_("Ignore unsuccessful validation (in case of TLS/SSL)"),
                            ),
                        ),
                        (
                            "port",
                            NetworkPort(
                                title=_("TCP Port"),
                                label=_("(default is %r for %s/TLS)") % (port_defaults, protocol),
                            ),
                        ),
                    ],
                ),
            ),
            (
                "auth",
                CascadingDropdown(
                    title=_("Authentication types"),
                    choices=[credentials_basic]
                    + ([credentials_oauth2] if protocol == "EWS" else []),
                ),
            ),
        ]
        + (
            [
                (
                    "email_address",
                    EmailAddress(
                        title=_("Email address used for account identification"),
                        label=_("(overrides <b>username</b>)"),
                        help=_(
                            "Used to specify the account to be contacted"
                            " (aka. 'PrimarySmtpAddress') in case it's different from the"
                            " username. If not specified the credentials username is used."
                        ),
                        allow_empty=False,
                    ),
                )
            ]
            if protocol == "EWS"
            else []
        ),
        validate=validate_common_email_parameters,
    )


def validate_common_email_parameters(params: Mapping[str, tuple], varprefix: str) -> None:
    if params["auth"][0] == "oauth2" and "email_address" not in params:
        raise MKUserError(
            varprefix,
            "With authentication type set to 'OAuth2' an 'Email address used for"
            " account identification' must be specified.",
        )


# Note: already migrated as `cmk.plugins.email.rulesets.options.sending`
def _mail_sending_params() -> DictionaryEntry:
    return (
        "send",
        CascadingDropdown(
            title=_("Mail sending"),
            choices=[
                ("SMTP", _("SMTP"), _smtp_email_parameters()),
                ("EWS", _("EWS"), _common_email_parameters("EWS", "80/443")),
            ],
        ),
    )


# Note: already migrated as `cmk.plugins.email.rulesets.options.receiving`
def _mail_receiving_params(supported_protocols: Iterable[str]) -> DictionaryEntry:
    return (
        "fetch",
        CascadingDropdown(
            title=_("Mail receiving"),
            choices=[
                e
                for e in [
                    ("IMAP", _("IMAP"), _common_email_parameters("IMAP", "143/993")),
                    ("POP3", _("POP3"), _common_email_parameters("POP3", "110/995")),
                    ("EWS", _("EWS"), _common_email_parameters("EWS", "80/443")),
                ]
                if e[0] in supported_protocols
            ],
        ),
    )


def _valuespec_active_checks_mail_loop() -> Dictionary:
    return Dictionary(
        title=_("Check Email Delivery"),
        help=_(
            "This active check sends out special emails to a defined mail address using either "
            "the SMTP protocol or an EWS connection and then tries to receive these mails back "
            "by querying the inbox of an IMAP, POP3 or EWS mailbox. With this check you can "
            "verify that your whole mail delivery progress is working."
        ),
        optional_keys=[
            "subject",
            "connect_timeout",
            "delete_messages",
            "duration",
        ],
        elements=[
            (
                "item",
                TextInput(
                    title=_("Name"),
                    help=_("The service name will be <b>Mail Loop</b> plus this name"),
                    allow_empty=False,
                ),
            ),
            (
                "subject",
                TextInput(
                    title=_("Subject"),
                    allow_empty=False,
                    help=_(
                        "Here you can specify the subject text "
                        "instead of default text 'Check_MK-Mail-Loop'."
                    ),
                ),
            ),
            _mail_sending_params(),
            _mail_receiving_params({"IMAP", "POP3", "EWS"}),
            (
                "mail_from",
                EmailAddress(
                    title=_("From: email address"),
                ),
            ),
            (
                "mail_to",
                EmailAddress(
                    title=_("Destination email address"),
                ),
            ),
            (
                "connect_timeout",
                Integer(
                    title=_("Connect Timeout"),
                    minvalue=1,
                    default_value=10,
                    unit=_("sec"),
                ),
            ),
            (
                "duration",
                Tuple(
                    title=_("Loop duration"),
                    elements=[
                        Age(title=_("Warning at")),
                        Age(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "delete_messages",
                FixedValue(
                    value=True,
                    title=_("Delete processed messages"),
                    totext=_("Delete all processed message belonging to this check"),
                    help=_(
                        "Delete all messages identified as being related to this "
                        "check. This is disabled by default, which will make "
                        "your mailbox grow when you do not clean it up on your own."
                    ),
                ),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupActiveChecks,
        match_type="all",
        name=RuleGroup.ActiveChecks("mail_loop"),
        valuespec=_valuespec_active_checks_mail_loop,
    )
)


def _valuespec_active_checks_mail() -> Dictionary:
    return Dictionary(
        title=_("Check Email"),
        help=_(
            "The basic function of this check is to log in into an IMAP, POP3 or EWS mailbox "
            "to monitor whether or not the login is possible. An extended feature is, that the "
            "check can fetch all (or just some) from the mailbox and forward them as events "
            "to the Event Console."
        ),
        required_keys=["service_description", "fetch"],
        elements=[
            (
                "service_description",
                TextInput(
                    title=_("Service name"),
                    help=_(
                        "Please make sure that this is unique per host "
                        "and does not collide with other services."
                    ),
                    allow_empty=False,
                    default_value="Email",
                ),
            ),
            _mail_receiving_params({"IMAP", "POP3", "EWS"}),
            (
                "connect_timeout",
                Integer(
                    title=_("Connect Timeout"),
                    minvalue=1,
                    default_value=10,
                    unit=_("sec"),
                ),
            ),
        ]
        + _forward_to_ec_elements(),
    )


def _forward_to_ec_elements() -> list[DictionaryEntry]:
    if edition() is Edition.CSE:  # disabled in CSE
        return []
    return [
        (
            "forward",
            Dictionary(
                title=_("Forward mails as events to Event Console"),
                elements=[
                    (
                        "method",
                        Alternative(
                            title=_("Forwarding Method"),
                            elements=[
                                Alternative(
                                    title=_("Send events to local event console"),
                                    elements=[
                                        FixedValue(
                                            value="",
                                            totext=_("Directly forward to event console"),
                                            title=_(
                                                "Send events to local event console in same OMD site"
                                            ),
                                        ),
                                        TextInput(
                                            title=_(
                                                "Send events to local event console into unix socket"
                                            ),
                                            allow_empty=False,
                                        ),
                                        FixedValue(
                                            value="spool:",
                                            totext=_("Spool to event console"),
                                            title=_(
                                                "Spooling: Send events to local event console in same OMD site"
                                            ),
                                        ),
                                        Transform(
                                            valuespec=TextInput(
                                                allow_empty=False,
                                            ),
                                            title=_(
                                                "Spooling: Send events to local event console into given spool directory"
                                            ),
                                            # remove prefix
                                            to_valuespec=lambda x: x[6:],
                                            from_valuespec=lambda x: "spool:" + x,  # add prefix
                                        ),
                                    ],
                                    match=lambda x: x
                                    and (x == "spool:" and 2 or x.startswith("spool:") and 3 or 1)
                                    or 0,
                                ),
                                Tuple(
                                    title=_("Send events to remote syslog host"),
                                    elements=[
                                        DropdownChoice(
                                            choices=[
                                                ("udp", _("UDP")),
                                                ("tcp", _("TCP")),
                                            ],
                                            title=_("Protocol"),
                                        ),
                                        TextInput(
                                            title=_("Address"),
                                            allow_empty=False,
                                        ),
                                        NetworkPort(
                                            title=_("Port"),
                                            default_value=514,
                                            minvalue=1,
                                            maxvalue=65535,
                                            size=6,
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ),
                    (
                        "match_subject",
                        RegExp(
                            title=_("Only process mails with matching subject"),
                            help=_(
                                "Use this option to not process all messages found in the inbox, "
                                "but only the those whose subject matches the given regular expression."
                            ),
                            mode=RegExp.prefix,
                        ),
                    ),
                    (
                        "facility",
                        DropdownChoice(
                            title=_("Events: Syslog facility"),
                            help=_("Use this syslog facility for all created events"),
                            choices=syslog_facilities,
                            default_value=2,  # mail
                        ),
                    ),
                    (
                        "application",
                        Alternative(
                            title=_("Events: Syslog application"),
                            help=_("Use this syslog application for all created events"),
                            elements=[
                                FixedValue(
                                    value=None,
                                    title=_("Use the mail subject"),
                                    totext=_("The mail subject is used as syslog appliaction"),
                                ),
                                TextInput(
                                    title=_("Specify the application"),
                                    help=_(
                                        "Use this text as application. You can use macros like <tt>\\1</tt>, <tt>\\2</tt>, ... "
                                        "here when you configured <i>subject matching</i> in this rule with a regular expression "
                                        "that declares match groups (using braces)."
                                    ),
                                    allow_empty=False,
                                ),
                            ],
                        ),
                    ),
                    (
                        "host",
                        TextInput(
                            title=_("Events: Host name"),
                            help=_(
                                "Use this host name for all created events instead of the name of the mailserver"
                            ),
                        ),
                    ),
                    (
                        "body_limit",
                        Integer(
                            title=_("Limit length of mail body"),
                            help=_(
                                "When forwarding mails from the mailbox to the event console, the "
                                "body of the mail is limited to the given number of characters."
                            ),
                            default_value=1000,
                        ),
                    ),
                    (
                        "cleanup",
                        Alternative(
                            title=_("Cleanup messages"),
                            help=_(
                                "The handled messages (see <i>subject matching</i>) can be cleaned up by either "
                                "deleting them or moving them to a subfolder. By default nothing is cleaned up."
                            ),
                            elements=[
                                FixedValue(
                                    value=True,
                                    title=_("Delete messages"),
                                    totext=_(
                                        "Delete all processed message belonging to this check"
                                    ),
                                ),
                                TextInput(
                                    title=_("Move to subfolder"),
                                    help=_(
                                        "Specify the destination path in the format "
                                        "<tt>Path/To/Folder</tt>, for example "
                                        "<tt>INBOX/Processed_Mails</tt>. Note that the maximum "
                                        "depth of folder trees might be limited by your mail "
                                        "provider."
                                    ),
                                    allow_empty=False,
                                ),
                            ],
                        ),
                    ),
                ],
            ),
        ),
    ]


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupActiveChecks,
        match_type="all",
        name=RuleGroup.ActiveChecks("mail"),
        valuespec=_valuespec_active_checks_mail,
    )
)


def _valuespec_active_checks_mailboxes() -> Dictionary:
    return Dictionary(
        title=_("Check IMAP/EWS Mailboxes"),
        help=_("This check monitors count and age of mails in mailboxes."),
        elements=[
            (
                "service_description",
                TextInput(
                    title=_("Service name"),
                    help=_(
                        "Please make sure that this is unique per host "
                        "and does not collide with other services."
                    ),
                    allow_empty=False,
                    default_value="Mailboxes",
                ),
            ),
            _mail_receiving_params({"IMAP", "EWS"}),
            (
                "connect_timeout",
                Integer(
                    title=_("Connect Timeout"),
                    minvalue=1,
                    default_value=10,
                    unit=_("sec"),
                ),
            ),
            (
                "age",
                Tuple(
                    title=_("Message Age of oldest messages"),
                    elements=[
                        Age(title=_("Warning if older than")),
                        Age(title=_("Critical if older than")),
                    ],
                ),
            ),
            (
                "age_newest",
                Tuple(
                    title=_("Message Age of newest messages"),
                    elements=[
                        Age(title=_("Warning if older than")),
                        Age(title=_("Critical if older than")),
                    ],
                ),
            ),
            (
                "count",
                Tuple(
                    title=_("Message Count"),
                    elements=[Integer(title=_("Warning at")), Integer(title=_("Critical at"))],
                ),
            ),
            (
                "mailboxes",
                ListOfStrings(
                    title=_("Check only the listed mailboxes"),
                    help=_(
                        "By default, all mailboxes are checked with these parameters. "
                        "If you specify mailboxes here, only those are monitored."
                    ),
                ),
            ),
        ],
        required_keys=["service_description", "fetch"],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupActiveChecks,
        match_type="all",
        name=RuleGroup.ActiveChecks("mailboxes"),
        valuespec=_valuespec_active_checks_mailboxes,
    )
)

if __name__ == "__main__":
    # Please keep these lines - they make TDD easy and have no effect on normal test runs.
    # Just run this file from your IDE and dive into the code.
    import doctest

    assert not doctest.testmod().failed
