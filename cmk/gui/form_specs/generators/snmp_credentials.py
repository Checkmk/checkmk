#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence
from enum import Enum
from typing import Any

from cmk.ccc.exceptions import MKGeneralException

from cmk.gui.form_specs.converter import (
    SimplePassword,
    TransformDataForLegacyFormatOrRecomposeFunction,
    Tuple,
)
from cmk.gui.form_specs.private import (
    not_empty,
    SingleChoiceElementExtended,
    SingleChoiceExtended,
)
from cmk.gui.form_specs.vue.visitors import DefaultValue as VueDefaultValue

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    FixedValue,
    FormSpec,
    String,
)
from cmk.rulesets.v1.form_specs.validators import LengthInRange


class SNMPFormat(Enum):
    NOT_SET = "not_set"
    COMMUNITY = "community"
    SNMPV3_NO_AUTH_NO_PRIV = "snmpv3_noAuthNoPriv"
    SNMPV3_AUTH_NO_PRIV = "snmpv3_authNoPriv"
    SNMPV3_AUTH_PRIV = "snmpv3_authPriv"


def _snmpv3_auth_protocol_elements() -> list[FormSpec[Any]]:
    form_specs: list[FormSpec[Any]] = [
        SingleChoiceExtended[str](
            title=Title("Authentication protocol"),
            elements=[
                SingleChoiceElementExtended(name=name, title=title)
                for (name, title) in [
                    ("md5", Title("MD5 (MD5-96)")),
                    ("sha", Title("SHA-1 (SHA-96)")),
                    ("SHA-224", Title("SHA-2 (SHA-224)")),
                    ("SHA-256", Title("SHA-2 (SHA-256)")),
                    ("SHA-384", Title("SHA-2 (SHA-384)")),
                    ("SHA-512", Title("SHA-2 (SHA-512)")),
                ]
            ],
            prefill=DefaultValue("md5"),
        ),
        String(
            title=Title("Security name"),
        ),
        SimplePassword(
            title=Title("Authentication password"),
            custom_validate=(LengthInRange(min_value=8),),
        ),
    ]
    return form_specs


def _snmp_not_set_element() -> FixedValue[None]:
    return FixedValue(
        value=None,
        title=Title("No explicit credentials"),
        label=Label(""),
    )


def _snmp_community_element() -> SimplePassword:
    return SimplePassword(
        title=Title("SNMP community (SNMP Versions 1 and 2c)"), custom_validate=(not_empty(),)
    )


def _snmpv3_no_auth_no_priv_element() -> Tuple:
    def migrate(x: object) -> tuple[object, ...]:
        if isinstance(x, list | tuple) and len(x) == 2:
            return tuple(x)
        return ("noAuthNoPriv", "")

    return Tuple(
        title=Title("Credentials for SNMPv3 without authentication and privacy (noAuthNoPriv)"),
        elements=[
            FixedValue(
                value="noAuthNoPriv",
                title=Title("Security Level"),
                label=Label("No authentication, no privacy"),
            ),
            String(title=Title("Security name"), custom_validate=(LengthInRange(min_value=1),)),
        ],
        migrate=migrate,
    )


def _snmpv3_auth_no_priv_element() -> Tuple:
    elements: list[FormSpec[Any]] = [
        FixedValue(
            value="authNoPriv",
            title=Title("Security Level"),
            label=Label("authentication but no privacy"),
        ),
    ]
    return Tuple(
        title=Title("Credentials for SNMPv3 with authentication but without privacy (authNoPriv)"),
        elements=elements + _snmpv3_auth_protocol_elements(),
    )


def _snmpv3_auth_priv_element(for_ec: bool = False) -> Tuple:
    priv_protocol_choices = [
        ("DES", Title("CBC-DES")),
        ("AES", Title("AES-128")),
        ("AES-192", Title("AES-192")),
        ("AES-256", Title("AES-256")),
    ]
    if for_ec:
        # EC uses pysnmp which supports these protocols
        # netsnmp/inline + classic do not support these protocols
        priv_protocol_choices.extend(
            [
                ("3DES-EDE", Title("3DES-EDE")),
                ("AES-192-Blumenthal", Title("AES-192-Blumenthal")),
                ("AES-256-Blumenthal", Title("AES-256-Blumenthal")),
            ]
        )

    elements1: list[FormSpec[Any]] = [
        FixedValue(
            value="authPriv",
            title=Title("Security Level"),
            label=Label("authentication and encryption"),
        ),
    ]
    elements2: list[FormSpec[Any]] = [
        SingleChoiceExtended[str](
            title=Title("Privacy protocol"),
            elements=[
                SingleChoiceElementExtended(name=name, title=title)
                for (name, title) in priv_protocol_choices
            ],
            prefill=DefaultValue("DES"),
        ),
        SimplePassword(
            title=Title("Privacy pass phrase"), custom_validate=(LengthInRange(min_value=8),)
        ),
    ]
    return Tuple(
        title=Title("Credentials for SNMPv3 with authentication and privacy (authPriv)"),
        elements=elements1 + _snmpv3_auth_protocol_elements() + elements2,
    )


def _find_element_name_for_value(value: object, only_v3: bool, allow_none: bool) -> SNMPFormat:
    def alternative_match(x):
        if only_v3:
            if x is None or len(x) == 2:
                return SNMPFormat.SNMPV3_NO_AUTH_NO_PRIV
            if len(x) == 4:
                return SNMPFormat.SNMPV3_AUTH_NO_PRIV
            if len(x) == 6:
                return SNMPFormat.SNMPV3_AUTH_PRIV
        else:
            if x is None or isinstance(x, str):
                return SNMPFormat.COMMUNITY
            if len(x) == 1 or len(x) == 2:
                return SNMPFormat.SNMPV3_NO_AUTH_NO_PRIV
            if len(x) == 4:
                return SNMPFormat.SNMPV3_AUTH_NO_PRIV
            if len(x) == 6:
                return SNMPFormat.SNMPV3_AUTH_PRIV
        raise MKGeneralException("Invalid SNMP credentials")

    if allow_none and value is None:
        return SNMPFormat.NOT_SET
    return alternative_match(value)


def _get_elements(
    only_v3: bool, allow_none: bool, for_ec: bool
) -> Sequence[CascadingSingleChoiceElement[Any]]:
    elements: list[CascadingSingleChoiceElement[Any]] = []
    if allow_none:
        elements.append(
            CascadingSingleChoiceElement(
                name="none",
                title=Title("No explicit credentials"),
                parameter_form=_snmp_not_set_element(),
            )
        )

    elements.extend(
        [
            CascadingSingleChoiceElement(
                name="snmpv3_authPriv",
                title=Title("Credentials for SNMPv3 with authentication and privacy (authPriv)"),
                parameter_form=_snmpv3_auth_priv_element(for_ec=for_ec),
            ),
            CascadingSingleChoiceElement(
                name="snmpv3_authNoPriv",
                title=Title(
                    "Credentials for SNMPv3 with authentication but without privacy (authNoPriv)"
                ),
                parameter_form=_snmpv3_auth_no_priv_element(),
            ),
            CascadingSingleChoiceElement(
                name="snmpv3_noAuthNoPriv",
                title=Title(
                    "Credentials for SNMPv3 without authentication and privacy (noAuthNoPriv)"
                ),
                parameter_form=_snmpv3_no_auth_no_priv_element(),
            ),
            CascadingSingleChoiceElement(
                name="community",
                title=Title("SNMP community (SNMP Versions 1 and 2c)"),
                parameter_form=_snmp_community_element(),
            ),
        ]
    )
    if only_v3:
        # HACK: This shifts the indices in alternative_match above!!
        # Furthermore, it doesn't work in conjunction with allow_none.
        elements.pop(0)

    return elements


def convert_from_disk(
    value: object,
    only_v3: bool,
    allow_none: bool,
) -> tuple[object, ...] | VueDefaultValue:
    # Add cascading identifiers to data
    if isinstance(value, VueDefaultValue):
        return value
    snmp_format = _find_element_name_for_value(value, only_v3, allow_none)
    return snmp_format.value, value


def convert_to_disk(data: object) -> object:
    assert isinstance(data, tuple)
    return data[1]


def create_snmp_credentials(
    title: Title | None = None,
    help_text: Help | None = None,
    default_value: str | None = "public",
    only_v3: bool = False,
    allow_none: bool = False,
    for_ec: bool = False,
) -> TransformDataForLegacyFormatOrRecomposeFunction:
    elements = _get_elements(only_v3, allow_none, for_ec)

    if default_value is None:
        if allow_none:
            default_value = "none"
        elif only_v3:
            default_value = "snmpv3_noAuthNoPriv"
        else:
            default_value = "community"

    return TransformDataForLegacyFormatOrRecomposeFunction(
        title=title,
        help_text=help_text,
        from_disk=lambda value: convert_from_disk(value, only_v3, allow_none),
        to_disk=convert_to_disk,
        wrapped_form_spec=CascadingSingleChoice(
            title=title, help_text=help_text, elements=elements, prefill=DefaultValue(default_value)
        ),
    )
