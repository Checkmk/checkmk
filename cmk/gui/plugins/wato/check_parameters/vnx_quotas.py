#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    ListOf,
    Tuple,
    TextAscii,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersDiscovery,
    rulespec_registry,
    HostRulespec,
)


def _valuespec_discovery_rules_vnx_quotas():
    return Dictionary(
        title=_("VNX quotas and filesystems discovery"),
        elements=[
            ("dms_names",
             ListOf(
                 Tuple(elements=[
                     TextAscii(title=_("Exact RWVDMS name or regex")),
                     TextAscii(title=_("Substitution")),
                 ]),
                 title=_("Map RWVDMS names"),
                 help=_("Here you are able to substitute the RWVDMS name. Either you "
                        "determine an exact name and the related subsitution or you "
                        "enter a regex beginning with '~'. The regexes must include "
                        "groups marked by '(...)' which will be substituted."),
             )),
            ("mp_names",
             ListOf(
                 Tuple(elements=[
                     TextAscii(title=_("Exact mount point name or regex")),
                     TextAscii(title=_("Substitution")),
                 ]),
                 title=_("Map mount point names"),
                 help=_("Here you are able to substitute the filesystem name. Either you "
                        "determine an exact name and the related subsitution or you "
                        "enter a regex beginning with '~'. The regexes must include "
                        "groups marked by '(...)' which will be substituted."),
             )),
        ],
        optional_keys=[],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersDiscovery,
        match_type="dict",
        name="discovery_rules_vnx_quotas",
        valuespec=_valuespec_discovery_rules_vnx_quotas,
    ))
