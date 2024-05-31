#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import Dictionary, IPv4Address, Password, TextInput

from ._base import NotificationParameter


class NotificationParameterSpectrum(NotificationParameter):
    @property
    def ident(self) -> str:
        return "spectrum"

    @property
    def spec(self):
        return Dictionary(
            title=_("Create notification with the following parameters"),
            optional_keys=False,
            elements=[
                (
                    "destination",
                    IPv4Address(
                        title=_("Destination IP"),
                        help=_("IP address of the Spectrum server receiving the SNMP trap"),
                    ),
                ),
                (
                    "community",
                    Password(
                        title=_("SNMP community"),
                        help=_("SNMP community for the SNMP trap"),
                    ),
                ),
                (
                    "baseoid",
                    TextInput(
                        title=_("Base OID"),
                        help=_("The base OID for the trap content"),
                        default_value="1.3.6.1.4.1.1234",
                    ),
                ),
            ],
        )
