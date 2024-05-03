#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.rulesets.definition import RuleGroup

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.utils.urls import DocReference
from cmk.gui.valuespec import Dictionary, ListChoice
from cmk.gui.wato import RulespecGroupVMCloudContainer

# TODO agent rule will be migrated to plugins.aws, this will remove the module layer violation
from cmk.plugins.aws.lib import aws_region_to_monitor  # pylint: disable=cmk-module-layer-violation


def _valuespec_special_agents_aws_status() -> Dictionary:
    return Dictionary(
        elements=[
            (
                "regions",
                ListChoice(
                    title=_("Regions to monitor"),
                    choices=aws_region_to_monitor(),
                ),
            ),
        ],
        required_keys=["regions"],
        title=_("Amazon Web Services (AWS) Status"),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupVMCloudContainer,
        name=RuleGroup.SpecialAgents("aws_status"),
        valuespec=_valuespec_special_agents_aws_status,
        doc_references={DocReference.AWS: _("Monitoring Amazon Web Services (AWS)")},
    )
)
