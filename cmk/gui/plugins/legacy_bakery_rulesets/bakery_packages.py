#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    HostRulespec,
    rulespec_registry,
    RulespecGroupMonitoringAgentsGenericOptions,
)
from cmk.gui.valuespec import Dictionary, DropdownChoice, ListChoice
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_bakery_packages() -> Dictionary:
    return Dictionary(
        title=_("Agent Bakery packages"),
        help=_(
            "You can use these options to tune the way packages are baked for your hosts which may "
            "have a positive impact on the performance of the baking procedure. "
            "Defaults to bake for all platforms with no compression."
        ),
        elements=[
            (
                "selection",
                ListChoice(
                    title=_("Select packages"),
                    help=_(
                        "Explicitly select packages to be baked. "
                        "If this rule entry is not activated, all packages are baked."
                    ),
                    choices=[
                        ("linux_deb", _("Linux: DPKG (.deb)")),
                        ("linux_rpm", _("Linux: RPM (.rpm)")),
                        ("linux_tgz", _("Linux: TGZ (.tar.gz)")),
                        ("solaris_pkg", _("Solaris: PKG (.pkg)")),
                        ("solaris_tgz", _("Solaris: TGZ (.tar.gz)")),
                        ("aix_tgz", _("AIX: TGZ (.tar.gz)")),
                        ("windows_msi", _("Windows: MSI (.msi)")),
                    ],
                    toggle_all=True,
                ),
            ),
            (
                "compression",
                DropdownChoice(
                    title=_("Apply compression to agent packages"),
                    help=_(
                        "When activated, the Agent Bakery will compress most of the agent packages. "
                        "The compression applies to .deb packages, .rpm packages and to all "
                        ".tar.gz packages that result from baking agents. "
                        "Note: In order to avoid name changes in packages, the uncompressed TAR "
                        "packages also have a suffix of .tar.gz. Technically, they are compressed "
                        "using gzip with a compression level of 0."
                        "It's not recommended to activate compression unless you want to deploy "
                        "large files resulting from custom files or your own bakery plugins. "
                        "All large files (larger than a few kb, mainly the agent updater and the "
                        "agent controller) provided by Checkmk are precompressed and won't benefit "
                        "from enabling compression."
                    ),
                    choices=[
                        (True, _("Apply compression")),
                        (False, _("Don't apply compression")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsGenericOptions,
        name=RuleGroup.AgentConfig("bakery_packages"),
        match_type="dict",
        valuespec=_valuespec_bakery_packages,
    )
)
