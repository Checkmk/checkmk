// Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/TableStatus.h"

#include <chrono>
#include <cstdint>
#include <filesystem>
#include <memory>
#include <sstream>
#include <variant>  // IWYU pragma: keep

#include "livestatus/BlobColumn.h"
#include "livestatus/Column.h"
#include "livestatus/DoubleColumn.h"
#include "livestatus/IntColumn.h"
#include "livestatus/MonitoringCore.h"
#include "livestatus/Query.h"
#include "livestatus/StringColumn.h"
#include "livestatus/TimeColumn.h"
#include "livestatus/mk_inventory.h"

TableStatus::TableStatus(MonitoringCore *mc) : Table(mc) {
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

    addColumn(std::make_unique<IntColumn<TableStatus>>(
        "nagios_pid", "The process ID of the monitoring core", offsets,
        [mc](const TableStatus & /*r*/) { return mc->pid(); }));
    addColumn(std::make_unique<IntColumn<TableStatus>>(
        "core_pid", "The process ID of the monitoring core", offsets,
        [mc](const TableStatus & /*r*/) { return mc->pid(); }));
    addColumn(std::make_unique<BoolColumn<TableStatus>>(
        "enable_notifications",
        "Whether notifications are enabled in general (0/1)", offsets,
        [mc](const TableStatus & /*r*/) {
            return mc->isEnableNotifications();
        }));
    addColumn(std::make_unique<BoolColumn<TableStatus>>(
        "execute_service_checks",
        "Whether active service checks are activated in general (0/1)", offsets,
        [mc](const TableStatus & /*r*/) {
            return mc->isExecuteServiceChecks();
        }));
    addColumn(std::make_unique<BoolColumn<TableStatus>>(
        "accept_passive_service_checks",
        "Whether passive service checks are activated in general (0/1)",
        offsets, [mc](const TableStatus & /*r*/) {
            return mc->isAcceptPassiveServiceChecks();
        }));
    addColumn(std::make_unique<BoolColumn<TableStatus>>(
        "execute_host_checks",
        "Whether host checks are executed in general (0/1)", offsets,
        [mc](const TableStatus & /*r*/) { return mc->isExecuteHostChecks(); }));
    addColumn(std::make_unique<BoolColumn<TableStatus>>(
        "accept_passive_host_checks",
        "Whether passive host checks are accepted in general (0/1)", offsets,
        [mc](const TableStatus & /*r*/) {
            return mc->isAcceptPassiveHostChecks();
        }));
    addColumn(std::make_unique<BoolColumn<TableStatus>>(
        "obsess_over_services",
        "Whether Nagios will obsess over service checks and run the ocsp_command (0/1)",
        offsets, [mc](const TableStatus & /*r*/) {
            return mc->isObsessOverServices();
        }));
    addColumn(std::make_unique<BoolColumn<TableStatus>>(
        "obsess_over_hosts",
        "Whether Nagios will obsess over host checks (0/1)", offsets,
        [mc](const TableStatus & /*r*/) { return mc->isObsessOverHosts(); }));
    addColumn(std::make_unique<BoolColumn<TableStatus>>(
        "check_service_freshness",
        "Whether service freshness checking is activated in general (0/1)",
        offsets, [mc](const TableStatus & /*r*/) {
            return mc->isCheckServiceFreshness();
        }));
    addColumn(std::make_unique<BoolColumn<TableStatus>>(
        "check_host_freshness",
        "Whether host freshness checking is activated in general (0/1)",
        offsets, [mc](const TableStatus & /*r*/) {
            return mc->isCheckHostFreshness();
        }));
    addColumn(std::make_unique<BoolColumn<TableStatus>>(
        "enable_flap_detection",
        "Whether flap detection is activated in general (0/1)", offsets,
        [mc](const TableStatus & /*r*/) {
            return mc->isEnableFlapDetection();
        }));
    addColumn(std::make_unique<BoolColumn<TableStatus>>(
        "process_performance_data",
        "Whether processing of performance data is activated in general (0/1)",
        offsets, [mc](const TableStatus & /*r*/) {
            return mc->isProcessPerformanceData();
        }));
    addColumn(std::make_unique<BoolColumn<TableStatus>>(
        "enable_event_handlers",
        "Whether alert handlers are activated in general (0/1)", offsets,
        [mc](const TableStatus & /*r*/) {
            return mc->isEnableEventHandlers();
        }));
    addColumn(std::make_unique<BoolColumn<TableStatus>>(
        "check_external_commands",
        "Whether Nagios checks for external commands at its command pipe (0/1)",
        offsets, [mc](const TableStatus & /*r*/) {
            return mc->isCheckExternalCommands();
        }));
    addColumn(std::make_unique<TimeColumn<TableStatus>>(
        "program_start",
        "The time of the last program start or configuration reload as UNIX timestamp",
        offsets,
        [mc](const TableStatus & /*r*/) { return mc->programStartTime(); }));
    addColumn(std::make_unique<TimeColumn<TableStatus>>(
        "last_command_check",
        "The time of the last check for a command as UNIX timestamp", offsets,
        [mc](const TableStatus & /*r*/) {
            return mc->lastCommandCheckTime();
        }));
    addColumn(std::make_unique<TimeColumn<TableStatus>>(
        "last_log_rotation", "Time time of the last log file rotation", offsets,
        [mc](const TableStatus & /*r*/) {
            return mc->last_logfile_rotation();
        }));
    addColumn(std::make_unique<IntColumn<TableStatus>>(
        "interval_length", "The default interval length", offsets,
        [mc](const TableStatus & /*r*/) { return mc->intervalLength(); }));

    addColumn(std::make_unique<IntColumn<TableStatus>>(
        "num_hosts", "The total number of hosts", offsets,
        [mc](const TableStatus & /*r*/) { return mc->numHosts(); }));
    addColumn(std::make_unique<IntColumn<TableStatus>>(
        "num_services", "The total number of services", offsets,
        [mc](const TableStatus & /*r*/) { return mc->numServices(); }));

    addColumn(std::make_unique<StringColumn<TableStatus>>(
        "program_version", "The version of the monitoring daemon", offsets,
        [mc](const TableStatus & /*r*/) { return mc->programVersion(); }));

    // External command buffer
    addColumn(std::make_unique<IntColumn<TableStatus>>(
        "external_command_buffer_slots",
        "The size of the buffer for the external commands", offsets,
        [mc](const TableStatus & /*r*/) {
            return mc->externalCommandBufferSlots();
        }));
    addColumn(std::make_unique<IntColumn<TableStatus>>(
        "external_command_buffer_usage",
        "The number of slots in use of the external command buffer", offsets,
        [mc](const TableStatus & /*r*/) {
            return mc->externalCommandBufferUsage();
        }));
    addColumn(std::make_unique<IntColumn<TableStatus>>(
        "external_command_buffer_max",
        "The maximum number of slots used in the external command buffer",
        offsets, [mc](const TableStatus & /*r*/) {
            return mc->externalCommandBufferMax();
        }));

    // Livestatus' own status
    addColumn(std::make_unique<IntColumn<TableStatus>>(
        "cached_log_messages",
        "The current number of log messages MK Livestatus keeps in memory",
        offsets, [mc](const TableStatus & /*r*/) {
            return static_cast<int32_t>(mc->numCachedLogMessages());
        }));
    addColumn(std::make_unique<StringColumn<TableStatus>>(
        "livestatus_version", "The version of the MK Livestatus module",
        offsets,
        [mc](const TableStatus & /*r*/) { return mc->livestatusVersion(); }));
    addColumn(std::make_unique<IntColumn<TableStatus>>(
        "livestatus_active_connections",
        "The current number of active connections to MK Livestatus", offsets,
        [mc](const TableStatus & /*r*/) {
            return mc->livestatusActiveConnectionsNum();
        }));
    addColumn(std::make_unique<IntColumn<TableStatus>>(
        "livestatus_queued_connections",
        "The current number of queued connections to MK Livestatus", offsets,
        [mc](const TableStatus & /*r*/) {
            return mc->livestatusQueuedConnectionsNum();
        }));
    addColumn(std::make_unique<IntColumn<TableStatus>>(
        "livestatus_threads",
        "The maximum number of connections to MK Livestatus that can be handled in parallel",
        offsets, [mc](const TableStatus & /*r*/) {
            return mc->livestatusThreadsNum();
        }));
    addColumn(std::make_unique<DoubleColumn<TableStatus>>(
        "livestatus_usage",
        "The average usage of the livestatus connection slots, ranging from 0.0 (0%) up to 1.0 (100%)",
        offsets,
        [mc](const TableStatus & /*r*/) { return mc->livestatusUsage(); }));

    addColumn(std::make_unique<DoubleColumn<TableStatus>>(
        "average_latency_generic",
        "The average latency for executing active checks (i.e. the time the start of the execution is behind the schedule)",
        offsets, [mc](const TableStatus & /*r*/) {
            return mc->averageLatencyGeneric();
        }));
    addColumn(std::make_unique<DoubleColumn<TableStatus>>(
        "average_latency_cmk",
        "The average latency for executing Check_MK checks (i.e. the time the start of the execution is behind the schedule)",
        offsets,
        [mc](const TableStatus & /*r*/) { return mc->averageLatencyCmk(); }));
    addColumn(std::make_unique<DoubleColumn<TableStatus>>(
        "average_latency_fetcher",
        "The average latency for executing Check_MK fetchers (i.e. the time the start of the execution is behind the schedule)",
        offsets, [mc](const TableStatus & /*r*/) {
            return mc->averageLatencyFetcher();
        }));
    addColumn(std::make_unique<DoubleColumn<TableStatus>>(
        "average_latency_real_time",
        "The average latency for executing real time checks (i.e. the time the start of the execution is behind the schedule)",
        offsets, [mc](const TableStatus & /*r*/) {
            return mc->averageLatencyRealTime();
        }));

    addColumn(std::make_unique<DoubleColumn<TableStatus>>(
        "helper_usage_generic",
        "The average usage of the generic check helpers, ranging from 0.0 (0%) up to 1.0 (100%)",
        offsets,
        [mc](const TableStatus & /*r*/) { return mc->helperUsageGeneric(); }));
    addColumn(std::make_unique<DoubleColumn<TableStatus>>(
        "helper_usage_cmk",
        "The average usage of the Check_MK check helpers, ranging from 0.0 (0%) up to 1.0 (100%)",
        offsets,
        [mc](const TableStatus & /*r*/) { return mc->helperUsageCmk(); }));
    addColumn(std::make_unique<DoubleColumn<TableStatus>>(
        "helper_usage_real_time",
        "The average usage of the real time check helpers, ranging from 0.0 (0%) up to 1.0 (100%)",
        offsets,
        [mc](const TableStatus & /*r*/) { return mc->helperUsageRealTime(); }));
    addColumn(std::make_unique<DoubleColumn<TableStatus>>(
        "helper_usage_fetcher",
        "The average usage of the fetcher helpers, ranging from 0.0 (0%) up to 1.0 (100%)",
        offsets,
        [mc](const TableStatus & /*r*/) { return mc->helperUsageFetcher(); }));
    addColumn(std::make_unique<DoubleColumn<TableStatus>>(
        "helper_usage_checker",
        "The average usage of the checker helpers, ranging from 0.0 (0%) up to 1.0 (100%)",
        offsets,
        [mc](const TableStatus & /*r*/) { return mc->helperUsageChecker(); }));

    addColumn(std::make_unique<BoolColumn<TableStatus>>(
        "has_event_handlers",
        "Whether or not at alert handler rules are configured (0/1)", offsets,
        [mc](const TableStatus & /*r*/) { return mc->hasEventHandlers(); }));

    addColumn(std::make_unique<BoolColumn<TableStatus>>(
        "is_trial_expired", "Whether or not expired trial of demo version",
        offsets, [mc](const TableStatus & /*r*/) {
            return mc->isTrialExpired(std::chrono::system_clock::now());
        }));

    // Special stuff for Check_MK
    addColumn(std::make_unique<TimeColumn<TableStatus>>(
        "mk_inventory_last",
        "The timestamp of the last time a host has been inventorized by Check_MK HW/SW-Inventory",
        offsets, [mc](const TableStatus & /*r*/) {
            return mk_inventory_last(mc->mkInventoryPath() / ".last");
        }));
    addColumn(std::make_unique<IntColumn<TableStatus>>(
        "num_queued_notifications",
        "The number of queued notifications which have not yet been delivered to the notification helper",
        offsets, [mc](const TableStatus & /*r*/) {
            return static_cast<int32_t>(mc->numQueuedNotifications());
        }));
    addColumn(std::make_unique<IntColumn<TableStatus>>(
        "num_queued_alerts",
        "The number of queued alerts which have not yet been delivered to the alert helper",
        offsets, [mc](const TableStatus & /*r*/) {
            return static_cast<int32_t>(mc->numQueuedAlerts());
        }));
    addColumn(std::make_unique<BlobColumn<TableStatus>>(
        "license_usage_history", "Historic license usage information", offsets,
        BlobFileReader<TableStatus>{
            [mc]() { return mc->licenseUsageHistoryPath(); },
            [](const TableStatus & /*r*/) {
                return std::filesystem::path{};
            }}));
    addColumn(std::make_unique<DoubleColumn<TableStatus>>(
        "average_runnable_jobs_fetcher",
        "The average count of scheduled fetcher jobs which have not yet been processed",
        offsets, [mc](const TableStatus & /*r*/) {
            return mc->averageRunnableJobsChecker();
        }));
    addColumn(std::make_unique<DoubleColumn<TableStatus>>(
        "average_runnable_jobs_checker",
        "The average count of queued replies which have not yet been delivered to the checker helpers",
        offsets, [mc](const TableStatus & /*r*/) {
            return mc->averageRunnableJobsChecker();
        }));
    addColumn(std::make_unique<TimeColumn<TableStatus>>(
        "state_file_created", "The time when state file had been created",
        offsets, [mc](const TableStatus & /*r*/) {
            return mc->stateFileCreatedTime();
        }));
}

void TableStatus::addCounterColumns(const std::string &name,
                                    const std::string &description,
                                    const ColumnOffsets &offsets,
                                    Counter which) {
    addColumn(std::make_unique<DoubleColumn<TableStatus>>(
        name, "The number of " + description + " since program start", offsets,
        [which](const TableStatus & /*r*/) { return counterValue(which); }));
    addColumn(std::make_unique<DoubleColumn<TableStatus>>(
        name + "_rate", "The averaged number of " + description + " per second",
        offsets,
        [which](const TableStatus & /*r*/) { return counterRate(which); }));
}

std::string TableStatus::name() const { return "status"; }

std::string TableStatus::namePrefix() const { return "status_"; }

void TableStatus::answerQuery(Query &query, const User & /*user*/) {
    query.processDataset(Row{this});
}

Row TableStatus::getDefault() const { return Row{this}; }
