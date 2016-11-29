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
#include "AttributeListAsIntColumn.h"
#include "AttributeListColumn.h"
#include "ContactGroupsColumn.h"
#include "CustomTimeperiodColumn.h"
#include "CustomVarsDictColumn.h"
#include "CustomVarsExplicitColumn.h"
#include "CustomVarsNamesColumn.h"
#include "CustomVarsValuesColumn.h"
#include "DownCommColumn.h"
#include "DynamicLogwatchFileColumn.h"
#include "HostContactsColumn.h"
#include "HostFileColumn.h"
#include "HostGroupsColumn.h"
#include "HostListColumn.h"
#include "HostSpecialDoubleColumn.h"
#include "HostSpecialIntColumn.h"
#include "LogwatchListColumn.h"
#include "MetricsColumn.h"
#include "MonitoringCore.h"
#include "OffsetDoubleColumn.h"
#include "OffsetIntColumn.h"
#include "OffsetPerfdataColumn.h"
#include "OffsetStringColumn.h"
#include "OffsetStringHostMacroColumn.h"
#include "OffsetTimeColumn.h"
#include "OffsetTimeperiodColumn.h"
#include "Query.h"
#include "ServiceListColumn.h"
#include "ServiceListStateColumn.h"
#include "auth.h"

extern host *host_list;
extern char g_mk_inventory_path[];

using std::make_unique;
using std::string;

TableHosts::TableHosts(const DowntimesOrComments &downtimes_holder,
                       const DowntimesOrComments &comments_holder,
                       MonitoringCore *core)
    : Table(core->loggerLivestatus()) {
    addColumns(this, "", -1, -1, downtimes_holder, comments_holder, core);
}

string TableHosts::name() const { return "hosts"; }

string TableHosts::namePrefix() const { return "host_"; }

// static
void TableHosts::addColumns(Table *table, const string &prefix,
                            int indirect_offset, int extra_offset,
                            const DowntimesOrComments &downtimes_holder,
                            const DowntimesOrComments &comments_holder,
                            MonitoringCore *core) {
    host hst;
    char *ref = reinterpret_cast<char *>(&hst);
    table->addColumn(make_unique<OffsetStringColumn>(
        prefix + "name", "Host name", reinterpret_cast<char *>(&hst.name) - ref,
        indirect_offset, extra_offset));
    table->addColumn(make_unique<OffsetStringColumn>(
        prefix + "display_name",
        "Optional display name of the host - not used by Nagios' web interface",
        reinterpret_cast<char *>(&hst.display_name) - ref, indirect_offset,
        extra_offset));
    table->addColumn(make_unique<OffsetStringColumn>(
        prefix + "alias", "An alias name for the host",
        reinterpret_cast<char *>(&hst.alias) - ref, indirect_offset,
        extra_offset));
    table->addColumn(make_unique<OffsetStringColumn>(
        prefix + "address", "IP address",
        reinterpret_cast<char *>(&hst.address) - ref, indirect_offset,
        extra_offset));
#ifdef NAGIOS4
    table->addColumn(make_unique<OffsetStringColumn>(
        prefix + "check_command",
        "Nagios command for active host check of this host",
        (char *)(&hst.check_command) - ref, indirect_offset, extra_offset));
    table->addColumn(make_unique<OffsetStringHostMacroColumn>(
        prefix + "check_command_expanded",
        "Nagios command for active host check of this host with the macros "
        "expanded",
        (char *)(&hst.check_command) - ref, indirect_offset, extra_offset));
#else
    table->addColumn(make_unique<OffsetStringColumn>(
        prefix + "check_command",
        "Nagios command for active host check of this host",
        reinterpret_cast<char *>(&hst.host_check_command) - ref,
        indirect_offset, extra_offset));
    table->addColumn(make_unique<OffsetStringHostMacroColumn>(
        prefix + "check_command_expanded",
        "Nagios command for active host check "
        "of this host with the macros expanded",
        reinterpret_cast<char *>(&hst.host_check_command) - ref,
        indirect_offset, extra_offset));
#endif
    table->addColumn(make_unique<OffsetStringColumn>(
        prefix + "event_handler", "Nagios command used as event handler",
        reinterpret_cast<char *>(&hst.event_handler) - ref, indirect_offset,
        extra_offset));
    table->addColumn(make_unique<OffsetStringColumn>(
        prefix + "notification_period",
        "Time period in which problems of this host will be notified. If empty "
        "then notification will be always",
        reinterpret_cast<char *>(&hst.notification_period) - ref,
        indirect_offset, extra_offset));
    table->addColumn(make_unique<OffsetStringColumn>(
        prefix + "check_period",
        "Time period in which this host will be checked. If empty then the "
        "host will always be checked.",
        reinterpret_cast<char *>(&hst.check_period) - ref, indirect_offset,
        extra_offset));
    table->addColumn(make_unique<CustomVarsExplicitColumn>(
        prefix + "service_period", "The name of the service period of the host",
        reinterpret_cast<char *>(&hst.custom_variables) - ref, indirect_offset,
        "SERVICE_PERIOD", extra_offset));
    table->addColumn(make_unique<OffsetStringColumn>(
        prefix + "notes", "Optional notes for this host",
        reinterpret_cast<char *>(&hst.notes) - ref, indirect_offset,
        extra_offset));
    table->addColumn(make_unique<OffsetStringHostMacroColumn>(
        prefix + "notes_expanded",
        "The same as notes, but with the most important macros expanded",
        reinterpret_cast<char *>(&hst.notes) - ref, indirect_offset,
        extra_offset));
    table->addColumn(make_unique<OffsetStringColumn>(
        prefix + "notes_url",
        "An optional URL with further information about the host",
        reinterpret_cast<char *>(&hst.notes_url) - ref, indirect_offset,
        extra_offset));
    table->addColumn(make_unique<OffsetStringHostMacroColumn>(
        prefix + "notes_url_expanded",
        "Same es notes_url, but with the most important macros expanded",
        reinterpret_cast<char *>(&hst.notes_url) - ref, indirect_offset,
        extra_offset));
    table->addColumn(make_unique<OffsetStringColumn>(
        prefix + "action_url",
        "An optional URL to custom actions or information about this host",
        reinterpret_cast<char *>(&hst.action_url) - ref, indirect_offset,
        extra_offset));
    table->addColumn(make_unique<OffsetStringHostMacroColumn>(
        prefix + "action_url_expanded",
        "The same as action_url, but with the most important macros expanded",
        reinterpret_cast<char *>(&hst.action_url) - ref, indirect_offset,
        extra_offset));
    table->addColumn(make_unique<OffsetStringColumn>(
        prefix + "plugin_output", "Output of the last host check",
        reinterpret_cast<char *>(&hst.plugin_output) - ref, indirect_offset,
        extra_offset));
    table->addColumn(make_unique<OffsetPerfdataColumn>(
        prefix + "perf_data",
        "Optional performance data of the last host check",
        reinterpret_cast<char *>(&hst.perf_data) - ref, indirect_offset,
        extra_offset));
    table->addColumn(make_unique<OffsetStringColumn>(
        prefix + "icon_image",
        "The name of an image file to be used in the web pages",
        reinterpret_cast<char *>(&hst.icon_image) - ref, indirect_offset,
        extra_offset));
    table->addColumn(make_unique<OffsetStringHostMacroColumn>(
        prefix + "icon_image_expanded",
        "The same as icon_image, but with the most important macros expanded",
        reinterpret_cast<char *>(&hst.icon_image) - ref, indirect_offset,
        extra_offset));
    table->addColumn(make_unique<OffsetStringColumn>(
        prefix + "icon_image_alt", "Alternative text for the icon_image",
        reinterpret_cast<char *>(&hst.icon_image_alt) - ref, indirect_offset,
        extra_offset));
    table->addColumn(make_unique<OffsetStringColumn>(
        prefix + "statusmap_image",
        "The name of in image file for the status map",
        reinterpret_cast<char *>(&hst.statusmap_image) - ref, indirect_offset,
        extra_offset));
    table->addColumn(make_unique<OffsetStringColumn>(
        prefix + "long_plugin_output", "Complete output from check plugin",
        reinterpret_cast<char *>(&hst.long_plugin_output) - ref,
        indirect_offset, extra_offset));

    table->addColumn(make_unique<OffsetIntColumn>(
        prefix + "initial_state", "Initial host state",
        reinterpret_cast<char *>(&hst.initial_state) - ref, indirect_offset,
        extra_offset));
    table->addColumn(make_unique<OffsetIntColumn>(
        prefix + "max_check_attempts",
        "Max check attempts for active host checks",
        reinterpret_cast<char *>(&hst.max_attempts) - ref, indirect_offset,
        extra_offset));
    table->addColumn(make_unique<OffsetIntColumn>(
        prefix + "flap_detection_enabled",
        "Whether flap detection is enabled (0/1)",
        reinterpret_cast<char *>(&hst.flap_detection_enabled) - ref,
        indirect_offset, extra_offset));
    table->addColumn(make_unique<OffsetIntColumn>(
        prefix + "check_freshness",
        "Whether freshness checks are activated (0/1)",
        reinterpret_cast<char *>(&hst.check_freshness) - ref, indirect_offset,
        extra_offset));
    table->addColumn(make_unique<OffsetIntColumn>(
        prefix + "process_performance_data",
        "Whether processing of performance data is enabled (0/1)",
        reinterpret_cast<char *>(&hst.process_performance_data) - ref,
        indirect_offset, extra_offset));
#ifndef NAGIOS4
    table->addColumn(make_unique<OffsetIntColumn>(
        prefix + "accept_passive_checks",
        "Whether passive host checks are accepted (0/1)",
        reinterpret_cast<char *>(&hst.accept_passive_host_checks) - ref,
        indirect_offset, extra_offset));
#else
    table->addColumn(
        new OffsetIntColumn(prefix + "accept_passive_checks",
                            "Whether passive host checks are accepted (0/1)",
                            (char *)(&hst.accept_passive_checks) - ref,
                            indirect_offset, extra_offset));
#endif  // NAGIOS4
    table->addColumn(make_unique<OffsetIntColumn>(
        prefix + "event_handler_enabled",
        "Whether event handling is enabled (0/1)",
        reinterpret_cast<char *>(&hst.event_handler_enabled) - ref,
        indirect_offset, extra_offset));
    table->addColumn(make_unique<OffsetIntColumn>(
        prefix + "acknowledgement_type",
        "Type of acknowledgement (0: none, 1: normal, 2: stick)",
        reinterpret_cast<char *>(&hst.acknowledgement_type) - ref,
        indirect_offset, extra_offset));
    table->addColumn(make_unique<OffsetIntColumn>(
        prefix + "check_type", "Type of check (0: active, 1: passive)",
        reinterpret_cast<char *>(&hst.check_type) - ref, indirect_offset,
        extra_offset));
    table->addColumn(make_unique<OffsetIntColumn>(
        prefix + "last_state", "State before last state change",
        reinterpret_cast<char *>(&hst.last_state) - ref, indirect_offset,
        extra_offset));
    table->addColumn(make_unique<OffsetIntColumn>(
        prefix + "last_hard_state", "Last hard state",
        reinterpret_cast<char *>(&hst.last_hard_state) - ref, indirect_offset,
        extra_offset));
    table->addColumn(make_unique<OffsetIntColumn>(
        prefix + "current_attempt", "Number of the current check attempts",
        reinterpret_cast<char *>(&hst.current_attempt) - ref, indirect_offset,
        extra_offset));
#ifndef NAGIOS4
    table->addColumn(make_unique<OffsetTimeColumn>(
        prefix + "last_notification",
        "Time of the last notification (Unix timestamp)",
        reinterpret_cast<char *>(&hst.last_host_notification) - ref,
        indirect_offset, extra_offset));
    table->addColumn(make_unique<OffsetTimeColumn>(
        prefix + "next_notification",
        "Time of the next notification (Unix timestamp)",
        reinterpret_cast<char *>(&hst.next_host_notification) - ref,
        indirect_offset, extra_offset));
#else
    table->addColumn(make_unique<OffsetTimeColumn>(
        prefix + "last_notification",
        "Time of the last notification (Unix timestamp)",
        (char *)(&hst.last_notification) - ref, indirect_offset, extra_offset));
    table->addColumn(make_unique<OffsetTimeColumn>(
        prefix + "next_notification",
        "Time of the next notification (Unix timestamp)",
        (char *)(&hst.next_notification) - ref, indirect_offset, extra_offset));
#endif  // NAGIOS4
    table->addColumn(make_unique<OffsetTimeColumn>(
        prefix + "next_check",
        "Scheduled time for the next check (Unix timestamp)",
        reinterpret_cast<char *>(&hst.next_check) - ref, indirect_offset,
        extra_offset));
    table->addColumn(make_unique<OffsetTimeColumn>(
        prefix + "last_hard_state_change",
        "Time of the last hard state change (Unix timestamp)",
        reinterpret_cast<char *>(&hst.last_hard_state_change) - ref,
        indirect_offset, extra_offset));
    table->addColumn(make_unique<OffsetIntColumn>(
        prefix + "has_been_checked",
        "Whether the host has already been checked (0/1)",
        reinterpret_cast<char *>(&hst.has_been_checked) - ref, indirect_offset,
        extra_offset));
    table->addColumn(make_unique<OffsetIntColumn>(
        prefix + "current_notification_number",
        "Number of the current notification",
        reinterpret_cast<char *>(&hst.current_notification_number) - ref,
        indirect_offset, extra_offset));
    table->addColumn(make_unique<OffsetIntColumn>(
        prefix + "pending_flex_downtime",
        "Whether a flex downtime is pending (0/1)",
        reinterpret_cast<char *>(&hst.pending_flex_downtime) - ref,
        indirect_offset, extra_offset));
    table->addColumn(make_unique<OffsetIntColumn>(
        prefix + "total_services", "The total number of services of the host",
        reinterpret_cast<char *>(&hst.total_services) - ref, indirect_offset,
        extra_offset));
    // Note: this is redundant with "active_checks_enabled". Nobody noted this
    // before...
    table->addColumn(make_unique<OffsetIntColumn>(
        prefix + "checks_enabled",
        "Whether checks of the host are enabled (0/1)",
        reinterpret_cast<char *>(&hst.checks_enabled) - ref, indirect_offset,
        extra_offset));
    table->addColumn(make_unique<OffsetIntColumn>(
        prefix + "notifications_enabled",
        "Whether notifications of the host are enabled (0/1)",
        reinterpret_cast<char *>(&hst.notifications_enabled) - ref,
        indirect_offset, extra_offset));
    table->addColumn(make_unique<OffsetIntColumn>(
        prefix + "acknowledged",
        "Whether the current host problem has been acknowledged (0/1)",
        reinterpret_cast<char *>(&hst.problem_has_been_acknowledged) - ref,
        indirect_offset, extra_offset));
    table->addColumn(make_unique<OffsetIntColumn>(
        prefix + "state",
        "The current state of the host (0: up, 1: down, 2: unreachable)",
        reinterpret_cast<char *>(&hst.current_state) - ref, indirect_offset,
        extra_offset));
    table->addColumn(make_unique<OffsetIntColumn>(
        prefix + "state_type", "Type of the current state (0: soft, 1: hard)",
        reinterpret_cast<char *>(&hst.state_type) - ref, indirect_offset,
        extra_offset));
    table->addColumn(make_unique<OffsetIntColumn>(
        prefix + "no_more_notifications",
        "Whether to stop sending notifications (0/1)",
        reinterpret_cast<char *>(&hst.no_more_notifications) - ref,
        indirect_offset, extra_offset));
    table->addColumn(make_unique<OffsetIntColumn>(
        prefix + "check_flapping_recovery_notification",
        "Whether to check to send a recovery notification when flapping stops "
        "(0/1)",
        reinterpret_cast<char *>(&hst.check_flapping_recovery_notification) -
            ref,
        indirect_offset, extra_offset));
    table->addColumn(make_unique<OffsetTimeColumn>(
        prefix + "last_check", "Time of the last check (Unix timestamp)",
        reinterpret_cast<char *>(&hst.last_check) - ref, indirect_offset,
        extra_offset));
    table->addColumn(make_unique<OffsetTimeColumn>(
        prefix + "last_state_change",
        "Time of the last state change - soft or hard (Unix timestamp)",
        reinterpret_cast<char *>(&hst.last_state_change) - ref, indirect_offset,
        extra_offset));

    table->addColumn(make_unique<OffsetTimeColumn>(
        prefix + "last_time_up",
        "The last time the host was UP (Unix timestamp)",
        reinterpret_cast<char *>(&hst.last_time_up) - ref, indirect_offset,
        extra_offset));
    table->addColumn(make_unique<OffsetTimeColumn>(
        prefix + "last_time_down",
        "The last time the host was DOWN (Unix timestamp)",
        reinterpret_cast<char *>(&hst.last_time_down) - ref, indirect_offset,
        extra_offset));
    table->addColumn(make_unique<OffsetTimeColumn>(
        prefix + "last_time_unreachable",
        "The last time the host was UNREACHABLE (Unix timestamp)",
        reinterpret_cast<char *>(&hst.last_time_unreachable) - ref,
        indirect_offset, extra_offset));

    table->addColumn(make_unique<OffsetIntColumn>(
        prefix + "is_flapping", "Whether the host state is flapping (0/1)",
        reinterpret_cast<char *>(&hst.is_flapping) - ref, indirect_offset,
        extra_offset));
    table->addColumn(make_unique<OffsetIntColumn>(
        prefix + "scheduled_downtime_depth",
        "The number of downtimes this host is currently in",
        reinterpret_cast<char *>(&hst.scheduled_downtime_depth) - ref,
        indirect_offset, extra_offset));
    table->addColumn(make_unique<OffsetIntColumn>(
        prefix + "is_executing",
        "is there a host check currently running... (0/1)",
        reinterpret_cast<char *>(&hst.is_executing) - ref, indirect_offset,
        extra_offset));
    table->addColumn(make_unique<OffsetIntColumn>(
        prefix + "active_checks_enabled",
        "Whether active checks are enabled for the host (0/1)",
        reinterpret_cast<char *>(&hst.checks_enabled) - ref, indirect_offset,
        extra_offset));
    table->addColumn(make_unique<OffsetIntColumn>(
        prefix + "check_options",
        "The current check option, forced, normal, freshness... (0-2)",
        reinterpret_cast<char *>(&hst.check_options) - ref, indirect_offset,
        extra_offset));
#ifndef NAGIOS4
    table->addColumn(make_unique<OffsetIntColumn>(
        prefix + "obsess_over_host",
        "The current obsess_over_host setting... (0/1)",
        reinterpret_cast<char *>(&hst.obsess_over_host) - ref, indirect_offset,
        extra_offset));
#else
    table->addColumn(make_unique<OffsetIntColumn>(
        prefix + "obsess_over_host",
        "The current obsess_over_host setting... (0/1)",
        (char *)(&hst.obsess) - ref, indirect_offset, extra_offset));
#endif  // NAGIOS4
    table->addColumn(make_unique<AttributeListAsIntColumn>(
        prefix + "modified_attributes",
        "A bitmask specifying which attributes have been modified",
        reinterpret_cast<char *>(&hst.modified_attributes) - ref,
        indirect_offset, extra_offset, -1));
    table->addColumn(make_unique<AttributeListColumn>(
        prefix + "modified_attributes_list",
        "A list of all modified attributes",
        reinterpret_cast<char *>(&hst.modified_attributes) - ref,
        indirect_offset, extra_offset, -1));

    // columns of type double
    table->addColumn(make_unique<OffsetDoubleColumn>(
        prefix + "check_interval",
        "Number of basic interval lengths between two scheduled checks of the "
        "host",
        reinterpret_cast<char *>(&hst.check_interval) - ref, indirect_offset,
        extra_offset));
    table->addColumn(make_unique<OffsetDoubleColumn>(
        prefix + "retry_interval",
        "Number of basic interval lengths between checks when retrying after a "
        "soft error",
        reinterpret_cast<char *>(&hst.retry_interval) - ref, indirect_offset,
        extra_offset));
    table->addColumn(make_unique<OffsetDoubleColumn>(
        prefix + "notification_interval",
        "Interval of periodic notification or 0 if its off",
        reinterpret_cast<char *>(&hst.notification_interval) - ref,
        indirect_offset, extra_offset));
    table->addColumn(make_unique<OffsetDoubleColumn>(
        prefix + "first_notification_delay",
        "Delay before the first notification",
        reinterpret_cast<char *>(&hst.first_notification_delay) - ref,
        indirect_offset, extra_offset));
    table->addColumn(make_unique<OffsetDoubleColumn>(
        prefix + "low_flap_threshold", "Low threshold of flap detection",
        reinterpret_cast<char *>(&hst.low_flap_threshold) - ref,
        indirect_offset, extra_offset));
    table->addColumn(make_unique<OffsetDoubleColumn>(
        prefix + "high_flap_threshold", "High threshold of flap detection",
        reinterpret_cast<char *>(&hst.high_flap_threshold) - ref,
        indirect_offset, extra_offset));
    table->addColumn(make_unique<OffsetDoubleColumn>(
        prefix + "x_3d", "3D-Coordinates: X",
        reinterpret_cast<char *>(&hst.x_3d) - ref, indirect_offset,
        extra_offset));
    table->addColumn(make_unique<OffsetDoubleColumn>(
        prefix + "y_3d", "3D-Coordinates: Y",
        reinterpret_cast<char *>(&hst.y_3d) - ref, indirect_offset,
        extra_offset));
    table->addColumn(make_unique<OffsetDoubleColumn>(
        prefix + "z_3d", "3D-Coordinates: Z",
        reinterpret_cast<char *>(&hst.z_3d) - ref, indirect_offset,
        extra_offset));
    table->addColumn(make_unique<OffsetDoubleColumn>(
        prefix + "latency",
        "Time difference between scheduled check time and actual check time",
        reinterpret_cast<char *>(&hst.latency) - ref, indirect_offset,
        extra_offset));
    table->addColumn(make_unique<OffsetDoubleColumn>(
        prefix + "execution_time", "Time the host check needed for execution",
        reinterpret_cast<char *>(&hst.execution_time) - ref, indirect_offset,
        extra_offset));
    table->addColumn(make_unique<OffsetDoubleColumn>(
        prefix + "percent_state_change", "Percent state change",
        reinterpret_cast<char *>(&hst.percent_state_change) - ref,
        indirect_offset, extra_offset));

    table->addColumn(make_unique<OffsetTimeperiodColumn>(
        prefix + "in_notification_period",
        "Whether this host is currently in its notification period (0/1)",
        reinterpret_cast<char *>(&hst.notification_period_ptr) - ref,
        indirect_offset, extra_offset));
    table->addColumn(make_unique<OffsetTimeperiodColumn>(
        prefix + "in_check_period",
        "Whether this host is currently in its check period (0/1)",
        reinterpret_cast<char *>(&hst.check_period_ptr) - ref, indirect_offset,
        extra_offset));
    table->addColumn(make_unique<CustomTimeperiodColumn>(
        prefix + "in_service_period",
        "Whether this host is currently in its service period (0/1)",
        reinterpret_cast<char *>(&hst.custom_variables) - ref, indirect_offset,
        "SERVICE_PERIOD", extra_offset));

    table->addColumn(
        make_unique<HostContactsColumn>(prefix + "contacts",
                                        "A list of all contacts of this "
                                        "host, either direct or via a "
                                        "contact group",
                                        indirect_offset, extra_offset));
    table->addColumn(make_unique<DownCommColumn>(
        prefix + "downtimes",
        "A list of the ids of all scheduled downtimes of this host",
        indirect_offset, downtimes_holder, true, false, false, false,
        extra_offset));
    table->addColumn(make_unique<DownCommColumn>(
        prefix + "downtimes_with_info",
        "A list of the all scheduled downtimes of the host "
        "with id, author and comment",
        indirect_offset, downtimes_holder, true, false, true, false,
        extra_offset));
    table->addColumn(make_unique<DownCommColumn>(
        prefix + "comments", "A list of the ids of all comments of this host",
        indirect_offset, comments_holder, false, false, false, false,
        extra_offset));
    table->addColumn(make_unique<DownCommColumn>(
        prefix + "comments_with_info",
        "A list of all comments of the host with id, author and comment",
        indirect_offset, comments_holder, false, false, true, false,
        extra_offset));
    table->addColumn(make_unique<DownCommColumn>(
        prefix + "comments_with_extra_info",
        "A list of all comments of the host with id, "
        "author, comment, entry type and entry time",
        indirect_offset, comments_holder, false, false, true, true,
        extra_offset));

    table->addColumn(make_unique<CustomVarsNamesColumn>(
        prefix + "custom_variable_names",
        "A list of the names of all custom variables",
        reinterpret_cast<char *>(&hst.custom_variables) - ref, indirect_offset,
        extra_offset));
    table->addColumn(make_unique<CustomVarsValuesColumn>(
        prefix + "custom_variable_values",
        "A list of the values of the custom variables",
        reinterpret_cast<char *>(&hst.custom_variables) - ref, indirect_offset,
        extra_offset));
    table->addColumn(make_unique<CustomVarsDictColumn>(
        prefix + "custom_variables", "A dictionary of the custom variables",
        reinterpret_cast<char *>(&hst.custom_variables) - ref, indirect_offset,
        extra_offset));

    // Add direct access to the custom macro _FILENAME. In a future version of
    // Livestatus this will probably be configurable so access to further custom
    // variable can be added, such that those variables are presented like
    // ordinary Nagios columns.
    table->addColumn(make_unique<CustomVarsExplicitColumn>(
        prefix + "filename", "The value of the custom variable FILENAME",
        reinterpret_cast<char *>(&hst.custom_variables) - ref, indirect_offset,
        "FILENAME", extra_offset));

    table->addColumn(make_unique<HostListColumn>(
        prefix + "parents", "A list of all direct parents of the host",
        reinterpret_cast<char *>(&hst.parent_hosts) - ref, indirect_offset,
        false, extra_offset));
    table->addColumn(make_unique<HostListColumn>(
        prefix + "childs", "A list of all direct childs of the host",
        reinterpret_cast<char *>(&hst.child_hosts) - ref, indirect_offset,
        false, extra_offset));

    table->addColumn(make_unique<ServiceListStateColumn>(
        prefix + "num_services", "The total number of services of the host",
        SLSC_NUM, reinterpret_cast<char *>(&hst.services) - ref,
        indirect_offset, extra_offset));
    table->addColumn(make_unique<ServiceListStateColumn>(
        prefix + "worst_service_state",
        "The worst soft state of all of the host's services (OK <= WARN <= "
        "UNKNOWN <= CRIT)",
        SLSC_WORST_STATE, reinterpret_cast<char *>(&hst.services) - ref,
        indirect_offset, extra_offset));
    table->addColumn(make_unique<ServiceListStateColumn>(
        prefix + "num_services_ok",
        "The number of the host's services with the soft state OK", SLSC_NUM_OK,
        reinterpret_cast<char *>(&hst.services) - ref, indirect_offset,
        extra_offset));
    table->addColumn(make_unique<ServiceListStateColumn>(
        prefix + "num_services_warn",
        "The number of the host's services with the soft state WARN",
        SLSC_NUM_WARN, reinterpret_cast<char *>(&hst.services) - ref,
        indirect_offset, extra_offset));
    table->addColumn(make_unique<ServiceListStateColumn>(
        prefix + "num_services_crit",
        "The number of the host's services with the soft state CRIT",
        SLSC_NUM_CRIT, reinterpret_cast<char *>(&hst.services) - ref,
        indirect_offset, extra_offset));
    table->addColumn(make_unique<ServiceListStateColumn>(
        prefix + "num_services_unknown",
        "The number of the host's services with the soft state UNKNOWN",
        SLSC_NUM_UNKNOWN, reinterpret_cast<char *>(&hst.services) - ref,
        indirect_offset, extra_offset));
    table->addColumn(make_unique<ServiceListStateColumn>(
        prefix + "num_services_pending",
        "The number of the host's services which have not been checked yet "
        "(pending)",
        SLSC_NUM_PENDING, reinterpret_cast<char *>(&hst.services) - ref,
        indirect_offset, extra_offset));
    table->addColumn(make_unique<ServiceListStateColumn>(
        prefix + "worst_service_hard_state",
        "The worst hard state of all of the host's services (OK <= WARN <= "
        "UNKNOWN <= CRIT)",
        SLSC_WORST_HARD_STATE, reinterpret_cast<char *>(&hst.services) - ref,
        indirect_offset, extra_offset));
    table->addColumn(make_unique<ServiceListStateColumn>(
        prefix + "num_services_hard_ok",
        "The number of the host's services with the hard state OK",
        SLSC_NUM_HARD_OK, reinterpret_cast<char *>(&hst.services) - ref,
        indirect_offset, extra_offset));
    table->addColumn(make_unique<ServiceListStateColumn>(
        prefix + "num_services_hard_warn",
        "The number of the host's services with the hard state WARN",
        SLSC_NUM_HARD_WARN, reinterpret_cast<char *>(&hst.services) - ref,
        indirect_offset, extra_offset));
    table->addColumn(make_unique<ServiceListStateColumn>(
        prefix + "num_services_hard_crit",
        "The number of the host's services with the hard state CRIT",
        SLSC_NUM_HARD_CRIT, reinterpret_cast<char *>(&hst.services) - ref,
        indirect_offset, extra_offset));
    table->addColumn(make_unique<ServiceListStateColumn>(
        prefix + "num_services_hard_unknown",
        "The number of the host's services with the hard state UNKNOWN",
        SLSC_NUM_HARD_UNKNOWN, reinterpret_cast<char *>(&hst.services) - ref,
        indirect_offset, extra_offset));

    table->addColumn(make_unique<HostSpecialIntColumn>(
        prefix + "hard_state",
        "The effective hard state of the host (eliminates a problem in "
        "hard_state)",
        HSIC_REAL_HARD_STATE, indirect_offset, extra_offset));
    table->addColumn(make_unique<HostSpecialIntColumn>(
        prefix + "pnpgraph_present",
        "Whether there is a PNP4Nagios graph present for this host (-1/0/1)",
        HSIC_PNP_GRAPH_PRESENT, indirect_offset, extra_offset));
    table->addColumn(make_unique<HostSpecialIntColumn>(
        prefix + "mk_inventory_last",
        "The timestamp of the last Check_MK HW/SW-Inventory for this host. 0 "
        "means that no inventory data is present",
        HSIC_MK_INVENTORY_LAST, indirect_offset, extra_offset));
    table->addColumn(make_unique<HostFileColumn>(
        prefix + "mk_inventory",
        "The file content content of the Check_MK HW/SW-Inventory",
        g_mk_inventory_path, "", false, indirect_offset, extra_offset));
    table->addColumn(make_unique<HostFileColumn>(
        prefix + "mk_inventory_gz",
        "The gzipped file content content of the Check_MK HW/SW-Inventory",
        g_mk_inventory_path, ".gz", false, indirect_offset, extra_offset));

    extern char g_mk_logwatch_path[];
    table->addColumn(make_unique<LogwatchListColumn>(
        prefix + "mk_logwatch_files",
        "This list of logfiles with problems fetched via mk_logwatch",
        indirect_offset, extra_offset, g_mk_logwatch_path));

    table->addDynamicColumn(make_unique<DynamicLogwatchFileColumn>(
        prefix + "mk_logwatch_file",
        "This contents of a logfile fetched via mk_logwatch", indirect_offset,
        extra_offset, table->_logger, g_mk_logwatch_path));

    table->addColumn(make_unique<HostSpecialDoubleColumn>(
        prefix + "staleness", "Staleness indicator for this host",
        HSDC_STALENESS, indirect_offset, extra_offset));

    table->addColumn(make_unique<HostGroupsColumn>(
        prefix + "groups", "A list of all host groups this host is in",
        reinterpret_cast<char *>(&hst.hostgroups_ptr) - ref, indirect_offset,
        extra_offset));
    table->addColumn(make_unique<ContactGroupsColumn>(
        prefix + "contact_groups",
        "A list of all contact groups this host is in",
        reinterpret_cast<char *>(&hst.contact_groups) - ref, indirect_offset,
        extra_offset, core));

    table->addColumn(make_unique<ServiceListColumn>(
        prefix + "services", "A list of all services of the host",
        reinterpret_cast<char *>(&hst.services) - ref, indirect_offset, false,
        0, extra_offset));
    table->addColumn(make_unique<ServiceListColumn>(
        prefix + "services_with_state",
        "A list of all services of the host together with state and "
        "has_been_checked",
        reinterpret_cast<char *>(&hst.services) - ref, indirect_offset, false,
        1, extra_offset));
    table->addColumn(make_unique<ServiceListColumn>(
        prefix + "services_with_info",
        "A list of all services including detailed information about each "
        "service",
        reinterpret_cast<char *>(&hst.services) - ref, indirect_offset, false,
        2, extra_offset));
    table->addColumn(make_unique<ServiceListColumn>(
        prefix + "services_with_fullstate",
        "A list of all services including full state information. The list of "
        "entries can grow in future versions.",
        reinterpret_cast<char *>(&hst.services) - ref, indirect_offset, false,
        3, extra_offset));

    table->addColumn(make_unique<MetricsColumn>(
        prefix + "metrics",
        "A dummy column in order to be compatible with Check_MK Multisite",
        indirect_offset, extra_offset));
}

void TableHosts::answerQuery(Query *query) {
    // do we know the host group?
    if (const string *value = query->findValueForIndexing("groups")) {
        if (hostgroup *hg =
                find_hostgroup(const_cast<char *>(value->c_str()))) {
            for (hostsmember *mem = hg->members; mem != nullptr;
                 mem = mem->next) {
                if (!query->processDataset(mem->host_ptr)) {
                    break;
                }
            }
        }
        return;
    }

    // no index -> linear search over all hosts
    for (host *hst = host_list; hst != nullptr; hst = hst->next) {
        if (!query->processDataset(hst)) {
            break;
        }
    }
}
bool TableHosts::isAuthorized(contact *ctc, void *data) {
    return is_authorized_for(ctc, static_cast<host *>(data), nullptr);
}

void *TableHosts::findObject(const string &objectspec) {
    return find_host(const_cast<char *>(objectspec.c_str()));
}
