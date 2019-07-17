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

#include "TableStatus.h"
#include <atomic>
#include <ctime>
#include <memory>
#include "AtomicInt32PointerColumn.h"
#include "Column.h"
#include "DoublePointerColumn.h"
#include "IntPointerColumn.h"
#include "Query.h"
#include "Row.h"
#include "StatusSpecialIntColumn.h"
#include "StringPointerColumn.h"
#include "TimePointerColumn.h"
#include "global_counters.h"
#include "nagios.h"

extern time_t program_start;
extern int nagios_pid;
#ifndef NAGIOS4
extern time_t last_command_check;
#endif
extern time_t last_log_rotation;
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
extern double g_average_active_latency;
extern int g_livestatus_threads;
extern int g_num_queued_connections;
extern std::atomic_int32_t g_livestatus_active_connections;

#ifndef NAGIOS4
extern circular_buffer external_command_buffer;
extern int external_command_buffer_slots;
#else
// TODO: check if this data is available in nagios_squeue
namespace {
time_t dummy_time = 0;
int dummy_int = 0;
}  // namespace
#endif  // NAGIOS4

namespace {
// NOTE: We have a FixedDoubleColumn, but this lives somewhere else, and this is
// only a temporary hack.
double dummy_double{0};
}  // namespace

TableStatus::TableStatus(MonitoringCore *mc) : Table(mc) {
    addCounterColumns("neb_callbacks", "NEB callbacks", Counter::neb_callbacks);
    addCounterColumns("requests", "requests to Livestatus", Counter::requests);
    addCounterColumns("connections", "client connections to Livestatus",
                      Counter::connections);
    addCounterColumns("service_checks", "completed service checks",
                      Counter::service_checks);
    addCounterColumns("host_checks", "host checks", Counter::host_checks);
    addCounterColumns("forks", "process creations", Counter::forks);
    addCounterColumns("log_messages", "new log messages",
                      Counter::log_messages);
    addCounterColumns("external_commands", "external commands",
                      Counter::commands);
    addCounterColumns("livechecks", "checks executed via livecheck",
                      Counter::livechecks);

    // Nagios program status data
    addColumn(std::make_unique<IntPointerColumn>(
        "nagios_pid", "The process ID of the monitoring core", &nagios_pid));
    addColumn(std::make_unique<IntPointerColumn>(
        "core_pid", "The process ID of the monitoring core", &nagios_pid));
    addColumn(std::make_unique<IntPointerColumn>(
        "enable_notifications",
        "Whether notifications are enabled in general (0/1)",
        &enable_notifications));
    addColumn(std::make_unique<IntPointerColumn>(
        "execute_service_checks",
        "Whether active service checks are activated in general (0/1)",
        &execute_service_checks));
    addColumn(std::make_unique<IntPointerColumn>(
        "accept_passive_service_checks",
        "Whether passive service checks are activated in general (0/1)",
        &accept_passive_service_checks));
    addColumn(std::make_unique<IntPointerColumn>(
        "execute_host_checks",
        "Whether host checks are executed in general (0/1)",
        &execute_host_checks));
    addColumn(std::make_unique<IntPointerColumn>(
        "accept_passive_host_checks",
        "Whether passive host checks are accepted in general (0/1)",
        &accept_passive_host_checks));
    addColumn(std::make_unique<IntPointerColumn>(
        "obsess_over_services",
        "Whether Nagios will obsess over service checks and run the ocsp_command (0/1)",
        &obsess_over_services));
    addColumn(std::make_unique<IntPointerColumn>(
        "obsess_over_hosts",
        "Whether Nagios will obsess over host checks (0/1)",
        &obsess_over_hosts));
    addColumn(std::make_unique<IntPointerColumn>(
        "check_service_freshness",
        "Whether service freshness checking is activated in general (0/1)",
        &check_service_freshness));
    addColumn(std::make_unique<IntPointerColumn>(
        "check_host_freshness",
        "Whether host freshness checking is activated in general (0/1)",
        &check_host_freshness));
    addColumn(std::make_unique<IntPointerColumn>(
        "enable_flap_detection",
        "Whether flap detection is activated in general (0/1)",
        &enable_flap_detection));
    addColumn(std::make_unique<IntPointerColumn>(
        "process_performance_data",
        "Whether processing of performance data is activated in general (0/1)",
        &process_performance_data));
    addColumn(std::make_unique<IntPointerColumn>(
        "enable_event_handlers",
        "Whether event handlers are activated in general (0/1)",
        &enable_event_handlers));
    addColumn(std::make_unique<IntPointerColumn>(
        "check_external_commands",
        "Whether Nagios checks for external commands at its command pipe (0/1)",
        &check_external_commands));
    addColumn(std::make_unique<TimePointerColumn>(
        "program_start", "The time of the last program start as UNIX timestamp",
        &program_start));
#ifndef NAGIOS4
    addColumn(std::make_unique<TimePointerColumn>(
        "last_command_check",
        "The time of the last check for a command as UNIX timestamp",
        &last_command_check));
#else
    addColumn(std::make_unique<TimePointerColumn>(
        "last_command_check",
        "The time of the last check for a command as UNIX timestamp (placeholder)",
        &dummy_time));
#endif  // NAGIOS4
    addColumn(std::make_unique<TimePointerColumn>(
        "last_log_rotation", "Time time of the last log file rotation",
        &last_log_rotation));
    addColumn(std::make_unique<IntPointerColumn>(
        "interval_length", "The default interval length from nagios.cfg",
        &interval_length));

    addColumn(std::make_unique<IntPointerColumn>(
        "num_hosts", "The total number of hosts", &g_num_hosts));
    addColumn(std::make_unique<IntPointerColumn>(
        "num_services", "The total number of services", &g_num_services));

    addColumn(std::make_unique<StringPointerColumn>(
        "program_version", "The version of the monitoring daemon",
        get_program_version()));

// External command buffer
#ifndef NAGIOS4
    addColumn(std::make_unique<IntPointerColumn>(
        "external_command_buffer_slots",
        "The size of the buffer for the external commands",
        &external_command_buffer_slots));
    addColumn(std::make_unique<IntPointerColumn>(
        "external_command_buffer_usage",
        "The number of slots in use of the external command buffer",
        &(external_command_buffer.items)));
    addColumn(std::make_unique<IntPointerColumn>(
        "external_command_buffer_max",
        "The maximum number of slots used in the external command buffer",
        &(external_command_buffer.high)));
#else
    addColumn(std::make_unique<IntPointerColumn>(
        "external_command_buffer_slots",
        "The size of the buffer for the external commands (placeholder)",
        &dummy_int));
    addColumn(std::make_unique<IntPointerColumn>(
        "external_command_buffer_usage",
        "The number of slots in use of the external command buffer (placeholder)",
        &dummy_int));
    addColumn(std::make_unique<IntPointerColumn>(
        "external_command_buffer_max",
        "The maximum number of slots used in the external command buffer (placeholder)",
        &dummy_int));
#endif  // NAGIOS4

    // Livestatus' own status
    addColumn(std::make_unique<StatusSpecialIntColumn>(
        "cached_log_messages",
        "The current number of log messages MK Livestatus keeps in memory", -1,
        -1, -1, 0, mc, StatusSpecialIntColumn::Type::num_cached_log_messages));
    addColumn(std::make_unique<StringPointerColumn>(
        "livestatus_version", "The version of the MK Livestatus module",
        VERSION));
    addColumn(std::make_unique<AtomicInt32PointerColumn>(
        "livestatus_active_connections",
        "The current number of active connections to MK Livestatus",
        &g_livestatus_active_connections));
    addColumn(std::make_unique<IntPointerColumn>(
        "livestatus_queued_connections",
        "The current number of queued connections to MK Livestatus (that wait for a free thread)",
        &g_num_queued_connections));
    addColumn(std::make_unique<IntPointerColumn>(
        "livestatus_threads",
        "The maximum number of connections to MK Livestatus that can be handled in parallel",
        &g_livestatus_threads));

    addColumn(std::make_unique<DoublePointerColumn>(
        "average_latency_generic",
        "The average latency for executing active checks (i.e. the time the start of the execution is behind the schedule)",
        &g_average_active_latency));
    addColumn(std::make_unique<DoublePointerColumn>(
        "average_latency_cmk",
        "The average latency for executing Check_MK checks (i.e. the time the start of the execution is behind the schedule)",
        &dummy_double));
    addColumn(std::make_unique<DoublePointerColumn>(
        "average_latency_real_time",
        "The average latency for executing real time checks (i.e. the time the start of the execution is behind the schedule)",
        &dummy_double));

    addColumn(std::make_unique<DoublePointerColumn>(
        "helper_usage_generic",
        "The average usage of the generic check helpers, ranging from 0.0 (0%) up to 1.0 (100%)",
        &dummy_double));
    addColumn(std::make_unique<DoublePointerColumn>(
        "helper_usage_cmk",
        "The average usage of the Check_MK check helpers, ranging from 0.0 (0%) up to 1.0 (100%)",
        &dummy_double));
    addColumn(std::make_unique<DoublePointerColumn>(
        "helper_usage_real_time",
        "The average usage of the real time check helpers, ranging from 0.0 (0%) up to 1.0 (100%)",
        &dummy_double));

    // Special stuff for Check_MK
    addColumn(std::make_unique<StatusSpecialIntColumn>(
        "mk_inventory_last",
        "The timestamp of the last time a host has been inventorized by Check_MK HW/SW-Inventory",
        -1, -1, -1, 0, mc, StatusSpecialIntColumn::Type::mk_inventory_last));
    addColumn(std::make_unique<StatusSpecialIntColumn>(
        "num_queued_notifications",
        "The number of queued notifications which have not yet been delivered to the notification helper",
        -1, -1, -1, 0, mc,
        StatusSpecialIntColumn::Type::num_queued_notifications));
    addColumn(std::make_unique<StatusSpecialIntColumn>(
        "num_queued_alerts",
        "The number of queued alerts which have not yet been delivered to the alert helper",
        -1, -1, -1, 0, mc, StatusSpecialIntColumn::Type::num_queued_alerts));
}

void TableStatus::addCounterColumns(const std::string &name,
                                    const std::string &description,
                                    Counter which) {
    addColumn(std::make_unique<DoublePointerColumn>(
        name, "The number of " + description + " since program start",
        counterAddress(which)));
    addColumn(std::make_unique<DoublePointerColumn>(
        name + "_rate", "The averaged number of " + description + " per second",
        counterRateAddress(which)));
}

std::string TableStatus::name() const { return "status"; }

std::string TableStatus::namePrefix() const { return "status_"; }

void TableStatus::answerQuery(Query *query) {
    query->processDataset(Row(this));
}
