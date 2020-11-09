// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "TableHosts.h"

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <filesystem>
#include <iterator>
#include <memory>
#include <optional>
#include <ostream>
#include <unordered_map>
#include <utility>
#include <vector>

#include "AttributeListAsIntColumn.h"
#include "AttributeListColumn.h"
#include "BoolLambdaColumn.h"
#include "Column.h"
#include "CommentColumn.h"
#include "ContactGroupsColumn.h"
#include "CustomVarsDictColumn.h"
#include "CustomVarsExplicitColumn.h"
#include "CustomVarsNamesColumn.h"
#include "CustomVarsValuesColumn.h"
#include "DoubleLambdaColumn.h"
#include "DowntimeColumn.h"
#include "DynamicColumn.h"
#include "DynamicFileColumn.h"
#include "DynamicRRDColumn.h"
#include "FileColumn.h"
#include "HostContactsColumn.h"
#include "HostGroupsColumn.h"
#include "HostListColumn.h"
#include "HostRRDColumn.h"
#include "HostSpecialDoubleColumn.h"
#include "HostSpecialIntColumn.h"
#include "IntLambdaColumn.h"
#include "ListLambdaColumn.h"
#include "Logger.h"
#include "LogwatchListColumn.h"
#include "MacroExpander.h"
#include "Metric.h"
#include "MonitoringCore.h"
#include "Query.h"
#include "ServiceListColumn.h"
#include "ServiceListStateColumn.h"
#include "StringLambdaColumn.h"
#include "StringPerfdataColumn.h"
#include "TimeLambdaColumn.h"
#include "TimeperiodsCache.h"
#include "auth.h"
#include "nagios.h"
#include "pnp4nagios.h"

extern host *host_list;
extern TimeperiodsCache *g_timeperiods_cache;

TableHosts::TableHosts(MonitoringCore *mc) : Table(mc) {
    addColumns(this, "", ColumnOffsets{});
}

std::string TableHosts::name() const { return "hosts"; }

std::string TableHosts::namePrefix() const { return "host_"; }

// static
void TableHosts::addColumns(Table *table, const std::string &prefix,
                            const ColumnOffsets &offsets) {
    auto offsets_custom_variables{offsets.add(
        [](Row r) { return &r.rawData<host>()->custom_variables; })};
    auto offsets_services{
        offsets.add([](Row r) { return &r.rawData<host>()->services; })};
    auto *mc = table->core();
    table->addColumn(std::make_unique<StringLambdaColumn<host>>(
        prefix + "name", "Host name", offsets,
        [](const host &r) { return r.name == nullptr ? "" : r.name; }));
    table->addColumn(std::make_unique<StringLambdaColumn<host>>(
        prefix + "display_name",
        "Optional display name of the host - not used by Nagios' web interface",
        offsets, [](const host &r) {
            return r.display_name == nullptr ? "" : r.display_name;
        }));
    table->addColumn(std::make_unique<StringLambdaColumn<host>>(
        prefix + "alias", "An alias name for the host", offsets,
        [](const host &r) { return r.alias == nullptr ? "" : r.alias; }));
    table->addColumn(std::make_unique<StringLambdaColumn<host>>(
        prefix + "address", "IP address", offsets,
        [](const host &r) { return r.address == nullptr ? "" : r.address; }));
#ifdef NAGIOS4
    table->addColumn(std::make_unique<StringLambdaColumn<host>>(
        prefix + "check_command",
        "Nagios command for active host check of this host", offsets,
        [](const host &r) {
            return r.check_command == nullptr ? "" : r.check_command;
        }));
    table->addColumn(std::make_unique<StringLambdaColumn<host>>(
        prefix + "check_command_expanded",
        "Nagios command for active host check of this host with the macros expanded",
        offsets, [mc](const host &r) {
            return HostMacroExpander::make(r, mc)->expandMacros(
                r.check_command);
        }));
#else
    table->addColumn(std::make_unique<StringLambdaColumn<host>>(
        prefix + "check_command",
        "Nagios command for active host check of this host", offsets,
        [](const host &r) {
            return r.host_check_command == nullptr ? "" : r.host_check_command;
        }));
    table->addColumn(std::make_unique<StringLambdaColumn<host>>(
        prefix + "check_command_expanded",
        "Nagios command for active host check of this host with the macros expanded",
        offsets, [mc](const host &r) {
            return HostMacroExpander::make(r, mc)->expandMacros(
                r.host_check_command);
        }));
#endif
    table->addColumn(std::make_unique<StringLambdaColumn<host>>(
        prefix + "event_handler", "Nagios command used as event handler",
        offsets, [](const host &r) {
            return r.event_handler == nullptr ? "" : r.event_handler;
        }));
    table->addColumn(std::make_unique<StringLambdaColumn<host>>(
        prefix + "notification_period",
        "Time period in which problems of this host will be notified. If empty then notification will be always",
        offsets, [](const host &r) {
            return r.notification_period == nullptr ? ""
                                                    : r.notification_period;
        }));
    table->addColumn(std::make_unique<StringLambdaColumn<host>>(
        prefix + "check_period",
        "Time period in which this host will be checked. If empty then the host will always be checked.",
        offsets, [](const host &r) {
            return r.check_period == nullptr ? "" : r.check_period;
        }));
    table->addColumn(std::make_unique<CustomVarsExplicitColumn>(
        prefix + "service_period", "The name of the service period of the host",
        offsets_custom_variables, table->core(), "SERVICE_PERIOD"));
    table->addColumn(std::make_unique<StringLambdaColumn<host>>(
        prefix + "notes", "Optional notes for this host", offsets,
        [](const host &r) { return r.notes == nullptr ? "" : r.notes; }));
    table->addColumn(std::make_unique<StringLambdaColumn<host>>(
        prefix + "notes_expanded",
        "The same as notes, but with the most important macros expanded",
        offsets, [mc](const host &r) {
            return HostMacroExpander::make(r, mc)->expandMacros(r.notes);
        }));
    table->addColumn(std::make_unique<StringLambdaColumn<host>>(
        prefix + "notes_url",
        "An optional URL with further information about the host", offsets,
        [](const host &r) {
            return r.notes_url == nullptr ? "" : r.notes_url;
        }));
    table->addColumn(std::make_unique<StringLambdaColumn<host>>(
        prefix + "notes_url_expanded",
        "Same es notes_url, but with the most important macros expanded",
        offsets, [mc](const host &r) {
            return HostMacroExpander::make(r, mc)->expandMacros(r.notes_url);
        }));
    table->addColumn(std::make_unique<StringLambdaColumn<host>>(
        prefix + "action_url",
        "An optional URL to custom actions or information about this host",
        offsets, [](const host &r) {
            return r.action_url == nullptr ? "" : r.action_url;
        }));
    table->addColumn(std::make_unique<StringLambdaColumn<host>>(
        prefix + "action_url_expanded",
        "The same as action_url, but with the most important macros expanded",
        offsets, [mc](const host &r) {
            return HostMacroExpander::make(r, mc)->expandMacros(r.action_url);
        }));
    table->addColumn(std::make_unique<StringLambdaColumn<host>>(
        prefix + "plugin_output", "Output of the last host check", offsets,
        [](const host &r) {
            return r.plugin_output == nullptr ? "" : r.plugin_output;
        }));
    table->addColumn(std::make_unique<StringPerfdataColumn<host>>(
        prefix + "perf_data",
        "Optional performance data of the last host check", offsets,
        [](const host &r) {
            return r.perf_data == nullptr ? "" : r.perf_data;
        }));
    table->addColumn(std::make_unique<StringLambdaColumn<host>>(
        prefix + "icon_image",
        "The name of an image file to be used in the web pages", offsets,
        [](const host &r) {
            return r.icon_image == nullptr ? "" : r.icon_image;
        }));
    table->addColumn(std::make_unique<StringLambdaColumn<host>>(
        prefix + "icon_image_expanded",
        "The same as icon_image, but with the most important macros expanded",
        offsets, [mc](const host &r) {
            return HostMacroExpander::make(r, mc)->expandMacros(r.icon_image);
        }));
    table->addColumn(std::make_unique<StringLambdaColumn<host>>(
        prefix + "icon_image_alt", "Alternative text for the icon_image",
        offsets, [](const host &r) {
            return r.icon_image_alt == nullptr ? "" : r.icon_image_alt;
        }));
    table->addColumn(std::make_unique<StringLambdaColumn<host>>(
        prefix + "statusmap_image",
        "The name of in image file for the status map", offsets,
        [](const host &r) {
            return r.statusmap_image == nullptr ? "" : r.statusmap_image;
        }));
    table->addColumn(std::make_unique<StringLambdaColumn<host>>(
        prefix + "long_plugin_output", "Complete output from check plugin",
        offsets, [](const host &r) {
            return r.long_plugin_output == nullptr ? "" : r.long_plugin_output;
        }));

    table->addColumn(std::make_unique<IntLambdaColumn<host>>(
        prefix + "initial_state", "Initial host state", offsets,
        [](const host &r) { return r.initial_state; }));
    table->addColumn(std::make_unique<IntLambdaColumn<host>>(
        prefix + "max_check_attempts",
        "Max check attempts for active host checks", offsets,
        [](const host &r) { return r.max_attempts; }));
    table->addColumn(std::make_unique<IntLambdaColumn<host>>(
        prefix + "flap_detection_enabled",
        "Whether flap detection is enabled (0/1)", offsets,
        [](const host &r) { return r.flap_detection_enabled; }));
    table->addColumn(std::make_unique<IntLambdaColumn<host>>(
        prefix + "check_freshness",
        "Whether freshness checks are activated (0/1)", offsets,
        [](const host &r) { return r.check_freshness; }));
    table->addColumn(std::make_unique<IntLambdaColumn<host>>(
        prefix + "process_performance_data",
        "Whether processing of performance data is enabled (0/1)", offsets,
        [](const host &r) { return r.process_performance_data; }));
#ifndef NAGIOS4
    table->addColumn(std::make_unique<IntLambdaColumn<host>>(
        prefix + "accept_passive_checks",
        "Whether passive host checks are accepted (0/1)", offsets,
        [](const host &r) { return r.accept_passive_host_checks; }));
#else
    table->addColumn(std::make_unique<IntLambdaColumn<host>>(
        prefix + "accept_passive_checks",
        "Whether passive host checks are accepted (0/1)", offsets,
        [](const host &r) { return r.accept_passive_checks; }));
#endif  // NAGIOS4
    table->addColumn(std::make_unique<IntLambdaColumn<host>>(
        prefix + "event_handler_enabled",
        "Whether event handling is enabled (0/1)", offsets,
        [](const host &r) { return r.event_handler_enabled; }));
    table->addColumn(std::make_unique<IntLambdaColumn<host>>(
        prefix + "acknowledgement_type",
        "Type of acknowledgement (0: none, 1: normal, 2: sticky)", offsets,
        [](const host &r) { return r.acknowledgement_type; }));
    table->addColumn(std::make_unique<IntLambdaColumn<host>>(
        prefix + "check_type", "Type of check (0: active, 1: passive)", offsets,
        [](const host &r) { return r.check_type; }));
    table->addColumn(std::make_unique<IntLambdaColumn<host>>(
        prefix + "last_state", "State before last state change", offsets,
        [](const host &r) { return r.last_state; }));
    table->addColumn(std::make_unique<IntLambdaColumn<host>>(
        prefix + "last_hard_state", "Last hard state", offsets,
        [](const host &r) { return r.last_hard_state; }));
    table->addColumn(std::make_unique<IntLambdaColumn<host>>(
        prefix + "current_attempt", "Number of the current check attempts",
        offsets, [](const host &r) { return r.current_attempt; }));
#ifndef NAGIOS4
    table->addColumn(std::make_unique<TimeLambdaColumn<host>>(
        prefix + "last_notification",
        "Time of the last notification (Unix timestamp)", offsets,
        [](const host &r) {
            return std::chrono::system_clock::from_time_t(
                r.last_host_notification);
        }));
    table->addColumn(std::make_unique<TimeLambdaColumn<host>>(
        prefix + "next_notification",
        "Time of the next notification (Unix timestamp)", offsets,
        [](const host &r) {
            return std::chrono::system_clock::from_time_t(
                r.next_host_notification);
        }));
#else
    table->addColumn(std::make_unique<TimeLambdaColumn<host>>(
        prefix + "last_notification",
        "Time of the last notification (Unix timestamp)", offsets,
        [](const host &r) {
            return std::chrono::system_clock::from_time_t(r.last_notification);
        }));
    table->addColumn(std::make_unique<TimeLambdaColumn<host>>(
        prefix + "next_notification",
        "Time of the next notification (Unix timestamp)", offsets,
        [](const host &r) {
            return std::chrono::system_clock::from_time_t(r.next_notification);
        }));
#endif  // NAGIOS4
    table->addColumn(std::make_unique<TimeLambdaColumn<host>>(
        prefix + "next_check",
        "Scheduled time for the next check (Unix timestamp)", offsets,
        [](const host &r) {
            return std::chrono::system_clock::from_time_t(r.next_check);
        }));
    table->addColumn(std::make_unique<TimeLambdaColumn<host>>(
        prefix + "last_hard_state_change",
        "Time of the last hard state change (Unix timestamp)", offsets,
        [](const host &r) {
            return std::chrono::system_clock::from_time_t(
                r.last_hard_state_change);
        }));
    table->addColumn(std::make_unique<IntLambdaColumn<host>>(
        prefix + "has_been_checked",
        "Whether the host has already been checked (0/1)", offsets,
        [](const host &r) { return r.has_been_checked; }));
    table->addColumn(std::make_unique<IntLambdaColumn<host>>(
        prefix + "current_notification_number",
        "Number of the current notification", offsets,
        [](const host &r) { return r.current_notification_number; }));
    table->addColumn(std::make_unique<IntLambdaColumn<host>>(
        prefix + "pending_flex_downtime",
        "Number of pending flexible downtimes", offsets,
        [](const host &r) { return r.pending_flex_downtime; }));
    table->addColumn(std::make_unique<IntLambdaColumn<host>>(
        prefix + "total_services", "The total number of services of the host",
        offsets, [](const host &r) { return r.total_services; }));
    // Note: this is redundant with "active_checks_enabled". Nobody noted this
    // before...
    table->addColumn(std::make_unique<IntLambdaColumn<host>>(
        prefix + "checks_enabled",
        "Whether checks of the host are enabled (0/1)", offsets,
        [](const host &r) { return r.checks_enabled; }));
    table->addColumn(std::make_unique<IntLambdaColumn<host>>(
        prefix + "notifications_enabled",
        "Whether notifications of the host are enabled (0/1)", offsets,
        [](const host &r) { return r.notifications_enabled; }));
    table->addColumn(std::make_unique<IntLambdaColumn<host>>(
        prefix + "acknowledged",
        "Whether the current host problem has been acknowledged (0/1)", offsets,
        [](const host &r) { return r.problem_has_been_acknowledged; }));
    table->addColumn(std::make_unique<IntLambdaColumn<host>>(
        prefix + "state",
        "The current state of the host (0: up, 1: down, 2: unreachable)",
        offsets, [](const host &r) { return r.current_state; }));
    table->addColumn(std::make_unique<IntLambdaColumn<host>>(
        prefix + "state_type", "Type of the current state (0: soft, 1: hard)",
        offsets, [](const host &r) { return r.state_type; }));
    table->addColumn(std::make_unique<IntLambdaColumn<host>>(
        prefix + "no_more_notifications",
        "Whether to stop sending notifications (0/1)", offsets,
        [](const host &r) { return r.no_more_notifications; }));
    table->addColumn(std::make_unique<IntLambdaColumn<host>>(
        prefix + "check_flapping_recovery_notification",
        "Whether to check to send a recovery notification when flapping stops (0/1)",
        offsets,
        [](const host &r) { return r.check_flapping_recovery_notification; }));
    table->addColumn(std::make_unique<TimeLambdaColumn<host>>(
        prefix + "last_check", "Time of the last check (Unix timestamp)",
        offsets, [](const host &r) {
            return std::chrono::system_clock::from_time_t(r.last_check);
        }));
    table->addColumn(std::make_unique<TimeLambdaColumn<host>>(
        prefix + "last_state_change",
        "Time of the last state change - soft or hard (Unix timestamp)",
        offsets, [](const host &r) {
            return std::chrono::system_clock::from_time_t(r.last_state_change);
        }));

    table->addColumn(std::make_unique<TimeLambdaColumn<host>>(
        prefix + "last_time_up",
        "The last time the host was UP (Unix timestamp)", offsets,
        [](const host &r) {
            return std::chrono::system_clock::from_time_t(r.last_time_up);
        }));
    table->addColumn(std::make_unique<TimeLambdaColumn<host>>(
        prefix + "last_time_down",
        "The last time the host was DOWN (Unix timestamp)", offsets,
        [](const host &r) {
            return std::chrono::system_clock::from_time_t(r.last_time_down);
        }));
    table->addColumn(std::make_unique<TimeLambdaColumn<host>>(
        prefix + "last_time_unreachable",
        "The last time the host was UNREACHABLE (Unix timestamp)", offsets,
        [](const host &r) {
            return std::chrono::system_clock::from_time_t(
                r.last_time_unreachable);
        }));

    table->addColumn(std::make_unique<IntLambdaColumn<host>>(
        prefix + "is_flapping", "Whether the host state is flapping (0/1)",
        offsets, [](const host &r) { return r.is_flapping; }));
    table->addColumn(std::make_unique<IntLambdaColumn<host>>(
        prefix + "scheduled_downtime_depth",
        "The number of downtimes this host is currently in", offsets,
        [](const host &r) { return r.scheduled_downtime_depth; }));
    table->addColumn(std::make_unique<IntLambdaColumn<host>>(
        prefix + "is_executing",
        "is there a host check currently running... (0/1)", offsets,
        [](const host &r) { return r.is_executing; }));
    table->addColumn(std::make_unique<IntLambdaColumn<host>>(
        prefix + "active_checks_enabled",
        "Whether active checks are enabled for the host (0/1)", offsets,
        [](const host &r) { return r.checks_enabled; }));
    table->addColumn(std::make_unique<IntLambdaColumn<host>>(
        prefix + "check_options",
        "The current check option, forced, normal, freshness... (0-2)", offsets,
        [](const host &r) { return r.check_options; }));
#ifndef NAGIOS4
    table->addColumn(std::make_unique<IntLambdaColumn<host>>(
        prefix + "obsess_over_host",
        "The current obsess_over_host setting... (0/1)", offsets,
        [](const host &r) { return r.obsess_over_host; }));
#else
    table->addColumn(std::make_unique<IntLambdaColumn<host>>(
        prefix + "obsess_over_host",
        "The current obsess_over_host setting... (0/1)", offsets,
        [](const host &r) { return r.obsess; }));
#endif  // NAGIOS4
    table->addColumn(std::make_unique<AttributeListAsIntColumn>(
        prefix + "modified_attributes",
        "A bitmask specifying which attributes have been modified",
        offsets.add(
            [](Row r) { return &r.rawData<host>()->modified_attributes; })));
    table->addColumn(std::make_unique<AttributeListColumn>(
        prefix + "modified_attributes_list",
        "A list of all modified attributes", offsets.add([](Row r) {
            return &r.rawData<host>()->modified_attributes;
        })));

    // columns of type double
    table->addColumn(std::make_unique<DoubleLambdaColumn<host>>(
        prefix + "check_interval",
        "Number of basic interval lengths between two scheduled checks of the host",
        offsets, [](const host &r) { return r.check_interval; }));
    table->addColumn(std::make_unique<DoubleLambdaColumn<host>>(
        prefix + "retry_interval",
        "Number of basic interval lengths between checks when retrying after a soft error",
        offsets, [](const host &r) { return r.retry_interval; }));
    table->addColumn(std::make_unique<DoubleLambdaColumn<host>>(
        prefix + "notification_interval",
        "Interval of periodic notification or 0 if its off", offsets,
        [](const host &r) { return r.notification_interval; }));
    table->addColumn(std::make_unique<DoubleLambdaColumn<host>>(
        prefix + "first_notification_delay",
        "Delay before the first notification", offsets,
        [](const host &r) { return r.first_notification_delay; }));
    table->addColumn(std::make_unique<DoubleLambdaColumn<host>>(
        prefix + "low_flap_threshold", "Low threshold of flap detection",
        offsets, [](const host &r) { return r.low_flap_threshold; }));
    table->addColumn(std::make_unique<DoubleLambdaColumn<host>>(
        prefix + "high_flap_threshold", "High threshold of flap detection",
        offsets, [](const host &r) { return r.high_flap_threshold; }));
    table->addColumn(std::make_unique<DoubleLambdaColumn<host>>(
        prefix + "x_3d", "3D-Coordinates: X", offsets,
        [](const host &r) { return r.x_3d; }));
    table->addColumn(std::make_unique<DoubleLambdaColumn<host>>(
        prefix + "y_3d", "3D-Coordinates: Y", offsets,
        [](const host &r) { return r.y_3d; }));
    table->addColumn(std::make_unique<DoubleLambdaColumn<host>>(
        prefix + "z_3d", "3D-Coordinates: Z", offsets,
        [](const host &r) { return r.z_3d; }));
    table->addColumn(std::make_unique<DoubleLambdaColumn<host>>(
        prefix + "latency",
        "Time difference between scheduled check time and actual check time",
        offsets, [](const host &r) { return r.latency; }));
    table->addColumn(std::make_unique<DoubleLambdaColumn<host>>(
        prefix + "execution_time", "Time the host check needed for execution",
        offsets, [](const host &r) { return r.execution_time; }));
    table->addColumn(std::make_unique<DoubleLambdaColumn<host>>(
        prefix + "percent_state_change", "Percent state change", offsets,
        [](const host &r) { return r.percent_state_change; }));

    table->addColumn(std::make_unique<BoolLambdaColumn<host, true>>(
        prefix + "in_notification_period",
        "Whether this host is currently in its notification period (0/1)",
        offsets, [](const host &r) {
            return g_timeperiods_cache->inTimeperiod(r.notification_period_ptr);
        }));
    table->addColumn(std::make_unique<BoolLambdaColumn<host, true>>(
        prefix + "in_check_period",
        "Whether this host is currently in its check period (0/1)", offsets,
        [](const host &r) {
            return g_timeperiods_cache->inTimeperiod(r.check_period_ptr);
        }));
    table->addColumn(std::make_unique<BoolLambdaColumn<host, true>>(
        prefix + "in_service_period",
        "Whether this host is currently in its service period (0/1)", offsets,
        [mc](const host &r) {
            auto attrs = mc->customAttributes(&r.custom_variables,
                                              AttributeKind::custom_variables);
            auto it = attrs.find("SERVICE_PERIOD");
            return it == attrs.end() ||
                   g_timeperiods_cache->inTimeperiod(it->second);
        }));

    table->addColumn(std::make_unique<HostContactsColumn>(
        prefix + "contacts",
        "A list of all contacts of this host, either direct or via a contact group",
        offsets));
    table->addColumn(std::make_unique<DowntimeColumn>(
        prefix + "downtimes",
        "A list of the ids of all scheduled downtimes of this host", offsets,
        table->core(), false, DowntimeColumn::info::none));
    table->addColumn(std::make_unique<DowntimeColumn>(
        prefix + "downtimes_with_info",
        "A list of the scheduled downtimes of the host with id, author and comment",
        offsets, table->core(), false, DowntimeColumn::info::medium));
    table->addColumn(std::make_unique<DowntimeColumn>(
        prefix + "downtimes_with_extra_info",
        "A list of the scheduled downtimes of the host with id, author, comment, origin, entry_time, start_time, end_time, fixed, duration, recurring and is_pending",
        offsets, table->core(), false, DowntimeColumn::info::full));
    table->addColumn(std::make_unique<CommentColumn>(
        prefix + "comments", "A list of the ids of all comments of this host",
        offsets, table->core(), false, false, false));
    table->addColumn(std::make_unique<CommentColumn>(
        prefix + "comments_with_info",
        "A list of all comments of the host with id, author and comment",
        offsets, table->core(), false, true, false));
    table->addColumn(std::make_unique<CommentColumn>(
        prefix + "comments_with_extra_info",
        "A list of all comments of the host with id, author, comment, entry type and entry time",
        offsets, table->core(), false, true, true));

    table->addColumn(std::make_unique<CustomVarsNamesColumn>(
        prefix + "custom_variable_names",
        "A list of the names of the custom variables", offsets_custom_variables,
        table->core(), AttributeKind::custom_variables));
    table->addColumn(std::make_unique<CustomVarsValuesColumn>(
        prefix + "custom_variable_values",
        "A list of the values of the custom variables",
        offsets_custom_variables, table->core(),
        AttributeKind::custom_variables));
    table->addColumn(std::make_unique<CustomVarsDictColumn>(
        prefix + "custom_variables", "A dictionary of the custom variables",
        offsets_custom_variables, table->core(),
        AttributeKind::custom_variables));

    table->addColumn(std::make_unique<CustomVarsNamesColumn>(
        prefix + "tag_names", "A list of the names of the tags",
        offsets_custom_variables, table->core(), AttributeKind::tags));
    table->addColumn(std::make_unique<CustomVarsValuesColumn>(
        prefix + "tag_values", "A list of the values of the tags",
        offsets_custom_variables, table->core(), AttributeKind::tags));
    table->addColumn(std::make_unique<CustomVarsDictColumn>(
        prefix + "tags", "A dictionary of the tags", offsets_custom_variables,
        table->core(), AttributeKind::tags));

    table->addColumn(std::make_unique<CustomVarsNamesColumn>(
        prefix + "label_names", "A list of the names of the labels",
        offsets_custom_variables, table->core(), AttributeKind::labels));
    table->addColumn(std::make_unique<CustomVarsValuesColumn>(
        prefix + "label_values", "A list of the values of the labels",
        offsets_custom_variables, table->core(), AttributeKind::labels));
    table->addColumn(std::make_unique<CustomVarsDictColumn>(
        prefix + "labels", "A dictionary of the labels",
        offsets_custom_variables, table->core(), AttributeKind::labels));

    table->addColumn(std::make_unique<CustomVarsNamesColumn>(
        prefix + "label_source_names",
        "A list of the names of the label sources", offsets_custom_variables,
        table->core(), AttributeKind::label_sources));
    table->addColumn(std::make_unique<CustomVarsValuesColumn>(
        prefix + "label_source_values",
        "A list of the values of the label sources", offsets_custom_variables,
        table->core(), AttributeKind::label_sources));
    table->addColumn(std::make_unique<CustomVarsDictColumn>(
        prefix + "label_sources", "A dictionary of the label sources",
        offsets_custom_variables, table->core(), AttributeKind::label_sources));

    // Add direct access to the custom macro _FILENAME. In a future version of
    // Livestatus this will probably be configurable so access to further custom
    // variable can be added, such that those variables are presented like
    // ordinary Nagios columns.
    table->addColumn(std::make_unique<CustomVarsExplicitColumn>(
        prefix + "filename", "The value of the custom variable FILENAME",
        offsets_custom_variables, table->core(), "FILENAME"));

    table->addColumn(std::make_unique<HostListColumn>(
        prefix + "parents", "A list of all direct parents of the host",
        offsets.add([](Row r) { return &r.rawData<host>()->parent_hosts; }),
        table->core(), false));
    table->addColumn(std::make_unique<HostListColumn>(
        prefix + "childs", "A list of all direct children of the host",
        offsets.add([](Row r) { return &r.rawData<host>()->child_hosts; }),
        table->core(), false));
    table->addDynamicColumn(std::make_unique<DynamicRRDColumn<HostRRDColumn>>(
        prefix + "rrddata",
        "RRD metrics data of this object. This is a column with parameters: rrddata:COLUMN_TITLE:VARNAME:FROM_TIME:UNTIL_TIME:RESOLUTION",
        table->core(), offsets));

    table->addColumn(std::make_unique<ServiceListStateColumn>(
        prefix + "num_services", "The total number of services of the host",
        offsets_services, table->core(), ServiceListStateColumn::Type::num));
    table->addColumn(std::make_unique<ServiceListStateColumn>(
        prefix + "worst_service_state",
        "The worst soft state of all of the host's services (OK <= WARN <= UNKNOWN <= CRIT)",
        offsets_services, table->core(),
        ServiceListStateColumn::Type::worst_state));
    table->addColumn(std::make_unique<ServiceListStateColumn>(
        prefix + "num_services_ok",
        "The number of the host's services with the soft state OK",
        offsets_services, table->core(), ServiceListStateColumn::Type::num_ok));
    table->addColumn(std::make_unique<ServiceListStateColumn>(
        prefix + "num_services_warn",
        "The number of the host's services with the soft state WARN",
        offsets_services, table->core(),
        ServiceListStateColumn::Type::num_warn));
    table->addColumn(std::make_unique<ServiceListStateColumn>(
        prefix + "num_services_crit",
        "The number of the host's services with the soft state CRIT",
        offsets_services, table->core(),
        ServiceListStateColumn::Type::num_crit));
    table->addColumn(std::make_unique<ServiceListStateColumn>(
        prefix + "num_services_unknown",
        "The number of the host's services with the soft state UNKNOWN",
        offsets_services, table->core(),
        ServiceListStateColumn::Type::num_unknown));
    table->addColumn(std::make_unique<ServiceListStateColumn>(
        prefix + "num_services_pending",
        "The number of the host's services which have not been checked yet (pending)",
        offsets_services, table->core(),
        ServiceListStateColumn::Type::num_pending));
    table->addColumn(std::make_unique<ServiceListStateColumn>(
        prefix + "num_services_handled_problems",
        "The number of the host's services which have handled problems",
        offsets_services, table->core(),
        ServiceListStateColumn::Type::num_handled_problems));
    table->addColumn(std::make_unique<ServiceListStateColumn>(
        prefix + "num_services_unhandled_problems",
        "The number of the host's services which have unhandled problems",
        offsets_services, table->core(),
        ServiceListStateColumn::Type::num_unhandled_problems));
    table->addColumn(std::make_unique<ServiceListStateColumn>(
        prefix + "worst_service_hard_state",
        "The worst hard state of all of the host's services (OK <= WARN <= UNKNOWN <= CRIT)",
        offsets_services, table->core(),
        ServiceListStateColumn::Type::worst_hard_state));
    table->addColumn(std::make_unique<ServiceListStateColumn>(
        prefix + "num_services_hard_ok",
        "The number of the host's services with the hard state OK",
        offsets_services, table->core(),
        ServiceListStateColumn::Type::num_hard_ok));
    table->addColumn(std::make_unique<ServiceListStateColumn>(
        prefix + "num_services_hard_warn",
        "The number of the host's services with the hard state WARN",
        offsets_services, table->core(),
        ServiceListStateColumn::Type::num_hard_warn));
    table->addColumn(std::make_unique<ServiceListStateColumn>(
        prefix + "num_services_hard_crit",
        "The number of the host's services with the hard state CRIT",
        offsets_services, table->core(),
        ServiceListStateColumn::Type::num_hard_crit));
    table->addColumn(std::make_unique<ServiceListStateColumn>(
        prefix + "num_services_hard_unknown",
        "The number of the host's services with the hard state UNKNOWN",
        offsets_services, table->core(),
        ServiceListStateColumn::Type::num_hard_unknown));

    table->addColumn(std::make_unique<HostSpecialIntColumn>(
        prefix + "hard_state",
        "The effective hard state of the host (eliminates a problem in hard_state)",
        offsets, table->core(), HostSpecialIntColumn::Type::real_hard_state));
    table->addColumn(std::make_unique<HostSpecialIntColumn>(
        prefix + "pnpgraph_present",
        "Whether there is a PNP4Nagios graph present for this host (-1/0/1)",
        offsets, table->core(), HostSpecialIntColumn::Type::pnp_graph_present));
    table->addColumn(std::make_unique<HostSpecialIntColumn>(
        prefix + "mk_inventory_last",
        "The timestamp of the last Check_MK HW/SW-Inventory for this host. 0 means that no inventory data is present",
        offsets, table->core(), HostSpecialIntColumn::Type::mk_inventory_last));

    table->addColumn(std::make_unique<FileColumn<host>>(
        prefix + "mk_inventory",
        "The file content of the Check_MK HW/SW-Inventory", offsets,
        [mc]() { return mc->mkInventoryPath(); },
        [](const host &r) { return std::filesystem::path{r.name}; }));
    table->addColumn(std::make_unique<FileColumn<host>>(
        prefix + "mk_inventory_gz",
        "The gzipped file content of the Check_MK HW/SW-Inventory", offsets,
        [mc]() { return mc->mkInventoryPath(); },
        [](const host &r) {
            return std::filesystem::path{std::string{r.name} + ".gz"};
        }));
    table->addColumn(std::make_unique<FileColumn<host>>(
        prefix + "structured_status",
        "The file content of the structured status of the Check_MK HW/SW-Inventory",
        offsets, [mc]() { return mc->structuredStatusPath(); },
        [](const host &r) { return std::filesystem::path{r.name}; }));
    table->addColumn(std::make_unique<LogwatchListColumn>(
        prefix + "mk_logwatch_files",
        "This list of logfiles with problems fetched via mk_logwatch", offsets,
        table->core()));

    table->addDynamicColumn(std::make_unique<DynamicFileColumn<host>>(
        prefix + "mk_logwatch_file",
        "This contents of a logfile fetched via mk_logwatch", offsets,
        [mc]() { return mc->mkLogwatchPath(); },
        [](const host &r, const std::string &args) {
            return std::filesystem::path{r.name} / args;
        }));

    table->addColumn(std::make_unique<HostSpecialDoubleColumn>(
        prefix + "staleness", "Staleness indicator for this host", offsets,
        HostSpecialDoubleColumn::Type::staleness));

    table->addColumn(std::make_unique<HostGroupsColumn>(
        prefix + "groups", "A list of all host groups this host is in",
        offsets.add([](Row r) { return &r.rawData<host>()->hostgroups_ptr; }),
        table->core()));
    table->addColumn(std::make_unique<ContactGroupsColumn>(
        prefix + "contact_groups",
        "A list of all contact groups this host is in",
        offsets.add([](Row r) { return &r.rawData<host>()->contact_groups; })));

    table->addColumn(std::make_unique<ServiceListColumn>(
        prefix + "services", "A list of all services of the host",
        offsets_services, table->core(), 0));
    table->addColumn(std::make_unique<ServiceListColumn>(
        prefix + "services_with_state",
        "A list of all services of the host together with state and has_been_checked",
        offsets_services, table->core(), 1));
    table->addColumn(std::make_unique<ServiceListColumn>(
        prefix + "services_with_info",
        "A list of all services including detailed information about each service",
        offsets_services, table->core(), 2));
    table->addColumn(std::make_unique<ServiceListColumn>(
        prefix + "services_with_fullstate",
        "A list of all services including full state information. The list of entries can grow in future versions.",
        offsets_services, table->core(), 3));

    table->addColumn(std::make_unique<ListLambdaColumn<host>>(
        prefix + "metrics",
        "A list of all metrics of this object that historically existed",
        offsets, [mc](const host &r) {
            std::vector<std::string> metrics;
            if (r.name != nullptr) {
                auto names =
                    scan_rrd(mc->pnpPath() / r.name,
                             dummy_service_description(), mc->loggerRRD());
                std::transform(std::begin(names), std::end(names),
                               std::back_inserter(metrics),
                               [](auto &&m) { return m.string(); });
            }
            return metrics;
        }));
}

void TableHosts::answerQuery(Query *query) {
    // do we know the host group?
    if (auto value = query->stringValueRestrictionFor("groups")) {
        Debug(logger()) << "using host group index with '" << *value << "'";
        if (hostgroup *hg =
                find_hostgroup(const_cast<char *>(value->c_str()))) {
            for (hostsmember *mem = hg->members; mem != nullptr;
                 mem = mem->next) {
                const host *r = mem->host_ptr;
                if (!query->processDataset(Row(r))) {
                    break;
                }
            }
        }
        return;
    }

    // no index -> linear search over all hosts
    Debug(logger()) << "using full table scan";
    for (const auto *hst = host_list; hst != nullptr; hst = hst->next) {
        const host *r = hst;
        if (!query->processDataset(Row(r))) {
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
