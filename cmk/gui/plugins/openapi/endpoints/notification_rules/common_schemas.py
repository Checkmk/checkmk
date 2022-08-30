#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, get_args, Type

from marshmallow import post_dump, post_load, ValidationError
from marshmallow.schema import Schema
from marshmallow_oneofschema import OneOfSchema  # type: ignore[import]

from cmk.utils.notify_types import (
    BuiltInPluginNames,
    EmailBodyElementsType,
    GroupbyType,
    HostTagAgentOrSpecialAgentType,
    HostTagAgentType,
    HostTagCheckMkAgentType,
    HostTagCriticalType,
    HostTagIpAddressFamilyType,
    HostTagIpV4Type,
    HostTagIpV6Type,
    HostTagMonitorSNMPType,
    HostTagNetworkType,
    HostTagPiggyBackType,
    HostTagPingType,
    HostTagSNMPType,
    IlertPriorityType,
    MgmntPriorityType,
    MgmntUrgencyType,
    OpsGeniePriorityStrType,
    PushOverPriorityStringType,
    RegexModes,
    ServiceLevelsStr,
    SoundType,
    SysLogFacilityStrType,
    SysLogPriorityStrType,
)

from cmk.gui.fields import (
    ContactGroupField,
    FolderIDField,
    GroupField,
    HostField,
    IPField,
    PasswordStoreIDField,
    SiteField,
    SplunkURLField,
    TimePeriodIDField,
)
from cmk.gui.fields.utils import BaseSchema
from cmk.gui.rest_api_types.notifications_rule_types import CASE_STATE_TYPE, INCIDENT_STATE_TYPE

from cmk import fields


class Checkbox(BaseSchema):
    state = fields.String(
        enum=["enabled", "disabled"],
        required=True,
        description="",
        example="",
    )


class CheckboxOneOfSchema(OneOfSchema):
    type_field = "state"
    type_field_remove = False

    def __init__(self, value_schema: Type[Schema], *args: Any, **kwargs: Any) -> None:
        self.type_schemas = {"disabled": Checkbox, "enabled": value_schema}
        super().__init__(*args, **kwargs)


class HttpProxy(BaseSchema):
    option = fields.String(
        enum=["no_proxy", "environment", "url"],
        required=True,
        example="",
    )
    url = fields.String(
        required=False,
        example="http://example_proxy",
    )


class HttpProxyValue(Checkbox):
    value = fields.Nested(
        HttpProxy,
        description="Use the proxy settings from the environment variables. The variables NO_PROXY, HTTP_PROXY and HTTPS_PROXY are taken into account during execution. Have a look at the python requests module documentation for further information. Note that these variables must be defined as a site-user in ~/etc/environment and that this might affect other notification methods which also use the requests module",
    )


CHECKMK_URL_PREFIX_URL = fields.String(
    required=True,
    example="http://example_url_prefix",
)

CHECKMK_PREFIX_SCHEMA = fields.String(
    enum=["http", "https"],
    required=True,
    example="http",
)
CHECKMK_URL_PREFIX_OPTION = fields.String(
    enum=["manual", "automatic"],
    required=True,
    example="automatic",
)


class CheckMKURLPrefixBase(BaseSchema):
    option = CHECKMK_URL_PREFIX_OPTION


class CheckMKURLPrefixAuto(CheckMKURLPrefixBase):
    schema = CHECKMK_PREFIX_SCHEMA


class CheckMKURLPrefixManual(CheckMKURLPrefixBase):
    url = CHECKMK_URL_PREFIX_URL


class ManualOrAutomaticSelector(OneOfSchema):
    type_field = "option"
    type_field_remove = False
    type_schemas = {
        "automatic": CheckMKURLPrefixAuto,
        "manual": CheckMKURLPrefixManual,
    }


class CheckMKURLPrefixValue(Checkbox):
    value = fields.Nested(
        ManualOrAutomaticSelector,
        description="If you use Automatic HTTP/s, the URL prefix for host and service links within the notification is filled automatically. If you specify an URL prefix here, then several parts of the notification are armed with hyperlinks to your Check_MK GUI. In both cases, the recipient of the notification can directly visit the host or service in question in Check_MK. Specify an absolute URL including the .../check_mk/",
    )


class URLPrefixForLinksToCheckMk(BaseSchema):
    option = CHECKMK_URL_PREFIX_OPTION
    schema = CHECKMK_PREFIX_SCHEMA
    url = CHECKMK_URL_PREFIX_URL


class URLPrefixForLinksToCheckMkCheckbox(Checkbox):
    value = fields.Nested(
        URLPrefixForLinksToCheckMk,
        description="If you use Automatic HTTP/s, the URL prefix for host and service links within the notification is filled automatically. If you specify an URL prefix here, then several parts of the notification are armed with hyperlinks to your Check_MK GUI. In both cases, the recipient of the notification can directly visit the host or service in question in Check_MK. Specify an absolute URL including the .../check_mk/",
    )


DISABLE_SSL_CERT_VERIFICATION = fields.Nested(
    Checkbox,
    required=True,
    description="Ignore unverified HTTPS request warnings. Use with caution.",
)

USERNAME = fields.String(
    required=True,
    example="username_a",
    description="Configure the user name here",
)


HTTP_PROXY_CREATE = fields.Nested(
    CheckboxOneOfSchema(HttpProxyValue),
    required=True,
    description="Use the proxy settings from the environment variables. The variables NO_PROXY, HTTP_PROXY and HTTPS_PROXY are taken into account during execution.",
)

HTTP_PROXY_RESPONSE = fields.Nested(
    HttpProxyValue,
    required=True,
    example={},
    description="",
)

URL_PREFIX_FOR_LINKS_TO_CHECKMK_CREATE = fields.Nested(
    CheckboxOneOfSchema(CheckMKURLPrefixValue),
    required=True,
)

URL_PREFIX_FOR_LINKS_TO_CHECKMK_RESPONSE = fields.Nested(
    URLPrefixForLinksToCheckMkCheckbox,
    required=True,
)


class CustomMacro(BaseSchema):
    macro_name = fields.String(
        required=True,
        description="The name of the macro",
        example="macro_1",
    )
    match_regex = fields.String(
        required=True,
        description="The text entered here is handled as a regular expression pattern",
        example="[A-Z]+",
    )


class MatchCustomMacros(Checkbox):
    value = fields.List(
        fields.Nested(CustomMacro),
        required=False,
    )


class CheckboxWithStr(Checkbox):
    value = fields.String(
        required=True,
    )


class CheckboxWithListOfStr(Checkbox):
    value = fields.List(
        fields.String,
        required=True,
    )


class CheckboxWithListOfContactGroups(Checkbox):
    value = fields.List(
        ContactGroupField(presence="should_exist"),
        required=True,
        uniqueItems=True,
    )


class CheckboxWithListOfEmailAddresses(Checkbox):
    value = fields.List(
        fields.Email,
        required=True,
        description="You may paste a text from your clipboard which contains several parts separated by ';' characters into the last input field. The text will then be split by these separators and the single parts are added into dedicated input fields",
        example=["email1@tribe.com", "email2@tribe.com"],
        uniqueItems=True,
    )


class CheckboxWithListOfSites(Checkbox):
    value = fields.List(
        SiteField(presence="should_exist"),
        required=True,
        description="Match only hosts of the selected sites.",
        example=["site_1", "site_2"],
    )


class CheckboxWithFolderStr(Checkbox):
    value = FolderIDField(
        presence="should_exist",
        required=True,
        description="This condition makes the rule match only hosts that are managed via WATO and that are contained in this folder - either directly or in one of its subfolders.",
    )


class HostTagValues(BaseSchema):
    ip_address_family = fields.String(
        enum=list(get_args(HostTagIpAddressFamilyType)),
        required=True,
        example="no-ip",
    )
    ip_v4 = fields.String(
        enum=list(get_args(HostTagIpV4Type)),
        required=True,
        example="ip-v4",
    )
    ip_v6 = fields.String(
        enum=list(get_args(HostTagIpV6Type)),
        required=True,
        example="!ip-v6",
    )

    checkmk_agent_api_integration = fields.String(
        enum=list(get_args(HostTagCheckMkAgentType)),
        required=True,
        example="special-agents",
    )

    piggyback = fields.String(
        enum=list(get_args(HostTagPiggyBackType)),
        required=True,
        example="auto-piggyback",
    )

    snmp = fields.String(
        enum=list(get_args(HostTagSNMPType)),
        required=True,
        example="snmp-v2",
    )

    monitor_via_snmp = fields.String(
        enum=list(get_args(HostTagMonitorSNMPType)),
        required=True,
        example="snmp",
    )

    monitor_via_checkmkagent_or_specialagent = fields.String(
        enum=list(get_args(HostTagAgentOrSpecialAgentType)),
        required=True,
        example="tcp",
    )

    monitor_via_checkmkagent = fields.String(
        enum=list(get_args(HostTagAgentType)),
        required=True,
        example="checkmk-agent",
    )

    only_ping_this_device = fields.String(
        enum=list(get_args(HostTagPingType)),
        required=True,
        example="ping",
    )

    criticality = fields.String(
        enum=list(get_args(HostTagCriticalType)),
        required=True,
        example="critical",
    )

    networking_segment = fields.String(
        enum=list(get_args(HostTagNetworkType)),
        required=True,
        example="lan",
    )


class CheckboxMatchHostTags(Checkbox):
    value = fields.Nested(
        HostTagValues,
        required=True,
        description="Match host tags with the following parameters",
    )


class CheckboxWithListOfHostGroups(Checkbox):
    value = fields.List(
        GroupField(
            group_type="host",
            should_exist=True,
            example="host_group_1",
        ),
        example=["host_group1", "host_group2"],
        description="The host must be in one of the selected host groups",
        required=True,
        uniqueItems=True,
    )


class CheckboxWithListOfHosts(Checkbox):
    value = fields.List(
        HostField(should_exist=True),
        required=True,
        example=["host_1", "host_2"],
        description="",
        uniqueItems=True,
    )


class CheckboxLabel(BaseSchema):
    key = fields.String(
        required=True,
        example="cmk/os_family",
    )
    value = fields.String(
        required=True,
        example="linux",
    )


class CheckboxWithListOfLabels(Checkbox):
    value = fields.List(
        fields.Nested(CheckboxLabel),
        required=True,
        description="A list of key, value label pairs",
    )


class CheckboxWithListOfServiceGroups(Checkbox):
    value = fields.List(
        GroupField(
            group_type="service",
            should_exist=True,
            example="service_group_1",
        ),
        required=True,
    )


class CheckboxWithListOfCheckTypes(Checkbox):
    value = fields.List(  # TODO: validate check types, maybe?
        fields.String,
        required=True,
        uniqueItems=True,
        example=["3par_capacity", "acme_fan", "acme_realm"],
        description="Only apply the rule if the notification originates from certain types of check plugins. Note: Host notifications never match this rule if this option is being used",
    )


class ServiceGroupsRegex(BaseSchema):
    match_type = fields.String(
        enum=list(get_args(RegexModes)),
        required=True,
        example="match_alias",
    )
    regex_list = fields.List(
        fields.String,
        required=True,
        uniqueItems=True,
        example=["[A-Z]+123", "[A-Z]+456"],
        description="The text entered in this list is handled as a regular expression pattern",
    )


class CheckboxWithListOfServiceGroupsRegex(Checkbox):
    value = fields.Nested(
        ServiceGroupsRegex,
        required=True,
        description="The service group alias must not match one of the following regular expressions. For host events this condition is simply ignored. The text entered here is handled as a regular expression pattern. The pattern is applied as infix search. Add a leading ^ to make it match from the beginning and/or a tailing $ to match till the end of the text. The match is performed case sensitive. Read more about regular expression matching in Checkmk in our user guide. You may paste a text from your clipboard which contains several parts separated by ';' characters into the last input field. The text will then be split by these separators and the single parts are added into dedicated input field",
    )


class FromToServiceLevels(BaseSchema):
    from_level = fields.String(
        enum=list(get_args(ServiceLevelsStr)),
        required=True,
        example="gold",
    )
    to_level = fields.String(
        enum=list(get_args(ServiceLevelsStr)),
        required=True,
        example="gold",
    )


class CheckboxWithFromToServiceLevels(Checkbox):
    value = fields.Nested(
        FromToServiceLevels,
        required=True,
        description="Host or service must be in the following service level to get notification",
    )


class CheckboxWithTimePeriod(Checkbox):
    value = TimePeriodIDField(
        presence="should_exist",
        required=True,
        description="Match this rule only during times where the selected time period from the monitoring system is active",
    )


class HostOrServiceEventTypeCommon(BaseSchema):
    start_or_end_of_flapping_state = fields.Boolean(
        required=True,
        example=True,
    )
    start_or_end_of_scheduled_downtime = fields.Boolean(
        required=True,
        example=True,
    )
    acknowledgement_of_problem = fields.Boolean(
        required=True,
        example=False,
    )
    alert_handler_execution_successful = fields.Boolean(
        required=True,
        example=True,
    )
    alert_handler_execution_failed = fields.Boolean(
        required=True,
        example=False,
    )


class HostEventType(HostOrServiceEventTypeCommon):
    up_down = fields.Boolean(
        required=True,
        example=True,
    )
    up_unreachable = fields.Boolean(
        required=True,
        example=False,
    )
    down_up = fields.Boolean(
        required=True,
        example=True,
    )
    down_unreachable = fields.Boolean(
        required=True,
        example=False,
    )
    unreachable_down = fields.Boolean(
        required=True,
        example=False,
    )
    unreachable_up = fields.Boolean(
        required=True,
        example=False,
    )
    any_up = fields.Boolean(
        required=True,
        example=False,
    )
    any_down = fields.Boolean(
        required=True,
        example=True,
    )
    any_unreachable = fields.Boolean(
        required=True,
        example=True,
    )


class ServiceEventType(HostOrServiceEventTypeCommon):
    ok_warn = fields.Boolean(
        required=True,
        example=True,
    )
    ok_ok = fields.Boolean(
        required=True,
        example=True,
    )
    ok_crit = fields.Boolean(
        required=True,
        example=False,
    )
    ok_unknown = fields.Boolean(
        required=True,
        example=True,
    )
    warn_ok = fields.Boolean(
        required=True,
        example=False,
    )
    warn_crit = fields.Boolean(
        required=True,
        example=False,
    )
    warn_unknown = fields.Boolean(
        required=True,
        example=False,
    )
    crit_ok = fields.Boolean(
        required=True,
        example=True,
    )
    crit_warn = fields.Boolean(
        required=True,
        example=True,
    )
    crit_unknown = fields.Boolean(
        required=True,
        example=True,
    )
    unknown_ok = fields.Boolean(
        required=True,
        example=True,
    )
    unknown_warn = fields.Boolean(
        required=True,
        example=True,
    )
    unknown_crit = fields.Boolean(
        required=True,
        example=True,
    )
    any_ok = fields.Boolean(
        required=True,
        example=False,
    )
    any_warn = fields.Boolean(
        required=True,
        example=False,
    )
    any_crit = fields.Boolean(
        required=True,
        example=True,
    )
    any_unknown = fields.Boolean(
        required=True,
        example=False,
    )


class CheckboxHostEventType(Checkbox):
    value = fields.Nested(
        HostEventType,
        required=True,
        description="Select the host event types and transitions this rule should handle. Note: If you activate this option and do not also specify service event types then this rule will never hold for service notifications! Note: You can only match on event types created by the core.",
    )


class CheckboxServiceEventType(Checkbox):
    value = fields.Nested(
        ServiceEventType,
        required=True,
        description="Select the service event types and transitions this rule should handle. Note: If you activate this option and do not also specify host event types then this rule will never hold for host notifications! Note: You can only match on event types created by the core",
    )


class FromToNotificationNumbers(BaseSchema):
    beginning_from = fields.Integer(
        required=True,
        example=1,
        description="Let through notifications counting from this number. The first notification always has the number 1",
    )
    up_to = fields.Integer(
        required=True,
        example=999999,
        description="Let through notifications counting upto this number",
    )


class CheckboxRestrictNotificationNumbers(Checkbox):
    value = fields.Nested(
        FromToNotificationNumbers,
        required=True,
    )


class ThrottlePeriodicNotifications(BaseSchema):
    beginning_from = fields.Integer(
        required=True,
        example=10,
        description="Beginning notification number",
    )
    send_every_nth_notification = fields.Integer(
        required=True,
        example=5,
        description="The rate then you will receive the notification 1 through 10 and then 15, 20, 25... and so on",
    )


class CheckboxThrottlePeriodicNotifcations(Checkbox):
    value = fields.Nested(
        ThrottlePeriodicNotifications,
        required=True,
    )


class CheckboxWithListOfRuleIds(Checkbox):
    value = fields.List(
        fields.String,
        uniqueItems=True,
        required=True,
        example="",
        description="",
    )


class SysLogToFromPriorities(BaseSchema):
    from_priority = fields.String(
        enum=list(get_args(SysLogPriorityStrType)),
        required=True,
        example="warning",
        description="",
    )
    to_priority = fields.String(
        enum=list(get_args(SysLogPriorityStrType)),
        required=True,
        example="warning",
        description="",
    )


class CheckboxWithSysLogPriority(Checkbox):
    value = fields.Nested(
        SysLogToFromPriorities,
        required=False,
    )


class CheckboxWithSysLogFacility(Checkbox):
    value = fields.String(
        enum=list(get_args(SysLogFacilityStrType)),
        required=False,
        example="kern",
        description="",
    )


class CheckboxWithMgmtTypePriorityValue(Checkbox):
    value = fields.String(
        enum=list(get_args(MgmntPriorityType)),
        required=True,
    )


class CheckboxWithMgmtTypeUrgencyValue(Checkbox):
    value = fields.String(
        enum=list(get_args(MgmntUrgencyType)),
        required=True,
    )


class CheckboxWithStrValue(Checkbox):
    value = fields.String(
        required=True,
    )


EVENT_CONSOLE_ALERT_MATCH_TYPE = fields.String(
    enum=["match_only_event_console_alerts", "do_not_match_event_console_alerts"],
    required=True,
    example="match_only_event_console_events",
    description="",
)


class EventConsoleAlertAttributesBase(BaseSchema):
    match_type = EVENT_CONSOLE_ALERT_MATCH_TYPE


class EventConsoleAlertAttrsCreate(BaseSchema):
    match_rule_ids = fields.Nested(
        CheckboxOneOfSchema(CheckboxWithListOfRuleIds),
    )
    match_syslog_priority = fields.Nested(
        CheckboxOneOfSchema(CheckboxWithSysLogPriority),
    )
    match_syslog_facility = fields.Nested(
        CheckboxOneOfSchema(CheckboxWithSysLogFacility),
    )
    match_event_comment = fields.Nested(
        CheckboxOneOfSchema(CheckboxWithStrValue),
    )


class EventConsoleAlertAttributes(EventConsoleAlertAttributesBase):
    values = fields.Nested(
        EventConsoleAlertAttrsCreate,
        required=True,
    )


class MatchTypeSelector(OneOfSchema):
    type_field = "match_type"
    type_field_remove = False
    type_schemas = {
        "match_only_event_console_alerts": EventConsoleAlertAttributes,
        "do_not_match_event_console_alerts": EventConsoleAlertAttributesBase,
    }


class CheckboxEventConsoleAlerts(Checkbox):
    value = fields.Nested(
        MatchTypeSelector,
        required=True,
        description="The Event Console can have events create notifications in Check_MK. These notifications will be processed by the rule based notification system of Check_MK. This matching option helps you distinguishing and also gives you access to special event fields",
    )


class EventConsoleAlertAttrsResponse(BaseSchema):
    match_rule_ids = fields.Nested(CheckboxWithListOfStr)
    match_syslog_priority = fields.Nested(CheckboxWithSysLogPriority)
    match_syslog_facility = fields.Nested(CheckboxWithStr)
    match_event_comment = fields.Nested(CheckboxWithStr)


class EventConsoleAlertsResponse(Checkbox):
    match_type = EVENT_CONSOLE_ALERT_MATCH_TYPE
    values = fields.Nested(
        EventConsoleAlertAttrsResponse,
        required=False,
    )

    @post_dump
    def _post_dump(self, data, many, **kwargs):
        if data.get("values") == {}:
            del data["values"]
        return data


class MatchEventConsoleAlertsResponse(Checkbox):
    value = fields.Nested(
        EventConsoleAlertsResponse,
    )


class SubjectForHostNotificationsCheckbox(Checkbox):
    value = fields.String(
        required=False,
        description="Here you are allowed to use all macros that are defined in the notification context.",
        example="Check_MK: $HOSTNAME$ - $EVENT_TXT$",
    )


class SubjectForServiceNotificationsCheckbox(Checkbox):
    value = fields.String(
        required=False,
        description="Here you are allowed to use all macros that are defined in the notification context.",
        example="Check_MK: $HOSTNAME$/$SERVICEDESC$ $EVENT_TXT$",
    )


class Authentication(BaseSchema):
    method = fields.String(
        enum=["plaintext"],
        required=False,
        description="",
        example="plaintext",
    )
    user = fields.String(
        required=False,
        description="",
        example="",
    )
    password = fields.String(
        required=False,
        description="",
        example="",
    )


class AuthenticationValue(Checkbox):
    value = fields.Nested(
        Authentication,
    )


class EmailAndDisplayName(BaseSchema):
    address = fields.String(
        required=False,
        description="",
        example="mat@tribe29.com",
    )
    display_name = fields.String(
        required=False,
        description="",
        example="",
    )


class FromEmailAndNameCheckbox(Checkbox):
    value = fields.Nested(
        EmailAndDisplayName,
        description="The email address and visible name used in the From header of notifications messages. If no email address is specified the default address is OMD_SITE@FQDN is used. If the environment variable OMD_SITE is not set it defaults to checkmk",
    )


class ToEmailAndNameCheckbox(Checkbox):
    value = fields.Nested(
        EmailAndDisplayName,
        description="The email address and visible name used in the Reply-To header of notifications messages",
    )


class GraphsPerNotification(Checkbox):
    value = fields.Integer(
        required=True,
        description="Sets a limit for the number of graphs that are displayed in a notification",
        example=5,
    )


class BulkNotificationsWithGraphs(Checkbox):
    value = fields.Integer(
        required=True,
        description="Sets a limit for the number of notifications in a bulk for which graphs are displayed. If you do not use bulk notifications this option is ignored. Note that each graph increases the size of the mail and takes time to renderon the monitoring server. Therefore, large bulks may exceed the maximum size for attachements or the plugin may run into a timeout so that a failed notification is produced",
        example=5,
    )


class CheckboxSortOrderValue(Checkbox):
    value = fields.String(
        enum=["oldest_first", "newest_first"],
        required=True,
        description="With this option you can specify, whether the oldest (default) or the newest notification should get shown at the top of the notification mail",
        example="oldest_first",
    )


class HtmlSectionBetweenBodyAndTableCheckbox(Checkbox):
    value = fields.String(
        required=False,
        description="Insert HTML section between body and table",
        example="<HTMLTAG>CONTENT</HTMLTAG>",
    )


class CheckboxWithListOfEmailInfoStrs(Checkbox):
    value = fields.List(
        fields.String(enum=list(get_args(EmailBodyElementsType))),
        required=True,
        description="Information to be displayed in the email body.",
        example=["abstime", "graph"],
        uniqueItems=True,
    )


class CheckboxSysLogFacilityToUseValue(Checkbox):
    value = fields.String(
        enum=list(get_args(SysLogFacilityStrType)),
        required=False,
        description="",
        example="",
    )


class EnableSynchronousDeliveryViaSMTP(BaseSchema):
    auth = fields.Nested(
        AuthenticationValue,
    )
    encryption = fields.String(
        required=False,
        description="",
        example="ssl/tls",
    )
    port = fields.Integer(
        required=False,
        description="",
        example=25,
    )
    smarthosts = fields.List(
        fields.String(),
        uniqueItems=True,
    )


class EnableSynchronousDeliveryViaSMTPValue(Checkbox):
    value = fields.Nested(
        EnableSynchronousDeliveryViaSMTP,
    )


class CheckBoxIPAddressValue(Checkbox):
    value = IPField(
        ip_type_allowed="ipv4",
        required=True,
    )


class CheckboxOpsGeniePriorityValue(Checkbox):
    value = fields.String(
        enum=list(get_args(OpsGeniePriorityStrType)),
        required=True,
        description="",
        example="moderate",
    )


class CheckBoxUseSiteIDPrefix(Checkbox):
    value = fields.String(
        enum=["use_site_id_prefix", "deactivated"],
        required=True,
        description="",
        example="use_site_id",
    )


class PushOverPriority(Checkbox):
    value = fields.String(  # TODO: Emergency is Nested
        enum=list(get_args(PushOverPriorityStringType)),
        required=True,
        description="The pushover priority level",
        example="normal",
    )


class Sounds(Checkbox):
    value = fields.String(
        enum=list(get_args(SoundType)),
        required=True,
        description="See https://pushover.net/api#sounds for more information and trying out available sounds.",
        example="none",
    )


# ===================================================================================


PASSWORD_STORE_ID_SHOULD_EXIST = PasswordStoreIDField(
    presence="should_exist",
    required=True,
)


class ExplicitOrStoreOptions(BaseSchema):
    option = fields.String(
        enum=["store", "explicit"],
        required=True,
        example="store",
    )


# ====================================== CISCO AUTH
class WebhookURLResponse(ExplicitOrStoreOptions):
    store_id = PasswordStoreIDField(presence="should_exist")
    url = fields.URL(
        example="http://example_webhook_url.com",
    )


class CiscoPasswordStore(ExplicitOrStoreOptions):
    store_id = PASSWORD_STORE_ID_SHOULD_EXIST


class CiscoExplicitWebhookUrl(ExplicitOrStoreOptions):
    url = fields.URL(
        required=True,
        example="http://example_webhook_url.com",
    )


class CiscoUrlOrStoreSelector(OneOfSchema):
    type_field = "option"
    type_field_remove = False
    type_schemas = {
        "explicit": CiscoExplicitWebhookUrl,
        "store": CiscoPasswordStore,
    }


# ====================================== ILERT AUTH


class IlertKeyResponse(ExplicitOrStoreOptions):
    store_id = PASSWORD_STORE_ID_SHOULD_EXIST
    key = fields.String(example="example_key")


class IlertPasswordStoreID(ExplicitOrStoreOptions):
    store_id = PASSWORD_STORE_ID_SHOULD_EXIST


class IlertAPIKey(ExplicitOrStoreOptions):
    key = fields.String(
        required=True,
        example="example_api_key",
    )


class IlertKeyOrStoreSelector(OneOfSchema):
    type_field = "option"
    type_field_remove = False
    type_schemas = {
        "explicit": IlertAPIKey,
        "store": IlertPasswordStoreID,
    }


# ====================================== Opsgenie AUTH
class OpsGeniePasswordResponse(ExplicitOrStoreOptions):
    store_id = PASSWORD_STORE_ID_SHOULD_EXIST
    key = fields.String(example="example key")


class OpsGenieStoreID(ExplicitOrStoreOptions):
    store_id = PASSWORD_STORE_ID_SHOULD_EXIST


class OpsGenieExplicitKey(ExplicitOrStoreOptions):
    key = fields.String(
        required=True,
        example="example_api_key",
    )


class OpsGenisStoreOrExplicitKeySelector(OneOfSchema):
    type_field = "option"
    type_field_remove = False
    type_schemas = {
        "explicit": OpsGenieExplicitKey,
        "store": OpsGenieStoreID,
    }


# ====================================== PagerDuty AUTH
class PagerDutyIntegrationKeyResponse(ExplicitOrStoreOptions):
    key = fields.String(example="some_key_example")
    store_id = PASSWORD_STORE_ID_SHOULD_EXIST


class PagerDutyAPIKeyStoreID(ExplicitOrStoreOptions):
    store_id = PASSWORD_STORE_ID_SHOULD_EXIST


class PagerDutyExplicitKey(ExplicitOrStoreOptions):
    key = fields.String(
        required=True,
        example="some_key_example",
    )


class PagerDutyStoreOrIntegrationKeySelector(OneOfSchema):
    type_field = "option"
    type_field_remove = False
    type_schemas = {
        "explicit": PagerDutyExplicitKey,
        "store": PagerDutyAPIKeyStoreID,
    }


# ====================================== ServiceNow AUTH
class ServiceNowPasswordResponse(ExplicitOrStoreOptions):
    store_id = PASSWORD_STORE_ID_SHOULD_EXIST
    password = fields.String(example="http://example_webhook_url.com")


class ServiceNowPasswordStoreID(ExplicitOrStoreOptions):
    store_id = PASSWORD_STORE_ID_SHOULD_EXIST


class ServiceNowExplicitPassword(ExplicitOrStoreOptions):
    password = fields.String(
        required=True,
        example="password_example",
    )


class ServiceNowPasswordSelector(OneOfSchema):
    type_field = "option"
    type_field_remove = False
    type_schemas = {
        "explicit": ServiceNowExplicitPassword,
        "store": ServiceNowPasswordStoreID,
    }


# ====================================== SignL4 AUTH
class SignL4TeamSecretResponse(ExplicitOrStoreOptions):
    store_id = PASSWORD_STORE_ID_SHOULD_EXIST
    secret = fields.String(example="http://example_webhook_url.com")


class SignL4TeamSecretStoreID(ExplicitOrStoreOptions):
    store_id = PASSWORD_STORE_ID_SHOULD_EXIST


class SignL4TeamSecret(ExplicitOrStoreOptions):
    secret = fields.String(
        required=True,
        example="team_secret_example",
    )


class SignL4ExplicitOrStoreSelector(OneOfSchema):
    type_field = "option"
    type_field_remove = False
    type_schemas = {
        "explicit": SignL4TeamSecret,
        "store": SignL4TeamSecretStoreID,
    }


# ====================================== Slack AUTH
class SlackWebhookURLResponse(ExplicitOrStoreOptions):
    store_id = PASSWORD_STORE_ID_SHOULD_EXIST
    url = fields.String(example="http://example_webhook_url.com")


class SlackWebhookStore(ExplicitOrStoreOptions):
    store_id = PASSWORD_STORE_ID_SHOULD_EXIST


class SlackWebhookURL(ExplicitOrStoreOptions):
    url = fields.String(
        required=True,
        example="https://example_webhook_url.com",
    )


class SlackStoreOrExplicitURLSelector(OneOfSchema):
    type_field = "option"
    type_field_remove = False
    type_schemas = {
        "explicit": SlackWebhookURL,
        "store": SlackWebhookStore,
    }


# ====================================== SMS API AUTH
class SMSAPIPAsswordResponse(ExplicitOrStoreOptions):
    store_id = PASSWORD_STORE_ID_SHOULD_EXIST
    password = fields.String(example="http://example_webhook_url.com")


class SMSAPIPStoreID(ExplicitOrStoreOptions):
    store_id = PASSWORD_STORE_ID_SHOULD_EXIST


class SMSAPIExplicitPassword(ExplicitOrStoreOptions):
    password = fields.String(
        required=True,
        example="https://example_webhook_url.com",
    )


class SMSAPIPasswordSelector(OneOfSchema):
    type_field = "option"
    type_field_remove = False
    type_schemas = {
        "explicit": SMSAPIExplicitPassword,
        "store": SMSAPIPStoreID,
    }


# ====================================== Splunk AUTH
class SplunkRESTEndpointResponse(ExplicitOrStoreOptions):
    store_id = PASSWORD_STORE_ID_SHOULD_EXIST
    url = fields.String(
        example="https://alert.victorops.com/integrations/example",
    )


class SplunkStoreID(ExplicitOrStoreOptions):
    store_id = PASSWORD_STORE_ID_SHOULD_EXIST


class SplunkURLExplicit(ExplicitOrStoreOptions):
    url = SplunkURLField(required=True)


class SplunkRESTEndpointSelector(OneOfSchema):
    type_field = "option"
    type_field_remove = False
    type_schemas = {
        "explicit": SplunkURLExplicit,
        "store": SplunkStoreID,
    }


# ====================================== MSTEams AUTH
class MSTeamsURLResponse(ExplicitOrStoreOptions):
    store_id = PASSWORD_STORE_ID_SHOULD_EXIST
    url = fields.String(example="http://example_webhook_url.com")


class MSTeamsExplicitWebhookUrl(ExplicitOrStoreOptions):
    url = fields.URL(
        required=True,
        example="http://example_webhook_url.com",
    )


class MSTeamsUrlOrStoreSelector(OneOfSchema):
    type_field = "option"
    type_field_remove = False
    type_schemas = {
        "explicit": MSTeamsExplicitWebhookUrl,
        "store": MSTeamsURLResponse,
    }


# ======================================


class ManagementTypeIncedentStates(BaseSchema):
    start_predefined = fields.String(
        enum=list(get_args(INCIDENT_STATE_TYPE)),
        example="hold",
    )
    start_integer = fields.Integer(
        example=1,
        minimum=0,
    )
    end_predefined = fields.String(
        enum=list(get_args(INCIDENT_STATE_TYPE)),
        example="resolved",
    )
    end_integer = fields.Integer(
        example=0,
        minimum=0,
    )


class CheckboxWithManagementTypeStateIncedentValues(Checkbox):
    value = fields.Nested(
        ManagementTypeIncedentStates,
    )


class ManagementTypeCaseStates(BaseSchema):
    start_predefined = fields.String(
        enum=list(get_args(CASE_STATE_TYPE)),
        example="new",
    )
    start_integer = fields.Integer(
        example=1,
        minimum=0,
    )


class CheckboxWithManagementTypeStateCaseValues(Checkbox):
    value = fields.Nested(
        ManagementTypeCaseStates,
    )


# ----------------------------------------------------------------


class ManagementTypeStates(BaseSchema):
    start_predefined = fields.String(
        example="hold",
    )
    start_integer = fields.Integer(
        example=1,
    )
    end_predefined = fields.String(
        example="resolved",
    )
    end_integer = fields.Integer(
        example=0,
    )


class CheckboxWithManagementTypeStateValue(Checkbox):
    value = fields.Nested(
        ManagementTypeStates,
    )


class ManagementTypeParams(BaseSchema):
    host_description = fields.Nested(
        CheckboxWithStrValue,
        required=True,
    )
    service_description = fields.Nested(
        CheckboxWithStrValue,
        required=True,
    )
    host_short_description = fields.Nested(
        CheckboxWithStrValue,
        required=True,
    )
    service_short_description = fields.Nested(
        CheckboxWithStrValue,
        required=True,
    )
    caller = fields.String(
        required=True,
    )
    urgency = fields.Nested(
        CheckboxWithStrValue,
        required=True,
    )
    impact = fields.Nested(
        CheckboxWithStrValue,
        required=True,
    )
    state_recovery = fields.Nested(
        CheckboxWithManagementTypeStateValue,
        required=True,
    )
    state_acknowledgement = fields.Nested(
        CheckboxWithManagementTypeStateValue,
        required=True,
    )
    state_downtime = fields.Nested(
        CheckboxWithManagementTypeStateValue,
        required=True,
    )
    priority = fields.Nested(
        CheckboxWithStrValue,
        required=True,
    )


class ServiceNowMngmtType(BaseSchema):
    option = fields.String(
        enum=["case", "incident"],
        required=True,
        description="The management type",
        example="case",
    )
    params = fields.Nested(
        ManagementTypeParams,
    )


class IncidentAndCaseParams(BaseSchema):
    host_description = fields.Nested(
        CheckboxOneOfSchema(CheckboxWithStrValue),
    )
    service_description = fields.Nested(
        CheckboxOneOfSchema(CheckboxWithStrValue),
    )
    host_short_description = fields.Nested(
        CheckboxOneOfSchema(CheckboxWithStrValue),
    )
    service_short_description = fields.Nested(
        CheckboxOneOfSchema(CheckboxWithStrValue),
    )


class CaseParams(IncidentAndCaseParams):
    priority = fields.Nested(
        CheckboxOneOfSchema(CheckboxWithMgmtTypePriorityValue),
    )
    state_recovery = fields.Nested(
        CheckboxOneOfSchema(CheckboxWithManagementTypeStateCaseValues),
    )


class IncidentParams(IncidentAndCaseParams):
    caller = fields.String(
        required=True,
        example="Alice",
        description="Caller is the user on behalf of whom the incident is being reported within ServiceNow.",
    )
    urgency = fields.Nested(
        CheckboxOneOfSchema(CheckboxWithMgmtTypeUrgencyValue),
    )
    impact = fields.Nested(
        CheckboxOneOfSchema(CheckboxWithStrValue),
    )
    state_acknowledgement = fields.Nested(
        CheckboxOneOfSchema(CheckboxWithManagementTypeStateIncedentValues),
    )
    state_downtime = fields.Nested(
        CheckboxOneOfSchema(CheckboxWithManagementTypeStateIncedentValues),
    )
    state_recovery = fields.Nested(
        CheckboxOneOfSchema(CheckboxWithManagementTypeStateIncedentValues),
    )


class MgmntTypeCommon(BaseSchema):
    option = fields.String(
        enum=["case", "incident"],
        required=True,
        example="case",
    )


class MgmntTypeCaseParams(MgmntTypeCommon):
    params = fields.Nested(CaseParams)


class MgmntTypeIncidentParams(MgmntTypeCommon):
    params = fields.Nested(IncidentParams)


class MgmntTypeSelector(OneOfSchema):
    type_field = "option"
    type_field_remove = False
    type_schemas = {
        "case": MgmntTypeCaseParams,
        "incident": MgmntTypeIncidentParams,
    }


class PluginName(BaseSchema):
    plugin_name = fields.String(
        enum=list(get_args(BuiltInPluginNames)),
        required=True,
        description="The plugin name. Built-in plugins only.",
        example="mail",
    )


# ----------------------------------------------------------------------------


class MailBaseCreate(PluginName):
    from_details = fields.Nested(
        CheckboxOneOfSchema(FromEmailAndNameCheckbox),
        required=True,
    )
    reply_to = fields.Nested(
        CheckboxOneOfSchema(ToEmailAndNameCheckbox),
        required=True,
    )
    subject_for_host_notifications = fields.Nested(
        CheckboxOneOfSchema(SubjectForHostNotificationsCheckbox),
        required=True,
    )
    subject_for_service_notifications = fields.Nested(
        CheckboxOneOfSchema(SubjectForServiceNotificationsCheckbox),
        required=True,
    )
    send_separate_notification_to_every_recipient = fields.Nested(
        Checkbox,
        required=True,
    )
    sort_order_for_bulk_notificaions = fields.Nested(
        CheckboxOneOfSchema(CheckboxSortOrderValue),
        required=True,
    )


class AsciiMailPluginCreate(MailBaseCreate):
    body_head_for_both_host_and_service_notifications = fields.Nested(
        CheckboxOneOfSchema(CheckboxWithStr),
        required=True,
    )
    body_tail_for_host_notifications = fields.Nested(
        CheckboxOneOfSchema(CheckboxWithStr),
        required=True,
    )
    body_tail_for_service_notifications = fields.Nested(
        CheckboxOneOfSchema(CheckboxWithStr),
        required=True,
    )


class HTMLMailPluginCreate(MailBaseCreate):
    info_to_be_displayed_in_the_email_body = fields.Nested(
        CheckboxOneOfSchema(CheckboxWithListOfEmailInfoStrs),
        required=True,
    )
    insert_html_section_between_body_and_table = fields.Nested(
        CheckboxOneOfSchema(HtmlSectionBetweenBodyAndTableCheckbox),
        required=True,
    )

    url_prefix_for_links_to_checkmk = URL_PREFIX_FOR_LINKS_TO_CHECKMK_CREATE

    display_graphs_among_each_other = fields.Nested(
        Checkbox,
        required=True,
    )
    enable_sync_smtp = fields.Nested(
        CheckboxOneOfSchema(EnableSynchronousDeliveryViaSMTPValue),
        required=True,
    )
    graphs_per_notification = fields.Nested(
        CheckboxOneOfSchema(GraphsPerNotification),
        required=True,
    )
    bulk_notifications_with_graphs = fields.Nested(
        CheckboxOneOfSchema(BulkNotificationsWithGraphs),
        required=True,
    )


class MailCommonParams(PluginName):
    from_details = fields.Nested(
        FromEmailAndNameCheckbox,
        required=True,
    )
    reply_to = fields.Nested(
        ToEmailAndNameCheckbox,
        required=True,
    )
    subject_for_host_notifications = fields.Nested(
        SubjectForHostNotificationsCheckbox,
        required=True,
    )
    subject_for_service_notifications = fields.Nested(
        SubjectForServiceNotificationsCheckbox,
        required=True,
    )
    sort_order_for_bulk_notificaions = fields.Nested(
        CheckboxSortOrderValue,
        required=True,
    )
    send_separate_notification_to_every_recipient = fields.Nested(
        Checkbox,
        required=True,
    )


class HTMLEmailParamsResponse(MailCommonParams):
    info_to_be_displayed_in_the_email_body = fields.Nested(
        CheckboxWithListOfEmailInfoStrs,
        required=True,
    )
    insert_html_section_between_body_and_table = fields.Nested(
        HtmlSectionBetweenBodyAndTableCheckbox,
        required=True,
    )
    url_prefix_for_links_to_checkmk = URL_PREFIX_FOR_LINKS_TO_CHECKMK_RESPONSE

    enable_sync_smtp = fields.Nested(
        EnableSynchronousDeliveryViaSMTPValue,
        required=True,
    )
    display_graphs_among_each_other = fields.Nested(
        Checkbox,
        required=True,
    )
    graphs_per_notification = fields.Nested(
        GraphsPerNotification,
        required=True,
    )
    bulk_notifications_with_graphs = fields.Nested(
        BulkNotificationsWithGraphs,
        required=True,
    )


class AsciiEmailParamsResponse(MailCommonParams):
    body_head_for_both_host_and_service_notifications = fields.Nested(
        CheckboxWithStr,
        required=True,
    )
    body_tail_for_host_notifications = fields.Nested(
        CheckboxWithStr,
        required=True,
    )
    body_tail_for_service_notifications = fields.Nested(
        CheckboxWithStr,
        required=True,
    )


# ----------------------------------------------------------------------------


class CiscoWebexPluginBase(PluginName):
    disable_ssl_cert_verification = DISABLE_SSL_CERT_VERIFICATION


class CiscoWebexPluginCreate(CiscoWebexPluginBase):
    webhook_url = fields.Nested(CiscoUrlOrStoreSelector)
    url_prefix_for_links_to_checkmk = URL_PREFIX_FOR_LINKS_TO_CHECKMK_CREATE
    http_proxy = HTTP_PROXY_CREATE


class CiscoWebexPluginResponse(CiscoWebexPluginBase):
    webhook_url = fields.Nested(WebhookURLResponse, required=True)
    url_prefix_for_links_to_checkmk = URL_PREFIX_FOR_LINKS_TO_CHECKMK_RESPONSE
    http_proxy = HTTP_PROXY_RESPONSE


# ----------------------------------------------------------------------------


class MkEventDPluginCreate(PluginName):
    syslog_facility_to_use = fields.Nested(
        CheckboxOneOfSchema(CheckboxSysLogFacilityToUseValue),
        required=True,
    )
    ip_address_of_remote_event_console = fields.Nested(
        CheckboxOneOfSchema(CheckBoxIPAddressValue),
        required=True,
    )


class MkEventParamsResponse(PluginName):
    syslog_facility_to_use = fields.Nested(
        CheckboxSysLogFacilityToUseValue,
        required=True,
    )
    ip_address_of_remote_event_console = fields.Nested(
        CheckBoxIPAddressValue,
        required=True,
    )


# ----------------------------------------------------------------------------
class ILertPluginBase(PluginName):
    notification_priority = fields.String(
        enum=list(get_args(IlertPriorityType)),
        required=True,
        description="HIGH - with escalation, LOW - without escalation",
        example="HIGH",
    )
    custom_summary_for_host_alerts = fields.String(
        required=True,
        example="$NOTIFICATIONTYPE$ Host Alert: $HOSTNAME$ is $HOSTSTATE$ - $HOSTOUTPUT$",
        description="A custom summary for host alerts",
    )
    custom_summary_for_service_alerts = fields.String(
        required=True,
        example="$NOTIFICATIONTYPE$ Service Alert: $HOSTALIAS$/$SERVICEDESC$ is $SERVICESTATE$ - $SERVICEOUTPUT$",
        description="A custom summary for service alerts",
    )
    disable_ssl_cert_verification = DISABLE_SSL_CERT_VERIFICATION


class IlertPluginCreate(ILertPluginBase):
    api_key = fields.Nested(IlertKeyOrStoreSelector, required=True)
    url_prefix_for_links_to_checkmk = URL_PREFIX_FOR_LINKS_TO_CHECKMK_CREATE
    http_proxy = HTTP_PROXY_CREATE


class IlertPluginResponse(ILertPluginBase):
    api_key = fields.Nested(IlertKeyResponse, required=True)
    url_prefix_for_links_to_checkmk = URL_PREFIX_FOR_LINKS_TO_CHECKMK_RESPONSE
    http_proxy = HTTP_PROXY_RESPONSE


# ----------------------------------------------------------------------------


class JiraPluginBase(PluginName):
    jira_url = fields.String(
        required=False,
        example="http://jira_url_example.com",
        description="Configure the JIRA URL here",
    )
    disable_ssl_cert_verification = DISABLE_SSL_CERT_VERIFICATION
    username = USERNAME
    password = fields.String(
        required=True,
        example="example_pass_123&*",
        description="The password entered here is stored in plain text within the monitoring site. This usually needed because the monitoring process needs to have access to the unencrypted password because it needs to submit it to authenticate with remote systems",
    )
    project_id = fields.String(
        required=True,
        example="",
        description="The numerical JIRA project ID. If not set, it will be retrieved from a custom user attribute named jiraproject. If that is not set, the notification will fail",
    )
    issue_type_id = fields.String(
        required=True,
        example="",
        description="The numerical JIRA issue type ID. If not set, it will be retrieved from a custom user attribute named jiraissuetype. If that is not set, the notification will fail",
    )
    host_custom_id = fields.String(
        required=True,
        example="",
        description="The numerical JIRA custom field ID for host problems",
    )
    service_custom_id = fields.String(
        required=True,
        example="",
        description="The numerical JIRA custom field ID for service problems",
    )
    monitoring_url = fields.String(
        required=True,
        example="",
        description="Configure the base URL for the Monitoring Web-GUI here. Include the site name. Used for link to check_mk out of jira",
    )


class JiraPluginCreate(JiraPluginBase):
    site_custom_id = fields.Nested(
        CheckboxOneOfSchema(CheckboxWithStr),
        required=True,
        description="The numerical ID of the JIRA custom field for sites. Please use this option if you have multiple sites in a distributed setup which send their notifications to the same JIRA instance",
    )
    priority_id = fields.Nested(
        CheckboxOneOfSchema(CheckboxWithStr),
        required=True,
        description="The numerical JIRA priority ID. If not set, it will be retrieved from a custom user attribute named jirapriority. If that is not set, the standard priority will be used",
    )
    host_summary = fields.Nested(
        CheckboxOneOfSchema(CheckboxWithStr),
        required=True,
        description="Here you are allowed to use all macros that are defined in the notification context",
    )
    service_summary = fields.Nested(
        CheckboxOneOfSchema(CheckboxWithStr),
        required=True,
        description="Here you are allowed to use all macros that are defined in the notification context",
    )
    label = fields.Nested(
        CheckboxOneOfSchema(CheckboxWithStr),
        required=True,
        description="Here you can set a custom label for new issues. If not set, 'monitoring' will be used",
    )
    resolution_id = fields.Nested(
        CheckboxOneOfSchema(CheckboxWithStr),
        required=True,
        description="The numerical JIRA resolution transition ID. 11 - 'To Do', 21 - 'In Progress', 31 - 'Done'",
    )
    optional_timeout = fields.Nested(
        CheckboxOneOfSchema(CheckboxWithStr),
        required=True,
        description="Here you can configure timeout settings.",
    )


class JiraPluginResponse(JiraPluginBase):
    site_custom_id = fields.Nested(
        CheckboxWithStr,
        required=True,
    )
    priority_id = fields.Nested(
        CheckboxWithStr,
        required=True,
    )
    host_summary = fields.Nested(
        CheckboxWithStr,
        required=True,
    )
    service_summary = fields.Nested(
        CheckboxWithStr,
        required=True,
    )
    label = fields.Nested(
        CheckboxWithStr,
        required=True,
    )
    resolution_id = fields.Nested(
        CheckboxWithStr,
        required=True,
    )
    optional_timeout = fields.Nested(
        CheckboxWithStr,
        required=True,
    )


# ----------------------------------------------------------------------------
class OpsGeniePluginCreate(PluginName):
    api_key = fields.Nested(OpsGenisStoreOrExplicitKeySelector, required=True)
    domain = fields.Nested(
        CheckboxOneOfSchema(CheckboxWithStr),
        required=True,
        description="If you have an european account, please set the domain of your opsgenie. Specify an absolute URL like https://api.eu.opsgenie.com",
    )
    http_proxy = HTTP_PROXY_CREATE
    owner = fields.Nested(
        CheckboxOneOfSchema(CheckboxWithStr),
        required=True,
        description="Sets the user of the alert. Display name of the request owner",
    )
    source = fields.Nested(
        CheckboxOneOfSchema(CheckboxWithStr),
        required=True,
        description="Source field of the alert. Default value is IP address of the incoming request",
    )
    priority = fields.Nested(
        CheckboxOneOfSchema(CheckboxOpsGeniePriorityValue),
        required=True,
    )
    note_while_creating = fields.Nested(
        CheckboxOneOfSchema(CheckboxWithStr),
        required=True,
        description="Additional note that will be added while creating the alert",
    )
    note_while_closing = fields.Nested(
        CheckboxOneOfSchema(CheckboxWithStr),
        required=True,
        description="Additional note that will be added while closing the alert",
    )
    desc_for_host_alerts = fields.Nested(
        CheckboxOneOfSchema(CheckboxWithStr),
        required=True,
        description="Description field of host alert that is generally used to provide a detailed information about the alert",
    )
    desc_for_service_alerts = fields.Nested(
        CheckboxOneOfSchema(CheckboxWithStr),
        required=True,
        description="Description field of service alert that is generally used to provide a detailed information about the alert",
    )
    message_for_host_alerts = fields.Nested(
        CheckboxOneOfSchema(CheckboxWithStr),
        required=True,
        description="",
    )
    message_for_service_alerts = fields.Nested(
        CheckboxOneOfSchema(CheckboxWithStr),
        required=True,
        description="",
    )
    responsible_teams = fields.Nested(
        CheckboxOneOfSchema(CheckboxWithListOfStr),
        required=True,
        description="Team names which will be responsible for the alert. If the API Key belongs to a team integration, this field will be overwritten with the owner team. You may paste a text from your clipboard which contains several parts separated by ';' characters into the last input field. The text will then be split by these separators and the single parts are added into dedicated input fields",
    )
    actions = fields.Nested(
        CheckboxOneOfSchema(CheckboxWithListOfStr),
        required=True,
        description="Custom actions that will be available for the alert. You may paste a text from your clipboard which contains several parts separated by ';' characters into the last input field. The text will then be split by these separators and the single parts are added into dedicated input fields",
    )
    tags = fields.Nested(
        CheckboxOneOfSchema(CheckboxWithListOfStr),
        required=True,
        description="Tags of the alert. You may paste a text from your clipboard which contains several parts separated by ';' characters into the last input field. The text will then be split by these separators and the single parts are added into dedicated input fields",
    )
    entity = fields.Nested(
        CheckboxOneOfSchema(CheckboxWithStr),
        required=True,
        description="Is used to specify which domain the alert is related to",
    )


class OpenGeniePluginResponse(PluginName):
    api_key = fields.Nested(OpsGeniePasswordResponse, required=True)
    domain = fields.Nested(
        CheckboxWithStr,
        required=True,
    )
    http_proxy = fields.Nested(
        HttpProxyValue,
        required=True,
    )
    owner = fields.Nested(
        CheckboxWithStr,
        required=True,
    )
    source = fields.Nested(
        CheckboxWithStr,
        required=True,
    )
    priority = fields.Nested(
        CheckboxOpsGeniePriorityValue,
        required=True,
    )
    note_while_creating = fields.Nested(
        CheckboxWithStr,
        required=True,
    )
    note_while_closing = fields.Nested(
        CheckboxWithStr,
        required=True,
    )
    desc_for_host_alerts = fields.Nested(
        CheckboxWithStr,
        required=True,
    )
    desc_for_service_alerts = fields.Nested(
        CheckboxWithStr,
        required=True,
    )
    message_for_host_alerts = fields.Nested(
        CheckboxWithStr,
        required=True,
    )
    message_for_service_alerts = fields.Nested(
        CheckboxWithStr,
        required=True,
    )
    responsible_teams = fields.Nested(
        CheckboxWithListOfStr,
        required=True,
    )
    actions = fields.Nested(
        CheckboxWithListOfStr,
        required=True,
    )
    tags = fields.Nested(
        CheckboxWithListOfStr,
        required=True,
    )
    entity = fields.Nested(
        CheckboxWithStr,
        required=True,
    )


# ----------------------------------------------------------------------------
class PagerDutyPluginCreate(PluginName):
    integration_key = fields.Nested(PagerDutyStoreOrIntegrationKeySelector, required=True)
    disable_ssl_cert_verification = DISABLE_SSL_CERT_VERIFICATION
    url_prefix_for_links_to_checkmk = URL_PREFIX_FOR_LINKS_TO_CHECKMK_CREATE
    http_proxy = HTTP_PROXY_CREATE


class PagerDutyPluginResponse(PluginName):
    integration_key = fields.Nested(PagerDutyIntegrationKeyResponse, required=True)
    disable_ssl_cert_verification = DISABLE_SSL_CERT_VERIFICATION
    url_prefix_for_links_to_checkmk = URL_PREFIX_FOR_LINKS_TO_CHECKMK_RESPONSE
    http_proxy = HTTP_PROXY_RESPONSE


# ----------------------------------------------------------------------------


class PushOverPluginBase(PluginName):
    api_key = fields.String(
        required=True,
        example="azGDORePK8gMaC0QOYAMyEEuzJnyUi",
        description="You need to provide a valid API key to be able to send push notifications using Pushover. Register and login to Pushover, thn create your Check_MK installation as application and obtain your API key",
        pattern="[a-zA-Z0-9]{30}",
    )
    user_group_key = fields.String(
        required=True,
        example="azGDORePK8gMaC0QOYAMyEEuzJnyUi",
        description="Configure the user or group to receive the notifications by providing the user or group key here. The key can be obtained from the Pushover website.",
        pattern="[a-zA-Z0-9]{30}",
    )


class PushOverPluginCreate(PushOverPluginBase):
    url_prefix_for_links_to_checkmk = fields.Nested(
        CheckboxOneOfSchema(CheckboxWithStr),
        required=True,
        description="If you specify an URL prefix here, then several parts of the email body are armed with hyperlinks to your Check_MK GUI, so that the recipient of the email can directly visit the host or service in question in Check_MK. Specify an absolute URL including the .../check_mk/",
    )
    priority = fields.Nested(
        CheckboxOneOfSchema(PushOverPriority),
        required=True,
    )
    sound = fields.Nested(
        CheckboxOneOfSchema(Sounds),
        required=True,
    )
    http_proxy = HTTP_PROXY_CREATE


class PushOverPluginResponse(PushOverPluginBase):
    url_prefix_for_links_to_checkmk = fields.Nested(
        CheckboxWithStrValue,
        required=True,
    )
    priority = fields.Nested(
        PushOverPriority,
        required=True,
    )
    sound = fields.Nested(
        Sounds,
        required=True,
    )
    http_proxy = HTTP_PROXY_RESPONSE


# ----------------------------------------------------------------------------


class ServiceNowBase(PluginName):
    servicenow_url = fields.String(
        required=True,
        example="https://myservicenow.com",
        description="Configure your ServiceNow URL here",
    )
    username = USERNAME


class ServiceNowPluginCreate(ServiceNowBase):
    user_password = fields.Nested(ServiceNowPasswordSelector, required=True)
    http_proxy = HTTP_PROXY_CREATE
    use_site_id_prefix = fields.Nested(
        CheckboxOneOfSchema(CheckBoxUseSiteIDPrefix),
        required=True,
    )
    optional_timeout = fields.Nested(
        CheckboxOneOfSchema(CheckboxWithStr),
        required=True,
    )
    management_type = fields.Nested(
        MgmntTypeSelector,
    )


class ServiceNowPluginResponse(ServiceNowBase):
    user_password = fields.Nested(
        ServiceNowPasswordResponse,
        required=True,
        description="The password for ServiceNow Plugin.",
        example={"option": "password", "password": "my_unique_password"},
    )
    http_proxy = HTTP_PROXY_RESPONSE
    use_site_id_prefix = fields.Nested(
        CheckBoxUseSiteIDPrefix,
        required=True,
    )
    optional_timeout = fields.Nested(
        CheckboxWithStr,
        required=True,
    )
    management_type = fields.Nested(
        ServiceNowMngmtType,
        required=True,
    )


# ----------------------------------------------------------------------------


class Signl4PluginCreate(PluginName):
    team_secret = fields.Nested(SignL4ExplicitOrStoreSelector, required=True)
    url_prefix_for_links_to_checkmk = URL_PREFIX_FOR_LINKS_TO_CHECKMK_CREATE
    disable_ssl_cert_verification = DISABLE_SSL_CERT_VERIFICATION
    http_proxy = HTTP_PROXY_CREATE


class Signl4PluginResponse(PluginName):
    team_secret = fields.Nested(
        SignL4TeamSecretResponse,
        required=True,
        description="The password for SignL4 Plugin.",
        example={"option": "password", "password": "my_unique_password"},
    )
    url_prefix_for_links_to_checkmk = URL_PREFIX_FOR_LINKS_TO_CHECKMK_RESPONSE
    disable_ssl_cert_verification = DISABLE_SSL_CERT_VERIFICATION
    http_proxy = HTTP_PROXY_RESPONSE


# ----------------------------------------------------------------------------


class SlackPluginCreate(PluginName):
    webhook_url = fields.Nested(SlackStoreOrExplicitURLSelector, required=True)
    url_prefix_for_links_to_checkmk = URL_PREFIX_FOR_LINKS_TO_CHECKMK_CREATE
    disable_ssl_cert_verification = DISABLE_SSL_CERT_VERIFICATION
    http_proxy = HTTP_PROXY_CREATE


class SlackPluginResponse(PluginName):
    webhook_url = fields.Nested(SlackWebhookURLResponse, required=True)
    url_prefix_for_links_to_checkmk = URL_PREFIX_FOR_LINKS_TO_CHECKMK_RESPONSE
    disable_ssl_cert_verification = DISABLE_SSL_CERT_VERIFICATION
    http_proxy = HTTP_PROXY_RESPONSE


# ----------------------------------------------------------------------------


class SMSAPIPluginBase(PluginName):
    modem_type = fields.String(
        enum=["trb140"],
        required=True,
        example="trb140",
        description="Choose what modem is used. Currently supported is only Teltonika-TRB140.",
    )
    modem_url = fields.URL(
        required=True,
        example="https://mymodem.mydomain.example",
        description="Configure your modem URL here",
    )
    disable_ssl_cert_verification = DISABLE_SSL_CERT_VERIFICATION
    username = USERNAME
    timeout = fields.String(
        required=True,
        example="10",
        description="Here you can configure timeout settings",
    )


class SMSAPIPluginCreate(SMSAPIPluginBase):
    user_password = fields.Nested(SMSAPIPasswordSelector, required=True)
    http_proxy = HTTP_PROXY_CREATE


class SMSAPIPluginResponse(SMSAPIPluginBase):
    user_password = fields.Nested(SMSAPIPAsswordResponse, required=True)
    http_proxy = HTTP_PROXY_RESPONSE


# ----------------------------------------------------------------------------


class SMSPluginBase(PluginName):
    params = fields.List(
        fields.String,
        required=True,
        uniqueItems=True,
        description="The given parameters are available in scripts as NOTIFY_PARAMETER_1, NOTIFY_PARAMETER_2, etc. You may paste a text from your clipboard which contains several parts separated by ';' characters into the last input field. The text will then be split by these separators and the single parts are added into dedicated input fields.",
        example=["NOTIFY_PARAMETER_1", "NOTIFY_PARAMETER_1"],
    )


# ----------------------------------------------------------------------------


class SpectrumPluginBase(PluginName):
    destination_ip = IPField(
        ip_type_allowed="ipv4",
        required=True,
        description="IP Address of the Spectrum server receiving the SNMP trap",
    )
    snmp_community = fields.String(
        required=True,
        example="",
        description="SNMP Community for the SNMP trap. The password entered here is stored in plain text within the monitoring site. This usually needed because the monitoring process needs to have access to the unencrypted password because it needs to submit it to authenticate with remote systems",
    )
    base_oid = fields.String(
        required=True,
        example="1.3.6.1.4.1.1234",
        description="The base OID for the trap content",
    )


# ----------------------------------------------------------------------------


class VictoropsPluginCreate(PluginName):
    splunk_on_call_rest_endpoint = fields.Nested(SplunkRESTEndpointSelector, required=True)
    url_prefix_for_links_to_checkmk = URL_PREFIX_FOR_LINKS_TO_CHECKMK_CREATE
    disable_ssl_cert_verification = DISABLE_SSL_CERT_VERIFICATION
    http_proxy = HTTP_PROXY_CREATE


class VictoropsPluginResponse(PluginName):
    splunk_on_call_rest_endpoint = fields.Nested(SplunkRESTEndpointResponse, required=True)
    url_prefix_for_links_to_checkmk = URL_PREFIX_FOR_LINKS_TO_CHECKMK_RESPONSE
    disable_ssl_cert_verification = DISABLE_SSL_CERT_VERIFICATION
    http_proxy = HTTP_PROXY_RESPONSE


# ----------------------------------------------------------------------------


class MSTeamsPluginCreate(PluginName):
    affected_host_groups = fields.Nested(
        Checkbox,
        required=True,
        description="Enable/disable if we show affected host groups in the created message",
    )
    host_details = fields.Nested(
        CheckboxOneOfSchema(CheckboxWithStrValue),
        required=True,
        description="Enable/disable the details for host notifications",
    )
    service_details = fields.Nested(
        CheckboxOneOfSchema(CheckboxWithStrValue),
        required=True,
        description="Enable/disable the details for service notifications",
    )
    host_summary = fields.Nested(
        CheckboxOneOfSchema(CheckboxWithStrValue),
        required=True,
        description="Enable/disable the summary for host notifications",
    )
    service_summary = fields.Nested(
        CheckboxOneOfSchema(CheckboxWithStrValue),
        required=True,
        description="Enable/disable the summary for service notifications",
    )
    host_title = fields.Nested(
        CheckboxOneOfSchema(CheckboxWithStrValue),
        required=True,
        description="Enable/disable the title for host notifications",
    )
    service_title = fields.Nested(
        CheckboxOneOfSchema(CheckboxWithStrValue),
        required=True,
        description="Enable/disable the title for service notifications",
    )
    http_proxy = HTTP_PROXY_CREATE
    url_prefix_for_links_to_checkmk = URL_PREFIX_FOR_LINKS_TO_CHECKMK_CREATE
    webhook_url = fields.Nested(MSTeamsUrlOrStoreSelector, required=True)


class MSTeamsPluginResponse(PluginName):
    affected_host_groups = fields.Nested(
        Checkbox,
        required=True,
    )
    host_details = fields.Nested(
        CheckboxWithStrValue,
        required=True,
    )
    service_details = fields.Nested(
        CheckboxWithStrValue,
        required=True,
    )
    host_summary = fields.Nested(
        CheckboxWithStrValue,
        required=True,
    )
    service_summary = fields.Nested(
        CheckboxWithStrValue,
        required=True,
    )
    host_title = fields.Nested(
        CheckboxWithStrValue,
        required=True,
    )
    service_title = fields.Nested(
        CheckboxWithStrValue,
        required=True,
    )
    http_proxy = HTTP_PROXY_RESPONSE
    url_prefix_for_links_to_checkmk = URL_PREFIX_FOR_LINKS_TO_CHECKMK_RESPONSE
    webhook_url = fields.Nested(WebhookURLResponse, required=True)


# ----------------------------------------------------------------------------


class PluginSelector(OneOfSchema):
    type_field = "plugin_name"
    type_field_remove = False
    type_schemas = {
        "asciimail": AsciiMailPluginCreate,
        "mail": HTMLMailPluginCreate,
        "cisco_webex_teams": CiscoWebexPluginCreate,
        "mkeventd": MkEventDPluginCreate,
        "ilert": IlertPluginCreate,
        "jira_issues": JiraPluginCreate,
        "opsgenie_issues": OpsGeniePluginCreate,
        "pagerduty": PagerDutyPluginCreate,
        "pushover": PushOverPluginCreate,
        "servicenow": ServiceNowPluginCreate,
        "signl4": Signl4PluginCreate,
        "slack": SlackPluginCreate,
        "sms_api": SMSAPIPluginCreate,
        "sms": SMSPluginBase,
        "spectrum": SpectrumPluginBase,
        "victorops": VictoropsPluginCreate,
        "msteams": MSTeamsPluginCreate,
    }


class PluginOption(BaseSchema):
    option = fields.String(
        enum=[
            "cancel_previous_notifications",
            "create_notification_with_the_following_parameters",
        ],
        required=False,
        description="Create notifications with parameters or cancel previous notifications",
        example="cancel_previous_notifications",
    )


class PluginBase(PluginOption):
    plugin_params = fields.Nested(
        PluginName,
        required=True,
    )


class PluginWithParams(PluginOption):
    plugin_params = fields.Nested(
        PluginSelector,
        required=True,
    )


TIME_HORIZON = fields.Integer(
    required=True,
    description="Notifications are kept back for bulking at most for this time (seconds)",
    example=60,
)

NOTIFICATION_BULKS_BASED_ON = fields.List(
    fields.String(
        enum=list(get_args(GroupbyType)),
    ),
    required=True,
    uniqueItems=True,
)

NOTIFICATION_BULKS_BASED_ON_CUSTOM_MACROS = fields.List(
    fields.String(
        required=True,
        description="If you enter the names of host/service-custom macros here then for each different combination of values of those macros a separate bulk will be created. Service macros match first, if no service macro is found, the host macros are searched. This can be used in combination with the grouping by folder, host etc. Omit any leading underscore. Note: If you are using Nagios as a core you need to make sure that the values of the required macros are present in the notification context. This is done in check_mk_templates.cfg. If you macro is _FOO then you need to add the variables NOTIFY_HOST_FOO and NOTIFY_SERVICE_FOO. You may paste a text from your clipboard which contains several parts separated by ';' characters into the last input field. The text will then be split by these separators and the single parts are added into dedicated input fields",
        example="",
    )
)

MAX_BULK_SIZE = fields.Integer(
    required=True,
    description="At most that many Notifications are kept back for bulking. A value of 1 essentially turns off notification bulking.",
    example="1000",
)

TIME_PERIOD = fields.String(
    required=True,
    description="",
    example="24X7",
)

WHEN_TO_BULK = fields.String(
    enum=["always", "timeperiod"],
    required=True,
    description="Bulking can always happen or during a set time period",
    example="always",
)


class NotificationBulkingCommon(BaseSchema):
    subject_for_bulk_notifications = fields.Nested(
        CheckboxOneOfSchema(CheckboxWithStr),
        required=True,
    )
    max_bulk_size = MAX_BULK_SIZE
    notification_bulks_based_on = NOTIFICATION_BULKS_BASED_ON
    notification_bulks_based_on_custom_macros = NOTIFICATION_BULKS_BASED_ON_CUSTOM_MACROS


class NotificationBulkingAlways(NotificationBulkingCommon):
    time_horizon = TIME_HORIZON


class OutsideTimeperiodValue(Checkbox):
    value = fields.Nested(
        NotificationBulkingAlways,
    )


class NotificationBulkingTimePeriod(NotificationBulkingCommon):
    time_period = TIME_PERIOD
    bulk_outside_timeperiod = fields.Nested(
        CheckboxOneOfSchema(OutsideTimeperiodValue),
        required=True,
    )


class WhenToBulk(BaseSchema):
    when_to_bulk = WHEN_TO_BULK


class AlwaysBulk(WhenToBulk):
    params = fields.Nested(
        NotificationBulkingAlways,
        required=True,
    )


class TimePeriod(WhenToBulk):
    params = fields.Nested(
        NotificationBulkingTimePeriod,
        required=True,
    )


class NotificationBulkingWhenToBulkSelector(OneOfSchema):
    type_field = "when_to_bulk"
    type_field_remove = False
    type_schemas = {
        "always": AlwaysBulk,
        "timeperiod": TimePeriod,
    }


class NotificationBulkingValue(Checkbox):
    value = fields.Nested(
        NotificationBulkingWhenToBulkSelector,
    )


class PluginOptionsSelector(OneOfSchema):
    type_field = "option"
    type_field_remove = False
    type_schemas = {
        "cancel_previous_notifications": PluginBase,
        "create_notification_with_the_following_parameters": PluginWithParams,
    }


class RulePropertiesDescription(fields.String):
    def __init__(self, required: bool):
        super().__init__(
            description="A description or title of this rule.",
            example="Notify all contacts of a host/service via HTML email",
            required=required,
        )


class RulePropertiesComment(fields.String):
    def __init__(self, required: bool):
        super().__init__(
            description="An optional comment that may be used to explain the purpose of this object.",
            example="An example comment",
            required=required,
        )


class RulePropertiesDocURL(fields.String):
    def __init__(self, required: bool):
        super().__init__(
            description="An optional URL pointing to documentation or any other page. This will be displayed as an icon and open a new page when clicked.",
            example="http://link/to/documentation",
            required=required,
        )


class RulePropertiesDoNotApplyRule(fields.Nested):
    def __init__(self, required: bool):
        super().__init__(
            Checkbox,
            description="Disabled rules are kept in the configuration but are not applied.",
            example={"state": "enabled"},
            required=required,
        )


class RulePropertiesAllowDeactivate(fields.Nested):
    def __init__(self, required: bool):
        super().__init__(
            Checkbox,
            description="If you set this option then users are allowed to deactivate notifications that are created by this rule.",
            example={"state": "enabled"},
            required=required,
        )


class NotificationPlugin(fields.Nested):
    def __init__(self, required: bool):
        super().__init__(
            PluginOptionsSelector,
            required=required,
        )


class NotificationBulk(fields.Nested):
    def __init__(self, required: bool):
        super().__init__(
            CheckboxOneOfSchema(NotificationBulkingValue),
            required=required,
        )


class SimpleCheckbox(fields.Nested):
    def __init__(self, required: bool):
        super().__init__(
            Checkbox,
            required=required,
        )


class AllContacts(SimpleCheckbox):
    ...


class AllUsers(SimpleCheckbox):
    ...


class AllUsersWithEmail(SimpleCheckbox):
    ...


class StringCheckbox(fields.Nested):
    def __init__(self, required: bool):
        super().__init__(
            CheckboxOneOfSchema(CheckboxWithStr),
            required=required,
        )


class ListOfStringCheckbox(fields.Nested):
    def __init__(self, required: bool):
        super().__init__(
            CheckboxOneOfSchema(CheckboxWithListOfStr),
            required=required,
        )


class TheFollowingUsers(ListOfStringCheckbox):
    ...


class ListOfContactGroupsCheckbox(fields.Nested):
    def __init__(self, required: bool):
        super().__init__(
            CheckboxOneOfSchema(CheckboxWithListOfContactGroups),
            required=required,
        )


class ExplicitEmailAddressesCheckbox(fields.Nested):
    def __init__(self, required: bool):
        super().__init__(
            CheckboxOneOfSchema(CheckboxWithListOfEmailAddresses),
            required=required,
        )


class CustomMacrosCheckbox(fields.Nested):
    def __init__(self, required: bool):
        super().__init__(
            CheckboxOneOfSchema(MatchCustomMacros),
            required=required,
        )


class MatchSitesCheckbox(fields.Nested):
    def __init__(self, required: bool):
        super().__init__(
            CheckboxOneOfSchema(CheckboxWithListOfSites),
            required=required,
        )


class MatchFolderCheckbox(fields.Nested):
    def __init__(self, required: bool):
        super().__init__(
            CheckboxOneOfSchema(CheckboxWithFolderStr),
            required=required,
        )


class MatchHostTagsCheckbox(fields.Nested):
    def __init__(self, required: bool):
        super().__init__(
            CheckboxOneOfSchema(CheckboxMatchHostTags),
            required=required,
        )


class MatchHostsCheckbox(fields.Nested):
    def __init__(self, required: bool):
        super().__init__(
            CheckboxOneOfSchema(CheckboxWithListOfHosts),
            required=required,
        )


class MatchServiceGroupsCheckbox(fields.Nested):
    def __init__(self, required: bool):
        super().__init__(
            CheckboxOneOfSchema(CheckboxWithListOfServiceGroups),
            required=required,
        )


class MatchServicesCheckbox(ListOfStringCheckbox):
    ...


class MatchHostGroupsCheckbox(fields.Nested):
    def __init__(self, required: bool):
        super().__init__(
            CheckboxOneOfSchema(CheckboxWithListOfHostGroups),
            required=required,
        )


class MatchLabelsCheckbox(fields.Nested):
    def __init__(self, required: bool):
        super().__init__(
            CheckboxOneOfSchema(CheckboxWithListOfLabels),
            required=required,
        )


class MatchServiceGroupRegexCheckbox(fields.Nested):
    def __init__(self, required: bool):
        super().__init__(
            CheckboxOneOfSchema(CheckboxWithListOfServiceGroupsRegex),
            required=required,
        )


class MatchCheckTypesCheckbox(fields.Nested):
    def __init__(self, required: bool):
        super().__init__(
            CheckboxOneOfSchema(CheckboxWithListOfCheckTypes),
            required=required,
        )


class MatchContactGroupsCheckbox(fields.Nested):
    def __init__(self, required: bool):
        super().__init__(
            CheckboxOneOfSchema(CheckboxWithListOfContactGroups),
            required=required,
        )


class MatchServiceLevelsCheckbox(fields.Nested):
    def __init__(self, required: bool):
        super().__init__(
            CheckboxOneOfSchema(CheckboxWithFromToServiceLevels),
            required=required,
        )


class MatchTimePeriodCheckbox(fields.Nested):
    def __init__(self, required: bool):
        super().__init__(
            CheckboxOneOfSchema(CheckboxWithTimePeriod),
            required=required,
        )


class MatchHostEventTypeCheckbox(fields.Nested):
    def __init__(self, required: bool):
        super().__init__(
            CheckboxOneOfSchema(CheckboxHostEventType),
            required=required,
        )


class MatchServiceEventTypeCheckbox(fields.Nested):
    def __init__(self, required: bool):
        super().__init__(
            CheckboxOneOfSchema(CheckboxServiceEventType),
            required=required,
        )


class RestrictNotificationNumCheckbox(fields.Nested):
    def __init__(self, required: bool):
        super().__init__(
            CheckboxOneOfSchema(CheckboxRestrictNotificationNumbers),
            required=required,
        )


class ThorttlePeriodicNotificationsCheckbox(fields.Nested):
    def __init__(self, required: bool):
        super().__init__(
            CheckboxOneOfSchema(CheckboxThrottlePeriodicNotifcations),
            required=required,
        )


class EventConsoleAlertCheckbox(fields.Nested):
    def __init__(self, required: bool):
        super().__init__(
            CheckboxOneOfSchema(CheckboxEventConsoleAlerts),
            required=required,
        )


class RuleProperties(BaseSchema):
    description = RulePropertiesDescription(required=False)
    comment = RulePropertiesComment(required=False)
    documentation_url = RulePropertiesDocURL(required=False)
    do_not_apply_this_rule = RulePropertiesDoNotApplyRule(required=False)
    allow_users_to_deactivate = RulePropertiesAllowDeactivate(required=False)


class RuleNotificationMethod(BaseSchema):
    notify_plugin = NotificationPlugin(required=False)
    notification_bulking = NotificationBulk(required=False)


class ContactSelection(BaseSchema):
    all_contacts_of_the_notified_object = AllContacts(required=False)
    all_users = AllUsers(required=False)
    all_users_with_an_email_address = AllUsersWithEmail(required=False)
    the_following_users = TheFollowingUsers(required=False)
    members_of_contact_groups = ListOfContactGroupsCheckbox(required=False)
    explicit_email_addresses = ExplicitEmailAddressesCheckbox(required=False)
    restrict_by_contact_groups = ListOfContactGroupsCheckbox(required=False)
    restrict_by_custom_macros = CustomMacrosCheckbox(required=False)


class RuleConditions(BaseSchema):
    match_sites = MatchSitesCheckbox(required=False)
    match_folder = MatchFolderCheckbox(required=False)
    match_host_tags = MatchHostTagsCheckbox(required=False)
    match_host_labels = MatchLabelsCheckbox(required=False)
    match_host_groups = MatchHostGroupsCheckbox(required=False)
    match_hosts = MatchHostsCheckbox(required=False)
    match_exclude_hosts = MatchHostsCheckbox(required=False)
    match_service_labels = MatchLabelsCheckbox(required=False)
    match_service_groups = MatchServiceGroupsCheckbox(required=False)
    match_exclude_service_groups = MatchServiceGroupsCheckbox(required=False)
    match_service_groups_regex = MatchServiceGroupRegexCheckbox(required=False)
    match_exclude_service_groups_regex = MatchServiceGroupRegexCheckbox(required=False)
    match_services = MatchServicesCheckbox(required=False)
    match_exclude_services = MatchServicesCheckbox(required=False)
    match_check_types = MatchCheckTypesCheckbox(required=False)
    match_plugin_output = StringCheckbox(required=False)
    match_contact_groups = MatchContactGroupsCheckbox(required=False)
    match_service_levels = MatchServiceLevelsCheckbox(required=False)
    match_only_during_time_period = MatchTimePeriodCheckbox(required=False)
    match_host_event_type = MatchHostEventTypeCheckbox(required=False)
    match_service_event_type = MatchServiceEventTypeCheckbox(required=False)
    restrict_to_notification_numbers = RestrictNotificationNumCheckbox(required=False)
    throttle_periodic_notifications = ThorttlePeriodicNotificationsCheckbox(required=False)
    match_notification_comment = StringCheckbox(required=False)
    event_console_alerts = EventConsoleAlertCheckbox(required=False)


class RuleNotificationUpdate(BaseSchema):
    rule_properties = fields.Nested(
        RuleProperties,
        required=False,
    )
    notification_method = fields.Nested(
        RuleNotificationMethod,
        required=False,
    )
    contact_selection = fields.Nested(
        ContactSelection,
        required=False,
    )
    conditions = fields.Nested(
        RuleConditions,
        required=False,
    )

    @post_load
    def verify_at_least_one(self, *args, **kwargs):
        at_least_one_of = {
            "rule_properties",
            "notification_method",
            "contact_selection",
            "conditions",
        }
        if not at_least_one_of & set(args[0]):
            raise ValidationError(
                f"At least one of the following parameters should be provided: {at_least_one_of}"
            )
        return args[0]
