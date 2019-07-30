// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// tails. You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#include "TableHosts.h"
#include <memory>
#include <optional>
#include <ostream>
#include "AttributeListAsIntColumn.h"
#include "AttributeListColumn.h"
#include "Column.h"
#include "CommentColumn.h"
#include "ContactGroupsColumn.h"
#include "CustomTimeperiodColumn.h"
#include "CustomVarsDictColumn.h"
#include "CustomVarsExplicitColumn.h"
#include "CustomVarsNamesColumn.h"
#include "CustomVarsValuesColumn.h"
#include "DowntimeColumn.h"
#include "DynamicColumn.h"
#include "DynamicLogwatchFileColumn.h"
#include "HostContactsColumn.h"
#include "HostFileColumn.h"
#include "HostGroupsColumn.h"
#include "HostListColumn.h"
#include "HostSpecialDoubleColumn.h"
#include "HostSpecialIntColumn.h"
#include "Logger.h"
#include "LogwatchListColumn.h"
#include "MetricsColumn.h"
#include "MonitoringCore.h"
#include "OffsetDoubleColumn.h"
#include "OffsetIntColumn.h"
#include "OffsetPerfdataColumn.h"
#include "OffsetStringColumn.h"
#include "OffsetStringHostMacroColumn.h"
#include "OffsetTimeColumn.h"
#include "Query.h"
#include "ServiceListColumn.h"
#include "ServiceListStateColumn.h"
#include "TimeperiodColumn.h"
#include "auth.h"
#include "nagios.h"

extern host *host_list;

TableHosts::TableHosts(MonitoringCore *mc) : Table(mc) {
    addColumns(this, "", -1, -1);
}

std::string TableHosts::name() const { return "hosts"; }

std::string TableHosts::namePrefix() const { return "host_"; }

// static
void TableHosts::addColumns(Table *table, const std::string &prefix,
                            int indirect_offset, int extra_offset) {
    auto mc = table->core();
    table->addColumn(std::make_unique<OffsetStringColumn>(
        prefix + "name", "Host name", indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, name)));
    table->addColumn(std::make_unique<OffsetStringColumn>(
        prefix + "display_name",
        "Optional display name of the host - not used by Nagios' web interface",
        indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, display_name)));
    table->addColumn(std::make_unique<OffsetStringColumn>(
        prefix + "alias", "An alias name for the host", indirect_offset,
        extra_offset, -1, DANGEROUS_OFFSETOF(host, alias)));
    table->addColumn(std::make_unique<OffsetStringColumn>(
        prefix + "address", "IP address", indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, address)));
#ifdef NAGIOS4
    table->addColumn(std::make_unique<OffsetStringColumn>(
        prefix + "check_command",
        "Nagios command for active host check of this host", indirect_offset,
        extra_offset, -1, DANGEROUS_OFFSETOF(host, check_command)));
    table->addColumn(std::make_unique<OffsetStringHostMacroColumn>(
        prefix + "check_command_expanded",
        "Nagios command for active host check of this host with the macros expanded",
        indirect_offset, extra_offset, -1, table->core(),
        DANGEROUS_OFFSETOF(host, check_command)));
#else
    table->addColumn(std::make_unique<OffsetStringColumn>(
        prefix + "check_command",
        "Nagios command for active host check of this host", indirect_offset,
        extra_offset, -1, DANGEROUS_OFFSETOF(host, host_check_command)));
    table->addColumn(std::make_unique<OffsetStringHostMacroColumn>(
        prefix + "check_command_expanded",
        "Nagios command for active host check of this host with the macros expanded",
        indirect_offset, extra_offset, -1, table->core(),
        DANGEROUS_OFFSETOF(host, host_check_command)));
#endif
    table->addColumn(std::make_unique<OffsetStringColumn>(
        prefix + "event_handler", "Nagios command used as event handler",
        indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, event_handler)));
    table->addColumn(std::make_unique<OffsetStringColumn>(
        prefix + "notification_period",
        "Time period in which problems of this host will be notified. If empty then notification will be always",
        indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, notification_period)));
    table->addColumn(std::make_unique<OffsetStringColumn>(
        prefix + "check_period",
        "Time period in which this host will be checked. If empty then the host will always be checked.",
        indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, check_period)));
    table->addColumn(std::make_unique<CustomVarsExplicitColumn>(
        prefix + "service_period", "The name of the service period of the host",
        indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, custom_variables), table->core(),
        "SERVICE_PERIOD"));
    table->addColumn(std::make_unique<OffsetStringColumn>(
        prefix + "notes", "Optional notes for this host", indirect_offset,
        extra_offset, -1, DANGEROUS_OFFSETOF(host, notes)));
    table->addColumn(std::make_unique<OffsetStringHostMacroColumn>(
        prefix + "notes_expanded",
        "The same as notes, but with the most important macros expanded",
        indirect_offset, extra_offset, -1, table->core(),
        DANGEROUS_OFFSETOF(host, notes)));
    table->addColumn(std::make_unique<OffsetStringColumn>(
        prefix + "notes_url",
        "An optional URL with further information about the host",
        indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, notes_url)));
    table->addColumn(std::make_unique<OffsetStringHostMacroColumn>(
        prefix + "notes_url_expanded",
        "Same es notes_url, but with the most important macros expanded",
        indirect_offset, extra_offset, -1, table->core(),
        DANGEROUS_OFFSETOF(host, notes_url)));
    table->addColumn(std::make_unique<OffsetStringColumn>(
        prefix + "action_url",
        "An optional URL to custom actions or information about this host",
        indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, action_url)));
    table->addColumn(std::make_unique<OffsetStringHostMacroColumn>(
        prefix + "action_url_expanded",
        "The same as action_url, but with the most important macros expanded",
        indirect_offset, extra_offset, -1, table->core(),
        DANGEROUS_OFFSETOF(host, action_url)));
    table->addColumn(std::make_unique<OffsetStringColumn>(
        prefix + "plugin_output", "Output of the last host check",
        indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, plugin_output)));
    table->addColumn(std::make_unique<OffsetPerfdataColumn>(
        prefix + "perf_data",
        "Optional performance data of the last host check", indirect_offset,
        extra_offset, -1, DANGEROUS_OFFSETOF(host, perf_data)));
    table->addColumn(std::make_unique<OffsetStringColumn>(
        prefix + "icon_image",
        "The name of an image file to be used in the web pages",
        indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, icon_image)));
    table->addColumn(std::make_unique<OffsetStringHostMacroColumn>(
        prefix + "icon_image_expanded",
        "The same as icon_image, but with the most important macros expanded",
        indirect_offset, extra_offset, -1, table->core(),
        DANGEROUS_OFFSETOF(host, icon_image)));
    table->addColumn(std::make_unique<OffsetStringColumn>(
        prefix + "icon_image_alt", "Alternative text for the icon_image",
        indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, icon_image_alt)));
    table->addColumn(std::make_unique<OffsetStringColumn>(
        prefix + "statusmap_image",
        "The name of in image file for the status map", indirect_offset,
        extra_offset, -1, DANGEROUS_OFFSETOF(host, statusmap_image)));
    table->addColumn(std::make_unique<OffsetStringColumn>(
        prefix + "long_plugin_output", "Complete output from check plugin",
        indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, long_plugin_output)));

    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "initial_state", "Initial host state", indirect_offset,
        extra_offset, -1, DANGEROUS_OFFSETOF(host, initial_state)));
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "max_check_attempts",
        "Max check attempts for active host checks", indirect_offset,
        extra_offset, -1, DANGEROUS_OFFSETOF(host, max_attempts)));
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "flap_detection_enabled",
        "Whether flap detection is enabled (0/1)", indirect_offset,
        extra_offset, -1, DANGEROUS_OFFSETOF(host, flap_detection_enabled)));
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "check_freshness",
        "Whether freshness checks are activated (0/1)", indirect_offset,
        extra_offset, -1, DANGEROUS_OFFSETOF(host, check_freshness)));
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "process_performance_data",
        "Whether processing of performance data is enabled (0/1)",
        indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, process_performance_data)));
#ifndef NAGIOS4
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "accept_passive_checks",
        "Whether passive host checks are accepted (0/1)", indirect_offset,
        extra_offset, -1,
        DANGEROUS_OFFSETOF(host, accept_passive_host_checks)));
#else
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "accept_passive_checks",
        "Whether passive host checks are accepted (0/1)", indirect_offset,
        extra_offset, -1, DANGEROUS_OFFSETOF(host, accept_passive_checks)));
#endif  // NAGIOS4
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "event_handler_enabled",
        "Whether event handling is enabled (0/1)", indirect_offset,
        extra_offset, -1, DANGEROUS_OFFSETOF(host, event_handler_enabled)));
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "acknowledgement_type",
        "Type of acknowledgement (0: none, 1: normal, 2: stick)",
        indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, acknowledgement_type)));
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "check_type", "Type of check (0: active, 1: passive)",
        indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, check_type)));
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "last_state", "State before last state change",
        indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, last_state)));
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "last_hard_state", "Last hard state", indirect_offset,
        extra_offset, -1, DANGEROUS_OFFSETOF(host, last_hard_state)));
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "current_attempt", "Number of the current check attempts",
        indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, current_attempt)));
#ifndef NAGIOS4
    table->addColumn(std::make_unique<OffsetTimeColumn>(
        prefix + "last_notification",
        "Time of the last notification (Unix timestamp)", indirect_offset,
        extra_offset, -1, DANGEROUS_OFFSETOF(host, last_host_notification)));
    table->addColumn(std::make_unique<OffsetTimeColumn>(
        prefix + "next_notification",
        "Time of the next notification (Unix timestamp)", indirect_offset,
        extra_offset, -1, DANGEROUS_OFFSETOF(host, next_host_notification)));
#else
    table->addColumn(std::make_unique<OffsetTimeColumn>(
        prefix + "last_notification",
        "Time of the last notification (Unix timestamp)", indirect_offset,
        extra_offset, -1, DANGEROUS_OFFSETOF(host, last_notification)));
    table->addColumn(std::make_unique<OffsetTimeColumn>(
        prefix + "next_notification",
        "Time of the next notification (Unix timestamp)", indirect_offset,
        extra_offset, -1, DANGEROUS_OFFSETOF(host, next_notification)));
#endif  // NAGIOS4
    table->addColumn(std::make_unique<OffsetTimeColumn>(
        prefix + "next_check",
        "Scheduled time for the next check (Unix timestamp)", indirect_offset,
        extra_offset, -1, DANGEROUS_OFFSETOF(host, next_check)));
    table->addColumn(std::make_unique<OffsetTimeColumn>(
        prefix + "last_hard_state_change",
        "Time of the last hard state change (Unix timestamp)", indirect_offset,
        extra_offset, -1, DANGEROUS_OFFSETOF(host, last_hard_state_change)));
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "has_been_checked",
        "Whether the host has already been checked (0/1)", indirect_offset,
        extra_offset, -1, DANGEROUS_OFFSETOF(host, has_been_checked)));
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "current_notification_number",
        "Number of the current notification", indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, current_notification_number)));
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "pending_flex_downtime",
        "Number of pending flexible downtimes", indirect_offset, extra_offset,
        -1, DANGEROUS_OFFSETOF(host, pending_flex_downtime)));
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "total_services", "The total number of services of the host",
        indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, total_services)));
    // Note: this is redundant with "active_checks_enabled". Nobody noted this
    // before...
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "checks_enabled",
        "Whether checks of the host are enabled (0/1)", indirect_offset,
        extra_offset, -1, DANGEROUS_OFFSETOF(host, checks_enabled)));
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "notifications_enabled",
        "Whether notifications of the host are enabled (0/1)", indirect_offset,
        extra_offset, -1, DANGEROUS_OFFSETOF(host, notifications_enabled)));
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "acknowledged",
        "Whether the current host problem has been acknowledged (0/1)",
        indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, problem_has_been_acknowledged)));
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "state",
        "The current state of the host (0: up, 1: down, 2: unreachable)",
        indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, current_state)));
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "state_type", "Type of the current state (0: soft, 1: hard)",
        indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, state_type)));
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "no_more_notifications",
        "Whether to stop sending notifications (0/1)", indirect_offset,
        extra_offset, -1, DANGEROUS_OFFSETOF(host, no_more_notifications)));
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "check_flapping_recovery_notification",
        "Whether to check to send a recovery notification when flapping stops (0/1)",
        indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, check_flapping_recovery_notification)));
    table->addColumn(std::make_unique<OffsetTimeColumn>(
        prefix + "last_check", "Time of the last check (Unix timestamp)",
        indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, last_check)));
    table->addColumn(std::make_unique<OffsetTimeColumn>(
        prefix + "last_state_change",
        "Time of the last state change - soft or hard (Unix timestamp)",
        indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, last_state_change)));

    table->addColumn(std::make_unique<OffsetTimeColumn>(
        prefix + "last_time_up",
        "The last time the host was UP (Unix timestamp)", indirect_offset,
        extra_offset, -1, DANGEROUS_OFFSETOF(host, last_time_up)));
    table->addColumn(std::make_unique<OffsetTimeColumn>(
        prefix + "last_time_down",
        "The last time the host was DOWN (Unix timestamp)", indirect_offset,
        extra_offset, -1, DANGEROUS_OFFSETOF(host, last_time_down)));
    table->addColumn(std::make_unique<OffsetTimeColumn>(
        prefix + "last_time_unreachable",
        "The last time the host was UNREACHABLE (Unix timestamp)",
        indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, last_time_unreachable)));

    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "is_flapping", "Whether the host state is flapping (0/1)",
        indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, is_flapping)));
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "scheduled_downtime_depth",
        "The number of downtimes this host is currently in", indirect_offset,
        extra_offset, -1, DANGEROUS_OFFSETOF(host, scheduled_downtime_depth)));
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "is_executing",
        "is there a host check currently running... (0/1)", indirect_offset,
        extra_offset, -1, DANGEROUS_OFFSETOF(host, is_executing)));
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "active_checks_enabled",
        "Whether active checks are enabled for the host (0/1)", indirect_offset,
        extra_offset, -1, DANGEROUS_OFFSETOF(host, checks_enabled)));
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "check_options",
        "The current check option, forced, normal, freshness... (0-2)",
        indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, check_options)));
#ifndef NAGIOS4
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "obsess_over_host",
        "The current obsess_over_host setting... (0/1)", indirect_offset,
        extra_offset, -1, DANGEROUS_OFFSETOF(host, obsess_over_host)));
#else
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "obsess_over_host",
        "The current obsess_over_host setting... (0/1)", indirect_offset,
        extra_offset, -1, DANGEROUS_OFFSETOF(host, obsess)));
#endif  // NAGIOS4
    table->addColumn(std::make_unique<AttributeListAsIntColumn>(
        prefix + "modified_attributes",
        "A bitmask specifying which attributes have been modified",
        indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, modified_attributes)));
    table->addColumn(std::make_unique<AttributeListColumn>(
        prefix + "modified_attributes_list",
        "A list of all modified attributes", indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, modified_attributes)));

    // columns of type double
    table->addColumn(std::make_unique<OffsetDoubleColumn>(
        prefix + "check_interval",
        "Number of basic interval lengths between two scheduled checks of the host",
        indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, check_interval)));
    table->addColumn(std::make_unique<OffsetDoubleColumn>(
        prefix + "retry_interval",
        "Number of basic interval lengths between checks when retrying after a soft error",
        indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, retry_interval)));
    table->addColumn(std::make_unique<OffsetDoubleColumn>(
        prefix + "notification_interval",
        "Interval of periodic notification or 0 if its off", indirect_offset,
        extra_offset, -1, DANGEROUS_OFFSETOF(host, notification_interval)));
    table->addColumn(std::make_unique<OffsetDoubleColumn>(
        prefix + "first_notification_delay",
        "Delay before the first notification", indirect_offset, extra_offset,
        -1, DANGEROUS_OFFSETOF(host, first_notification_delay)));
    table->addColumn(std::make_unique<OffsetDoubleColumn>(
        prefix + "low_flap_threshold", "Low threshold of flap detection",
        indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, low_flap_threshold)));
    table->addColumn(std::make_unique<OffsetDoubleColumn>(
        prefix + "high_flap_threshold", "High threshold of flap detection",
        indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, high_flap_threshold)));
    table->addColumn(std::make_unique<OffsetDoubleColumn>(
        prefix + "x_3d", "3D-Coordinates: X", indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, x_3d)));
    table->addColumn(std::make_unique<OffsetDoubleColumn>(
        prefix + "y_3d", "3D-Coordinates: Y", indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, y_3d)));
    table->addColumn(std::make_unique<OffsetDoubleColumn>(
        prefix + "z_3d", "3D-Coordinates: Z", indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, z_3d)));
    table->addColumn(std::make_unique<OffsetDoubleColumn>(
        prefix + "latency",
        "Time difference between scheduled check time and actual check time",
        indirect_offset, extra_offset, -1, DANGEROUS_OFFSETOF(host, latency)));
    table->addColumn(std::make_unique<OffsetDoubleColumn>(
        prefix + "execution_time", "Time the host check needed for execution",
        indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, execution_time)));
    table->addColumn(std::make_unique<OffsetDoubleColumn>(
        prefix + "percent_state_change", "Percent state change",
        indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, percent_state_change)));

    table->addColumn(std::make_unique<TimeperiodColumn>(
        prefix + "in_notification_period",
        "Whether this host is currently in its notification period (0/1)",
        indirect_offset, extra_offset,
        DANGEROUS_OFFSETOF(host, notification_period_ptr), 0));
    table->addColumn(std::make_unique<TimeperiodColumn>(
        prefix + "in_check_period",
        "Whether this host is currently in its check period (0/1)",
        indirect_offset, extra_offset,
        DANGEROUS_OFFSETOF(host, check_period_ptr), 0));
    table->addColumn(std::make_unique<CustomTimeperiodColumn>(
        prefix + "in_service_period",
        "Whether this host is currently in its service period (0/1)",
        indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, custom_variables), table->core(),
        "SERVICE_PERIOD"));

    table->addColumn(std::make_unique<HostContactsColumn>(
        prefix + "contacts",
        "A list of all contacts of this host, either direct or via a contact group",
        indirect_offset, extra_offset, -1, 0));
    table->addColumn(std::make_unique<DowntimeColumn>(
        prefix + "downtimes",
        "A list of the ids of all scheduled downtimes of this host",
        indirect_offset, extra_offset, -1, 0, table->core(), false,
        DowntimeColumn::info::none));
    table->addColumn(std::make_unique<DowntimeColumn>(
        prefix + "downtimes_with_info",
        "A list of the scheduled downtimes of the host with id, author and comment",
        indirect_offset, extra_offset, -1, 0, table->core(), false,
        DowntimeColumn::info::medium));
    table->addColumn(std::make_unique<DowntimeColumn>(
        prefix + "downtimes_with_extra_info",
        "A list of the scheduled downtimes of the host with id, author, comment, origin, entry_time, start_time, end_time, fixed, duration, recurring and is_pending",
        indirect_offset, extra_offset, -1, 0, table->core(), false,
        DowntimeColumn::info::full));
    table->addColumn(std::make_unique<CommentColumn>(
        prefix + "comments", "A list of the ids of all comments of this host",
        indirect_offset, extra_offset, -1, 0, table->core(), false, false,
        false));
    table->addColumn(std::make_unique<CommentColumn>(
        prefix + "comments_with_info",
        "A list of all comments of the host with id, author and comment",
        indirect_offset, extra_offset, -1, 0, table->core(), false, true,
        false));
    table->addColumn(std::make_unique<CommentColumn>(
        prefix + "comments_with_extra_info",
        "A list of all comments of the host with id, author, comment, entry type and entry time",
        indirect_offset, extra_offset, -1, 0, table->core(), false, true,
        true));

    table->addColumn(std::make_unique<CustomVarsNamesColumn>(
        prefix + "custom_variable_names",
        "A list of the names of the custom variables", indirect_offset,
        extra_offset, -1, DANGEROUS_OFFSETOF(host, custom_variables),
        table->core(), AttributeKind::custom_variables));
    table->addColumn(std::make_unique<CustomVarsValuesColumn>(
        prefix + "custom_variable_values",
        "A list of the values of the custom variables", indirect_offset,
        extra_offset, -1, DANGEROUS_OFFSETOF(host, custom_variables),
        table->core(), AttributeKind::custom_variables));
    table->addColumn(std::make_unique<CustomVarsDictColumn>(
        prefix + "custom_variables", "A dictionary of the custom variables",
        indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, custom_variables), table->core(),
        AttributeKind::custom_variables));

    table->addColumn(std::make_unique<CustomVarsNamesColumn>(
        prefix + "tag_names", "A list of the names of the tags",
        indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, custom_variables), table->core(),
        AttributeKind::tags));
    table->addColumn(std::make_unique<CustomVarsValuesColumn>(
        prefix + "tag_values", "A list of the values of the tags",
        indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, custom_variables), table->core(),
        AttributeKind::tags));
    table->addColumn(std::make_unique<CustomVarsDictColumn>(
        prefix + "tags", "A dictionary of the tags", indirect_offset,
        extra_offset, -1, DANGEROUS_OFFSETOF(host, custom_variables),
        table->core(), AttributeKind::tags));

    table->addColumn(std::make_unique<CustomVarsNamesColumn>(
        prefix + "label_names", "A list of the names of the labels",
        indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, custom_variables), table->core(),
        AttributeKind::labels));
    table->addColumn(std::make_unique<CustomVarsValuesColumn>(
        prefix + "label_values", "A list of the values of the labels",
        indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, custom_variables), table->core(),
        AttributeKind::labels));
    table->addColumn(std::make_unique<CustomVarsDictColumn>(
        prefix + "labels", "A dictionary of the labels", indirect_offset,
        extra_offset, -1, DANGEROUS_OFFSETOF(host, custom_variables),
        table->core(), AttributeKind::labels));

    table->addColumn(std::make_unique<CustomVarsNamesColumn>(
        prefix + "label_source_names",
        "A list of the names of the label sources", indirect_offset,
        extra_offset, -1, DANGEROUS_OFFSETOF(host, custom_variables),
        table->core(), AttributeKind::label_sources));
    table->addColumn(std::make_unique<CustomVarsValuesColumn>(
        prefix + "label_source_values",
        "A list of the values of the label sources", indirect_offset,
        extra_offset, -1, DANGEROUS_OFFSETOF(host, custom_variables),
        table->core(), AttributeKind::label_sources));
    table->addColumn(std::make_unique<CustomVarsDictColumn>(
        prefix + "label_sources", "A dictionary of the label sources",
        indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, custom_variables), table->core(),
        AttributeKind::label_sources));

    // Add direct access to the custom macro _FILENAME. In a future version of
    // Livestatus this will probably be configurable so access to further custom
    // variable can be added, such that those variables are presented like
    // ordinary Nagios columns.
    table->addColumn(std::make_unique<CustomVarsExplicitColumn>(
        prefix + "filename", "The value of the custom variable FILENAME",
        indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, custom_variables), table->core(), "FILENAME"));

    table->addColumn(std::make_unique<HostListColumn>(
        prefix + "parents", "A list of all direct parents of the host",
        indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, parent_hosts), table->core(), false));
    table->addColumn(std::make_unique<HostListColumn>(
        prefix + "childs", "A list of all direct childs of the host",
        indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, child_hosts), table->core(), false));

    table->addColumn(std::make_unique<ServiceListStateColumn>(
        prefix + "num_services", "The total number of services of the host",
        indirect_offset, extra_offset, -1, DANGEROUS_OFFSETOF(host, services),
        table->core(), ServiceListStateColumn::Type::num));
    table->addColumn(std::make_unique<ServiceListStateColumn>(
        prefix + "worst_service_state",
        "The worst soft state of all of the host's services (OK <= WARN <= UNKNOWN <= CRIT)",
        indirect_offset, extra_offset, -1, DANGEROUS_OFFSETOF(host, services),
        table->core(), ServiceListStateColumn::Type::worst_state));
    table->addColumn(std::make_unique<ServiceListStateColumn>(
        prefix + "num_services_ok",
        "The number of the host's services with the soft state OK",
        indirect_offset, extra_offset, -1, DANGEROUS_OFFSETOF(host, services),
        table->core(), ServiceListStateColumn::Type::num_ok));
    table->addColumn(std::make_unique<ServiceListStateColumn>(
        prefix + "num_services_warn",
        "The number of the host's services with the soft state WARN",
        indirect_offset, extra_offset, -1, DANGEROUS_OFFSETOF(host, services),
        table->core(), ServiceListStateColumn::Type::num_warn));
    table->addColumn(std::make_unique<ServiceListStateColumn>(
        prefix + "num_services_crit",
        "The number of the host's services with the soft state CRIT",
        indirect_offset, extra_offset, -1, DANGEROUS_OFFSETOF(host, services),
        table->core(), ServiceListStateColumn::Type::num_crit));
    table->addColumn(std::make_unique<ServiceListStateColumn>(
        prefix + "num_services_unknown",
        "The number of the host's services with the soft state UNKNOWN",
        indirect_offset, extra_offset, -1, DANGEROUS_OFFSETOF(host, services),
        table->core(), ServiceListStateColumn::Type::num_unknown));
    table->addColumn(std::make_unique<ServiceListStateColumn>(
        prefix + "num_services_pending",
        "The number of the host's services which have not been checked yet (pending)",
        indirect_offset, extra_offset, -1, DANGEROUS_OFFSETOF(host, services),
        table->core(), ServiceListStateColumn::Type::num_pending));
    table->addColumn(std::make_unique<ServiceListStateColumn>(
        prefix + "worst_service_hard_state",
        "The worst hard state of all of the host's services (OK <= WARN <= UNKNOWN <= CRIT)",
        indirect_offset, extra_offset, -1, DANGEROUS_OFFSETOF(host, services),
        table->core(), ServiceListStateColumn::Type::worst_hard_state));
    table->addColumn(std::make_unique<ServiceListStateColumn>(
        prefix + "num_services_hard_ok",
        "The number of the host's services with the hard state OK",
        indirect_offset, extra_offset, -1, DANGEROUS_OFFSETOF(host, services),
        table->core(), ServiceListStateColumn::Type::num_hard_ok));
    table->addColumn(std::make_unique<ServiceListStateColumn>(
        prefix + "num_services_hard_warn",
        "The number of the host's services with the hard state WARN",
        indirect_offset, extra_offset, -1, DANGEROUS_OFFSETOF(host, services),
        table->core(), ServiceListStateColumn::Type::num_hard_warn));
    table->addColumn(std::make_unique<ServiceListStateColumn>(
        prefix + "num_services_hard_crit",
        "The number of the host's services with the hard state CRIT",
        indirect_offset, extra_offset, -1, DANGEROUS_OFFSETOF(host, services),
        table->core(), ServiceListStateColumn::Type::num_hard_crit));
    table->addColumn(std::make_unique<ServiceListStateColumn>(
        prefix + "num_services_hard_unknown",
        "The number of the host's services with the hard state UNKNOWN",
        indirect_offset, extra_offset, -1, DANGEROUS_OFFSETOF(host, services),
        table->core(), ServiceListStateColumn::Type::num_hard_unknown));

    table->addColumn(std::make_unique<HostSpecialIntColumn>(
        prefix + "hard_state",
        "The effective hard state of the host (eliminates a problem in hard_state)",
        indirect_offset, extra_offset, -1, 0, table->core(),
        HostSpecialIntColumn::Type::real_hard_state));
    table->addColumn(std::make_unique<HostSpecialIntColumn>(
        prefix + "pnpgraph_present",
        "Whether there is a PNP4Nagios graph present for this host (-1/0/1)",
        indirect_offset, extra_offset, -1, 0, table->core(),
        HostSpecialIntColumn::Type::pnp_graph_present));
    table->addColumn(std::make_unique<HostSpecialIntColumn>(
        prefix + "mk_inventory_last",
        "The timestamp of the last Check_MK HW/SW-Inventory for this host. 0 means that no inventory data is present",
        indirect_offset, extra_offset, -1, 0, table->core(),
        HostSpecialIntColumn::Type::mk_inventory_last));
    table->addColumn(std::make_unique<HostFileColumn>(
        prefix + "mk_inventory",
        "The file content of the Check_MK HW/SW-Inventory", indirect_offset,
        extra_offset, -1, 0, [mc]() { return mc->mkInventoryPath(); }, ""));
    table->addColumn(std::make_unique<HostFileColumn>(
        prefix + "mk_inventory_gz",
        "The gzipped file content of the Check_MK HW/SW-Inventory",
        indirect_offset, extra_offset, -1, 0,
        [mc]() { return mc->mkInventoryPath(); }, ".gz"));
    table->addColumn(std::make_unique<HostFileColumn>(
        prefix + "structured_status",
        "The file content of the structured status of the Check_MK HW/SW-Inventory",
        indirect_offset, extra_offset, -1, 0,
        [mc]() { return mc->structuredStatusPath(); }, ""));

    table->addColumn(std::make_unique<LogwatchListColumn>(
        prefix + "mk_logwatch_files",
        "This list of logfiles with problems fetched via mk_logwatch",
        indirect_offset, extra_offset, -1, 0, table->core()));

    table->addDynamicColumn(std::make_unique<DynamicLogwatchFileColumn>(
        prefix + "mk_logwatch_file",
        "This contents of a logfile fetched via mk_logwatch", table->core(),
        indirect_offset, extra_offset, -1));

    table->addColumn(std::make_unique<HostSpecialDoubleColumn>(
        prefix + "staleness", "Staleness indicator for this host",
        indirect_offset, extra_offset, -1, 0,
        HostSpecialDoubleColumn::Type::staleness));

    table->addColumn(std::make_unique<HostGroupsColumn>(
        prefix + "groups", "A list of all host groups this host is in",
        indirect_offset, extra_offset, -1,
        DANGEROUS_OFFSETOF(host, hostgroups_ptr), table->core()));
    table->addColumn(std::make_unique<ContactGroupsColumn>(
        prefix + "contact_groups",
        "A list of all contact groups this host is in", indirect_offset,
        extra_offset, -1, DANGEROUS_OFFSETOF(host, contact_groups)));

    table->addColumn(std::make_unique<ServiceListColumn>(
        prefix + "services", "A list of all services of the host",
        indirect_offset, extra_offset, -1, DANGEROUS_OFFSETOF(host, services),
        table->core(), 0));
    table->addColumn(std::make_unique<ServiceListColumn>(
        prefix + "services_with_state",
        "A list of all services of the host together with state and has_been_checked",
        indirect_offset, extra_offset, -1, DANGEROUS_OFFSETOF(host, services),
        table->core(), 1));
    table->addColumn(std::make_unique<ServiceListColumn>(
        prefix + "services_with_info",
        "A list of all services including detailed information about each service",
        indirect_offset, extra_offset, -1, DANGEROUS_OFFSETOF(host, services),
        table->core(), 2));
    table->addColumn(std::make_unique<ServiceListColumn>(
        prefix + "services_with_fullstate",
        "A list of all services including full state information. The list of entries can grow in future versions.",
        indirect_offset, extra_offset, -1, DANGEROUS_OFFSETOF(host, services),
        table->core(), 3));

    table->addColumn(std::make_unique<MetricsColumn>(
        prefix + "metrics",
        "A dummy column in order to be compatible with Check_MK Multisite",
        indirect_offset, extra_offset, -1, 0));
}

void TableHosts::answerQuery(Query *query) {
    // do we know the host group?
    if (auto value = query->stringValueRestrictionFor("groups")) {
        Debug(logger()) << "using host group index with '" << *value << "'";
        if (hostgroup *hg =
                find_hostgroup(const_cast<char *>(value->c_str()))) {
            for (hostsmember *mem = hg->members; mem != nullptr;
                 mem = mem->next) {
                if (!query->processDataset(Row(mem->host_ptr))) {
                    break;
                }
            }
        }
        return;
    }

    // no index -> linear search over all hosts
    Debug(logger()) << "using full table scan";
    for (host *hst = host_list; hst != nullptr; hst = hst->next) {
        if (!query->processDataset(Row(hst))) {
            break;
        }
    }
}
bool TableHosts::isAuthorized(Row row, const contact *ctc) const {
    return is_authorized_for(core(), ctc, rowData<host>(row), nullptr);
}

Row TableHosts::findObject(const std::string &objectspec) const {
    return Row(core()->find_host(objectspec));
}
