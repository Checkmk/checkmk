#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.utils.rule_specs.legacy_converter import convert_dictionary_formspec_to_valuespec
from cmk.gui.watolib.notification_parameter import (
    NotificationParameter,
    NotificationParameterRegistry,
)

from . import _cisco_webex_teams as cisco_webex_teams
from . import _ilert as ilert
from . import _jira_issues as jira_issues
from . import _mail as mail
from . import _ms_teams as ms_teams
from . import _opsgenie_issues as opsgenie_issues
from . import _pagerduty as pagerduty
from . import _pushover as pushover
from . import _servicenow as servicenow
from . import _signl4 as signl4
from . import _slack as slack
from . import _sms_api as sms_api
from . import _spectrum as spectrum
from . import _victorops as victorops


def register(notification_parameter_registry: NotificationParameterRegistry) -> None:
    notification_parameter_registry.register(
        NotificationParameter(
            ident="slack",
            spec=lambda: convert_dictionary_formspec_to_valuespec(slack.form_spec),
            form_spec=slack.form_spec,
        )
    )
    notification_parameter_registry.register(
        NotificationParameter(
            ident="cisco_webex_teams",
            spec=lambda: convert_dictionary_formspec_to_valuespec(cisco_webex_teams.form_spec),
            form_spec=cisco_webex_teams.form_spec,
        )
    )
    notification_parameter_registry.register(
        NotificationParameter(
            ident="victorops",
            spec=lambda: convert_dictionary_formspec_to_valuespec(victorops.form_spec),
            form_spec=victorops.form_spec,
        )
    )
    notification_parameter_registry.register(
        NotificationParameter(
            ident="pagerduty",
            spec=lambda: convert_dictionary_formspec_to_valuespec(pagerduty.form_spec),
            form_spec=pagerduty.form_spec,
        )
    )
    notification_parameter_registry.register(
        NotificationParameter(
            ident="signl4",
            spec=lambda: convert_dictionary_formspec_to_valuespec(signl4.form_spec),
            form_spec=signl4.form_spec,
        )
    )
    notification_parameter_registry.register(
        NotificationParameter(
            ident="asciimail",
            spec=lambda: convert_dictionary_formspec_to_valuespec(mail.form_spec_asciimail),
            form_spec=mail.form_spec_asciimail,
        )
    )
    notification_parameter_registry.register(
        NotificationParameter(
            ident="ilert",
            spec=lambda: convert_dictionary_formspec_to_valuespec(ilert.form_spec),
            form_spec=ilert.form_spec,
        )
    )
    notification_parameter_registry.register(
        NotificationParameter(
            ident="jira_issues",
            spec=lambda: convert_dictionary_formspec_to_valuespec(jira_issues.form_spec),
            form_spec=jira_issues.form_spec,
        )
    )
    notification_parameter_registry.register(
        NotificationParameter(
            ident="servicenow",
            spec=lambda: convert_dictionary_formspec_to_valuespec(servicenow.form_spec),
            form_spec=servicenow.form_spec,
        )
    )
    notification_parameter_registry.register(
        NotificationParameter(
            ident="opsgenie_issues",
            spec=lambda: convert_dictionary_formspec_to_valuespec(opsgenie_issues.form_spec),
            form_spec=opsgenie_issues.form_spec,
        )
    )
    notification_parameter_registry.register(
        NotificationParameter(
            ident="spectrum",
            spec=lambda: convert_dictionary_formspec_to_valuespec(spectrum.form_spec),
            form_spec=spectrum.form_spec,
        )
    )
    notification_parameter_registry.register(
        NotificationParameter(
            ident="pushover",
            spec=lambda: convert_dictionary_formspec_to_valuespec(pushover.form_spec),
            form_spec=pushover.form_spec,
        )
    )
    notification_parameter_registry.register(
        NotificationParameter(
            ident="sms_api",
            spec=lambda: convert_dictionary_formspec_to_valuespec(sms_api.form_spec),
            form_spec=sms_api.form_spec,
        )
    )
    notification_parameter_registry.register(
        NotificationParameter(
            ident="msteams",
            spec=lambda: convert_dictionary_formspec_to_valuespec(ms_teams.form_spec),
            form_spec=ms_teams.form_spec,
        )
    )
