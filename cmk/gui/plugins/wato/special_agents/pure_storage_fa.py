#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupVMCloudContainer
from cmk.gui.plugins.wato.special_agents.common_tls_verification import tls_verify_options
from cmk.gui.plugins.wato.utils import HostRulespec, IndividualOrStoredPassword, rulespec_registry
from cmk.gui.valuespec import Dictionary, Integer


def _valuespec_special_agents_pure_storage_fa() -> Dictionary:
    return Dictionary(
        title=_("Pure Storage FlashArray"),
        elements=[
            (
                "api_token",
                IndividualOrStoredPassword(
                    title=_("API token"),
                    allow_empty=False,
                    size=36,
                    help=_(
                        "Generate the API token through the Purity user interface"
                        " (System > Users > Create API Token)"
                        " or through the Purity command line interface"
                        " (pureadmin create --api-token)"
                    ),
                ),
            ),
            tls_verify_options(),
            ("timeout", Integer(title=_("Timeout"), minvalue=1, default_value=5)),
        ],
        optional_keys=["timeout"],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupVMCloudContainer,
        name="special_agents:pure_storage_fa",
        title=lambda: _("Pure Storage FlashArray"),
        valuespec=_valuespec_special_agents_pure_storage_fa,
    )
)
