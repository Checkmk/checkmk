#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from typing import Any, cast, Type

from cmk.utils.notify_types import NotificationPluginNameStr

from cmk.gui.fields.utils import BaseSchema
from cmk.gui.plugins.openapi.endpoints.notification_rules.common_schemas import (
    AsciiEmailParamsResponse,
    Checkbox,
    CheckboxHostEventType,
    CheckboxMatchHostTags,
    CheckboxRestrictNotificationNumbers,
    CheckboxServiceEventType,
    CheckboxThrottlePeriodicNotifcations,
    CheckboxWithFromToServiceLevels,
    CheckboxWithListOfLabels,
    CheckboxWithListOfServiceGroupsRegex,
    CheckboxWithListOfStr,
    CheckboxWithStr,
    CheckboxWithStrValue,
    CiscoWebexPluginResponse,
    HTMLEmailParamsResponse,
    IlertPluginResponse,
    JiraPluginResponse,
    MatchCustomMacros,
    MatchEventConsoleAlertsResponse,
    MAX_BULK_SIZE,
    MkEventParamsResponse,
    MSTeamsPluginResponse,
    NOTIFICATION_BULKS_BASED_ON,
    NOTIFICATION_BULKS_BASED_ON_CUSTOM_MACROS,
    OpenGeniePluginResponse,
    PagerDutyPluginResponse,
    PushOverPluginResponse,
    RulePropertiesAllowDeactivate,
    RulePropertiesComment,
    RulePropertiesDescription,
    RulePropertiesDocURL,
    RulePropertiesDoNotApplyRule,
    ServiceNowPluginResponse,
    Signl4PluginResponse,
    SlackPluginResponse,
    SMSAPIPluginResponse,
    SMSPluginBase,
    SpectrumPluginBase,
    TIME_HORIZON,
    TIME_PERIOD,
    VictoropsPluginResponse,
    WHEN_TO_BULK,
)
from cmk.gui.plugins.openapi.endpoints.notification_rules.request_example import (
    notification_rule_request_example,
)
from cmk.gui.plugins.openapi.restful_objects.response_schemas import (
    DomainObject,
    DomainObjectCollection,
)
from cmk.gui.rest_api_types.notifications_rule_types import APINotifyPlugin

from cmk import fields


class RulePropertiesAttributes(BaseSchema):
    description = RulePropertiesDescription(required=True)
    comment = RulePropertiesComment(required=True)
    documentation_url = RulePropertiesDocURL(required=True)
    do_not_apply_this_rule = RulePropertiesDoNotApplyRule(required=True)
    allow_users_to_deactivate = RulePropertiesAllowDeactivate(required=True)


class PluginBase(BaseSchema):
    option = fields.String(
        enum=[
            "cancel_previous_notifications",
            "create_notification_with_the_following_parameters",
            "create_notification_with_the_following_custom_parameters",
        ],
        required=True,
    )

    def dump(self, obj: APINotifyPlugin, *args: Any, **kwargs: Any) -> Mapping:
        schema_mapper = cast(
            Mapping[NotificationPluginNameStr, Type[BaseSchema]],
            {
                "mail": HTMLEmailParamsResponse,
                "cisco_webex_teams": CiscoWebexPluginResponse,
                "mkeventd": MkEventParamsResponse,
                "asciimail": AsciiEmailParamsResponse,
                "ilert": IlertPluginResponse,
                "jira_issues": JiraPluginResponse,
                "opsgenie_issues": OpenGeniePluginResponse,
                "pagerduty": PagerDutyPluginResponse,
                "pushover": PushOverPluginResponse,
                "servicenow": ServiceNowPluginResponse,
                "signl4": Signl4PluginResponse,
                "slack": SlackPluginResponse,
                "sms_api": SMSAPIPluginResponse,
                "sms": SMSPluginBase,
                "spectrum": SpectrumPluginBase,
                "victorops": VictoropsPluginResponse,
                "msteams": MSTeamsPluginResponse,
            },
        )

        # If it's a built-in plugin, use the corresponding schema
        # If not, it's a 3rd party plugin, let it through.
        plugin_params = obj["plugin_params"]
        plugin_name = plugin_params["plugin_name"]
        if schema_to_use := schema_mapper.get(plugin_name):
            result = schema_to_use().dump(plugin_params)
            obj.update({"plugin_params": result})

        return obj


class NotificationBulkingCommonAttributes(Checkbox):
    time_horizon = TIME_HORIZON
    max_bulk_size = MAX_BULK_SIZE
    notification_bulks_based_on = NOTIFICATION_BULKS_BASED_ON
    notification_bulks_based_on_custom_macros = NOTIFICATION_BULKS_BASED_ON_CUSTOM_MACROS
    subject_for_bulk_notifications = fields.Nested(
        CheckboxWithStrValue,
    )


class BulkOutsideTimePeriodValue(Checkbox):
    value = fields.Nested(NotificationBulkingCommonAttributes)


class NotificationBulking(NotificationBulkingCommonAttributes):
    time_period = TIME_PERIOD
    bulk_outside_timeperiod = fields.Nested(
        BulkOutsideTimePeriodValue,
        required=True,
    )


class WhenToBulk(BaseSchema):
    when_to_bulk = WHEN_TO_BULK
    params = fields.Nested(
        NotificationBulking,
        required=True,
    )


class NotificationBulkingCheckbox(Checkbox):
    value = fields.Nested(
        WhenToBulk,
        required=True,
    )


class NotificationPlugin(BaseSchema):
    notify_plugin = fields.Nested(PluginBase)
    notification_bulking = fields.Nested(NotificationBulkingCheckbox)


class ContactSelectionAttributes(BaseSchema):
    all_contacts_of_the_notified_object = fields.Nested(Checkbox)
    all_users = fields.Nested(Checkbox)
    all_users_with_an_email_address = fields.Nested(Checkbox)
    the_following_users = fields.Nested(CheckboxWithListOfStr)
    members_of_contact_groups = fields.Nested(CheckboxWithListOfStr)
    explicit_email_addresses = fields.Nested(CheckboxWithListOfStr)
    restrict_by_custom_macros = fields.Nested(MatchCustomMacros)
    restrict_by_contact_groups = fields.Nested(CheckboxWithListOfStr)


class ConditionsAttributes(BaseSchema):
    match_sites = fields.Nested(CheckboxWithListOfStr)
    match_folder = fields.Nested(CheckboxWithStr)
    match_host_tags = fields.Nested(CheckboxMatchHostTags)
    match_host_labels = fields.Nested(CheckboxWithListOfLabels)
    match_host_groups = fields.Nested(CheckboxWithListOfStr)
    match_hosts = fields.Nested(CheckboxWithListOfStr)
    match_exclude_hosts = fields.Nested(CheckboxWithListOfStr)
    match_service_labels = fields.Nested(CheckboxWithListOfLabels)
    match_service_groups = fields.Nested(CheckboxWithListOfStr)
    match_exclude_service_groups = fields.Nested(CheckboxWithListOfStr)
    match_service_groups_regex = fields.Nested(CheckboxWithListOfServiceGroupsRegex)
    match_exclude_service_groups_regex = fields.Nested(CheckboxWithListOfServiceGroupsRegex)
    match_services = fields.Nested(CheckboxWithListOfStr)
    match_exclude_services = fields.Nested(CheckboxWithListOfStr)
    match_check_types = fields.Nested(CheckboxWithListOfStr)
    match_plugin_output = fields.Nested(CheckboxWithStr)
    match_contact_groups = fields.Nested(CheckboxWithListOfStr)
    match_service_levels = fields.Nested(CheckboxWithFromToServiceLevels)
    match_only_during_time_period = fields.Nested(CheckboxWithStr)
    match_host_event_type = fields.Nested(CheckboxHostEventType)
    match_service_event_type = fields.Nested(CheckboxServiceEventType)
    restrict_to_notification_numbers = fields.Nested(CheckboxRestrictNotificationNumbers)
    throttle_periodic_notifications = fields.Nested(CheckboxThrottlePeriodicNotifcations)
    match_notification_comment = fields.Nested(CheckboxWithStr)
    event_console_alerts = fields.Nested(MatchEventConsoleAlertsResponse)


class NotificationRuleAttributes(BaseSchema):
    rule_properties = fields.Nested(RulePropertiesAttributes)
    notification_method = fields.Nested(NotificationPlugin)
    contact_selection = fields.Nested(ContactSelectionAttributes)
    conditions = fields.Nested(ConditionsAttributes)


class NotificationRuleConfig(BaseSchema):
    rule_config = fields.Nested(
        NotificationRuleAttributes,
    )


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
