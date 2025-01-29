#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.utils.livestatus_helpers.types import Column, Table

# fmt: off


class Statehist(Table):
    __tablename__ = 'statehist'

    current_host_accept_passive_checks = Column(
        'current_host_accept_passive_checks',
        col_type='int',
        description='Whether passive host checks are accepted (0/1)',
    )
    """Whether passive host checks are accepted (0/1)"""

    current_host_acknowledged = Column(
        'current_host_acknowledged',
        col_type='int',
        description='Whether the current problem has been acknowledged (0/1)',
    )
    """Whether the current problem has been acknowledged (0/1)"""

    current_host_acknowledgement_type = Column(
        'current_host_acknowledgement_type',
        col_type='int',
        description='Type of acknowledgement (0: none, 1: normal, 2: sticky)',
    )
    """Type of acknowledgement (0: none, 1: normal, 2: sticky)"""

    current_host_action_url = Column(
        'current_host_action_url',
        col_type='string',
        description='An optional URL to custom actions or information about this host',
    )
    """An optional URL to custom actions or information about this host"""

    current_host_action_url_expanded = Column(
        'current_host_action_url_expanded',
        col_type='string',
        description='The same as action_url, but with the most important macros expanded',
    )
    """The same as action_url, but with the most important macros expanded"""

    current_host_active_checks_enabled = Column(
        'current_host_active_checks_enabled',
        col_type='int',
        description='Whether active checks of the object are enabled (0/1)',
    )
    """Whether active checks of the object are enabled (0/1)"""

    current_host_address = Column(
        'current_host_address',
        col_type='string',
        description='IP address',
    )
    """IP address"""

    current_host_alias = Column(
        'current_host_alias',
        col_type='string',
        description='An alias name for the host',
    )
    """An alias name for the host"""

    current_host_check_command = Column(
        'current_host_check_command',
        col_type='string',
        description='Logical command name for active checks',
    )
    """Logical command name for active checks"""

    current_host_check_command_expanded = Column(
        'current_host_check_command_expanded',
        col_type='string',
        description='Logical command name for active checks, with macros expanded',
    )
    """Logical command name for active checks, with macros expanded"""

    current_host_check_flapping_recovery_notification = Column(
        'current_host_check_flapping_recovery_notification',
        col_type='int',
        description='Whether to check to send a recovery notification when flapping stops (0/1)',
    )
    """Whether to check to send a recovery notification when flapping stops (0/1)"""

    current_host_check_freshness = Column(
        'current_host_check_freshness',
        col_type='int',
        description='Whether freshness checks are enabled (0/1)',
    )
    """Whether freshness checks are enabled (0/1)"""

    current_host_check_interval = Column(
        'current_host_check_interval',
        col_type='float',
        description='Number of basic interval lengths between two scheduled checks',
    )
    """Number of basic interval lengths between two scheduled checks"""

    current_host_check_options = Column(
        'current_host_check_options',
        col_type='int',
        description='The current check option, forced, normal, freshness (0-2)',
    )
    """The current check option, forced, normal, freshness (0-2)"""

    current_host_check_period = Column(
        'current_host_check_period',
        col_type='string',
        description='Time period in which this object will be checked. If empty then the check will always be executed.',
    )
    """Time period in which this object will be checked. If empty then the check will always be executed."""

    current_host_check_type = Column(
        'current_host_check_type',
        col_type='int',
        description='Type of check (0: active, 1: passive)',
    )
    """Type of check (0: active, 1: passive)"""

    current_host_checks_enabled = Column(
        'current_host_checks_enabled',
        col_type='int',
        description='Whether checks of the object are enabled (0/1)',
    )
    """Whether checks of the object are enabled (0/1)"""

    current_host_childs = Column(
        'current_host_childs',
        col_type='list',
        description='A list of all direct children of the host',
    )
    """A list of all direct children of the host"""

    current_host_comments = Column(
        'current_host_comments',
        col_type='list',
        description='A list of the ids of all comments',
    )
    """A list of the ids of all comments"""

    current_host_comments_with_extra_info = Column(
        'current_host_comments_with_extra_info',
        col_type='list',
        description='A list of all comments with id, author, comment, entry type and entry time',
    )
    """A list of all comments with id, author, comment, entry type and entry time"""

    current_host_comments_with_info = Column(
        'current_host_comments_with_info',
        col_type='list',
        description='A list of all comments with id, author and comment',
    )
    """A list of all comments with id, author and comment"""

    current_host_contact_groups = Column(
        'current_host_contact_groups',
        col_type='list',
        description='A list of all contact groups this object is in',
    )
    """A list of all contact groups this object is in"""

    current_host_contacts = Column(
        'current_host_contacts',
        col_type='list',
        description='A list of all contacts of this object',
    )
    """A list of all contacts of this object"""

    current_host_current_attempt = Column(
        'current_host_current_attempt',
        col_type='int',
        description='Number of the current check attempts',
    )
    """Number of the current check attempts"""

    current_host_current_notification_number = Column(
        'current_host_current_notification_number',
        col_type='int',
        description='Number of the current notification',
    )
    """Number of the current notification"""

    current_host_custom_variable_names = Column(
        'current_host_custom_variable_names',
        col_type='list',
        description='A list of the names of the custom variables',
    )
    """A list of the names of the custom variables"""

    current_host_custom_variable_values = Column(
        'current_host_custom_variable_values',
        col_type='list',
        description='A list of the values of the custom variables',
    )
    """A list of the values of the custom variables"""

    current_host_custom_variables = Column(
        'current_host_custom_variables',
        col_type='dict',
        description='A dictionary of the custom variables',
    )
    """A dictionary of the custom variables"""

    current_host_display_name = Column(
        'current_host_display_name',
        col_type='string',
        description='Optional display name',
    )
    """Optional display name"""

    current_host_downtimes = Column(
        'current_host_downtimes',
        col_type='list',
        description='A list of the ids of all scheduled downtimes of this object',
    )
    """A list of the ids of all scheduled downtimes of this object"""

    current_host_downtimes_with_extra_info = Column(
        'current_host_downtimes_with_extra_info',
        col_type='list',
        description='A list of the scheduled downtimes with id, author, comment, origin, entry_time, start_time, end_time, fixed, duration, recurring and is_pending',
    )
    """A list of the scheduled downtimes with id, author, comment, origin, entry_time, start_time, end_time, fixed, duration, recurring and is_pending"""

    current_host_downtimes_with_info = Column(
        'current_host_downtimes_with_info',
        col_type='list',
        description='A list of the scheduled downtimes with id, author and comment',
    )
    """A list of the scheduled downtimes with id, author and comment"""

    current_host_event_handler = Column(
        'current_host_event_handler',
        col_type='string',
        description='Command used as event handler',
    )
    """Command used as event handler"""

    current_host_event_handler_enabled = Column(
        'current_host_event_handler_enabled',
        col_type='int',
        description='Whether event handling is enabled (0/1)',
    )
    """Whether event handling is enabled (0/1)"""

    current_host_execution_time = Column(
        'current_host_execution_time',
        col_type='float',
        description='Time the check needed for execution',
    )
    """Time the check needed for execution"""

    current_host_filename = Column(
        'current_host_filename',
        col_type='string',
        description='The value of the custom variable FILENAME',
    )
    """The value of the custom variable FILENAME"""

    current_host_first_notification_delay = Column(
        'current_host_first_notification_delay',
        col_type='float',
        description='Delay before the first notification',
    )
    """Delay before the first notification"""

    current_host_flap_detection_enabled = Column(
        'current_host_flap_detection_enabled',
        col_type='int',
        description='Whether flap detection is enabled (0/1)',
    )
    """Whether flap detection is enabled (0/1)"""

    current_host_flappiness = Column(
        'current_host_flappiness',
        col_type='float',
        description='The current level of flappiness, this corresponds with the recent frequency of state changes',
    )
    """The current level of flappiness, this corresponds with the recent frequency of state changes"""

    current_host_groups = Column(
        'current_host_groups',
        col_type='list',
        description='A list of all host groups this object is in',
    )
    """A list of all host groups this object is in"""

    current_host_hard_state = Column(
        'current_host_hard_state',
        col_type='int',
        description='The effective hard state of this object',
    )
    """The effective hard state of this object"""

    current_host_has_been_checked = Column(
        'current_host_has_been_checked',
        col_type='int',
        description='Whether a check has already been executed (0/1)',
    )
    """Whether a check has already been executed (0/1)"""

    current_host_high_flap_threshold = Column(
        'current_host_high_flap_threshold',
        col_type='float',
        description='High threshold of flap detection',
    )
    """High threshold of flap detection"""

    current_host_icon_image = Column(
        'current_host_icon_image',
        col_type='string',
        description='The name of an image file to be used in the web pages',
    )
    """The name of an image file to be used in the web pages"""

    current_host_icon_image_alt = Column(
        'current_host_icon_image_alt',
        col_type='string',
        description='Alternative text for the icon_image',
    )
    """Alternative text for the icon_image"""

    current_host_icon_image_expanded = Column(
        'current_host_icon_image_expanded',
        col_type='string',
        description='The same as icon_image, but with the most important macros expanded',
    )
    """The same as icon_image, but with the most important macros expanded"""

    current_host_in_check_period = Column(
        'current_host_in_check_period',
        col_type='int',
        description='Whether this object is currently in its check period (0/1)',
    )
    """Whether this object is currently in its check period (0/1)"""

    current_host_in_notification_period = Column(
        'current_host_in_notification_period',
        col_type='int',
        description='Whether this object is currently in its notification period (0/1)',
    )
    """Whether this object is currently in its notification period (0/1)"""

    current_host_in_service_period = Column(
        'current_host_in_service_period',
        col_type='int',
        description='Whether this object is currently in its service period (0/1)',
    )
    """Whether this object is currently in its service period (0/1)"""

    current_host_initial_state = Column(
        'current_host_initial_state',
        col_type='int',
        description='Initial state',
    )
    """Initial state"""

    current_host_is_executing = Column(
        'current_host_is_executing',
        col_type='int',
        description='is there a check currently running (0/1)',
    )
    """is there a check currently running (0/1)"""

    current_host_is_flapping = Column(
        'current_host_is_flapping',
        col_type='int',
        description='Whether the state is flapping (0/1)',
    )
    """Whether the state is flapping (0/1)"""

    current_host_label_names = Column(
        'current_host_label_names',
        col_type='list',
        description='A list of the names of the labels',
    )
    """A list of the names of the labels"""

    current_host_label_source_names = Column(
        'current_host_label_source_names',
        col_type='list',
        description='A list of the names of the label sources',
    )
    """A list of the names of the label sources"""

    current_host_label_source_values = Column(
        'current_host_label_source_values',
        col_type='list',
        description='A list of the values of the label sources',
    )
    """A list of the values of the label sources"""

    current_host_label_sources = Column(
        'current_host_label_sources',
        col_type='dict',
        description='A dictionary of the label sources',
    )
    """A dictionary of the label sources"""

    current_host_label_values = Column(
        'current_host_label_values',
        col_type='list',
        description='A list of the values of the labels',
    )
    """A list of the values of the labels"""

    current_host_labels = Column(
        'current_host_labels',
        col_type='dict',
        description='A dictionary of the labels',
    )
    """A dictionary of the labels"""

    current_host_last_check = Column(
        'current_host_last_check',
        col_type='time',
        description='Time of the last check (Unix timestamp)',
    )
    """Time of the last check (Unix timestamp)"""

    current_host_last_hard_state = Column(
        'current_host_last_hard_state',
        col_type='int',
        description='Last hard state',
    )
    """Last hard state"""

    current_host_last_hard_state_change = Column(
        'current_host_last_hard_state_change',
        col_type='time',
        description='Time of the last hard state change - soft or hard (Unix timestamp)',
    )
    """Time of the last hard state change - soft or hard (Unix timestamp)"""

    current_host_last_notification = Column(
        'current_host_last_notification',
        col_type='time',
        description='Time of the last notification (Unix timestamp)',
    )
    """Time of the last notification (Unix timestamp)"""

    current_host_last_state = Column(
        'current_host_last_state',
        col_type='int',
        description='State before last state change',
    )
    """State before last state change"""

    current_host_last_state_change = Column(
        'current_host_last_state_change',
        col_type='time',
        description='Time of the last state change - soft or hard (Unix timestamp)',
    )
    """Time of the last state change - soft or hard (Unix timestamp)"""

    current_host_last_time_down = Column(
        'current_host_last_time_down',
        col_type='time',
        description='Last time the host was DOWN (Unix timestamp)',
    )
    """Last time the host was DOWN (Unix timestamp)"""

    current_host_last_time_unreachable = Column(
        'current_host_last_time_unreachable',
        col_type='time',
        description='Last time the host was UNREACHABLE (Unix timestamp)',
    )
    """Last time the host was UNREACHABLE (Unix timestamp)"""

    current_host_last_time_up = Column(
        'current_host_last_time_up',
        col_type='time',
        description='Last time the host was UP (Unix timestamp)',
    )
    """Last time the host was UP (Unix timestamp)"""

    current_host_latency = Column(
        'current_host_latency',
        col_type='float',
        description='Time difference between scheduled check time and actual check time',
    )
    """Time difference between scheduled check time and actual check time"""

    current_host_long_plugin_output = Column(
        'current_host_long_plugin_output',
        col_type='string',
        description='Long (extra) output of the last check',
    )
    """Long (extra) output of the last check"""

    current_host_low_flap_threshold = Column(
        'current_host_low_flap_threshold',
        col_type='float',
        description='Low threshold of flap detection',
    )
    """Low threshold of flap detection"""

    current_host_max_check_attempts = Column(
        'current_host_max_check_attempts',
        col_type='int',
        description='Maximum attempts for active checks before a hard state',
    )
    """Maximum attempts for active checks before a hard state"""

    current_host_metrics = Column(
        'current_host_metrics',
        col_type='list',
        description='A list of all metrics of this object that historically existed',
    )
    """A list of all metrics of this object that historically existed"""

    current_host_mk_inventory = Column(
        'current_host_mk_inventory',
        col_type='blob',
        description='The file content of the Check_MK HW/SW Inventory',
    )
    """The file content of the Check_MK HW/SW Inventory"""

    current_host_mk_inventory_gz = Column(
        'current_host_mk_inventory_gz',
        col_type='blob',
        description='The gzipped file content of the Check_MK HW/SW Inventory',
    )
    """The gzipped file content of the Check_MK HW/SW Inventory"""

    current_host_mk_inventory_last = Column(
        'current_host_mk_inventory_last',
        col_type='time',
        description='The timestamp of the last Check_MK HW/SW Inventory for this host. 0 means that no inventory data is present',
    )
    """The timestamp of the last Check_MK HW/SW Inventory for this host. 0 means that no inventory data is present"""

    current_host_mk_logwatch_files = Column(
        'current_host_mk_logwatch_files',
        col_type='list',
        description='This list of logfiles with problems fetched via mk_logwatch',
    )
    """This list of logfiles with problems fetched via mk_logwatch"""

    current_host_modified_attributes = Column(
        'current_host_modified_attributes',
        col_type='int',
        description='A bitmask specifying which attributes have been modified',
    )
    """A bitmask specifying which attributes have been modified"""

    current_host_modified_attributes_list = Column(
        'current_host_modified_attributes_list',
        col_type='list',
        description='A list of all modified attributes',
    )
    """A list of all modified attributes"""

    current_host_name = Column(
        'current_host_name',
        col_type='string',
        description='Host name',
    )
    """Host name"""

    current_host_next_check = Column(
        'current_host_next_check',
        col_type='time',
        description='Scheduled time for the next check (Unix timestamp)',
    )
    """Scheduled time for the next check (Unix timestamp)"""

    current_host_next_notification = Column(
        'current_host_next_notification',
        col_type='time',
        description='Time of the next notification (Unix timestamp)',
    )
    """Time of the next notification (Unix timestamp)"""

    current_host_no_more_notifications = Column(
        'current_host_no_more_notifications',
        col_type='int',
        description='Whether to stop sending notifications (0/1)',
    )
    """Whether to stop sending notifications (0/1)"""

    current_host_notes = Column(
        'current_host_notes',
        col_type='string',
        description='Optional notes for this object, with macros not expanded',
    )
    """Optional notes for this object, with macros not expanded"""

    current_host_notes_expanded = Column(
        'current_host_notes_expanded',
        col_type='string',
        description='The same as notes, but with the most important macros expanded',
    )
    """The same as notes, but with the most important macros expanded"""

    current_host_notes_url = Column(
        'current_host_notes_url',
        col_type='string',
        description='An optional URL with further information about the object',
    )
    """An optional URL with further information about the object"""

    current_host_notes_url_expanded = Column(
        'current_host_notes_url_expanded',
        col_type='string',
        description='Same es notes_url, but with the most important macros expanded',
    )
    """Same es notes_url, but with the most important macros expanded"""

    current_host_notification_interval = Column(
        'current_host_notification_interval',
        col_type='float',
        description='Interval of periodic notification in minutes or 0 if its off',
    )
    """Interval of periodic notification in minutes or 0 if its off"""

    current_host_notification_period = Column(
        'current_host_notification_period',
        col_type='string',
        description='Time period in which problems of this object will be notified. If empty then notification will be always',
    )
    """Time period in which problems of this object will be notified. If empty then notification will be always"""

    current_host_notification_postponement_reason = Column(
        'current_host_notification_postponement_reason',
        col_type='string',
        description='reason for postponing the pending notification, empty if nothing is postponed',
    )
    """reason for postponing the pending notification, empty if nothing is postponed"""

    current_host_notifications_enabled = Column(
        'current_host_notifications_enabled',
        col_type='int',
        description='Whether notifications of the host are enabled (0/1)',
    )
    """Whether notifications of the host are enabled (0/1)"""

    current_host_num_services = Column(
        'current_host_num_services',
        col_type='int',
        description='The total number of services of the host',
    )
    """The total number of services of the host"""

    current_host_num_services_crit = Column(
        'current_host_num_services_crit',
        col_type='int',
        description='The number of the host\'s services with the soft state CRIT',
    )
    """The number of the host's services with the soft state CRIT"""

    current_host_num_services_handled_problems = Column(
        'current_host_num_services_handled_problems',
        col_type='int',
        description='The number of the host\'s services which have handled problems',
    )
    """The number of the host's services which have handled problems"""

    current_host_num_services_hard_crit = Column(
        'current_host_num_services_hard_crit',
        col_type='int',
        description='The number of the host\'s services with the hard state CRIT',
    )
    """The number of the host's services with the hard state CRIT"""

    current_host_num_services_hard_ok = Column(
        'current_host_num_services_hard_ok',
        col_type='int',
        description='The number of the host\'s services with the hard state OK',
    )
    """The number of the host's services with the hard state OK"""

    current_host_num_services_hard_unknown = Column(
        'current_host_num_services_hard_unknown',
        col_type='int',
        description='The number of the host\'s services with the hard state UNKNOWN',
    )
    """The number of the host's services with the hard state UNKNOWN"""

    current_host_num_services_hard_warn = Column(
        'current_host_num_services_hard_warn',
        col_type='int',
        description='The number of the host\'s services with the hard state WARN',
    )
    """The number of the host's services with the hard state WARN"""

    current_host_num_services_ok = Column(
        'current_host_num_services_ok',
        col_type='int',
        description='The number of the host\'s services with the soft state OK',
    )
    """The number of the host's services with the soft state OK"""

    current_host_num_services_pending = Column(
        'current_host_num_services_pending',
        col_type='int',
        description='The number of the host\'s services which have not been checked yet (pending)',
    )
    """The number of the host's services which have not been checked yet (pending)"""

    current_host_num_services_unhandled_problems = Column(
        'current_host_num_services_unhandled_problems',
        col_type='int',
        description='The number of the host\'s services which have unhandled problems',
    )
    """The number of the host's services which have unhandled problems"""

    current_host_num_services_unknown = Column(
        'current_host_num_services_unknown',
        col_type='int',
        description='The number of the host\'s services with the soft state UNKNOWN',
    )
    """The number of the host's services with the soft state UNKNOWN"""

    current_host_num_services_warn = Column(
        'current_host_num_services_warn',
        col_type='int',
        description='The number of the host\'s services with the soft state WARN',
    )
    """The number of the host's services with the soft state WARN"""

    current_host_obsess_over_host = Column(
        'current_host_obsess_over_host',
        col_type='int',
        description='The current obsess_over_host setting (0/1)',
    )
    """The current obsess_over_host setting (0/1)"""

    current_host_parents = Column(
        'current_host_parents',
        col_type='list',
        description='A list of all direct parents of the host',
    )
    """A list of all direct parents of the host"""

    current_host_pending_flex_downtime = Column(
        'current_host_pending_flex_downtime',
        col_type='int',
        description='Number of pending flexible downtimes',
    )
    """Number of pending flexible downtimes"""

    current_host_percent_state_change = Column(
        'current_host_percent_state_change',
        col_type='float',
        description='Percent state change',
    )
    """Percent state change"""

    current_host_perf_data = Column(
        'current_host_perf_data',
        col_type='string',
        description='Optional performance data of the last check',
    )
    """Optional performance data of the last check"""

    current_host_performance_data = Column(
        'current_host_performance_data',
        col_type='dictdouble',
        description='Optional performance data as a dict',
    )
    """Optional performance data as a dict"""

    current_host_plugin_output = Column(
        'current_host_plugin_output',
        col_type='string',
        description='Output of the last check',
    )
    """Output of the last check"""

    current_host_pnpgraph_present = Column(
        'current_host_pnpgraph_present',
        col_type='int',
        description='Whether there is a PNP4Nagios graph present for this object (-1/0/1)',
    )
    """Whether there is a PNP4Nagios graph present for this object (-1/0/1)"""

    current_host_previous_hard_state = Column(
        'current_host_previous_hard_state',
        col_type='int',
        description='Previous hard state (that hard state before the current/last hard state)',
    )
    """Previous hard state (that hard state before the current/last hard state)"""

    current_host_process_performance_data = Column(
        'current_host_process_performance_data',
        col_type='int',
        description='Whether processing of performance data is enabled (0/1)',
    )
    """Whether processing of performance data is enabled (0/1)"""

    current_host_retry_interval = Column(
        'current_host_retry_interval',
        col_type='float',
        description='Number of basic interval lengths between checks when retrying after a soft error',
    )
    """Number of basic interval lengths between checks when retrying after a soft error"""

    current_host_scheduled_downtime_depth = Column(
        'current_host_scheduled_downtime_depth',
        col_type='int',
        description='The number of downtimes this object is currently in',
    )
    """The number of downtimes this object is currently in"""

    current_host_service_period = Column(
        'current_host_service_period',
        col_type='string',
        description='Time period during which the object is expected to be available',
    )
    """Time period during which the object is expected to be available"""

    current_host_services = Column(
        'current_host_services',
        col_type='list',
        description='A list of all services of the host',
    )
    """A list of all services of the host"""

    current_host_services_with_fullstate = Column(
        'current_host_services_with_fullstate',
        col_type='list',
        description='A list of all services including full state information. The list of entries can grow in future versions.',
    )
    """A list of all services including full state information. The list of entries can grow in future versions."""

    current_host_services_with_info = Column(
        'current_host_services_with_info',
        col_type='list',
        description='A list of all services including detailed information about each service',
    )
    """A list of all services including detailed information about each service"""

    current_host_services_with_state = Column(
        'current_host_services_with_state',
        col_type='list',
        description='A list of all services of the host together with state and has_been_checked',
    )
    """A list of all services of the host together with state and has_been_checked"""

    current_host_smartping_timeout = Column(
        'current_host_smartping_timeout',
        col_type='int',
        description='Maximum expected time between two received packets in ms',
    )
    """Maximum expected time between two received packets in ms"""

    current_host_staleness = Column(
        'current_host_staleness',
        col_type='float',
        description='The staleness of this object',
    )
    """The staleness of this object"""

    current_host_state = Column(
        'current_host_state',
        col_type='int',
        description='The current state of the object, for hosts: 0/1/2 for UP/DOWN/UNREACH, for services: 0/1/2/3 for OK/WARN/CRIT/UNKNOWN',
    )
    """The current state of the object, for hosts: 0/1/2 for UP/DOWN/UNREACH, for services: 0/1/2/3 for OK/WARN/CRIT/UNKNOWN"""

    current_host_state_type = Column(
        'current_host_state_type',
        col_type='int',
        description='Type of the current state (0: soft, 1: hard)',
    )
    """Type of the current state (0: soft, 1: hard)"""

    current_host_statusmap_image = Column(
        'current_host_statusmap_image',
        col_type='string',
        description='The name of in image file for the status map',
    )
    """The name of in image file for the status map"""

    current_host_structured_status = Column(
        'current_host_structured_status',
        col_type='blob',
        description='The file content of the structured status of the Check_MK HW/SW Inventory',
    )
    """The file content of the structured status of the Check_MK HW/SW Inventory"""

    current_host_tag_names = Column(
        'current_host_tag_names',
        col_type='list',
        description='A list of the names of the tags',
    )
    """A list of the names of the tags"""

    current_host_tag_values = Column(
        'current_host_tag_values',
        col_type='list',
        description='A list of the values of the tags',
    )
    """A list of the values of the tags"""

    current_host_tags = Column(
        'current_host_tags',
        col_type='dict',
        description='A dictionary of the tags',
    )
    """A dictionary of the tags"""

    current_host_total_services = Column(
        'current_host_total_services',
        col_type='int',
        description='The total number of services of the host',
    )
    """The total number of services of the host"""

    current_host_worst_service_hard_state = Column(
        'current_host_worst_service_hard_state',
        col_type='int',
        description='The worst hard state of all of the host\'s services (OK <= WARN <= UNKNOWN <= CRIT)',
    )
    """The worst hard state of all of the host's services (OK <= WARN <= UNKNOWN <= CRIT)"""

    current_host_worst_service_state = Column(
        'current_host_worst_service_state',
        col_type='int',
        description='The worst soft state of all of the host\'s services (OK <= WARN <= UNKNOWN <= CRIT)',
    )
    """The worst soft state of all of the host's services (OK <= WARN <= UNKNOWN <= CRIT)"""

    current_host_x_3d = Column(
        'current_host_x_3d',
        col_type='float',
        description='3D-Coordinates: X',
    )
    """3D-Coordinates: X"""

    current_host_y_3d = Column(
        'current_host_y_3d',
        col_type='float',
        description='3D-Coordinates: Y',
    )
    """3D-Coordinates: Y"""

    current_host_z_3d = Column(
        'current_host_z_3d',
        col_type='float',
        description='3D-Coordinates: Z',
    )
    """3D-Coordinates: Z"""

    current_service_accept_passive_checks = Column(
        'current_service_accept_passive_checks',
        col_type='int',
        description='Whether passive host checks are accepted (0/1)',
    )
    """Whether passive host checks are accepted (0/1)"""

    current_service_acknowledged = Column(
        'current_service_acknowledged',
        col_type='int',
        description='Whether the current problem has been acknowledged (0/1)',
    )
    """Whether the current problem has been acknowledged (0/1)"""

    current_service_acknowledgement_type = Column(
        'current_service_acknowledgement_type',
        col_type='int',
        description='Type of acknowledgement (0: none, 1: normal, 2: sticky)',
    )
    """Type of acknowledgement (0: none, 1: normal, 2: sticky)"""

    current_service_action_url = Column(
        'current_service_action_url',
        col_type='string',
        description='An optional URL to custom actions or information about this host',
    )
    """An optional URL to custom actions or information about this host"""

    current_service_action_url_expanded = Column(
        'current_service_action_url_expanded',
        col_type='string',
        description='The same as action_url, but with the most important macros expanded',
    )
    """The same as action_url, but with the most important macros expanded"""

    current_service_active_checks_enabled = Column(
        'current_service_active_checks_enabled',
        col_type='int',
        description='Whether active checks of the object are enabled (0/1)',
    )
    """Whether active checks of the object are enabled (0/1)"""

    current_service_cache_interval = Column(
        'current_service_cache_interval',
        col_type='int',
        description='For checks that base on cached agent data the interval in that this cache is recreated. 0 for other services.',
    )
    """For checks that base on cached agent data the interval in that this cache is recreated. 0 for other services."""

    current_service_cached_at = Column(
        'current_service_cached_at',
        col_type='time',
        description='For checks that base on cached agent data the time when this data was created. 0 for other services.',
    )
    """For checks that base on cached agent data the time when this data was created. 0 for other services."""

    current_service_check_command = Column(
        'current_service_check_command',
        col_type='string',
        description='Logical command name for active checks',
    )
    """Logical command name for active checks"""

    current_service_check_command_expanded = Column(
        'current_service_check_command_expanded',
        col_type='string',
        description='Logical command name for active checks, with macros expanded',
    )
    """Logical command name for active checks, with macros expanded"""

    current_service_check_flapping_recovery_notification = Column(
        'current_service_check_flapping_recovery_notification',
        col_type='int',
        description='Whether to check to send a recovery notification when flapping stops (0/1)',
    )
    """Whether to check to send a recovery notification when flapping stops (0/1)"""

    current_service_check_freshness = Column(
        'current_service_check_freshness',
        col_type='int',
        description='Whether freshness checks are enabled (0/1)',
    )
    """Whether freshness checks are enabled (0/1)"""

    current_service_check_interval = Column(
        'current_service_check_interval',
        col_type='float',
        description='Number of basic interval lengths between two scheduled checks',
    )
    """Number of basic interval lengths between two scheduled checks"""

    current_service_check_options = Column(
        'current_service_check_options',
        col_type='int',
        description='The current check option, forced, normal, freshness (0-2)',
    )
    """The current check option, forced, normal, freshness (0-2)"""

    current_service_check_period = Column(
        'current_service_check_period',
        col_type='string',
        description='Time period in which this object will be checked. If empty then the check will always be executed.',
    )
    """Time period in which this object will be checked. If empty then the check will always be executed."""

    current_service_check_type = Column(
        'current_service_check_type',
        col_type='int',
        description='Type of check (0: active, 1: passive)',
    )
    """Type of check (0: active, 1: passive)"""

    current_service_checks_enabled = Column(
        'current_service_checks_enabled',
        col_type='int',
        description='Whether checks of the object are enabled (0/1)',
    )
    """Whether checks of the object are enabled (0/1)"""

    current_service_comments = Column(
        'current_service_comments',
        col_type='list',
        description='A list of the ids of all comments',
    )
    """A list of the ids of all comments"""

    current_service_comments_with_extra_info = Column(
        'current_service_comments_with_extra_info',
        col_type='list',
        description='A list of all comments with id, author, comment, entry type and entry time',
    )
    """A list of all comments with id, author, comment, entry type and entry time"""

    current_service_comments_with_info = Column(
        'current_service_comments_with_info',
        col_type='list',
        description='A list of all comments with id, author and comment',
    )
    """A list of all comments with id, author and comment"""

    current_service_contact_groups = Column(
        'current_service_contact_groups',
        col_type='list',
        description='A list of all contact groups this object is in',
    )
    """A list of all contact groups this object is in"""

    current_service_contacts = Column(
        'current_service_contacts',
        col_type='list',
        description='A list of all contacts of this object',
    )
    """A list of all contacts of this object"""

    current_service_current_attempt = Column(
        'current_service_current_attempt',
        col_type='int',
        description='Number of the current check attempts',
    )
    """Number of the current check attempts"""

    current_service_current_notification_number = Column(
        'current_service_current_notification_number',
        col_type='int',
        description='Number of the current notification',
    )
    """Number of the current notification"""

    current_service_custom_variable_names = Column(
        'current_service_custom_variable_names',
        col_type='list',
        description='A list of the names of the custom variables',
    )
    """A list of the names of the custom variables"""

    current_service_custom_variable_values = Column(
        'current_service_custom_variable_values',
        col_type='list',
        description='A list of the values of the custom variables',
    )
    """A list of the values of the custom variables"""

    current_service_custom_variables = Column(
        'current_service_custom_variables',
        col_type='dict',
        description='A dictionary of the custom variables',
    )
    """A dictionary of the custom variables"""

    current_service_description = Column(
        'current_service_description',
        col_type='string',
        description='Service name',
    )
    """Service name"""

    current_service_display_name = Column(
        'current_service_display_name',
        col_type='string',
        description='Optional display name',
    )
    """Optional display name"""

    current_service_downtimes = Column(
        'current_service_downtimes',
        col_type='list',
        description='A list of the ids of all scheduled downtimes of this object',
    )
    """A list of the ids of all scheduled downtimes of this object"""

    current_service_downtimes_with_extra_info = Column(
        'current_service_downtimes_with_extra_info',
        col_type='list',
        description='A list of the scheduled downtimes with id, author, comment, origin, entry_time, start_time, end_time, fixed, duration, recurring and is_pending',
    )
    """A list of the scheduled downtimes with id, author, comment, origin, entry_time, start_time, end_time, fixed, duration, recurring and is_pending"""

    current_service_downtimes_with_info = Column(
        'current_service_downtimes_with_info',
        col_type='list',
        description='A list of the scheduled downtimes with id, author and comment',
    )
    """A list of the scheduled downtimes with id, author and comment"""

    current_service_event_handler = Column(
        'current_service_event_handler',
        col_type='string',
        description='Command used as event handler',
    )
    """Command used as event handler"""

    current_service_event_handler_enabled = Column(
        'current_service_event_handler_enabled',
        col_type='int',
        description='Whether event handling is enabled (0/1)',
    )
    """Whether event handling is enabled (0/1)"""

    current_service_execution_time = Column(
        'current_service_execution_time',
        col_type='float',
        description='Time the check needed for execution',
    )
    """Time the check needed for execution"""

    current_service_first_notification_delay = Column(
        'current_service_first_notification_delay',
        col_type='float',
        description='Delay before the first notification',
    )
    """Delay before the first notification"""

    current_service_flap_detection_enabled = Column(
        'current_service_flap_detection_enabled',
        col_type='int',
        description='Whether flap detection is enabled (0/1)',
    )
    """Whether flap detection is enabled (0/1)"""

    current_service_flappiness = Column(
        'current_service_flappiness',
        col_type='float',
        description='The current level of flappiness, this corresponds with the recent frequency of state changes',
    )
    """The current level of flappiness, this corresponds with the recent frequency of state changes"""

    current_service_groups = Column(
        'current_service_groups',
        col_type='list',
        description='A list of all service groups this object is in',
    )
    """A list of all service groups this object is in"""

    current_service_hard_state = Column(
        'current_service_hard_state',
        col_type='int',
        description='The effective hard state of this object',
    )
    """The effective hard state of this object"""

    current_service_has_been_checked = Column(
        'current_service_has_been_checked',
        col_type='int',
        description='Whether a check has already been executed (0/1)',
    )
    """Whether a check has already been executed (0/1)"""

    current_service_high_flap_threshold = Column(
        'current_service_high_flap_threshold',
        col_type='float',
        description='High threshold of flap detection',
    )
    """High threshold of flap detection"""

    current_service_icon_image = Column(
        'current_service_icon_image',
        col_type='string',
        description='The name of an image file to be used in the web pages',
    )
    """The name of an image file to be used in the web pages"""

    current_service_icon_image_alt = Column(
        'current_service_icon_image_alt',
        col_type='string',
        description='Alternative text for the icon_image',
    )
    """Alternative text for the icon_image"""

    current_service_icon_image_expanded = Column(
        'current_service_icon_image_expanded',
        col_type='string',
        description='The same as icon_image, but with the most important macros expanded',
    )
    """The same as icon_image, but with the most important macros expanded"""

    current_service_in_check_period = Column(
        'current_service_in_check_period',
        col_type='int',
        description='Whether this object is currently in its check period (0/1)',
    )
    """Whether this object is currently in its check period (0/1)"""

    current_service_in_notification_period = Column(
        'current_service_in_notification_period',
        col_type='int',
        description='Whether this object is currently in its notification period (0/1)',
    )
    """Whether this object is currently in its notification period (0/1)"""

    current_service_in_passive_check_period = Column(
        'current_service_in_passive_check_period',
        col_type='int',
        description='Whether this service is currently in its passive check period (0/1)',
    )
    """Whether this service is currently in its passive check period (0/1)"""

    current_service_in_service_period = Column(
        'current_service_in_service_period',
        col_type='int',
        description='Whether this object is currently in its service period (0/1)',
    )
    """Whether this object is currently in its service period (0/1)"""

    current_service_initial_state = Column(
        'current_service_initial_state',
        col_type='int',
        description='Initial state',
    )
    """Initial state"""

    current_service_is_executing = Column(
        'current_service_is_executing',
        col_type='int',
        description='is there a check currently running (0/1)',
    )
    """is there a check currently running (0/1)"""

    current_service_is_flapping = Column(
        'current_service_is_flapping',
        col_type='int',
        description='Whether the state is flapping (0/1)',
    )
    """Whether the state is flapping (0/1)"""

    current_service_label_names = Column(
        'current_service_label_names',
        col_type='list',
        description='A list of the names of the labels',
    )
    """A list of the names of the labels"""

    current_service_label_source_names = Column(
        'current_service_label_source_names',
        col_type='list',
        description='A list of the names of the label sources',
    )
    """A list of the names of the label sources"""

    current_service_label_source_values = Column(
        'current_service_label_source_values',
        col_type='list',
        description='A list of the values of the label sources',
    )
    """A list of the values of the label sources"""

    current_service_label_sources = Column(
        'current_service_label_sources',
        col_type='dict',
        description='A dictionary of the label sources',
    )
    """A dictionary of the label sources"""

    current_service_label_values = Column(
        'current_service_label_values',
        col_type='list',
        description='A list of the values of the labels',
    )
    """A list of the values of the labels"""

    current_service_labels = Column(
        'current_service_labels',
        col_type='dict',
        description='A dictionary of the labels',
    )
    """A dictionary of the labels"""

    current_service_last_check = Column(
        'current_service_last_check',
        col_type='time',
        description='Time of the last check (Unix timestamp)',
    )
    """Time of the last check (Unix timestamp)"""

    current_service_last_hard_state = Column(
        'current_service_last_hard_state',
        col_type='int',
        description='Last hard state',
    )
    """Last hard state"""

    current_service_last_hard_state_change = Column(
        'current_service_last_hard_state_change',
        col_type='time',
        description='Time of the last hard state change - soft or hard (Unix timestamp)',
    )
    """Time of the last hard state change - soft or hard (Unix timestamp)"""

    current_service_last_notification = Column(
        'current_service_last_notification',
        col_type='time',
        description='Time of the last notification (Unix timestamp)',
    )
    """Time of the last notification (Unix timestamp)"""

    current_service_last_state = Column(
        'current_service_last_state',
        col_type='int',
        description='State before last state change',
    )
    """State before last state change"""

    current_service_last_state_change = Column(
        'current_service_last_state_change',
        col_type='time',
        description='Time of the last state change - soft or hard (Unix timestamp)',
    )
    """Time of the last state change - soft or hard (Unix timestamp)"""

    current_service_last_time_critical = Column(
        'current_service_last_time_critical',
        col_type='time',
        description='Last time the service was CRIT (Unix timestamp)',
    )
    """Last time the service was CRIT (Unix timestamp)"""

    current_service_last_time_ok = Column(
        'current_service_last_time_ok',
        col_type='time',
        description='Last time the service was OK (Unix timestamp)',
    )
    """Last time the service was OK (Unix timestamp)"""

    current_service_last_time_unknown = Column(
        'current_service_last_time_unknown',
        col_type='time',
        description='Last time the service was UNKNOWN (Unix timestamp)',
    )
    """Last time the service was UNKNOWN (Unix timestamp)"""

    current_service_last_time_warning = Column(
        'current_service_last_time_warning',
        col_type='time',
        description='Last time the service was WARN (Unix timestamp)',
    )
    """Last time the service was WARN (Unix timestamp)"""

    current_service_latency = Column(
        'current_service_latency',
        col_type='float',
        description='Time difference between scheduled check time and actual check time',
    )
    """Time difference between scheduled check time and actual check time"""

    current_service_long_plugin_output = Column(
        'current_service_long_plugin_output',
        col_type='string',
        description='Long (extra) output of the last check',
    )
    """Long (extra) output of the last check"""

    current_service_low_flap_threshold = Column(
        'current_service_low_flap_threshold',
        col_type='float',
        description='Low threshold of flap detection',
    )
    """Low threshold of flap detection"""

    current_service_max_check_attempts = Column(
        'current_service_max_check_attempts',
        col_type='int',
        description='Maximum attempts for active checks before a hard state',
    )
    """Maximum attempts for active checks before a hard state"""

    current_service_metrics = Column(
        'current_service_metrics',
        col_type='list',
        description='A list of all metrics of this object that historically existed',
    )
    """A list of all metrics of this object that historically existed"""

    current_service_modified_attributes = Column(
        'current_service_modified_attributes',
        col_type='int',
        description='A bitmask specifying which attributes have been modified',
    )
    """A bitmask specifying which attributes have been modified"""

    current_service_modified_attributes_list = Column(
        'current_service_modified_attributes_list',
        col_type='list',
        description='A list of all modified attributes',
    )
    """A list of all modified attributes"""

    current_service_next_check = Column(
        'current_service_next_check',
        col_type='time',
        description='Scheduled time for the next check (Unix timestamp)',
    )
    """Scheduled time for the next check (Unix timestamp)"""

    current_service_next_notification = Column(
        'current_service_next_notification',
        col_type='time',
        description='Time of the next notification (Unix timestamp)',
    )
    """Time of the next notification (Unix timestamp)"""

    current_service_no_more_notifications = Column(
        'current_service_no_more_notifications',
        col_type='int',
        description='Whether to stop sending notifications (0/1)',
    )
    """Whether to stop sending notifications (0/1)"""

    current_service_notes = Column(
        'current_service_notes',
        col_type='string',
        description='Optional notes for this object, with macros not expanded',
    )
    """Optional notes for this object, with macros not expanded"""

    current_service_notes_expanded = Column(
        'current_service_notes_expanded',
        col_type='string',
        description='The same as notes, but with the most important macros expanded',
    )
    """The same as notes, but with the most important macros expanded"""

    current_service_notes_url = Column(
        'current_service_notes_url',
        col_type='string',
        description='An optional URL with further information about the object',
    )
    """An optional URL with further information about the object"""

    current_service_notes_url_expanded = Column(
        'current_service_notes_url_expanded',
        col_type='string',
        description='Same es notes_url, but with the most important macros expanded',
    )
    """Same es notes_url, but with the most important macros expanded"""

    current_service_notification_interval = Column(
        'current_service_notification_interval',
        col_type='float',
        description='Interval of periodic notification in minutes or 0 if its off',
    )
    """Interval of periodic notification in minutes or 0 if its off"""

    current_service_notification_period = Column(
        'current_service_notification_period',
        col_type='string',
        description='Time period in which problems of this object will be notified. If empty then notification will be always',
    )
    """Time period in which problems of this object will be notified. If empty then notification will be always"""

    current_service_notification_postponement_reason = Column(
        'current_service_notification_postponement_reason',
        col_type='string',
        description='reason for postponing the pending notification, empty if nothing is postponed',
    )
    """reason for postponing the pending notification, empty if nothing is postponed"""

    current_service_notifications_enabled = Column(
        'current_service_notifications_enabled',
        col_type='int',
        description='Whether notifications of the host are enabled (0/1)',
    )
    """Whether notifications of the host are enabled (0/1)"""

    current_service_obsess_over_service = Column(
        'current_service_obsess_over_service',
        col_type='int',
        description='The current obsess_over_service setting (0/1)',
    )
    """The current obsess_over_service setting (0/1)"""

    current_service_passive_check_period = Column(
        'current_service_passive_check_period',
        col_type='string',
        description='Time period in which this (passive) service will be checked.',
    )
    """Time period in which this (passive) service will be checked."""

    current_service_pending_flex_downtime = Column(
        'current_service_pending_flex_downtime',
        col_type='int',
        description='Number of pending flexible downtimes',
    )
    """Number of pending flexible downtimes"""

    current_service_percent_state_change = Column(
        'current_service_percent_state_change',
        col_type='float',
        description='Percent state change',
    )
    """Percent state change"""

    current_service_perf_data = Column(
        'current_service_perf_data',
        col_type='string',
        description='Optional performance data of the last check',
    )
    """Optional performance data of the last check"""

    current_service_performance_data = Column(
        'current_service_performance_data',
        col_type='dictdouble',
        description='Optional performance data as a dict',
    )
    """Optional performance data as a dict"""

    current_service_plugin_output = Column(
        'current_service_plugin_output',
        col_type='string',
        description='Output of the last check',
    )
    """Output of the last check"""

    current_service_pnpgraph_present = Column(
        'current_service_pnpgraph_present',
        col_type='int',
        description='Whether there is a PNP4Nagios graph present for this object (-1/0/1)',
    )
    """Whether there is a PNP4Nagios graph present for this object (-1/0/1)"""

    current_service_prediction_files = Column(
        'current_service_prediction_files',
        col_type='list',
        description='List currently available predictions',
    )
    """List currently available predictions"""

    current_service_previous_hard_state = Column(
        'current_service_previous_hard_state',
        col_type='int',
        description='Previous hard state (that hard state before the current/last hard state)',
    )
    """Previous hard state (that hard state before the current/last hard state)"""

    current_service_process_performance_data = Column(
        'current_service_process_performance_data',
        col_type='int',
        description='Whether processing of performance data is enabled (0/1)',
    )
    """Whether processing of performance data is enabled (0/1)"""

    current_service_retry_interval = Column(
        'current_service_retry_interval',
        col_type='float',
        description='Number of basic interval lengths between checks when retrying after a soft error',
    )
    """Number of basic interval lengths between checks when retrying after a soft error"""

    current_service_robotmk_last_error_log = Column(
        'current_service_robotmk_last_error_log',
        col_type='blob',
        description='The file content of the Robotmk error log',
    )
    """The file content of the Robotmk error log"""

    current_service_robotmk_last_error_log_gz = Column(
        'current_service_robotmk_last_error_log_gz',
        col_type='blob',
        description='The gzipped file content of the Robotmk error log',
    )
    """The gzipped file content of the Robotmk error log"""

    current_service_robotmk_last_log = Column(
        'current_service_robotmk_last_log',
        col_type='blob',
        description='The file content of the Robotmk log',
    )
    """The file content of the Robotmk log"""

    current_service_robotmk_last_log_gz = Column(
        'current_service_robotmk_last_log_gz',
        col_type='blob',
        description='The gzipped file content of the Robotmk log',
    )
    """The gzipped file content of the Robotmk log"""

    current_service_scheduled_downtime_depth = Column(
        'current_service_scheduled_downtime_depth',
        col_type='int',
        description='The number of downtimes this object is currently in',
    )
    """The number of downtimes this object is currently in"""

    current_service_service_period = Column(
        'current_service_service_period',
        col_type='string',
        description='Time period during which the object is expected to be available',
    )
    """Time period during which the object is expected to be available"""

    current_service_staleness = Column(
        'current_service_staleness',
        col_type='float',
        description='The staleness of this object',
    )
    """The staleness of this object"""

    current_service_state = Column(
        'current_service_state',
        col_type='int',
        description='The current state of the object, for hosts: 0/1/2 for UP/DOWN/UNREACH, for services: 0/1/2/3 for OK/WARN/CRIT/UNKNOWN',
    )
    """The current state of the object, for hosts: 0/1/2 for UP/DOWN/UNREACH, for services: 0/1/2/3 for OK/WARN/CRIT/UNKNOWN"""

    current_service_state_type = Column(
        'current_service_state_type',
        col_type='int',
        description='Type of the current state (0: soft, 1: hard)',
    )
    """Type of the current state (0: soft, 1: hard)"""

    current_service_tag_names = Column(
        'current_service_tag_names',
        col_type='list',
        description='A list of the names of the tags',
    )
    """A list of the names of the tags"""

    current_service_tag_values = Column(
        'current_service_tag_values',
        col_type='list',
        description='A list of the values of the tags',
    )
    """A list of the values of the tags"""

    current_service_tags = Column(
        'current_service_tags',
        col_type='dict',
        description='A dictionary of the tags',
    )
    """A dictionary of the tags"""

    debug_info = Column(
        'debug_info',
        col_type='string',
        description='Debug information',
    )
    """Debug information"""

    duration = Column(
        'duration',
        col_type='int',
        description='Duration of state (until - from)',
    )
    """Duration of state (until - from)"""

    duration_critical = Column(
        'duration_critical',
        col_type='int',
        description='CRITICAL duration of state (until - from)',
    )
    """CRITICAL duration of state (until - from)"""

    duration_ok = Column(
        'duration_ok',
        col_type='int',
        description='OK duration of state ( until - from )',
    )
    """OK duration of state ( until - from )"""

    duration_part = Column(
        'duration_part',
        col_type='float',
        description='Duration part in regard to the query timeframe',
    )
    """Duration part in regard to the query timeframe"""

    duration_part_critical = Column(
        'duration_part_critical',
        col_type='float',
        description='CRITICAL duration part in regard to the query timeframe',
    )
    """CRITICAL duration part in regard to the query timeframe"""

    duration_part_ok = Column(
        'duration_part_ok',
        col_type='float',
        description='OK duration part in regard to the query timeframe',
    )
    """OK duration part in regard to the query timeframe"""

    duration_part_unknown = Column(
        'duration_part_unknown',
        col_type='float',
        description='UNKNOWN duration part in regard to the query timeframe',
    )
    """UNKNOWN duration part in regard to the query timeframe"""

    duration_part_unmonitored = Column(
        'duration_part_unmonitored',
        col_type='float',
        description='UNMONITORED duration part in regard to the query timeframe',
    )
    """UNMONITORED duration part in regard to the query timeframe"""

    duration_part_warning = Column(
        'duration_part_warning',
        col_type='float',
        description='WARNING duration part in regard to the query timeframe',
    )
    """WARNING duration part in regard to the query timeframe"""

    duration_unknown = Column(
        'duration_unknown',
        col_type='int',
        description='UNKNOWN duration of state (until - from)',
    )
    """UNKNOWN duration of state (until - from)"""

    duration_unmonitored = Column(
        'duration_unmonitored',
        col_type='int',
        description='UNMONITORED duration of state (until - from)',
    )
    """UNMONITORED duration of state (until - from)"""

    duration_warning = Column(
        'duration_warning',
        col_type='int',
        description='WARNING duration of state (until - from)',
    )
    """WARNING duration of state (until - from)"""

    from_ = Column(
        'from',
        col_type='time',
        description='Start time of state (seconds since 1/1/1970)',
    )
    """Start time of state (seconds since 1/1/1970)"""

    host_down = Column(
        'host_down',
        col_type='int',
        description='Shows if the host of this service is down',
    )
    """Shows if the host of this service is down"""

    host_name = Column(
        'host_name',
        col_type='string',
        description='Host name',
    )
    """Host name"""

    in_downtime = Column(
        'in_downtime',
        col_type='int',
        description='Shows if the host or service is in downtime',
    )
    """Shows if the host or service is in downtime"""

    in_host_downtime = Column(
        'in_host_downtime',
        col_type='int',
        description='Shows if the host of this service is in downtime',
    )
    """Shows if the host of this service is in downtime"""

    in_notification_period = Column(
        'in_notification_period',
        col_type='int',
        description='Shows if the host or service is within its notification period',
    )
    """Shows if the host or service is within its notification period"""

    in_service_period = Column(
        'in_service_period',
        col_type='int',
        description='Shows if the host or service is within its service period',
    )
    """Shows if the host or service is within its service period"""

    is_flapping = Column(
        'is_flapping',
        col_type='int',
        description='Shows if the host or service is flapping',
    )
    """Shows if the host or service is flapping"""

    lineno = Column(
        'lineno',
        col_type='int',
        description='The number of the line in the log file',
    )
    """The number of the line in the log file"""

    log_output = Column(
        'log_output',
        col_type='string',
        description='Logfile output relevant for this state',
    )
    """Logfile output relevant for this state"""

    long_log_output = Column(
        'long_log_output',
        col_type='string',
        description='Complete logfile output relevant for this state',
    )
    """Complete logfile output relevant for this state"""

    notification_period = Column(
        'notification_period',
        col_type='string',
        description='The notification period of the host or service in question',
    )
    """The notification period of the host or service in question"""

    service_description = Column(
        'service_description',
        col_type='string',
        description='Description of the service',
    )
    """Description of the service"""

    service_period = Column(
        'service_period',
        col_type='string',
        description='The service period of the host or service in question',
    )
    """The service period of the host or service in question"""

    state = Column(
        'state',
        col_type='int',
        description='The state of the host or service in question - OK(0) / WARNING(1) / CRITICAL(2) / UNKNOWN(3) / UNMONITORED(-1)',
    )
    """The state of the host or service in question - OK(0) / WARNING(1) / CRITICAL(2) / UNKNOWN(3) / UNMONITORED(-1)"""

    time = Column(
        'time',
        col_type='time',
        description='Time of the log event (seconds since 1/1/1970)',
    )
    """Time of the log event (seconds since 1/1/1970)"""

    until = Column(
        'until',
        col_type='time',
        description='End time of state (seconds since 1/1/1970)',
    )
    """End time of state (seconds since 1/1/1970)"""
