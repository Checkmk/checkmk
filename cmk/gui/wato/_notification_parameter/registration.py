#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.watolib.notification_parameter import NotificationParameterRegistry

from ._cisco_webex_teams import NotificationParameterCiscoWebexTeams
from ._ilert import NotificationParameterILert
from ._jira_issues import NotificationParameterJiraIssues
from ._mail import NotificationParameterASCIIMail
from ._ms_teams import NotificationParameterMsTeams
from ._opsgenie_issues import NotificationParameterOpsgenie
from ._pagerduty import NotificationParameterPagerDuty
from ._pushover import NotificationParameterPushover
from ._servicenow import NotificationParameterServiceNow
from ._signl4 import NotificationParameterSIGNL4
from ._slack import NotificationParameterSlack
from ._sms_api import NotificationParameterSMSviaIP
from ._spectrum import NotificationParameterSpectrum
from ._victorops import NotificationParameterVictorOPS


def register(notification_parameter_registry: NotificationParameterRegistry) -> None:
    notification_parameter_registry.register(NotificationParameterSlack)
    notification_parameter_registry.register(NotificationParameterCiscoWebexTeams)
    notification_parameter_registry.register(NotificationParameterVictorOPS)
    notification_parameter_registry.register(NotificationParameterPagerDuty)
    notification_parameter_registry.register(NotificationParameterSIGNL4)
    notification_parameter_registry.register(NotificationParameterASCIIMail)
    notification_parameter_registry.register(NotificationParameterILert)
    notification_parameter_registry.register(NotificationParameterJiraIssues)
    notification_parameter_registry.register(NotificationParameterServiceNow)
    notification_parameter_registry.register(NotificationParameterOpsgenie)
    notification_parameter_registry.register(NotificationParameterSpectrum)
    notification_parameter_registry.register(NotificationParameterPushover)
    notification_parameter_registry.register(NotificationParameterSMSviaIP)
    notification_parameter_registry.register(NotificationParameterMsTeams)
