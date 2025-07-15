#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from typing import Any, cast, get_args

from marshmallow import post_dump
from marshmallow_oneofschema import OneOfSchema

from cmk import fields
from cmk.gui.fields import (
    AuxTagIDField,
    FolderIDField,
    GlobalHTTPProxyField,
    IPField,
    PasswordStoreIDField,
    ServiceLevelField,
    TagGroupIDField,
)
from cmk.gui.fields.utils import BaseSchema
from cmk.gui.openapi.endpoints.notification_rules.request_example import (
    notification_rule_request_example,
)
from cmk.gui.openapi.restful_objects.response_schemas import DomainObject, DomainObjectCollection
from cmk.gui.rest_api_types.notifications_rule_types import PluginType
from cmk.utils.notify_types import (
    BuiltInPluginNames,
    EmailBodyElementsType,
    get_builtin_plugin_names,
    GroupbyType,
    IlertPriorityType,
    OpsgenieElement,
    OpsGeniePriorityStrType,
    PluginOptions,
    PushOverPriorityStringType,
    RegexModes,
    SoundType,
    SysLogFacilityStrType,
    SysLogPriorityStrType,
)


class CheckboxOutput(BaseSchema):
    state = fields.String(
        enum=["enabled", "disabled"],
        description="To enable or disable this field",
        example="enabled",
    )


class CheckboxWithStrValueOutput(CheckboxOutput):
    value = fields.String()


class CheckboxWithListOfStrOutput(CheckboxOutput):
    value = fields.List(fields.String)


class SysLogToFromPrioritiesOutput(BaseSchema):
    from_priority = fields.String(
        enum=list(get_args(SysLogPriorityStrType)),
        example="warning",
        description="",
    )
    to_priority = fields.String(
        enum=list(get_args(SysLogPriorityStrType)),
        example="warning",
        description="",
    )


class CheckboxWithSysLogPriorityOutput(CheckboxOutput):
    value = fields.Nested(SysLogToFromPrioritiesOutput)


class EventConsoleAlertAttrsResponse(BaseSchema):
    match_rule_ids = fields.Nested(CheckboxWithListOfStrOutput)
    match_syslog_priority = fields.Nested(CheckboxWithSysLogPriorityOutput)
    match_syslog_facility = fields.Nested(CheckboxWithStrValueOutput)
    match_event_comment = fields.Nested(CheckboxWithStrValueOutput)


class EventConsoleAlertsResponse(CheckboxOutput):
    match_type = fields.String(
        enum=["match_only_event_console_alerts", "do_not_match_event_console_alerts"],
        example="match_only_event_console_events",
        description="",
    )
    values = fields.Nested(EventConsoleAlertAttrsResponse)

    @post_dump
    def _post_dump(self, data, many, **kwargs):
        if data.get("values") == {}:
            del data["values"]
        return data


class MatchEventConsoleAlertsResponse(CheckboxOutput):
    value = fields.Nested(EventConsoleAlertsResponse)


class CheckboxLabelOutput(BaseSchema):
    key = fields.String(example="cmk/os_family")
    value = fields.String(example="linux")


class CheckboxWithListOfLabelsOutput(CheckboxOutput):
    value = fields.List(
        fields.Nested(CheckboxLabelOutput),
        description="A list of key, value label pairs",
    )


class ServiceGroupsRegexOutput(BaseSchema):
    match_type = fields.String(
        enum=list(get_args(RegexModes)),
        example="match_alias",
    )
    regex_list = fields.List(
        fields.String,
        uniqueItems=True,
        example=["[A-Z]+123", "[A-Z]+456"],
        description="The text entered in this list is handled as a regular expression pattern",
    )


class CheckboxWithListOfServiceGroupsRegexOutput(CheckboxOutput):
    value = fields.Nested(
        ServiceGroupsRegexOutput,
        description="The service group alias must not match one of the following regular expressions. For host events this condition is simply ignored. The text entered here is handled as a regular expression pattern. The pattern is applied as infix search. Add a leading ^ to make it match from the beginning and/or a tailing $ to match till the end of the text. The match is performed case sensitive. Read more about regular expression matching in Checkmk in our user guide. You may paste a text from your clipboard which contains several parts separated by ';' characters into the last input field. The text will then be split by these separators and the single parts are added into dedicated input field",
    )


class CustomMacroOutput(BaseSchema):
    macro_name = fields.String(
        description="The name of the macro",
        example="macro_1",
    )
    match_regex = fields.String(
        description="The text entered here is handled as a regular expression pattern",
        example="[A-Z]+",
    )


class MatchCustomMacrosOutput(CheckboxOutput):
    value = fields.List(fields.Nested(CustomMacroOutput))


class CheckboxWithFolderStrOutput(CheckboxOutput):
    value = FolderIDField(
        description="This condition makes the rule match only hosts that are managed via WATO and that are contained in this folder - either directly or in one of its subfolders.",
    )


class AuxTagOutput(BaseSchema):
    tag_type = fields.Constant(
        "aux_tag",
        description="Identifies the type of host tag.",
    )
    operator = fields.String(
        enum=["is_not_set", "is_set"],
        description="This describes the matching action",
    )
    tag_id = AuxTagIDField(
        example="checkmk-agent",
        description="Tag groups tag ids are available via the host tag group endpoint.",
    )


class TagGroupBaseOutput(BaseSchema):
    tag_type = fields.String(
        enum=["aux_tag", "tag_group"],
        example="tag_group",
        description="Identifies the type of host tag.",
    )
    tag_group_id = TagGroupIDField(
        example="agent",
        required=False,
        description="If the tag_type is 'tag_group', the id of that group is shown here.",
    )


class TagGroupNoneOfOrOneOfOutput(TagGroupBaseOutput):
    operator = fields.String(enum=["one_of", "none_of"])
    tag_ids = fields.List(
        AuxTagIDField(
            example="checkmk-agent",
            description="Tag groups tag ids are available via the host tag group endpoint.",
        ),
        example=["ip-v4-only", "ip-v6-only"],
    )


class TagGroupIsNotOrIsOutput(TagGroupBaseOutput):
    operator = fields.String(enum=["is", "is_not"])
    tag_id = AuxTagIDField(
        example="checkmk-agent",
        description="Tag groups tag ids are available via the host tag group endpoint.",
    )


class TagGroupSelectorOutput(OneOfSchema):
    type_field = "operator"
    type_schemas = {
        "one_of": TagGroupNoneOfOrOneOfOutput,
        "none_of": TagGroupNoneOfOrOneOfOutput,
        "is_not": TagGroupIsNotOrIsOutput,
        "is": TagGroupIsNotOrIsOutput,
    }
    type_field_remove = False

    def get_obj_type(self, obj):
        operator = obj.get("operator")
        if operator in self.type_schemas:
            return operator

        raise Exception("Unknown object type: %s" % repr(obj))


class TagTypeSelectorOutput(OneOfSchema):
    type_field = "tag_type"
    type_schemas = {
        "aux_tag": AuxTagOutput,
        "tag_group": TagGroupSelectorOutput,
    }
    type_field_remove = False

    def get_obj_type(self, obj):
        tag_type = obj.get("tag_type")
        if tag_type in self.type_schemas:
            return tag_type

        raise Exception("Unknown object type: %s" % repr(obj))


class CheckboxMatchHostTagsOutput(CheckboxOutput):
    value = fields.List(
        fields.Nested(TagTypeSelectorOutput),
        example=[
            {
                "tag_type": "tag_group",
                "tag_group_id": "agent",
                "operator": "is",
                "tag_id": "checkmk-agent",
            },
            {
                "tag_type": "aux_tag",
                "operator": "is_set",
                "tag_id": "snmp",
            },
        ],
        description="A list of tag groups or aux tags with conditions",
    )


class FromToNotificationNumbersOutput(BaseSchema):
    beginning_from = fields.Integer(
        example=1,
        description="Let through notifications counting from this number. The first notification always has the number 1",
    )
    up_to = fields.Integer(
        example=999999,
        description="Let through notifications counting upto this number",
    )


class CheckboxRestrictNotificationNumbersOutput(CheckboxOutput):
    value = fields.Nested(FromToNotificationNumbersOutput)


class ThrottlePeriodicNotificationsOutput(BaseSchema):
    beginning_from = fields.Integer(
        example=10,
        description="Beginning notification number",
    )
    send_every_nth_notification = fields.Integer(
        example=5,
        description="The rate then you will receive the notification 1 through 10 and then 15, 20, 25... and so on",
    )


class CheckboxThrottlePeriodicNotifcationsOuput(CheckboxOutput):
    value = fields.Nested(ThrottlePeriodicNotificationsOutput)


class FromToServiceLevelsOutput(BaseSchema):
    from_level = ServiceLevelField()
    to_level = ServiceLevelField()


class CheckboxWithFromToServiceLevelsOutput(CheckboxOutput):
    value = fields.Nested(
        FromToServiceLevelsOutput,
        description="Host or service must be in the following service level to get notification",
    )


class HostOrServiceEventTypeCommon(BaseSchema):
    start_or_end_of_flapping_state = fields.Boolean(example=True)
    start_or_end_of_scheduled_downtime = fields.Boolean(example=True)
    acknowledgement_of_problem = fields.Boolean(example=False)
    alert_handler_execution_successful = fields.Boolean(example=True)
    alert_handler_execution_failed = fields.Boolean(example=False)


class HostEventTypeOutput(HostOrServiceEventTypeCommon):
    up_down = fields.Boolean(example=True)
    up_unreachable = fields.Boolean(example=False)
    down_up = fields.Boolean(example=True)
    down_unreachable = fields.Boolean(example=False)
    unreachable_down = fields.Boolean(example=False)
    unreachable_up = fields.Boolean(example=False)
    any_up = fields.Boolean(example=False)
    any_down = fields.Boolean(example=True)
    any_unreachable = fields.Boolean(example=True)


class ServiceEventTypeOutput(HostOrServiceEventTypeCommon):
    ok_warn = fields.Boolean(example=True)
    ok_ok = fields.Boolean(example=True)
    ok_crit = fields.Boolean(example=False)
    ok_unknown = fields.Boolean(example=True)
    warn_ok = fields.Boolean(example=False)
    warn_crit = fields.Boolean(example=False)
    warn_unknown = fields.Boolean(example=False)
    crit_ok = fields.Boolean(example=True)
    crit_warn = fields.Boolean(example=True)
    crit_unknown = fields.Boolean(example=True)
    unknown_ok = fields.Boolean(example=True)
    unknown_warn = fields.Boolean(example=True)
    unknown_crit = fields.Boolean(example=True)
    any_ok = fields.Boolean(example=False)
    any_warn = fields.Boolean(example=False)
    any_crit = fields.Boolean(example=True)
    any_unknown = fields.Boolean(example=False)


class CheckboxHostEventTypeOutput(CheckboxOutput):
    value = fields.Nested(
        HostEventTypeOutput,
        description="Select the host event types and transitions this rule should handle. Note: If you activate this option and do not also specify service event types then this rule will never hold for service notifications! Note: You can only match on event types created by the core.",
    )


class CheckboxServiceEventTypeOutput(CheckboxOutput):
    value = fields.Nested(
        ServiceEventTypeOutput,
        description="Select the service event types and transitions this rule should handle. Note: If you activate this option and do not also specify host event types then this rule will never hold for host notifications! Note: You can only match on event types created by the core",
    )


# Plugin Responses --------------------------------------------------
class PluginName(BaseSchema):
    plugin_name = fields.String(
        enum=get_builtin_plugin_names(),
        description="The plug-in name.",
        example="mail",
    )


class EmailAndDisplayName(BaseSchema):
    address = fields.String(
        description="",
        example="mail@example.com",
    )
    display_name = fields.String(
        description="",
        example="",
    )


class FromEmailAndNameCheckbox(CheckboxOutput):
    value = fields.Nested(
        EmailAndDisplayName,
        description="The email address and visible name used in the From header of notifications messages. If no email address is specified the default address is OMD_SITE@FQDN is used. If the environment variable OMD_SITE is not set it defaults to checkmk",
    )


class ToEmailAndNameCheckbox(CheckboxOutput):
    value = fields.Nested(
        EmailAndDisplayName,
        description="The email address and visible name used in the Reply-To header of notifications messages",
    )


class SubjectForHostNotificationsCheckbox(CheckboxOutput):
    value = fields.String(
        description="Here you are allowed to use all macros that are defined in the notification context.",
        example="Check_MK: $HOSTNAME$ - $EVENT_TXT$",
    )


class SubjectForServiceNotificationsCheckbox(CheckboxOutput):
    value = fields.String(
        description="Here you are allowed to use all macros that are defined in the notification context.",
        example="Check_MK: $HOSTNAME$/$SERVICEDESC$ $EVENT_TXT$",
    )


class CheckboxSortOrderValue(CheckboxOutput):
    value = fields.String(
        enum=["oldest_first", "newest_first"],
        description="With this option you can specify, whether the oldest (default) or the newest notification should get shown at the top of the notification mail",
        example="oldest_first",
    )


class MailCommonParams(PluginName):
    from_details = fields.Nested(FromEmailAndNameCheckbox)
    reply_to = fields.Nested(ToEmailAndNameCheckbox)
    subject_for_host_notifications = fields.Nested(SubjectForHostNotificationsCheckbox)
    subject_for_service_notifications = fields.Nested(SubjectForServiceNotificationsCheckbox)
    sort_order_for_bulk_notifications = fields.Nested(CheckboxSortOrderValue)
    send_separate_notification_to_every_recipient = fields.Nested(CheckboxOutput)


# Ascii Email -------------------------------------------------------


class AsciiEmailParamsResponse(MailCommonParams):
    body_head_for_both_host_and_service_notifications = fields.Nested(CheckboxWithStrValueOutput)
    body_tail_for_host_notifications = fields.Nested(CheckboxWithStrValueOutput)
    body_tail_for_service_notifications = fields.Nested(CheckboxWithStrValueOutput)


# HTML Email --------------------------------------------------------


class CheckboxWithListOfEmailInfoStrs(CheckboxOutput):
    value = fields.List(
        fields.String(enum=list(get_args(EmailBodyElementsType))),
        description="Information to be displayed in the email body.",
        example=["abstime", "graph"],
        uniqueItems=True,
    )


class HtmlSectionBetweenBodyAndTableCheckbox(CheckboxOutput):
    value = fields.String(
        description="Insert HTML section between body and table",
        example="<HTMLTAG>CONTENT</HTMLTAG>",
    )


class URLPrefixForLinksToCheckMk(BaseSchema):
    option = fields.String(
        enum=["manual", "automatic"],
        example="automatic",
    )
    schema = fields.String(
        enum=["http", "https"],
        example="http",
    )
    url = fields.String(
        example="http://example_url_prefix",
    )


class URLPrefixForLinksToCheckMkCheckbox(CheckboxOutput):
    value = fields.Nested(
        URLPrefixForLinksToCheckMk,
        description="If you use Automatic HTTP/s, the URL prefix for host and service links within the notification is filled automatically. If you specify an URL prefix here, then several parts of the notification are armed with hyperlinks to your Check_MK GUI. In both cases, the recipient of the notification can directly visit the host or service in question in Check_MK. Specify an absolute URL including the .../check_mk/",
    )


class Authentication(BaseSchema):
    method = fields.String(
        enum=["plaintext"],
        description="The authentication method is fixed at 'plaintext' for now.",
        example="plaintext",
    )
    user = fields.String(
        description="The username for the SMTP connection",
        example="user_1",
    )
    password = fields.String(
        description="The password for the SMTP connection.",
        example="password",
    )


class AuthenticationValue(CheckboxOutput):
    value = fields.Nested(Authentication)


class EnableSynchronousDeliveryViaSMTP(BaseSchema):
    auth = fields.Nested(
        AuthenticationValue,
    )
    encryption = fields.String(
        enum=["ssl_tls", "starttls"],
        description="The encryption type for the SMTP connection.",
        example="ssl_tls",
    )
    port = fields.Integer(
        description="",
        example=25,
    )
    smarthosts = fields.List(
        fields.String(),
        uniqueItems=True,
    )


class EnableSynchronousDeliveryViaSMTPValue(CheckboxOutput):
    value = fields.Nested(EnableSynchronousDeliveryViaSMTP)


class GraphsPerNotification(CheckboxOutput):
    value = fields.Integer(
        description="Sets a limit for the number of graphs that are displayed in a notification",
        example=5,
    )


class BulkNotificationsWithGraphs(CheckboxOutput):
    value = fields.Integer(
        description="Sets a limit for the number of notifications in a bulk for which graphs are displayed. If you do not use bulk notifications this option is ignored. Note that each graph increases the size of the mail and takes time to renderon the monitoring server. Therefore, large bulks may exceed the maximum size for attachements or the plug-in may run into a timeout so that a failed notification is produced",
        example=5,
    )


class HTMLEmailParamsResponse(MailCommonParams):
    info_to_be_displayed_in_the_email_body = fields.Nested(CheckboxWithListOfEmailInfoStrs)
    insert_html_section_between_body_and_table = fields.Nested(
        HtmlSectionBetweenBodyAndTableCheckbox
    )
    url_prefix_for_links_to_checkmk = fields.Nested(URLPrefixForLinksToCheckMkCheckbox)
    enable_sync_smtp = fields.Nested(EnableSynchronousDeliveryViaSMTPValue)
    display_graphs_among_each_other = fields.Nested(CheckboxOutput)
    graphs_per_notification = fields.Nested(GraphsPerNotification)
    bulk_notifications_with_graphs = fields.Nested(BulkNotificationsWithGraphs)


# Cisco -------------------------------------------------------------


class ExplicitOrStoreOptions(BaseSchema):
    option = fields.String(
        enum=["store", "explicit"],
        example="store",
    )


class WebhookURLResponse(ExplicitOrStoreOptions):
    store_id = PasswordStoreIDField()
    url = fields.URL(example="http://example_webhook_url.com")


DISABLE_SSL_CERT_VERIFICATION = fields.Nested(
    CheckboxOutput,
    description="Ignore unverified HTTPS request warnings. Use with caution.",
)


URL_PREFIX_FOR_LINKS_TO_CHECKMK_RESPONSE = fields.Nested(
    URLPrefixForLinksToCheckMkCheckbox,
)


class HttpProxy(BaseSchema):
    option = fields.String(
        enum=["no_proxy", "environment", "url", "global"],
        example="no_proxy",
    )
    url = fields.String(
        example="http://example_proxy",
    )
    global_proxy_id = GlobalHTTPProxyField(
        presence="should_exist",
    )


class HttpProxyValue(CheckboxOutput):
    value = fields.Nested(
        HttpProxy,
        description="Use the proxy settings from the environment variables. The variables NO_PROXY, HTTP_PROXY and HTTPS_PROXY are taken into account during execution. Have a look at the python requests module documentation for further information. Note that these variables must be defined as a site-user in ~/etc/environment and that this might affect other notification methods which also use the requests module",
    )


HTTP_PROXY_RESPONSE = fields.Nested(
    HttpProxyValue,
    example={"state": "enabled", "value": "no_proxy"},
    description="The http proxy settings for the plugin",
)


class CiscoWebexPluginResponse(PluginName):
    disable_ssl_cert_verification = DISABLE_SSL_CERT_VERIFICATION
    webhook_url = fields.Nested(WebhookURLResponse)
    url_prefix_for_links_to_checkmk = URL_PREFIX_FOR_LINKS_TO_CHECKMK_RESPONSE
    http_proxy = HTTP_PROXY_RESPONSE


# Ilert -------------------------------------------------------------


PASSWORD_STORE_ID_SHOULD_EXIST = PasswordStoreIDField()


class IlertKeyResponse(ExplicitOrStoreOptions):
    store_id = PASSWORD_STORE_ID_SHOULD_EXIST
    key = fields.String(example="example_key")


class IlertPluginResponse(PluginName):
    notification_priority = fields.String(
        enum=list(get_args(IlertPriorityType)),
        description="HIGH - with escalation, LOW - without escalation",
        example="HIGH",
    )
    custom_summary_for_host_alerts = fields.String(
        example="$NOTIFICATIONTYPE$ Host Alert: $HOSTNAME$ is $HOSTSTATE$ - $HOSTOUTPUT$",
        description="A custom summary for host alerts",
    )
    custom_summary_for_service_alerts = fields.String(
        example="$NOTIFICATIONTYPE$ Service Alert: $HOSTALIAS$/$SERVICEDESC$ is $SERVICESTATE$ - $SERVICEOUTPUT$",
        description="A custom summary for service alerts",
    )
    disable_ssl_cert_verification = DISABLE_SSL_CERT_VERIFICATION
    api_key = fields.Nested(IlertKeyResponse)
    url_prefix_for_links_to_checkmk = URL_PREFIX_FOR_LINKS_TO_CHECKMK_RESPONSE
    http_proxy = HTTP_PROXY_RESPONSE


# Jira --------------------------------------------------------------


class AuthResponse(BaseSchema):
    option = fields.String(
        enum=["explicit_token", "token_store_id", "explicit_password", "password_store_id"],
        description="The authentication method to use",
        example="basic",
    )
    username = fields.String(
        description="The username for the connection",
        example="user_1",
    )
    password = fields.String(
        description="The password for the connection",
        example="password",
    )
    token = fields.String(
        description="The token for the connection",
        example="token",
    )
    store_id = PASSWORD_STORE_ID_SHOULD_EXIST


class JiraPluginResponse(PluginName):
    jira_url = fields.String(
        example="http://jira_url_example.com",
        description="Configure the Jira URL here",
    )
    disable_ssl_cert_verification = DISABLE_SSL_CERT_VERIFICATION
    auth = fields.Nested(
        AuthResponse,
        description="The authentication credentials for the Jira connection",
    )
    project_id = fields.String(
        example="",
        description="The numerical Jira project ID. If not set, it will be retrieved from a custom user attribute named jiraproject. If that is not set, the notification will fail",
    )
    issue_type_id = fields.String(
        example="",
        description="The numerical Jira issue type ID. If not set, it will be retrieved from a custom user attribute named jiraissuetype. If that is not set, the notification will fail",
    )
    host_custom_id = fields.String(
        example="",
        description="The numerical Jira custom field ID for host problems",
    )
    service_custom_id = fields.String(
        example="",
        description="The numerical Jira custom field ID for service problems",
    )
    monitoring_url = fields.String(
        example="",
        description="Configure the base URL for the monitoring web GUI here. Include the site name. Used for linking to Checkmk out of Jira",
    )
    site_custom_id = fields.Nested(CheckboxWithStrValueOutput)
    priority_id = fields.Nested(CheckboxWithStrValueOutput)
    host_summary = fields.Nested(CheckboxWithStrValueOutput)
    service_summary = fields.Nested(CheckboxWithStrValueOutput)
    label = fields.Nested(CheckboxWithStrValueOutput)
    graphs_per_notification = fields.Nested(GraphsPerNotification)
    resolution_id = fields.Nested(CheckboxWithStrValueOutput)
    optional_timeout = fields.Nested(CheckboxWithStrValueOutput)


# MkEvent -----------------------------------------------------------


class CheckboxSysLogFacilityToUseValue(CheckboxOutput):
    value = fields.String(
        enum=list(get_args(SysLogFacilityStrType)),
        description="",
        example="",
    )


class CheckBoxIPAddressValue(CheckboxOutput):
    value = IPField(ip_type_allowed="ipv4")


class MkEventParamsResponse(PluginName):
    syslog_facility_to_use = fields.Nested(CheckboxSysLogFacilityToUseValue)
    ip_address_of_remote_event_console = fields.Nested(CheckBoxIPAddressValue)


# MSTeams -----------------------------------------------------------


class MSTeamsPluginResponse(PluginName):
    affected_host_groups = fields.Nested(CheckboxOutput)
    host_details = fields.Nested(CheckboxWithStrValueOutput)
    service_details = fields.Nested(CheckboxWithStrValueOutput)
    host_summary = fields.Nested(CheckboxWithStrValueOutput)
    service_summary = fields.Nested(CheckboxWithStrValueOutput)
    host_title = fields.Nested(CheckboxWithStrValueOutput)
    service_title = fields.Nested(CheckboxWithStrValueOutput)
    http_proxy = HTTP_PROXY_RESPONSE
    url_prefix_for_links_to_checkmk = URL_PREFIX_FOR_LINKS_TO_CHECKMK_RESPONSE
    webhook_url = fields.Nested(WebhookURLResponse)


# OpenGenie ---------------------------------------------------------


class OpsGeniePasswordResponse(ExplicitOrStoreOptions):
    store_id = PASSWORD_STORE_ID_SHOULD_EXIST
    key = fields.String(example="example key")


class CheckboxOpsGeniePriorityValue(CheckboxOutput):
    value = fields.String(
        enum=list(get_args(OpsGeniePriorityStrType)),
        description="",
        example="moderate",
    )


class CheckboxOpsExtraPropertiesValue(CheckboxOutput):
    value = fields.List(
        fields.String(enum=list(get_args(OpsgenieElement))),
        description="A list of extra properties to be included in the notification",
        example=["abstime", "address", "longoutput"],
    )


class OpsgeniePluginResponse(PluginName):
    api_key = fields.Nested(OpsGeniePasswordResponse)
    domain = fields.Nested(CheckboxWithStrValueOutput)
    disable_ssl_cert_verification = DISABLE_SSL_CERT_VERIFICATION
    http_proxy = fields.Nested(HttpProxyValue)
    owner = fields.Nested(CheckboxWithStrValueOutput)
    source = fields.Nested(CheckboxWithStrValueOutput)
    priority = fields.Nested(CheckboxOpsGeniePriorityValue)
    note_while_creating = fields.Nested(CheckboxWithStrValueOutput)
    note_while_closing = fields.Nested(CheckboxWithStrValueOutput)
    desc_for_host_alerts = fields.Nested(CheckboxWithStrValueOutput)
    desc_for_service_alerts = fields.Nested(CheckboxWithStrValueOutput)
    message_for_host_alerts = fields.Nested(CheckboxWithStrValueOutput)
    message_for_service_alerts = fields.Nested(CheckboxWithStrValueOutput)
    responsible_teams = fields.Nested(CheckboxWithListOfStrOutput)
    actions = fields.Nested(CheckboxWithListOfStrOutput)
    tags = fields.Nested(CheckboxWithListOfStrOutput)
    entity = fields.Nested(CheckboxWithStrValueOutput)
    extra_properties = fields.Nested(CheckboxOpsExtraPropertiesValue)


# PagerDuty ---------------------------------------------------------


class PagerDutyIntegrationKeyResponse(ExplicitOrStoreOptions):
    key = fields.String(example="some_key_example")
    store_id = PASSWORD_STORE_ID_SHOULD_EXIST


class PagerDutyPluginResponse(PluginName):
    integration_key = fields.Nested(PagerDutyIntegrationKeyResponse)
    disable_ssl_cert_verification = DISABLE_SSL_CERT_VERIFICATION
    url_prefix_for_links_to_checkmk = URL_PREFIX_FOR_LINKS_TO_CHECKMK_RESPONSE
    http_proxy = HTTP_PROXY_RESPONSE


# PushOver ----------------------------------------------------------
class PushOverPriority(BaseSchema):
    level = fields.String(
        enum=list(get_args(PushOverPriorityStringType)),
        description="The pushover priority level",
        example="normal",
    )
    retry = fields.Integer(
        example=60,
        description="The retry time in seconds",
    )
    expire = fields.Integer(
        example=3600,
        description="The expiration time in seconds",
    )
    receipt = fields.String(
        example="The receipt can be used to periodically poll receipts API to get "
        "the status of the notification. "
        'See <a href="https://pushover.net/api#receipt" target="_blank">'
        "Pushover receipts and callbacks</a> for more information.",
        description="The receipt of the message",
    )


class PushOverPriorityValue(CheckboxOutput):
    value = fields.Nested(
        PushOverPriority,
        description="The pushover priority level",
    )


class Sounds(CheckboxOutput):
    value = fields.String(
        enum=list(get_args(SoundType)),
        description="See https://pushover.net/api#sounds for more information and trying out available sounds.",
        example="none",
    )


class PushOverPluginResponse(PluginName):
    api_key = fields.String(
        example="azGDORePK8gMaC0QOYAMyEEuzJnyUi",
        description="You need to provide a valid API key to be able to send push notifications using Pushover. Register and login to Pushover, thn create your Check_MK installation as application and obtain your API key",
        pattern="^[a-zA-Z0-9]{30,40}$",
    )
    user_group_key = fields.String(
        example="azGDORePK8gMaC0QOYAMyEEuzJnyUi",
        description="Configure the user or group to receive the notifications by providing the user or group key here. The key can be obtained from the Pushover website.",
        pattern="^[a-zA-Z0-9]{30,40}$",
    )
    url_prefix_for_links_to_checkmk = URL_PREFIX_FOR_LINKS_TO_CHECKMK_RESPONSE
    priority = fields.Nested(PushOverPriorityValue)
    sound = fields.Nested(Sounds)
    http_proxy = HTTP_PROXY_RESPONSE


# ServiceNow --------------------------------------------------------


class CheckBoxUseSiteIDPrefix(CheckboxOutput):
    value = fields.String(
        enum=["use_site_id", "deactivated"],
        description="",
        example="use_site_id",
    )


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


class CheckboxWithManagementTypeStateValue(CheckboxOutput):
    value = fields.Nested(ManagementTypeStates)


class ManagementTypeParams(BaseSchema):
    host_description = fields.Nested(CheckboxWithStrValueOutput)
    service_description = fields.Nested(CheckboxWithStrValueOutput)
    host_short_description = fields.Nested(CheckboxWithStrValueOutput)
    service_short_description = fields.Nested(CheckboxWithStrValueOutput)
    caller = fields.String()
    urgency = fields.Nested(CheckboxWithStrValueOutput)
    impact = fields.Nested(CheckboxWithStrValueOutput)
    state_recovery = fields.Nested(CheckboxWithManagementTypeStateValue)
    state_acknowledgement = fields.Nested(CheckboxWithManagementTypeStateValue)
    state_downtime = fields.Nested(CheckboxWithManagementTypeStateValue)
    priority = fields.Nested(CheckboxWithStrValueOutput)


class ServiceNowMngmtType(BaseSchema):
    option = fields.String(
        enum=["case", "incident"],
        description="The management type",
        example="case",
    )
    params = fields.Nested(
        ManagementTypeParams,
    )


class ServiceNowPluginResponse(PluginName):
    servicenow_url = fields.String(
        example="https://myservicenow.com",
        description="Configure your ServiceNow URL here",
    )
    auth = fields.Nested(
        AuthResponse,
        description="The authentication credentials for the ServiceNow connection",
    )
    http_proxy = HTTP_PROXY_RESPONSE
    use_site_id_prefix = fields.Nested(CheckBoxUseSiteIDPrefix)
    optional_timeout = fields.Nested(CheckboxWithStrValueOutput)
    management_type = fields.Nested(ServiceNowMngmtType)


# Signl4 ------------------------------------------------------------


class SignL4TeamSecretResponse(ExplicitOrStoreOptions):
    store_id = PASSWORD_STORE_ID_SHOULD_EXIST
    secret = fields.String(example="http://example_webhook_url.com")


class Signl4PluginResponse(PluginName):
    team_secret = fields.Nested(
        SignL4TeamSecretResponse,
        description="The password for SignL4 Plugin.",
        example={"option": "password", "password": "my_unique_password"},
    )
    url_prefix_for_links_to_checkmk = URL_PREFIX_FOR_LINKS_TO_CHECKMK_RESPONSE
    disable_ssl_cert_verification = DISABLE_SSL_CERT_VERIFICATION
    http_proxy = HTTP_PROXY_RESPONSE


# Slack -------------------------------------------------------------


class SlackWebhookURLResponse(ExplicitOrStoreOptions):
    store_id = PASSWORD_STORE_ID_SHOULD_EXIST
    url = fields.String(example="http://example_webhook_url.com")


class SlackPluginResponse(PluginName):
    webhook_url = fields.Nested(SlackWebhookURLResponse)
    url_prefix_for_links_to_checkmk = URL_PREFIX_FOR_LINKS_TO_CHECKMK_RESPONSE
    disable_ssl_cert_verification = DISABLE_SSL_CERT_VERIFICATION
    http_proxy = HTTP_PROXY_RESPONSE


# SMS API -----------------------------------------------------------


class SMSAPIPAsswordResponse(ExplicitOrStoreOptions):
    store_id = PASSWORD_STORE_ID_SHOULD_EXIST
    password = fields.String(example="http://example_webhook_url.com")


class SMSAPIPluginResponse(PluginName):
    modem_type = fields.String(
        enum=["trb140"],
        example="trb140",
        description="Choose what modem is used. Currently supported is only Teltonika-TRB140.",
    )
    modem_url = fields.URL(
        example="https://mymodem.mydomain.example",
        description="Configure your modem URL here",
    )
    disable_ssl_cert_verification = DISABLE_SSL_CERT_VERIFICATION
    username = fields.String(
        example="username_a",
        description="Configure the user name here",
    )
    timeout = fields.String(
        example="10",
        description="Here you can configure timeout settings",
    )
    user_password = fields.Nested(SMSAPIPAsswordResponse)
    http_proxy = HTTP_PROXY_RESPONSE


# SMS ---------------------------------------------------------------


class SMSPluginResponse(PluginName):
    params = fields.List(
        fields.String,
        uniqueItems=True,
        description="The given parameters are available in scripts as NOTIFY_PARAMETER_1, NOTIFY_PARAMETER_2, etc. You may paste a text from your clipboard which contains several parts separated by ';' characters into the last input field. The text will then be split by these separators and the single parts are added into dedicated input fields.",
        example=["NOTIFY_PARAMETER_1", "NOTIFY_PARAMETER_1"],
    )


# Spectrum ----------------------------------------------------------


class SpectrumPluginResponse(PluginName):
    destination_ip = IPField(
        ip_type_allowed="ipv4",
        description="IP address of the Spectrum server receiving the SNMP trap",
    )
    snmp_community = fields.String(
        example="",
        description="SNMP community for the SNMP trap. The password entered here is stored in plain text within the monitoring site. This usually needed because the monitoring process needs to have access to the unencrypted password because it needs to submit it to authenticate with remote systems",
    )
    base_oid = fields.String(
        example="1.3.6.1.4.1.1234",
        description="The base OID for the trap content",
    )


# Victorops ---------------------------------------------------------


class SplunkRESTEndpointResponse(ExplicitOrStoreOptions):
    store_id = PASSWORD_STORE_ID_SHOULD_EXIST
    url = fields.String(
        example="https://alert.victorops.com/integrations/example",
    )


class VictoropsPluginResponse(PluginName):
    splunk_on_call_rest_endpoint = fields.Nested(SplunkRESTEndpointResponse)
    url_prefix_for_links_to_checkmk = URL_PREFIX_FOR_LINKS_TO_CHECKMK_RESPONSE
    disable_ssl_cert_verification = DISABLE_SSL_CERT_VERIFICATION
    http_proxy = HTTP_PROXY_RESPONSE


#  --------------------------------------------------------------


class RulePropertiesAttributes(BaseSchema):
    description = fields.String(
        description="A description or title of this rule.",
        example="Notify all contacts of a host/service via HTML email",
    )
    comment = fields.String(
        description="An optional comment that may be used to explain the purpose of this object.",
        example="An example comment",
    )
    documentation_url = fields.String(
        description="An optional URL pointing to documentation or any other page. This will be displayed as an icon and open a new page when clicked.",
        example="http://link/to/documentation",
    )
    do_not_apply_this_rule = fields.Nested(
        CheckboxOutput,
        description="Disabled rules are kept in the configuration but are not applied.",
        example={"state": "enabled"},
    )
    allow_users_to_deactivate = fields.Nested(
        CheckboxOutput,
        description="If you set this option then users are allowed to deactivate notifications that are created by this rule.",
        example={"state": "enabled"},
    )


class PluginBase(BaseSchema):
    option = fields.String(
        enum=[
            PluginOptions.CANCEL.value,
            PluginOptions.WITH_PARAMS.value,
            PluginOptions.WITH_CUSTOM_PARAMS.value,
        ],
        example=PluginOptions.CANCEL.value,
    )

    plugin_params = fields.Dict(
        description="The plug-in name and configuration parameters defined.",
    )

    def dump(self, obj: dict[str, Any], *args: Any, **kwargs: Any) -> Mapping:
        if obj["plugin_params"]["plugin_name"] not in get_builtin_plugin_names():
            return obj

        schema_mapper: Mapping[BuiltInPluginNames, type[BaseSchema]] = {
            "mail": HTMLEmailParamsResponse,
            "cisco_webex_teams": CiscoWebexPluginResponse,
            "mkeventd": MkEventParamsResponse,
            "asciimail": AsciiEmailParamsResponse,
            "ilert": IlertPluginResponse,
            "jira_issues": JiraPluginResponse,
            "opsgenie_issues": OpsgeniePluginResponse,
            "pagerduty": PagerDutyPluginResponse,
            "pushover": PushOverPluginResponse,
            "servicenow": ServiceNowPluginResponse,
            "signl4": Signl4PluginResponse,
            "slack": SlackPluginResponse,
            "sms_api": SMSAPIPluginResponse,
            "sms": SMSPluginResponse,
            "spectrum": SpectrumPluginResponse,
            "victorops": VictoropsPluginResponse,
            "msteams": MSTeamsPluginResponse,
        }

        plugin_params: PluginType = obj["plugin_params"]
        plugin_name = cast(BuiltInPluginNames, plugin_params["plugin_name"])
        schema_to_use = schema_mapper[plugin_name]
        obj.update({"plugin_params": schema_to_use().dump(plugin_params)})
        return obj


class NotificationBulkingCommonAttributes(CheckboxOutput):
    time_horizon = fields.Integer(
        description="Notifications are kept back for bulking at most for this time (seconds)",
        example=60,
    )
    max_bulk_size = fields.Integer(
        description="At most that many notifications are kept back for bulking. A value of 1 essentially turns off notification bulking.",
        example="1000",
    )
    notification_bulks_based_on = fields.List(
        fields.String(enum=list(get_args(GroupbyType))),
        uniqueItems=True,
    )
    notification_bulks_based_on_custom_macros = fields.List(
        fields.String,
        description="If you enter the names of host/service-custom macros here then for each different combination of values of those macros a separate bulk will be created. Service macros match first, if no service macro is found, the host macros are searched. This can be used in combination with the grouping by folder, host etc. Omit any leading underscore. Note: If you are using Nagios as a core you need to make sure that the values of the required macros are present in the notification context. This is done in check_mk_templates.cfg. If you macro is _FOO then you need to add the variables NOTIFY_HOST_FOO and NOTIFY_SERVICE_FOO. You may paste a text from your clipboard which contains several parts separated by ';' characters into the last input field. The text will then be split by these separators and the single parts are added into dedicated input fields",
        example="",
    )
    subject_for_bulk_notifications = fields.Nested(
        CheckboxWithStrValueOutput,
    )


class BulkOutsideTimePeriodValue(CheckboxOutput):
    value = fields.Nested(
        NotificationBulkingCommonAttributes,
    )


class NotificationBulking(NotificationBulkingCommonAttributes):
    time_period = fields.String(
        description="",
        example="24X7",
    )
    bulk_outside_timeperiod = fields.Nested(
        BulkOutsideTimePeriodValue,
    )


class WhenToBulk(BaseSchema):
    when_to_bulk = fields.String(
        enum=["always", "timeperiod"],
        description="Bulking can always happen or during a set time period",
        example="always",
    )
    params = fields.Nested(
        NotificationBulking,
    )


class NotificationBulkingCheckbox(CheckboxOutput):
    value = fields.Nested(WhenToBulk)


class NotificationPlugin(BaseSchema):
    notify_plugin = fields.Nested(PluginBase)
    notification_bulking = fields.Nested(NotificationBulkingCheckbox)


class ContactSelectionAttributes(BaseSchema):
    all_contacts_of_the_notified_object = fields.Nested(CheckboxOutput)
    all_users = fields.Nested(CheckboxOutput)
    all_users_with_an_email_address = fields.Nested(CheckboxOutput)
    the_following_users = fields.Nested(CheckboxWithListOfStrOutput)
    members_of_contact_groups = fields.Nested(CheckboxWithListOfStrOutput)
    explicit_email_addresses = fields.Nested(CheckboxWithListOfStrOutput)
    restrict_by_custom_macros = fields.Nested(MatchCustomMacrosOutput)
    restrict_by_contact_groups = fields.Nested(CheckboxWithListOfStrOutput)


class ConditionsAttributes(BaseSchema):
    match_sites = fields.Nested(CheckboxWithListOfStrOutput)
    match_folder = fields.Nested(CheckboxWithFolderStrOutput)
    match_host_tags = fields.Nested(CheckboxMatchHostTagsOutput)
    match_host_labels = fields.Nested(CheckboxWithListOfLabelsOutput)
    match_host_groups = fields.Nested(CheckboxWithListOfStrOutput)
    match_hosts = fields.Nested(CheckboxWithListOfStrOutput)
    match_exclude_hosts = fields.Nested(CheckboxWithListOfStrOutput)
    match_service_labels = fields.Nested(CheckboxWithListOfLabelsOutput)
    match_service_groups = fields.Nested(CheckboxWithListOfStrOutput)
    match_exclude_service_groups = fields.Nested(CheckboxWithListOfStrOutput)
    match_service_groups_regex = fields.Nested(CheckboxWithListOfServiceGroupsRegexOutput)
    match_exclude_service_groups_regex = fields.Nested(CheckboxWithListOfServiceGroupsRegexOutput)
    match_services = fields.Nested(CheckboxWithListOfStrOutput)
    match_exclude_services = fields.Nested(CheckboxWithListOfStrOutput)
    match_check_types = fields.Nested(CheckboxWithListOfStrOutput)
    match_plugin_output = fields.Nested(CheckboxWithStrValueOutput)
    match_contact_groups = fields.Nested(CheckboxWithListOfStrOutput)
    match_service_levels = fields.Nested(CheckboxWithFromToServiceLevelsOutput)
    match_only_during_time_period = fields.Nested(CheckboxWithStrValueOutput)
    match_host_event_type = fields.Nested(CheckboxHostEventTypeOutput)
    match_service_event_type = fields.Nested(CheckboxServiceEventTypeOutput)
    restrict_to_notification_numbers = fields.Nested(CheckboxRestrictNotificationNumbersOutput)
    throttle_periodic_notifications = fields.Nested(CheckboxThrottlePeriodicNotifcationsOuput)
    match_notification_comment = fields.Nested(CheckboxWithStrValueOutput)
    event_console_alerts = fields.Nested(MatchEventConsoleAlertsResponse)


class NotificationRuleAttributes(BaseSchema):
    rule_properties = fields.Nested(RulePropertiesAttributes)
    notification_method = fields.Nested(NotificationPlugin)
    contact_selection = fields.Nested(ContactSelectionAttributes)
    conditions = fields.Nested(ConditionsAttributes)


class NotificationRuleConfig(BaseSchema):
    rule_config = fields.Nested(NotificationRuleAttributes)


class NotificationRuleResponse(DomainObject):
    domainType = fields.Constant(
        "rule_notifications",
        description="The domain type of the object.",
    )
    extensions = fields.Nested(
        NotificationRuleConfig,
        description="The configuration attributes of a notification rule.",
        example={"rule_config": notification_rule_request_example()},
    )


class NotificationRuleResponseCollection(DomainObjectCollection):
    domainType = fields.Constant(
        "rule_notifications",
        description="The domain type of the objects in the collection.",
    )
    value = fields.List(
        fields.Nested(NotificationRuleResponse),
        description="A list of notification rule objects.",
        example=[
            {
                "links": [],
                "domainType": "rule_notifications",
                "id": "1",
                "title": "Rule Description",
                "members": {},
                "extensions": {"rule_config": notification_rule_request_example()},
            }
        ],
    )
