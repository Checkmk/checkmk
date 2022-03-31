#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import cmk.gui.watolib as watolib
from cmk.gui.i18n import _
from cmk.gui.mkeventd import service_levels, syslog_facilities, syslog_priorities
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupDatasourceProgramsApps
from cmk.gui.plugins.wato.utils import (
    HostRulespec,
    HTTPProxyReference,
    IndividualOrStoredPassword,
    rulespec_registry,
)
from cmk.gui.valuespec import Age, Dictionary, DropdownChoice, HTTPUrl, ListOfStrings, RegExp


def _valuespec_special_agents_datadog() -> Dictionary:
    return Dictionary(
        title=_("Datadog"),
        help=_("Configuration of the Datadog special agent."),
        elements=[
            (
                "instance",
                Dictionary(
                    title=_("Datadog instance"),
                    help=_("Provide API host and credentials for your Datadog instance here."),
                    elements=[
                        (
                            "api_key",
                            IndividualOrStoredPassword(
                                title=_("API Key"),
                                allow_empty=False,
                            ),
                        ),
                        (
                            "app_key",
                            IndividualOrStoredPassword(
                                title=_("Application Key"),
                                allow_empty=False,
                            ),
                        ),
                        (
                            "api_host",
                            HTTPUrl(
                                title=_("API host"),
                                default_value="api.datadoghq.eu",
                            ),
                        ),
                    ],
                    optional_keys=False,
                ),
            ),
            (
                "proxy",
                HTTPProxyReference(),
            ),
            (
                "monitors",
                Dictionary(
                    title=_("Fetch monitors"),
                    help=_(
                        "Fetch monitors from your datadog instance. Fetched monitors will be "
                        "discovered as services on the host where the special agent is executed."
                    ),
                    elements=[
                        (
                            "tags",
                            ListOfStrings(
                                title=_("Restrict by tags"),
                                help=_(
                                    "Restrict fetched monitors by tags (API field <tt>tags</tt>). "
                                    "Monitors must have all of the configured tags in order to be "
                                    "fetched."
                                ),
                                size=30,
                                allow_empty=False,
                            ),
                        ),
                        (
                            "monitor_tags",
                            ListOfStrings(
                                title=_("Restrict by monitor tags"),
                                help=_(
                                    "Restrict fetched monitors by service and/or custom tags (API "
                                    "field <tt>monitor_tags</tt>). Monitors must have all of the "
                                    "configured tags in order to be fetched."
                                ),
                                size=30,
                                allow_empty=False,
                            ),
                        ),
                    ],
                ),
            ),
            (
                "events",
                Dictionary(
                    title=_("Fetch events"),
                    help=_(
                        "Fetch events from the event stream of your datadog instance. Fetched "
                        "events will be forwared to the event console of the site where the "
                        "special agent is executed."
                    ),
                    elements=[
                        (
                            "max_age",
                            Age(
                                title=_("Maximum age of fetched events (10 hours max.)"),
                                help=_(
                                    "During each run, the agent will fetch events which are at "
                                    "maximum this old. The agent memorizes events already fetched "
                                    "during the last run, s.t. no event will be sent to the event "
                                    "console multiple times. Setting this value lower than the "
                                    "check interval of the host will result in missing events. "
                                    "Also note that the Datadog API allows for creating new events "
                                    "which lie in the past. Such events will be missed by the "
                                    "agent if their age exceeds the value specified here."
                                ),
                                minvalue=10,
                                maxvalue=10 * 3600,
                                default_value=600,
                                display=["hours", "minutes", "seconds"],
                            ),
                        ),
                        (
                            "tags",
                            ListOfStrings(
                                title=_("Restrict by tags"),
                                help=_(
                                    "Restrict fetched events by tags (API field <tt>tags</tt>). "
                                    "Events must have all of the configured tags in order to be "
                                    "fetched."
                                ),
                                size=30,
                                allow_empty=False,
                            ),
                        ),
                        (
                            "tags_to_show",
                            ListOfStrings(
                                valuespec=RegExp(
                                    mode=RegExp.prefix,
                                    size=30,
                                ),
                                title=_("Tags shown in Event Console"),
                                help=_(
                                    "This option allows you to configure which Datadog tags will be "
                                    "shown in the events forwarded to the Event Console. This is "
                                    "done by entering regular expressions matching one or more "
                                    "Datadog tags. Any matching tag will be added to the text of the "
                                    "corresponding event."
                                ),
                                allow_empty=False,
                            ),
                        ),
                        (
                            "syslog_facility",
                            DropdownChoice(
                                choices=syslog_facilities,
                                title=_("Syslog facility"),
                                help=_(
                                    "Syslog facility of forwarded events shown in Event Console."
                                ),
                                default_value=1,
                            ),
                        ),
                        (
                            "syslog_priority",
                            DropdownChoice(
                                choices=syslog_priorities,
                                title=_("Syslog priority"),
                                help=_(
                                    "Syslog priority of forwarded events shown in Event Console."
                                ),
                                default_value=1,
                            ),
                        ),
                        (
                            "service_level",
                            DropdownChoice(
                                choices=service_levels(),
                                title=_("Service level"),
                                help=_("Service level of forwarded events shown in Event Console."),
                                prefix_values=True,
                            ),
                        ),
                        (
                            "add_text",
                            DropdownChoice(
                                choices=[
                                    (
                                        False,
                                        "Do not add text",
                                    ),
                                    (
                                        True,
                                        "Add text",
                                    ),
                                ],
                                title=_("Add text of events"),
                                default_value=False,
                                help=_(
                                    "Add text of events to data forwarded to the Event Console. "
                                    "Newline characters are replaced by '~'."
                                ),
                            ),
                        ),
                    ],
                    optional_keys=["tags", "tags_to_show"],
                ),
            ),
        ],
        optional_keys=["proxy", "monitors", "events"],
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=watolib.Rulespec.FACTORY_DEFAULT_UNUSED,
        group=RulespecGroupDatasourceProgramsApps,
        name="special_agents:datadog",
        valuespec=_valuespec_special_agents_datadog,
    )
)
