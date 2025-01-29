#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping, Sequence
from enum import StrEnum
from typing import (
    Any,
    get_args,
    Literal,
    NewType,
    NotRequired,
    Required,
    TypedDict,
    TypeGuard,
)

from pydantic import (
    TypeAdapter,
    ValidationInfo,
)

from cmk.utils.rulesets.ruleset_matcher import TagCondition
from cmk.utils.tags import TagGroupID
from cmk.utils.timeperiod import TimeperiodName

from cmk.events.notification_result import NotificationContext as NotificationContext

__all__ = [
    # Types
    "ContactName",
    "HandlerName",
    "HandlerParameters",
    "NotifyPluginParamsDict",
    "NotifyBulkParameters",
    "NotificationContext",
    "PluginNotificationContext",
    "NotifyRuleInfo",
    "NotifyPluginName",
    "NotifyPluginInfo",
    "NotifyAnalysisInfo",
    "UUIDs",
    "NotifyBulk",
    "NotifyBulks",
    "NotificationParameterID",
    "NotificationParameterMethod",
    "NotificationParameterSpec",
    "NotificationParameterSpecs",
    # Classes
    "EventRule",
    "DisabledNotificationsOptions",
    "Contact",
    "NotificationParameterGeneralInfos",
    "NotificationParameterItem",
]

ContactName = str

HandlerName = str
HandlerParameters = dict[str, Any]

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


class AlwaysBulkParameters(BulkBaseParameters):
    interval: int


class TimeperiodBulkParameters(BulkBaseParameters):
    timeperiod: str
    bulk_outside: NotRequired[AlwaysBulkParameters]


NotifyBulkParameters = AlwaysBulkParameters | TimeperiodBulkParameters
NotifyBulkType = (
    tuple[Literal["always"], AlwaysBulkParameters]
    | tuple[Literal["timeperiod"], TimeperiodBulkParameters]
)


def is_always_bulk(bulk_params: NotifyBulkParameters) -> TypeGuard[AlwaysBulkParameters]:
    return "interval" in bulk_params


def is_timeperiod_bulk(bulk_params: NotifyBulkParameters) -> TypeGuard[TimeperiodBulkParameters]:
    return "timeperiod" in bulk_params


class PluginOptions(StrEnum):
    CANCEL = "cancel_previous_notifications"
    WITH_PARAMS = "create_notification_with_the_following_parameters"
    WITH_CUSTOM_PARAMS = "create_notification_with_custom_parameters"


MgmntPriorityType = Literal[
    "low",
    "moderate",
    "high",
    "critical",
]
MgmntUrgencyType = Literal[
    "low",
    "medium",
    "high",
]
OpsGeniePriorityStrType = Literal[
    "critical",
    "high",
    "moderate",
    "low",
    "informational",
]
OpsGeniePriorityPValueType = Literal[
    "P1",
    "P2",
    "P3",
    "P4",
    "P5",
]
GroupbyType = Literal[
    "folder",
    "host",
    "service",
    "sl",
    "check_type",
    "state",
    "ec_contact",
    "ec_comment",
]

NonStatusChangeEventType = Literal["f", "s", "x", "as", "af"]


def is_non_status_change_event_type(value: str) -> TypeGuard[NonStatusChangeEventType]:
    return value in get_args(NonStatusChangeEventType)


HostEventType = (
    Literal[
        "rd",
        "ru",
        "dr",
        "du",
        "ud",
        "ur",
        "?r",
        "?d",
        "?u",
    ]
    | NonStatusChangeEventType
)

ServiceEventType = (
    Literal[
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
    ]
    | NonStatusChangeEventType
)
SysLogFacilityIntType = Literal[
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
SysLogFacilityStrType = Literal[
    "kern",
    "user",
    "mail",
    "daemon",
    "auth",
    "syslog",
    "lpr",
    "news",
    "uucp",
    "cron",
    "authpriv",
    "ftp",
    "ntp",
    "logaudit",
    "logalert",
    "clock",
    "local0",
    "local1",
    "local2",
    "local3",
    "local4",
    "local5",
    "local6",
    "local7",
    "logfile",
    "snmptrap",
]
SyslogPriorityIntType = Literal[
    0,
    1,
    2,
    3,
    4,
    5,
    6,
    7,
]
SysLogPriorityStrType = Literal[
    "emerg",
    "alert",
    "crit",
    "err",
    "warning",
    "notice",
    "info",
    "debug",
]
EventConsoleOption = Literal[
    "match_only_event_console_alerts",
    "do_not_match_event_console_alerts",
]
SoundType = Literal[
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
    "disabled",
]
EmailBodyElementsType = Literal[
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
FromOrToType = Mapping[
    Literal["address", "display_name"],
    str,
]
SortOrder = Literal[
    "oldest_first",
    "newest_first",
]
WebHookUrl = tuple[
    Literal["webhook_url", "store"],
    str,
]
IlertAPIKey = tuple[
    Literal["ilert_api_key", "store"],
    str,
]
IlertPriorityType = Literal[
    "HIGH",
    "LOW",
]
PasswordType = tuple[
    Literal["password", "store"],
    str,
]
RoutingKeyType = tuple[
    Literal["routing_key", "store"],
    str,
]
RegexModes = Literal[
    "match_id",
    "match_alias",
]
MatchRegex = tuple[
    RegexModes,
    list[str],
]


HTTPPrefixURL = tuple[Literal["automatic_http"], None]
HTTPSPrefixURL = tuple[Literal["automatic_https"], None]
ManualPrefixURL = tuple[Literal["manual"], str]
URLPrefix = HTTPPrefixURL | HTTPSPrefixURL | ManualPrefixURL


class SMTPAuthAttrs(TypedDict):
    method: Literal["plaintext"]
    password: str
    user: str


class SyncDeliverySMTP(TypedDict):
    auth: NotRequired[SMTPAuthAttrs]
    encryption: NotRequired[Literal["ssl_tls", "starttls"]]
    port: int
    smarthosts: list[str]


MatchServiceGroupsRegex = tuple[
    Literal["match_id", "match_alias"],
    list[str],
]


class ConditionEventConsoleAlertsType(TypedDict, total=False):
    match_rule_id: list[str]
    match_priority: tuple[SyslogPriorityIntType, SyslogPriorityIntType]
    match_facility: SysLogFacilityIntType
    match_comment: str


class BulkOutsideTimePeriodType(TypedDict, total=False):
    count: int
    groupby: list[GroupbyType]
    groupby_custom: list[str]
    interval: int
    bulk_subject: str


class BulkParameters(TypedDict, total=False):
    timeperiod: str
    count: int
    groupby: list[GroupbyType]
    groupby_custom: list[str]
    interval: int
    bulk_subject: str
    bulk_outside: BulkOutsideTimePeriodType


PluginNotificationContext = dict[str, str]
NotificationRuleID = NewType("NotificationRuleID", str)


CheckmkPassword = tuple[
    Literal["cmk_postprocessed"],
    Literal["stored_password", "explicit_password"],
    tuple[str, str],
]


class EmailFromOrTo(TypedDict):
    display_name: NotRequired[str]
    address: NotRequired[str]


MailPluginModel = TypedDict(
    "MailPluginModel",
    {
        "from": NotRequired[EmailFromOrTo],
        "reply_to": NotRequired[EmailFromOrTo],
        "host_subject": NotRequired[str],
        "service_subject": NotRequired[str],
        "bulk_sort_order": NotRequired[Literal["oldest_first", "newest_first"]],
        "disable_multiplexing": NotRequired[Literal[True]],
        "elements": NotRequired[list[EmailBodyElementsType]],
        "insert_html_section": NotRequired[str],
        "url_prefix": NotRequired[URLPrefix],
        "no_floating_graphs": NotRequired[Literal[True]],
        "graphs_per_notification": NotRequired[int],
        "notifications_with_graphs": NotRequired[int],
        "smtp": NotRequired[SyncDeliverySMTP],
    },
)


AsciiMailPluginModel = TypedDict(
    "AsciiMailPluginModel",
    {
        "from": NotRequired[EmailFromOrTo],
        "reply_to": NotRequired[EmailFromOrTo],
        "host_subject": NotRequired[str],
        "service_subject": NotRequired[str],
        "bulk_sort_order": NotRequired[Literal["oldest_first", "newest_first"]],
        "disable_multiplexing": NotRequired[Literal[True]],
        "common_body": NotRequired[str],
        "host_body": NotRequired[str],
        "service_body": NotRequired[str],
    },
)

EnvironmentProxy = tuple[Literal["cmk_postprocessed"], Literal["environment_proxy"], str]
WithoutProxy = tuple[Literal["cmk_postprocessed"], Literal["no_proxy"], str]
StoredProxy = tuple[Literal["cmk_postprocessed"], Literal["stored_proxy"], str]
ExplicitProxy = tuple[Literal["cmk_postprocessed"], Literal["explicit_proxy"], str]
ProxyUrl = EnvironmentProxy | WithoutProxy | StoredProxy | ExplicitProxy

WebhookURL = tuple[Literal["webhook_url", "store"], str]


class CiscoPluginModel(TypedDict, total=False):
    webhook_url: Required[WebhookURL]
    url_prefix: URLPrefix
    ignore_ssl: Literal[True]
    proxy_url: ProxyUrl


class MKEventdPluginModel(TypedDict):
    facility: NotRequired[SysLogFacilityIntType]
    remote: NotRequired[str]


class IlertPluginModel(TypedDict):
    ilert_api_key: CheckmkPassword
    ilert_priority: Literal["HIGH", "LOW"]
    ilert_summary_host: str
    ilert_summary_service: str
    url_prefix: URLPrefix
    ignore_ssl: NotRequired[Literal[True]]
    proxy_url: NotRequired[ProxyUrl]


class TokenAuthCredentials(TypedDict):
    token: CheckmkPassword


class BasicAuthCredentials(TypedDict):
    username: str
    password: CheckmkPassword


TokenAuth = tuple[Literal["auth_token"], TokenAuthCredentials]
BasicAuth = tuple[Literal["auth_basic"], BasicAuthCredentials]


class JiraIssuePluginModel(TypedDict):
    url: str
    auth: BasicAuth | TokenAuth
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
    graphs_per_notification: NotRequired[int]
    resolution: NotRequired[str]
    timeout: NotRequired[str]
    site_customid: NotRequired[str]
    proxy_url: NotRequired[ProxyUrl]


class MicrosoftTeamsPluginModel(TypedDict):
    webhook_url: NotRequired[WebhookURL]
    proxy_url: NotRequired[ProxyUrl]
    url_prefix: NotRequired[URLPrefix]
    host_title: NotRequired[str]
    service_title: NotRequired[str]
    host_summary: NotRequired[str]
    service_summary: NotRequired[str]
    host_details: NotRequired[str]
    service_details: NotRequired[str]
    affected_host_groups: NotRequired[Literal[True]]


OpsgenieElement = Literal[
    "omd_site",
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
    "notesurl",
    "context",
]


class OpsGenieIssuesPluginModel(TypedDict, total=False):
    password: CheckmkPassword
    url: str
    ignore_ssl: Literal[True]
    proxy_url: ProxyUrl
    owner: str
    source: str
    priority: OpsGeniePriorityPValueType
    note_created: str
    note_closed: str
    host_msg: str
    svc_msg: str
    host_desc: str
    svc_desc: str
    teams: list[str]
    actions: list[str]
    tags: list[str]
    entity: str
    elements: list[OpsgenieElement]


class PagerDutyPluginModel(TypedDict):
    routing_key: tuple[Literal["routing_key", "store"], str]
    webhook_url: Literal["https://events.pagerduty.com/v2/enqueue"]
    ignore_ssl: NotRequired[Literal[True]]
    proxy_url: NotRequired[ProxyUrl]
    url_prefix: NotRequired[URLPrefix]


PushOverPriorityStringType = Literal["lowest", "low", "normal", "high"]
PushOverEmergencyType = tuple[Literal["emergency"], tuple[float, float, str]]
PushOverPriorityType = tuple[PushOverPriorityStringType, None] | PushOverEmergencyType


class PushoverPluginModel(TypedDict):
    api_key: str
    recipient_key: str
    url_prefix: URLPrefix
    proxy_url: NotRequired[ProxyUrl]
    priority: NotRequired[PushOverPriorityType]
    sound: NotRequired[SoundType]


CaseStateStr = Literal["none", "new", "closed", "resolved", "open", "awaiting_info"]
CaseState = tuple[Literal["predefined"], CaseStateStr] | tuple[Literal["integer"], int]

IncidentStateStr = Literal["none", "new", "progress", "closed", "resolved", "hold", "canceled"]
IncidentState = tuple[Literal["predefined"], IncidentStateStr] | tuple[Literal["integer"], int]


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


class MgmtTypeIncident(MgmtTypeBase, total=False):
    caller: Required[str]
    urgency: MgmntUrgencyType
    impact: MgmntUrgencyType
    ack_state: AckState
    dt_state: DowntimeState
    recovery_state: IncidentRecoveryState


class MgmtTypeCase(MgmtTypeBase):
    priority: NotRequired[MgmntPriorityType]
    recovery_state: NotRequired[CaseRecoveryState]


MgmtTypeCaseType = tuple[Literal["case"], MgmtTypeCase]
MgmtTypeIncidentType = tuple[Literal["incident"], MgmtTypeIncident]

UseSiteIDType = Literal["use_site_id", "deactivated"]


class ServiceNowPluginModel(TypedDict):
    url: str
    auth: BasicAuth | TokenAuth
    use_site_id: NotRequired[UseSiteIDType]
    timeout: NotRequired[str]
    proxy_url: NotRequired[ProxyUrl]
    mgmt_type: MgmtTypeCaseType | MgmtTypeIncidentType


class SignL4PluginModel(TypedDict):
    password: CheckmkPassword
    url_prefix: URLPrefix
    proxy_url: NotRequired[ProxyUrl]
    ignore_ssl: NotRequired[Literal[True]]


class SlackPluginModel(TypedDict, total=False):
    webhook_url: Required[WebhookURL]
    ignore_ssl: Literal[True]
    url_prefix: URLPrefix
    proxy_url: ProxyUrl


class SmsApiPluginModel(TypedDict):
    modem_type: Literal["trb140"]
    url: str
    proxy_url: ProxyUrl
    username: str
    password: CheckmkPassword
    ignore_ssl: NotRequired[Literal[True]]
    timeout: NotRequired[str]


class SmsPluginModel(TypedDict):
    params: list[str]


class SpectrumPluginModel(TypedDict):
    destination: str
    community: CheckmkPassword
    baseoid: str


class SplunkPluginModel(TypedDict, total=False):
    webhook_url: Required[WebhookURL]
    ignore_ssl: Literal[True]
    proxy_url: ProxyUrl
    url_prefix: URLPrefix


CiscoPluginName = Literal["cisco_webex_teams"]
CiscoNotify = tuple[CiscoPluginName, CiscoPluginModel | None]

MkeventdPluginName = Literal["mkeventd"]
MkeventdNotify = tuple[MkeventdPluginName, MKEventdPluginModel | None]

AsciiMailPluginName = Literal["asciimail"]
AsciiMailNotify = tuple[AsciiMailPluginName, AsciiMailPluginModel | None]

MailPluginName = Literal["mail"]
MailNotify = tuple[MailPluginName, MailPluginModel | None]

MSTeamsPluginName = Literal["msteams"]
MSteamsNotify = tuple[MSTeamsPluginName, MicrosoftTeamsPluginModel | None]

IlertPluginName = Literal["ilert"]
IlertNotify = tuple[IlertPluginName, IlertPluginModel | None]

JiraPluginName = Literal["jira_issues"]
JiraNotify = tuple[JiraPluginName, JiraIssuePluginModel | None]

OpsGeniePluginName = Literal["opsgenie_issues"]
OpsgenieNotify = tuple[OpsGeniePluginName, OpsGenieIssuesPluginModel | None]

PagerdutyPluginName = Literal["pagerduty"]
PagerdutyNotify = tuple[PagerdutyPluginName, PagerDutyPluginModel | None]

PushoverPluginName = Literal["pushover"]
PushoverNotify = tuple[PushoverPluginName, PushoverPluginModel | None]

ServiceNowPluginName = Literal["servicenow"]
ServiceNowNotify = tuple[ServiceNowPluginName, ServiceNowPluginModel | None]

Signl4PluginName = Literal["signl4"]
SignL4Notify = tuple[Signl4PluginName, SignL4PluginModel | None]

SlackPluginName = Literal["slack"]
SlackNotify = tuple[SlackPluginName, SlackPluginModel | None]

SmsApiPluginName = Literal["sms_api"]
SmsApiNotify = tuple[SmsApiPluginName, SmsApiPluginModel | None]

SmsPluginName = Literal["sms"]
SmsNotify = tuple[SmsPluginName, SmsPluginModel | None]

SpectrumPluginName = Literal["spectrum"]
SpectrumNotify = tuple[SpectrumPluginName, SpectrumPluginModel | None]

SplunkPluginName = Literal["victorops"]
SplunkNotify = tuple[SplunkPluginName, SplunkPluginModel | None]

CustomPluginName = NewType("CustomPluginName", str)
CustomPluginParameters = tuple[CustomPluginName, dict[str, Any] | None]

KnownPluginParameters = (
    MailNotify
    | AsciiMailNotify
    | CiscoNotify
    | MkeventdNotify
    | IlertNotify
    | JiraNotify
    | OpsgenieNotify
    | PagerdutyNotify
    | PushoverNotify
    | ServiceNowNotify
    | SignL4Notify
    | SlackNotify
    | SmsApiNotify
    | SmsNotify
    | SpectrumNotify
    | SplunkNotify
    | MSteamsNotify
)

BuiltInPluginNames = (
    CiscoPluginName
    | MkeventdPluginName
    | AsciiMailPluginName
    | MailPluginName
    | MSTeamsPluginName
    | IlertPluginName
    | JiraPluginName
    | OpsGeniePluginName
    | PagerdutyPluginName
    | PushoverPluginName
    | ServiceNowPluginName
    | Signl4PluginName
    | SlackPluginName
    | SmsApiPluginName
    | SmsPluginName
    | SpectrumPluginName
    | SplunkPluginName
)

NotifyPluginParamsDict = (
    MailPluginModel
    | AsciiMailPluginModel
    | CiscoPluginModel
    | MKEventdPluginModel
    | IlertPluginModel
    | JiraIssuePluginModel
    | OpsGenieIssuesPluginModel
    | PagerDutyPluginModel
    | PushoverPluginModel
    | ServiceNowPluginModel
    | SignL4PluginModel
    | SlackPluginModel
    | SmsApiPluginModel
    | SmsPluginModel
    | SpectrumPluginModel
    | SplunkPluginModel
    | MicrosoftTeamsPluginModel
    | dict[str, Any]
)

NotificationPluginNameStr = BuiltInPluginNames | CustomPluginName
NotificationParameterID = NewType("NotificationParameterID", str)
PluginNameWithParameters = tuple[NotificationPluginNameStr, NotifyPluginParamsDict | None]
NotifyPlugin = tuple[NotificationPluginNameStr, NotificationParameterID | None]


def get_builtin_plugin_names() -> list[BuiltInPluginNames]:
    return [get_args(name)[0] for name in get_args(BuiltInPluginNames)]


def is_known_plugin(notify_plugin: PluginNameWithParameters) -> TypeGuard[KnownPluginParameters]:
    return notify_plugin[0] in get_builtin_plugin_names()


custom_plugin_type_adapter: TypeAdapter = TypeAdapter(CustomPluginParameters)
known_plugin_type_adapter: TypeAdapter = TypeAdapter(KnownPluginParameters)


def validate_plugin(value: Any, _handler: ValidationInfo) -> PluginNameWithParameters:
    assert isinstance(value, tuple)
    assert len(value) == 2

    # If it's a builtin plugin, validate against it's corresponding typeddict.
    if value[0] in get_args(BuiltInPluginNames):
        known_plugin_type_adapter.validate_python(value, strict=True)
        return value

    custom_plugin_type_adapter.validate_python(value)
    return value


class _EventRuleMandatory(TypedDict):
    rule_id: NotificationRuleID
    allow_disable: bool
    contact_all: bool
    contact_all_with_email: bool
    contact_object: bool
    description: str
    disabled: bool
    notify_plugin: NotifyPlugin


class EventRule(_EventRuleMandatory):
    """Event Rule

    used to be dict[str, Any], feel free to add stuff"""

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
    match_exclude_servicegroups_regex: NotRequired[MatchServiceGroupsRegex]
    match_exclude_services: NotRequired[list[str]]
    match_folder: NotRequired[str]
    match_host_event: NotRequired[Sequence[HostEventType]]
    match_hostgroups: NotRequired[list[str]]
    match_hostlabels: NotRequired[dict[str, str]]
    match_hosts: NotRequired[list[str]]
    match_hosttags: NotRequired[Mapping[TagGroupID, TagCondition]]
    match_notification_comment: NotRequired[str]
    match_plugin_output: NotRequired[str]
    match_service_event: NotRequired[Sequence[ServiceEventType]]
    match_servicegroups: NotRequired[list[str]]
    match_servicegroups_regex: NotRequired[MatchServiceGroupsRegex]
    match_servicelabels: NotRequired[dict[str, str]]
    match_services: NotRequired[list[str]]
    match_site: NotRequired[list[str]]
    match_sl: NotRequired[tuple[int, int]]
    match_timeperiod: NotRequired[TimeperiodName]
    bulk: NotRequired[NotifyBulkType]
    match_service_level: NotRequired[tuple[int, int]]
    match_only_during_timeperiod: NotRequired[str]


NotifyRuleInfo = tuple[str, EventRule, str]
NotifyPluginName = str
NotifyPluginInfo = tuple[
    ContactName, NotificationPluginNameStr, NotifyPluginParamsDict, NotifyBulkParameters | None
]
NotifyAnalysisInfo = tuple[list[NotifyRuleInfo], list[NotifyPluginInfo]]

UUIDs = list[tuple[float, str]]
NotifyBulk = tuple[str, float, None | str | int, None | str | int, int, UUIDs]
NotifyBulks = list[NotifyBulk]


class DisabledNotificationsOptions(TypedDict, total=False):
    disabled: bool
    timerange: tuple[float, float]


class Contact(TypedDict, total=False):
    alias: str
    contactgroups: tuple[str, ...] | list[str]
    disable_notifications: DisabledNotificationsOptions
    email: str
    name: str
    pager: str
    notification_rules: list[EventRule]
    authorized_sites: list[str] | None
    notifications_enabled: bool
    host_notification_options: str
    service_notification_options: str


class NotificationParameterGeneralInfos(TypedDict):
    description: str
    comment: str
    docu_url: str


class NotificationParameterItem(TypedDict):
    general: NotificationParameterGeneralInfos
    parameter_properties: NotifyPluginParamsDict


NotificationParameterMethod = str
NotificationParameterSpec = dict[NotificationParameterID, NotificationParameterItem]
NotificationParameterSpecs = dict[NotificationParameterMethod, NotificationParameterSpec]


def get_rules_related_to_parameter(
    rules: Iterable[EventRule], parameter_id: NotificationParameterID
) -> list[EventRule]:
    return [rule for rule in rules if parameter_id in rule["notify_plugin"]]
