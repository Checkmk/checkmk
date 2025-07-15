#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from types import NoneType
from typing import Literal

from cmk.ccc.exceptions import MKGeneralException

from cmk.gui.form_specs.converter import SimplePassword
from cmk.gui.form_specs.private import not_empty
from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Alternative,
    Dictionary,
    DropdownChoice,
    FixedValue,
    MigrateNotUpdated,
    Password,
    TextInput,
    Tuple,
    ValueSpec,
    ValueSpecHelp,
)

from cmk.rulesets.v1 import form_specs, Title


def IPMIParameters() -> Dictionary:
    return Dictionary(
        title=_("IPMI credentials"),
        elements=[
            (
                "username",
                TextInput(
                    title=_("Username"),
                    allow_empty=False,
                ),
            ),
            (
                "password",
                Password(
                    title=_("Password"),
                    allow_empty=False,
                ),
            ),
        ],
        optional_keys=[],
    )


def create_ipmi_parameters() -> form_specs.Dictionary:
    return form_specs.Dictionary(
        title=Title("IPMI credentials"),
        elements={
            "username": form_specs.DictElement(
                required=True,
                parameter_form=form_specs.String(
                    title=Title("Username"),
                ),
            ),
            "password": form_specs.DictElement(
                required=True,
                parameter_form=SimplePassword(
                    title=Title("Password"), custom_validate=[not_empty()]
                ),
            ),
        },
    )


def SNMPCredentials(
    title: str | None = None,
    help: ValueSpecHelp | None = None,
    only_v3: bool = False,
    default_value: str | None = "public",
    allow_none: bool = False,
    for_ec: bool = False,
) -> Alternative:
    def alternative_match(x: object) -> Literal[0, 1, 2, 3]:
        if not isinstance(x, tuple | str | NoneType):
            raise MKGeneralException("invalid SNMP credential type %s" % type(x))

        if only_v3:
            # NOTE: Indices are shifted by 1 due to a only_v3 hack below!!
            if x is None or len(x) == 2:
                return 0  # noAuthNoPriv
            if len(x) == 4:
                return 1  # authNoPriv
            if len(x) == 6:
                return 2  # authPriv
        else:
            if x is None or isinstance(x, str):
                return 0  # community only
            if len(x) == 1 or len(x) == 2:
                return 1  # noAuthNoPriv
            if len(x) == 4:
                return 2  # authNoPriv
            if len(x) == 6:
                return 3  # authPriv
        raise MKGeneralException("invalid SNMP credential format %s" % tuple("***" for _ in x))

    def allow_none_match(x: object) -> int:
        return 0 if x is None else (alternative_match(x) + 1)

    if allow_none:
        # Wrap match() function defined above
        match = allow_none_match
        elements = [_snmp_no_credentials_element()]
    else:
        match = alternative_match
        elements = []

    elements.extend(
        [
            _snmpv1_v2_credentials_element(),
            _snmpv3_no_auth_no_priv_credentials_element(),
            _snmpv3_auth_no_priv_credentials_element(),
            _snmpv3_auth_priv_credentials_element(for_ec=for_ec),
        ]
    )

    if only_v3:
        # HACK: This shifts the indices in alternative_match above!!
        # Furthermore, it doesn't work in conjunction with allow_none.
        elements.pop(0)
        title = title if title is not None else _("SNMPv3 credentials")
    else:
        title = title if title is not None else _("SNMP credentials")

    return Alternative(
        title=title,
        help=help,
        default_value=default_value,
        match=match,
        elements=elements,
    )


def _snmp_no_credentials_element() -> ValueSpec:
    return FixedValue(
        value=None,
        title=_("No explicit credentials"),
        totext="",
    )


def _snmpv1_v2_credentials_element() -> ValueSpec:
    return Password(
        title=_("SNMP community (SNMP Versions 1 and 2c)"),
        allow_empty=False,
    )


def _snmpv3_no_auth_no_priv_credentials_element() -> ValueSpec:
    return MigrateNotUpdated(
        valuespec=Tuple(
            title=_("Credentials for SNMPv3 without authentication and privacy (noAuthNoPriv)"),
            elements=[
                FixedValue(
                    value="noAuthNoPriv",
                    title=_("Security Level"),
                    totext=_("No authentication, no privacy"),
                ),
                TextInput(title=_("Security name"), allow_empty=False),
            ],
        ),
        migrate=lambda x: x if (x and len(x) == 2) else ("noAuthNoPriv", ""),
    )


def _snmpv3_auth_no_priv_credentials_element() -> ValueSpec:
    elements: list[ValueSpec] = [
        FixedValue(
            value="authNoPriv",
            title=_("Security Level"),
            totext=_("authentication but no privacy"),
        ),
    ]
    return Tuple(
        title=_("Credentials for SNMPv3 with authentication but without privacy (authNoPriv)"),
        elements=elements + _snmpv3_auth_protocol_elements(),
    )


def _snmpv3_auth_priv_credentials_element(for_ec: bool = False) -> ValueSpec:
    priv_protocol_choices = [
        ("DES", _("CBC-DES")),
        ("AES", _("AES-128")),
        ("AES-192", _("AES-192")),
        ("AES-256", _("AES-256")),
    ]
    if for_ec:
        # EC uses pysnmp which supports these protocols
        # netsnmp/inline + classic do not support these protocols
        priv_protocol_choices.extend(
            [
                ("3DES-EDE", _("3DES-EDE")),
                ("AES-192-Blumenthal", _("AES-192-Blumenthal")),
                ("AES-256-Blumenthal", _("AES-256-Blumenthal")),
            ]
        )
    elements1: list[ValueSpec] = [
        FixedValue(
            value="authPriv",
            title=_("Security Level"),
            totext=_("authentication and encryption"),
        ),
    ]
    elements2: list[ValueSpec] = [
        DropdownChoice(
            choices=priv_protocol_choices,
            title=_("Privacy protocol"),
        ),
        Password(
            title=_("Privacy pass phrase"),
            minlen=8,
        ),
    ]
    return Tuple(
        title=_("Credentials for SNMPv3 with authentication and privacy (authPriv)"),
        elements=elements1 + _snmpv3_auth_protocol_elements() + elements2,
    )


def _snmpv3_auth_protocol_elements() -> list[ValueSpec]:
    return [
        DropdownChoice(
            choices=[
                ("md5", _("MD5 (MD5-96)")),
                ("sha", _("SHA-1 (SHA-96)")),
                ("SHA-224", _("SHA-2 (SHA-224)")),
                ("SHA-256", _("SHA-2 (SHA-256)")),
                ("SHA-384", _("SHA-2 (SHA-384)")),
                ("SHA-512", _("SHA-2 (SHA-512)")),
            ],
            title=_("Authentication protocol"),
        ),
        TextInput(
            title=_("Security name"),
        ),
        Password(
            title=_("Authentication password"),
            minlen=8,
        ),
    ]
