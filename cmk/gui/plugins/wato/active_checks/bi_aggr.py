#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.plugins.wato.active_checks.common import RulespecGroupIntegrateOtherServices
from cmk.gui.plugins.wato.utils import HostRulespec, IndividualOrStoredPassword, rulespec_registry
from cmk.gui.valuespec import (
    CascadingDropdown,
    Checkbox,
    Dictionary,
    DropdownChoice,
    Integer,
    TextInput,
    Transform,
    Tuple,
)


def _active_checks_bi_aggr_transform_from_disk(value):
    if isinstance(value, dict):
        return value
    new_value = {}
    new_value["base_url"] = value[0]
    new_value["aggregation_name"] = value[1]
    new_value["optional"] = value[4]
    new_value["credentials"] = ("configured", (value[2], value[3]))
    return new_value


def _valuespec_active_checks_bi_aggr():
    return Transform(
        valuespec=Dictionary(
            title=_("Check State of BI Aggregation"),
            help=_(
                "Connect to the local or a remote monitoring host, which uses Check_MK BI to aggregate "
                "several states to a single BI aggregation, which you want to show up as a single "
                "service."
            ),
            elements=[
                (
                    "base_url",
                    TextInput(
                        title=_("Base URL (OMD Site)"),
                        help=_(
                            "The base URL to the monitoring instance. For example <tt>http://mycheckmk01/mysite</tt>. "
                            "You can use macros like <tt>$HOSTADDRESS$</tt> and <tt>$HOSTNAME$</tt> within this URL to "
                            "make them be replaced by the hosts values."
                        ),
                        size=60,
                        allow_empty=False,
                    ),
                ),
                (
                    "aggregation_name",
                    TextInput(
                        title=_("Aggregation Name"),
                        help=_(
                            "The name of the aggregation to fetch. It will be added to the service description. You can "
                            "use macros like <tt>$HOSTADDRESS$</tt> and <tt>$HOSTNAME$</tt> within this parameter to "
                            "make them be replaced by the hosts values. The aggregation name is the title in the "
                            "top-level-rule of your BI pack."
                        ),
                        allow_empty=False,
                    ),
                ),
                (
                    "credentials",
                    CascadingDropdown(
                        choices=[
                            ("automation", _("Use the credentials of the 'automation' user")),
                            (
                                "configured",
                                _("Use the following credentials"),
                                Tuple(
                                    elements=[
                                        TextInput(
                                            title=_("Automation Username"),
                                            allow_empty=True,
                                            help=_(
                                                "The name of the automation account to use for fetching the BI aggregation via HTTP. Note: You may "
                                                "also set credentials of a standard user account, though it is disadvised. "
                                                "Using the credentials of a standard user also requires a valid authentication method set in the "
                                                "optional parameters."
                                            ),
                                        ),
                                        IndividualOrStoredPassword(
                                            title=_("Automation Secret"),
                                            help=_(
                                                "Valid automation secret for the automation user"
                                            ),
                                            allow_empty=False,
                                        ),
                                    ]
                                ),
                            ),
                        ],
                        help=_(
                            "Here you can configured the credentials to be used. Keep in mind that the <tt>automation</tt> user need "
                            "to exist if you choose this option"
                        ),
                        title=_("Login credentials"),
                        default_value="automation",
                    ),
                ),
                (
                    "optional",
                    Dictionary(
                        title=_("Optional parameters"),
                        elements=[
                            (
                                "auth_mode",
                                DropdownChoice(
                                    title=_("Authentication Mode"),
                                    default_value="header",
                                    choices=[
                                        ("header", _("Authorization Header")),
                                        ("basic", _("HTTP Basic")),
                                        ("digest", _("HTTP Digest")),
                                        ("kerberos", _("Kerberos")),
                                    ],
                                    deprecated_choices=("cookie",),
                                    invalid_choice_error=_(
                                        "The specified choice is no longer available. "
                                        "Please use another, like 'header' instead."
                                    ),
                                ),
                            ),
                            (
                                "timeout",
                                Integer(
                                    title=_("Seconds before connection times out"),
                                    unit=_("sec"),
                                    default_value=60,
                                ),
                            ),
                            (
                                "in_downtime",
                                DropdownChoice(
                                    title=_("State, if BI aggregate is in scheduled downtime"),
                                    choices=[
                                        (None, _("Use normal state, ignore downtime")),
                                        ("ok", _("Force to be OK")),
                                        ("warn", _("Force to be WARN, if aggregate is not OK")),
                                    ],
                                ),
                            ),
                            (
                                "acknowledged",
                                DropdownChoice(
                                    title=_("State, if BI aggregate is acknowledged"),
                                    choices=[
                                        (None, _("Use normal state, ignore acknowledgement")),
                                        ("ok", _("Force to be OK")),
                                        ("warn", _("Force to be WARN, if aggregate is not OK")),
                                    ],
                                ),
                            ),
                            (
                                "track_downtimes",
                                Checkbox(
                                    title=_("Track downtimes"),
                                    label=_("Automatically track downtimes of aggregation"),
                                    help=_(
                                        "If this is active, the check will automatically go into downtime "
                                        "whenever the aggregation does. This downtime is also cleaned up "
                                        "automatically when the aggregation leaves downtime. "
                                        "Downtimes you set manually for this check are unaffected."
                                    ),
                                ),
                            ),
                        ],
                    ),
                ),
            ],
            optional_keys=False,
        ),
        forth=_active_checks_bi_aggr_transform_from_disk,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupIntegrateOtherServices,
        match_type="all",
        name="active_checks:bi_aggr",
        valuespec=_valuespec_active_checks_bi_aggr,
    )
)
