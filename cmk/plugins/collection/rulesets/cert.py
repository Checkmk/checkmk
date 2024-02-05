#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

from cmk.rulesets.v1 import Localizable
from cmk.rulesets.v1.form_specs import DefaultValue, InputHint
from cmk.rulesets.v1.form_specs.basic import BooleanChoice, FixedValue, Float, Integer, Text
from cmk.rulesets.v1.form_specs.composed import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DictElement,
    Dictionary,
    List,
    TupleDoNotUseWillbeRemoved,
)
from cmk.rulesets.v1.form_specs.levels import LevelDirection, Levels
from cmk.rulesets.v1.rule_specs import ActiveCheck, EvalType, Topic
from cmk.rulesets.v1.validators import DisallowEmpty, InRange


def _valuespec_response_time() -> TupleDoNotUseWillbeRemoved:
    # TODO API uses seconds, we need ms here!
    # NOTE (mo): store seconds, not milliseconds. Use TimeSpan Formspec!
    return TupleDoNotUseWillbeRemoved(
        title=Localizable("Response time"),
        elements=[
            Levels(
                form_spec_template=Float(unit=Localizable("seconds")),
                level_direction=LevelDirection.LOWER,
                prefill_fixed_levels=InputHint((0.0, 0.0)),
                predictive=None,
            ),
            Levels(
                form_spec_template=Float(unit=Localizable("seconds")),
                level_direction=LevelDirection.UPPER,
                prefill_fixed_levels=DefaultValue((0.001, 0.002)),
                predictive=None,
            ),
        ],
    )


def _valuespec_validity() -> Dictionary:
    return Dictionary(
        title=Localizable("Check certificate validity"),
        elements={
            "remaining": DictElement(parameter_form=_valuespec_remaining_validity()),
            "maximum": DictElement(
                parameter_form=Integer(
                    title=Localizable("Maximum allowed validity"),
                    unit=Localizable("days"),
                    custom_validate=InRange(min_value=0),
                )
            ),
            "self_signed": DictElement(
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
            "serialnumber": DictElement(
                parameter_form=Text(
                    title=Localizable("Serial number"),
                    prefill=InputHint("5E:49:62:BB:CE:2A:56:A4:15:7F:A1:7C:86:38:45:0F"),
                )
            ),
            "signature_algorithm": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Localizable("Encryption algorithm"),
                    prefill=DefaultValue("rsa"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="rsa",
                            title=Localizable("RSA"),
                            parameter_form=_get_hashing_algorithm("RSA"),
                        ),
                        CascadingSingleChoiceElement(
                            name="ecdsa",
                            title=Localizable("ECDSA"),
                            parameter_form=_get_hashing_algorithm("ECDSA"),
                        ),
                        CascadingSingleChoiceElement(
                            name="ed25519",
                            title=Localizable("ED25519"),
                            parameter_form=FixedValue(
                                value=None,
                                title=Localizable("ED25519"),
                                label=Localizable("Hashing algorithm included in encryption"),
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="rsassa_pss",
                            title=Localizable("RSASSA_PSS"),
                            parameter_form=FixedValue(
                                value=None,
                                title=Localizable("RSASSA_PSS"),
                                label=Localizable(
                                    "Defined by signature algorithm parameters",
                                ),
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="dsa",
                            title=Localizable("DSA"),
                            parameter_form=_get_hashing_algorithm("DSA"),
                        ),
                    ],
                )
            ),
            "issuer": DictElement(
                parameter_form=Dictionary(
                    title=Localizable("Issuer"),
                    elements={
                        "common_name": DictElement(
                            parameter_form=Text(title=Localizable("Common name (CN)")),
                            required=True,
                        ),
                        "organization": DictElement(
                            parameter_form=Text(title=Localizable("Organization (O)"))
                        ),
                        "org_unit": DictElement(
                            parameter_form=Text(title=Localizable("Organizational unit (OU)"))
                        ),
                        "state": DictElement(parameter_form=Text(title=Localizable("State (ST)"))),
                        "country": DictElement(
                            parameter_form=Text(title=Localizable("Country (C)"))
                        ),
                    },
                )
            ),
            "subject": DictElement(
                parameter_form=Dictionary(
                    title=Localizable("Subject"),
                    elements={
                        "common_name": DictElement(
                            parameter_form=Text(title=Localizable("Common name (CN)")),
                            required=True,
                        ),
                        "organization": DictElement(
                            parameter_form=Text(title=Localizable("Organization (O)"))
                        ),
                        "org_unit": DictElement(
                            parameter_form=Text(title=Localizable("Organizational unit (OU)"))
                        ),
                        "pubkey_algorithm": DictElement(
                            parameter_form=CascadingSingleChoice(
                                title=Localizable("Public key algorithm"),
                                prefill=DefaultValue("rsa"),
                                elements=[
                                    CascadingSingleChoiceElement(
                                        name="rsa",
                                        title=Localizable("RSA"),
                                        parameter_form=FixedValue(
                                            value="rsa", title=Localizable("RSA")
                                        ),
                                    ),
                                    CascadingSingleChoiceElement(
                                        name="ec",
                                        title=Localizable("Elliptic curve"),
                                        parameter_form=FixedValue(
                                            value="ec", title=Localizable("Elliptic curve")
                                        ),
                                    ),
                                    CascadingSingleChoiceElement(
                                        name="dsa",
                                        title=Localizable("DSA"),
                                        parameter_form=FixedValue(
                                            value="dsa", title=Localizable("DSA")
                                        ),
                                    ),
                                    CascadingSingleChoiceElement(
                                        name="gost_r3410",
                                        title=Localizable("GOST R 34.10-2001"),
                                        parameter_form=FixedValue(
                                            value=None,
                                            title=Localizable("GOST R 34.10-2001"),
                                        ),
                                    ),
                                    CascadingSingleChoiceElement(
                                        name="gost_r3410_2012",
                                        title=Localizable("GOST R 34.10-2012"),
                                        parameter_form=FixedValue(
                                            value=None,
                                            title=Localizable("GOST R 34.10-2012"),
                                        ),
                                    ),
                                ],
                            )
                        ),
                        "pubkeysize": DictElement(
                            parameter_form=Text(title=Localizable("Public key size"))
                        ),
                    },
                )
            ),
            "altnames": DictElement(
                parameter_form=List(
                    element_template=Text(),
                    title=Localizable("Certificate subject alternative name"),
                ),
            ),
        },
    )


def _valuespec_remaining_validity() -> TupleDoNotUseWillbeRemoved:
    return TupleDoNotUseWillbeRemoved(
        title=Localizable("Remaining validity time"),
        help_text=Localizable("Minimum number of days a certificate has to be valid."),
        elements=[
            Integer(
                title=Localizable("Warning at or below"),
                unit=Localizable("days"),
                custom_validate=InRange(min_value=0),
            ),
            Integer(
                title=Localizable("Critical at or below"),
                unit=Localizable("days"),
                custom_validate=InRange(min_value=0),
            ),
        ],
    )


def _valuespec_port() -> Integer:
    return Integer(
        title=Localizable("Port"),
        prefill=DefaultValue(443),
    )


def _valuespec_host_settings() -> List:
    return List(
        element_template=Dictionary(
            elements={
                "connection": DictElement(
                    parameter_form=Dictionary(
                        elements={
                            "address": DictElement(
                                parameter_form=Text(
                                    title=Localizable("Host address or name"),
                                    prefill=InputHint("my.host.tld | 192.168.0.73"),
                                    custom_validate=DisallowEmpty(),
                                ),
                                required=True,
                            ),
                            "port": DictElement(parameter_form=_valuespec_port()),
                        },
                    ),
                    required=True,
                ),
                "individual_settings": DictElement(
                    parameter_form=Dictionary(
                        title=Localizable("Individual settings"),
                        elements={
                            "response_time": DictElement(parameter_form=_valuespec_response_time()),
                            "validity": DictElement(parameter_form=_valuespec_validity()),
                            "cert_details": DictElement(
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
            "port": DictElement(parameter_form=_valuespec_port()),
            "response_time": DictElement(parameter_form=_valuespec_response_time()),
            "validity": DictElement(parameter_form=_valuespec_validity()),
            "cert_details": DictElement(parameter_form=_valuespec_specific_values()),
        },
    )


def _form_active_checks_cert() -> Dictionary:
    return Dictionary(
        elements={
            "host_settings": DictElement(
                parameter_form=_valuespec_host_settings(),
                required=True,
            ),
            "standard_settings": DictElement(parameter_form=_valuespec_standard_settings()),
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
            CascadingSingleChoiceElement(
                name=value,
                title=title,
                parameter_form=FixedValue(
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
