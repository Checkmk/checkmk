#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import rulespec_group_registry, RulespecGroup
from cmk.gui.valuespec import DropdownChoice


@rulespec_group_registry.register
class RulespecGroupIntegrateOtherServices(RulespecGroup):
    @property
    def name(self):
        return "custom_checks"

    @property
    def title(self):
        return _("Other services")

    @property
    def help(self):
        return _(
            "This services are provided by so called active checks. "
            "You can also integrate custom nagios plugins."
        )


@rulespec_group_registry.register
class RulespecGroupActiveChecks(RulespecGroup):
    @property
    def name(self):
        return "activechecks"

    @property
    def title(self):
        return _("HTTP, TCP, Email, ...")

    @property
    def help(self):
        return _(
            "Rules to add [active_checks|network services] like HTTP and TCP to the "
            "monitoring. The services are provided by so called active checks that allow "
            "you to monitor network services directly from the outside."
        )


# Several active checks just had crit levels as one integer
def transform_cert_days(cert_days):
    if not isinstance(cert_days, tuple):
        return (cert_days, 0)
    return cert_days


def ip_address_family_element():
    return (
        "address_family",
        DropdownChoice(
            title=_("IP address family"),
            choices=[
                (None, _("Primary address family")),
                ("ipv4", _("Enforce IPv4")),
                ("ipv6", _("Enforce IPv6")),
            ],
            default_value=None,
        ),
    )


def transform_add_address_family(v):
    v.setdefault("address_family", None)
    return v
