#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.utils.livestatus_helpers.types import Column, Table

# yapf: disable


class Downtimes(Table):
    __tablename__ = 'downtimes'

    author = Column(
        'author',
        col_type='string',
        description='The contact that scheduled the downtime',
    )
    """The contact that scheduled the downtime"""

    comment = Column(
        'comment',
        col_type='string',
        description='A comment text',
    )
    """A comment text"""

    duration = Column(
        'duration',
        col_type='int',
        description='The duration of the downtime in seconds',
    )
    """The duration of the downtime in seconds"""

    end_time = Column(
        'end_time',
        col_type='time',
        description='The end time of the downtime as UNIX timestamp',
    )
    """The end time of the downtime as UNIX timestamp"""

    entry_time = Column(
        'entry_time',
        col_type='time',
        description='The time the entry was made as UNIX timestamp',
    )
    """The time the entry was made as UNIX timestamp"""

    fixed = Column(
        'fixed',
        col_type='int',
        description='A 1 if the downtime is fixed, a 0 if it is flexible',
    )
    """A 1 if the downtime is fixed, a 0 if it is flexible"""

    host_accept_passive_checks = Column(
        'host_accept_passive_checks',
        col_type='int',
        description='Whether passive host checks are accepted (0/1)',
    )
    """Whether passive host checks are accepted (0/1)"""

    host_acknowledged = Column(
        'host_acknowledged',
        col_type='int',
        description='Whether the current problem has been acknowledged (0/1)',
    )
    """Whether the current problem has been acknowledged (0/1)"""

    host_acknowledgement_type = Column(
        'host_acknowledgement_type',
        col_type='int',
        description='Type of acknowledgement (0: none, 1: normal, 2: sticky)',
    )
    """Type of acknowledgement (0: none, 1: normal, 2: sticky)"""

    host_action_url = Column(
        'host_action_url',
        col_type='string',
        description='An optional URL to custom actions or information about this host',
    )
    """An optional URL to custom actions or information about this host"""

    host_action_url_expanded = Column(
        'host_action_url_expanded',
        col_type='string',
        description='The same as action_url, but with the most important macros expanded',
    )
    """The same as action_url, but with the most important macros expanded"""

    host_active_checks_enabled = Column(
        'host_active_checks_enabled',
        col_type='int',
        description='Whether active checks of the object are enabled (0/1)',
    )
    """Whether active checks of the object are enabled (0/1)"""

    host_address = Column(
        'host_address',
        col_type='string',
        description='IP address',
    )
    """IP address"""

    host_alias = Column(
        'host_alias',
        col_type='string',
        description='An alias name for the host',
    )
    """An alias name for the host"""

    host_check_command = Column(
        'host_check_command',
        col_type='string',
        description='Logical command name for active checks',
    )
    """Logical command name for active checks"""

    host_check_command_expanded = Column(
        'host_check_command_expanded',
        col_type='string',
        description='Logical command name for active checks, with macros expanded',
    )
    """Logical command name for active checks, with macros expanded"""

    host_check_flapping_recovery_notification = Column(
        'host_check_flapping_recovery_notification',
        col_type='int',
        description='Whether to check to send a recovery notification when flapping stops (0/1)',
    )
    """Whether to check to send a recovery notification when flapping stops (0/1)"""

    host_check_freshness = Column(
        'host_check_freshness',
        col_type='int',
        description='Whether freshness checks are enabled (0/1)',
    )
    """Whether freshness checks are enabled (0/1)"""

    host_check_interval = Column(
        'host_check_interval',
        col_type='float',
        description='Number of basic interval lengths between two scheduled checks',
    )
    """Number of basic interval lengths between two scheduled checks"""

    host_check_options = Column(
        'host_check_options',
        col_type='int',
        description='The current check option, forced, normal, freshness (0-2)',
    )
    """The current check option, forced, normal, freshness (0-2)"""

    host_check_period = Column(
        'host_check_period',
        col_type='string',
        description='Time period in which this object will be checked. If empty then the check will always be executed.',
    )
    """Time period in which this object will be checked. If empty then the check will always be executed."""

    host_check_type = Column(
        'host_check_type',
        col_type='int',
        description='Type of check (0: active, 1: passive)',
    )
    """Type of check (0: active, 1: passive)"""

    host_checks_enabled = Column(
        'host_checks_enabled',
        col_type='int',
        description='Whether checks of the object are enabled (0/1)',
    )
    """Whether checks of the object are enabled (0/1)"""

    host_childs = Column(
        'host_childs',
        col_type='list',
        description='A list of all direct children of the host',
    )
    """A list of all direct children of the host"""

    host_comments = Column(
        'host_comments',
        col_type='list',
        description='A list of the ids of all comments',
    )
    """A list of the ids of all comments"""

    host_comments_with_extra_info = Column(
        'host_comments_with_extra_info',
        col_type='list',
        description='A list of all comments with id, author, comment, entry type and entry time',
    )
    """A list of all comments with id, author, comment, entry type and entry time"""

    host_comments_with_info = Column(
        'host_comments_with_info',
        col_type='list',
        description='A list of all comments with id, author and comment',
    )
    """A list of all comments with id, author and comment"""

    host_contact_groups = Column(
        'host_contact_groups',
        col_type='list',
        description='A list of all contact groups this object is in',
    )
    """A list of all contact groups this object is in"""

    host_contacts = Column(
        'host_contacts',
        col_type='list',
        description='A list of all contacts of this object',
    )
    """A list of all contacts of this object"""

    host_current_attempt = Column(
        'host_current_attempt',
        col_type='int',
        description='Number of the current check attempts',
    )
    """Number of the current check attempts"""

    host_current_notification_number = Column(
        'host_current_notification_number',
        col_type='int',
        description='Number of the current notification',
    )
    """Number of the current notification"""

    host_custom_variable_names = Column(
        'host_custom_variable_names',
        col_type='list',
        description='A list of the names of the custom variables',
    )
    """A list of the names of the custom variables"""

    host_custom_variable_values = Column(
        'host_custom_variable_values',
        col_type='list',
        description='A list of the values of the custom variables',
    )
    """A list of the values of the custom variables"""

    host_custom_variables = Column(
        'host_custom_variables',
        col_type='dict',
        description='A dictionary of the custom variables',
    )
    """A dictionary of the custom variables"""

    host_display_name = Column(
        'host_display_name',
        col_type='string',
        description='Optional display name',
    )
    """Optional display name"""

    host_downtimes = Column(
        'host_downtimes',
        col_type='list',
        description='A list of the ids of all scheduled downtimes of this object',
    )
    """A list of the ids of all scheduled downtimes of this object"""

    host_downtimes_with_extra_info = Column(
        'host_downtimes_with_extra_info',
        col_type='list',
        description='A list of the scheduled downtimes with id, author, comment, origin, entry_time, start_time, end_time, fixed, duration, recurring and is_pending',
    )
    """A list of the scheduled downtimes with id, author, comment, origin, entry_time, start_time, end_time, fixed, duration, recurring and is_pending"""

    host_downtimes_with_info = Column(
        'host_downtimes_with_info',
        col_type='list',
        description='A list of the scheduled downtimes with id, author and comment',
    )
    """A list of the scheduled downtimes with id, author and comment"""

    host_event_handler = Column(
        'host_event_handler',
        col_type='string',
        description='Command used as event handler',
    )
    """Command used as event handler"""

    host_event_handler_enabled = Column(
        'host_event_handler_enabled',
        col_type='int',
        description='Whether event handling is enabled (0/1)',
    )
    """Whether event handling is enabled (0/1)"""

    host_execution_time = Column(
        'host_execution_time',
        col_type='float',
        description='Time the check needed for execution',
    )
    """Time the check needed for execution"""

    host_filename = Column(
        'host_filename',
        col_type='string',
        description='The value of the custom variable FILENAME',
    )
    """The value of the custom variable FILENAME"""

    host_first_notification_delay = Column(
        'host_first_notification_delay',
        col_type='float',
        description='Delay before the first notification',
    )
    """Delay before the first notification"""

    host_flap_detection_enabled = Column(
        'host_flap_detection_enabled',
        col_type='int',
        description='Whether flap detection is enabled (0/1)',
    )
    """Whether flap detection is enabled (0/1)"""

    host_flappiness = Column(
        'host_flappiness',
        col_type='float',
        description='The current level of flappiness, this corresponds with the recent frequency of state changes',
    )
    """The current level of flappiness, this corresponds with the recent frequency of state changes"""

    host_groups = Column(
        'host_groups',
        col_type='list',
        description='A list of all host groups this object is in',
    )
    """A list of all host groups this object is in"""

    host_hard_state = Column(
        'host_hard_state',
        col_type='int',
        description='The effective hard state of this object',
    )
    """The effective hard state of this object"""

    host_has_been_checked = Column(
        'host_has_been_checked',
        col_type='int',
        description='Whether a check has already been executed (0/1)',
    )
    """Whether a check has already been executed (0/1)"""

    host_high_flap_threshold = Column(
        'host_high_flap_threshold',
        col_type='float',
        description='High threshold of flap detection',
    )
    """High threshold of flap detection"""

    host_icon_image = Column(
        'host_icon_image',
        col_type='string',
        description='The name of an image file to be used in the web pages',
    )
    """The name of an image file to be used in the web pages"""

    host_icon_image_alt = Column(
        'host_icon_image_alt',
        col_type='string',
        description='Alternative text for the icon_image',
    )
    """Alternative text for the icon_image"""

    host_icon_image_expanded = Column(
        'host_icon_image_expanded',
        col_type='string',
        description='The same as icon_image, but with the most important macros expanded',
    )
    """The same as icon_image, but with the most important macros expanded"""

    host_in_check_period = Column(
        'host_in_check_period',
        col_type='int',
        description='Whether this object is currently in its check period (0/1)',
    )
    """Whether this object is currently in its check period (0/1)"""

    host_in_notification_period = Column(
        'host_in_notification_period',
        col_type='int',
        description='Whether this object is currently in its notification period (0/1)',
    )
    """Whether this object is currently in its notification period (0/1)"""

    host_in_service_period = Column(
        'host_in_service_period',
        col_type='int',
        description='Whether this object is currently in its service period (0/1)',
    )
    """Whether this object is currently in its service period (0/1)"""

    host_initial_state = Column(
        'host_initial_state',
        col_type='int',
        description='Initial state',
    )
    """Initial state"""

    host_is_executing = Column(
        'host_is_executing',
        col_type='int',
        description='is there a check currently running (0/1)',
    )
    """is there a check currently running (0/1)"""

    host_is_flapping = Column(
        'host_is_flapping',
        col_type='int',
        description='Whether the state is flapping (0/1)',
    )
    """Whether the state is flapping (0/1)"""

    host_label_names = Column(
        'host_label_names',
        col_type='list',
        description='A list of the names of the labels',
    )
    """A list of the names of the labels"""

    host_label_source_names = Column(
        'host_label_source_names',
        col_type='list',
        description='A list of the names of the label sources',
    )
    """A list of the names of the label sources"""

    host_label_source_values = Column(
        'host_label_source_values',
        col_type='list',
        description='A list of the values of the label sources',
    )
    """A list of the values of the label sources"""

    host_label_sources = Column(
        'host_label_sources',
        col_type='dict',
        description='A dictionary of the label sources',
    )
    """A dictionary of the label sources"""

    host_label_values = Column(
        'host_label_values',
        col_type='list',
        description='A list of the values of the labels',
    )
    """A list of the values of the labels"""

    host_labels = Column(
        'host_labels',
        col_type='dict',
        description='A dictionary of the labels',
    )
    """A dictionary of the labels"""

    host_last_check = Column(
        'host_last_check',
        col_type='time',
        description='Time of the last check (Unix timestamp)',
    )
    """Time of the last check (Unix timestamp)"""

    host_last_hard_state = Column(
        'host_last_hard_state',
        col_type='int',
        description='Last hard state',
    )
    """Last hard state"""

    host_last_hard_state_change = Column(
        'host_last_hard_state_change',
        col_type='time',
        description='Time of the last hard state change - soft or hard (Unix timestamp)',
    )
    """Time of the last hard state change - soft or hard (Unix timestamp)"""

    host_last_notification = Column(
        'host_last_notification',
        col_type='time',
        description='Time of the last notification (Unix timestamp)',
    )
    """Time of the last notification (Unix timestamp)"""

    host_last_state = Column(
        'host_last_state',
        col_type='int',
        description='State before last state change',
    )
    """State before last state change"""

    host_last_state_change = Column(
        'host_last_state_change',
        col_type='time',
        description='Time of the last state change - soft or hard (Unix timestamp)',
    )
    """Time of the last state change - soft or hard (Unix timestamp)"""

    host_last_time_down = Column(
        'host_last_time_down',
        col_type='time',
        description='The last time the host was DOWN (Unix timestamp)',
    )
    """The last time the host was DOWN (Unix timestamp)"""

    host_last_time_unreachable = Column(
        'host_last_time_unreachable',
        col_type='time',
        description='The last time the host was UNREACHABLE (Unix timestamp)',
    )
    """The last time the host was UNREACHABLE (Unix timestamp)"""

    host_last_time_up = Column(
        'host_last_time_up',
        col_type='time',
        description='The last time the host was UP (Unix timestamp)',
    )
    """The last time the host was UP (Unix timestamp)"""

    host_latency = Column(
        'host_latency',
        col_type='float',
        description='Time difference between scheduled check time and actual check time',
    )
    """Time difference between scheduled check time and actual check time"""

    host_long_plugin_output = Column(
        'host_long_plugin_output',
        col_type='string',
        description='Long (extra) output of the last check',
    )
    """Long (extra) output of the last check"""

    host_low_flap_threshold = Column(
        'host_low_flap_threshold',
        col_type='float',
        description='Low threshold of flap detection',
    )
    """Low threshold of flap detection"""

    host_max_check_attempts = Column(
        'host_max_check_attempts',
        col_type='int',
        description='Maximum attempts for active checks before a hard state',
    )
    """Maximum attempts for active checks before a hard state"""

    host_metrics = Column(
        'host_metrics',
        col_type='list',
        description='A list of all metrics of this object that historically existed',
    )
    """A list of all metrics of this object that historically existed"""

    host_mk_inventory = Column(
        'host_mk_inventory',
        col_type='blob',
        description='The file content of the Check_MK HW/SW-Inventory',
    )
    """The file content of the Check_MK HW/SW-Inventory"""

    host_mk_inventory_gz = Column(
        'host_mk_inventory_gz',
        col_type='blob',
        description='The gzipped file content of the Check_MK HW/SW-Inventory',
    )
    """The gzipped file content of the Check_MK HW/SW-Inventory"""

    host_mk_inventory_last = Column(
        'host_mk_inventory_last',
        col_type='time',
        description='The timestamp of the last Check_MK HW/SW-Inventory for this host. 0 means that no inventory data is present',
    )
    """The timestamp of the last Check_MK HW/SW-Inventory for this host. 0 means that no inventory data is present"""

    host_mk_logwatch_files = Column(
        'host_mk_logwatch_files',
        col_type='list',
        description='This list of logfiles with problems fetched via mk_logwatch',
    )
    """This list of logfiles with problems fetched via mk_logwatch"""

    host_modified_attributes = Column(
        'host_modified_attributes',
        col_type='int',
        description='A bitmask specifying which attributes have been modified',
    )
    """A bitmask specifying which attributes have been modified"""

    host_modified_attributes_list = Column(
        'host_modified_attributes_list',
        col_type='list',
        description='A list of all modified attributes',
    )
    """A list of all modified attributes"""

    host_name = Column(
        'host_name',
        col_type='string',
        description='Host name',
    )
    """Host name"""

    host_next_check = Column(
        'host_next_check',
        col_type='time',
        description='Scheduled time for the next check (Unix timestamp)',
    )
    """Scheduled time for the next check (Unix timestamp)"""

    host_next_notification = Column(
        'host_next_notification',
        col_type='time',
        description='Time of the next notification (Unix timestamp)',
    )
    """Time of the next notification (Unix timestamp)"""

    host_no_more_notifications = Column(
        'host_no_more_notifications',
        col_type='int',
        description='Whether to stop sending notifications (0/1)',
    )
    """Whether to stop sending notifications (0/1)"""

    host_notes = Column(
        'host_notes',
        col_type='string',
        description='Optional notes for this object, with macros not expanded',
    )
    """Optional notes for this object, with macros not expanded"""

    host_notes_expanded = Column(
        'host_notes_expanded',
        col_type='string',
        description='The same as notes, but with the most important macros expanded',
    )
    """The same as notes, but with the most important macros expanded"""

    host_notes_url = Column(
        'host_notes_url',
        col_type='string',
        description='An optional URL with further information about the object',
    )
    """An optional URL with further information about the object"""

    host_notes_url_expanded = Column(
        'host_notes_url_expanded',
        col_type='string',
        description='Same es notes_url, but with the most important macros expanded',
    )
    """Same es notes_url, but with the most important macros expanded"""

    host_notification_interval = Column(
        'host_notification_interval',
        col_type='float',
        description='Interval of periodic notification in minutes or 0 if its off',
    )
    """Interval of periodic notification in minutes or 0 if its off"""

    host_notification_period = Column(
        'host_notification_period',
        col_type='string',
        description='Time period in which problems of this object will be notified. If empty then notification will be always',
    )
    """Time period in which problems of this object will be notified. If empty then notification will be always"""

    host_notification_postponement_reason = Column(
        'host_notification_postponement_reason',
        col_type='string',
        description='reason for postponing the pending notification, empty if nothing is postponed',
    )
    """reason for postponing the pending notification, empty if nothing is postponed"""

    host_notifications_enabled = Column(
        'host_notifications_enabled',
        col_type='int',
        description='Whether notifications of the host are enabled (0/1)',
    )
    """Whether notifications of the host are enabled (0/1)"""

    host_num_services = Column(
        'host_num_services',
        col_type='int',
        description='The total number of services of the host',
    )
    """The total number of services of the host"""

    host_num_services_crit = Column(
        'host_num_services_crit',
        col_type='int',
        description='The number of the host\'s services with the soft state CRIT',
    )
    """The number of the host's services with the soft state CRIT"""

    host_num_services_handled_problems = Column(
        'host_num_services_handled_problems',
        col_type='int',
        description='The number of the host\'s services which have handled problems',
    )
    """The number of the host's services which have handled problems"""

    host_num_services_hard_crit = Column(
        'host_num_services_hard_crit',
        col_type='int',
        description='The number of the host\'s services with the hard state CRIT',
    )
    """The number of the host's services with the hard state CRIT"""

    host_num_services_hard_ok = Column(
        'host_num_services_hard_ok',
        col_type='int',
        description='The number of the host\'s services with the hard state OK',
    )
    """The number of the host's services with the hard state OK"""

    host_num_services_hard_unknown = Column(
        'host_num_services_hard_unknown',
        col_type='int',
        description='The number of the host\'s services with the hard state UNKNOWN',
    )
    """The number of the host's services with the hard state UNKNOWN"""

    host_num_services_hard_warn = Column(
        'host_num_services_hard_warn',
        col_type='int',
        description='The number of the host\'s services with the hard state WARN',
    )
    """The number of the host's services with the hard state WARN"""

    host_num_services_ok = Column(
        'host_num_services_ok',
        col_type='int',
        description='The number of the host\'s services with the soft state OK',
    )
    """The number of the host's services with the soft state OK"""

    host_num_services_pending = Column(
        'host_num_services_pending',
        col_type='int',
        description='The number of the host\'s services which have not been checked yet (pending)',
    )
    """The number of the host's services which have not been checked yet (pending)"""

    host_num_services_unhandled_problems = Column(
        'host_num_services_unhandled_problems',
        col_type='int',
        description='The number of the host\'s services which have unhandled problems',
    )
    """The number of the host's services which have unhandled problems"""

    host_num_services_unknown = Column(
        'host_num_services_unknown',
        col_type='int',
        description='The number of the host\'s services with the soft state UNKNOWN',
    )
    """The number of the host's services with the soft state UNKNOWN"""

    host_num_services_warn = Column(
        'host_num_services_warn',
        col_type='int',
        description='The number of the host\'s services with the soft state WARN',
    )
    """The number of the host's services with the soft state WARN"""

    host_obsess_over_host = Column(
        'host_obsess_over_host',
        col_type='int',
        description='The current obsess_over_host setting (0/1)',
    )
    """The current obsess_over_host setting (0/1)"""

    host_parents = Column(
        'host_parents',
        col_type='list',
        description='A list of all direct parents of the host',
    )
    """A list of all direct parents of the host"""

    host_pending_flex_downtime = Column(
        'host_pending_flex_downtime',
        col_type='int',
        description='Number of pending flexible downtimes',
    )
    """Number of pending flexible downtimes"""

    host_percent_state_change = Column(
        'host_percent_state_change',
        col_type='float',
        description='Percent state change',
    )
    """Percent state change"""

    host_perf_data = Column(
        'host_perf_data',
        col_type='string',
        description='Optional performance data of the last check',
    )
    """Optional performance data of the last check"""

    host_plugin_output = Column(
        'host_plugin_output',
        col_type='string',
        description='Output of the last check',
    )
    """Output of the last check"""

    host_pnpgraph_present = Column(
        'host_pnpgraph_present',
        col_type='int',
        description='Whether there is a PNP4Nagios graph present for this object (-1/0/1)',
    )
    """Whether there is a PNP4Nagios graph present for this object (-1/0/1)"""

    host_previous_hard_state = Column(
        'host_previous_hard_state',
        col_type='int',
        description='Previous hard state (that hard state before the current/last hard state)',
    )
    """Previous hard state (that hard state before the current/last hard state)"""

    host_process_performance_data = Column(
        'host_process_performance_data',
        col_type='int',
        description='Whether processing of performance data is enabled (0/1)',
    )
    """Whether processing of performance data is enabled (0/1)"""

    host_retry_interval = Column(
        'host_retry_interval',
        col_type='float',
        description='Number of basic interval lengths between checks when retrying after a soft error',
    )
    """Number of basic interval lengths between checks when retrying after a soft error"""

    host_scheduled_downtime_depth = Column(
        'host_scheduled_downtime_depth',
        col_type='int',
        description='The number of downtimes this object is currently in',
    )
    """The number of downtimes this object is currently in"""

    host_service_period = Column(
        'host_service_period',
        col_type='string',
        description='Time period during which the object is expected to be available',
    )
    """Time period during which the object is expected to be available"""

    host_services = Column(
        'host_services',
        col_type='list',
        description='A list of all services of the host',
    )
    """A list of all services of the host"""

    host_services_with_fullstate = Column(
        'host_services_with_fullstate',
        col_type='list',
        description='A list of all services including full state information. The list of entries can grow in future versions.',
    )
    """A list of all services including full state information. The list of entries can grow in future versions."""

    host_services_with_info = Column(
        'host_services_with_info',
        col_type='list',
        description='A list of all services including detailed information about each service',
    )
    """A list of all services including detailed information about each service"""

    host_services_with_state = Column(
        'host_services_with_state',
        col_type='list',
        description='A list of all services of the host together with state and has_been_checked',
    )
    """A list of all services of the host together with state and has_been_checked"""

    host_smartping_timeout = Column(
        'host_smartping_timeout',
        col_type='int',
        description='Maximum expected time between two received packets in ms',
    )
    """Maximum expected time between two received packets in ms"""

    host_staleness = Column(
        'host_staleness',
        col_type='float',
        description='The staleness of this object',
    )
    """The staleness of this object"""

    host_state = Column(
        'host_state',
        col_type='int',
        description='The current state of the object, for hosts: 0/1/2 for UP/DOWN/UNREACH, for services: 0/1/2/3 for OK/WARN/CRIT/UNKNOWN',
    )
    """The current state of the object, for hosts: 0/1/2 for UP/DOWN/UNREACH, for services: 0/1/2/3 for OK/WARN/CRIT/UNKNOWN"""

    host_state_type = Column(
        'host_state_type',
        col_type='int',
        description='Type of the current state (0: soft, 1: hard)',
    )
    """Type of the current state (0: soft, 1: hard)"""

    host_statusmap_image = Column(
        'host_statusmap_image',
        col_type='string',
        description='The name of in image file for the status map',
    )
    """The name of in image file for the status map"""

    host_structured_status = Column(
        'host_structured_status',
        col_type='blob',
        description='The file content of the structured status of the Check_MK HW/SW-Inventory',
    )
    """The file content of the structured status of the Check_MK HW/SW-Inventory"""

    host_tag_names = Column(
        'host_tag_names',
        col_type='list',
        description='A list of the names of the tags',
    )
    """A list of the names of the tags"""

    host_tag_values = Column(
        'host_tag_values',
        col_type='list',
        description='A list of the values of the tags',
    )
    """A list of the values of the tags"""

    host_tags = Column(
        'host_tags',
        col_type='dict',
        description='A dictionary of the tags',
    )
    """A dictionary of the tags"""

    host_total_services = Column(
        'host_total_services',
        col_type='int',
        description='The total number of services of the host',
    )
    """The total number of services of the host"""

    host_worst_service_hard_state = Column(
        'host_worst_service_hard_state',
        col_type='int',
        description='The worst hard state of all of the host\'s services (OK <= WARN <= UNKNOWN <= CRIT)',
    )
    """The worst hard state of all of the host's services (OK <= WARN <= UNKNOWN <= CRIT)"""

    host_worst_service_state = Column(
        'host_worst_service_state',
        col_type='int',
        description='The worst soft state of all of the host\'s services (OK <= WARN <= UNKNOWN <= CRIT)',
    )
    """The worst soft state of all of the host's services (OK <= WARN <= UNKNOWN <= CRIT)"""

    host_x_3d = Column(
        'host_x_3d',
        col_type='float',
        description='3D-Coordinates: X',
    )
    """3D-Coordinates: X"""

    host_y_3d = Column(
        'host_y_3d',
        col_type='float',
        description='3D-Coordinates: Y',
    )
    """3D-Coordinates: Y"""

    host_z_3d = Column(
        'host_z_3d',
        col_type='float',
        description='3D-Coordinates: Z',
    )
    """3D-Coordinates: Z"""

    id = Column(
        'id',
        col_type='int',
        description='The id of the downtime',
    )
    """The id of the downtime"""

    is_pending = Column(
        'is_pending',
        col_type='int',
        description='1 if the downtime is currently pending (not active), 0 if it is active',
    )
    """1 if the downtime is currently pending (not active), 0 if it is active"""

    is_service = Column(
        'is_service',
        col_type='int',
        description='0, if this entry is for a host, 1 if it is for a service',
    )
    """0, if this entry is for a host, 1 if it is for a service"""

    origin = Column(
        'origin',
        col_type='int',
        description='A 0 if the downtime has been set by a command, a 1 if it has been configured by a rule',
    )
    """A 0 if the downtime has been set by a command, a 1 if it has been configured by a rule"""

    recurring = Column(
        'recurring',
        col_type='int',
        description='For recurring downtimes: 1: hourly, 2: daily, 3: weekly, 4: two-weekly, 5: four-weekly. Otherwise 0',
    )
    """For recurring downtimes: 1: hourly, 2: daily, 3: weekly, 4: two-weekly, 5: four-weekly. Otherwise 0"""

    service_accept_passive_checks = Column(
        'service_accept_passive_checks',
        col_type='int',
        description='Whether passive host checks are accepted (0/1)',
    )
    """Whether passive host checks are accepted (0/1)"""

    service_acknowledged = Column(
        'service_acknowledged',
        col_type='int',
        description='Whether the current problem has been acknowledged (0/1)',
    )
    """Whether the current problem has been acknowledged (0/1)"""

    service_acknowledgement_type = Column(
        'service_acknowledgement_type',
        col_type='int',
        description='Type of acknowledgement (0: none, 1: normal, 2: sticky)',
    )
    """Type of acknowledgement (0: none, 1: normal, 2: sticky)"""

    service_action_url = Column(
        'service_action_url',
        col_type='string',
        description='An optional URL to custom actions or information about this host',
    )
    """An optional URL to custom actions or information about this host"""

    service_action_url_expanded = Column(
        'service_action_url_expanded',
        col_type='string',
        description='The same as action_url, but with the most important macros expanded',
    )
    """The same as action_url, but with the most important macros expanded"""

    service_active_checks_enabled = Column(
        'service_active_checks_enabled',
        col_type='int',
        description='Whether active checks of the object are enabled (0/1)',
    )
    """Whether active checks of the object are enabled (0/1)"""

    service_cache_interval = Column(
        'service_cache_interval',
        col_type='int',
        description='For checks that base on cached agent data the interval in that this cache is recreated. 0 for other services.',
    )
    """For checks that base on cached agent data the interval in that this cache is recreated. 0 for other services."""

    service_cached_at = Column(
        'service_cached_at',
        col_type='time',
        description='For checks that base on cached agent data the time when this data was created. 0 for other services.',
    )
    """For checks that base on cached agent data the time when this data was created. 0 for other services."""

    service_check_command = Column(
        'service_check_command',
        col_type='string',
        description='Logical command name for active checks',
    )
    """Logical command name for active checks"""

    service_check_command_expanded = Column(
        'service_check_command_expanded',
        col_type='string',
        description='Logical command name for active checks, with macros expanded',
    )
    """Logical command name for active checks, with macros expanded"""

    service_check_flapping_recovery_notification = Column(
        'service_check_flapping_recovery_notification',
        col_type='int',
        description='Whether to check to send a recovery notification when flapping stops (0/1)',
    )
    """Whether to check to send a recovery notification when flapping stops (0/1)"""

    service_check_freshness = Column(
        'service_check_freshness',
        col_type='int',
        description='Whether freshness checks are enabled (0/1)',
    )
    """Whether freshness checks are enabled (0/1)"""

    service_check_interval = Column(
        'service_check_interval',
        col_type='float',
        description='Number of basic interval lengths between two scheduled checks',
    )
    """Number of basic interval lengths between two scheduled checks"""

    service_check_options = Column(
        'service_check_options',
        col_type='int',
        description='The current check option, forced, normal, freshness (0-2)',
    )
    """The current check option, forced, normal, freshness (0-2)"""

    service_check_period = Column(
        'service_check_period',
        col_type='string',
        description='Time period in which this object will be checked. If empty then the check will always be executed.',
    )
    """Time period in which this object will be checked. If empty then the check will always be executed."""

    service_check_type = Column(
        'service_check_type',
        col_type='int',
        description='Type of check (0: active, 1: passive)',
    )
    """Type of check (0: active, 1: passive)"""

    service_checks_enabled = Column(
        'service_checks_enabled',
        col_type='int',
        description='Whether checks of the object are enabled (0/1)',
    )
    """Whether checks of the object are enabled (0/1)"""

    service_comments = Column(
        'service_comments',
        col_type='list',
        description='A list of the ids of all comments',
    )
    """A list of the ids of all comments"""

    service_comments_with_extra_info = Column(
        'service_comments_with_extra_info',
        col_type='list',
        description='A list of all comments with id, author, comment, entry type and entry time',
    )
    """A list of all comments with id, author, comment, entry type and entry time"""

    service_comments_with_info = Column(
        'service_comments_with_info',
        col_type='list',
        description='A list of all comments with id, author and comment',
    )
    """A list of all comments with id, author and comment"""

    service_contact_groups = Column(
        'service_contact_groups',
        col_type='list',
        description='A list of all contact groups this object is in',
    )
    """A list of all contact groups this object is in"""

    service_contacts = Column(
        'service_contacts',
        col_type='list',
        description='A list of all contacts of this object',
    )
    """A list of all contacts of this object"""

    service_current_attempt = Column(
        'service_current_attempt',
        col_type='int',
        description='Number of the current check attempts',
    )
    """Number of the current check attempts"""

    service_current_notification_number = Column(
        'service_current_notification_number',
        col_type='int',
        description='Number of the current notification',
    )
    """Number of the current notification"""

    service_custom_variable_names = Column(
        'service_custom_variable_names',
        col_type='list',
        description='A list of the names of the custom variables',
    )
    """A list of the names of the custom variables"""

    service_custom_variable_values = Column(
        'service_custom_variable_values',
        col_type='list',
        description='A list of the values of the custom variables',
    )
    """A list of the values of the custom variables"""

    service_custom_variables = Column(
        'service_custom_variables',
        col_type='dict',
        description='A dictionary of the custom variables',
    )
    """A dictionary of the custom variables"""

    service_description = Column(
        'service_description',
        col_type='string',
        description='Service description',
    )
    """Service description"""

    service_display_name = Column(
        'service_display_name',
        col_type='string',
        description='Optional display name',
    )
    """Optional display name"""

    service_downtimes = Column(
        'service_downtimes',
        col_type='list',
        description='A list of the ids of all scheduled downtimes of this object',
    )
    """A list of the ids of all scheduled downtimes of this object"""

    service_downtimes_with_extra_info = Column(
        'service_downtimes_with_extra_info',
        col_type='list',
        description='A list of the scheduled downtimes with id, author, comment, origin, entry_time, start_time, end_time, fixed, duration, recurring and is_pending',
    )
    """A list of the scheduled downtimes with id, author, comment, origin, entry_time, start_time, end_time, fixed, duration, recurring and is_pending"""

    service_downtimes_with_info = Column(
        'service_downtimes_with_info',
        col_type='list',
        description='A list of the scheduled downtimes with id, author and comment',
    )
    """A list of the scheduled downtimes with id, author and comment"""

    service_event_handler = Column(
        'service_event_handler',
        col_type='string',
        description='Command used as event handler',
    )
    """Command used as event handler"""

    service_event_handler_enabled = Column(
        'service_event_handler_enabled',
        col_type='int',
        description='Whether event handling is enabled (0/1)',
    )
    """Whether event handling is enabled (0/1)"""

    service_execution_time = Column(
        'service_execution_time',
        col_type='float',
        description='Time the check needed for execution',
    )
    """Time the check needed for execution"""

    service_first_notification_delay = Column(
        'service_first_notification_delay',
        col_type='float',
        description='Delay before the first notification',
    )
    """Delay before the first notification"""

    service_flap_detection_enabled = Column(
        'service_flap_detection_enabled',
        col_type='int',
        description='Whether flap detection is enabled (0/1)',
    )
    """Whether flap detection is enabled (0/1)"""

    service_flappiness = Column(
        'service_flappiness',
        col_type='float',
        description='The current level of flappiness, this corresponds with the recent frequency of state changes',
    )
    """The current level of flappiness, this corresponds with the recent frequency of state changes"""

    service_groups = Column(
        'service_groups',
        col_type='list',
        description='A list of all service groups this object is in',
    )
    """A list of all service groups this object is in"""

    service_hard_state = Column(
        'service_hard_state',
        col_type='int',
        description='The effective hard state of this object',
    )
    """The effective hard state of this object"""

    service_has_been_checked = Column(
        'service_has_been_checked',
        col_type='int',
        description='Whether a check has already been executed (0/1)',
    )
    """Whether a check has already been executed (0/1)"""

    service_high_flap_threshold = Column(
        'service_high_flap_threshold',
        col_type='float',
        description='High threshold of flap detection',
    )
    """High threshold of flap detection"""

    service_icon_image = Column(
        'service_icon_image',
        col_type='string',
        description='The name of an image file to be used in the web pages',
    )
    """The name of an image file to be used in the web pages"""

    service_icon_image_alt = Column(
        'service_icon_image_alt',
        col_type='string',
        description='Alternative text for the icon_image',
    )
    """Alternative text for the icon_image"""

    service_icon_image_expanded = Column(
        'service_icon_image_expanded',
        col_type='string',
        description='The same as icon_image, but with the most important macros expanded',
    )
    """The same as icon_image, but with the most important macros expanded"""

    service_in_check_period = Column(
        'service_in_check_period',
        col_type='int',
        description='Whether this object is currently in its check period (0/1)',
    )
    """Whether this object is currently in its check period (0/1)"""

    service_in_notification_period = Column(
        'service_in_notification_period',
        col_type='int',
        description='Whether this object is currently in its notification period (0/1)',
    )
    """Whether this object is currently in its notification period (0/1)"""

    service_in_passive_check_period = Column(
        'service_in_passive_check_period',
        col_type='int',
        description='Whether this service is currently in its passive check period (0/1)',
    )
    """Whether this service is currently in its passive check period (0/1)"""

    service_in_service_period = Column(
        'service_in_service_period',
        col_type='int',
        description='Whether this object is currently in its service period (0/1)',
    )
    """Whether this object is currently in its service period (0/1)"""

    service_initial_state = Column(
        'service_initial_state',
        col_type='int',
        description='Initial state',
    )
    """Initial state"""

    service_is_executing = Column(
        'service_is_executing',
        col_type='int',
        description='is there a check currently running (0/1)',
    )
    """is there a check currently running (0/1)"""

    service_is_flapping = Column(
        'service_is_flapping',
        col_type='int',
        description='Whether the state is flapping (0/1)',
    )
    """Whether the state is flapping (0/1)"""

    service_label_names = Column(
        'service_label_names',
        col_type='list',
        description='A list of the names of the labels',
    )
    """A list of the names of the labels"""

    service_label_source_names = Column(
        'service_label_source_names',
        col_type='list',
        description='A list of the names of the label sources',
    )
    """A list of the names of the label sources"""

    service_label_source_values = Column(
        'service_label_source_values',
        col_type='list',
        description='A list of the values of the label sources',
    )
    """A list of the values of the label sources"""

    service_label_sources = Column(
        'service_label_sources',
        col_type='dict',
        description='A dictionary of the label sources',
    )
    """A dictionary of the label sources"""

    service_label_values = Column(
        'service_label_values',
        col_type='list',
        description='A list of the values of the labels',
    )
    """A list of the values of the labels"""

    service_labels = Column(
        'service_labels',
        col_type='dict',
        description='A dictionary of the labels',
    )
    """A dictionary of the labels"""

    service_last_check = Column(
        'service_last_check',
        col_type='time',
        description='Time of the last check (Unix timestamp)',
    )
    """Time of the last check (Unix timestamp)"""

    service_last_hard_state = Column(
        'service_last_hard_state',
        col_type='int',
        description='Last hard state',
    )
    """Last hard state"""

    service_last_hard_state_change = Column(
        'service_last_hard_state_change',
        col_type='time',
        description='Time of the last hard state change - soft or hard (Unix timestamp)',
    )
    """Time of the last hard state change - soft or hard (Unix timestamp)"""

    service_last_notification = Column(
        'service_last_notification',
        col_type='time',
        description='Time of the last notification (Unix timestamp)',
    )
    """Time of the last notification (Unix timestamp)"""

    service_last_state = Column(
        'service_last_state',
        col_type='int',
        description='State before last state change',
    )
    """State before last state change"""

    service_last_state_change = Column(
        'service_last_state_change',
        col_type='time',
        description='Time of the last state change - soft or hard (Unix timestamp)',
    )
    """Time of the last state change - soft or hard (Unix timestamp)"""

    service_last_time_critical = Column(
        'service_last_time_critical',
        col_type='time',
        description='The last time the service was CRIT (Unix timestamp)',
    )
    """The last time the service was CRIT (Unix timestamp)"""

    service_last_time_ok = Column(
        'service_last_time_ok',
        col_type='time',
        description='The last time the service was OK (Unix timestamp)',
    )
    """The last time the service was OK (Unix timestamp)"""

    service_last_time_unknown = Column(
        'service_last_time_unknown',
        col_type='time',
        description='The last time the service was UNKNOWN (Unix timestamp)',
    )
    """The last time the service was UNKNOWN (Unix timestamp)"""

    service_last_time_warning = Column(
        'service_last_time_warning',
        col_type='time',
        description='The last time the service was WARN (Unix timestamp)',
    )
    """The last time the service was WARN (Unix timestamp)"""

    service_latency = Column(
        'service_latency',
        col_type='float',
        description='Time difference between scheduled check time and actual check time',
    )
    """Time difference between scheduled check time and actual check time"""

    service_long_plugin_output = Column(
        'service_long_plugin_output',
        col_type='string',
        description='Long (extra) output of the last check',
    )
    """Long (extra) output of the last check"""

    service_low_flap_threshold = Column(
        'service_low_flap_threshold',
        col_type='float',
        description='Low threshold of flap detection',
    )
    """Low threshold of flap detection"""

    service_max_check_attempts = Column(
        'service_max_check_attempts',
        col_type='int',
        description='Maximum attempts for active checks before a hard state',
    )
    """Maximum attempts for active checks before a hard state"""

    service_metrics = Column(
        'service_metrics',
        col_type='list',
        description='A list of all metrics of this object that historically existed',
    )
    """A list of all metrics of this object that historically existed"""

    service_modified_attributes = Column(
        'service_modified_attributes',
        col_type='int',
        description='A bitmask specifying which attributes have been modified',
    )
    """A bitmask specifying which attributes have been modified"""

    service_modified_attributes_list = Column(
        'service_modified_attributes_list',
        col_type='list',
        description='A list of all modified attributes',
    )
    """A list of all modified attributes"""

    service_next_check = Column(
        'service_next_check',
        col_type='time',
        description='Scheduled time for the next check (Unix timestamp)',
    )
    """Scheduled time for the next check (Unix timestamp)"""

    service_next_notification = Column(
        'service_next_notification',
        col_type='time',
        description='Time of the next notification (Unix timestamp)',
    )
    """Time of the next notification (Unix timestamp)"""

    service_no_more_notifications = Column(
        'service_no_more_notifications',
        col_type='int',
        description='Whether to stop sending notifications (0/1)',
    )
    """Whether to stop sending notifications (0/1)"""

    service_notes = Column(
        'service_notes',
        col_type='string',
        description='Optional notes for this object, with macros not expanded',
    )
    """Optional notes for this object, with macros not expanded"""

    service_notes_expanded = Column(
        'service_notes_expanded',
        col_type='string',
        description='The same as notes, but with the most important macros expanded',
    )
    """The same as notes, but with the most important macros expanded"""

    service_notes_url = Column(
        'service_notes_url',
        col_type='string',
        description='An optional URL with further information about the object',
    )
    """An optional URL with further information about the object"""

    service_notes_url_expanded = Column(
        'service_notes_url_expanded',
        col_type='string',
        description='Same es notes_url, but with the most important macros expanded',
    )
    """Same es notes_url, but with the most important macros expanded"""

    service_notification_interval = Column(
        'service_notification_interval',
        col_type='float',
        description='Interval of periodic notification in minutes or 0 if its off',
    )
    """Interval of periodic notification in minutes or 0 if its off"""

    service_notification_period = Column(
        'service_notification_period',
        col_type='string',
        description='Time period in which problems of this object will be notified. If empty then notification will be always',
    )
    """Time period in which problems of this object will be notified. If empty then notification will be always"""

    service_notification_postponement_reason = Column(
        'service_notification_postponement_reason',
        col_type='string',
        description='reason for postponing the pending notification, empty if nothing is postponed',
    )
    """reason for postponing the pending notification, empty if nothing is postponed"""

    service_notifications_enabled = Column(
        'service_notifications_enabled',
        col_type='int',
        description='Whether notifications of the host are enabled (0/1)',
    )
    """Whether notifications of the host are enabled (0/1)"""

    service_obsess_over_service = Column(
        'service_obsess_over_service',
        col_type='int',
        description='The current obsess_over_service setting (0/1)',
    )
    """The current obsess_over_service setting (0/1)"""

    service_passive_check_period = Column(
        'service_passive_check_period',
        col_type='string',
        description='Time period in which this (passive) service will be checked.',
    )
    """Time period in which this (passive) service will be checked."""

    service_pending_flex_downtime = Column(
        'service_pending_flex_downtime',
        col_type='int',
        description='Number of pending flexible downtimes',
    )
    """Number of pending flexible downtimes"""

    service_percent_state_change = Column(
        'service_percent_state_change',
        col_type='float',
        description='Percent state change',
    )
    """Percent state change"""

    service_perf_data = Column(
        'service_perf_data',
        col_type='string',
        description='Optional performance data of the last check',
    )
    """Optional performance data of the last check"""

    service_plugin_output = Column(
        'service_plugin_output',
        col_type='string',
        description='Output of the last check',
    )
    """Output of the last check"""

    service_pnpgraph_present = Column(
        'service_pnpgraph_present',
        col_type='int',
        description='Whether there is a PNP4Nagios graph present for this object (-1/0/1)',
    )
    """Whether there is a PNP4Nagios graph present for this object (-1/0/1)"""

    service_previous_hard_state = Column(
        'service_previous_hard_state',
        col_type='int',
        description='Previous hard state (that hard state before the current/last hard state)',
    )
    """Previous hard state (that hard state before the current/last hard state)"""

    service_process_performance_data = Column(
        'service_process_performance_data',
        col_type='int',
        description='Whether processing of performance data is enabled (0/1)',
    )
    """Whether processing of performance data is enabled (0/1)"""

    service_retry_interval = Column(
        'service_retry_interval',
        col_type='float',
        description='Number of basic interval lengths between checks when retrying after a soft error',
    )
    """Number of basic interval lengths between checks when retrying after a soft error"""

    service_robotmk_last_error_log = Column(
        'service_robotmk_last_error_log',
        col_type='blob',
        description='The file content of the Robotmk error log',
    )
    """The file content of the Robotmk error log"""

    service_robotmk_last_error_log_gz = Column(
        'service_robotmk_last_error_log_gz',
        col_type='blob',
        description='The gzipped file content of the Robotmk error log',
    )
    """The gzipped file content of the Robotmk error log"""

    service_robotmk_last_log = Column(
        'service_robotmk_last_log',
        col_type='blob',
        description='The file content of the Robotmk log',
    )
    """The file content of the Robotmk log"""

    service_robotmk_last_log_gz = Column(
        'service_robotmk_last_log_gz',
        col_type='blob',
        description='The gzipped file content of the Robotmk log',
    )
    """The gzipped file content of the Robotmk log"""

    service_scheduled_downtime_depth = Column(
        'service_scheduled_downtime_depth',
        col_type='int',
        description='The number of downtimes this object is currently in',
    )
    """The number of downtimes this object is currently in"""

    service_service_period = Column(
        'service_service_period',
        col_type='string',
        description='Time period during which the object is expected to be available',
    )
    """Time period during which the object is expected to be available"""

    service_staleness = Column(
        'service_staleness',
        col_type='float',
        description='The staleness of this object',
    )
    """The staleness of this object"""

    service_state = Column(
        'service_state',
        col_type='int',
        description='The current state of the object, for hosts: 0/1/2 for UP/DOWN/UNREACH, for services: 0/1/2/3 for OK/WARN/CRIT/UNKNOWN',
    )
    """The current state of the object, for hosts: 0/1/2 for UP/DOWN/UNREACH, for services: 0/1/2/3 for OK/WARN/CRIT/UNKNOWN"""

    service_state_type = Column(
        'service_state_type',
        col_type='int',
        description='Type of the current state (0: soft, 1: hard)',
    )
    """Type of the current state (0: soft, 1: hard)"""

    service_tag_names = Column(
        'service_tag_names',
        col_type='list',
        description='A list of the names of the tags',
    )
    """A list of the names of the tags"""

    service_tag_values = Column(
        'service_tag_values',
        col_type='list',
        description='A list of the values of the tags',
    )
    """A list of the values of the tags"""

    service_tags = Column(
        'service_tags',
        col_type='dict',
        description='A dictionary of the tags',
    )
    """A dictionary of the tags"""

    start_time = Column(
        'start_time',
        col_type='time',
        description='The start time of the downtime as UNIX timestamp',
    )
    """The start time of the downtime as UNIX timestamp"""

    triggered_by = Column(
        'triggered_by',
        col_type='int',
        description='The id of the downtime this downtime was triggered by or 0 if it was not triggered by another downtime',
    )
    """The id of the downtime this downtime was triggered by or 0 if it was not triggered by another downtime"""

    type = Column(
        'type',
        col_type='int',
        description='The type of the downtime: 0 if it is active, 1 if it is pending',
    )
    """The type of the downtime: 0 if it is active, 1 if it is pending"""
