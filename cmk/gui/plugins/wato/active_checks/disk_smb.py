#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.active_checks.common import RulespecGroupActiveChecks
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import (
    CascadingDropdown,
    Dictionary,
    HostAddress,
    Migrate,
    NetworkPort,
    Password,
    Percentage,
    TextInput,
    Tuple,
)


def _migrate(params: dict[str, Any]) -> Mapping[str, Any]:
    if "host" not in params:
        # Up to 2.1.0p31 and 2.2.0p5 the host was not required
        params["host"] = "use_parent_host"

    return params


def _valuespec_active_checks_disk_smb() -> Migrate:
    return Migrate(
        valuespec=Dictionary(
            title=_("Check SMB share access"),
            help=_(
                "This ruleset helps you to configure the classical Nagios "
                "plugin <tt>check_disk_smb</tt> that checks the access to "
                "filesystem shares that are exported via SMB/CIFS."
            ),
            elements=[
                (
                    "share",
                    TextInput(
                        title=_("SMB share to check"),
                        help=_(
                            "Enter the plain name of the share only, e. g. <tt>iso</tt>, <b>not</b> "
                            "the full UNC like <tt>\\\\servername\\iso</tt>"
                        ),
                        size=32,
                        allow_empty=False,
                    ),
                ),
                (
                    "workgroup",
                    TextInput(
                        title=_("Workgroup"),
                        help=_("Workgroup or domain used (defaults to <tt>WORKGROUP</tt>)"),
                        size=32,
                        allow_empty=False,
                    ),
                ),
                (
                    "host",
                    CascadingDropdown(
                        title=_("NetBIOS name of the server"),
                        help=_(
                            "Choose, whether you want to use the parent host information for the NetBIOS server name,"
                            " or if you want to specify one."
                        ),
                        choices=[
                            (
                                "use_parent_host",
                                _("Use parent host information for the NetBIOS server name"),
                            ),
                            (
                                "define_host",
                                _("Define name of NetBIOS server"),
                                HostAddress(
                                    title="Define name of NetBIOS server",
                                    allow_empty=False,
                                    help=_("You can specify the NetBIOS server name."),
                                    size=32,
                                ),
                            ),
                        ],
                    ),
                ),
                (
                    "ip_address",
                    HostAddress(
                        title=_("IP Address"),
                        help=_(
                            "IP address of SMB share host (only necessary if SMB share host is in another network)"
                        ),
                        size=32,
                        allow_host_name=False,
                        allow_empty=False,
                    ),
                ),
                (
                    "port",
                    NetworkPort(
                        title=_("TCP Port"),
                        help=_("TCP port number to connect to. Usually either 139 or 445."),
                        default_value=445,
                        minvalue=1,
                        maxvalue=65535,
                    ),
                ),
                (
                    "levels",
                    Tuple(
                        title=_("Levels for used disk space"),
                        elements=[
                            Percentage(
                                title=_("Warning if above"), default_value=85, allow_int=True
                            ),
                            Percentage(
                                title=_("Critical if above"), default_value=95, allow_int=True
                            ),
                        ],
                    ),
                ),
                (
                    "auth",
                    Tuple(
                        title=_("Authorization"),
                        elements=[
                            TextInput(title=_("Username"), allow_empty=False, size=24),
                            Password(title=_("Password"), allow_empty=False, size=12),
                        ],
                    ),
                ),
            ],
            required_keys=["share", "levels", "host"],
        ),
        migrate=_migrate,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupActiveChecks,
        match_type="all",
        name="active_checks:disk_smb",
        valuespec=_valuespec_active_checks_disk_smb,
    )
)
