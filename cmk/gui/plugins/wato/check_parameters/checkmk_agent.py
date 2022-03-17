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
                    valuespec=CascadingDropdown(
                        title=_("Check version of Checkmk agent"),
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
                "agent_version_missmatch",
                MonitoringState(default_value=1, title=_("State in case of wrong agent version")),
            ),
            (
                "restricted_address_mismatch",
                MonitoringState(
                    title=_("State in case of restricted address mismatch"),
                    help=_(
                        "If a Checkmk site is updated to a newer version but the agents of some "
                        "hosts are not, then the warning <i>Unexpected allowed IP ranges</i> may "
                        "be displayed in the details of the <i>Check_MK</i> service and the "
                        "service state changes to <i>WARN</i> (by default).<br>"
                        "With this setting you can overwrite the default service state. This will help "
                        "you to reduce above warnings during the update process of your Checkmk sites "
                        "and agents."
                    ),
                    default_value=1,
                ),
            ),
            (
                "legacy_pull_mode",
                MonitoringState(
                    title=_("State in case of available but not enabled TLS"),
                    help=_(
                        "New agent installations that support TLS will refuse to send any data "
                        "without TLS. However, if you upgrade an existing installation, the "
                        "old transport mode (with optional encryption) will continue to work, "
                        "to ease migration."
                    )
                    + "<br>"
                    + _(
                        "It is recommended to enable TLS as soon as possible by running the "
                        "`register` command of the `cmk-agent-ctl` utility on the monitored "
                        "host."
                    )
                    + "<br>"
                    + _(
                        "However, if that is not feasable, you can configure the legacy mode "
                        "(which may or <b>may not</b> include encryption) to be OK using this "
                        "setting. Note that this option may become ineffective in a future "
                        "Checkmk version."
                    ),
                    default_value=1,
                ),
            ),
            (
                "error_deployment_globally_disabled",
                MonitoringState(
                    title=_("State if agent deployment is globally disabled"), default_value=1
                ),
            ),
            (
                "versions_plugins",
                Dictionary(
                    title=_("Agent plugins: versions"),
                    optional_keys=False,
                    elements=[
                        (
                            "min_versions",
                            Tuple(
                                title=_("Required minimal versions"),
                                help=_(
                                    "You can configure lower thresholds for the versions of the "
                                    "currently deployed agent plugins."
                                ),
                                elements=[
                                    TextInput(title=_("Warning at"), validate=_validate_version),
                                    TextInput(title=_("Critical at"), validate=_validate_version),
                                ],
                            ),
                        ),
                        (
                            "mon_state_unparsable",
                            MonitoringState(
                                title=_("Monitoring state in case of version parsing failure"),
                                help=_(
                                    "The monitoring state in case the version of an agent plugin "
                                    "is unparsable."
                                ),
                                default_value=3,
                            ),
                        ),
                    ],
                ),
            ),
            (
                "versions_lchecks",
                Dictionary(
                    title=_("Local checks: versions"),
                    optional_keys=False,
                    elements=[
                        (
                            "min_versions",
                            Tuple(
                                title=_("Required minimal versions"),
                                help=_(
                                    "You can configure lower thresholds for the versions of the "
                                    "currently deployed local checks."
                                ),
                                elements=[
                                    TextInput(title=_("Warning at"), validate=_validate_version),
                                    TextInput(title=_("Critical at"), validate=_validate_version),
                                ],
                            ),
                        ),
                        (
                            "mon_state_unparsable",
                            MonitoringState(
                                title=_("Monitoring state in case of version parsing failure"),
                                help=_(
                                    "The monitoring state in case the version of a local check is "
                                    "unparsable."
                                ),
                                default_value=3,
                            ),
                        ),
                    ],
                ),
            ),
            (
                "exclude_pattern_plugins",
                RegExp(
                    title=_("Agent plugins: Regular expression to exclude plugins"),
                    mode=RegExp.infix,
                    help=_(
                        "Plugins matching this pattern will be excluded from the comparison with "
                        "the required versions specified in '%s' and from the duplicates check."
                    )
                    % _("Agent plugins: versions"),
                ),
            ),
            (
                "exclude_pattern_lchecks",
                RegExp(
                    title=_("Local checks: Regular expression to exclude files"),
                    mode=RegExp.infix,
                    help=_(
                        "Local checks matching this pattern will be excluded from the comparison "
                        "with the required versions specified in '%s' and from the duplicates check."
                    )
                    % _("Local checks: versions"),
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
        title=lambda: _("Checkmk Agent installation auditing"),
    )
)
