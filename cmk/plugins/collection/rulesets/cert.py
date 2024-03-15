#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    InputHint,
    Integer,
    LevelDirection,
    List,
    SimpleLevels,
    SimpleLevelsConfigModel,
    String,
    TimeMagnitude,
    TimeSpan,
    validators,
)
from cmk.rulesets.v1.rule_specs import ActiveCheck, Topic

_DAY = 60.0 * 60.0 * 24.0


def _valuespec_response_time() -> SimpleLevels[float]:
    return SimpleLevels[float](
        title=Title("Response time"),
        help_text=Help("Simply defines the thresholds for the time a request may take."),
        form_spec_template=TimeSpan(
            displayed_magnitudes=[
                TimeMagnitude.SECOND,
                TimeMagnitude.MILLISECOND,
            ],
        ),
        level_direction=LevelDirection.UPPER,
        prefill_fixed_levels=DefaultValue((0.1, 0.2)),
    )


def _valuespec_validity() -> Dictionary:
    return Dictionary(
        title=Title("Check certificate validity"),
        help_text=Help("Options to check the general validity of the certificate."),
        elements={
            "remaining": DictElement[SimpleLevelsConfigModel[float]](
                parameter_form=_valuespec_remaining_validity()
            ),
            "maximum": DictElement[float](
                parameter_form=TimeSpan(
                    title=Title("Maximum allowed validity"),
                    help_text=Help(
                        "Any certificate should be expire at some point. Usual values "
                        "are within 90 and 365 days."
                    ),
                    displayed_magnitudes=[TimeMagnitude.DAY],
                    custom_validate=(validators.NumberInRange(min_value=0),),
                    prefill=DefaultValue(90.0 * _DAY),
                )
            ),
            "self_signed": DictElement[bool](
                parameter_form=BooleanChoice(
                    help_text=Help(
                        "The service will not warn if self-signed certificates are used "
                        "if this option is checked."
                    ),
                    label=Label("Allow self-signed certificates"),
                ),
                required=True,
            ),
        },
    )


def _valuespec_specific_values() -> Dictionary:
    return Dictionary(
        title=Title("Check for specific values"),
        help_text=Help("Options to verify that specific fields have an expected value."),
        elements={
            "serialnumber": DictElement[str](
                parameter_form=String(
                    title=Title("Serial number"),
                    help_text=Help(
                        "The serial number needs to be in colon-separated hex format, as also "
                        "shown by 'openssl x509'. The format is not case sensitive."
                    ),
                    prefill=InputHint("5E:49:62:BB:CE:2A:56:A4:15:7F:A1:7C:86:38:45:0F"),
                )
            ),
            "signature_algorithm": DictElement[tuple[str, object]](
                parameter_form=CascadingSingleChoice(
                    title=Title("Certificate signature algorithm"),
                    help_text=Help(
                        "The signature algorithm and the message digest algorithm for the "
                        "certificate's signature. Please note that an exact match is expected if "
                        "this option is used."
                    ),
                    prefill=DefaultValue("rsa"),
                    elements=[
                        CascadingSingleChoiceElement[tuple[str, object]](
                            name="rsa",
                            title=Title("RSA"),
                            parameter_form=_hash_algorithm_choice(),
                        ),
                        CascadingSingleChoiceElement[tuple[str, object]](
                            name="ecdsa",
                            title=Title("ECDSA"),
                            parameter_form=_hash_algorithm_choice(),
                        ),
                        CascadingSingleChoiceElement[None](
                            name="ed25519",
                            title=Title("Ed25519"),
                            parameter_form=FixedValue[None](
                                value=None,
                                title=Title("Ed25519"),
                                label=Label("SHA-512 (fixed)"),
                            ),
                        ),
                        CascadingSingleChoiceElement[tuple[str, object]](
                            name="rsassa_pss",
                            title=Title("RSASSA-PSS"),
                            parameter_form=_hash_algorithm_choice(),
                        ),
                        CascadingSingleChoiceElement[tuple[str, object]](
                            name="dsa",
                            title=Title("DSA"),
                            parameter_form=_hash_algorithm_choice(),
                        ),
                    ],
                )
            ),
            "issuer": DictElement[Mapping[str, object]](
                parameter_form=Dictionary(
                    title=Title("Issuer"),
                    help_text=Help(
                        "With this option you may verify the direct issuer of the checked "
                        "certificate. As the requirements of an intermediate or direct "
                        "root CA are usually higher, this option provides some more "
                        "fields as the option for checking the subject. All entries are "
                        "case sensitive and need to be exaclty specified as provided in "
                        "the certificate."
                    ),
                    elements={
                        "common_name": DictElement[str](
                            parameter_form=String(title=Title("Common name (CN)")),
                            required=True,
                        ),
                        "organization": DictElement[str](
                            parameter_form=String(title=Title("Organization (O)"))
                        ),
                        "org_unit": DictElement[str](
                            parameter_form=String(title=Title("Organizational unit (OU)"))
                        ),
                        "state": DictElement[str](parameter_form=String(title=Title("State (ST)"))),
                        "country": DictElement[str](
                            parameter_form=String(title=Title("Country (C)"))
                        ),
                    },
                )
            ),
            "subject": DictElement[Mapping[str, object]](
                parameter_form=Dictionary(
                    title=Title("Subject"),
                    help_text=Help(
                        "With this option you may verify the subject of the checked "
                        "certificate. This includes a checking for the public key algorithm "
                        "and the size of the public key. Please note that all entries are "
                        "case sensitive and need to be exaclty specified as provided in "
                        "the certificate."
                    ),
                    elements={
                        "common_name": DictElement[str](
                            parameter_form=String(title=Title("Common name (CN)")),
                            required=True,
                        ),
                        "organization": DictElement[str](
                            parameter_form=String(title=Title("Organization (O)"))
                        ),
                        "org_unit": DictElement[str](
                            parameter_form=String(title=Title("Organizational unit (OU)"))
                        ),
                        "pubkey_algorithm": DictElement(
                            parameter_form=CascadingSingleChoice(
                                title=Title("Public key algorithm"),
                                prefill=DefaultValue("rsa"),
                                elements=[
                                    CascadingSingleChoiceElement[str](
                                        name="rsa",
                                        title=Title("RSA"),
                                        parameter_form=FixedValue[str](
                                            value="rsa", title=Title("RSA")
                                        ),
                                    ),
                                    CascadingSingleChoiceElement[str](
                                        name="ec",
                                        title=Title("Elliptic curve"),
                                        parameter_form=FixedValue[str](
                                            value="ec", title=Title("Elliptic curve")
                                        ),
                                    ),
                                    CascadingSingleChoiceElement[str](
                                        name="dsa",
                                        title=Title("DSA"),
                                        parameter_form=FixedValue[str](
                                            value="dsa", title=Title("DSA")
                                        ),
                                    ),
                                ],
                            )
                        ),
                        "pubkeysize": DictElement[str](
                            parameter_form=String(
                                title=Title("Public key size"),
                                prefill=InputHint("2048"),
                                help_text=Help(
                                    "The key size is provided as an integer and needs to match "
                                    "exactly the value in the certificate."
                                ),
                            )
                        ),
                    },
                )
            ),
            "altnames": DictElement[Sequence[str]](
                parameter_form=List[str](
                    element_template=String(),
                    title=Title("Certificate subject alternative name"),
                    help_text=Help(
                        "You may enter one or several alternative names that are "
                        "expected to be in the certificate. Please note that the check "
                        "does only accept DNS names and is case sensitive. So, the "
                        "alternative names need to be exaclty provided as defined "
                        "in the certificate."
                    ),
                ),
            ),
        },
    )


def _valuespec_remaining_validity() -> SimpleLevels[float]:
    return SimpleLevels[float](
        title=Title("Remaining validity time"),
        help_text=Help(
            "These thresholds should be set to reasonable values still allowing "
            "automatic renewals to run or manual processes to take place."
        ),
        form_spec_template=TimeSpan(
            displayed_magnitudes=[TimeMagnitude.DAY],
            custom_validate=(validators.NumberInRange(min_value=0),),
        ),
        level_direction=LevelDirection.LOWER,
        prefill_fixed_levels=DefaultValue((40 * _DAY, 20 * _DAY)),
    )


def _valuespec_port() -> Integer:
    return Integer(
        title=Title("Port"),
        help_text=Help(
            "Any valid TCP port may entered here. The host needs to provide a "
            "certificate on this port. Otherwise the service will be CRIT and "
            "report a handshakre error."
        ),
        prefill=DefaultValue(443),
        custom_validate=(validators.NetworkPort(),),
    )


def _valuespec_host_settings() -> List[Mapping[str, object]]:
    return List(
        title=Title("Endpoints to monitor"),
        help_text=Help(
            "Each endpoint will result in its own service. If not specified or explicitly "
            "overwritten below the endpoint, all standard settings will be used."
        ),
        add_element_label=Label("Add new endpoint"),
        remove_element_label=Label("Remove this endpoint"),
        no_element_label=Label("Please add at least one endpoint to monitor"),
        custom_validate=(validators.LengthInRange(min_value=1),),
        element_template=Dictionary(
            elements={
                "address": DictElement[str](
                    parameter_form=String(
                        title=Title("Host address or name"),
                        help_text=Help(
                            "You may enter any fully qualified domain name or valid "
                            "IP address here. The name does must not contain any further "
                            "information, like port or protocol. You may use macros in "
                            "this field. The most common ones are $HOSTNAME$, $HOSTALIAS$ "
                            "or $HOSTADDRESS$."
                        ),
                        prefill=InputHint("my.host.tld | 192.168.0.73"),
                        custom_validate=(validators.LengthInRange(min_value=1),),
                    ),
                    required=True,
                ),
                "port": DictElement[int](parameter_form=_valuespec_port()),
                "individual_settings": DictElement[Mapping[str, object]](
                    parameter_form=Dictionary(
                        title=Title("Individual settings for this endpoint"),
                        help_text=Help(
                            "Individual settings overwrite or define additional options for this "
                            "particular endpoint. Please note that you will overwrite the complete "
                            "group of options, if you select any of the options below. This enables "
                            "you to unset options for an endpoint, but requires to copy settings "
                            "from the standard if you want to keep some of them."
                        ),
                        elements={
                            "response_time": DictElement(parameter_form=_valuespec_response_time()),
                            "validity": DictElement[Mapping[str, object]](
                                parameter_form=_valuespec_validity()
                            ),
                            "cert_details": DictElement[Mapping[str, object]](
                                parameter_form=_valuespec_specific_values()
                            ),
                        },
                    ),
                ),
            },
        ),
    )


def _valuespec_standard_settings() -> Dictionary:
    return Dictionary(
        title=Title("Standard settings for all endpoints"),
        help_text=Help(
            "Standard settings are used for all endpoints unless overwritten by the individual"
            "settings of an endpoint. Some of the options may not make sense all times as "
            "default for all endpoints."
        ),
        elements={
            "port": DictElement[int](
                parameter_form=_valuespec_port(),
                required=True,
            ),
            "response_time": DictElement(parameter_form=_valuespec_response_time()),
            "validity": DictElement[Mapping[str, object]](parameter_form=_valuespec_validity()),
            "cert_details": DictElement[Mapping[str, object]](
                parameter_form=_valuespec_specific_values()
            ),
        },
    )


def _form_active_checks_cert() -> Dictionary:
    return Dictionary(
        elements={
            "connections": DictElement[Sequence[Mapping[str, object]]](
                parameter_form=_valuespec_host_settings(),
                required=True,
            ),
            "standard_settings": DictElement[Mapping[str, object]](
                parameter_form=_valuespec_standard_settings(),
                required=True,
            ),
        },
    )


def _hash_algorithm_choice() -> CascadingSingleChoice:
    choices = [
        ("sha224", Title("SHA-224")),
        ("sha256", Title("SHA-256")),
        ("sha384", Title("SHA-384")),
        ("sha512", Title("SHA-512")),
        ("sha3_224", Title("SHA3-224")),
        ("sha3_256", Title("SHA3-256")),
        ("sha3_384", Title("SHA3-384")),
        ("sha3_512", Title("SHA3-512")),
    ]
    return CascadingSingleChoice(
        title=Title("Hashing algorithm"),
        elements=[
            CascadingSingleChoiceElement[str](
                name=value,
                title=title,
                parameter_form=FixedValue[str](
                    value=value,
                    title=title,
                ),
            )
            for value, title in choices
        ],
        prefill=DefaultValue("sha256"),
    )


rule_spec_cert = ActiveCheck(
    title=Title("Check certificates"),
    topic=Topic.NETWORKING,
    name="cert",
    parameter_form=_form_active_checks_cert,
)
