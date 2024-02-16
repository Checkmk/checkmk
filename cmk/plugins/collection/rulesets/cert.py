#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Literal

from cmk.rulesets.v1 import Localizable
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    Float,
    InputHint,
    Integer,
    LevelDirection,
    Levels,
    LevelsConfigModel,
    List,
    Text,
)
from cmk.rulesets.v1.rule_specs import ActiveCheck, EvalType, Topic
from cmk.rulesets.v1.validators import DisallowEmpty, InRange


def _valuespec_response_time() -> Dictionary:
    # TODO API uses seconds, we need ms here!
    # NOTE (mo): store seconds, not milliseconds. Use TimeSpan Formspec!
    return Dictionary(
        title=Localizable("Response time"),
        elements={
            "levels_lower": DictElement[LevelsConfigModel[float]](
                parameter_form=Levels[float](
                    form_spec_template=Float(unit=Localizable("seconds")),
                    level_direction=LevelDirection.LOWER,
                    prefill_fixed_levels=InputHint((0.0, 0.0)),
                    predictive=None,
                ),
                required=True,
            ),
            "levels_upper": DictElement[LevelsConfigModel[float]](
                parameter_form=Levels[float](
                    form_spec_template=Float(unit=Localizable("seconds")),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue((0.001, 0.002)),
                    predictive=None,
                ),
                required=True,
            ),
        },
    )


def _valuespec_validity() -> Dictionary:
    return Dictionary(
        title=Localizable("Check certificate validity"),
        elements={
            "remaining": DictElement[LevelsConfigModel[int]](
                parameter_form=_valuespec_remaining_validity()
            ),
            "maximum": DictElement[int](
                parameter_form=Integer(
                    title=Localizable("Maximum allowed validity"),
                    unit=Localizable("days"),
                    custom_validate=InRange(min_value=0),
                )
            ),
            "self_signed": DictElement[bool](
                parameter_form=BooleanChoice(
                    label=Localizable("Allow self-signed certificates"),
                ),
                required=True,
            ),
        },
    )


def _valuespec_specific_values() -> Dictionary:
    return Dictionary(
        title=Localizable("Check for specific values"),
        elements={
            "serialnumber": DictElement[str](
                parameter_form=Text(
                    title=Localizable("Serial number"),
                    prefill=InputHint("5E:49:62:BB:CE:2A:56:A4:15:7F:A1:7C:86:38:45:0F"),
                )
            ),
            "signature_algorithm": DictElement[tuple[str, object]](
                parameter_form=CascadingSingleChoice(
                    title=Localizable("Encryption algorithm"),
                    prefill=DefaultValue("rsa"),
                    elements=[
                        CascadingSingleChoiceElement[tuple[str, object]](
                            name="rsa",
                            title=Localizable("RSA"),
                            parameter_form=_get_hashing_algorithm("RSA"),
                        ),
                        CascadingSingleChoiceElement[tuple[str, object]](
                            name="ecdsa",
                            title=Localizable("ECDSA"),
                            parameter_form=_get_hashing_algorithm("ECDSA"),
                        ),
                        CascadingSingleChoiceElement[None](
                            name="ed25519",
                            title=Localizable("ED25519"),
                            parameter_form=FixedValue[None](
                                value=None,
                                title=Localizable("ED25519"),
                                label=Localizable("Hashing algorithm included in encryption"),
                            ),
                        ),
                        CascadingSingleChoiceElement[None](
                            name="rsassa_pss",
                            title=Localizable("RSASSA_PSS"),
                            parameter_form=FixedValue[None](
                                value=None,
                                title=Localizable("RSASSA_PSS"),
                                label=Localizable(
                                    "Defined by signature algorithm parameters",
                                ),
                            ),
                        ),
                        CascadingSingleChoiceElement[tuple[str, object]](
                            name="dsa",
                            title=Localizable("DSA"),
                            parameter_form=_get_hashing_algorithm("DSA"),
                        ),
                    ],
                )
            ),
            "issuer": DictElement[Mapping[str, object]](
                parameter_form=Dictionary(
                    title=Localizable("Issuer"),
                    elements={
                        "common_name": DictElement[str](
                            parameter_form=Text(title=Localizable("Common name (CN)")),
                            required=True,
                        ),
                        "organization": DictElement[str](
                            parameter_form=Text(title=Localizable("Organization (O)"))
                        ),
                        "org_unit": DictElement[str](
                            parameter_form=Text(title=Localizable("Organizational unit (OU)"))
                        ),
                        "state": DictElement[str](
                            parameter_form=Text(title=Localizable("State (ST)"))
                        ),
                        "country": DictElement[str](
                            parameter_form=Text(title=Localizable("Country (C)"))
                        ),
                    },
                )
            ),
            "subject": DictElement[Mapping[str, object]](
                parameter_form=Dictionary(
                    title=Localizable("Subject"),
                    elements={
                        "common_name": DictElement[str](
                            parameter_form=Text(title=Localizable("Common name (CN)")),
                            required=True,
                        ),
                        "organization": DictElement[str](
                            parameter_form=Text(title=Localizable("Organization (O)"))
                        ),
                        "org_unit": DictElement[str](
                            parameter_form=Text(title=Localizable("Organizational unit (OU)"))
                        ),
                        "pubkey_algorithm": DictElement[tuple[str, object]](
                            parameter_form=CascadingSingleChoice(
                                title=Localizable("Public key algorithm"),
                                prefill=DefaultValue("rsa"),
                                elements=[
                                    CascadingSingleChoiceElement[str](
                                        name="rsa",
                                        title=Localizable("RSA"),
                                        parameter_form=FixedValue[str](
                                            value="rsa", title=Localizable("RSA")
                                        ),
                                    ),
                                    CascadingSingleChoiceElement[str](
                                        name="ec",
                                        title=Localizable("Elliptic curve"),
                                        parameter_form=FixedValue[str](
                                            value="ec", title=Localizable("Elliptic curve")
                                        ),
                                    ),
                                    CascadingSingleChoiceElement[str](
                                        name="dsa",
                                        title=Localizable("DSA"),
                                        parameter_form=FixedValue[str](
                                            value="dsa", title=Localizable("DSA")
                                        ),
                                    ),
                                    CascadingSingleChoiceElement[None](
                                        name="gost_r3410",
                                        title=Localizable("GOST R 34.10-2001"),
                                        parameter_form=FixedValue[None](
                                            value=None,
                                            title=Localizable("GOST R 34.10-2001"),
                                        ),
                                    ),
                                    CascadingSingleChoiceElement[None](
                                        name="gost_r3410_2012",
                                        title=Localizable("GOST R 34.10-2012"),
                                        parameter_form=FixedValue[None](
                                            value=None,
                                            title=Localizable("GOST R 34.10-2012"),
                                        ),
                                    ),
                                ],
                            )
                        ),
                        "pubkeysize": DictElement[str](
                            parameter_form=Text(title=Localizable("Public key size"))
                        ),
                    },
                )
            ),
            "altnames": DictElement[Sequence[str]](
                parameter_form=List[str](
                    element_template=Text(),
                    title=Localizable("Certificate subject alternative name"),
                ),
            ),
        },
    )


def _valuespec_remaining_validity() -> Levels[int]:
    return Levels[int](
        title=Localizable("Remaining validity time"),
        help_text=Localizable("Minimum number of days a certificate has to be valid."),
        form_spec_template=Integer(custom_validate=InRange(min_value=0), unit=Localizable("days")),
        level_direction=LevelDirection.LOWER,
        prefill_fixed_levels=InputHint(value=(0, 0)),
        predictive=None,
    )


def _valuespec_port() -> Integer:
    return Integer(
        title=Localizable("Port"),
        prefill=DefaultValue(443),
    )


def _valuespec_host_settings() -> List[Mapping[str, object]]:
    return List(
        element_template=Dictionary(
            elements={
                "connection": DictElement[Mapping[str, object]](
                    parameter_form=Dictionary(
                        elements={
                            "address": DictElement[str](
                                parameter_form=Text(
                                    title=Localizable("Host address or name"),
                                    prefill=InputHint("my.host.tld | 192.168.0.73"),
                                    custom_validate=DisallowEmpty(),
                                ),
                                required=True,
                            ),
                            "port": DictElement[int](parameter_form=_valuespec_port()),
                        },
                    ),
                    required=True,
                ),
                "individual_settings": DictElement[Mapping[str, object]](
                    parameter_form=Dictionary(
                        title=Localizable("Individual settings"),
                        elements={
                            "response_time": DictElement[Mapping[str, object]](
                                parameter_form=_valuespec_response_time()
                            ),
                            "validity": DictElement[Mapping[str, object]](
                                parameter_form=_valuespec_validity()
                            ),
                            "cert_details": DictElement[Mapping[str, object]](
                                parameter_form=_valuespec_specific_values()
                            ),
                        },
                    )
                ),
            },
        )
    )


def _valuespec_standard_settings() -> Dictionary:
    return Dictionary(
        title=Localizable("Standard settings"),
        elements={
            "port": DictElement[int](parameter_form=_valuespec_port()),
            "response_time": DictElement[Mapping[str, object]](
                parameter_form=_valuespec_response_time()
            ),
            "validity": DictElement[Mapping[str, object]](parameter_form=_valuespec_validity()),
            "cert_details": DictElement[Mapping[str, object]](
                parameter_form=_valuespec_specific_values()
            ),
        },
    )


def _form_active_checks_cert() -> Dictionary:
    return Dictionary(
        elements={
            "host_settings": DictElement[Sequence[Mapping[str, object]]](
                parameter_form=_valuespec_host_settings(),
                required=True,
            ),
            "standard_settings": DictElement[Mapping[str, object]](
                parameter_form=_valuespec_standard_settings()
            ),
        },
    )


def _get_hashing_algorithm(algorithm: Literal["RSA", "ECDSA", "DSA"]) -> CascadingSingleChoice:
    sha2 = [
        ("sha224", Localizable("SHA224")),
        ("sha256", Localizable("SHA256")),
        ("sha384", Localizable("SHA384")),
        ("sha512", Localizable("SHA512")),
    ]
    sha3 = [
        ("sha3_224", Localizable("SHA3_224")),
        ("sha3_256", Localizable("SHA3_256")),
        ("sha3_384", Localizable("SHA3_384")),
        ("sha3_512", Localizable("SHA3_512")),
    ]
    elements = sha2 + sha3 if algorithm in ["RSA", "ECDSA"] else sha2
    return CascadingSingleChoice(
        title=Localizable(algorithm),
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
    title=Localizable("Check certificates"),
    topic=Topic.NETWORKING,
    eval_type=EvalType.ALL,
    name="cert",
    parameter_form=_form_active_checks_cert,
)
