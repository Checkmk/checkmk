// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "TableServices.h"

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
#include "DynamicRRDColumn.h"
#include "IntLambdaColumn.h"
#include "ListLambdaColumn.h"
#include "Logger.h"
#include "MacroExpander.h"
#include "Metric.h"
#include "MonitoringCore.h"
#include "Query.h"
#include "ServiceContactsColumn.h"
#include "ServiceGroupsColumn.h"
#include "ServiceRRDColumn.h"
#include "ServiceSpecialDoubleColumn.h"
#include "ServiceSpecialIntColumn.h"
#include "StringLambdaColumn.h"
#include "StringPerfdataColumn.h"
#include "StringUtils.h"
#include "TableHosts.h"
#include "TimeLambdaColumn.h"
#include "TimeperiodsCache.h"
#include "auth.h"
#include "nagios.h"

extern service *service_list;
extern TimeperiodsCache *g_timeperiods_cache;

TableServices::TableServices(MonitoringCore *mc) : Table(mc) {
    addColumns(this, "", ColumnOffsets{}, true);
}

std::string TableServices::name() const { return "services"; }

std::string TableServices::namePrefix() const { return "service_"; }

// static
void TableServices::addColumns(Table *table, const std::string &prefix,
                               const ColumnOffsets &offsets, bool add_hosts) {
    auto offsets_custom_variables{offsets.add(
        [](Row r) { return &r.rawData<service>()->custom_variables; })};
    auto *mc = table->core();
    // Es fehlen noch: double-Spalten, unsigned long spalten, etliche weniger
    // wichtige Spalten und die Servicegruppen.
    table->addColumn(std::make_unique<StringLambdaColumn<service>>(
        prefix + "description", "Description of the service (also used as key)",
        offsets, [](const service &r) {
            return r.description == nullptr ? "" : r.description;
        }));
    table->addColumn(std::make_unique<StringLambdaColumn<service>>(
        prefix + "display_name",
        "An optional display name (not used by Nagios standard web pages)",
        offsets, [](const service &r) {
            return r.display_name == nullptr ? "" : r.display_name;
        }));
#ifndef NAGIOS4
    table->addColumn(std::make_unique<StringLambdaColumn<service>>(
        prefix + "check_command", "Nagios command used for active checks",
        offsets, [](const service &r) {
            return r.service_check_command == nullptr ? ""
                                                      : r.service_check_command;
        }));
    table->addColumn(std::make_unique<StringLambdaColumn<service>>(
        prefix + "check_command_expanded",
        "Nagios command used for active checks with the macros expanded",
        offsets, [mc](const service &r) {
            return ServiceMacroExpander::make(r, mc)->expandMacros(
                r.service_check_command);
        }));
#else
    table->addColumn(std::make_unique<StringLambdaColumn<service>>(
        prefix + "check_command", "Nagios command used for active checks",
        offsets, [](const service &r) {
            return r.check_command == nullptr ? "" : r.check_command;
        }));
    table->addColumn(std::make_unique<StringLambdaColumn<service>>(
        prefix + "check_command_expanded",
        "Nagios command used for active checks with the macros expanded",
        offsets, [mc](const service &r) {
            return ServiceMacroExpander::make(r, mc)->expandMacros(
                r.check_command);
        }));
#endif
    table->addColumn(std::make_unique<StringLambdaColumn<service>>(
        prefix + "event_handler", "Nagios command used as event handler",
        offsets, [](const service &r) {
            return r.event_handler == nullptr ? "" : r.event_handler;
        }));
    table->addColumn(std::make_unique<StringLambdaColumn<service>>(
        prefix + "plugin_output", "Output of the last check plugin", offsets,
        [](const service &r) {
            return r.plugin_output == nullptr ? "" : r.plugin_output;
        }));
    table->addColumn(std::make_unique<StringLambdaColumn<service>>(
        prefix + "long_plugin_output",
        "Unabbreviated output of the last check plugin", offsets,
        [](const service &r) {
            return r.long_plugin_output == nullptr ? "" : r.long_plugin_output;
        }));
    table->addColumn(std::make_unique<StringPerfdataColumn<service>>(
        prefix + "perf_data", "Performance data of the last check plugin",
        offsets, [](const service &r) {
            return r.perf_data == nullptr ? "" : r.perf_data;
        }));
    table->addColumn(std::make_unique<StringLambdaColumn<service>>(
        prefix + "notification_period",
        "The name of the notification period of the service. It this is empty, service problems are always notified.",
        offsets, [](const service &r) {
            return r.notification_period == nullptr ? ""
                                                    : r.notification_period;
        }));
    table->addColumn(std::make_unique<StringLambdaColumn<service>>(
        prefix + "check_period",
        "The name of the check period of the service. It this is empty, the service is always checked.",
        offsets, [](const service &r) {
            return r.check_period == nullptr ? "" : r.check_period;
        }));
    table->addColumn(std::make_unique<CustomVarsExplicitColumn>(
        prefix + "service_period",
        "The name of the service period of the service",
        offsets_custom_variables, table->core(), "SERVICE_PERIOD"));
    table->addColumn(std::make_unique<StringLambdaColumn<service>>(
        prefix + "notes", "Optional notes about the service", offsets,
        [](const service &r) { return r.notes == nullptr ? "" : r.notes; }));
    table->addColumn(std::make_unique<StringLambdaColumn<service>>(
        prefix + "notes_expanded",
        "The notes with (the most important) macros expanded", offsets,
        [mc](const service &r) {
            return ServiceMacroExpander::make(r, mc)->expandMacros(r.notes);
        }));
    table->addColumn(std::make_unique<StringLambdaColumn<service>>(
        prefix + "notes_url",
        "An optional URL for additional notes about the service", offsets,
        [](const service &r) {
            return r.notes_url == nullptr ? "" : r.notes_url;
        }));
    table->addColumn(std::make_unique<StringLambdaColumn<service>>(
        prefix + "notes_url_expanded",
        "The notes_url with (the most important) macros expanded", offsets,
        [mc](const service &r) {
            return ServiceMacroExpander::make(r, mc)->expandMacros(r.notes_url);
        }));
    table->addColumn(std::make_unique<StringLambdaColumn<service>>(
        prefix + "action_url",
        "An optional URL for actions or custom information about the service",
        offsets, [](const service &r) {
            return r.action_url == nullptr ? "" : r.action_url;
        }));
    table->addColumn(std::make_unique<StringLambdaColumn<service>>(
        prefix + "action_url_expanded",
        "The action_url with (the most important) macros expanded", offsets,
        [mc](const service &r) {
            return ServiceMacroExpander::make(r, mc)->expandMacros(
                r.action_url);
        }));
    table->addColumn(std::make_unique<StringLambdaColumn<service>>(
        prefix + "icon_image",
        "The name of an image to be used as icon in the web interface", offsets,
        [](const service &r) {
            return r.icon_image == nullptr ? "" : r.icon_image;
        }));
    table->addColumn(std::make_unique<StringLambdaColumn<service>>(
        prefix + "icon_image_expanded",
        "The icon_image with (the most important) macros expanded", offsets,
        [mc](const service &r) {
            return ServiceMacroExpander::make(r, mc)->expandMacros(
                r.icon_image);
        }));
    table->addColumn(std::make_unique<StringLambdaColumn<service>>(
        prefix + "icon_image_alt",
        "An alternative text for the icon_image for browsers not displaying icons",
        offsets, [](const service &r) {
            return r.icon_image_alt == nullptr ? "" : r.icon_image_alt;
        }));

    table->addColumn(std::make_unique<IntLambdaColumn<service>>(
        prefix + "initial_state", "The initial state of the service", offsets,
        [](const service &r) { return r.initial_state; }));
    table->addColumn(std::make_unique<IntLambdaColumn<service>>(
        prefix + "max_check_attempts", "The maximum number of check attempts",
        offsets, [](const service &r) { return r.max_attempts; }));
    table->addColumn(std::make_unique<IntLambdaColumn<service>>(
        prefix + "current_attempt", "The number of the current check attempt",
        offsets, [](const service &r) { return r.current_attempt; }));
    table->addColumn(std::make_unique<IntLambdaColumn<service>>(
        prefix + "state",
        "The current state of the service (0: OK, 1: WARN, 2: CRITICAL, 3: UNKNOWN)",
        offsets, [](const service &r) { return r.current_state; }));
    table->addColumn(std::make_unique<IntLambdaColumn<service>>(
        prefix + "has_been_checked",
        "Whether the service already has been checked (0/1)", offsets,
        [](const service &r) { return r.has_been_checked; }));
    table->addColumn(std::make_unique<IntLambdaColumn<service>>(
        prefix + "last_state", "The last state of the service", offsets,
        [](const service &r) { return r.last_state; }));
    table->addColumn(std::make_unique<IntLambdaColumn<service>>(
        prefix + "last_hard_state", "The last hard state of the service",
        offsets, [](const service &r) { return r.last_hard_state; }));
    table->addColumn(std::make_unique<IntLambdaColumn<service>>(
        prefix + "state_type",
        "The type of the current state (0: soft, 1: hard)", offsets,
        [](const service &r) { return r.state_type; }));
    table->addColumn(std::make_unique<IntLambdaColumn<service>>(
        prefix + "check_type",
        "The type of the last check (0: active, 1: passive)", offsets,
        [](const service &r) { return r.check_type; }));
    table->addColumn(std::make_unique<IntLambdaColumn<service>>(
        prefix + "acknowledged",
        "Whether the current service problem has been acknowledged (0/1)",
        offsets,
        [](const service &r) { return r.problem_has_been_acknowledged; }));
    table->addColumn(std::make_unique<IntLambdaColumn<service>>(
        prefix + "acknowledgement_type",
        "The type of the acknownledgement (0: none, 1: normal, 2: sticky)",
        offsets, [](const service &r) { return r.acknowledgement_type; }));
    table->addColumn(std::make_unique<IntLambdaColumn<service>>(
        prefix + "no_more_notifications",
        "Whether to stop sending notifications (0/1)", offsets,
        [](const service &r) { return r.no_more_notifications; }));
    table->addColumn(std::make_unique<TimeLambdaColumn<service>>(
        prefix + "last_time_ok",
        "The last time the service was OK (Unix timestamp)", offsets,
        [](const service &r) {
            return std::chrono::system_clock::from_time_t(r.last_time_ok);
        }));
    table->addColumn(std::make_unique<TimeLambdaColumn<service>>(
        prefix + "last_time_warning",
        "The last time the service was in WARNING state (Unix timestamp)",
        offsets, [](const service &r) {
            return std::chrono::system_clock::from_time_t(r.last_time_warning);
        }));
    table->addColumn(std::make_unique<TimeLambdaColumn<service>>(
        prefix + "last_time_critical",
        "The last time the service was CRITICAL (Unix timestamp)", offsets,
        [](const service &r) {
            return std::chrono::system_clock::from_time_t(r.last_time_critical);
        }));
    table->addColumn(std::make_unique<TimeLambdaColumn<service>>(
        prefix + "last_time_unknown",
        "The last time the service was UNKNOWN (Unix timestamp)", offsets,
        [](const service &r) {
            return std::chrono::system_clock::from_time_t(r.last_time_unknown);
        }));

    table->addColumn(std::make_unique<TimeLambdaColumn<service>>(
        prefix + "last_check", "The time of the last check (Unix timestamp)",
        offsets, [](const service &r) {
            return std::chrono::system_clock::from_time_t(r.last_check);
        }));
    table->addColumn(std::make_unique<TimeLambdaColumn<service>>(
        prefix + "next_check",
        "The scheduled time of the next check (Unix timestamp)", offsets,
        [](const service &r) {
            return std::chrono::system_clock::from_time_t(r.next_check);
        }));
    table->addColumn(std::make_unique<TimeLambdaColumn<service>>(
        prefix + "last_notification",
        "The time of the last notification (Unix timestamp)", offsets,
        [](const service &r) {
            return std::chrono::system_clock::from_time_t(r.last_notification);
        }));
    table->addColumn(std::make_unique<TimeLambdaColumn<service>>(
        prefix + "next_notification",
        "The time of the next notification (Unix timestamp)", offsets,
        [](const service &r) {
            return std::chrono::system_clock::from_time_t(r.next_notification);
        }));
    table->addColumn(std::make_unique<IntLambdaColumn<service>>(
        prefix + "current_notification_number",
        "The number of the current notification", offsets,
        [](const service &r) { return r.current_notification_number; }));
    table->addColumn(std::make_unique<TimeLambdaColumn<service>>(
        prefix + "last_state_change",
        "The time of the last state change - soft or hard (Unix timestamp)",
        offsets, [](const service &r) {
            return std::chrono::system_clock::from_time_t(r.last_state_change);
        }));
    table->addColumn(std::make_unique<TimeLambdaColumn<service>>(
        prefix + "last_hard_state_change",
        "The time of the last hard state change (Unix timestamp)", offsets,
        [](const service &r) {
            return std::chrono::system_clock::from_time_t(
                r.last_hard_state_change);
        }));
    table->addColumn(std::make_unique<IntLambdaColumn<service>>(
        prefix + "scheduled_downtime_depth",
        "The number of scheduled downtimes the service is currently in",
        offsets, [](const service &r) { return r.scheduled_downtime_depth; }));
    table->addColumn(std::make_unique<IntLambdaColumn<service>>(
        prefix + "is_flapping", "Whether the service is flapping (0/1)",
        offsets, [](const service &r) { return r.is_flapping; }));
    table->addColumn(std::make_unique<IntLambdaColumn<service>>(
        prefix + "checks_enabled",
        "Whether active checks are enabled for the service (0/1)", offsets,
        [](const service &r) { return r.checks_enabled; }));
#ifndef NAGIOS4
    table->addColumn(std::make_unique<IntLambdaColumn<service>>(
        prefix + "accept_passive_checks",
        "Whether the service accepts passive checks (0/1)", offsets,
        [](const service &r) { return r.accept_passive_service_checks; }));
#else
    table->addColumn(std::make_unique<IntLambdaColumn<service>>(
        prefix + "accept_passive_checks",
        "Whether the service accepts passive checks (0/1)", offsets,
        [](const service &r) { return r.accept_passive_checks; }));
#endif  // NAGIOS4
    table->addColumn(std::make_unique<IntLambdaColumn<service>>(
        prefix + "event_handler_enabled",
        "Whether and event handler is activated for the service (0/1)", offsets,
        [](const service &r) { return r.event_handler_enabled; }));
    table->addColumn(std::make_unique<IntLambdaColumn<service>>(
        prefix + "notifications_enabled",
        "Whether notifications are enabled for the service (0/1)", offsets,
        [](const service &r) { return r.notifications_enabled; }));
    table->addColumn(std::make_unique<IntLambdaColumn<service>>(
        prefix + "process_performance_data",
        "Whether processing of performance data is enabled for the service (0/1)",
        offsets, [](const service &r) { return r.process_performance_data; }));
    table->addColumn(std::make_unique<IntLambdaColumn<service>>(
        prefix + "is_executing",
        "is there a service check currently running... (0/1)", offsets,
        [](const service &r) { return r.is_executing; }));
    table->addColumn(std::make_unique<IntLambdaColumn<service>>(
        prefix + "active_checks_enabled",
        "Whether active checks are enabled for the service (0/1)", offsets,
        [](const service &r) { return r.checks_enabled; }));
    table->addColumn(std::make_unique<IntLambdaColumn<service>>(
        prefix + "check_options",
        "The current check option, forced, normal, freshness... (0/1)", offsets,
        [](const service &r) { return r.check_options; }));
    table->addColumn(std::make_unique<IntLambdaColumn<service>>(
        prefix + "flap_detection_enabled",
        "Whether flap detection is enabled for the service (0/1)", offsets,
        [](const service &r) { return r.flap_detection_enabled; }));
    table->addColumn(std::make_unique<IntLambdaColumn<service>>(
        prefix + "check_freshness",
        "Whether freshness checks are activated (0/1)", offsets,
        [](const service &r) { return r.check_freshness; }));
#ifndef NAGIOS4
    table->addColumn(std::make_unique<IntLambdaColumn<service>>(
        prefix + "obsess_over_service",
        "Whether 'obsess_over_service' is enabled for the service (0/1)",
        offsets, [](const service &r) { return r.obsess_over_service; }));
#else
    table->addColumn(std::make_unique<IntLambdaColumn<service>>(
        prefix + "obsess_over_service",
        "Whether 'obsess_over_service' is enabled for the service (0/1)",
        offsets, [](const service &r) { return r.obsess; }));
#endif  // NAGIOS4
    table->addColumn(std::make_unique<AttributeListAsIntColumn>(
        prefix + "modified_attributes",
        "A bitmask specifying which attributes have been modified",
        offsets.add(
            [](Row r) { return &r.rawData<service>()->modified_attributes; })));
    table->addColumn(std::make_unique<AttributeListColumn>(
        prefix + "modified_attributes_list",
        "A list of all modified attributes", offsets.add([](Row r) {
            return &r.rawData<service>()->modified_attributes;
        })));
    table->addColumn(std::make_unique<ServiceSpecialIntColumn>(
        prefix + "hard_state",
        "The effective hard state of the service (eliminates a problem in hard_state)",
        offsets, table->core(),
        ServiceSpecialIntColumn::Type::real_hard_state));
    table->addColumn(std::make_unique<ServiceSpecialIntColumn>(
        prefix + "pnpgraph_present",
        "Whether there is a PNP4Nagios graph present for this service (0/1)",
        offsets, table->core(),
        ServiceSpecialIntColumn::Type::pnp_graph_present));
    table->addColumn(std::make_unique<ServiceSpecialDoubleColumn>(
        prefix + "staleness", "The staleness indicator for this service",
        offsets, ServiceSpecialDoubleColumn::Type::staleness));

    // columns of type double
    table->addColumn(std::make_unique<DoubleLambdaColumn<service>>(
        prefix + "check_interval",
        "Number of basic interval lengths between two scheduled checks of the service",
        offsets, [](const service &r) { return r.check_interval; }));
    table->addColumn(std::make_unique<DoubleLambdaColumn<service>>(
        prefix + "retry_interval",
        "Number of basic interval lengths between checks when retrying after a soft error",
        offsets, [](const service &r) { return r.retry_interval; }));
    table->addColumn(std::make_unique<DoubleLambdaColumn<service>>(
        prefix + "notification_interval",
        "Interval of periodic notification or 0 if its off", offsets,
        [](const service &r) { return r.notification_interval; }));
    table->addColumn(std::make_unique<DoubleLambdaColumn<service>>(
        prefix + "first_notification_delay",
        "Delay before the first notification", offsets,
        [](const service &r) { return r.first_notification_delay; }));
    table->addColumn(std::make_unique<DoubleLambdaColumn<service>>(
        prefix + "low_flap_threshold", "Low threshold of flap detection",
        offsets, [](const service &r) { return r.low_flap_threshold; }));
    table->addColumn(std::make_unique<DoubleLambdaColumn<service>>(
        prefix + "high_flap_threshold", "High threshold of flap detection",
        offsets, [](const service &r) { return r.high_flap_threshold; }));
    table->addColumn(std::make_unique<DoubleLambdaColumn<service>>(
        prefix + "latency",
        "Time difference between scheduled check time and actual check time",
        offsets, [](const service &r) { return r.latency; }));
    table->addColumn(std::make_unique<DoubleLambdaColumn<service>>(
        prefix + "execution_time",
        "Time the service check needed for execution", offsets,
        [](const service &r) { return r.execution_time; }));
    table->addColumn(std::make_unique<DoubleLambdaColumn<service>>(
        prefix + "percent_state_change", "Percent state change", offsets,
        [](const service &r) { return r.percent_state_change; }));

    table->addColumn(std::make_unique<BoolLambdaColumn<service, true>>(
        prefix + "in_check_period",
        "Whether the service is currently in its check period (0/1)", offsets,
        [](const service &r) {
            return g_timeperiods_cache->inTimeperiod(r.check_period_ptr);
        }));
    table->addColumn(std::make_unique<BoolLambdaColumn<service, true>>(
        prefix + "in_service_period",
        "Whether this service is currently in its service period (0/1)",
        offsets, [mc](const service &r) {
            auto attrs = mc->customAttributes(&r.custom_variables,
                                              AttributeKind::custom_variables);
            auto it = attrs.find("SERVICE_PERIOD");
            return it == attrs.end() ||
                   g_timeperiods_cache->inTimeperiod(it->second);
        }));
    table->addColumn(std::make_unique<BoolLambdaColumn<service, true>>(
        prefix + "in_notification_period",
        "Whether the service is currently in its notification period (0/1)",
        offsets, [](const service &r) {
            return g_timeperiods_cache->inTimeperiod(r.notification_period_ptr);
        }));

    table->addColumn(std::make_unique<ServiceContactsColumn>(
        prefix + "contacts",
        "A list of all contacts of the service, either direct or via a contact group",
        offsets));
    table->addColumn(std::make_unique<DowntimeColumn>(
        prefix + "downtimes", "A list of all downtime ids of the service",
        offsets, table->core(), true, DowntimeColumn::info::none));
    table->addColumn(std::make_unique<DowntimeColumn>(
        prefix + "downtimes_with_info",
        "A list of all downtimes of the service with id, author and comment",
        offsets, table->core(), true, DowntimeColumn::info::medium));
    table->addColumn(std::make_unique<DowntimeColumn>(
        prefix + "downtimes_with_extra_info",
        "A list of all downtimes of the service with id, author, comment, origin, entry_time, start_time, end_time, fixed, duration, recurring and is_pending",
        offsets, table->core(), true, DowntimeColumn::info::full));
    table->addColumn(std::make_unique<CommentColumn>(
        prefix + "comments", "A list of all comment ids of the service",
        offsets, table->core(), true, false, false));
    table->addColumn(std::make_unique<CommentColumn>(
        prefix + "comments_with_info",
        "A list of all comments of the service with id, author and comment",
        offsets, table->core(), true, true, false));
    table->addColumn(std::make_unique<CommentColumn>(
        prefix + "comments_with_extra_info",
        "A list of all comments of the service with id, author, comment, entry type and entry time",
        offsets, table->core(), true, true, true));

    if (add_hosts) {
        TableHosts::addColumns(table, "host_", offsets.add([](Row r) {
            return r.rawData<service>()->host_ptr;
        }));
    }

    table->addColumn(std::make_unique<CustomVarsNamesColumn>(
        prefix + "custom_variable_names",
        "A list of the names of the custom variables of the service",
        offsets_custom_variables, table->core(),
        AttributeKind::custom_variables));
    table->addColumn(std::make_unique<CustomVarsValuesColumn>(
        prefix + "custom_variable_values",
        "A list of the values of all custom variable of the service",
        offsets_custom_variables, table->core(),
        AttributeKind::custom_variables));
    table->addColumn(std::make_unique<CustomVarsDictColumn>(
        prefix + "custom_variables", "A dictionary of the custom variables",
        offsets_custom_variables, table->core(),
        AttributeKind::custom_variables));

    table->addColumn(std::make_unique<CustomVarsNamesColumn>(
        prefix + "tag_names", "A list of the names of the tags of the service",
        offsets_custom_variables, table->core(), AttributeKind::tags));
    table->addColumn(std::make_unique<CustomVarsValuesColumn>(
        prefix + "tag_values",
        "A list of the values of all tags of the service",
        offsets_custom_variables, table->core(), AttributeKind::tags));
    table->addColumn(std::make_unique<CustomVarsDictColumn>(
        prefix + "tags", "A dictionary of the tags", offsets_custom_variables,
        table->core(), AttributeKind::tags));

    table->addColumn(std::make_unique<CustomVarsNamesColumn>(
        prefix + "label_names",
        "A list of the names of the labels of the service",
        offsets_custom_variables, table->core(), AttributeKind::labels));
    table->addColumn(std::make_unique<CustomVarsValuesColumn>(
        prefix + "label_values",
        "A list of the values of all labels of the service",
        offsets_custom_variables, table->core(), AttributeKind::labels));
    table->addColumn(std::make_unique<CustomVarsDictColumn>(
        prefix + "labels", "A dictionary of the labels",
        offsets_custom_variables, table->core(), AttributeKind::labels));

    table->addColumn(std::make_unique<CustomVarsNamesColumn>(
        prefix + "label_source_names",
        "A list of the names of the sources of the service",
        offsets_custom_variables, table->core(), AttributeKind::label_sources));
    table->addColumn(std::make_unique<CustomVarsValuesColumn>(
        prefix + "label_source_values",
        "A list of the values of all sources of the service",
        offsets_custom_variables, table->core(), AttributeKind::label_sources));
    table->addColumn(std::make_unique<CustomVarsDictColumn>(
        prefix + "label_sources", "A dictionary of the label sources",
        offsets_custom_variables, table->core(), AttributeKind::label_sources));

    table->addColumn(std::make_unique<ServiceGroupsColumn>(
        prefix + "groups", "A list of all service groups the service is in",
        offsets.add(
            [](Row r) { return &r.rawData<service>()->servicegroups_ptr; }),
        table->core()));
    table->addColumn(std::make_unique<ContactGroupsColumn>(
        prefix + "contact_groups",
        "A list of all contact groups this service is in",
        offsets.add(
            [](Row r) { return &r.rawData<service>()->contact_groups; })));

    table->addColumn(std::make_unique<ListLambdaColumn<service>>(
        prefix + "metrics",
        "A list of all metrics of this object that historically existed",
        offsets, [mc](const service &r) {
            std::vector<std::string> metrics;
            if (r.host_name == nullptr || r.description == nullptr) {
                return metrics;
            }
            auto names = scan_rrd(mc->pnpPath() / r.host_name, r.description,
                                  mc->loggerRRD());
            std::transform(std::begin(names), std::end(names),
                           std::back_inserter(metrics),
                           [](auto &&m) { return m.string(); });
            return metrics;
        }));
    table->addDynamicColumn(std::make_unique<
                            DynamicRRDColumn<ServiceRRDColumn>>(
        prefix + "rrddata",
        "RRD metrics data of this object. This is a column with parameters: rrddata:COLUMN_TITLE:VARNAME:FROM_TIME:UNTIL_TIME:RESOLUTION",
        table->core(), offsets));
    table->addColumn(std::make_unique<TimeLambdaColumn<service>::Constant>(
        prefix + "cached_at",
        "A dummy column in order to be compatible with Check_MK Multisite",
        std::chrono::system_clock::time_point{}));
    table->addColumn(std::make_unique<IntLambdaColumn<service>::Constant>(
        prefix + "cache_interval",
        "A dummy column in order to be compatible with Check_MK Multisite", 0));
}

void TableServices::answerQuery(Query *query) {
    // do we know the host?
    if (auto value = query->stringValueRestrictionFor("host_name")) {
        Debug(logger()) << "using host name index with '" << *value << "'";
        // TODO(sp): Remove ugly cast.
        if (const auto *host =
                reinterpret_cast<::host *>(core()->find_host(*value))) {
            for (const auto *m = host->services; m != nullptr; m = m->next) {
                const service *r = m->service_ptr;
                if (!query->processDataset(Row(r))) {
                    break;
                }
            }
            return;
        }
    }

    // do we know the service group?
    if (auto value = query->stringValueRestrictionFor("groups")) {
        Debug(logger()) << "using service group index with '" << *value << "'";
        if (const auto *sg =
                find_servicegroup(const_cast<char *>(value->c_str()))) {
            for (const auto *m = sg->members; m != nullptr; m = m->next) {
                const service *r = m->service_ptr;
                if (!query->processDataset(Row(r))) {
                    break;
                }
            }
        }
        return;
    }

    // do we know the host group?
    if (auto value = query->stringValueRestrictionFor("host_groups")) {
        Debug(logger()) << "using host group index with '" << *value << "'";
        if (const auto *hg =
                find_hostgroup(const_cast<char *>(value->c_str()))) {
            for (const auto *m = hg->members; m != nullptr; m = m->next) {
                for (const auto *smem = m->host_ptr->services; smem != nullptr;
                     smem = smem->next) {
                    const service *r = smem->service_ptr;
                    if (!query->processDataset(Row(r))) {
                        return;
                    }
                }
            }
        }
        return;
    }

    // no index -> iterator over *all* services
    Debug(logger()) << "using full table scan";
    for (const auto *svc = service_list; svc != nullptr; svc = svc->next) {
        const service *r = svc;
        if (!query->processDataset(Row(r))) {
            break;
        }
    }
}

bool TableServices::isAuthorized(Row row, const contact *ctc) const {
    const auto *svc = rowData<service>(row);
    return is_authorized_for(core(), ctc, svc->host_ptr, svc);
}

Row TableServices::findObject(const std::string &objectspec) const {
    // The protocol proposes spaces as a separator between the host name and the
    // service description. That introduces the problem that host name
    // containing spaces will not work. For that reason we alternatively allow a
    // semicolon as a separator.
    auto semicolon = objectspec.find(';');
    auto host_and_desc =
        semicolon == std::string::npos
            ? mk::nextField(objectspec)
            : make_pair(mk::rstrip(objectspec.substr(0, semicolon)),
                        mk::rstrip(objectspec.substr(semicolon + 1)));
    return Row(core()->find_service(host_and_desc.first, host_and_desc.second));
}
