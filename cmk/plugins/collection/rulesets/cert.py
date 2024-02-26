#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Literal

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
from cmk.rulesets.v1.rule_specs import ActiveCheck, EvalType, Topic


def _valuespec_response_time() -> SimpleLevels[float]:
    return SimpleLevels[float](
        title=Title("Response time"),
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
        elements={
            "remaining": DictElement[SimpleLevelsConfigModel[float]](
                parameter_form=_valuespec_remaining_validity()
            ),
            "maximum": DictElement[float](
                parameter_form=TimeSpan(
                    title=Title("Maximum allowed validity"),
                    displayed_magnitudes=[TimeMagnitude.DAY],
                    custom_validate=validators.InRange(min_value=0),
                )
            ),
            "self_signed": DictElement[bool](
                parameter_form=BooleanChoice(
                    label=Label("Allow self-signed certificates"),
                ),
                required=True,
            ),
        },
    )


def _valuespec_specific_values() -> Dictionary:
    return Dictionary(
        title=Title("Check for specific values"),
        elements={
            "serialnumber": DictElement[str](
                parameter_form=String(
                    title=Title("Serial number"),
                    prefill=InputHint("5E:49:62:BB:CE:2A:56:A4:15:7F:A1:7C:86:38:45:0F"),
                )
            ),
            "signature_algorithm": DictElement[tuple[str, object]](
                parameter_form=CascadingSingleChoice(
                    title=Title("Encryption algorithm"),
                    prefill=DefaultValue("rsa"),
                    elements=[
                        CascadingSingleChoiceElement[tuple[str, object]](
                            name="rsa",
                            title=Title("RSA"),
                            parameter_form=_get_hashing_algorithm("RSA"),
                        ),
                        CascadingSingleChoiceElement[tuple[str, object]](
                            name="ecdsa",
                            title=Title("ECDSA"),
                            parameter_form=_get_hashing_algorithm("ECDSA"),
                        ),
                        CascadingSingleChoiceElement[None](
                            name="ed25519",
                            title=Title("ED25519"),
                            parameter_form=FixedValue[None](
                                value=None,
                                title=Title("ED25519"),
                                label=Label("Hashing algorithm included in encryption"),
                            ),
                        ),
                        CascadingSingleChoiceElement[None](
                            name="rsassa_pss",
                            title=Title("RSASSA_PSS"),
                            parameter_form=FixedValue[None](
                                value=None,
                                title=Title("RSASSA_PSS"),
                                label=Label(
                                    "Defined by signature algorithm parameters",
                                ),
                            ),
                        ),
                        CascadingSingleChoiceElement[tuple[str, object]](
                            name="dsa",
                            title=Title("DSA"),
                            parameter_form=_get_hashing_algorithm("DSA"),
                        ),
                    ],
                )
            ),
            "issuer": DictElement[Mapping[str, object]](
                parameter_form=Dictionary(
                    title=Title("Issuer"),
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
                            parameter_form=String(title=Title("Public key size"))
                        ),
                    },
                )
            ),
            "altnames": DictElement[Sequence[str]](
                parameter_form=List[str](
                    element_template=String(),
                    title=Title("Certificate subject alternative name"),
                ),
            ),
        },
    )


def _valuespec_remaining_validity() -> SimpleLevels[float]:
    return SimpleLevels[float](
        title=Title("Remaining validity time"),
        help_text=Help("Minimum number of days a certificate has to be valid."),
        form_spec_template=TimeSpan(
            displayed_magnitudes=[TimeMagnitude.DAY],
            custom_validate=validators.InRange(min_value=0),
        ),
        level_direction=LevelDirection.LOWER,
        prefill_fixed_levels=InputHint((0.0, 0.0)),
    )


def _valuespec_port() -> Integer:
    return Integer(
        title=Title("Port"),
        prefill=DefaultValue(443),
        custom_validate=validators.NetworkPort(),
    )


def _valuespec_host_settings() -> List[Mapping[str, object]]:
    return List(
        title=Title("Endpoints to monitor"),
        add_element_label=Label("Add new endpoint"),
        remove_element_label=Label("Remove this endpoint"),
        no_element_label=Label("Please add at least one endpoint to monitor"),
        custom_validate=validators.DisallowEmpty(),
        element_template=Dictionary(
            elements={
                "address": DictElement[str](
                    parameter_form=String(
                        title=Title("Host address or name"),
                        prefill=InputHint("my.host.tld | 192.168.0.73"),
                        custom_validate=validators.DisallowEmpty(),
                    ),
                    required=True,
                ),
                "port": DictElement[int](parameter_form=_valuespec_port()),
                "individual_settings": DictElement[Mapping[str, object]](
                    parameter_form=Dictionary(
                        title=Title("Individual settings for this endpoint"),
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
        elements={
            "port": DictElement[int](parameter_form=_valuespec_port(), required=True),
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


def _get_hashing_algorithm(algorithm: Literal["RSA", "ECDSA", "DSA"]) -> CascadingSingleChoice:
    sha2 = [
        ("sha224", Title("SHA224")),
        ("sha256", Title("SHA256")),
        ("sha384", Title("SHA384")),
        ("sha512", Title("SHA512")),
    ]
    sha3 = [
        ("sha3_224", Title("SHA3_224")),
        ("sha3_256", Title("SHA3_256")),
        ("sha3_384", Title("SHA3_384")),
        ("sha3_512", Title("SHA3_512")),
    ]
    elements = sha2 + sha3 if algorithm in ["RSA", "ECDSA"] else sha2
    return CascadingSingleChoice(
        title=Title(algorithm),
        elements=[
            CascadingSingleChoiceElement[str](
                name=value,
                title=title,
                parameter_form=FixedValue[str](
                    value=value,
                    title=title,
                ),
            )
            for value, title in elements
        ],
        prefill=DefaultValue("sha256"),
    )


rule_spec_cert = ActiveCheck(
    title=Title("Check certificates"),
    topic=Topic.NETWORKING,
    eval_type=EvalType.ALL,
    name="cert",
    parameter_form=_form_active_checks_cert,
)
