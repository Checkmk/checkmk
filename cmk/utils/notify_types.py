#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import (
    Annotated,
    Any,
    get_args,
    Literal,
    NewType,
    NotRequired,
    Required,
    TypedDict,
    TypeGuard,
)

from pydantic import PlainValidator, TypeAdapter, ValidationInfo

from cmk.utils.hostaddress import HostName
from cmk.utils.timeperiod import TimeperiodName

__all__ = [
    # Types
    "ContactName",
    "HandlerName",
    "HandlerParameters",
    "NotifyPluginParamsList",
    "NotifyPluginParamsDict",
    "NotifyPluginParams",
    "NotifyBulkParameters",
    "NotificationType",
    "NotificationContext",
    "PluginNotificationContext",
    "NotifyRuleInfo",
    "NotifyPluginName",
    "NotifyPluginInfo",
    "NotifyAnalysisInfo",
    "UUIDs",
    "NotifyBulk",
    "NotifyBulks",
    # Classes
    "EventRule",
    "DisabledNotificationsOptions",
    "Contact",
    "EventContext",
    "ECEventContext",
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


def is_always_bulk(
    bulk_params: NotifyBulkParameters,
) -> TypeGuard[AlwaysBulkParameters]:
    return "interval" in bulk_params


def is_timeperiod_bulk(
    bulk_params: NotifyBulkParameters,
) -> TypeGuard[TimeperiodBulkParameters]:
    return "timeperiod" in bulk_params


class PluginOptions(StrEnum):
    CANCEL = "cancel_previous_notifications"
    WITH_PARAMS = "create_notification_with_the_following_parameters"
    WITH_CUSTOM_PARAMS = "create_notification_with_custom_parameters"


NotificationType = Literal[
    "ACKNOWLEDGEMENT",
    "DOWNTIMECANCELLED",
    "DOWNTIMEEND",
    "DOWNTIMESTART",
    "FLAPPINGDISABLED",
    "FLAPPINGSTART",
    "FLAPPINGSTOP",
    "PROBLEM",
    "RECOVERY",
]
NotificationContext = NewType("NotificationContext", dict[str, str])

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
PushOverPriorityNumType = Literal[
    "-2",
    "-1",
    "0",
    "1",
]
PushOverPriorityStringType = Literal[
    "lowest",
    "low",
    "normal",
    "high",
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
HostEventType = Literal[
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
ServiceEventType = Literal[
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


class AutomaticUrlPrefix(TypedDict):
    automatic: Literal["http", "https"]


class ManualUrlPrefix(TypedDict):
    manual: str


URLPrefix = AutomaticUrlPrefix | ManualUrlPrefix


def is_auto_urlprefix(url_prefix: URLPrefix) -> TypeGuard[AutomaticUrlPrefix]:
    return "automatic" in url_prefix


def is_manual_urlprefix(url_prefix: URLPrefix) -> TypeGuard[ManualUrlPrefix]:
    return "manual" in url_prefix


class SMTPAuthAttrs(TypedDict, total=False):
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


Environment = tuple[Literal["environment"], Literal["environment"]]
WithoutProxy = tuple[Literal["no_proxy"], None]
GlobalProxy = tuple[Literal["global"], str]
ExplicitProxy = tuple[Literal["url"], str]
ProxyUrl = Environment | WithoutProxy | GlobalProxy | ExplicitProxy
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
    ilert_api_key: tuple[Literal["ilert_api_key", "store"], str]
    ilert_priority: Literal["HIGH", "LOW"]
    ilert_summary_host: str
    ilert_summary_service: str
    url_prefix: URLPrefix
    ignore_ssl: NotRequired[Literal[True]]
    proxy_url: NotRequired[ProxyUrl]


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
    site_customid: NotRequired[str]


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


class OpsGenieIssuesPluginModel(TypedDict, total=False):
    password: Required[tuple[Literal["password", "store"], str]]
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


class PagerDutyPluginModel(TypedDict):
    routing_key: tuple[Literal["routing_key", "store"], str]
    webhook_url: Literal["https://events.pagerduty.com/v2/enqueue"]
    ignore_ssl: NotRequired[Literal[True]]
    proxy_url: NotRequired[ProxyUrl]
    url_prefix: NotRequired[URLPrefix]


class PushoverPluginModel(TypedDict):
    api_key: str
    recipient_key: str
    url_prefix: str
    proxy_url: NotRequired[ProxyUrl]
    priority: NotRequired[PushOverPriorityNumType]
    sound: NotRequired[SoundType]


CaseStateStr = Literal["none", "new", "closed", "resolved", "open", "awaiting_info"]
CaseState = CaseStateStr | int

IncidentStateStr = Literal["none", "new", "progress", "closed", "resolved", "hold", "canceled"]
IncidentState = IncidentStateStr | int


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


class ServiceNowPluginModel(TypedDict):
    url: str
    username: str
    password: tuple[Literal["password", "store"], str]
    use_site_id: NotRequired[bool]
    timeout: NotRequired[str]
    proxy_url: NotRequired[ProxyUrl]
    mgmt_type: tuple[Literal["incident"], MgmtTypeIncident] | tuple[Literal["case"], MgmtTypeCase]


class SignL4PluginModel(TypedDict):
    password: tuple[Literal["password", "store"], str]
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
    password: tuple[Literal["password", "store"], str]
    ignore_ssl: NotRequired[Literal[True]]
    timeout: NotRequired[str]


class SpectrumPluginModel(TypedDict):
    destination: str
    community: str
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
SmsNotify = tuple[SmsPluginName, list[str] | None]

SpectrumPluginName = Literal["spectrum"]
SpectrumNotify = tuple[SpectrumPluginName, SpectrumPluginModel | None]

SplunkPluginName = Literal["victorops"]
SplunkNotify = tuple[SplunkPluginName, SplunkPluginModel | None]

CustomPluginName = NewType("CustomPluginName", str)
CustomPluginType = tuple[CustomPluginName, dict[str, Any] | list[str] | None]

KnownPlugins = (
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


NotificationPluginNameStr = BuiltInPluginNames | CustomPluginName
NotifyPlugin = KnownPlugins | CustomPluginType


def get_builtin_plugin_names() -> list[BuiltInPluginNames]:
    return [get_args(name)[0] for name in get_args(BuiltInPluginNames)]


def is_known_plugin(notify_plugin: NotifyPlugin) -> TypeGuard[KnownPlugins]:
    return notify_plugin[0] in get_builtin_plugin_names()


NotifyPluginParamsList = list[str]
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
    | SpectrumPluginModel
    | SplunkPluginModel
    | MicrosoftTeamsPluginModel
    | dict[str, Any]
)

NotifyPluginParams = NotifyPluginParamsList | NotifyPluginParamsDict


custom_plugin_type_adapter = TypeAdapter(CustomPluginType)
known_plugin_type_adapter = TypeAdapter(KnownPlugins)


def validate_plugin(value: Any, _handler: ValidationInfo) -> NotifyPlugin:
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
    notify_plugin: Annotated[NotifyPlugin, PlainValidator(validate_plugin)]


class EventRule(_EventRuleMandatory, total=False):
    """Event Rule

    used to be dict[str, Any], feel free to add stuff"""

    user_id: str | None
    comment: str
    docu_url: str
    alert_handler: tuple[HandlerName, HandlerParameters]
    contact: str
    contact_emails: list[str]
    contact_groups: list[str]
    contact_match_groups: list[str]
    contact_match_macros: list[tuple[str, str]]
    contact_users: list[str]
    match_attempt: tuple[int, int]
    match_checktype: list[str]
    match_contactgroups: list[str]
    match_contacts: list[str]
    match_ec: ConditionEventConsoleAlertsType | Literal[False]
    match_escalation: tuple[int, int]
    match_escalation_throttle: tuple[int, int]
    match_exclude_hosts: list[str]
    match_exclude_servicegroups: list[str]
    match_exclude_servicegroups_regex: MatchServiceGroupsRegex
    match_exclude_services: list[str]
    match_folder: str
    match_host_event: Sequence[HostEventType]
    match_hostgroups: list[str]
    match_hostlabels: dict[str, str]
    match_hosts: list[str]
    match_hosttags: list[str]
    match_notification_comment: str
    match_plugin_output: str
    match_service_event: Sequence[ServiceEventType]
    match_servicegroups: list[str]
    match_servicegroups_regex: MatchServiceGroupsRegex
    match_servicelabels: dict[str, str]
    match_services: list[str]
    match_site: list[str]
    match_sl: tuple[int, int]
    match_timeperiod: TimeperiodName
    bulk: NotifyBulkType
    match_service_level: tuple[int, int]
    match_only_during_timeperiod: str


NotifyRuleInfo = tuple[str, EventRule, str]
NotifyPluginName = str
NotifyPluginInfo = tuple[
    ContactName,
    NotificationPluginNameStr,
    NotifyPluginParams,
    NotifyBulkParameters | None,
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


class EventContext(TypedDict, total=False):
    """Used to be dict[str, Any]"""

    CONTACTNAME: str
    CONTACTS: str
    DATE: str
    EC_COMMENT: str
    EC_FACILITY: str
    EC_PRIORITY: str
    EC_RULE_ID: str
    HOSTATTEMPT: str
    HOSTCONTACTGROUPNAMES: str
    HOSTFORURL: str
    HOSTGROUPNAMES: str
    HOSTNAME: HostName
    HOSTNOTIFICATIONNUMBER: str
    HOSTOUTPUT: str
    HOSTSTATE: Literal["UP", "DOWN", "UNREACHABLE"]
    HOSTTAGS: str
    HOSTURL: str
    HOST_SL: str
    LASTHOSTSTATE: str
    LASTHOSTSTATECHANGE: str
    LASTHOSTSTATECHANGE_REL: str
    LASTHOSTUP: str
    LASTHOSTUP_REL: str
    LASTSERVICEOK: str
    LASTSERVICEOK_REL: str
    LASTSERVICESTATE: str
    LASTSERVICESTATECHANGE: str
    LASTSERVICESTATECHANGE_REL: str
    LOGDIR: str
    LONGDATETIME: str
    LONGSERVICEOUTPUT: str
    MICROTIME: str
    MONITORING_HOST: str
    NOTIFICATIONCOMMENT: str
    NOTIFICATIONTYPE: NotificationType
    OMD_ROOT: str
    OMD_SITE: str
    PREVIOUSHOSTHARDSTATE: str
    PREVIOUSSERVICEHARDSTATE: str
    SERVICEATTEMPT: str
    SERVICECHECKCOMMAND: str
    SERVICECONTACTGROUPNAMES: str
    SERVICEDESC: str
    SERVICEFORURL: str
    SERVICEGROUPNAMES: str
    SERVICENOTIFICATIONNUMBER: str
    SERVICEOUTPUT: str
    SERVICESTATE: str
    SERVICEURL: str
    SHORTDATETIME: str
    SVC_SL: str
    WHAT: Literal["SERVICE", "HOST"]

    # Dynamically added:
    # HOSTLABEL_*: str
    # SERVICELABEL_*: str

    # Dynamically added:
    # # Add short variants for state names (at most 4 characters)
    # for key, value in list(raw_context.items()):
    #     if key.endswith("STATE"):
    #         raw_context[key[:-5] + "SHORTSTATE"] = value[:4]
    # We know of:
    HOSTSHORTSTATE: str
    LASTHOSTSHORTSTATE: str
    LASTSERVICESHORTSTATE: str
    PREVIOUSHOSTHARDSHORTSTATE: str
    PREVIOUSSERVICEHARDSHORTSTATE: str
    SERVICESHORTSTATE: str


class ECEventContext(EventContext, total=False):
    """The keys "found" in cmk.ec

    Not sure if subclassing EventContext is the right call...
    Feel free to merge if you feel like doing it.
    """

    EC_CONTACT: str
    EC_CONTACT_GROUPS: str
    EC_ID: str
    EC_MATCH_GROUPS: str
    EC_ORIG_HOST: str
    EC_OWNER: str
    EC_PHASE: str
    EC_PID: str
    HOSTADDRESS: str
    HOSTALIAS: str
    HOSTDOWNTIME: str
    LASTSERVICESTATEID: str
    NOTIFICATIONAUTHOR: str
    NOTIFICATIONAUTHORALIAS: str
    NOTIFICATIONAUTHORNAME: str
    SERVICEACKAUTHOR: str
    SERVICEACKCOMMENT: str
    SERVICEPERFDATA: str
    SERVICEPROBLEMID: str
    SERVICESTATEID: str
    SERVICE_EC_CONTACT: str
    SERVICE_SL: str

    # Dynamically added:
    # HOST_*: str  #  custom_variables
