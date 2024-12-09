// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/TableStatus.h"

#include <chrono>
#include <cstdint>
#include <filesystem>
#include <functional>
#include <memory>

#include "livestatus/BlobColumn.h"
#include "livestatus/Column.h"
#include "livestatus/DoubleColumn.h"
#include "livestatus/ICore.h"
#include "livestatus/IntColumn.h"
#include "livestatus/Interface.h"
#include "livestatus/Query.h"
#include "livestatus/Row.h"
#include "livestatus/StringColumn.h"
#include "livestatus/TimeColumn.h"
#include "livestatus/global_counters.h"
#include "livestatus/mk_inventory.h"

using row_type = ICore;

TableStatus::TableStatus(ICore *mc) {
    const ColumnOffsets offsets{};
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
    addCounterColumns("perf_data_count",
                      "number of performance data processed by the core",
                      offsets, Counter::perf_data);
    addCounterColumns("metrics_count",
                      "number of metrics processed by the core", offsets,
                      Counter::metrics);
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
    addCounterColumns("carbon_bytes_sent",
                      "number of bytes sent over the carbon connections",
                      offsets, Counter::carbon_bytes_sent);
    addCounterColumns("carbon_overflows",
                      "times a Carbon connection could not send the metrics",
                      offsets, Counter::carbon_overflows);
    addCounterColumns("carbon_queue_usage",
                      "number of elements in the queue / size of the queue",
                      offsets, Counter::carbon_queue_usage);
    addCounterColumns(
        "influxdb_bytes_sent",
        "number of bytes sent over the InfluxDB connections (payload only)",
        offsets, Counter::influxdb_bytes_sent);
    addCounterColumns("influxdb_overflows",
                      "times an InfluxDB connection could not send the metrics",
                      offsets, Counter::influxdb_overflows);
    addCounterColumns("influxdb_queue_usage",
                      "number of elements in the queue / size of the queue",
                      offsets, Counter::influxdb_queue_usage);
    addCounterColumns(
        "livestatus_overflows",
        "times a Livestatus connection could not be immediately accepted because all threads where busy",
        offsets, Counter::livestatus_overflows);
    addCounterColumns("rrdcached_bytes_sent",
                      "number of bytes sent over to the RRDs", offsets,
                      Counter::rrdcached_bytes_sent);
    addCounterColumns(
        "rrdcached_overflows",
        "times an RRDCacheD connection could not send the metrics", offsets,
        Counter::rrdcached_overflows);
    addCounterColumns("rrdcached_queue_usage",
                      "number of elements in the queue / size of the queue",
                      offsets, Counter::rrdcached_queue_usage);

    addColumn(std::make_unique<IntColumn<row_type>>(
        "nagios_pid", "The process ID of the monitoring core", offsets,
        [](const row_type &row) { return row.pid(); }));
    addColumn(std::make_unique<IntColumn<row_type>>(
        "core_pid", "The process ID of the monitoring core", offsets,
        [](const row_type &row) { return row.pid(); }));
    addColumn(std::make_unique<BoolColumn<row_type>>(
        "enable_notifications",
        "Whether notifications are enabled in general (0/1)", offsets,
        [](const row_type &row) {
            return row.globalFlags()->enable_notifications();
        }));
    addColumn(std::make_unique<BoolColumn<row_type>>(
        "execute_service_checks",
        "Whether active service checks are activated in general (0/1)", offsets,
        [](const row_type &row) {
            return row.globalFlags()->execute_service_checks();
        }));
    addColumn(std::make_unique<BoolColumn<row_type>>(
        "accept_passive_service_checks",
        "Whether passive service checks are activated in general (0/1)",
        offsets, [](const row_type &row) {
            return row.globalFlags()->accept_passive_service_checks();
        }));
    addColumn(std::make_unique<BoolColumn<row_type>>(
        "execute_host_checks",
        "Whether host checks are executed in general (0/1)", offsets,
        [](const row_type &row) {
            return row.globalFlags()->execute_host_checks();
        }));
    addColumn(std::make_unique<BoolColumn<row_type>>(
        "accept_passive_host_checks",
        "Whether passive host checks are accepted in general (0/1)", offsets,
        [](const row_type &row) {
            return row.globalFlags()->accept_passive_hostchecks();
        }));
    addColumn(std::make_unique<BoolColumn<row_type>>(
        "obsess_over_services",
        "Whether Nagios will obsess over service checks and run the ocsp_command (0/1)",
        offsets, [](const row_type &row) {
            return row.globalFlags()->obsess_over_services();
        }));
    addColumn(std::make_unique<BoolColumn<row_type>>(
        "obsess_over_hosts",
        "Whether Nagios will obsess over host checks (0/1)", offsets,
        [](const row_type &row) {
            return row.globalFlags()->obsess_over_hosts();
        }));
    addColumn(std::make_unique<BoolColumn<row_type>>(
        "check_service_freshness",
        "Whether service freshness checking is activated in general (0/1)",
        offsets, [](const row_type &row) {
            return row.globalFlags()->check_service_freshness();
        }));
    addColumn(std::make_unique<BoolColumn<row_type>>(
        "check_host_freshness",
        "Whether host freshness checking is activated in general (0/1)",
        offsets, [](const row_type &row) {
            return row.globalFlags()->check_host_freshness();
        }));
    addColumn(std::make_unique<BoolColumn<row_type>>(
        "enable_flap_detection",
        "Whether flap detection is activated in general (0/1)", offsets,
        [](const row_type &row) {
            return row.globalFlags()->enable_flap_detection();
        }));
    addColumn(std::make_unique<BoolColumn<row_type>>(
        "process_performance_data",
        "Whether processing of performance data is activated in general (0/1)",
        offsets, [](const row_type &row) {
            return row.globalFlags()->process_performance_data();
        }));
    addColumn(std::make_unique<BoolColumn<row_type>>(
        "enable_event_handlers",
        "Whether alert handlers are activated in general (0/1)", offsets,
        [](const row_type &row) {
            return row.globalFlags()->enable_event_handlers();
        }));
    addColumn(std::make_unique<BoolColumn<row_type>>(
        "check_external_commands",
        "Whether Nagios checks for external commands at its command pipe (0/1)",
        offsets, [](const row_type &row) {
            return row.globalFlags()->check_external_commands();
        }));
    addColumn(std::make_unique<TimeColumn<row_type>>(
        "program_start",
        "The time of the last program start or configuration reload as UNIX timestamp",
        offsets, [](const row_type &row) { return row.programStartTime(); }));
    addColumn(std::make_unique<TimeColumn<row_type>>(
        "last_command_check",
        "The time of the last check for a command as UNIX timestamp", offsets,
        [](const row_type &row) { return row.lastCommandCheckTime(); }));
    addColumn(std::make_unique<TimeColumn<row_type>>(
        "last_log_rotation", "Time time of the last log file rotation", offsets,
        [](const row_type &row) { return row.last_logfile_rotation(); }));
    addColumn(std::make_unique<IntColumn<row_type>>(
        "interval_length", "The default interval length", offsets,
        [](const row_type &row) { return row.intervalLength(); }));
    addColumn(std::make_unique<IntColumn<row_type>>(
        "max_long_output_size", "Maximum length of long output", offsets,
        [](const row_type &row) { return row.maxLongOutputSize(); }));

    addColumn(std::make_unique<IntColumn<row_type>>(
        "num_hosts", "The total number of hosts", offsets,
        [](const row_type &row) { return row.numHosts(); }));
    addColumn(std::make_unique<IntColumn<row_type>>(
        "num_services", "The total number of services", offsets,
        [](const row_type &row) { return row.numServices(); }));

    addColumn(std::make_unique<StringColumn<row_type>>(
        "program_version", "The version of the monitoring daemon", offsets,
        [](const row_type &row) { return row.programVersion(); }));
    addColumn(std::make_unique<StringColumn<row_type>>(
        "edition", "The edition of the site", offsets,
        [](const row_type &row) { return row.edition(); }));

    // External command buffer
    addColumn(std::make_unique<IntColumn<row_type>>(
        "external_command_buffer_slots",
        "The size of the buffer for the external commands", offsets,
        [](const row_type &row) { return row.externalCommandBufferSlots(); }));
    addColumn(std::make_unique<IntColumn<row_type>>(
        "external_command_buffer_usage",
        "The number of slots in use of the external command buffer", offsets,
        [](const row_type &row) { return row.externalCommandBufferUsage(); }));
    addColumn(std::make_unique<IntColumn<row_type>>(
        "external_command_buffer_max",
        "The maximum number of slots used in the external command buffer",
        offsets,
        [](const row_type &row) { return row.externalCommandBufferMax(); }));

    // Livestatus' own status
    // TODO(sp) Use "r" instead of "mc" when numCachedLogMessages is const
    addColumn(std::make_unique<IntColumn<row_type>>(
        "cached_log_messages",
        "The current number of log messages MK Livestatus keeps in memory",
        offsets, [mc](const row_type & /*row*/) {
            return static_cast<int32_t>(mc->numCachedLogMessages());
        }));
    addColumn(std::make_unique<StringColumn<row_type>>(
        "livestatus_version", "The version of the MK Livestatus module",
        offsets, [](const row_type &row) { return row.livestatusVersion(); }));
    addColumn(std::make_unique<IntColumn<row_type>>(
        "livestatus_active_connections",
        "The current number of active connections to MK Livestatus", offsets,
        [](const row_type &row) {
            return row.livestatusActiveConnectionsNum();
        }));
    addColumn(std::make_unique<IntColumn<row_type>>(
        "livestatus_queued_connections",
        "The current number of queued connections to MK Livestatus", offsets,
        [](const row_type &row) {
            return row.livestatusQueuedConnectionsNum();
        }));
    addColumn(std::make_unique<IntColumn<row_type>>(
        "livestatus_threads",
        "The maximum number of connections to MK Livestatus that can be handled in parallel",
        offsets,
        [](const row_type &row) { return row.livestatusThreadsNum(); }));
    addColumn(std::make_unique<DoubleColumn<row_type>>(
        "livestatus_usage",
        "The average usage of the livestatus connection slots, ranging from 0.0 (0%) up to 1.0 (100%)",
        offsets, [](const row_type &row) { return row.livestatusUsage(); }));

    addColumn(std::make_unique<DoubleColumn<row_type>>(
        "average_latency_generic",
        "The average latency for executing active checks (i.e. the time the start of the execution is behind the schedule)",
        offsets,
        [](const row_type &row) { return row.averageLatencyGeneric(); }));
    addColumn(std::make_unique<DoubleColumn<row_type>>(
        "average_latency_real_time",
        "The average latency for executing real time checks (i.e. the time the start of the execution is behind the schedule)",
        offsets,
        [](const row_type &row) { return row.averageLatencyRealTime(); }));
    addColumn(std::make_unique<DoubleColumn<row_type>>(
        "average_latency_fetcher",
        "The average latency for executing Check_MK fetchers (i.e. the time the start of the execution is behind the schedule)",
        offsets,
        [](const row_type &row) { return row.averageLatencyFetcher(); }));
    addColumn(std::make_unique<DoubleColumn<row_type>>(
        "average_latency_checker",
        "The average latency for executing Check_MK checkers (i.e. the time the start of the execution is behind the schedule)",
        offsets,
        [](const row_type &row) { return row.averageLatencyChecker(); }));

    addColumn(std::make_unique<DoubleColumn<row_type>>(
        "helper_usage_generic",
        "The average usage of the active check helpers, ranging from 0.0 (0%) up to 1.0 (100%)",
        offsets, [](const row_type &row) { return row.helperUsageGeneric(); }));
    addColumn(std::make_unique<DoubleColumn<row_type>>(
        "helper_usage_real_time",
        "The average usage of the real time check helpers, ranging from 0.0 (0%) up to 1.0 (100%)",
        offsets,
        [](const row_type &row) { return row.helperUsageRealTime(); }));
    addColumn(std::make_unique<DoubleColumn<row_type>>(
        "helper_usage_fetcher",
        "The average usage of the fetcher helpers, ranging from 0.0 (0%) up to 1.0 (100%)",
        offsets, [](const row_type &row) { return row.helperUsageFetcher(); }));
    addColumn(std::make_unique<DoubleColumn<row_type>>(
        "helper_usage_checker",
        "The average usage of the checker helpers, ranging from 0.0 (0%) up to 1.0 (100%)",
        offsets, [](const row_type &row) { return row.helperUsageChecker(); }));

    addColumn(std::make_unique<BoolColumn<row_type>>(
        "has_event_handlers",
        "Whether or not at alert handler rules are configured (0/1)", offsets,
        [](const row_type &row) { return row.hasEventHandlers(); }));

    // Special stuff for Check_MK
    addColumn(std::make_unique<TimeColumn<row_type>>(
        "mk_inventory_last",
        "The timestamp of the last time a host has been inventorized by Check_MK HW/SW Inventory",
        offsets, [](const row_type &row) {
            return mk_inventory_last(row.paths()->inventory_directory() /
                                     ".last");
        }));
    addColumn(std::make_unique<IntColumn<row_type>>(
        "num_queued_notifications",
        "The number of queued notifications which have not yet been delivered to the notification helper",
        offsets, [](const row_type &row) {
            return static_cast<int32_t>(row.numQueuedNotifications());
        }));
    addColumn(std::make_unique<IntColumn<row_type>>(
        "num_queued_alerts",
        "The number of queued alerts which have not yet been delivered to the alert helper",
        offsets, [](const row_type &row) {
            return static_cast<int32_t>(row.numQueuedAlerts());
        }));
    addColumn(std::make_unique<BlobColumn<row_type>>(
        "license_usage_history", "Historic license usage information", offsets,
        BlobFileReader<row_type>{[mc](const row_type & /*row*/) {
            return mc->paths()->license_usage_history_file();
        }}));
    addColumn(std::make_unique<DoubleColumn<row_type>>(
        "average_runnable_jobs_fetcher",
        "The average count of scheduled fetcher jobs which have not yet been processed",
        offsets,
        [](const row_type &row) { return row.averageRunnableJobsChecker(); }));
    addColumn(std::make_unique<DoubleColumn<row_type>>(
        "average_runnable_jobs_checker",
        "The average count of queued replies which have not yet been delivered to the checker helpers",
        offsets,
        [](const row_type &row) { return row.averageRunnableJobsChecker(); }));
    addColumn(std::make_unique<TimeColumn<row_type>>(
        "state_file_created", "The time when state file had been created",
        offsets,
        [](const row_type &row) { return row.stateFileCreatedTime(); }));
}

void TableStatus::addCounterColumns(const std::string &name,
                                    const std::string &description,
                                    const ColumnOffsets &offsets,
                                    Counter which) {
    addColumn(std::make_unique<DoubleColumn<row_type>>(
        name, "The number of " + description + " since program start", offsets,
        [which](const row_type & /*row*/) { return counterValue(which); }));
    addColumn(std::make_unique<DoubleColumn<row_type>>(
        name + "_rate", "The averaged number of " + description + " per second",
        offsets,
        [which](const row_type & /*row*/) { return counterRate(which); }));
}

std::string TableStatus::name() const { return "status"; }

std::string TableStatus::namePrefix() const { return "status_"; }

void TableStatus::answerQuery(Query &query, const User & /*user*/,
                              const ICore &core) {
    query.processDataset(Row{&core});
}

Row TableStatus::getDefault(const ICore &core) const { return Row{&core}; }
