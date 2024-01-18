#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from marshmallow_oneofschema import OneOfSchema

from cmk.gui.fields.utils import BaseSchema
from cmk.gui.openapi.endpoints.notification_rules.common_schemas import (
    AlwaysBulk,
    Checkbox,
    CheckboxEventConsoleAlerts,
    CheckboxHostEventType,
    CheckboxMatchHostTags,
    CheckboxRestrictNotificationNumbers,
    CheckboxServiceEventType,
    CheckboxThrottlePeriodicNotifcations,
    CheckboxWithFolderStr,
    CheckboxWithFromToServiceLevels,
    CheckboxWithListOfCheckTypes,
    CheckboxWithListOfContactGroups,
    CheckboxWithListOfEmailAddresses,
    CheckboxWithListOfHostGroups,
    CheckboxWithListOfHosts,
    CheckboxWithListOfLabels,
    CheckboxWithListOfServiceGroups,
    CheckboxWithListOfServiceGroupsRegex,
    CheckboxWithListOfSites,
    CheckboxWithListOfStr,
    CheckboxWithStrValue,
    CheckboxWithTimePeriod,
    MatchCustomMacros,
    NotificationPlugin,
    RulePropertiesAllowDeactivate,
    RulePropertiesComment,
    RulePropertiesDescription,
    RulePropertiesDocURL,
    RulePropertiesDoNotApplyRule,
    TimePeriod,
)
from cmk.gui.openapi.endpoints.notification_rules.request_example import (
    notification_rule_request_example,
)

from cmk import fields


class CheckboxOneOfSchema(OneOfSchema):
    type_field = "state"
    type_field_remove = False


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
    description = RulePropertiesDescription(required=True)
    comment = RulePropertiesComment(required=True)
    documentation_url = RulePropertiesDocURL(required=True)
    do_not_apply_this_rule = RulePropertiesDoNotApplyRule(required=True)
    allow_users_to_deactivate = RulePropertiesAllowDeactivate(required=True)


class RuleNotificationMethod(BaseSchema):
    notify_plugin = NotificationPlugin(required=True)
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
