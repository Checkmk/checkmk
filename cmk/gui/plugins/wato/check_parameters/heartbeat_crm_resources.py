#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.valuespec import Alternative, Dictionary, FixedValue, Migrate, TextInput


def _migrate_opt_string(
    parameters: Mapping[str, str | None] | str | None
) -> Mapping[str, str | None]:
    """
    >>> _migrate_opt_string(None)
    {'expected_node': None}
    >>> _migrate_opt_string("foobar")
    {'expected_node': 'foobar'}
    >>> _migrate_opt_string({'expected_node': 'mooo'})
    {'expected_node': 'mooo'}
    """
    if parameters is None or isinstance(parameters, str):
        return {"expected_node": parameters}
    return parameters


def _item_spec_heartbeat_crm_resources():
    return TextInput(
        title=_("Resource Name"),
        help=_("The name of the cluster resource as shown in the service description."),
        allow_empty=False,
    )


def _parameter_valuespec_heartbeat_crm_resources():
    return Migrate(
        Dictionary(
            elements=[
                (
                    "expected_node",
                    Alternative(
                        title=_("Expected node"),
                        help=_("The hostname of the expected node to hold this resource."),
                        elements=[
                            FixedValue(value=None, totext="", title=_("Do not check the node")),
                            TextInput(allow_empty=False, title=_("Expected node")),
                        ],
                    ),
                ),
            ],
        ),
        migrate=_migrate_opt_string,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="heartbeat_crm_resources",
        group=RulespecGroupCheckParametersStorage,
        item_spec=_item_spec_heartbeat_crm_resources,
        parameter_valuespec=_parameter_valuespec_heartbeat_crm_resources,
        title=lambda: _("Heartbeat CRM resource status"),
    )
)
