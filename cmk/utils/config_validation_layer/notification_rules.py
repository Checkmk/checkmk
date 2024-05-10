#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from ipaddress import IPv4Address, IPv6Address
from typing import Annotated, Any, Literal, Sequence
from uuid import UUID

from pydantic import (
    BaseModel,
    Field,
    field_validator,
    PlainValidator,
    ValidationError,
    ValidationInfo,
)

from cmk.utils.config_validation_layer.type_defs import Omitted, OMITTED_FIELD
from cmk.utils.config_validation_layer.validation_utils import ConfigValidationError


class EmailFromOrTo(BaseModel):
    display_name: str | Omitted = OMITTED_FIELD
    address: str | Omitted = OMITTED_FIELD


class AutomaticUrlPrefix(BaseModel):
    automatic: Literal["http", "https"]


class ManualUrlPrefix(BaseModel):
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


class MailAuth(BaseModel):
    method: Literal["plaintext"]
    user: str
    password: str


class SyncDeliverySMTP(BaseModel):
    smarthosts: list[str]
    port: int
    encryption: Literal["ssl_tls", "starttls"] | Omitted = OMITTED_FIELD
    auth: MailAuth | Omitted = OMITTED_FIELD


class BaseMailPlugin(BaseModel):
    from_: EmailFromOrTo | Omitted = Field(default=Omitted(), alias="from")
    reply_to: EmailFromOrTo | Omitted = OMITTED_FIELD
    host_subject: str | Omitted = OMITTED_FIELD
    service_subject: str | Omitted = OMITTED_FIELD
    bulk_sort_order: Literal["oldest_first", "newest_first"] | Omitted = OMITTED_FIELD
    disable_multiplexing: Literal[True] | Omitted = OMITTED_FIELD


class MailPluginModel(BaseMailPlugin):
    elements: list[MailElement] | Omitted = OMITTED_FIELD
    insert_html_section: str | Omitted = OMITTED_FIELD
    url_prefix: AutomaticUrlPrefix | ManualUrlPrefix | Omitted = OMITTED_FIELD
    no_floating_graphs: Literal[True] | Omitted = OMITTED_FIELD
    graphs_per_notification: int | Omitted = OMITTED_FIELD
    notifications_with_graphs: int | Omitted = OMITTED_FIELD
    smtp: SyncDeliverySMTP | Omitted = OMITTED_FIELD


class AsciiMailPluginModel(BaseMailPlugin):
    common_body: str | Omitted = OMITTED_FIELD
    host_body: str | Omitted = OMITTED_FIELD
    service_body: str | Omitted = OMITTED_FIELD


Environment = tuple[Literal["environment"], Literal["envronment"]]
WithoutProxy = tuple[Literal["no_proxy"], None]
GlobalProxy = Any  # TODO: Not sure how to configure this.
ExplicitProxy = tuple[Literal["url"], str]
ProxyURL = Environment | WithoutProxy | GlobalProxy | ExplicitProxy

WebhookURL = tuple[Literal["webhook_url", "store"], str]


class CiscoPluginModel(BaseModel):
    webhook_url: WebhookURL
    url_prefix: AutomaticUrlPrefix | ManualUrlPrefix | Omitted = OMITTED_FIELD
    ignore_ssl: Literal[True] | Omitted = OMITTED_FIELD
    proxy_url: ProxyURL | Omitted = OMITTED_FIELD


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


class MKEventdPluginModel(BaseModel):
    facility: SysLogFacility | Omitted = OMITTED_FIELD
    remote: IPv4Address | IPv6Address | Omitted = OMITTED_FIELD


class IlertPluginModel(BaseModel):
    ilert_api_key: tuple[Literal["ilert_api_key", "store"], str]
    ilert_priority: Literal["HIGH", "LOW"]
    ilert_summary_host: str
    ilert_summary_service: str
    url_prefix: AutomaticUrlPrefix | ManualUrlPrefix
    ignore_ssl: Literal[True] | Omitted = OMITTED_FIELD
    proxy_url: ProxyURL | Omitted = OMITTED_FIELD


class JiraIssuePluginModel(BaseModel):
    url: str
    username: str
    password: str
    project: str
    issuetype: str
    host_customid: str
    service_customid: str
    monitoring: str
    ignore_ssl: Literal[True] | Omitted = OMITTED_FIELD
    priority: str | Omitted = OMITTED_FIELD
    host_summary: str | Omitted = OMITTED_FIELD
    service_summary: str | Omitted = OMITTED_FIELD
    label: str | Omitted = OMITTED_FIELD
    resolution: str | Omitted = OMITTED_FIELD
    timeout: str | Omitted = OMITTED_FIELD


class MicrosoftTeamsPluginModel(BaseModel):
    webhook_url: WebhookURL | Omitted = OMITTED_FIELD
    proxy_url: ProxyURL | Omitted = OMITTED_FIELD
    url_prefix: AutomaticUrlPrefix | ManualUrlPrefix | Omitted = OMITTED_FIELD
    host_title: str | Omitted = OMITTED_FIELD
    service_title: str | Omitted = OMITTED_FIELD
    host_summary: str | Omitted = OMITTED_FIELD
    service_summary: str | Omitted = OMITTED_FIELD
    host_details: str | Omitted = OMITTED_FIELD
    service_details: str | Omitted = OMITTED_FIELD
    affected_host_groups: Literal[True] | Omitted = OMITTED_FIELD


class OpsGenieIssuesPluginModel(BaseModel):
    password: tuple[Literal["password", "store"], str]
    url: str | Omitted = OMITTED_FIELD
    proxy_url: ProxyURL | Omitted = OMITTED_FIELD
    owner: str | Omitted = OMITTED_FIELD
    source: str | Omitted = OMITTED_FIELD
    priority: Literal["P1", "P2", "P3", "P4", "P5"] | Omitted = OMITTED_FIELD
    note_created: str | Omitted = OMITTED_FIELD
    note_closed: str | Omitted = OMITTED_FIELD
    host_msg: str | Omitted = OMITTED_FIELD
    svc_msg: str | Omitted = OMITTED_FIELD
    host_desc: str | Omitted = OMITTED_FIELD
    svc_desc: str | Omitted = OMITTED_FIELD
    teams: list[str] | Omitted = OMITTED_FIELD
    actions: list[str] | Omitted = OMITTED_FIELD
    tags: list[str] | Omitted = OMITTED_FIELD
    entity: str | Omitted = OMITTED_FIELD

    @field_validator("url")
    @classmethod
    def check_url(cls, value: str) -> None:
        assert value.startswith("https://")


class PagerDutyPluginModel(BaseModel):
    routing_key: tuple[Literal["routing_key", "store"], str]
    webhook_url: Literal["https://events.pagerduty.com/v2/enqueue"]
    ignore_ssl: Literal[True] | Omitted = OMITTED_FIELD
    proxy_url: ProxyURL | Omitted = OMITTED_FIELD
    url_prefix: AutomaticUrlPrefix | ManualUrlPrefix | Omitted = OMITTED_FIELD


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


class PriorityEmergency(BaseModel):
    priority: Literal["2"]
    retry: int
    expire: int
    receipts: str


PushoverPriority = Literal["-2", "-1", "0", "1"] | PriorityEmergency


class PushoverPluginModel(BaseModel):
    api_key: str
    recipient_key: str
    url_prefix: str
    proxy_url: ProxyURL | Omitted = OMITTED_FIELD
    priority: PushoverPriority | Omitted = OMITTED_FIELD
    sound: Sound | Omitted = OMITTED_FIELD


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


class IncidentRecoveryState(BaseModel):
    start: IncidentState | Omitted = OMITTED_FIELD


class CaseRecoveryState(BaseModel):
    start: CaseState | Omitted = OMITTED_FIELD


class AckState(BaseModel):
    start: IncidentState | Omitted = OMITTED_FIELD


class DowntimeState(BaseModel):
    start: IncidentState | Omitted = OMITTED_FIELD
    end: IncidentState | Omitted = OMITTED_FIELD


class MgmtTypeBase(BaseModel):
    host_short_desc: str | Omitted = OMITTED_FIELD
    svc_short_desc: str | Omitted = OMITTED_FIELD
    host_desc: str | Omitted = OMITTED_FIELD
    svc_desc: str | Omitted = OMITTED_FIELD


Weight = Literal["low", "medium", "high"]


class MgmtTypeIncident(MgmtTypeBase):
    caller: str
    urgency: Weight | Omitted = OMITTED_FIELD
    impact: Weight | Omitted = OMITTED_FIELD
    ack_state: AckState | Omitted = OMITTED_FIELD
    dt_state: DowntimeState | Omitted = OMITTED_FIELD
    recovery_state: IncidentRecoveryState | Omitted = OMITTED_FIELD


Priority = Literal["low", "moderate", "high", "critical"]


class MgmtTypeCase(MgmtTypeBase):
    priority: Priority | Omitted = OMITTED_FIELD
    recovery_state: CaseRecoveryState | Omitted = OMITTED_FIELD


Mgmt = tuple[Literal["incident"], MgmtTypeIncident] | tuple[Literal["case"], MgmtTypeCase]


class ServiceNowPluginModel(BaseModel):
    url: str
    username: str
    password: tuple[Literal["password", "store"], str]
    use_site_id: bool | Omitted = OMITTED_FIELD
    timeout: str | Omitted = OMITTED_FIELD
    mgmt_type: Mgmt


class SignL4PluginModel(BaseModel):
    password: tuple[Literal["password", "store"], str]
    url_prefix: AutomaticUrlPrefix | ManualUrlPrefix
    proxy_url: ProxyURL | Omitted = OMITTED_FIELD
    ignore_ssl: Literal[True] | Omitted = OMITTED_FIELD


class SlackPluginModel(BaseModel):
    webhook_url: WebhookURL
    ignore_ssl: Literal[True] | Omitted = OMITTED_FIELD
    url_prefix: AutomaticUrlPrefix | ManualUrlPrefix | Omitted = OMITTED_FIELD
    proxy_url: ProxyURL | Omitted = OMITTED_FIELD


class SmsApiPluginModel(BaseModel):
    modem_type: Literal["trb140"]
    url: str
    proxy_url: ProxyURL
    username: str
    password: tuple[Literal["password", "store"], str]
    ignore_ssl: Literal[True] | Omitted = OMITTED_FIELD
    timeout: str | Omitted = OMITTED_FIELD


class SpectrumPluginModel(BaseModel):
    destination: IPv4Address | IPv6Address
    community: str
    baseoid: str


class SplunkPluginModel(BaseModel):
    webhook_url: WebhookURL
    ignore_ssl: Literal[True] | Omitted = OMITTED_FIELD
    proxy_url: ProxyURL | Omitted = OMITTED_FIELD
    url_prefix: AutomaticUrlPrefix | ManualUrlPrefix | Omitted = OMITTED_FIELD

    @field_validator("webhook_url")
    @classmethod
    def check_webhook_url(cls, value: WebhookURL) -> None:
        if value[0] == "webhook_url":
            assert value[1].startswith("https://alert.victorops.com/integrations")


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


class ConditionEventConsoleAlertsType(BaseModel):
    match_rule_id: list[str] | Omitted = OMITTED_FIELD
    match_priority: tuple[SyslogPriority, SyslogPriority] | Omitted = OMITTED_FIELD
    match_facility: SysLogFacility | Omitted = OMITTED_FIELD
    match_comment: str | Omitted = OMITTED_FIELD


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


class BulkBaseParameters(BaseModel):
    count: int
    groupby: list[GroupBy]
    groupby_custom: list[str]
    bulk_subject: str | Omitted = OMITTED_FIELD


class AlwayBulkParameters(BulkBaseParameters):
    interval: int


class TimeperiodBulkParameters(BulkBaseParameters):
    timeperiod: str
    bulk_outside: AlwayBulkParameters | Omitted = OMITTED_FIELD


NotifyBulk = (
    tuple[Literal["always"], AlwayBulkParameters]
    | tuple[Literal["timeperiod"], TimeperiodBulkParameters]
)


Plugin = (
    tuple[Literal["mail"], MailPluginModel | None]
    | tuple[Literal["asciimail"], AsciiMailPluginModel | None]
    | tuple[Literal["cisco_webex_teams"], CiscoPluginModel | None]
    | tuple[Literal["mkeventd"], MKEventdPluginModel | None]
    | tuple[Literal["ilert"], IlertPluginModel | None]
    | tuple[Literal["jira_issues"], JiraIssuePluginModel | None]
    | tuple[Literal["msteams"], MicrosoftTeamsPluginModel | None]
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
    | tuple[str, dict[str, Any] | list[str] | None]
)


PLUGIN_MAP = {
    "mail": MailPluginModel,
    "asciimail": AsciiMailPluginModel,
    "cisco_webex_teams": CiscoPluginModel,
    "mkeventd": MKEventdPluginModel,
    "ilert": IlertPluginModel,
    "jira_issues": JiraIssuePluginModel,
    "msteams": MicrosoftTeamsPluginModel,
    "opsgenie_issues": OpsGenieIssuesPluginModel,
    "pagerduty": PagerDutyPluginModel,
    "pushover": PushoverPluginModel,
    "servicenow": ServiceNowPluginModel,
    "signl4": SignL4PluginModel,
    "slack": SlackPluginModel,
    "sms_api": SmsApiPluginModel,
    "spectrum": SpectrumPluginModel,
    "victorops": SplunkPluginModel,
}


def validate_plugin(value: tuple[str, Any], _handler: ValidationInfo) -> Plugin:
    plugin_name, plugin_params = value
    if plugin_params is None:
        return value

    if plugin_name in PLUGIN_MAP:
        return plugin_name, PLUGIN_MAP[plugin_name](**plugin_params)

    if plugin_name == "sms":
        assert isinstance(plugin_params, list)
        for param in plugin_params:
            assert isinstance(param, str)

    else:
        # Custom plugins
        if isinstance(plugin_params, list):
            for param in plugin_params:
                assert isinstance(param, str)
        else:
            assert isinstance(plugin_params, dict)

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


class NotificationRuleModel(BaseModel):
    rule_id: UUID
    allow_disable: bool
    contact_all: bool
    contact_all_with_email: bool
    contact_object: bool
    description: str
    disabled: bool
    notify_plugin: Annotated[Plugin, PlainValidator(validate_plugin)]
    comment: str | Omitted = OMITTED_FIELD
    docu_url: str | Omitted = OMITTED_FIELD
    user_id: str | None | Omitted = OMITTED_FIELD
    contact: str | Omitted = OMITTED_FIELD
    contact_emails: list[str] | Omitted = OMITTED_FIELD
    contact_groups: list[str] | Omitted = OMITTED_FIELD
    contact_match_groups: list[str] | Omitted = OMITTED_FIELD
    contact_match_macros: list[tuple[str, str]] | Omitted = OMITTED_FIELD
    contact_users: list[str] | Omitted = OMITTED_FIELD
    match_attempt: tuple[int, int] | Omitted = OMITTED_FIELD
    match_checktype: list[str] | Omitted = OMITTED_FIELD
    match_contactgroups: list[str] | Omitted = OMITTED_FIELD
    match_contacts: list[str] | Omitted = OMITTED_FIELD
    match_ec: ConditionEventConsoleAlertsType | Literal[False] | Omitted = OMITTED_FIELD
    match_escalation: tuple[int, int] | Omitted = OMITTED_FIELD
    match_escalation_throttle: tuple[int, int] | Omitted = OMITTED_FIELD
    match_exclude_hosts: list[str] | Omitted = OMITTED_FIELD
    match_exclude_servicegroups: list[str] | Omitted = OMITTED_FIELD
    match_exclude_servicegroups_regex: MatchServiceGroupRegex | Omitted = OMITTED_FIELD
    match_exclude_services: list[str] | Omitted = OMITTED_FIELD
    match_folder: str | Omitted = OMITTED_FIELD
    match_host_event: Sequence[HostEvent] | Omitted = OMITTED_FIELD
    match_hostgroups: list[str] | Omitted = OMITTED_FIELD
    match_hostlabels: dict[str, str] | Omitted = OMITTED_FIELD
    match_hosts: list[str] | Omitted = OMITTED_FIELD
    match_hosttags: list[str] | Omitted = OMITTED_FIELD
    match_notification_comment: str | Omitted = OMITTED_FIELD
    match_plugin_output: str | Omitted = OMITTED_FIELD
    match_service_event: Sequence[ServiceEvent] | Omitted = OMITTED_FIELD
    match_servicegroups: list[str] | Omitted = OMITTED_FIELD
    match_servicegroups_regex: MatchServiceGroupRegex | Omitted = OMITTED_FIELD
    match_servicelabels: dict[str, str] | Omitted = OMITTED_FIELD
    match_services: list[str] | Omitted = OMITTED_FIELD
    match_site: list[str] | Omitted = OMITTED_FIELD
    match_sl: tuple[int, int] | Omitted = OMITTED_FIELD
    match_timeperiod: str | Omitted = OMITTED_FIELD
    bulk: NotifyBulk | Omitted = OMITTED_FIELD
    match_service_level: tuple[int, int] | Omitted = OMITTED_FIELD
    match_only_during_timeperiod: str | Omitted = OMITTED_FIELD


def validate_notification_rules(rules: list) -> None:
    for rule in rules:
        validate_notification_rule(rule)


def validate_notification_rule(rule: dict) -> None:
    try:
        NotificationRuleModel(**rule)
    except ValidationError as exc:
        raise ConfigValidationError(
            which_file="notifications.mk",
            pydantic_error=exc,
            original_data=rule,
        )
