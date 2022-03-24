#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import cmk.gui.watolib as watolib
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupDatasourceProgramsHardware
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Dictionary, HTTPUrl, Password, TextInput


def _factory_default_special_agents_hivemanager_ng():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


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
                Password(
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
        name="special_agents:hivemanager_ng",
        valuespec=_valuespec_special_agents_hivemanager_ng,
    )
)
