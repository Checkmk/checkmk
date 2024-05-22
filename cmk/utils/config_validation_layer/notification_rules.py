#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from ipaddress import IPv4Address, IPv6Address
from typing import Annotated, Any, Literal, NotRequired, Sequence, TypedDict

from pydantic import PlainValidator, TypeAdapter, ValidationInfo

from cmk.utils.timeperiod import TimeperiodName


class EmailFromOrTo(TypedDict):
    display_name: NotRequired[str]
    address: NotRequired[str]


class AutomaticUrlPrefix(TypedDict):
    automatic: Literal["http", "https"]


class ManualUrlPrefix(TypedDict):
    manual: str


MailElement = Literal[
    "omdsite",
    "hosttags",
    "address",
    "abstime",
    "reltime",
    "longoutput",
    "ack_author",
    "ack_comment",
    "notification_author",
    "notification_comment",
    "perfdata",
    "graph",
    "notesurl",
    "context",
]


class MailAuth(TypedDict):
    method: Literal["plaintext"]
    user: str
    password: str


class SyncDeliverySMTP(TypedDict):
    smarthosts: list[str]
    port: int
    encryption: NotRequired[Literal["ssl_tls", "starttls"]]
    auth: NotRequired[MailAuth]


BaseMailPlugin = TypedDict(
    "BaseMailPlugin",
    {
        "from": NotRequired[EmailFromOrTo],
        "reply_to": NotRequired[EmailFromOrTo],
        "host_subject": NotRequired[str],
        "service_subject": NotRequired[str],
        "bulk_sort_order": NotRequired[Literal["oldest_first", "newest_first"]],
        "disable_multiplexing": NotRequired[Literal[True]],
    },
)


class MailPluginModel(BaseMailPlugin):
    elements: NotRequired[list[MailElement]]
    insert_html_section: NotRequired[str]
    url_prefix: NotRequired[AutomaticUrlPrefix | ManualUrlPrefix]
    no_floating_graphs: NotRequired[Literal[True]]
    graphs_per_notification: NotRequired[int]
    notifications_with_graphs: NotRequired[int]
    smtp: NotRequired[SyncDeliverySMTP]


class AsciiMailPluginModel(BaseMailPlugin):
    common_body: NotRequired[str]
    host_body: NotRequired[str]
    service_body: NotRequired[str]


Environment = tuple[Literal["environment"], Literal["envronment"]]
WithoutProxy = tuple[Literal["no_proxy"], None]
GlobalProxy = Any  # TODO: Not sure how to configure this.
ExplicitProxy = tuple[Literal["url"], str]
ProxyURL = Environment | WithoutProxy | GlobalProxy | ExplicitProxy

WebhookURL = tuple[Literal["webhook_url", "store"], str]


class CiscoPluginModel(TypedDict):
    webhook_url: WebhookURL
    url_prefix: NotRequired[AutomaticUrlPrefix | ManualUrlPrefix]
    ignore_ssl: NotRequired[Literal[True]]
    proxy_url: NotRequired[ProxyURL]


SysLogFacility = Literal[
    0,
    1,
    2,
    3,
    4,
    5,
    6,
    7,
    8,
    9,
    10,
    11,
    12,
    13,
    14,
    15,
    16,
    17,
    18,
    19,
    20,
    21,
    22,
    23,
    30,
    31,
]


class MKEventdPluginModel(TypedDict):
    facility: NotRequired[SysLogFacility]
    remote: NotRequired[IPv4Address | IPv6Address]


class IlertPluginModel(TypedDict):
    ilert_api_key: tuple[Literal["ilert_api_key", "store"], str]
    ilert_priority: Literal["HIGH", "LOW"]
    ilert_summary_host: str
    ilert_summary_service: str
    url_prefix: AutomaticUrlPrefix | ManualUrlPrefix
    ignore_ssl: NotRequired[Literal[True]]
    proxy_url: NotRequired[ProxyURL]


class JiraIssuePluginModel(TypedDict):
    url: str
    username: str
    password: str
    project: str
    issuetype: str
    host_customid: str
    service_customid: str
    monitoring: str
    ignore_ssl: NotRequired[Literal[True]]
    priority: NotRequired[str]
    host_summary: NotRequired[str]
    service_summary: NotRequired[str]
    label: NotRequired[str]
    resolution: NotRequired[str]
    timeout: NotRequired[str]


class MicrosoftTeamsPluginModel(TypedDict):
    webhook_url: NotRequired[WebhookURL]
    proxy_url: NotRequired[ProxyURL]
    url_prefix: NotRequired[AutomaticUrlPrefix | ManualUrlPrefix]
    host_title: NotRequired[str]
    service_title: NotRequired[str]
    host_summary: NotRequired[str]
    service_summary: NotRequired[str]
    host_details: NotRequired[str]
    service_details: NotRequired[str]
    affected_host_groups: NotRequired[Literal[True]]


class OpsGenieIssuesPluginModel(TypedDict):
    password: tuple[Literal["password", "store"], str]
    url: NotRequired[str]
    proxy_url: NotRequired[ProxyURL]
    owner: NotRequired[str]
    source: NotRequired[str]
    priority: NotRequired[Literal["P1", "P2", "P3", "P4", "P5"]]
    note_created: NotRequired[str]
    note_closed: NotRequired[str]
    host_msg: NotRequired[str]
    svc_msg: NotRequired[str]
    host_desc: NotRequired[str]
    svc_desc: NotRequired[str]
    teams: NotRequired[list[str]]
    actions: NotRequired[list[str]]
    tags: NotRequired[list[str]]
    entity: NotRequired[str]


class PagerDutyPluginModel(TypedDict):
    routing_key: tuple[Literal["routing_key", "store"], str]
    webhook_url: Literal["https://events.pagerduty.com/v2/enqueue"]
    ignore_ssl: NotRequired[Literal[True]]
    proxy_url: NotRequired[ProxyURL]
    url_prefix: NotRequired[AutomaticUrlPrefix | ManualUrlPrefix]


Sound = Literal[
    "none",
    "alien",
    "bike",
    "bugle",
    "cashregister",
    "classical",
    "climb",
    "cosmic",
    "echo",
    "falling",
    "gamelan",
    "incoming",
    "intermission",
    "magic",
    "mechanical",
    "persistent",
    "pianobar",
    "pushover",
    "siren",
    "spacealarm",
    "tugboat",
    "updown",
    "vibrate",
]


class PriorityEmergency(TypedDict):
    priority: Literal["2"]
    retry: int
    expire: int
    receipts: str


PushoverPriority = Literal["-2", "-1", "0", "1"] | PriorityEmergency


class PushoverPluginModel(TypedDict):
    api_key: str
    recipient_key: str
    url_prefix: str
    proxy_url: NotRequired[ProxyURL]
    priority: NotRequired[PushoverPriority]
    sound: NotRequired[Sound]


CaseState = (
    Literal[
        "none",
        "new",
        "closed",
        "resolved",
        "open",
        "awaiting_info",
    ]
    | int
)
IncidentState = (
    Literal[
        "none",
        "new",
        "progress",
        "closed",
        "resolved",
        "hold",
        "canceled",
    ]
    | int
)


class IncidentRecoveryState(TypedDict):
    start: NotRequired[IncidentState]


class CaseRecoveryState(TypedDict):
    start: NotRequired[CaseState]


class AckState(TypedDict):
    start: NotRequired[IncidentState]


class DowntimeState(TypedDict):
    start: NotRequired[IncidentState]
    end: NotRequired[IncidentState]


class MgmtTypeBase(TypedDict):
    host_short_desc: NotRequired[str]
    svc_short_desc: NotRequired[str]
    host_desc: NotRequired[str]
    svc_desc: NotRequired[str]


Weight = Literal["low", "medium", "high"]


class MgmtTypeIncident(MgmtTypeBase):
    caller: str
    urgency: NotRequired[Weight]
    impact: NotRequired[Weight]
    ack_state: NotRequired[AckState]
    dt_state: NotRequired[DowntimeState]
    recovery_state: NotRequired[IncidentRecoveryState]


Priority = Literal["low", "moderate", "high", "critical"]


class MgmtTypeCase(MgmtTypeBase):
    priority: NotRequired[Priority]
    recovery_state: NotRequired[CaseRecoveryState]


Mgmt = tuple[Literal["incident"], MgmtTypeIncident] | tuple[Literal["case"], MgmtTypeCase]


class ServiceNowPluginModel(TypedDict):
    url: str
    username: str
    password: tuple[Literal["password", "store"], str]
    use_site_id: NotRequired[bool]
    timeout: NotRequired[str]
    mgmt_type: Mgmt


class SignL4PluginModel(TypedDict):
    password: tuple[Literal["password", "store"], str]
    url_prefix: AutomaticUrlPrefix | ManualUrlPrefix
    proxy_url: NotRequired[ProxyURL]
    ignore_ssl: NotRequired[Literal[True]]


class SlackPluginModel(TypedDict):
    webhook_url: WebhookURL
    ignore_ssl: NotRequired[Literal[True]]
    url_prefix: NotRequired[AutomaticUrlPrefix | ManualUrlPrefix]
    proxy_url: NotRequired[ProxyURL]


class SmsApiPluginModel(TypedDict):
    modem_type: Literal["trb140"]
    url: str
    proxy_url: ProxyURL
    username: str
    password: tuple[Literal["password", "store"], str]
    ignore_ssl: NotRequired[Literal[True]]
    timeout: NotRequired[str]


class SpectrumPluginModel(TypedDict):
    destination: IPv4Address | IPv6Address
    community: str
    baseoid: str


class SplunkPluginModel(TypedDict):
    webhook_url: WebhookURL
    ignore_ssl: NotRequired[Literal[True]]
    proxy_url: NotRequired[ProxyURL]
    url_prefix: NotRequired[AutomaticUrlPrefix | ManualUrlPrefix]


SyslogPriority = Literal[
    0,
    1,
    2,
    3,
    4,
    5,
    6,
    7,
]


class ConditionEventConsoleAlertsType(TypedDict):
    match_rule_id: NotRequired[list[str]]
    match_priority: NotRequired[tuple[SyslogPriority, SyslogPriority]]
    match_facility: NotRequired[SysLogFacility]
    match_comment: NotRequired[str]


GroupBy = Literal[
    "folder",
    "host",
    "service",
    "sl",
    "check_type",
    "state",
    "ec_comment",
    "ec_contact",
]


class BulkBaseParameters(TypedDict):
    count: int
    groupby: list[GroupBy]
    groupby_custom: list[str]
    bulk_subject: NotRequired[str]


class AlwayBulkParameters(BulkBaseParameters):
    interval: int


class TimeperiodBulkParameters(BulkBaseParameters):
    timeperiod: str
    bulk_outside: NotRequired[AlwayBulkParameters]


NotifyBulkType = (
    tuple[Literal["always"], AlwayBulkParameters]
    | tuple[Literal["timeperiod"], TimeperiodBulkParameters]
)


KnownPlugin = (
    tuple[Literal["mail"], MailPluginModel | None]
    | tuple[Literal["asciimail"], AsciiMailPluginModel | None]
    | tuple[Literal["cisco_webex_teams"], CiscoPluginModel | None]
    | tuple[Literal["mkeventd"], MKEventdPluginModel | None]
    | tuple[Literal["ilert"], IlertPluginModel | None]
    | tuple[Literal["jira_issues"], JiraIssuePluginModel | None]
    | tuple[Literal["opsgenie_issues"], OpsGenieIssuesPluginModel | None]
    | tuple[Literal["pagerduty"], PagerDutyPluginModel | None]
    | tuple[Literal["pushover"], PushoverPluginModel | None]
    | tuple[Literal["servicenow"], ServiceNowPluginModel | None]
    | tuple[Literal["signl4"], SignL4PluginModel | None]
    | tuple[Literal["slack"], SlackPluginModel | None]
    | tuple[Literal["sms_api"], SmsApiPluginModel | None]
    | tuple[Literal["sms"], list[str] | None]
    | tuple[Literal["spectrum"], SpectrumPluginModel | None]
    | tuple[Literal["victorops"], SplunkPluginModel | None]
    | tuple[Literal["msteams"], MicrosoftTeamsPluginModel | None]
)

CustomPlugin = tuple[str, dict[str, Any] | list[str] | None]

Plugin = KnownPlugin | CustomPlugin

KNOWN_PLUGINS = (
    "mail",
    "asciimail",
    "cisco_webex_teams",
    "mkeventd",
    "ilert",
    "jira_issues",
    "msteams",
    "opsgenie_issues",
    "pagerduty",
    "pushover",
    "servicenow",
    "signl4",
    "slack",
    "sms_api",
    "spectrum",
    "victorops",
)


def validate_plugin(value: Any, _handler: ValidationInfo) -> Plugin:
    assert isinstance(value, tuple)
    assert len(value) == 2

    # If it's a builtin plugin, validate against it's corresponding typeddict.
    if value[0] in KNOWN_PLUGINS:
        TypeAdapter(KnownPlugin).validate_python(value, strict=True)
        return value

    TypeAdapter(CustomPlugin).validate_python(value)
    return value


MatchServiceGroupRegex = tuple[Literal["match_id", "match_alias"], list[str]]

HostEvent = Literal[
    "rd",
    "ru",
    "dr",
    "du",
    "ud",
    "ur",
    "?r",
    "?d",
    "?u",
    "f",
    "s",
    "x",
    "as",
    "af",
]

ServiceEvent = Literal[
    "rw",
    "rr",
    "rc",
    "ru",
    "wr",
    "wc",
    "wu",
    "cr",
    "cw",
    "cu",
    "ur",
    "uw",
    "uc",
    "?r",
    "?w",
    "?c",
    "?u",
    "f",
    "s",
    "x",
    "as",
    "af",
]

HandlerName = str
HandlerParameters = dict[str, Any]


class EventRule(TypedDict):
    rule_id: str
    allow_disable: bool
    contact_all: bool
    contact_all_with_email: bool
    contact_object: bool
    description: str
    disabled: bool
    notify_plugin: Annotated[Plugin, PlainValidator(validate_plugin)]
    user_id: NotRequired[str | None]
    comment: NotRequired[str]
    docu_url: NotRequired[str]
    alert_handler: NotRequired[tuple[HandlerName, HandlerParameters]]
    contact: NotRequired[str]
    contact_emails: NotRequired[list[str]]
    contact_groups: NotRequired[list[str]]
    contact_match_groups: NotRequired[list[str]]
    contact_match_macros: NotRequired[list[tuple[str, str]]]
    contact_users: NotRequired[list[str]]
    match_attempt: NotRequired[tuple[int, int]]
    match_checktype: NotRequired[list[str]]
    match_contactgroups: NotRequired[list[str]]
    match_contacts: NotRequired[list[str]]
    match_ec: NotRequired[ConditionEventConsoleAlertsType | Literal[False]]
    match_escalation: NotRequired[tuple[int, int]]
    match_escalation_throttle: NotRequired[tuple[int, int]]
    match_exclude_hosts: NotRequired[list[str]]
    match_exclude_servicegroups: NotRequired[list[str]]
    match_exclude_servicegroups_regex: NotRequired[MatchServiceGroupRegex]
    match_exclude_services: NotRequired[list[str]]
    match_folder: NotRequired[str]
    match_host_event: NotRequired[Sequence[HostEvent]]
    match_hostgroups: NotRequired[list[str]]
    match_hostlabels: NotRequired[dict[str, str]]
    match_hosts: NotRequired[list[str]]
    match_hosttags: NotRequired[list[str]]
    match_notification_comment: NotRequired[str]
    match_plugin_output: NotRequired[str]
    match_service_event: NotRequired[Sequence[ServiceEvent]]
    match_servicegroups: NotRequired[list[str]]
    match_servicegroups_regex: NotRequired[MatchServiceGroupRegex]
    match_servicelabels: NotRequired[dict[str, str]]
    match_services: NotRequired[list[str]]
    match_site: NotRequired[list[str]]
    match_sl: NotRequired[tuple[int, int]]
    match_timeperiod: NotRequired[TimeperiodName]
    bulk: NotRequired[NotifyBulkType]
    match_service_level: NotRequired[tuple[int, int]]
    match_only_during_timeperiod: NotRequired[str]
