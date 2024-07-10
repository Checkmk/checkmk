#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.utils import paths
from cmk.utils.password_store import ad_hoc_password_id
from cmk.utils.rulesets.definition import RuleGroup

from cmk.gui.i18n import _
from cmk.gui.mkeventd import service_levels, syslog_facilities, syslog_priorities
from cmk.gui.valuespec import (
    Age,
    Dictionary,
    DictionaryEntry,
    DropdownChoice,
    HTTPUrl,
    ListOf,
    ListOfStrings,
    RegExp,
    TextInput,
    Transform,
    Tuple,
)
from cmk.gui.wato import (
    HTTPProxyReference,
    IndividualOrStoredPassword,
    RulespecGroupDatasourceProgramsApps,
)
from cmk.gui.watolib.rulespecs import HostRulespec, rulespec_registry

from cmk.ccc.version import edition, Edition
from cmk.rulesets.v1.form_specs import migrate_to_proxy as migrate_proxy_back


def migrate_password_back(value):

    # from this rulespec I just expect the old password formats
    match value:
        case "password", str(password):
            return (
                "cmk_postprocessed",
                "explicit_password",
                (ad_hoc_password_id(), password),
            )
        case "store", str(password_store_id):
            return "cmk_postprocessed", "stored_password", (password_store_id, "")

    raise TypeError(f"Could not migrate {value!r} to Password.")


def migrate_password_forth(value):

    match value:
        # old formats
        case ("password", str()) | ("store", str()):
            return value

        # already migrated passwords
        case "cmk_postprocessed", "explicit_password", (str(_password_id), str(password)):
            return "password", password
        case "cmk_postprocessed", "stored_password", (str(password_store_id), str(password)):
            return "store", password_store_id

    raise ValueError(f"Invalid password format for forth function: {value}")


def migrate_proxy_forth(value):

    match value:

        case "cmk_postprocessed", "stored_proxy", str(stored_proxy_id):
            return "global", stored_proxy_id
        case "cmk_postprocessed", "environment_proxy", str():
            return "environment", "environment"
        case "cmk_postprocessed", "explicit_proxy", str(url):
            return "url", url
        case "cmk_postprocessed", "no_proxy", str():
            return "no_proxy", None

        case ("global", str(_element)) | ("environment", str(_element)) | ("url", str(_element)):
            return value
        case "no_proxy", None:
            return value

    raise TypeError(f"Could not migrate {value!r} to Proxy.")


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
                            Transform(
                                valuespec=IndividualOrStoredPassword(
                                    title=_("API Key"),
                                    allow_empty=False,
                                ),
                                back=migrate_password_back,
                                forth=migrate_password_forth,
                            ),
                        ),
                        (
                            "app_key",
                            Transform(
                                valuespec=IndividualOrStoredPassword(
                                    title=_("Application Key"),
                                    allow_empty=False,
                                ),
                                back=migrate_password_back,
                                forth=migrate_password_forth,
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
                Transform(
                    valuespec=HTTPProxyReference(),
                    back=migrate_proxy_back,
                    forth=migrate_proxy_forth,
                ),
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
        ]
        + _fetch_events_and_logs_elements(),
        optional_keys=["proxy", "monitors", "events", "logs"],
    )


def _fetch_events_and_logs_elements() -> list[DictionaryEntry]:
    if edition(paths.omd_root) is Edition.CSE:  # disabled in CSE
        return []
    return [
        (
            "events",
            Dictionary(
                title=_("Fetch events"),
                help=_(
                    "Fetch events from the event stream of your datadog instance. Fetched "
                    "events will be forwared to the Event Console of the site where the "
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
                            help=_("Syslog facility of forwarded events shown in Event Console."),
                            default_value=1,
                        ),
                    ),
                    (
                        "syslog_priority",
                        DropdownChoice(
                            choices=syslog_priorities,
                            title=_("Syslog priority"),
                            help=_("Syslog priority of forwarded events shown in Event Console."),
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
        (
            "logs",
            Dictionary(
                title=_("Fetch logs"),
                help=_(
                    "Fetch logs of your datadog instance. Fetched logs will be forwared to the "
                    "Event Console of the site where the special agent is executed."
                ),
                elements=[
                    (
                        "max_age",
                        Age(
                            title=_("Maximum age of fetched logs (10 hours max.)"),
                            help=_(
                                "During each run, the agent will fetch logs which are at "
                                "maximum this old. The agent memorizes logs already fetched "
                                "during the last run, s.t. no logs will be sent to the event "
                                "console multiple times. Setting this value lower than the "
                                "check interval of the host will result in missing logs. "
                            ),
                            minvalue=10,
                            maxvalue=10 * 3600,
                            default_value=600,
                            display=["hours", "minutes", "seconds"],
                        ),
                    ),
                    (
                        "query",
                        TextInput(
                            title=_("Log search query"),
                            help=_(
                                "Query to speficy which logs should be forwarded to the event "
                                "console. Use the Datadog "
                                "<a href='https://docs.datadoghq.com/logs/explorer/search_syntax'>log search syntax</a>."
                            ),
                        ),
                    ),
                    (
                        "indexes",
                        ListOfStrings(
                            title=_("Indexes to search"),
                            default_value=["*"],
                            help=_("Indexes to search, defaults to '*', which means all indexes."),
                        ),
                    ),
                    (
                        "syslog_facility",
                        DropdownChoice(
                            choices=syslog_facilities,
                            title=_("Syslog facility"),
                            help=_("Syslog facility of forwarded logs shown in Event Console."),
                            default_value=1,
                        ),
                    ),
                    (
                        "service_level",
                        DropdownChoice(
                            choices=service_levels(),
                            title=_("Service level"),
                            help=_("Service level of forwarded logs shown in Event Console."),
                            prefix_values=True,
                        ),
                    ),
                    (
                        "text",
                        ListOf(
                            title=_("Text of forwarded events"),
                            help=_(
                                "The text of the event can be constructed from the "
                                "<a href='https://docs.datadoghq.com/api/latest/logs/#search-logs'>attributes section of a log entry</a>. "
                                "The text elements are rendered as 'Name:str(attributes[Key])', separated by a comma. "
                                "To access nested fields, use 'key.subkey'. Defaults to the message of the log."
                            ),
                            add_label=_("new element"),
                            default_value=[("message", "message")],
                            valuespec=Tuple(
                                orientation="horizontal",
                                elements=[
                                    TextInput(title=_("Name")),
                                    TextInput(title=_("Key")),
                                ],
                            ),
                        ),
                    ),
                ],
                optional_keys=[],
            ),
        ),
    ]


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsApps,
        name=RuleGroup.SpecialAgents("datadog"),
        valuespec=_valuespec_special_agents_datadog,
    )
)
