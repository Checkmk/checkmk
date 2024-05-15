#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.utils.rulesets.definition import RuleGroup

from cmk.gui.i18n import _
from cmk.gui.valuespec import Dictionary, HTTPUrl, TextInput
from cmk.gui.wato import (
    MigrateToIndividualOrStoredPassword,
    RulespecGroupDatasourceProgramsHardware,
)
from cmk.gui.watolib.rulespecs import HostRulespec, Rulespec, rulespec_registry


def _factory_default_special_agents_hivemanager_ng():
    # No default, do not use setting if no rule matches
    return Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_hivemanager_ng():
    return Dictionary(
        title=_("Aerohive HiveManager NG"),
        help=_("Activate monitoring of the HiveManagerNG cloud."),
        elements=[
            (
                "url",
                HTTPUrl(
                    title=_("URL to HiveManagerNG, e.g. https://cloud.aerohive.com"),
                    allow_empty=False,
                ),
            ),
            (
                "vhm_id",
                TextInput(
                    title=_("Numerical ID of the VHM, e.g. 102"),
                    allow_empty=False,
                ),
            ),
            (
                "api_token",
                TextInput(
                    title=_("API Access Token"),
                    size=64,
                    allow_empty=False,
                ),
            ),
            (
                "client_id",
                TextInput(
                    title=_("Client ID"),
                    allow_empty=False,
                ),
            ),
            (
                "client_secret",
                MigrateToIndividualOrStoredPassword(
                    title=_("Client secret"),
                    allow_empty=False,
                ),
            ),
            (
                "redirect_url",
                HTTPUrl(
                    title=_("Redirect URL (has to be https)"),
                    allow_empty=False,
                ),
            ),
        ],
        optional_keys=False,
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_hivemanager_ng(),
        group=RulespecGroupDatasourceProgramsHardware,
        name=RuleGroup.SpecialAgents("hivemanager_ng"),
        valuespec=_valuespec_special_agents_hivemanager_ng,
    )
)
