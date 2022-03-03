#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Union

from cmk.utils.version import parse_check_mk_version

from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import (
    CascadingDropdown,
    Dictionary,
    FixedValue,
    MonitoringState,
    RegExp,
    TextInput,
    Transform,
    Tuple,
)


def _validate_version(value: str, varprefix: str) -> None:
    try:
        parse_check_mk_version(value)
    except (ValueError, TypeError, KeyError):
        raise MKUserError(varprefix, _("Can't parse version %r") % value)


def _transform_version_spec(
    param: Union[str, tuple[str, str], tuple[str, dict[str, str]]]
) -> tuple[str, dict[str, str]]:
    """
    >>> _transform_version_spec(('at_least', {'build': '1.1.1'}))
    ('at_least', {'build': '1.1.1'})
    >>> _transform_version_spec(("specific", "2.1.0b2"))
    ('specific', {'literal': '2.1.0b2'})
    >>> _transform_version_spec("1.2.3")
    ('specific', {'literal': '1.2.3'})
    >>> _transform_version_spec("site")
    ('site', {})
    >>> _transform_version_spec("ignore")
    ('ignore', {})

    """
    if isinstance(param, tuple):
        type_, spec = param
        if isinstance(spec, dict):
            return type_, spec
        return "specific", {"literal": str(spec)}

    if param in ("ignore", "site"):
        return param, {}
    return "specific", {"literal": param}


def _parameter_valuespec_checkmk_agent():
    return Dictionary(
        elements=[
            (
                "agent_version",
                Transform(
                    CascadingDropdown(
                        title=_("Check for correct version of Checkmk agent"),
                        help=_(
                            "Here you can make sure that all of your Check_MK agents are running"
                            " one specific version. Agents running "
                            " a different version return a non-OK state."
                        ),
                        choices=[
                            (
                                "ignore",
                                _("Ignore the version"),
                                FixedValue(value={}, totext=""),
                            ),
                            (
                                "site",
                                _("Same version as the monitoring site"),
                                FixedValue(value={}, totext=""),
                            ),
                            (
                                "specific",
                                _("Specific version"),
                                Dictionary(
                                    elements=[
                                        (
                                            "literal",
                                            TextInput(allow_empty=False, title=_("Expected")),
                                        ),
                                    ],
                                    optional_keys=[],
                                ),
                            ),
                            (
                                "at_least",
                                _("At least"),
                                Dictionary(
                                    elements=[
                                        (
                                            "release",
                                            TextInput(
                                                title=_("Official Release version"),
                                                allow_empty=False,
                                            ),
                                        ),
                                        (
                                            "daily_build",
                                            TextInput(
                                                title=_("Daily build"),
                                                allow_empty=False,
                                            ),
                                        ),
                                    ]
                                ),
                            ),
                        ],
                        default_value=("ignore", {}),
                    ),
                    # In the past, this was a OptionalDropdownChoice() which values could be strings:
                    # ignore, site or a custom string representing a version number.
                    forth=_transform_version_spec,
                ),
            ),
            (
                "error_deployment_globally_disabled",
                MonitoringState(
                    title=_("State if agent deployment is globally disabled"), default_value=1
                ),
            ),
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
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="agent_update",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_checkmk_agent,
        title=lambda: _("Checkmk Agent"),
    )
)
