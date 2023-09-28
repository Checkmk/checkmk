#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import rulespec_group_registry, RulespecGroup
from cmk.gui.valuespec import DropdownChoice


@rulespec_group_registry.register
class RulespecGroupIntegrateOtherServices(RulespecGroup):
    @property
    def name(self) -> str:
        return "custom_checks"

    @property
    def title(self) -> str:
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
    def name(self) -> str:
        return "activechecks"

    @property
    def title(self) -> str:
        return _("HTTP, TCP, Email, ...")

    @property
    def help(self):
        return _(
            "Rules to add [active_checks|network services] like HTTP and TCP to the "
            "monitoring. The services are provided by so called active checks that allow "
            "you to monitor network services directly from the outside."
        )


def ip_address_family_element():
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


def ip_address_family_http():
    return (
        "address_family",
        DropdownChoice(
            title=_("IP address family"),
            choices=[
                (None, _("Primary address family")),
                ("ipv4", _("Use any network address")),
                ("ipv4_enforced", _("Enforce IPv4")),
                ("ipv6", _("Enforce IPv6")),
            ],
            default_value=None,
        ),
    )
