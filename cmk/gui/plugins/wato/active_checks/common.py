#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

from cmk.gui.i18n import _
from cmk.gui.valuespec import DropdownChoice

# courtesy to RS: leave this in until 2.4 for MKP compatibility
from cmk.gui.wato import RulespecGroupIntegrateOtherServices  # noqa: F401


def ip_address_family_element() -> tuple[Literal["address_family"], DropdownChoice]:
    return (
        "address_family",
        DropdownChoice(
            title=_("IP address family"),
            choices=[
                (None, _("Primary address family")),
                ("ipv4", _("Use any network address")),
                ("ipv6", _("Enforce IPv6")),
            ],
            default_value=None,
        ),
    )
