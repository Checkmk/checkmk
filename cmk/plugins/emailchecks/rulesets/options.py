#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="exhaustive-match"

# mypy: disable-error-code="type-arg"


from collections.abc import Callable, Container, Mapping, Sequence
from typing import Literal

from cmk.rulesets.internal.form_specs import OAuth2Connection
from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    Integer,
    migrate_to_password,
    Password,
    String,
    TimeMagnitude,
    TimeSpan,
    validators,
)


def _tuple_do_dict_with_keys(*keys: str) -> Callable[[object], Mapping[str, object]]:
    def _tuple_to_dict(
        param: object,
    ) -> Mapping[str, object]:
        match param:
            case tuple():
                return dict(zip(keys, param))
            case dict() as already_migrated:
                return already_migrated
        raise ValueError(param)

    return _tuple_to_dict


def smtp() -> Dictionary:
    return Dictionary(
        title=Title("SMTP"),
        elements={
            "server": DictElement(
                parameter_form=String(
                    title=Title("SMTP server"),
                    custom_validate=(validators.LengthInRange(1, None),),
                    help_text=Help(
                        "You can specify a host name or IP address different from the IP address "
                        "of the host this check will be assigned to."
                    ),
                ),
            ),
            "connection": DictElement(
                required=True,
                parameter_form=Dictionary(
                    title=Title("Connection settings"),
                    elements={
                        "tls": DictElement(
                            parameter_form=FixedValue(
                                value=True,
                                title=Title("Use TLS over SMTP"),
                                label=Label("Encrypt SMTP communication using TLS"),
                            ),
                        ),
                        "port": DictElement(
                            parameter_form=Integer(
                                title=Title("SMTP TCP Port to connect to"),
                                help_text=Help(
                                    "The TCP Port the SMTP server is listening on. Defaulting to <tt>25</tt>."
                                ),
                                prefill=DefaultValue(25),
                                custom_validate=(validators.NetworkPort(),),
                            ),
                        ),
                    },
                ),
            ),
            "auth": DictElement(
                parameter_form=Dictionary(
                    title=Title("SMTP Authentication"),
                    elements={
                        "username": DictElement(
                            required=True,
                            parameter_form=String(
                                title=Title("Username"),
                                custom_validate=(validators.LengthInRange(1, None),),
                            ),
                        ),
                        "password": DictElement(
                            required=True,
                            parameter_form=Password(
                                title=Title("Password"), migrate=migrate_to_password
                            ),
                        ),
                    },
                    migrate=_tuple_do_dict_with_keys("username", "password"),
                ),
            ),
        },
    )


def _oauth2_options() -> tuple[Sequence[CascadingSingleChoiceElement], Mapping[str, DictElement]]:
    return (
        [
            CascadingSingleChoiceElement(
                name="oauth2",
                title=Title("OAuth2 (ClientID/TenantID)"),
                parameter_form=Dictionary(
                    elements={
                        "client_id": DictElement(
                            required=True,
                            parameter_form=String(
                                title=Title("ClientID"),
                                custom_validate=(validators.LengthInRange(1, None),),
                            ),
                        ),
                        "client_secret": DictElement(
                            required=True,
                            parameter_form=Password(
                                title=Title("Client Secret"), migrate=migrate_to_password
                            ),
                        ),
                        "tenant_id": DictElement(
                            required=True,
                            parameter_form=String(
                                title=Title("TenantID"),
                                custom_validate=(validators.LengthInRange(1, None),),
                            ),
                        ),
                    },
                    migrate=_tuple_do_dict_with_keys("client_id", "client_secret", "tenant_id"),
                ),
            )
        ],
        {
            "email_address": DictElement(
                parameter_form=String(
                    title=Title("Email address used for account identification"),
                    label=Label("(overrides <b>username</b>)"),
                    help_text=Help(
                        "Used to specify the account to be contacted"
                        " (aka. 'PrimarySmtpAddress') in case it's different from the"
                        " username. If not specified the credentials username is used."
                    ),
                    custom_validate=(validators.EmailAddress(),),
                )
            )
        },
    )


def common(protocol: str, port_defaults: str) -> Dictionary:
    oauth, email_options = _oauth2_options() if protocol == "EWS" else ((), {})

    return Dictionary(
        title=Title("%s") % protocol,
        elements={
            "server": DictElement(
                parameter_form=String(
                    title=Title("%s server") % protocol,
                    macro_support=True,
                    help_text=Help(
                        "You can specify a host name or IP address different from the IP "
                        "address of the host this check will be assigned to."
                    ),
                )
            ),
            "connection": DictElement(
                required=True,
                parameter_form=Dictionary(
                    title=Title("Connection settings"),
                    elements={
                        "disable_tls": DictElement(
                            parameter_form=BooleanChoice(
                                title=Title("Disable TLS/SSL"),
                                label=Label("Force unencrypted communication"),
                            )
                        ),
                        "disable_cert_validation": DictElement(
                            parameter_form=BooleanChoice(
                                title=Title("Disable certificate validation"),
                                label=Label("Ignore unsuccessful validation (in case of TLS/SSL)"),
                            )
                        ),
                        "port": DictElement(
                            parameter_form=Integer(
                                title=Title("TCP Port"),
                                label=Label("(default is %r for %s/TLS)")
                                % (port_defaults, protocol),
                                custom_validate=(validators.NetworkPort(),),
                            )
                        ),
                    },
                ),
            ),
            "auth": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Authentication types"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="basic",
                            title=Title("Username / Password"),
                            parameter_form=Dictionary(
                                elements={
                                    "username": DictElement(
                                        required=True,
                                        parameter_form=String(
                                            title=Title("Username"),
                                            custom_validate=(validators.LengthInRange(1, None),),
                                        ),
                                    ),
                                    "password": DictElement(
                                        required=True,
                                        parameter_form=Password(
                                            title=Title("Password"), migrate=migrate_to_password
                                        ),
                                    ),
                                },
                                migrate=_tuple_do_dict_with_keys("username", "password"),
                            ),
                        ),
                        *oauth,
                    ],
                ),
            ),
            **email_options,
        },
        custom_validate=(_validate_common,),
    )


def _validate_common(params: Mapping[str, object]) -> None:
    match params:
        case {"auth": ("oauth2", _value), **rest} if "email_address" not in rest:
            raise ValueError(
                Message(
                    "With authentication type set to 'OAuth2' the option '%s' must be specified."
                )
                % Message("Email address used for account identification")
            )


def sending() -> CascadingSingleChoice:
    return CascadingSingleChoice(
        title=Title("Mail sending"),
        elements=[
            CascadingSingleChoiceElement(name="SMTP", title=Title("SMTP"), parameter_form=smtp()),
            CascadingSingleChoiceElement(
                name="EWS", title=Title("EWS"), parameter_form=common("EWS", "80/443")
            ),
            CascadingSingleChoiceElement(
                name="GRAPHAPI",
                title=Title("Microsoft Exchange Online"),
                parameter_form=Dictionary(
                    title=Title("Microsoft Exchange Online"),
                    elements={
                        "auth": DictElement(
                            required=True,
                            parameter_form=OAuth2Connection(
                                title=Title("Microsoft Entra ID connection"),
                                connector_type="microsoft_entra_id",
                            ),
                        )
                    },
                ),
            ),
        ],
    )


def fetching(
    supported_protocols: Container[Literal["IMAP", "POP3", "EWS", "GRAPHAPI"]],
) -> CascadingSingleChoice:
    return CascadingSingleChoice(
        title=Title("Mail receiving"),
        elements=[
            e
            for e in [
                CascadingSingleChoiceElement(
                    name="IMAP",
                    title=Title("IMAP"),
                    parameter_form=common("IMAP", "143/993"),
                ),
                CascadingSingleChoiceElement(
                    name="POP3", title=Title("POP3"), parameter_form=common("POP3", "110/995")
                ),
                CascadingSingleChoiceElement(
                    name="EWS", title=Title("EWS"), parameter_form=common("EWS", "80/443")
                ),
                CascadingSingleChoiceElement(
                    name="GRAPHAPI",
                    title=Title("Microsoft Exchange Online"),
                    parameter_form=Dictionary(
                        title=Title("Microsoft Exchange Online"),
                        elements={
                            "auth": DictElement(
                                required=True,
                                parameter_form=OAuth2Connection(
                                    title=Title("Microsoft Entra ID connection"),
                                    connector_type="microsoft_entra_id",
                                ),
                            )
                        },
                    ),
                ),
            ]
            if e.name in supported_protocols
        ],
    )


def timeout() -> TimeSpan:
    return TimeSpan(
        title=Title("Connect timeout"),
        custom_validate=(validators.NumberInRange(min_value=1),),
        prefill=DefaultValue(10.0),
        displayed_magnitudes=(TimeMagnitude.SECOND,),
        migrate=float,  # type: ignore[arg-type] # wrong type, right behaviour
    )
