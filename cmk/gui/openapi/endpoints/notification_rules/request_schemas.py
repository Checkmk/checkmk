#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from typing import Any, get_args

from marshmallow import post_load, pre_load, ValidationError
from marshmallow_oneofschema import OneOfSchema
from urllib3.util import parse_url

from cmk.ccc.i18n import _

from cmk.utils.notify_types import (
    CaseStateStr,
    EmailBodyElementsType,
    get_builtin_plugin_names,
    GroupbyType,
    IlertPriorityType,
    IncidentStateStr,
    MgmntPriorityType,
    MgmntUrgencyType,
    OpsgenieElement,
    OpsGeniePriorityStrType,
    PluginOptions,
    PushOverPriorityStringType,
    RegexModes,
    SoundType,
    SysLogFacilityStrType,
    SysLogPriorityStrType,
)

from cmk.gui.exceptions import MKUserError
from cmk.gui.fields import (
    AuxTagIDField,
    ContactGroupField,
    FolderIDField,
    GlobalHTTPProxyField,
    GroupField,
    HostField,
    IPField,
    PasswordStoreIDField,
    ServiceLevelField,
    SiteField,
    SplunkURLField,
    TagGroupIDField,
    TimePeriodIDField,
)
from cmk.gui.fields.utils import BaseSchema
from cmk.gui.openapi.endpoints.notification_rules.request_example import (
    notification_rule_request_example,
)
from cmk.gui.utils.rule_specs.legacy_converter import convert_to_legacy_valuespec
from cmk.gui.watolib.notification_parameter import notification_parameter_registry
from cmk.gui.watolib.tags import load_tag_group
from cmk.gui.watolib.user_scripts import user_script_choices

from cmk import fields
from cmk.rulesets.v1.rule_specs import NotificationParameters


class Checkbox(BaseSchema):
    state = fields.String(
        enum=["enabled", "disabled"],
        required=True,
        description="To enable or disable this field",
        example="enabled",
    )


class CheckboxOneOfSchema(OneOfSchema):
    type_field = "state"
    type_field_remove = False


class OptionOneOfSchema(OneOfSchema):
    type_field = "option"
    type_field_remove = False


class CheckboxWithFolderStr(Checkbox):
    value = FolderIDField(
        presence="should_exist",
        required=True,
        description="This condition makes the rule match only hosts that are managed via WATO and that are contained in this folder - either directly or in one of its subfolders.",
    )


class AuxTag(BaseSchema):
    tag_type = fields.String(
        enum=["aux_tag"],
        required=True,
        example="aux_tag",
    )
    operator = fields.String(
        enum=["is_set", "is_not_set"],
        required=True,
        example="is_set",
        description="",
    )
    tag_id = AuxTagIDField(
        presence="should_exist",
        required=True,
        example="snmp",
        description="Tag ids are available via the aux tag endpoint.",
    )


class TagGroupBase(BaseSchema):
    tag_type = fields.String(
        enum=["tag_group"],
        required=True,
        example="aux_tag",
    )

    tag_group_id = TagGroupIDField(
        presence="should_exist",
        required=True,
        example="agent",
        description="Tag group ids are available via the host tag group endpoint.",
    )

    @post_load
    def _post_load(self, data: dict[str, Any], **_kwargs: Any) -> dict[str, Any]:
        tg = load_tag_group(ident=data["tag_group_id"])
        if tg is not None:
            existing_tag_ids = tg.get_tag_ids()

            if "tag_id" in data:
                if data["tag_id"] not in existing_tag_ids:
                    raise ValidationError(
                        f"The tag id {data['tag_id']} does not belong to the tag group {data['tag_group_id']}"
                    )
            if "tag_ids" in data:
                for tag_id in data["tag_ids"]:
                    if tag_id not in existing_tag_ids:
                        raise ValidationError(
                            f"The tag id {tag_id} does not belong to the tag group {data['tag_group_id']}"
                        )
        return data


class TagGroupNoneOfOrOneof(TagGroupBase):
    operator = fields.String(enum=["one_of", "none_of"])
    tag_ids = fields.List(
        AuxTagIDField(
            example="checkmk-agent",
            description="Tag groups tag ids are available via the host tag group endpoint.",
        ),
        example=["ip-v4-only", "ip-v6-only"],
    )


class TagGroupIsNotOrIs(TagGroupBase):
    operator = fields.String(enum=["is", "is_not"])
    tag_id = AuxTagIDField(
        example="checkmk-agent",
        description="Tag groups tag ids are available via the host tag group endpoint.",
    )


class TagGroupSelector(OneOfSchema):
    type_field = "operator"
    type_field_remove = False
    type_schemas = {
        "one_of": TagGroupNoneOfOrOneof,
        "none_of": TagGroupNoneOfOrOneof,
        "is_not": TagGroupIsNotOrIs,
        "is": TagGroupIsNotOrIs,
    }


class TagTypeSelector(OneOfSchema):
    type_field = "tag_type"
    type_field_remove = False
    type_schemas = {
        "aux_tag": AuxTag,
        "tag_group": TagGroupSelector,
    }


class CheckboxMatchHostTags(Checkbox):
    value = fields.List(
        fields.Nested(TagTypeSelector),
        required=True,
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


class CheckboxWithListOfSites(Checkbox):
    value = fields.List(
        SiteField(presence="should_exist"),
        required=True,
        description="Match only hosts of the selected sites.",
        example=["site_1", "site_2"],
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


class CheckboxWithStrValue(Checkbox):
    value = fields.String(
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


class CheckboxWithListOfStr(Checkbox):
    value = fields.List(
        fields.String,
        required=True,
    )


class HttpProxy(BaseSchema):
    option = fields.String(
        enum=["no_proxy", "environment", "url", "global"],
        required=True,
        example="",
    )


class HttpProxyUrl(HttpProxy):
    url = fields.String(
        required=True,
        example="http://example_proxy",
    )


class HttpProxyGlobal(HttpProxy):
    global_proxy_id = GlobalHTTPProxyField(
        required=True,
        presence="should_exist",
    )


class HttpProxyOptions(OneOfSchema):
    type_field = "option"
    type_field_remove = False
    type_schemas = {
        "no_proxy": HttpProxy,
        "environment": HttpProxy,
        "url": HttpProxyUrl,
        "global": HttpProxyGlobal,
    }


class HttpProxyValue(Checkbox):
    value = fields.Nested(
        HttpProxyOptions,
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


class FromToServiceLevels(BaseSchema):
    from_level = ServiceLevelField()
    to_level = ServiceLevelField()


class CheckboxWithFromToServiceLevels(Checkbox):
    value = fields.Nested(
        FromToServiceLevels,
        required=True,
        description="Host or service must be in the following service level to get notification",
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


class CheckboxWithListOfCheckTypes(Checkbox):
    value = fields.List(
        fields.String,
        required=True,
        uniqueItems=True,
        example=["3par_capacity", "acme_fan", "acme_realm"],
        description="Only apply the rule if the notification originates from certain types of check plug-ins. Note: Host notifications never match this rule if this option is being used",
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


class CheckboxWithListOfServiceGroups(Checkbox):
    value = fields.List(
        GroupField(
            group_type="service",
            should_exist=True,
            example="service_group_1",
        ),
        required=True,
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


class CheckboxWithTimePeriod(Checkbox):
    value = TimePeriodIDField(
        presence="should_exist",
        required=True,
        description="Match this rule only during times where the selected time period from the monitoring system is active",
    )


class StrValueOneOfSchema(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": CheckboxWithStrValue,
    }


class NotificationBulkingCommon(BaseSchema):
    subject_for_bulk_notifications = fields.Nested(
        StrValueOneOfSchema,
        required=True,
    )
    max_bulk_size = fields.Integer(
        required=True,
        description="At most that many notifications are kept back for bulking. A value of 1 essentially turns off notification bulking.",
        example="1000",
    )
    notification_bulks_based_on = fields.List(
        fields.String(
            enum=list(get_args(GroupbyType)),
        ),
        required=True,
        uniqueItems=True,
    )
    notification_bulks_based_on_custom_macros = fields.List(
        fields.String(
            required=True,
            description="If you enter the names of host/service-custom macros here then for each different combination of values of those macros a separate bulk will be created. Service macros match first, if no service macro is found, the host macros are searched. This can be used in combination with the grouping by folder, host etc. Omit any leading underscore. Note: If you are using Nagios as a core you need to make sure that the values of the required macros are present in the notification context. This is done in check_mk_templates.cfg. If you macro is _FOO then you need to add the variables NOTIFY_HOST_FOO and NOTIFY_SERVICE_FOO. You may paste a text from your clipboard which contains several parts separated by ';' characters into the last input field. The text will then be split by these separators and the single parts are added into dedicated input fields",
            example="",
        ),
        required=False,
    )


class NotificationBulkingAlways(NotificationBulkingCommon):
    time_horizon = fields.Integer(
        required=True,
        description="Notifications are kept back for bulking at most for this time (seconds)",
        example=60,
    )


class OutsideTimeperiodValue(Checkbox):
    value = fields.Nested(
        NotificationBulkingAlways,
    )


class TimePeriodOneOfSchema(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": OutsideTimeperiodValue,
    }


class NotificationBulkingTimePeriod(NotificationBulkingCommon):
    time_period = fields.String(
        required=True,
        description="",
        example="24X7",
    )
    bulk_outside_timeperiod = fields.Nested(
        TimePeriodOneOfSchema,
        required=True,
    )


class WhenToBulk(BaseSchema):
    when_to_bulk = fields.String(
        enum=["always", "timeperiod"],
        required=True,
        description="Bulking can always happen or during a set time period",
        example="always",
    )


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


class EventConsoleAlertAttributesBase(BaseSchema):
    match_type = fields.String(
        enum=["match_only_event_console_alerts", "do_not_match_event_console_alerts"],
        required=True,
        example="match_only_event_console_events",
        description="",
    )


class CheckboxWithListOfRuleIds(Checkbox):
    value = fields.List(
        fields.String,
        uniqueItems=True,
        required=True,
        example="",
        description="",
    )


class MatchRuleIdsOneOfSchema(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": CheckboxWithListOfRuleIds,
    }


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


class MatchSysLogPriOneOfSchema(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": CheckboxWithSysLogPriority,
    }


class MatchSysLogFacOneOfSchema(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": CheckboxWithSysLogFacility,
    }


class EventConsoleAlertAttrsCreate(BaseSchema):
    match_rule_ids = fields.Nested(
        MatchRuleIdsOneOfSchema,
    )
    match_syslog_priority = fields.Nested(
        MatchSysLogPriOneOfSchema,
    )
    match_syslog_facility = fields.Nested(
        MatchSysLogFacOneOfSchema,
    )
    match_event_comment = fields.Nested(
        StrValueOneOfSchema,
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


# Plugins -----------------------------------------------------------


class PluginName(BaseSchema):
    plugin_name = fields.String(
        enum=get_builtin_plugin_names(),
        required=True,
        description="The plug-in name.",
        example="mail",
    )


class EmailAndDisplayName(BaseSchema):
    address = fields.String(
        required=False,
        description="",
        example="mail@example.com",
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


class FromDetailsOneOfSchema(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": FromEmailAndNameCheckbox,
    }


class ReplyToOneOfSchema(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": ToEmailAndNameCheckbox,
    }


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


class SubjectHostOneOfSchema(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": SubjectForHostNotificationsCheckbox,
    }


class SubjectServiceOneOfSchema(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": SubjectForServiceNotificationsCheckbox,
    }


class CheckboxSortOrderValue(Checkbox):
    value = fields.String(
        enum=["oldest_first", "newest_first"],
        required=True,
        description="With this option you can specify, whether the oldest (default) or the newest notification should get shown at the top of the notification mail",
        example="oldest_first",
    )


class SortOrderOneOfSchema(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": CheckboxSortOrderValue,
    }


class MailBaseCreate(PluginName):
    from_details = fields.Nested(
        FromDetailsOneOfSchema,
        required=True,
    )
    reply_to = fields.Nested(
        ReplyToOneOfSchema,
        required=True,
    )
    subject_for_host_notifications = fields.Nested(
        SubjectHostOneOfSchema,
        required=True,
    )
    subject_for_service_notifications = fields.Nested(
        SubjectServiceOneOfSchema,
        required=True,
    )
    send_separate_notification_to_every_recipient = fields.Nested(
        Checkbox,
        required=True,
    )
    sort_order_for_bulk_notifications = fields.Nested(
        SortOrderOneOfSchema,
        required=True,
    )


# Ascii Mail --------------------------------------------------------


class AsciiMailPluginCreate(MailBaseCreate):
    body_head_for_both_host_and_service_notifications = fields.Nested(
        StrValueOneOfSchema,
        required=True,
    )
    body_tail_for_host_notifications = fields.Nested(
        StrValueOneOfSchema,
        required=True,
    )
    body_tail_for_service_notifications = fields.Nested(
        StrValueOneOfSchema,
        required=True,
    )


# HTML Mail ---------------------------------------------------------


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


class Authentication(BaseSchema):
    method = fields.String(
        enum=["plaintext"],
        required=False,
        description="The authentication method is fixed at 'plaintext' for now.",
        example="plaintext",
        load_default="plaintext",
    )
    user = fields.String(
        required=False,
        description="The username for the SMTP connection.",
        example="user_1",
        load_default="",
    )
    password = fields.String(
        required=False,
        description="The password for the SMTP connection.",
        example="password",
        load_default="",
    )


class AuthenticationValue(Checkbox):
    value = fields.Nested(
        Authentication,
        required=True,
    )


class AuthOneOfSchema(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": AuthenticationValue,
    }


class EnableSynchronousDeliveryViaSMTP(BaseSchema):
    auth = fields.Nested(
        AuthOneOfSchema,
    )
    encryption = fields.String(
        enum=["ssl_tls", "starttls"],
        required=False,
        description="The encryption type for the SMTP connection.",
        example="ssl_tls",
    )
    port = fields.Integer(
        required=False,
        description="",
        example=25,
    )
    smarthosts = fields.List(
        fields.String(),
        uniqueItems=True,
        load_default=[],
    )


class EnableSynchronousDeliveryViaSMTPValue(Checkbox):
    value = fields.Nested(
        EnableSynchronousDeliveryViaSMTP,
    )


class EmailInfoOneOfSchema(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": CheckboxWithListOfEmailInfoStrs,
    }


class InsertHtmlOneOfSchema(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": HtmlSectionBetweenBodyAndTableCheckbox,
    }


class EnableSyncOneOfSchema(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": EnableSynchronousDeliveryViaSMTPValue,
    }


class GraphsPerNotification(Checkbox):
    value = fields.Integer(
        required=True,
        description="Sets a limit for the number of graphs that are displayed in a notification",
        example=5,
    )


class GraphsPerNotificationOneOfSchema(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": GraphsPerNotification,
    }


class BulkNotificationsWithGraphs(Checkbox):
    value = fields.Integer(
        required=True,
        description="Sets a limit for the number of notifications in a bulk for which graphs are displayed. If you do not use bulk notifications this option is ignored. Note that each graph increases the size of the mail and takes time to renderon the monitoring server. Therefore, large bulks may exceed the maximum size for attachements or the plug-in may run into a timeout so that a failed notification is produced",
        example=5,
    )


class BulkNotificationsOneOfSchema(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": BulkNotificationsWithGraphs,
    }


class CheckMKURLPrefixBase(BaseSchema):
    option = CHECKMK_URL_PREFIX_OPTION


class CheckMKURLPrefixAuto(CheckMKURLPrefixBase):
    schema = CHECKMK_PREFIX_SCHEMA


class CheckMKURLPrefixManual(CheckMKURLPrefixBase):
    url = CHECKMK_URL_PREFIX_URL


class ManualOrAutomaticSelector(OptionOneOfSchema):
    type_schemas = {
        "automatic": CheckMKURLPrefixAuto,
        "manual": CheckMKURLPrefixManual,
    }


class CheckMKURLPrefixValue(Checkbox):
    value = fields.Nested(
        ManualOrAutomaticSelector,
        description="If you use Automatic HTTP/s, the URL prefix for host and service links within the notification is filled automatically. If you specify an URL prefix here, then several parts of the notification are armed with hyperlinks to your Check_MK GUI. In both cases, the recipient of the notification can directly visit the host or service in question in Check_MK. Specify an absolute URL including the .../check_mk/",
    )


class UrlPrefixOneOfSchema(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": CheckMKURLPrefixValue,
    }


URL_PREFIX_FOR_LINKS_TO_CHECKMK_CREATE = fields.Nested(
    UrlPrefixOneOfSchema,
    required=True,
)


class HTMLMailPluginCreate(MailBaseCreate):
    info_to_be_displayed_in_the_email_body = fields.Nested(
        EmailInfoOneOfSchema,
        required=True,
    )
    insert_html_section_between_body_and_table = fields.Nested(
        InsertHtmlOneOfSchema,
        required=True,
    )

    url_prefix_for_links_to_checkmk = URL_PREFIX_FOR_LINKS_TO_CHECKMK_CREATE

    display_graphs_among_each_other = fields.Nested(
        Checkbox,
        required=True,
    )
    enable_sync_smtp = fields.Nested(
        EnableSyncOneOfSchema,
        required=True,
    )
    graphs_per_notification = fields.Nested(
        GraphsPerNotificationOneOfSchema,
        required=True,
    )
    bulk_notifications_with_graphs = fields.Nested(
        BulkNotificationsOneOfSchema,
        required=True,
    )


# Cisco -------------------------------------------------------------

DISABLE_SSL_CERT_VERIFICATION = fields.Nested(
    Checkbox,
    required=True,
    description="Ignore unverified HTTPS request warnings. Use with caution.",
)


class ExplicitOrStoreOptions(BaseSchema):
    option = fields.String(
        enum=["store", "explicit"],
        required=True,
        example="store",
    )


PASSWORD_STORE_ID_SHOULD_EXIST = PasswordStoreIDField(
    presence="should_exist",
    required=True,
)


class CiscoPasswordStore(ExplicitOrStoreOptions):
    store_id = PASSWORD_STORE_ID_SHOULD_EXIST


class CiscoExplicitWebhookUrl(ExplicitOrStoreOptions):
    url = fields.URL(
        required=True,
        example="http://example_webhook_url.com",
    )


class CiscoUrlOrStoreSelector(OptionOneOfSchema):
    type_schemas = {
        "explicit": CiscoExplicitWebhookUrl,
        "store": CiscoPasswordStore,
    }


class HttpProxyOneOfSchema(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": HttpProxyValue,
    }


HTTP_PROXY_CREATE = fields.Nested(
    HttpProxyOneOfSchema,
    required=True,
    description="Use the proxy settings from the environment variables. The variables NO_PROXY, HTTP_PROXY and HTTPS_PROXY are taken into account during execution.",
)


class CiscoWebexPluginCreate(PluginName):
    disable_ssl_cert_verification = DISABLE_SSL_CERT_VERIFICATION
    webhook_url = fields.Nested(CiscoUrlOrStoreSelector)
    url_prefix_for_links_to_checkmk = URL_PREFIX_FOR_LINKS_TO_CHECKMK_CREATE
    http_proxy = HTTP_PROXY_CREATE


# MkEvent -----------------------------------------------------------


class CheckboxSysLogFacilityToUseValue(Checkbox):
    value = fields.String(
        enum=list(get_args(SysLogFacilityStrType)),
        required=False,
        description="",
        example="",
    )


class SysLogFacilityOneOfSchema(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": CheckboxSysLogFacilityToUseValue,
    }


class CheckBoxIPAddressValue(Checkbox):
    value = IPField(
        ip_type_allowed="ipv4",
        required=True,
    )


class IPAddressOneOfSchema(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": CheckBoxIPAddressValue,
    }


class MkEventDPluginCreate(PluginName):
    syslog_facility_to_use = fields.Nested(
        SysLogFacilityOneOfSchema,
        required=True,
    )
    ip_address_of_remote_event_console = fields.Nested(
        IPAddressOneOfSchema,
        required=True,
    )


# Ilert -------------------------------------------------------------


class IlertPasswordStoreID(ExplicitOrStoreOptions):
    store_id = PASSWORD_STORE_ID_SHOULD_EXIST


class IlertAPIKey(ExplicitOrStoreOptions):
    key = fields.String(
        required=True,
        example="example_api_key",
    )


class IlertKeyOrStoreSelector(OptionOneOfSchema):
    type_schemas = {
        "explicit": IlertAPIKey,
        "store": IlertPasswordStoreID,
    }


class IlertPluginCreate(PluginName):
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
    api_key = fields.Nested(IlertKeyOrStoreSelector, required=True)
    url_prefix_for_links_to_checkmk = URL_PREFIX_FOR_LINKS_TO_CHECKMK_CREATE
    http_proxy = HTTP_PROXY_CREATE


# Jira --------------------------------------------------------------
class AuthOptions(BaseSchema):
    option = fields.String(
        enum=["explicit_token", "token_store_id", "explicit_password", "password_store_id"],
        required=True,
        example="password_store_id",
    )


class BasicAuth(AuthOptions):
    username = fields.String(
        required=True,
        example="username_example",
        description="Your username",
    )


class BasicAuthExplicit(BasicAuth):
    password = fields.String(
        required=True,
        example="password_example",
        description="Your password",
    )


class BasicAuthStorePassword(BasicAuth):
    store_id = PASSWORD_STORE_ID_SHOULD_EXIST


class ExplicitToken(AuthOptions):
    token = fields.String(
        required=True,
        example="token_example",
        description="Your personal access token",
    )


class AuthStoreToken(AuthOptions):
    store_id = PASSWORD_STORE_ID_SHOULD_EXIST


class AuthSelector(OptionOneOfSchema):
    type_schemas = {
        "password_store_id": BasicAuthStorePassword,
        "explicit_password": BasicAuthExplicit,
        "explicit_token": ExplicitToken,
        "token_store_id": AuthStoreToken,
    }


class JiraPluginCreate(PluginName):
    jira_url = fields.String(
        required=False,
        example="http://jira_url_example.com",
        description="Configure the Jira URL here",
    )
    disable_ssl_cert_verification = DISABLE_SSL_CERT_VERIFICATION
    auth = fields.Nested(
        AuthSelector,
        required=True,
        description="The authentication credentials for the Jira connection",
    )
    project_id = fields.String(
        required=True,
        example="",
        description="The numerical Jira project ID. If not set, it will be retrieved from a custom user attribute named jiraproject. If that is not set, the notification will fail",
    )
    issue_type_id = fields.String(
        required=True,
        example="",
        description="The numerical Jira issue type ID. If not set, it will be retrieved from a custom user attribute named jiraissuetype. If that is not set, the notification will fail",
    )
    host_custom_id = fields.String(
        required=True,
        example="",
        description="The numerical Jira custom field ID for host problems",
    )
    service_custom_id = fields.String(
        required=True,
        example="",
        description="The numerical Jira custom field ID for service problems",
    )
    monitoring_url = fields.String(
        required=True,
        example="",
        description="Configure the base URL for the monitoring web GUI here. Include the site name. Used for linking to Checkmk out of Jira",
    )
    site_custom_id = fields.Nested(
        StrValueOneOfSchema,
        required=True,
        description="The numerical ID of the Jira custom field for sites. Please use this option if you have multiple sites in a distributed setup which send their notifications to the same Jira instance",
    )
    priority_id = fields.Nested(
        StrValueOneOfSchema,
        required=True,
        description="The numerical Jira priority ID. If not set, it will be retrieved from a custom user attribute named jirapriority. If that is not set, the standard priority will be used",
    )
    host_summary = fields.Nested(
        StrValueOneOfSchema,
        required=True,
        description="Here you are allowed to use all macros that are defined in the notification context",
    )
    service_summary = fields.Nested(
        StrValueOneOfSchema,
        required=True,
        description="Here you are allowed to use all macros that are defined in the notification context",
    )
    label = fields.Nested(
        StrValueOneOfSchema,
        required=True,
        description="Here you can set a custom label for new issues. If not set, 'monitoring' will be used",
    )
    graphs_per_notification = fields.Nested(
        GraphsPerNotificationOneOfSchema,
        load_default=lambda: {"state": "disabled"},
        description="Here you can set a limit for the number of graphs that are displayed in a notification. If not set, 0 will be used",
    )
    resolution_id = fields.Nested(
        StrValueOneOfSchema,
        required=True,
        description="The numerical Jira resolution transition ID. 11 - 'To Do', 21 - 'In Progress', 31 - 'Done'",
    )
    optional_timeout = fields.Nested(
        StrValueOneOfSchema,
        required=True,
        description="Here you can configure timeout settings.",
    )


# OpsGenie ----------------------------------------------------------


class OpsGenieStoreID(ExplicitOrStoreOptions):
    store_id = PASSWORD_STORE_ID_SHOULD_EXIST


class OpsGenieExplicitKey(ExplicitOrStoreOptions):
    key = fields.String(
        required=True,
        example="example_api_key",
    )


class OpsGenisStoreOrExplicitKeySelector(OptionOneOfSchema):
    type_schemas = {
        "explicit": OpsGenieExplicitKey,
        "store": OpsGenieStoreID,
    }


class CheckboxOpsGeniePriorityValue(Checkbox):
    value = fields.String(
        enum=list(get_args(OpsGeniePriorityStrType)),
        required=True,
        description="",
        example="moderate",
    )


class OpsGeniePriorityOneOfSchema(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": CheckboxOpsGeniePriorityValue,
    }


class ListOfStrOneOfSchema(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": CheckboxWithListOfStr,
    }


class ListOfExtraProperties(Checkbox):
    value = fields.List(
        fields.String(enum=list(get_args(OpsgenieElement))),
        load_default=["abstime", "address", "longoutput"],
        uniqueItems=True,
    )


class ListOfExtraPropertiesOneOfSchema(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": ListOfExtraProperties,
    }


class OpsGeniePluginCreate(PluginName):
    api_key = fields.Nested(
        OpsGenisStoreOrExplicitKeySelector,
        required=True,
    )
    domain = fields.Nested(
        StrValueOneOfSchema,
        required=True,
        description="If you have an european account, please set the domain of your opsgenie. Specify an absolute URL like https://api.eu.opsgenie.com",
    )
    disable_ssl_cert_verification = DISABLE_SSL_CERT_VERIFICATION
    http_proxy = HTTP_PROXY_CREATE
    owner = fields.Nested(
        StrValueOneOfSchema,
        required=True,
        description="Sets the user of the alert. Display name of the request owner",
    )
    source = fields.Nested(
        StrValueOneOfSchema,
        required=True,
        description="Source field of the alert. Default value is IP address of the incoming request",
    )
    priority = fields.Nested(
        OpsGeniePriorityOneOfSchema,
        required=True,
    )
    note_while_creating = fields.Nested(
        StrValueOneOfSchema,
        required=True,
        description="Additional note that will be added while creating the alert",
    )
    note_while_closing = fields.Nested(
        StrValueOneOfSchema,
        required=True,
        description="Additional note that will be added while closing the alert",
    )
    desc_for_host_alerts = fields.Nested(
        StrValueOneOfSchema,
        required=True,
        description="Description field of host alert that is generally used to provide a detailed information about the alert",
    )
    desc_for_service_alerts = fields.Nested(
        StrValueOneOfSchema,
        required=True,
        description="Description field of service alert that is generally used to provide a detailed information about the alert",
    )
    message_for_host_alerts = fields.Nested(
        StrValueOneOfSchema,
        required=True,
        description="",
    )
    message_for_service_alerts = fields.Nested(
        StrValueOneOfSchema,
        required=True,
        description="",
    )
    responsible_teams = fields.Nested(
        ListOfStrOneOfSchema,
        required=True,
        description="Team names which will be responsible for the alert. If the API Key belongs to a team integration, this field will be overwritten with the owner team. You may paste a text from your clipboard which contains several parts separated by ';' characters into the last input field. The text will then be split by these separators and the single parts are added into dedicated input fields",
    )
    actions = fields.Nested(
        ListOfStrOneOfSchema,
        required=True,
        description="Custom actions that will be available for the alert. You may paste a text from your clipboard which contains several parts separated by ';' characters into the last input field. The text will then be split by these separators and the single parts are added into dedicated input fields",
    )
    tags = fields.Nested(
        ListOfStrOneOfSchema,
        required=True,
        description="Tags of the alert. You may paste a text from your clipboard which contains several parts separated by ';' characters into the last input field. The text will then be split by these separators and the single parts are added into dedicated input fields",
    )
    entity = fields.Nested(
        StrValueOneOfSchema,
        required=True,
        description="Is used to specify which domain the alert is related to",
    )
    extra_properties = fields.Nested(
        ListOfExtraPropertiesOneOfSchema,
        description="A list of extra properties that will be included in the notification",
        load_default=lambda: {"state": "disabled"},
    )


# PagerDuty ---------------------------------------------------------


class PagerDutyAPIKeyStoreID(ExplicitOrStoreOptions):
    store_id = PASSWORD_STORE_ID_SHOULD_EXIST


class PagerDutyExplicitKey(ExplicitOrStoreOptions):
    key = fields.String(
        required=True,
        example="some_key_example",
    )


class PagerDutyStoreOrIntegrationKeySelector(OptionOneOfSchema):
    type_schemas = {
        "explicit": PagerDutyExplicitKey,
        "store": PagerDutyAPIKeyStoreID,
    }


class PagerDutyPluginCreate(PluginName):
    integration_key = fields.Nested(
        PagerDutyStoreOrIntegrationKeySelector,
        required=True,
    )
    disable_ssl_cert_verification = DISABLE_SSL_CERT_VERIFICATION
    url_prefix_for_links_to_checkmk = URL_PREFIX_FOR_LINKS_TO_CHECKMK_CREATE
    http_proxy = HTTP_PROXY_CREATE


# PushOver ----------------------------------------------------------


class PushOverPriorityBase(BaseSchema):
    level = fields.String(
        enum=list(get_args(PushOverPriorityStringType)),
        required=True,
        description="The pushover priority level",
        example="normal",
    )


class PushOverPriorityEmergency(BaseSchema):
    level = fields.String(
        enum=["emergency"],
        required=True,
        description="The pushover priority level",
        example="emergency",
    )
    retry = fields.Integer(
        required=True,
        description="The retry interval in seconds",
        example=60,
    )
    expire = fields.Integer(
        required=True,
        description="The expiration time in seconds",
        example=3600,
    )
    receipt = fields.String(
        required=True,
        description="The receipt of the message",
        example="The receipt can be used to periodically poll receipts API to get "
        "the status of the notification. "
        'See <a href="https://pushover.net/api#receipt" target="_blank">'
        "Pushover receipts and callbacks</a> for more information.",
        pattern="^[a-zA-Z0-9]{30,40}$",
    )


class PushOverPrioritySelector(OneOfSchema):
    type_field = "level"
    type_field_remove = False
    type_schemas = {
        "lowest": PushOverPriorityBase,
        "low": PushOverPriorityBase,
        "normal": PushOverPriorityBase,
        "high": PushOverPriorityBase,
        "emergency": PushOverPriorityEmergency,
    }


class PushOverPriority(Checkbox):
    value = fields.Nested(
        PushOverPrioritySelector,
        required=True,
        description="The pushover priority level",
        example="normal",
    )


class PushOverOneOfSchema(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": PushOverPriority,
    }


class Sounds(Checkbox):
    value = fields.String(
        enum=list(get_args(SoundType)),
        required=True,
        description="See https://pushover.net/api#sounds for more information and trying out available sounds.",
        example="none",
    )


class SoundsOneOfSchema(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": Sounds,
    }


class PushOverPluginCreate(PluginName):
    api_key = fields.String(
        required=True,
        example="azGDORePK8gMaC0QOYAMyEEuzJnyUi",
        description="You need to provide a valid API key to be able to send push notifications using Pushover. Register and login to Pushover, thn create your Check_MK installation as application and obtain your API key",
        pattern="^[a-zA-Z0-9]{30,40}$",
    )
    user_group_key = fields.String(
        required=True,
        example="azGDORePK8gMaC0QOYAMyEEuzJnyUi",
        description="Configure the user or group to receive the notifications by providing the user or group key here. The key can be obtained from the Pushover website.",
        pattern="^[a-zA-Z0-9]{30,40}$",
    )
    url_prefix_for_links_to_checkmk = URL_PREFIX_FOR_LINKS_TO_CHECKMK_CREATE
    priority = fields.Nested(
        PushOverOneOfSchema,
        required=True,
    )
    sound = fields.Nested(
        SoundsOneOfSchema,
        required=True,
    )
    http_proxy = HTTP_PROXY_CREATE


# ServiceNow --------------------------------------------------------
class CheckBoxUseSiteIDPrefix(Checkbox):
    value = fields.String(
        enum=["use_site_id", "deactivated"],
        required=True,
        description="",
        example="use_site_id",
    )


class SiteIDPrefixOneOfSchema(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": CheckBoxUseSiteIDPrefix,
    }


class IncidentAndCaseParams(BaseSchema):
    host_description = fields.Nested(
        StrValueOneOfSchema,
    )
    service_description = fields.Nested(
        StrValueOneOfSchema,
    )
    host_short_description = fields.Nested(
        StrValueOneOfSchema,
    )
    service_short_description = fields.Nested(
        StrValueOneOfSchema,
    )


class CheckboxWithMgmtTypePriorityValue(Checkbox):
    value = fields.String(
        enum=list(get_args(MgmntPriorityType)),
        required=True,
    )


class PriorityOneOfSchema(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": CheckboxWithMgmtTypePriorityValue,
    }


class ManagementTypeCaseStates(BaseSchema):
    start_predefined = fields.String(
        enum=list(get_args(CaseStateStr)),
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


class StateRecoveryOneOfSchema(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": CheckboxWithManagementTypeStateCaseValues,
    }


class CaseParams(IncidentAndCaseParams):
    priority = fields.Nested(PriorityOneOfSchema)
    state_recovery = fields.Nested(StateRecoveryOneOfSchema)


class ManagementTypeIncedentStates(BaseSchema):
    start_predefined = fields.String(
        enum=list(get_args(IncidentStateStr)),
        example="hold",
    )
    start_integer = fields.Integer(
        example=1,
        minimum=0,
    )
    end_predefined = fields.String(
        enum=list(get_args(IncidentStateStr)),
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


class TypeStateOneOfSchema(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": CheckboxWithManagementTypeStateIncedentValues,
    }


class CheckboxWithMgmtTypeUrgencyValue(Checkbox):
    value = fields.String(
        enum=list(get_args(MgmntUrgencyType)),
        required=True,
    )


class TypeUrgencyOneOfSchema(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": CheckboxWithMgmtTypeUrgencyValue,
    }


class IncidentParams(IncidentAndCaseParams):
    caller = fields.String(
        required=True,
        example="Alice",
        description="Caller is the user on behalf of whom the incident is being reported within ServiceNow.",
    )
    urgency = fields.Nested(
        TypeUrgencyOneOfSchema,
    )
    impact = fields.Nested(
        StrValueOneOfSchema,
    )
    state_acknowledgement = fields.Nested(
        TypeStateOneOfSchema,
    )
    state_downtime = fields.Nested(
        TypeStateOneOfSchema,
    )
    state_recovery = fields.Nested(
        TypeStateOneOfSchema,
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


class MgmntTypeSelector(OptionOneOfSchema):
    type_schemas = {
        "case": MgmntTypeCaseParams,
        "incident": MgmntTypeIncidentParams,
    }


class ServiceNowPluginCreate(PluginName):
    servicenow_url = fields.String(
        required=True,
        example="https://myservicenow.com",
        description="Configure your ServiceNow URL here",
    )
    auth = fields.Nested(
        AuthSelector,
        required=True,
        description="The authentication credentials for the ServiceNow connection",
    )
    http_proxy = HTTP_PROXY_CREATE
    use_site_id_prefix = fields.Nested(
        SiteIDPrefixOneOfSchema,
        required=True,
    )
    optional_timeout = fields.Nested(
        StrValueOneOfSchema,
        required=True,
    )
    management_type = fields.Nested(
        MgmntTypeSelector,
    )


# Signl4 ------------------------------------------------------------


class SignL4TeamSecretStoreID(ExplicitOrStoreOptions):
    store_id = PASSWORD_STORE_ID_SHOULD_EXIST


class SignL4TeamSecret(ExplicitOrStoreOptions):
    secret = fields.String(
        required=True,
        example="team_secret_example",
    )


class SignL4ExplicitOrStoreSelector(OptionOneOfSchema):
    type_schemas = {
        "explicit": SignL4TeamSecret,
        "store": SignL4TeamSecretStoreID,
    }


class Signl4PluginCreate(PluginName):
    team_secret = fields.Nested(SignL4ExplicitOrStoreSelector, required=True)
    url_prefix_for_links_to_checkmk = URL_PREFIX_FOR_LINKS_TO_CHECKMK_CREATE
    disable_ssl_cert_verification = DISABLE_SSL_CERT_VERIFICATION
    http_proxy = HTTP_PROXY_CREATE


# Slack -------------------------------------------------------------


class SlackWebhookStore(ExplicitOrStoreOptions):
    store_id = PASSWORD_STORE_ID_SHOULD_EXIST


def _validate_slack_uses_https(url: object) -> bool:
    if not isinstance(url, str):
        return False

    parsed = parse_url(url)
    if (
        isinstance(parsed.host, str)
        and parsed.host.endswith("slack.com")
        and parsed.scheme != "https"
    ):  # Mattermost uses the same plugin, but we allow HTTP there
        raise ValidationError("Slack Webhooks must use HTTPS")

    return True


class SlackWebhookURL(ExplicitOrStoreOptions):
    url = fields.URL(
        required=True,
        example="https://example_webhook_url.com",
        schemes={"http", "https"},
        validate=_validate_slack_uses_https,
        description="Configure your Slack or Mattermost Webhook URL here. Slack Webhooks must use HTTPS",
    )


class SlackStoreOrExplicitURLSelector(OptionOneOfSchema):
    type_schemas = {
        "explicit": SlackWebhookURL,
        "store": SlackWebhookStore,
    }


class SlackPluginCreate(PluginName):
    webhook_url = fields.Nested(SlackStoreOrExplicitURLSelector, required=True)
    url_prefix_for_links_to_checkmk = URL_PREFIX_FOR_LINKS_TO_CHECKMK_CREATE
    disable_ssl_cert_verification = DISABLE_SSL_CERT_VERIFICATION
    http_proxy = HTTP_PROXY_CREATE


# SMS API -----------------------------------------------------------


class SMSAPIPStoreID(ExplicitOrStoreOptions):
    store_id = PASSWORD_STORE_ID_SHOULD_EXIST


class SMSAPIExplicitPassword(ExplicitOrStoreOptions):
    password = fields.String(
        required=True,
        example="https://example_webhook_url.com",
    )


class SMSAPIPasswordSelector(OptionOneOfSchema):
    type_schemas = {
        "explicit": SMSAPIExplicitPassword,
        "store": SMSAPIPStoreID,
    }


class SMSAPIPluginCreate(PluginName):
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
    username = fields.String(
        required=True,
        example="username_a",
        description="Configure the user name here",
    )
    timeout = fields.String(
        required=True,
        example="10",
        description="Here you can configure timeout settings",
    )
    user_password = fields.Nested(
        SMSAPIPasswordSelector,
        required=True,
    )
    http_proxy = HTTP_PROXY_CREATE


# SMS ---------------------------------------------------------------


class SMSPluginBase(PluginName):
    params = fields.List(
        fields.String,
        required=True,
        uniqueItems=True,
        description="The given parameters are available in scripts as NOTIFY_PARAMETER_1, NOTIFY_PARAMETER_2, etc. You may paste a text from your clipboard which contains several parts separated by ';' characters into the last input field. The text will then be split by these separators and the single parts are added into dedicated input fields.",
        example=["NOTIFY_PARAMETER_1", "NOTIFY_PARAMETER_1"],
    )


# Spectrum ----------------------------------------------------------


class SpectrumPluginBase(PluginName):
    destination_ip = IPField(
        ip_type_allowed="ipv4",
        required=True,
        description="IP address of the Spectrum server receiving the SNMP trap",
    )
    snmp_community = fields.String(
        required=True,
        example="",
        description="SNMP community for the SNMP trap. The password entered here is stored in plain text within the monitoring site. This usually needed because the monitoring process needs to have access to the unencrypted password because it needs to submit it to authenticate with remote systems",
    )
    base_oid = fields.String(
        required=True,
        example="1.3.6.1.4.1.1234",
        description="The base OID for the trap content",
    )


# Victorops ---------------------------------------------------------


class SplunkStoreID(ExplicitOrStoreOptions):
    store_id = PASSWORD_STORE_ID_SHOULD_EXIST


class SplunkURLExplicit(ExplicitOrStoreOptions):
    url = SplunkURLField(required=True)


class SplunkRESTEndpointSelector(OptionOneOfSchema):
    type_schemas = {
        "explicit": SplunkURLExplicit,
        "store": SplunkStoreID,
    }


class VictoropsPluginCreate(PluginName):
    splunk_on_call_rest_endpoint = fields.Nested(SplunkRESTEndpointSelector, required=True)
    url_prefix_for_links_to_checkmk = URL_PREFIX_FOR_LINKS_TO_CHECKMK_CREATE
    disable_ssl_cert_verification = DISABLE_SSL_CERT_VERIFICATION
    http_proxy = HTTP_PROXY_CREATE


# MSteams -----------------------------------------------------------


class MSTeamsURLResponse(ExplicitOrStoreOptions):
    store_id = PASSWORD_STORE_ID_SHOULD_EXIST
    url = fields.String(example="http://example_webhook_url.com")


class MSTeamsExplicitWebhookUrl(ExplicitOrStoreOptions):
    url = fields.URL(
        required=True,
        example="http://example_webhook_url.com",
    )


class MSTeamsUrlOrStoreSelector(OptionOneOfSchema):
    type_schemas = {
        "explicit": MSTeamsExplicitWebhookUrl,
        "store": MSTeamsURLResponse,
    }


class MSTeamsPluginCreate(PluginName):
    affected_host_groups = fields.Nested(
        Checkbox,
        required=True,
        description="Enable/disable if we show affected host groups in the created message",
    )
    host_details = fields.Nested(
        StrValueOneOfSchema,
        required=True,
        description="Enable/disable the details for host notifications",
    )
    service_details = fields.Nested(
        StrValueOneOfSchema,
        required=True,
        description="Enable/disable the details for service notifications",
    )
    host_summary = fields.Nested(
        StrValueOneOfSchema,
        required=True,
        description="Enable/disable the summary for host notifications",
    )
    service_summary = fields.Nested(
        StrValueOneOfSchema,
        required=True,
        description="Enable/disable the summary for service notifications",
    )
    host_title = fields.Nested(
        StrValueOneOfSchema,
        required=True,
        description="Enable/disable the title for host notifications",
    )
    service_title = fields.Nested(
        StrValueOneOfSchema,
        required=True,
        description="Enable/disable the title for service notifications",
    )
    http_proxy = HTTP_PROXY_CREATE
    url_prefix_for_links_to_checkmk = URL_PREFIX_FOR_LINKS_TO_CHECKMK_CREATE
    webhook_url = fields.Nested(MSTeamsUrlOrStoreSelector, required=True)


# -------------------------------------------------------------------


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


class PluginNameBuiltInOrCustom(BaseSchema):
    plugin_name = fields.String(
        required=True,
        description="The plug-in name.",
        example="mail",
    )


class PluginWithoutParams(BaseSchema):
    option = fields.Constant(
        PluginOptions.CANCEL.value,
        required=True,
        description="Cancel previous notifications",
        example=PluginOptions.CANCEL.value,
    )

    plugin_params = fields.Nested(
        PluginNameBuiltInOrCustom,
        required=True,
    )


class PluginWithParams(BaseSchema):
    option = fields.Constant(
        PluginOptions.WITH_PARAMS.value,
        required=True,
        description="Create notifications with parameters",
        example=PluginOptions.WITH_PARAMS.value,
    )
    plugin_params = fields.Nested(
        PluginSelector,
        required=True,
    )


class NonRegisteredCustomPlugin(BaseSchema):
    params = fields.List(
        fields.String,
        required=True,
        example=["param1", "param2", "param2"],
    )


class CustomPlugin(BaseSchema):
    plugin_name = fields.String(
        required=True,
        description="The custom plug-in name",
        example="mail",
    )

    @pre_load
    def _pre_load(self, data: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        return {k: v for k, v in data.items() if k in self.fields}

    @post_load(pass_original=True)
    def _post_load(
        self,
        data: dict[str, Any],
        original_data: dict[str, Any],
        **_unused_args: Any,
    ) -> dict[str, Any]:
        dif: dict[str, Any] = {k: v for k, v in original_data.items() if k not in data}
        plugin_name = data["plugin_name"]

        if plugin_name not in [n for (n, _) in user_script_choices("notifications")]:
            raise ValidationError(f"{plugin_name} does not exist")

        if plugin_name in notification_parameter_registry:
            instance = notification_parameter_registry[data["plugin_name"]]
            if isinstance(instance, NotificationParameters):
                vs = convert_to_legacy_valuespec(instance.parameter_form(), _)
            else:
                vs = instance.spec()
            try:
                vs.validate_datatype(dif, "plugin_params")
            except MKUserError as exc:
                message = exc.message if ": " not in exc.message else exc.message.split(": ")[-1]
                if re.search("The entry (.*)", exc.message) is not None:
                    message = "A required (sub-)field is missing."

                raise ValidationError(
                    message=message,
                    field_name="_schema" if exc.varname is None else exc.varname.split("_p_")[-1],
                )

            try:
                vs.validate_value(dif, "plugin_params")
            except MKUserError as exc:
                raise ValidationError(
                    message=exc.message,
                    field_name="_schema" if exc.varname is None else exc.varname.split("_p_")[-1],
                )

        else:
            NonRegisteredCustomPlugin().load(dif)

        return original_data


class CustomPluginWithParams(BaseSchema):
    option = fields.Constant(
        PluginOptions.WITH_CUSTOM_PARAMS.value,
        required=True,
        description="Create notifications with custom parameters",
        example=PluginOptions.WITH_CUSTOM_PARAMS.value,
    )
    plugin_params = fields.Nested(
        CustomPlugin,
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


class NotificationBulk(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": NotificationBulkingValue,
    }


class StringCheckbox(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": CheckboxWithStrValue,
    }


class ListOfStringCheckbox(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": CheckboxWithListOfStr,
    }


class TheFollowingUsers(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": CheckboxWithListOfStr,
    }


class ListOfContactGroupsCheckbox(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": CheckboxWithListOfContactGroups,
    }


class ExplicitEmailAddressesCheckbox(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": CheckboxWithListOfEmailAddresses,
    }


class CustomMacrosCheckbox(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": MatchCustomMacros,
    }


class MatchSitesCheckbox(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": CheckboxWithListOfSites,
    }


class MatchFolderCheckbox(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": CheckboxWithFolderStr,
    }


class MatchHostTagsCheckbox(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": CheckboxMatchHostTags,
    }


class MatchHostsCheckbox(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": CheckboxWithListOfHosts,
    }


class MatchServiceGroupsCheckbox(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": CheckboxWithListOfServiceGroups,
    }


class MatchServicesCheckbox(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": CheckboxWithListOfStr,
    }


class MatchHostGroupsCheckbox(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": CheckboxWithListOfHostGroups,
    }


class MatchLabelsCheckbox(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": CheckboxWithListOfLabels,
    }


class MatchServiceGroupRegexCheckbox(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": CheckboxWithListOfServiceGroupsRegex,
    }


class MatchCheckTypesCheckbox(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": CheckboxWithListOfCheckTypes,
    }


class MatchContactGroupsCheckbox(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": CheckboxWithListOfContactGroups,
    }


class MatchServiceLevelsCheckbox(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": CheckboxWithFromToServiceLevels,
    }


class MatchTimePeriodCheckbox(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": CheckboxWithTimePeriod,
    }


class MatchHostEventTypeCheckbox(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": CheckboxHostEventType,
    }


class MatchServiceEventTypeCheckbox(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": CheckboxServiceEventType,
    }


class RestrictNotificationNumCheckbox(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": CheckboxRestrictNotificationNumbers,
    }


class ThorttlePeriodicNotificationsCheckbox(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": CheckboxThrottlePeriodicNotifcations,
    }


class EventConsoleAlertCheckbox(CheckboxOneOfSchema):
    type_schemas = {
        "disabled": Checkbox,
        "enabled": CheckboxEventConsoleAlerts,
    }


class RuleProperties(BaseSchema):
    description = fields.String(
        description="A description or title of this rule.",
        example="Notify all contacts of a host/service via HTML email",
        required=True,
    )
    comment = fields.String(
        description="An optional comment that may be used to explain the purpose of this object.",
        example="An example comment",
        required=True,
    )
    documentation_url = fields.String(
        description="An optional URL pointing to documentation or any other page. This will be displayed as an icon and open a new page when clicked.",
        example="http://link/to/documentation",
        required=True,
    )
    do_not_apply_this_rule = fields.Nested(
        Checkbox,
        description="Disabled rules are kept in the configuration but are not applied.",
        example={"state": "enabled"},
        required=True,
    )
    allow_users_to_deactivate = fields.Nested(
        Checkbox,
        description="If you set this option then users are allowed to deactivate notifications that are created by this rule.",
        example={"state": "enabled"},
        required=True,
    )


class PluginOptionsSelector(OptionOneOfSchema):
    type_schemas = {
        PluginOptions.CANCEL.value: PluginWithoutParams,
        PluginOptions.WITH_PARAMS.value: PluginWithParams,
        PluginOptions.WITH_CUSTOM_PARAMS.value: CustomPluginWithParams,
    }


class RuleNotificationMethod(BaseSchema):
    notify_plugin = fields.Nested(
        PluginOptionsSelector,
        required=True,
    )
    notification_bulking = fields.Nested(NotificationBulk)


class ContactSelection(BaseSchema):
    all_contacts_of_the_notified_object = fields.Nested(Checkbox, required=True)
    all_users = fields.Nested(Checkbox, required=True)
    all_users_with_an_email_address = fields.Nested(Checkbox, required=True)
    the_following_users = fields.Nested(TheFollowingUsers, required=True)
    members_of_contact_groups = fields.Nested(ListOfContactGroupsCheckbox, required=True)
    explicit_email_addresses = fields.Nested(ExplicitEmailAddressesCheckbox, required=True)
    restrict_by_contact_groups = fields.Nested(ListOfContactGroupsCheckbox, required=True)
    restrict_by_custom_macros = fields.Nested(CustomMacrosCheckbox, required=True)


class RuleConditions(BaseSchema):
    match_sites = fields.Nested(MatchSitesCheckbox, required=True)
    match_folder = fields.Nested(MatchFolderCheckbox, required=True)
    match_host_tags = fields.Nested(MatchHostTagsCheckbox, required=True)
    match_host_labels = fields.Nested(MatchLabelsCheckbox, required=True)
    match_host_groups = fields.Nested(MatchHostGroupsCheckbox, required=True)
    match_hosts = fields.Nested(MatchHostsCheckbox, required=True)
    match_exclude_hosts = fields.Nested(MatchHostsCheckbox, required=True)
    match_service_labels = fields.Nested(MatchLabelsCheckbox, required=True)
    match_service_groups = fields.Nested(MatchServiceGroupsCheckbox, required=True)
    match_exclude_service_groups = fields.Nested(MatchServiceGroupsCheckbox, required=True)
    match_service_groups_regex = fields.Nested(MatchServiceGroupRegexCheckbox, required=True)
    match_exclude_service_groups_regex = fields.Nested(
        MatchServiceGroupRegexCheckbox, required=True
    )
    match_services = fields.Nested(MatchServicesCheckbox, required=True)
    match_exclude_services = fields.Nested(MatchServicesCheckbox, required=True)
    match_check_types = fields.Nested(MatchCheckTypesCheckbox, required=True)
    match_plugin_output = fields.Nested(StringCheckbox, required=True)
    match_contact_groups = fields.Nested(MatchContactGroupsCheckbox, required=True)
    match_service_levels = fields.Nested(MatchServiceLevelsCheckbox, required=True)
    match_only_during_time_period = fields.Nested(MatchTimePeriodCheckbox, required=True)
    match_host_event_type = fields.Nested(MatchHostEventTypeCheckbox, required=True)
    match_service_event_type = fields.Nested(MatchServiceEventTypeCheckbox, required=True)
    restrict_to_notification_numbers = fields.Nested(RestrictNotificationNumCheckbox, required=True)
    throttle_periodic_notifications = fields.Nested(
        ThorttlePeriodicNotificationsCheckbox, required=True
    )
    match_notification_comment = fields.Nested(StringCheckbox, required=True)
    event_console_alerts = fields.Nested(EventConsoleAlertCheckbox, required=True)


class RuleNotification(BaseSchema):
    rule_properties = fields.Nested(
        RuleProperties,
        required=True,
    )
    notification_method = fields.Nested(
        RuleNotificationMethod,
        required=True,
    )
    contact_selection = fields.Nested(
        ContactSelection,
        required=True,
    )
    conditions = fields.Nested(
        RuleConditions,
        required=True,
    )


class NotificationRuleRequest(BaseSchema):
    rule_config = fields.Nested(
        RuleNotification,
        required=True,
        description="",
        example=notification_rule_request_example(),
    )
