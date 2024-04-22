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

from cmk.utils.config_validation_layer.type_defs import OMITTED_FIELD
from cmk.utils.config_validation_layer.validation_utils import ConfigValidationError


class EmailFromOrTo(BaseModel):
    display_name: str = OMITTED_FIELD
    address: str = OMITTED_FIELD


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
    encryption: Literal["ssl_tls", "starttls"] = OMITTED_FIELD
    auth: MailAuth = OMITTED_FIELD


class BaseMailPlugin(BaseModel):
    from_: EmailFromOrTo = Field(default=OMITTED_FIELD, alias="from")
    reply_to: EmailFromOrTo = OMITTED_FIELD
    host_subject: str = OMITTED_FIELD
    service_subject: str = OMITTED_FIELD
    bulk_sort_order: Literal["oldest_first", "newest_first"] = OMITTED_FIELD
    disable_multiplexing: Literal[True] = OMITTED_FIELD


class MailPluginModel(BaseMailPlugin):
    elements: list[MailElement] = OMITTED_FIELD
    insert_html_section: str = OMITTED_FIELD
    url_prefix: AutomaticUrlPrefix | ManualUrlPrefix = OMITTED_FIELD
    no_floating_graphs: Literal[True] = OMITTED_FIELD
    graphs_per_notification: int = OMITTED_FIELD
    notifications_with_graphs: int = OMITTED_FIELD
    smtp: SyncDeliverySMTP = OMITTED_FIELD


class AsciiMailPluginModel(BaseMailPlugin):
    common_body: str = OMITTED_FIELD
    host_body: str = OMITTED_FIELD
    service_body: str = OMITTED_FIELD


Environment = tuple[Literal["environment"], Literal["envronment"]]
WithoutProxy = tuple[Literal["no_proxy"], None]
GlobalProxy = Any  # TODO: Not sure how to configure this.
ExplicitProxy = tuple[Literal["url"], str]
ProxyURL = Environment | WithoutProxy | GlobalProxy | ExplicitProxy

WebhookURL = tuple[Literal["webhook_url", "store"], str]


class CiscoPluginModel(BaseModel):
    webhook_url: WebhookURL
    url_prefix: AutomaticUrlPrefix | ManualUrlPrefix = OMITTED_FIELD
    ignore_ssl: Literal[True] = OMITTED_FIELD
    proxy_url: ProxyURL = OMITTED_FIELD


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
    facility: SysLogFacility = OMITTED_FIELD
    remote: IPv4Address | IPv6Address = OMITTED_FIELD


class IlertPluginModel(BaseModel):
    ilert_api_key: tuple[Literal["ilert_api_key", "store"], str]
    ilert_priority: Literal["HIGH", "LOW"]
    ilert_summary_host: str
    ilert_summary_service: str
    url_prefix: AutomaticUrlPrefix | ManualUrlPrefix
    ignore_ssl: Literal[True] = OMITTED_FIELD
    proxy_url: ProxyURL = OMITTED_FIELD


class JiraIssuePluginModel(BaseModel):
    url: str
    username: str
    password: str
    project: str
    issuetype: str
    host_customid: str
    service_customid: str
    monitoring: str
    ignore_ssl: Literal[True] = OMITTED_FIELD
    priority: str = OMITTED_FIELD
    host_summary: str = OMITTED_FIELD
    service_summary: str = OMITTED_FIELD
    label: str = OMITTED_FIELD
    resolution: str = OMITTED_FIELD
    timeout: str = OMITTED_FIELD


class MicrosoftTeamsPluginModel(BaseModel):
    webhook_url: WebhookURL = OMITTED_FIELD
    proxy_url: ProxyURL = OMITTED_FIELD
    url_prefix: AutomaticUrlPrefix | ManualUrlPrefix = OMITTED_FIELD
    host_title: str = OMITTED_FIELD
    service_title: str = OMITTED_FIELD
    host_summary: str = OMITTED_FIELD
    service_summary: str = OMITTED_FIELD
    host_details: str = OMITTED_FIELD
    service_details: str = OMITTED_FIELD
    affected_host_groups: Literal[True] = OMITTED_FIELD


class OpsGenieIssuesPluginModel(BaseModel):
    password: tuple[Literal["password", "store"], str]
    url: str = OMITTED_FIELD
    proxy_url: ProxyURL = OMITTED_FIELD
    owner: str = OMITTED_FIELD
    source: str = OMITTED_FIELD
    priority: Literal["P1", "P2", "P3", "P4", "P5"] = OMITTED_FIELD
    note_created: str = OMITTED_FIELD
    note_closed: str = OMITTED_FIELD
    host_msg: str = OMITTED_FIELD
    svc_msg: str = OMITTED_FIELD
    host_desc: str = OMITTED_FIELD
    svc_desc: str = OMITTED_FIELD
    teams: list[str] = OMITTED_FIELD
    actions: list[str] = OMITTED_FIELD
    tags: list[str] = OMITTED_FIELD
    entity: str = OMITTED_FIELD

    @field_validator("url")
    @classmethod
    def check_url(cls, value: str) -> None:
        assert value.startswith("https://")


class PagerDutyPluginModel(BaseModel):
    routing_key: tuple[Literal["routing_key", "store"], str]
    webhook_url: Literal["https://events.pagerduty.com/v2/enqueue"]
    ignore_ssl: Literal[True] = OMITTED_FIELD
    proxy_url: ProxyURL = OMITTED_FIELD
    url_prefix: AutomaticUrlPrefix | ManualUrlPrefix = OMITTED_FIELD


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
    proxy_url: ProxyURL = OMITTED_FIELD
    priority: PushoverPriority = OMITTED_FIELD
    sound: Sound = OMITTED_FIELD


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
    start: IncidentState = OMITTED_FIELD


class CaseRecoveryState(BaseModel):
    start: CaseState = OMITTED_FIELD


class AckState(BaseModel):
    start: IncidentState = OMITTED_FIELD


class DowntimeState(BaseModel):
    start: IncidentState = OMITTED_FIELD
    end: IncidentState = OMITTED_FIELD


class MgmtTypeBase(BaseModel):
    host_short_desc: str = OMITTED_FIELD
    svc_short_desc: str = OMITTED_FIELD
    host_desc: str = OMITTED_FIELD
    svc_desc: str = OMITTED_FIELD


Weight = Literal["low", "medium", "high"]


class MgmtTypeIncident(MgmtTypeBase):
    caller: str
    urgency: Weight = OMITTED_FIELD
    impact: Weight = OMITTED_FIELD
    ack_state: AckState = OMITTED_FIELD
    dt_state: DowntimeState = OMITTED_FIELD
    recovery_state: IncidentRecoveryState = OMITTED_FIELD


Priority = Literal["low", "moderate", "high", "critical"]


class MgmtTypeCase(MgmtTypeBase):
    priority: Priority = OMITTED_FIELD
    recovery_state: CaseRecoveryState = OMITTED_FIELD


Mgmt = tuple[Literal["incident"], MgmtTypeIncident] | tuple[Literal["case"], MgmtTypeCase]


class ServiceNowPluginModel(BaseModel):
    url: str
    username: str
    password: tuple[Literal["password", "store"], str]
    use_site_id: bool = OMITTED_FIELD
    timeout: str = OMITTED_FIELD
    mgmt_type: Mgmt


class SignL4PluginModel(BaseModel):
    password: tuple[Literal["password", "store"], str]
    url_prefix: AutomaticUrlPrefix | ManualUrlPrefix
    proxy_url: ProxyURL = OMITTED_FIELD
    ignore_ssl: Literal[True] = OMITTED_FIELD


class SlackPluginModel(BaseModel):
    webhook_url: WebhookURL
    ignore_ssl: Literal[True] = OMITTED_FIELD
    url_prefix: AutomaticUrlPrefix | ManualUrlPrefix = OMITTED_FIELD
    proxy_url: ProxyURL = OMITTED_FIELD


class SmsApiPluginModel(BaseModel):
    modem_type: Literal["trb140"]
    url: str
    proxy_url: ProxyURL
    username: str
    password: tuple[Literal["password", "store"], str]
    ignore_ssl: Literal[True] = OMITTED_FIELD
    timeout: str = OMITTED_FIELD


class SpectrumPluginModel(BaseModel):
    destination: IPv4Address | IPv6Address
    community: str
    baseoid: str


class SplunkPluginModel(BaseModel):
    webhook_url: WebhookURL
    ignore_ssl: Literal[True] = OMITTED_FIELD
    proxy_url: ProxyURL = OMITTED_FIELD
    url_prefix: AutomaticUrlPrefix | ManualUrlPrefix = OMITTED_FIELD

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
    match_rule_id: list[str] = OMITTED_FIELD
    match_priority: tuple[SyslogPriority, SyslogPriority] = OMITTED_FIELD
    match_facility: SysLogFacility = OMITTED_FIELD
    match_comment: str = OMITTED_FIELD


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
    bulk_subject: str = OMITTED_FIELD


class AlwayBulkParameters(BulkBaseParameters):
    interval: int


class TimeperiodBulkParameters(BulkBaseParameters):
    timeperiod: str
    bulk_outside: AlwayBulkParameters = OMITTED_FIELD


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
    comment: str = OMITTED_FIELD
    docu_url: str = OMITTED_FIELD
    user_id: str | None = OMITTED_FIELD
    contact: str = OMITTED_FIELD
    contact_emails: list[str] = OMITTED_FIELD
    contact_groups: list[str] = OMITTED_FIELD
    contact_match_groups: list[str] = OMITTED_FIELD
    contact_match_macros: list[tuple[str, str]] = OMITTED_FIELD
    contact_users: list[str] = OMITTED_FIELD
    match_attempt: tuple[int, int] = OMITTED_FIELD
    match_checktype: list[str] = OMITTED_FIELD
    match_contactgroups: list[str] = OMITTED_FIELD
    match_contacts: list[str] = OMITTED_FIELD
    match_ec: ConditionEventConsoleAlertsType | Literal[False] = OMITTED_FIELD
    match_escalation: tuple[int, int] = OMITTED_FIELD
    match_escalation_throttle: tuple[int, int] = OMITTED_FIELD
    match_exclude_hosts: list[str] = OMITTED_FIELD
    match_exclude_servicegroups: list[str] = OMITTED_FIELD
    match_exclude_servicegroups_regex: MatchServiceGroupRegex = OMITTED_FIELD
    match_exclude_services: list[str] = OMITTED_FIELD
    match_folder: str = OMITTED_FIELD
    match_host_event: Sequence[HostEvent] = OMITTED_FIELD
    match_hostgroups: list[str] = OMITTED_FIELD
    match_hostlabels: dict[str, str] = OMITTED_FIELD
    match_hosts: list[str] = OMITTED_FIELD
    match_hosttags: list[str] = OMITTED_FIELD
    match_notification_comment: str = OMITTED_FIELD
    match_plugin_output: str = OMITTED_FIELD
    match_service_event: Sequence[ServiceEvent] = OMITTED_FIELD
    match_servicegroups: list[str] = OMITTED_FIELD
    match_servicegroups_regex: MatchServiceGroupRegex = OMITTED_FIELD
    match_servicelabels: dict[str, str] = OMITTED_FIELD
    match_services: list[str] = OMITTED_FIELD
    match_site: list[str] = OMITTED_FIELD
    match_sl: tuple[int, int] = OMITTED_FIELD
    match_timeperiod: str = OMITTED_FIELD
    bulk: NotifyBulk = OMITTED_FIELD
    match_service_level: tuple[int, int] = OMITTED_FIELD
    match_only_during_timeperiod: str = OMITTED_FIELD


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
