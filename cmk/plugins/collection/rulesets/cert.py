#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

from cmk.rulesets.v1 import Localizable
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DictElement,
    Dictionary,
    FixedLevels,
    FixedValue,
    Float,
    Integer,
    LevelDirection,
    Levels,
    List,
    Text,
    TupleDoNotUseWillbeRemoved,
)
from cmk.rulesets.v1.rule_specs import ActiveChecks, EvalType, Topic
from cmk.rulesets.v1.validators import DisallowEmpty, InRange


def _valuespec_response_time() -> TupleDoNotUseWillbeRemoved:
    # TODO API uses seconds, we need ms here!
    return TupleDoNotUseWillbeRemoved(
        title=Localizable("Response time"),
        elements=[
            Levels(
                form_spec=Float,
                fixed=FixedLevels(),
                level_direction=LevelDirection.LOWER,
                predictive=None,
                unit=Localizable("seconds"),
            ),
            Levels(
                form_spec=Float,
                fixed=FixedLevels(prefill_value=(0.001, 0.002)),
                level_direction=LevelDirection.UPPER,
                predictive=None,
                unit=Localizable("seconds"),
            ),
        ],
    )


def _valuespec_validity() -> Dictionary:
    return Dictionary(
        title=Localizable("Check certificate validity"),
        elements={
            "remaining": DictElement(_valuespec_remaining_validity()),
            "maximum": DictElement(
                Integer(
                    title=Localizable("Maximum allowed validity"),
                    unit=Localizable("days"),
                    custom_validate=InRange(min_value=0),
                )
            ),
            "self_signed": DictElement(
                BooleanChoice(
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
                Text(
                    title=Localizable("Serial number"),
                    input_hint="5E:49:62:BB:CE:2A:56:A4:15:7F:A1:7C:86:38:45:0F",
                )
            ),
            "signature_algorithm": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Localizable("Encryption algorithm"),
                    prefill_selection="rsa",
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
                Dictionary(
                    title=Localizable("Issuer"),
                    elements={
                        "common_name": DictElement(
                            Text(title=Localizable("Common name (CN)")),
                            required=True,
                        ),
                        "organization": DictElement(Text(title=Localizable("Organization (O)"))),
                        "org_unit": DictElement(
                            Text(title=Localizable("Organizational unit (OU)"))
                        ),
                        "state": DictElement(Text(title=Localizable("State (ST)"))),
                        "country": DictElement(Text(title=Localizable("Country (C)"))),
                    },
                )
            ),
            "subject": DictElement(
                Dictionary(
                    title=Localizable("Subject"),
                    elements={
                        "common_name": DictElement(
                            Text(title=Localizable("Common name (CN)")),
                            required=True,
                        ),
                        "organization": DictElement(Text(title=Localizable("Organization (O)"))),
                        "org_unit": DictElement(
                            Text(title=Localizable("Organizational unit (OU)"))
                        ),
                        "pubkey_algorithm": DictElement(
                            CascadingSingleChoice(
                                title=Localizable("Public key algorithm"),
                                prefill_selection="rsa",
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
                                        name="gost-r3410",
                                        title=Localizable("GOST R 34.10-2001"),
                                        parameter_form=FixedValue(
                                            value="gost-r3410",
                                            title=Localizable("GOST R 34.10-2001"),
                                        ),
                                    ),
                                    CascadingSingleChoiceElement(
                                        name="gost-r3410-2012",
                                        title=Localizable("GOST R 34.10-2012"),
                                        parameter_form=FixedValue(
                                            value="gost-r3410",
                                            title=Localizable("GOST R 34.10-2012"),
                                        ),
                                    ),
                                ],
                            )
                        ),
                        "pubkeysize": DictElement(Text(title=Localizable("Public key size"))),
                    },
                )
            ),
            "altnames": DictElement(
                List(
                    parameter_form=Text(),
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
        prefill_value=443,
    )


def _valuespec_host_settings() -> List:
    return List(
        parameter_form=Dictionary(
            elements={
                "connection": DictElement(
                    Dictionary(
                        elements={
                            "address": DictElement(
                                Text(
                                    title=Localizable("Host address or name"),
                                    input_hint="my.host.tld or 192.168.0.73",
                                    custom_validate=DisallowEmpty(),
                                ),
                                required=True,
                            ),
                            "port": DictElement(_valuespec_port()),
                        },
                    ),
                    required=True,
                ),
                "individual_settings": DictElement(
                    Dictionary(
                        title=Localizable("Individual settings"),
                        elements={
                            "response_time": DictElement(_valuespec_response_time()),
                            "validity": DictElement(_valuespec_validity()),
                            "cert_details": DictElement(_valuespec_specific_values()),
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
            "port": DictElement(_valuespec_port()),
            "response_time": DictElement(_valuespec_response_time()),
            "validity": DictElement(_valuespec_validity()),
            "cert_details": DictElement(_valuespec_specific_values()),
        },
    )


def _form_active_checks_cert() -> Dictionary:
    return Dictionary(
        elements={
            "host_settings": DictElement(
                _valuespec_host_settings(),
                required=True,
            ),
            "standard_settings": DictElement(_valuespec_standard_settings()),
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
        prefill_selection="sha256",
    )


rule_spec_cert = ActiveChecks(
    title=Localizable("Check certificates"),
    topic=Topic.NETWORKING,
    eval_type=EvalType.ALL,
    name="cert",
    parameter_form=_form_active_checks_cert,
)
