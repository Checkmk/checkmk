#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Literal

from cmk.gui.i18n import _
from cmk.gui.valuespec import Alternative, FixedValue, TextInput


def tls_verify_options() -> tuple[Literal["ssl"], Alternative]:
    return (
        "ssl",
        Alternative(
            title=_("SSL certificate checking"),
            elements=[
                FixedValue(value=False, title=_("Deactivated"), totext=""),
                FixedValue(value=True, title=_("Use hostname"), totext=""),
                TextInput(
                    title=_("Use other hostname"),
                    help=_("Use a custom name for the SSL certificate validation"),
                ),
            ],
            default_value=True,
        ),
    )


def tls_verify_flag_default_yes() -> tuple[Literal["no-cert-check"], Alternative]:
    return (
        "no-cert-check",
        Alternative(
            title=_("SSL certificate verification"),
            elements=[
                FixedValue(value=False, title=_("Verify the certificate"), totext=""),
                FixedValue(value=True, title=_("Ignore certificate errors (unsecure)"), totext=""),
            ],
            default_value=False,
        ),
    )


def tls_verify_flag_default_no() -> tuple[Literal["verify-cert"], Alternative]:
    return (
        "verify-cert",
        Alternative(
            title=_("SSL certificate verification"),
            elements=[
                FixedValue(value=True, title=_("Verify the certificate"), totext=""),
                FixedValue(value=False, title=_("Ignore certificate errors (unsecure)"), totext=""),
            ],
            default_value=False,
        ),
    )
