#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    HostRulespec,
    rulespec_registry,
    RulespecGroupCheckParametersDiscovery,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.valuespec import (
    Age,
    Checkbox,
    Dictionary,
    ListOf,
    MonitoringState,
    TextInput,
    Tuple,
)

DEFAULT_TRANSFER_STATE = {
    "aborted": 2,
    "failed": 2,
    "hard_aborted": 2,
    "queued": 0,
    "success": 0,
    "transferring": 0,
}

DEFAULT_UNHEALTHY_STATE = 2


def _transfer_state_valuespec() -> Dictionary:
    titles = {
        "success": _("Success"),
        "transferring": _("Transferring"),
        "queued": _("Queued"),
        "aborted": _("Aborted"),
        "hard_aborted": _("Hard aborted"),
        "failed": _("Failed"),
    }
    return Dictionary(
        title=_("Monitoring state per transfer state"),
        help=_(
            "Map the transfer state reported by the SnapMirror relationship to a monitoring state."
        ),
        elements=[
            (
                transfer_state,
                MonitoringState(
                    title=title,
                    default_value=DEFAULT_TRANSFER_STATE[transfer_state],
                ),
            )
            for transfer_state, title in titles.items()
        ],
        optional_keys=False,
    )


def _parameter_valuespec_snapvault() -> Dictionary:
    return Dictionary(
        elements=[
            (
                "lag_time",
                Tuple(
                    title=_("Default levels"),
                    elements=[
                        Age(title=_("Warning at")),
                        Age(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "policy_lag_time",
                ListOf(
                    valuespec=Tuple(
                        orientation="horizontal",
                        elements=[
                            TextInput(title=_("Policy name")),
                            Tuple(
                                title=_("Maximum age"),
                                elements=[
                                    Age(title=_("Warning at")),
                                    Age(title=_("Critical at")),
                                ],
                            ),
                        ],
                    ),
                    title=_("Policy-specific levels (cluster mode only)"),
                    help=_(
                        "Here, you can specify levels for different policies which overrule the levels "
                        "from the <i>Default levels</i> parameter. This setting only works in NetApp Clustermode setups."
                    ),
                    allow_empty=False,
                ),
            ),
            ("transfer_state", _transfer_state_valuespec()),
            (
                "unhealthy_state",
                MonitoringState(
                    title=_("State if the relationship is unhealthy"),
                    help=_(
                        "ONTAP marks a SnapMirror relationship as unhealthy, for example when "
                        "an update failed. The reasons reported by ONTAP are shown in the "
                        "service summary. Older ONTAP versions may not report the health."
                    ),
                    default_value=DEFAULT_UNHEALTHY_STATE,
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="snapvault",
        group=RulespecGroupCheckParametersStorage,
        item_spec=lambda: TextInput(title=_("Destination"), allow_empty=False),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_snapvault,
        title=lambda: _("NetApp SnapVault / SnapMirror"),
    )
)


def _discovery_valuespec_snapvault():
    return Dictionary(
        elements=[
            (
                "exclude_destination_vserver",
                Checkbox(
                    title=_("Exclude destination vserver"),
                    help=_(
                        "Only applicable to clustermode installations. "
                        "The service name of snapvault services is composed of the "
                        "destination vserver (SVM) and the destination volume by default. Check "
                        "this box if you would like to use the destination volume as the "
                        "service name on its own. "
                        "Please be advised that this may lead to a service name that is "
                        "not unique, resulting in some services, which are not shown!"
                    ),
                ),
            ),
        ],
        title=_("NetApp snapvault discovery"),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersDiscovery,
        match_type="list",
        name="discovery_snapvault",
        valuespec=_discovery_valuespec_snapvault,
    )
)
