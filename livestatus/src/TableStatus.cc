// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "TableStatus.h"

#include <atomic>
#include <chrono>
#include <cstdint>
#include <ctime>
#include <filesystem>
#include <memory>

#include "Average.h"
#include "BoolLambdaColumn.h"
#include "Column.h"
#include "DoubleLambdaColumn.h"
#include "FileColumn.h"
#include "IntLambdaColumn.h"
#include "MonitoringCore.h"
#include "Query.h"
#include "Row.h"
#include "StringLambdaColumn.h"
#include "TimeLambdaColumn.h"
#include "global_counters.h"
#include "mk_inventory.h"
#include "nagios.h"

extern int nagios_pid;
extern int enable_notifications;
extern int execute_service_checks;
extern int accept_passive_service_checks;
extern int execute_host_checks;
extern int accept_passive_host_checks;
extern int enable_event_handlers;
extern int obsess_over_services;
extern int obsess_over_hosts;
extern int check_service_freshness;
extern int check_host_freshness;
extern int enable_flap_detection;
extern int process_performance_data;
extern int check_external_commands;
extern int interval_length;
extern int g_num_hosts;
extern int g_num_services;
extern bool g_any_event_handler_enabled;
extern double g_average_active_latency;
extern Average g_avg_livestatus_usage;
extern int g_livestatus_threads;
extern int g_num_queued_connections;
extern std::atomic_int32_t g_livestatus_active_connections;

#ifndef NAGIOS4
extern circular_buffer external_command_buffer;
extern int external_command_buffer_slots;
#endif  // NAGIOS4

TableStatus::TableStatus(MonitoringCore *mc) : Table(mc) {
    ColumnOffsets offsets{};
    addCounterColumns("neb_callbacks", "NEB callbacks", offsets,
                      Counter::neb_callbacks);
    addCounterColumns("requests", "requests to Livestatus", offsets,
                      Counter::requests);
    addCounterColumns("connections", "client connections to Livestatus",
                      offsets, Counter::connections);
    addCounterColumns("service_checks", "completed service checks", offsets,
                      Counter::service_checks);
    addCounterColumns("host_checks", "host checks", offsets,
                      Counter::host_checks);
    addCounterColumns("forks", "process creations", offsets, Counter::forks);
    addCounterColumns("log_messages", "new log messages", offsets,
                      Counter::log_messages);
    addCounterColumns("external_commands", "external commands", offsets,
                      Counter::commands);
    addCounterColumns("livechecks", "checks executed via livecheck", offsets,
                      Counter::livechecks);
    // NOTE: The NEB queues accepted connections, so we never have overflows
    // here. Nevertheless, we provide these columns for consistency with CMC,
    // always returning zero.
    addCounterColumns(
        "livestatus_overflows",
        "times a Livestatus connection could not be immediately accepted because all threads where busy",
        offsets, Counter::overflows);

    addColumn(std::make_unique<IntLambdaColumn<TableStatus>::Reference>(
        "nagios_pid", "The process ID of the monitoring core", nagios_pid));
    addColumn(std::make_unique<IntLambdaColumn<TableStatus>::Reference>(
        "core_pid", "The process ID of the monitoring core", nagios_pid));
    addColumn(std::make_unique<IntLambdaColumn<TableStatus>::Reference>(
        "enable_notifications",
        "Whether notifications are enabled in general (0/1)",
        enable_notifications));
    addColumn(std::make_unique<IntLambdaColumn<TableStatus>::Reference>(
        "execute_service_checks",
        "Whether active service checks are activated in general (0/1)",
        execute_service_checks));
    addColumn(std::make_unique<IntLambdaColumn<TableStatus>::Reference>(
        "accept_passive_service_checks",
        "Whether passive service checks are activated in general (0/1)",
        accept_passive_service_checks));
    addColumn(std::make_unique<IntLambdaColumn<TableStatus>::Reference>(
        "execute_host_checks",
        "Whether host checks are executed in general (0/1)",
        execute_host_checks));
    addColumn(std::make_unique<IntLambdaColumn<TableStatus>::Reference>(
        "accept_passive_host_checks",
        "Whether passive host checks are accepted in general (0/1)",
        accept_passive_host_checks));
    addColumn(std::make_unique<IntLambdaColumn<TableStatus>::Reference>(
        "obsess_over_services",
        "Whether Nagios will obsess over service checks and run the ocsp_command (0/1)",
        obsess_over_services));
    addColumn(std::make_unique<IntLambdaColumn<TableStatus>::Reference>(
        "obsess_over_hosts",
        "Whether Nagios will obsess over host checks (0/1)",
        obsess_over_hosts));
    addColumn(std::make_unique<IntLambdaColumn<TableStatus>::Reference>(
        "check_service_freshness",
        "Whether service freshness checking is activated in general (0/1)",
        check_service_freshness));
    addColumn(std::make_unique<IntLambdaColumn<TableStatus>::Reference>(
        "check_host_freshness",
        "Whether host freshness checking is activated in general (0/1)",
        check_host_freshness));
    addColumn(std::make_unique<IntLambdaColumn<TableStatus>::Reference>(
        "enable_flap_detection",
        "Whether flap detection is activated in general (0/1)",
        enable_flap_detection));
    addColumn(std::make_unique<IntLambdaColumn<TableStatus>::Reference>(
        "process_performance_data",
        "Whether processing of performance data is activated in general (0/1)",
        process_performance_data));
    addColumn(std::make_unique<IntLambdaColumn<TableStatus>::Reference>(
        "enable_event_handlers",
        "Whether event handlers are activated in general (0/1)",
        enable_event_handlers));
    addColumn(std::make_unique<IntLambdaColumn<TableStatus>::Reference>(
        "check_external_commands",
        "Whether Nagios checks for external commands at its command pipe (0/1)",
        check_external_commands));
    addColumn(std::make_unique<TimeLambdaColumn<TableStatus>>(
        "program_start", "The time of the last program start as UNIX timestamp",
        offsets, [](const TableStatus & /*r*/) {
            extern time_t program_start;
            return std::chrono::system_clock::from_time_t(program_start);
        }));
#ifndef NAGIOS4
    addColumn(std::make_unique<TimeLambdaColumn<TableStatus>>(
        "last_command_check",
        "The time of the last check for a command as UNIX timestamp", offsets,
        [](const TableStatus & /*r*/) {
            extern time_t last_command_check;
            return std::chrono::system_clock::from_time_t(last_command_check);
        }));
#else
    addColumn(std::make_unique<TimeLambdaColumn<TableStatus>>(
        "last_command_check",
        "The time of the last check for a command as UNIX timestamp (placeholder)",
        offsets, [](const TableStatus & /*r*/) {
            // TODO: check if this data is available in nagios_squeue
            return std::chrono::system_clock::from_time_t(0);
        }));
#endif  // NAGIOS4
    addColumn(std::make_unique<TimeLambdaColumn<TableStatus>>(
        "last_log_rotation", "Time time of the last log file rotation", offsets,
        [](const TableStatus & /*r*/) {
            extern time_t last_log_rotation;
            return std::chrono::system_clock::from_time_t(last_log_rotation);
        }));
    addColumn(std::make_unique<IntLambdaColumn<TableStatus>::Reference>(
        "interval_length", "The default interval length from nagios.cfg",
        interval_length));

    addColumn(std::make_unique<IntLambdaColumn<TableStatus>::Reference>(
        "num_hosts", "The total number of hosts", g_num_hosts));
    addColumn(std::make_unique<IntLambdaColumn<TableStatus>::Reference>(
        "num_services", "The total number of services", g_num_services));

    addColumn(std::make_unique<StringLambdaColumn<TableStatus>>(
        "program_version", "The version of the monitoring daemon", offsets,
        [](const TableStatus & /*r*/) { return get_program_version(); }));

// External command buffer
#ifndef NAGIOS4
    addColumn(std::make_unique<IntLambdaColumn<TableStatus>::Reference>(
        "external_command_buffer_slots",
        "The size of the buffer for the external commands",
        external_command_buffer_slots));
    addColumn(std::make_unique<IntLambdaColumn<TableStatus>::Reference>(
        "external_command_buffer_usage",
        "The number of slots in use of the external command buffer",
        external_command_buffer.items));
    addColumn(std::make_unique<IntLambdaColumn<TableStatus>::Reference>(
        "external_command_buffer_max",
        "The maximum number of slots used in the external command buffer",
        external_command_buffer.high));
#else
    addColumn(std::make_unique<IntLambdaColumn<TableStatus>::Constant>(
        "external_command_buffer_slots",
        "The size of the buffer for the external commands (placeholder)", 0));
    addColumn(std::make_unique<IntLambdaColumn<TableStatus>::Constant>(
        "external_command_buffer_usage",
        "The number of slots in use of the external command buffer (placeholder)",
        0));
    addColumn(std::make_unique<IntLambdaColumn<TableStatus>::Constant>(
        "external_command_buffer_max",
        "The maximum number of slots used in the external command buffer (placeholder)",
        0));
#endif  // NAGIOS4

    // Livestatus' own status
    addColumn(std::make_unique<IntLambdaColumn<TableStatus>>(
        "cached_log_messages",
        "The current number of log messages MK Livestatus keeps in memory",
        offsets, [](const TableStatus &ts) {
            return static_cast<int32_t>(ts.core()->numCachedLogMessages());
        }));
    addColumn(std::make_unique<StringLambdaColumn<TableStatus>>(
        "livestatus_version", "The version of the MK Livestatus module",
        offsets, [](const TableStatus & /*r*/) { return VERSION; }));
    addColumn(std::make_unique<IntLambdaColumn<TableStatus>>(
        "livestatus_active_connections",
        "The current number of active connections to MK Livestatus", offsets,
        [&](const TableStatus & /*ts*/) {
            return g_livestatus_active_connections.load();
        }));
    addColumn(std::make_unique<IntLambdaColumn<TableStatus>::Reference>(
        "livestatus_queued_connections",
        "The current number of queued connections to MK Livestatus (that wait for a free thread)",
        g_num_queued_connections));
    addColumn(std::make_unique<IntLambdaColumn<TableStatus>::Reference>(
        "livestatus_threads",
        "The maximum number of connections to MK Livestatus that can be handled in parallel",
        g_livestatus_threads));
    addColumn(std::make_unique<DoubleLambdaColumn<TableStatus>>(
        "livestatus_usage",
        "The average usage of the livestatus connection slots, ranging from 0.0 (0%) up to 1.0 (100%)",
        offsets, [](const TableStatus & /*r*/) {
            return g_avg_livestatus_usage._average;
        }));

    addColumn(std::make_unique<DoubleLambdaColumn<TableStatus>>(
        "average_latency_generic",
        "The average latency for executing active checks (i.e. the time the start of the execution is behind the schedule)",
        offsets,
        [](const TableStatus & /*r*/) { return g_average_active_latency; }));
    addColumn(std::make_unique<DoubleLambdaColumn<TableStatus>>(
        "average_latency_cmk",
        "The average latency for executing Check_MK checks (i.e. the time the start of the execution is behind the schedule)",
        offsets, [](const TableStatus & /*r*/) { return 0.0; }));
    addColumn(std::make_unique<DoubleLambdaColumn<TableStatus>>(
        "average_latency_real_time",
        "The average latency for executing real time checks (i.e. the time the start of the execution is behind the schedule)",
        offsets, [](const TableStatus & /*r*/) { return 0.0; }));

    addColumn(std::make_unique<DoubleLambdaColumn<TableStatus>>(
        "helper_usage_generic",
        "The average usage of the generic check helpers, ranging from 0.0 (0%) up to 1.0 (100%)",
        offsets, [](const TableStatus & /*r*/) { return 0.0; }));
    addColumn(std::make_unique<DoubleLambdaColumn<TableStatus>>(
        "helper_usage_cmk",
        "The average usage of the Check_MK check helpers, ranging from 0.0 (0%) up to 1.0 (100%)",
        offsets, [](const TableStatus & /*r*/) { return 0.0; }));
    addColumn(std::make_unique<DoubleLambdaColumn<TableStatus>>(
        "helper_usage_real_time",
        "The average usage of the real time check helpers, ranging from 0.0 (0%) up to 1.0 (100%)",
        offsets, [](const TableStatus & /*r*/) { return 0.0; }));
    addColumn(std::make_unique<DoubleLambdaColumn<TableStatus>>(
        "helper_usage_fetcher",
        "The average usage of the fetcher helpers, ranging from 0.0 (0%) up to 1.0 (100%)",
        offsets, [](const TableStatus & /*r*/) { return 0.0; }));
    addColumn(std::make_unique<DoubleLambdaColumn<TableStatus>>(
        "helper_usage_checker",
        "The average usage of the checker helpers, ranging from 0.0 (0%) up to 1.0 (100%)",
        offsets, [](const TableStatus & /*r*/) { return 0.0; }));

    addColumn(std::make_unique<BoolLambdaColumn<TableStatus>>(
        "has_event_handlers",
        "Whether or not at alert handler rules are configured (0/1)", offsets,
        [](const TableStatus & /*r*/) { return g_any_event_handler_enabled; }));

    // Special stuff for Check_MK
    addColumn(std::make_unique<IntLambdaColumn<TableStatus>>(
        "mk_inventory_last",
        "The timestamp of the last time a host has been inventorized by Check_MK HW/SW-Inventory",
        offsets, [](const TableStatus &ts) {
            return static_cast<int32_t>(
                mk_inventory_last(ts.core()->mkInventoryPath() / ".last"));
        }));
    addColumn(std::make_unique<IntLambdaColumn<TableStatus>>(
        "num_queued_notifications",
        "The number of queued notifications which have not yet been delivered to the notification helper",
        offsets, [](const TableStatus &ts) {
            return static_cast<int32_t>(ts.core()->numQueuedNotifications());
        }));
    addColumn(std::make_unique<IntLambdaColumn<TableStatus>>(
        "num_queued_alerts",
        "The number of queued alerts which have not yet been delivered to the alert helper",
        offsets, [](const TableStatus &ts) {
            return static_cast<int32_t>(ts.core()->numQueuedAlerts());
        }));
    addColumn(std::make_unique<FileColumn<TableStatus>>(
        "license_usage_history", "Historic license usage information", offsets,
        [mc]() { return mc->licenseUsageHistoryPath(); },
        [](const TableStatus & /*r*/) { return std::filesystem::path{}; }));
}

void TableStatus::addCounterColumns(const std::string &name,
                                    const std::string &description,
                                    const ColumnOffsets &offsets,
                                    Counter which) {
    addColumn(std::make_unique<DoubleLambdaColumn<TableStatus>>(
        name, "The number of " + description + " since program start", offsets,
        [which](const TableStatus & /*r*/) { return counterValue(which); }));
    addColumn(std::make_unique<DoubleLambdaColumn<TableStatus>>(
        name + "_rate", "The averaged number of " + description + " per second",
        offsets,
        [which](const TableStatus & /*r*/) { return counterRate(which); }));
}

std::string TableStatus::name() const { return "status"; }

std::string TableStatus::namePrefix() const { return "status_"; }

void TableStatus::answerQuery(Query *query) {
    const TableStatus *r = this;
    query->processDataset(Row(r));
}
