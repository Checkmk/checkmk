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
#include <ctime>
#include <memory>
#include "Column.h"
#include "DoublePointerColumn.h"
#include "IntPointerColumn.h"
#include "Query.h"
#include "StatusSpecialIntColumn.h"
#include "StringPointerColumn.h"
#include "TimePointerColumn.h"
#include "global_counters.h"
#include "nagios.h"

using std::make_unique;
using std::string;

// Nagios status values

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
extern int num_cached_log_messages;
extern int interval_length;
extern int g_num_hosts;
extern int g_num_services;
extern int g_num_clientthreads;
extern int g_num_queued_connections;
extern int g_num_active_connections;

// Livecheck has been removed, but we still need to provide the
// columns - for compatibility
int livechecks_performed = 0;
int livecheck_overflows = 0;

#ifndef NAGIOS4
extern circular_buffer external_command_buffer;
extern int external_command_buffer_slots;
#else
// TODO: check if this data is available in nagios_squeue
#endif  // NAGIOS4

TableStatus::TableStatus(Logger *logger) : Table(logger) {
    addCounterColumns("neb_callbacks", "NEB callbacks", COUNTER_NEB_CALLBACKS);
    addCounterColumns("requests", "requests to Livestatus", COUNTER_REQUESTS);
    addCounterColumns("connections", "client connections to Livestatus",
                      COUNTER_CONNECTIONS);
    addCounterColumns("service_checks", "completed service checks",
                      COUNTER_SERVICE_CHECKS);
    addCounterColumns("host_checks", "host checks", COUNTER_HOST_CHECKS);
    addCounterColumns("forks", "process creations", COUNTER_FORKS);
    addCounterColumns("log_messages", "new log messages", COUNTER_LOG_MESSAGES);
    addCounterColumns("external_commands", "external commands",
                      COUNTER_COMMANDS);
    addCounterColumns("livechecks", "checks executed via livecheck",
                      COUNTER_LIVECHECKS);
    addCounterColumns("livecheck_overflows",
                      "times a check could not be executed because no "
                      "livecheck helper was free",
                      COUNTER_LIVECHECK_OVERFLOWS);

    // Nagios program status data
    addColumn(make_unique<IntPointerColumn>(
        "nagios_pid", "The process ID of the Nagios main process",
        &nagios_pid));
    addColumn(make_unique<IntPointerColumn>(
        "enable_notifications",
        "Whether notifications are enabled in general (0/1)",
        &enable_notifications));
    addColumn(make_unique<IntPointerColumn>(
        "execute_service_checks",
        "Whether active service checks are activated in general (0/1)",
        &execute_service_checks));
    addColumn(make_unique<IntPointerColumn>(
        "accept_passive_service_checks",
        "Whether passive service checks are activated in general (0/1)",
        &accept_passive_service_checks));
    addColumn(make_unique<IntPointerColumn>(
        "execute_host_checks",
        "Whether host checks are executed in general (0/1)",
        &execute_host_checks));
    addColumn(make_unique<IntPointerColumn>(
        "accept_passive_host_checks",
        "Whether passive host checks are accepted in general (0/1)",
        &accept_passive_host_checks));
    addColumn(make_unique<IntPointerColumn>(
        "enable_event_handlers",
        "Whether event handlers are activated in general (0/1)",
        &enable_event_handlers));
    addColumn(
        make_unique<IntPointerColumn>("obsess_over_services",
                                      "Whether Nagios will obsess over service "
                                      "checks and run the ocsp_command (0/1)",
                                      &obsess_over_services));
    addColumn(make_unique<IntPointerColumn>(
        "obsess_over_hosts",
        "Whether Nagios will obsess over host checks (0/1)",
        &obsess_over_hosts));
    addColumn(make_unique<IntPointerColumn>(
        "check_service_freshness",
        "Whether service freshness checking is activated in general (0/1)",
        &check_service_freshness));
    addColumn(make_unique<IntPointerColumn>(
        "check_host_freshness",
        "Whether host freshness checking is activated in general (0/1)",
        &check_host_freshness));
    addColumn(make_unique<IntPointerColumn>(
        "enable_flap_detection",
        "Whether flap detection is activated in general (0/1)",
        &enable_flap_detection));
    addColumn(make_unique<IntPointerColumn>(
        "process_performance_data",
        "Whether processing of performance data is activated in general (0/1)",
        &process_performance_data));
    addColumn(make_unique<IntPointerColumn>(
        "check_external_commands",
        "Whether Nagios checks for external commands at its command pipe (0/1)",
        &check_external_commands));
    addColumn(make_unique<TimePointerColumn>(
        "program_start", "The time of the last program start as UNIX timestamp",
        reinterpret_cast<int *>(&program_start)));
#ifndef NAGIOS4
    addColumn(make_unique<TimePointerColumn>(
        "last_command_check",
        "The time of the last check for a command as UNIX timestamp",
        reinterpret_cast<int *>(&last_command_check)));
#else
    int dummy = 0;
    addColumn(make_unique<TimePointerColumn>(
        "last_command_check",
        "The time of the last check for a command "
        "as UNIX timestamp (placeholder)",
        &dummy));
#endif  // NAGIOS4
    addColumn(make_unique<TimePointerColumn>(
        "last_log_rotation", "Time time of the last log file rotation",
        reinterpret_cast<int *>(&last_log_rotation)));
    addColumn(make_unique<IntPointerColumn>(
        "interval_length", "The default interval length from nagios.cfg",
        &interval_length));

    addColumn(make_unique<IntPointerColumn>(
        "num_hosts", "The total number of hosts", &g_num_hosts));
    addColumn(make_unique<IntPointerColumn>(
        "num_services", "The total number of services", &g_num_services));

    addColumn(make_unique<StringPointerColumn>(
        "program_version", "The version of the monitoring daemon",
        get_program_version()));

// External command buffer
#ifndef NAGIOS4
    addColumn(make_unique<IntPointerColumn>(
        "external_command_buffer_slots",
        "The size of the buffer for the external commands",
        &external_command_buffer_slots));
    addColumn(make_unique<IntPointerColumn>(
        "external_command_buffer_usage",
        "The number of slots in use of the external command buffer",
        &(external_command_buffer.items)));
    addColumn(make_unique<IntPointerColumn>(
        "external_command_buffer_max",
        "The maximum number of slots used in the external command buffer",
        &(external_command_buffer.high)));
#else
    addColumn(make_unique<IntPointerColumn>(
        "external_command_buffer_slots",
        "The size of the buffer for the external commands (placeholder)",
        &dummy));
    addColumn(make_unique<IntPointerColumn>(
        "external_command_buffer_usage",
        "The number of slots in use of the external "
        "command buffer (placeholder)",
        &dummy));
    addColumn(
        make_unique<IntPointerColumn>("external_command_buffer_max",
                                      "The maximum number of slots used in the "
                                      "external command buffer (placeholder)",
                                      &dummy));
#endif  // NAGIOS4

    // Livestatus' own status
    addColumn(make_unique<IntPointerColumn>(
        "cached_log_messages",
        "The current number of log messages MK Livestatus keeps in memory",
        &num_cached_log_messages));
    addColumn(make_unique<StringPointerColumn>(
        "livestatus_version", "The version of the MK Livestatus module",
        VERSION));
    addColumn(make_unique<IntPointerColumn>(
        "livestatus_active_connections",
        "The current number of active connections to MK Livestatus",
        &g_num_active_connections));
    addColumn(make_unique<IntPointerColumn>(
        "livestatus_queued_connections",
        "The current number of queued connections "
        "to MK Livestatus (that wait for a free "
        "thread)",
        &g_num_queued_connections));
    addColumn(make_unique<IntPointerColumn>(
        "livestatus_threads",
        "The maximum number of connections to MK "
        "Livestatus that can be handled in parallel",
        &g_num_clientthreads));

    // Special stuff for Check_MK
    extern char g_mk_inventory_path[];
    addColumn(make_unique<StatusSpecialIntColumn>(
        "mk_inventory_last",
        "The timestamp of the last time a host has been inventorized by "
        "Check_MK HW/SW-Inventory",
        g_mk_inventory_path, SPIC_MK_INVENTORY_LAST));
}

void TableStatus::addCounterColumns(const string &name,
                                    const string &description, int which) {
    addColumn(make_unique<DoublePointerColumn>(
        name, "The number of " + description + " since program start",
        &g_counters[which]));
    addColumn(make_unique<DoublePointerColumn>(
        name + "_rate", "The averaged number of " + description + " per second",
        &g_counter_rate[which]));
}

string TableStatus::name() const { return "status"; }

string TableStatus::namePrefix() const { return "status_"; }

void TableStatus::answerQuery(Query *query) { query->processDataset(this); }
