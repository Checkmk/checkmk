#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.fields.utils import BaseSchema
from cmk.gui.plugins.openapi.endpoints.notification_rules.common_schemas import (
    AllContacts,
    AllUsers,
    AllUsersWithEmail,
    CustomMacrosCheckbox,
    EventConsoleAlertCheckbox,
    ExplicitEmailAddressesCheckbox,
    ListOfContactGroupsCheckbox,
    MatchCheckTypesCheckbox,
    MatchContactGroupsCheckbox,
    MatchFolderCheckbox,
    MatchHostEventTypeCheckbox,
    MatchHostGroupsCheckbox,
    MatchHostsCheckbox,
    MatchHostTagsCheckbox,
    MatchLabelsCheckbox,
    MatchServiceEventTypeCheckbox,
    MatchServiceGroupRegexCheckbox,
    MatchServiceGroupsCheckbox,
    MatchServiceLevelsCheckbox,
    MatchServicesCheckbox,
    MatchSitesCheckbox,
    MatchTimePeriodCheckbox,
    NotificationBulk,
    NotificationPlugin,
    RestrictNotificationNumCheckbox,
    RulePropertiesAllowDeactivate,
    RulePropertiesComment,
    RulePropertiesDescription,
    RulePropertiesDocURL,
    RulePropertiesDoNotApplyRule,
    StringCheckbox,
    TheFollowingUsers,
    ThorttlePeriodicNotificationsCheckbox,
)
from cmk.gui.plugins.openapi.endpoints.notification_rules.request_example import (
    notification_rule_request_example,
)

from cmk import fields


class RuleProperties(BaseSchema):
    description = RulePropertiesDescription(required=True)
    comment = RulePropertiesComment(required=True)
    documentation_url = RulePropertiesDocURL(required=True)
    do_not_apply_this_rule = RulePropertiesDoNotApplyRule(required=True)
    allow_users_to_deactivate = RulePropertiesAllowDeactivate(required=True)


class RuleNotificationMethod(BaseSchema):
    notify_plugin = NotificationPlugin(required=True)
    notification_bulking = NotificationBulk(required=True)


class ContactSelection(BaseSchema):
    all_contacts_of_the_notified_object = AllContacts(required=True)
    all_users = AllUsers(required=True)
    all_users_with_an_email_address = AllUsersWithEmail(required=True)
    the_following_users = TheFollowingUsers(required=True)
    members_of_contact_groups = ListOfContactGroupsCheckbox(required=True)
    explicit_email_addresses = ExplicitEmailAddressesCheckbox(required=True)
    restrict_by_contact_groups = ListOfContactGroupsCheckbox(required=True)
    restrict_by_custom_macros = CustomMacrosCheckbox(required=True)


class RuleConditions(BaseSchema):
    match_sites = MatchSitesCheckbox(required=True)
    match_folder = MatchFolderCheckbox(required=True)
    match_host_tags = MatchHostTagsCheckbox(required=True)
    match_host_labels = MatchLabelsCheckbox(required=True)
    match_host_groups = MatchHostGroupsCheckbox(required=True)
    match_hosts = MatchHostsCheckbox(required=True)
    match_exclude_hosts = MatchHostsCheckbox(required=True)
    match_service_labels = MatchLabelsCheckbox(required=True)
    match_service_groups = MatchServiceGroupsCheckbox(required=True)
    match_exclude_service_groups = MatchServiceGroupsCheckbox(required=True)
    match_service_groups_regex = MatchServiceGroupRegexCheckbox(required=True)
    match_exclude_service_groups_regex = MatchServiceGroupRegexCheckbox(required=True)
    match_services = MatchServicesCheckbox(required=True)
    match_exclude_services = MatchServicesCheckbox(required=True)
    match_check_types = MatchCheckTypesCheckbox(required=True)
    match_plugin_output = StringCheckbox(required=True)
    match_contact_groups = MatchContactGroupsCheckbox(required=True)
    match_service_levels = MatchServiceLevelsCheckbox(required=True)
    match_only_during_time_period = MatchTimePeriodCheckbox(required=True)
    match_host_event_type = MatchHostEventTypeCheckbox(required=True)
    match_service_event_type = MatchServiceEventTypeCheckbox(required=True)
    restrict_to_notification_numbers = RestrictNotificationNumCheckbox(required=True)
    throttle_periodic_notifications = ThorttlePeriodicNotificationsCheckbox(required=True)
    match_notification_comment = StringCheckbox(required=True)
    event_console_alerts = EventConsoleAlertCheckbox(required=True)


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
