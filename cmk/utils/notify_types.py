#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Literal, Mapping, NewType, Sequence, TypedDict, Union

from cmk.utils.timeperiod import TimeperiodName
from cmk.utils.type_defs.host import HostName

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

NotifyPluginParamsList = list[str]
NotifyPluginParamsDict = dict[str, Any]  # TODO: Improve this
NotifyPluginParams = NotifyPluginParamsList | NotifyPluginParamsDict
NotifyBulkParameters = dict[str, Any]  # TODO: Improve this
NotifyBulkType = tuple[Literal["always", "timeperiod"], NotifyBulkParameters]

PluginOption = Literal[
    "cancel_previous_notifications",
    "create_notification_with_the_following_parameters",
    "create_notification_with_the_following_custom_parameters",
]


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

BuiltInPluginNames = Literal[
    "asciimail",
    "cisco_webex_teams",
    "mkeventd",
    "mail",
    "ilert",
    "jira_issues",
    "opsgenie_issues",
    "pagerduty",
    "pushover",
    "servicenow",
    "signl4",
    "slack",
    "sms_api",
    "sms",
    "spectrum",
    "victorops",
    "msteams",
]
CustomPluginName = NewType("CustomPluginName", str)

NotificationPluginNameStr = BuiltInPluginNames | CustomPluginName

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
HostTagIpAddressFamilyType = Literal[
    "ip-v4-only",
    "ip-v6-only",
    "ip-v4v6",
    "no-ip",
    "!ip-v4-only",
    "!ip-v6-only",
    "!ip-v4v6",
    "!no-ip",
    "ignore",
]
HostTagIpV4Type = Literal[
    "ip-v4",
    "!ip-v4",
    "ignore",
]
HostTagIpV6Type = Literal[
    "ip-v6",
    "!ip-v6",
    "ignore",
]
HostTagCheckMkAgentType = Literal[
    "cmk-agent",
    "!cmk-agent",
    "all-agents",
    "!all-agents",
    "special-agents",
    "!special-agents",
    "no-agent",
    "!no-agent",
    "ignore",
]
HostTagPiggyBackType = Literal[
    "auto-piggyback",
    "!auto-piggyback",
    "piggyback",
    "!piggyback",
    "no-piggyback",
    "!no-piggyback",
    "ignore",
]
HostTagSNMPType = Literal[
    "no-snmp",
    "!no-snmp",
    "snmp-v1",
    "!snmp-v1",
    "snmp-v2",
    "!snmp-v2",
    "ignore",
]
HostTagMonitorSNMPType = Literal[
    "snmp",
    "!snmp",
    "ignore",
]
HostTagAgentOrSpecialAgentType = Literal[
    "tcp",
    "!tcp",
    "ignore",
]
HostTagAgentType = Literal[
    "checkmk-agent",
    "!checkmk-agent",
    "ignore",
]
HostTagPingType = Literal[
    "ping",
    "!ping",
    "ignore",
]
HostTagCriticalType = Literal[
    "prod",
    "critical",
    "test",
    "offline",
    "!prod",
    "!critical",
    "!test",
    "!offline",
    "ignore",
]
HostTagNetworkType = Literal[
    "lan",
    "wan",
    "dmz",
    "ignore",
    "!lan",
    "!wan",
    "!dmz",
]

HostTagTypes = list[
    HostTagIpAddressFamilyType
    | HostTagIpV4Type
    | HostTagIpV6Type
    | HostTagCheckMkAgentType
    | HostTagPiggyBackType
    | HostTagSNMPType
    | HostTagMonitorSNMPType
    | HostTagAgentOrSpecialAgentType
    | HostTagAgentType
    | HostTagPingType
    | HostTagCriticalType
    | HostTagNetworkType
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

NoProxy = tuple[Literal["no_proxy"], None]
EnvProxy = tuple[Literal["environment"], Literal["environment"]]
UrlProxy = tuple[Literal["url"], str]
ProxyUrl = Union[NoProxy, EnvProxy, UrlProxy]

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
ServiceLevels = Literal[
    0,
    10,
    20,
    30,
]
ServiceLevelsType = tuple[
    ServiceLevels,
    ServiceLevels,
]
ServiceLevelsStr = Literal[
    "no_service_level",
    "silver",
    "gold",
    "platinum",
]
ServiceLevelsMap = Mapping[
    ServiceLevels,
    ServiceLevelsStr,
]
RegexModes = Literal[
    "match_id",
    "match_alias",
]
MatchRegex = tuple[
    RegexModes,
    list[str],
]


class URLPrefix(TypedDict, total=False):
    automatic: Literal["http", "https"]
    manual: str


class SMTPAuth(TypedDict, total=False):
    method: Literal["plaintext"]
    password: str
    user: str


class SyncDeliverySMTP(TypedDict, total=False):
    auth: SMTPAuth
    encryption: Literal["ssl_tls", "starttls"]
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
NotifyPlugin = tuple[NotificationPluginNameStr, NotifyPluginParams | None]
NotificationRuleID = NewType("NotificationRuleID", str)


class _EventRuleMandatory(TypedDict):
    rule_id: NotificationRuleID
    allow_disable: bool
    contact_all: bool
    contact_all_with_email: bool
    contact_object: bool
    description: str
    disabled: bool
    notify_plugin: NotifyPlugin


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
    match_hosttags: HostTagTypes
    match_notification_comment: str
    match_plugin_output: str
    match_service_event: Sequence[ServiceEventType]
    match_servicegroups: list[str]
    match_servicegroups_regex: MatchServiceGroupsRegex
    match_servicelabels: dict[str, str]
    match_services: list[str]
    match_site: list[str]
    match_sl: ServiceLevelsType
    match_timeperiod: TimeperiodName
    notify_method: NotifyPluginParams
    bulk: NotifyBulkType
    match_service_level: ServiceLevelsType
    match_only_during_timeperiod: str
    notification_method: NotificationPluginNameStr


NotifyRuleInfo = tuple[str, EventRule, str]
NotifyPluginName = str
NotifyPluginInfo = tuple[
    ContactName, NotificationPluginNameStr, NotifyPluginParams, NotifyBulkParameters | None
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
