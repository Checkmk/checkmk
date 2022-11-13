#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, DropdownChoice, ListOfNetworkPorts, ListOfStrings, Migrate


def _parameter_valuespec_sshd_config() -> Migrate:
    return Migrate(
        migrate=lambda p: {k.lower(): v for k, v in p.items()},
        valuespec=Dictionary(
            elements=[
                (
                    "permitrootlogin",
                    DropdownChoice(
                        title=_("Permit root login"),
                        choices=[
                            ("yes", _("yes")),
                            ("key-based", _("without-password/prohibit-password (Key based)")),
                            ("forced-commands-only", _("forced-commands-only")),
                            ("no", _("no")),
                        ],
                        default_value="key-based",
                    ),
                ),
                (
                    "protocol",
                    DropdownChoice(
                        title=_("Allowed protocols"),
                        choices=[
                            ("1", _("Version 1")),
                            ("2", _("Version 2")),
                            ("1,2", _("Version 1 and 2")),
                        ],
                        default_value="2",
                    ),
                ),
                ("port", ListOfNetworkPorts(title=_("Allowed Ports"), default_value=[22])),
                (
                    "passwordauthentication",
                    DropdownChoice(
                        title=_("Allow password authentication"),
                        help=_("Specifies whether password authentication is allowed"),
                        choices=[
                            ("yes", _("Yes")),
                            ("no", _("No")),
                        ],
                        default_value="no",
                    ),
                ),
                (
                    "permitemptypasswords",
                    DropdownChoice(
                        title=_("Permit empty passwords"),
                        help=_(
                            "If password authentication is used this option "
                            "specifies wheter the server allows login to accounts "
                            "with empty passwords"
                        ),
                        choices=[
                            ("yes", _("Yes")),
                            ("no", _("No")),
                        ],
                        default_value="no",
                    ),
                ),
                (
                    "challengeresponseauthentication",
                    DropdownChoice(
                        title=_("Allow challenge-response authentication"),
                        choices=[
                            ("yes", _("Yes")),
                            ("no", _("No")),
                        ],
                        default_value="no",
                    ),
                ),
                (
                    "x11forwarding",
                    DropdownChoice(
                        title=_("Permit X11 forwarding"),
                        choices=[
                            ("yes", _("Yes")),
                            ("no", _("No")),
                        ],
                        default_value="no",
                    ),
                ),
                (
                    "usepam",
                    DropdownChoice(
                        title=_("Use pluggable authentication module"),
                        choices=[
                            ("yes", _("Yes")),
                            ("no", _("No")),
                        ],
                        default_value="no",
                    ),
                ),
                (
                    "ciphers",
                    ListOfStrings(
                        title=_("Allowed Ciphers"),
                        orientation="horizontal",
                    ),
                ),
            ],
        ),
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="sshd_config",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_sshd_config,
        title=lambda: _("SSH daemon configuration"),
    )
)
