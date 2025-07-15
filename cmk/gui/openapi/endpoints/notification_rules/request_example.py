#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Event notification rule api request/response example"""

from cmk.gui.rest_api_types.notifications_rule_types import APINotificationRule
from cmk.utils.notify_types import PluginOptions


def notification_rule_request_example() -> APINotificationRule:
    r: APINotificationRule = {
        "rule_properties": {
            "description": "A description or title of this rule.",
            "comment": "A example comment.",
            "documentation_url": "http://link/to/documentation",
            "do_not_apply_this_rule": {"state": "disabled"},
            "allow_users_to_deactivate": {"state": "enabled"},
        },
        "notification_method": {
            "notify_plugin": {
                "option": PluginOptions.WITH_PARAMS.value,
                "plugin_params": {
                    "plugin_name": "mail",
                    "from_details": {"state": "disabled"},
                    "reply_to": {"state": "disabled"},
                    "subject_for_host_notifications": {"state": "disabled"},
                    "subject_for_service_notifications": {"state": "disabled"},
                    "info_to_be_displayed_in_the_email_body": {"state": "disabled"},
                    "insert_html_section_between_body_and_table": {"state": "disabled"},
                    "url_prefix_for_links_to_checkmk": {"state": "disabled"},
                    "sort_order_for_bulk_notifications": {"state": "disabled"},
                    "send_separate_notification_to_every_recipient": {"state": "disabled"},
                    "enable_sync_smtp": {"state": "disabled"},
                    "display_graphs_among_each_other": {"state": "disabled"},
                    "graphs_per_notification": {"state": "disabled"},
                    "bulk_notifications_with_graphs": {"state": "disabled"},
                },
            },
            "notification_bulking": {"state": "disabled"},
        },
        "contact_selection": {
            "all_contacts_of_the_notified_object": {"state": "disabled"},
            "all_users": {"state": "disabled"},
            "all_users_with_an_email_address": {"state": "disabled"},
            "the_following_users": {"state": "disabled"},
            "members_of_contact_groups": {"state": "disabled"},
            "explicit_email_addresses": {"state": "disabled"},
            "restrict_by_custom_macros": {"state": "disabled"},
            "restrict_by_contact_groups": {"state": "disabled"},
        },
        "conditions": {
            "match_sites": {"state": "disabled"},
            "match_folder": {"state": "disabled"},
            "match_host_tags": {"state": "disabled"},
            "match_host_labels": {"state": "disabled"},
            "match_host_groups": {"state": "disabled"},
            "match_hosts": {"state": "disabled"},
            "match_exclude_hosts": {"state": "disabled"},
            "match_service_labels": {"state": "disabled"},
            "match_service_groups": {"state": "disabled"},
            "match_exclude_service_groups": {"state": "disabled"},
            "match_service_groups_regex": {"state": "disabled"},
            "match_exclude_service_groups_regex": {"state": "disabled"},
            "match_services": {"state": "disabled"},
            "match_exclude_services": {"state": "disabled"},
            "match_check_types": {"state": "disabled"},
            "match_plugin_output": {"state": "disabled"},
            "match_contact_groups": {"state": "disabled"},
            "match_service_levels": {"state": "disabled"},
            "match_only_during_time_period": {"state": "disabled"},
            "match_host_event_type": {"state": "disabled"},
            "match_service_event_type": {"state": "disabled"},
            "restrict_to_notification_numbers": {"state": "disabled"},
            "throttle_periodic_notifications": {"state": "disabled"},
            "match_notification_comment": {"state": "disabled"},
            "event_console_alerts": {"state": "disabled"},
        },
    }
    return r
