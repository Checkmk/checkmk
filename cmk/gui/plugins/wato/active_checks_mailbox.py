#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable, Mapping

import cmk.gui.mkeventd as mkeventd
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.active_checks import RulespecGroupActiveChecks
from cmk.gui.plugins.wato.utils import HostRulespec, IndividualOrStoredPassword, rulespec_registry
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
    RegExp,
    TextInput,
    Transform,
    Tuple,
)


def _common_email_parameters(protocol: str, port_defaults: str) -> Dictionary:
    credentials_basic: tuple[str, str, Tuple] = (
        "basic",
        _("Username/Password"),
        Tuple(
            title=_("Authentication"),
            elements=[
                TextInput(title=_("Username"), allow_empty=False),
                IndividualOrStoredPassword(title=_("Password"), allow_empty=False, size=12),
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
                IndividualOrStoredPassword(title=_("Client Secret"), allow_empty=False, size=12),
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
                    title=f"{protocol} Server",
                    elements=[
                        FixedValue(
                            value="$HOSTADDRESS$",
                            title=_(
                                "Use the address of the host for which the service is generated"
                            ),
                            totext="",
                        ),
                        FixedValue(
                            value="$HOSTNAME$",
                            title=_("Use the name of the host for which the service is generated"),
                            totext="",
                        ),
                        HostAddress(
                            title=f"{protocol} Server",
                            allow_empty=False,
                            help=_(
                                "You can specify a hostname or IP address different from the IP "
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
                            "tcp_port",
                            Integer(
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
        ),  # type: ignore[arg-type]
        validate=validate_common_email_parameters,
    )


def validate_common_email_parameters(params: Mapping[str, tuple], varprefix: str) -> None:
    if params["auth"][0] == "oauth2" and "email_address" not in params:
        raise MKUserError(
            varprefix,
            "With authentication type set to 'OAuth2' an 'Email address used for"
            " account identification' must be specified.",
        )


def _mail_receiving_params(supported_protocols: Iterable[str]) -> DictionaryEntry:
    return (
        "fetch",
        CascadingDropdown(
            title=_("Mail Receiving"),
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


def apply_fetch(params, fetch_param, allowed_keys):
    """Create a new set of params by taking all allowed elements from old dataset
    adding a new 'fetch' element"""
    return {
        **{k: v for k, v in params.items() if k in allowed_keys - {"fetch"}},
        **{"fetch": fetch_param},
    }


def is_typed_auth(auth: tuple[str, tuple]) -> bool:
    """New `auth` elements contain a type ('basic' or 'oauth2') as first element
    and a 2/3 tuple as second element containing the actual auth data, e.g.
    `(<type>:str, (<username>:str, (<pw-type>:str, <pw-or-id>:str)))`
     while older variants only consisted of
    a 2-tuple `(<username>:str, (<pw-type>:str, <pw-or-id>:str))`
    So checking the type of the second elment of the second element to be a
    tuple tells us if the given @auth is new.
    """
    return isinstance(auth[1][1], tuple)


def update_auth(auth: tuple[str, tuple]) -> tuple[str, tuple[str, ...]]:
    """Older `auth` element had been `basic` only, so we just have to wrap it
    if it's not typed yet"""
    return auth if is_typed_auth(auth) else ("basic", auth)


def update_fetch(old_fetch):
    """Create a new 'fetch' element out of an old one.
    Older `fetch` structures might have contained an `ssl` element with a tuple
    (use_ssl: optional[bool], tcp_port: optional[str]), which is being semantially
    inverted and merged into the new `connection` elment:
    "connection": {
        "disable_tls": not <prior-value>  # only if prior-value was not None
        "tcp_port": <prior-value>  # only if prior-value was not None
    }
    The `auth` element had been a tuple `(<username>, (<pw-type>, <pw-or-id>))`
    and contains a type now, which is being inserted by `update_auth()`
    """
    return {
        "server": old_fetch.get("server"),
        "connection": {
            **{
                k: (not v) if isinstance(v, bool) else v
                for k, v in zip(("disable_tls", "tcp_port"), old_fetch.get("ssl", (None, None)))
                if v is not None
            },
            **old_fetch.get("connection", {}),
        },
        "auth": update_auth(old_fetch["auth"]),
    }


def transform_check_mail_loop_params(params):
    """Transforms rule sets from 2.0 and below format to current (2.1 and up)"""
    allowed_keys = {
        "item",  # instead of "service_description"
        "fetch",  # can be asserted - since v2.0.0
        "connect_timeout",
        "subject",
        "smtp_server",
        "smtp_tls",
        "smtp_port",
        "smtp_auth",
        "mail_from",
        "mail_to",
        "duration",
        "delete_messages",
    }
    fetch_protocol, fetch_params = params["fetch"]

    # since v2.0.0 `fetch_protocol` is one of {"IMAP", "POP3"}
    # - but cannot be "EWS" for check_mail_loop yet

    # `connection` is part of `fetch_params` since v2.1.0
    if "connection" in fetch_params:
        if not is_typed_auth(fetch_params["auth"]):
            # Up to 2.1.0p24 we only had the basic auth tuple
            return {
                **params,
                "fetch": (fetch_protocol, update_fetch(fetch_params)),
            }
        # newest schema (2.1 and up) - return the unmodified argument
        return params

    # old format (2.0 and below)
    if params.get("imap_tls"):
        fetch_params["ssl"] = (True, fetch_params["ssl"][1])
    return apply_fetch(
        params,
        (fetch_protocol, update_fetch(fetch_params)),
        allowed_keys,
    )


def _valuespec_active_checks_mail_loop():
    return Transform(
        Dictionary(
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
                            IndividualOrStoredPassword(
                                title=_("Password"), allow_empty=False, size=12
                            ),
                        ],
                    ),
                ),
                _mail_receiving_params({"IMAP", "POP3"}),
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
        ),
        forth=transform_check_mail_loop_params,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupActiveChecks,
        match_type="all",
        name="active_checks:mail_loop",
        valuespec=_valuespec_active_checks_mail_loop,
    )
)


def transform_check_mail_params(params):
    """Transforms rule sets from 2.0 and below format to current (2.1 and up)
    >>> transformed = transform_check_mail_params({  # v2.0.0 / IMAP
    ...     'service_description': 'SD',
    ...     'fetch': ('IMAP', {
    ...       'server': 'srv',
    ...       'ssl': (False, 143),
    ...       'auth': ('usr', ('password', 'pw')),
    ...     }),
    ...     'connect_timeout': 12,
    ...     'forward': {'match_subject': 'test'},
    ... })
    >>> assert transform_check_mail_params(transformed) == transformed
    >>> import yaml; print(yaml.dump(transformed).strip())
    connect_timeout: 12
    fetch: !!python/tuple
    - IMAP
    - auth: !!python/tuple
      - basic
      - !!python/tuple
        - usr
        - !!python/tuple
          - password
          - pw
      connection:
        disable_tls: true
        tcp_port: 143
      server: srv
    forward:
      match_subject: test
    service_description: SD
    >>> transformed = transform_check_mail_params({  # v2.0.0 / POP3
    ...     'service_description': 'SD',
    ...     'fetch': ('POP3', {
    ...       'server': 'srv',
    ...       'ssl': (False, 110),
    ...       'auth': ('usr', ('password', 'pw')),
    ...     }),
    ...     'connect_timeout': 12,
    ...     'forward': {'match_subject': 'test'},
    ... })
    >>> assert transform_check_mail_params(transformed) == transformed
    >>> import yaml; print(yaml.dump(transformed).strip())
    connect_timeout: 12
    fetch: !!python/tuple
    - POP3
    - auth: !!python/tuple
      - basic
      - !!python/tuple
        - usr
        - !!python/tuple
          - password
          - pw
      connection:
        disable_tls: true
        tcp_port: 110
      server: srv
    forward:
      match_subject: test
    service_description: SD
    """

    if not params.keys() <= {
        "service_description",
        "fetch",
        "connect_timeout",
        "forward",
    }:
        raise ValueError(f"{params.keys()}")

    fetch_protocol, fetch_params = params["fetch"]

    # since v2.0.0 `fetch_protocol` is one of {"IMAP", "POP3"}
    # - but cannot be "EWS" for check_mail yet

    if "connection" in fetch_params:
        if not is_typed_auth(fetch_params["auth"]):
            # Up to 2.1.0p24 we only had the basic auth tuple
            return {
                **params,
                "fetch": (fetch_protocol, update_fetch(fetch_params)),
            }
        # newest schema (2.1 and up) - do nothing
        return params

    if {"ssl", "auth"} <= fetch_params.keys():
        # old format (2.0 and below)
        return apply_fetch(
            params,
            (fetch_protocol, update_fetch(fetch_params)),
            {"service_description", "forward", "connect_timeout"},
        )

    raise ValueError(f"Cannot transform {params}")


def _valuespec_active_checks_mail():
    return Transform(
        Dictionary(
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
                        title=_("Service name"),
                        help=_(
                            "Please make sure that this is unique per host "
                            "and does not collide with other services."
                        ),
                        allow_empty=False,
                        default_value="Email",
                    ),
                ),
                _mail_receiving_params({"IMAP", "POP3"}),
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
                                                x == "spool:"
                                                and 2
                                                or x.startswith("spool:")
                                                and 3
                                                or 1
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
                                            totext=_(
                                                "The mail subject is used as syslog appliaction"
                                            ),
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
        ),
        forth=transform_check_mail_params,
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
    >>> transformed = transform_check_mailbox_params({  # v2.0.0 / IMAP
    ...     'service_description': 'SD',
    ...     'imap_parameters': {
    ...       'server': 'srv', 'ssl': (True, 7), 'auth': ('usr', ('password', 'pw'))},
    ...     'age': (1, 2), 'age_newest': (3, 4), 'count': (5, 6),
    ...     'mailboxes': ['abc', 'def'],
    ... })
    >>> assert transform_check_mailbox_params(transformed) == transformed
    >>> import yaml; print(yaml.dump(transformed).strip())
    age: !!python/tuple
    - 1
    - 2
    age_newest: !!python/tuple
    - 3
    - 4
    count: !!python/tuple
    - 5
    - 6
    fetch: !!python/tuple
    - IMAP
    - auth: !!python/tuple
      - basic
      - !!python/tuple
        - usr
        - !!python/tuple
          - password
          - pw
      connection:
        disable_tls: false
        tcp_port: 7
      server: srv
    mailboxes:
    - abc
    - def
    service_description: SD
    >>> transformed = transform_check_mailbox_params({  # v2.1.0b / IMAP
    ...     'service_description': 'SD',
    ...     'fetch': ('IMAP', {
    ...       'server': 'srv', 'ssl': (True, None), 'auth': ('usr', ('password', 'pw'))}),
    ...     'age': (1, 2), 'age_newest': (3, 4), 'count': (5, 6),
    ...     'mailboxes': ['abc', 'def'],
    ...     'connect_timeout': 12,
    ... })
    >>> assert transform_check_mailbox_params(transformed) == transformed
    >>> import yaml; print(yaml.dump(transformed).strip())
    age: !!python/tuple
    - 1
    - 2
    age_newest: !!python/tuple
    - 3
    - 4
    connect_timeout: 12
    count: !!python/tuple
    - 5
    - 6
    fetch: !!python/tuple
    - IMAP
    - auth: !!python/tuple
      - basic
      - !!python/tuple
        - usr
        - !!python/tuple
          - password
          - pw
      connection:
        disable_tls: false
      server: srv
    mailboxes:
    - abc
    - def
    service_description: SD
    >>> transformed = transform_check_mailbox_params({  # v2.1.0 / EWS
    ...     'service_description': 'SD',
    ...     'fetch': ('EWS', {
    ...       'server': 'srv', 'connection': {},
    ...       'auth': ('usr', ('password', 'pw')),
    ...       'connection': {'disable_tls': False, 'disable_cert_validation': False, 'tcp_port': 123}}),
    ...     'age': (1, 2), 'age_newest': (3, 4), 'count': (5, 6),
    ...     'mailboxes': ['abc', 'def'],
    ... })
    >>> assert transform_check_mailbox_params(transformed) == transformed
    >>> import yaml; print(yaml.dump(transformed).strip())
    age: !!python/tuple
    - 1
    - 2
    age_newest: !!python/tuple
    - 3
    - 4
    count: !!python/tuple
    - 5
    - 6
    fetch: !!python/tuple
    - EWS
    - auth: !!python/tuple
      - basic
      - !!python/tuple
        - usr
        - !!python/tuple
          - password
          - pw
      connection:
        disable_cert_validation: false
        disable_tls: false
        tcp_port: 123
      server: srv
    mailboxes:
    - abc
    - def
    service_description: SD
    """
    allowed_keys = {
        "service_description",
        "age",
        "age_newest",
        "count",
        "mailboxes",
        "connect_timeout",
    }
    if not params.keys() <= allowed_keys | {"imap_parameters", "fetch"}:
        raise ValueError(f"{params.keys()}")

    if "fetch" in params:
        fetch_protocol, fetch_params = params["fetch"]
        if fetch_protocol in {"IMAP", "EWS"} and {"connection", "auth"} <= fetch_params.keys():
            if is_typed_auth(fetch_params["auth"]):
                # newest schema (2.1 and up) - do nothing
                return params
            # Up to 2.1.0p24 we only had the basic auth tuple
            return {
                **params,
                "fetch": (fetch_protocol, update_fetch(fetch_params)),
            }
        if fetch_protocol in {"IMAP"} and {"server", "ssl", "auth"} <= fetch_params.keys():
            # temporary 2.1.0b format - just update the connection element
            return apply_fetch(params, ("IMAP", update_fetch(fetch_params)), allowed_keys)

    if "imap_parameters" in params:
        # v2.0.0 and below
        fetch_params = params["imap_parameters"]
        return apply_fetch(params, ("IMAP", update_fetch(fetch_params)), allowed_keys)

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

if __name__ == "__main__":
    # Please keep these lines - they make TDD easy and have no effect on normal test runs.
    # Just run this file from your IDE and dive into the code.
    import doctest

    assert not doctest.testmod().failed
