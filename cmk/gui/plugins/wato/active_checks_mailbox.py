#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import cmk.gui.mkeventd as mkeventd
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.active_checks import RulespecGroupActiveChecks
from cmk.gui.plugins.wato.utils import HostRulespec, IndividualOrStoredPassword, rulespec_registry
from cmk.gui.valuespec import (
    Age,
    Alternative,
    CascadingDropdown,
    Checkbox,
    Dictionary,
    DropdownChoice,
    EmailAddress,
    FixedValue,
    HostAddress,
    Integer,
    ListOfStrings,
    Optional,
    RegExp,
    TextInput,
    Transform,
    Tuple,
)


def _imap_parameters():
    return Dictionary(
        title="IMAP",
        optional_keys=[],
        elements=[
            (
                "server",
                TextInput(
                    title=_("IMAP Server"),
                    allow_empty=False,
                    help=_(
                        "You can specify a hostname or IP address different from the IP address "
                        "of the host this check will be assigned to."
                    ),
                ),
            ),
            (
                "ssl",
                CascadingDropdown(
                    title=_("SSL Encryption"),
                    default_value=(False, 143),
                    choices=[
                        (
                            False,
                            _("Use no encryption"),
                            Optional(
                                valuespec=Integer(
                                    default_value=143,
                                ),
                                title=_("TCP Port"),
                                help=_("By default the standard IMAP Port 143 is used."),
                            ),
                        ),
                        (
                            True,
                            _("Encrypt IMAP communication using SSL"),
                            Optional(
                                valuespec=Integer(
                                    default_value=993,
                                ),
                                title=_("TCP Port"),
                                help=_("By default the standard IMAP/SSL Port 993 is used."),
                            ),
                        ),
                    ],
                ),
            ),
            (
                "auth",
                Tuple(
                    title=_("Authentication"),
                    elements=[
                        TextInput(title=_("Username"), allow_empty=False, size=24),
                        IndividualOrStoredPassword(title=_("Password"), allow_empty=False, size=12),
                    ],
                ),
            ),
        ],
    )


def _imap_parameters_check_mailboxes():
    return Dictionary(
        title="IMAP",
        optional_keys=[],
        elements=[
            (
                "server",
                TextInput(
                    title=_("IMAP Server"),
                    allow_empty=False,
                    help=_(
                        "You can specify a hostname or IP address different from the IP address "
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
                            "tcp_port",
                            Integer(
                                title=_("TCP Port"),
                                label=_("(default is 143/993 for IMAP/SSL)"),
                            ),
                        ),
                    ],
                ),
            ),
            (
                "auth",
                Tuple(
                    title=_("Authentication"),
                    elements=[
                        TextInput(title=_("Username"), allow_empty=False, size=24),
                        IndividualOrStoredPassword(title=_("Password"), allow_empty=False, size=12),
                    ],
                ),
            ),
        ],
    )


def _pop3_parameters():
    return Dictionary(
        optional_keys=["server"],
        elements=[
            (
                "server",
                TextInput(
                    title=_("POP3 Server"),
                    allow_empty=False,
                    help=_(
                        "You can specify a hostname or IP address different from the IP address "
                        "of the host this check will be assigned to."
                    ),
                ),
            ),
            (
                "ssl",
                CascadingDropdown(
                    title=_("SSL Encryption"),
                    default_value=(False, 110),
                    choices=[
                        (
                            False,
                            _("Use no encryption"),
                            Optional(
                                valuespec=Integer(
                                    default_value=110,
                                ),
                                title=_("TCP Port"),
                                help=_("By default the standard POP3 Port 110 is used."),
                            ),
                        ),
                        (
                            True,
                            _("Encrypt POP3 communication using SSL"),
                            Optional(
                                valuespec=Integer(
                                    default_value=995,
                                ),
                                title=_("TCP Port"),
                                help=_("By default the standard POP3/SSL Port 995 is used."),
                            ),
                        ),
                    ],
                ),
            ),
            (
                "auth",
                Tuple(
                    title=_("Authentication"),
                    elements=[
                        TextInput(title=_("Username"), allow_empty=False, size=24),
                        IndividualOrStoredPassword(title=_("Password"), allow_empty=False, size=12),
                    ],
                ),
            ),
        ],
    )


def _ews_parameters():
    return Dictionary(
        title="Exchange Web Services - EWS",
        optional_keys=[],
        elements=[
            (
                "server",
                HostAddress(
                    title=_("EWS Serverr"),
                    allow_empty=False,
                    help=_(
                        "You can specify a hostname or IP address different from the IP address "
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
                            "tcp_port",
                            Integer(
                                title=_("TCP Port"),
                                label=_("(default is 80/443 for HTTP(S))"),
                            ),
                        ),
                    ],
                ),
            ),
            (
                "auth",
                Tuple(
                    title=_("Authentication"),
                    elements=[
                        TextInput(title=_("Username"), allow_empty=False, size=24),
                        IndividualOrStoredPassword(title=_("Password"), allow_empty=False, size=12),
                    ],
                ),
            ),
        ],
    )


def _mail_receiving_params():
    return [
        (
            "fetch",
            CascadingDropdown(
                title=_("Mail Receiving"),
                choices=[
                    ("IMAP", _("IMAP"), _imap_parameters()),
                    ("POP3", _("POP3"), _pop3_parameters()),
                ],
            ),
        ),
    ]


def _valuespec_active_checks_mail_loop():
    return Dictionary(
        title=_("Check Email Delivery"),
        help=_(
            "This active check sends out special E-Mails to a defined mail address using "
            "the SMTP protocol and then tries to receive these mails back by querying the "
            "inbox of a IMAP or POP3 mailbox. With this check you can verify that your whole "
            "mail delivery progress is working."
        ),
        optional_keys=[
            "subject",
            "smtp_server",
            "smtp_tls",
            "smtp_port",
            "smtp_auth",
            "imap_tls",
            "connect_timeout",
            "delete_messages",
            "duration",
        ],
        elements=[
            (
                "item",
                TextInput(
                    title=_("Name"),
                    help=_("The service description will be <b>Mail Loop</b> plus this name"),
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
            (
                "smtp_server",
                TextInput(
                    title=_("SMTP Server"),
                    allow_empty=False,
                    help=_(
                        "You can specify a hostname or IP address different from the IP address "
                        "of the host this check will be assigned to."
                    ),
                ),
            ),
            (
                "smtp_tls",
                FixedValue(
                    value=True,
                    title=_("Use TLS over SMTP"),
                    totext=_("Encrypt SMTP communication using TLS"),
                ),
            ),
            (
                "imap_tls",
                FixedValue(
                    value=True,
                    title=_("Use TLS for IMAP authentification"),
                    totext=_("IMAP authentification uses TLS"),
                ),
            ),
            (
                "smtp_port",
                Integer(
                    title=_("SMTP TCP Port to connect to"),
                    help=_(
                        "The TCP Port the SMTP server is listening on. Defaulting to <tt>25</tt>."
                    ),
                    default_value=25,
                ),
            ),
            (
                "smtp_auth",
                Tuple(
                    title=_("SMTP Authentication"),
                    elements=[
                        TextInput(title=_("Username"), allow_empty=False, size=24),
                        IndividualOrStoredPassword(title=_("Password"), allow_empty=False, size=12),
                    ],
                ),
            ),
        ]
        + _mail_receiving_params()
        + [
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
                        "your mailbox grow when you not clean it up on your own."
                    ),
                ),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupActiveChecks,
        match_type="all",
        name="active_checks:mail_loop",
        valuespec=_valuespec_active_checks_mail_loop,
    )
)


def _valuespec_active_checks_mail():
    return Dictionary(
        title=_("Check Email"),
        help=_(
            "The basic function of this check is to log in into an IMAP or POP3 mailbox to "
            "monitor whether or not the login is possible. A extended feature is, that the "
            "check can fetch all (or just some) from the mailbox and forward them as events "
            "to the Event Console."
        ),
        required_keys=["service_description", "fetch"],
        elements=[
            (
                "service_description",
                TextInput(
                    title=_("Service description"),
                    help=_(
                        "Please make sure that this is unique per host "
                        "and does not collide with other services."
                    ),
                    allow_empty=False,
                    default_value="Email",
                ),
            )
        ]
        + _mail_receiving_params()
        + [
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
                                                forth=lambda x: x[6:],
                                                back=lambda x: "spool:" + x,  # add prefix
                                            ),
                                        ],
                                        match=lambda x: x
                                        and (
                                            x == "spool:" and 2 or x.startswith("spool:") and 3 or 1
                                        )
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
                                            Integer(
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
                                choices=mkeventd.syslog_facilities,
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
                                title=_("Events: Hostname"),
                                help=_(
                                    "Use this hostname for all created events instead of the name of the mailserver"
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
                                            "Specify the destination path in the format <tt>Path/To/Folder</tt>, for example"
                                            "<tt>INBOX/Processed_Mails</tt>."
                                        ),
                                        allow_empty=False,
                                    ),
                                ],
                            ),
                        ),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupActiveChecks,
        match_type="all",
        name="active_checks:mail",
        valuespec=_valuespec_active_checks_mail,
    )
)


def transform_check_mailbox_params(params):
    """Transforms rule sets from 2.0 and below format to current (2.1 and up)
    >>> for k, v in sorted(transform_check_mailbox_params({  # v2.0.0 / IMAP
    ...     'service_description': 'SD',
    ...     'imap_parameters': {
    ...       'server': 'srv', 'ssl': (True, 7), 'auth': ('usr', ('password', 'pw'))},
    ...     'age': (1, 2), 'age_newest': (3, 4), 'count': (5, 6),
    ...     'mailboxes': ['abc', 'def']}).items()):
    ...   print(f"{k}: {v}")
    age: (1, 2)
    age_newest: (3, 4)
    count: (5, 6)
    fetch: ('IMAP', {'server': 'srv', 'connection': {'disable_tls': False, 'tcp_port': 7}, 'auth': ('usr', ('password', 'pw'))})
    mailboxes: ['abc', 'def']
    service_description: SD
    >>> for k, v in sorted(transform_check_mailbox_params({  # v2.1.0b / IMAP
    ...     'service_description': 'SD',
    ...     'fetch': ('IMAP', {
    ...       'server': 'srv', 'ssl': (True, None), 'auth': ('usr', ('password', 'pw'))}),
    ...     'age': (1, 2), 'age_newest': (3, 4), 'count': (5, 6),
    ...     'mailboxes': ['abc', 'def']}).items()):
    ...   print(f"{k}: {v}")
    age: (1, 2)
    age_newest: (3, 4)
    count: (5, 6)
    fetch: ('IMAP', {'server': 'srv', 'connection': {'disable_tls': False}, 'auth': ('usr', ('password', 'pw'))})
    mailboxes: ['abc', 'def']
    service_description: SD
    >>> for k, v in sorted(transform_check_mailbox_params({  # v2.1.0 / EWS
    ...     'service_description': 'SD',
    ...     'fetch': ('EWS', {
    ...       'server': 'srv', 'connection': {},
    ...       'auth': ('usr', ('password', 'pw')),
    ...       'connection': {'disable_tls': False, 'disable_cert_validation': False, 'tcp_port': 123}}),
    ...     'age': (1, 2), 'age_newest': (3, 4), 'count': (5, 6),
    ...     'mailboxes': ['abc', 'def']}).items()):
    ...   print(f"{k}: {v}")
    age: (1, 2)
    age_newest: (3, 4)
    count: (5, 6)
    fetch: ('EWS', {'server': 'srv', 'connection': {'disable_tls': False, 'disable_cert_validation': False, 'tcp_port': 123}, 'auth': ('usr', ('password', 'pw'))})
    mailboxes: ['abc', 'def']
    service_description: SD
    """

    def apply_fetch(params, fetch_param):
        return {
            **{"fetch": fetch_param},
            **{
                k: v
                for k, v in params.items()
                if k in {"service_description", "age", "age_newest", "count", "mailboxes"}
            },
        }

    def update_fetch(old_fetch):
        return {
            "server": old_fetch["server"],
            "connection": {
                k: (not v) if isinstance(v, bool) else v
                for k, v in zip(("disable_tls", "tcp_port"), fetch_params["ssl"])
                if v is not None
            },
            "auth": old_fetch["auth"],
        }

    if not params.keys() <= {
        "imap_parameters",
        "fetch",
        "service_description",
        "age",
        "age_newest",
        "count",
        "mailboxes",
    }:
        raise ValueError(f"{params.keys()}")

    if "fetch" in params:
        fetch_protocol, fetch_params = params["fetch"]
        if fetch_protocol in {"IMAP", "EWS"} and {"connection", "auth"} <= fetch_params.keys():
            # newest schema (2.1 and up) - do nothing
            return params
        if fetch_protocol in {"IMAP"} and {"server", "ssl", "auth"} <= fetch_params.keys():
            # temporary 2.1.0b format - just update the connection element
            return apply_fetch(params, ("IMAP", update_fetch(fetch_params)))

    if "imap_parameters" in params:
        # v2.0.0 and below
        fetch_params = params["imap_parameters"]
        return apply_fetch(params, ("IMAP", update_fetch(fetch_params)))

    # no known format recognized
    raise ValueError(f"Cannot transform {params}")


def _valuespec_active_checks_mailboxes():
    return Transform(
        valuespec=Dictionary(
            title=_("Check IMAP/EWS Mailboxes"),
            help=_("This check monitors count and age of mails in mailboxes."),
            elements=[
                (
                    "service_description",
                    TextInput(
                        title=_("Service description"),
                        help=_(
                            "Please make sure that this is unique per host "
                            "and does not collide with other services."
                        ),
                        allow_empty=False,
                        default_value="Mailboxes",
                    ),
                ),
                (
                    "fetch",
                    CascadingDropdown(
                        title=_("Mail Receiving"),
                        choices=[
                            ("IMAP", _("IMAP"), _imap_parameters_check_mailboxes()),
                            ("EWS", _("EWS"), _ews_parameters()),
                        ],
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
        ),
        forth=transform_check_mailbox_params,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupActiveChecks,
        match_type="all",
        name="active_checks:mailboxes",
        valuespec=_valuespec_active_checks_mailboxes,
    )
)
