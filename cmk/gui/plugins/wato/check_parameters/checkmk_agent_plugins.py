#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.version import parse_check_mk_version

from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, RegExp, TextInput, Tuple


def _validate_version(value: str, varprefix: str) -> None:
    try:
        parse_check_mk_version(value)
    except (ValueError, TypeError, KeyError):
        raise MKUserError(varprefix, _("Can't parse version %r") % value)


def _parameter_valuespec_checkmk_agent_plugins():
    return Dictionary(
        elements=[
            (
                "min_versions",
                Tuple(
                    title=_("Required minimal versions"),
                    help=_(
                        "You can configure lower thresholds for the versions of the currently "
                        "deployed agent plugins and local checks."
                    ),
                    elements=[
                        TextInput(title=_("Warning at"), validate=_validate_version),
                        TextInput(title=_("Critical at"), validate=_validate_version),
                    ],
                ),
            ),
            (
                "exclude_pattern",
                RegExp(
                    title=_("Regular expression to exclude plugins"),
                    mode=RegExp.infix,
                    help=_(
                        "Plugins or local checks matching this pattern will be excluded from the "
                        "comparison with the specified required versions."
                    ),
                ),
            ),
        ],
        help=_('This ruleset is deprecated. Please use the ruleset <i>"%s"</i> instead.')
        % _("Checkmk Agent installation auditing"),
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="checkmk_agent_plugins",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_checkmk_agent_plugins,
        title=lambda: _("Checkmk agent plugins") + " - " + _("Deprecated"),
        # only present during 2.1.0b1. remove in 2.2!
        is_deprecated=True,
    )
)
