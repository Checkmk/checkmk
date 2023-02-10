// Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef MonitoringCore_h
#define MonitoringCore_h

#include <chrono>
#include <string>

#include "livestatus/Interface.h"
#include "livestatus/Metric.h"
#include "livestatus/Triggers.h"
#include "livestatus/User.h"
enum class Encoding;
class Logger;

// Livestatus view onto a command definition, regardless of the monitoring core
struct Command {
    std::string _name;
    std::string _command_line;
};

struct GlobalFlags {
    bool enable_notifications;
    bool execute_service_checks;
    bool accept_passive_service_checks;
    bool execute_host_checks;
    bool accept_passive_hostchecks;
    bool obsess_over_services;
    bool obsess_over_hosts;
    bool check_service_freshness;
    bool check_host_freshness;
    bool enable_flap_detection;
    bool process_performance_data;
    bool enable_event_handlers;
    bool check_external_commands;
};

struct Paths {
    std::filesystem::path crash_reports_directory;
    std::filesystem::path license_usage_history_file;
    std::filesystem::path inventory_directory;
    std::filesystem::path structured_status_directory;
    std::filesystem::path robotmk_html_log_directory;
    std::filesystem::path logwatch_directory;
    std::filesystem::path mkeventd_socket;
    std::filesystem::path history_file;
    std::filesystem::path history_archive_directory;
    std::filesystem::path rrd_multiple_directory;
    std::filesystem::path rrdcached_socket;
};

/// An abstraction layer for the monitoring core (nagios or cmc)
class MonitoringCore {
public:
    virtual ~MonitoringCore() = default;

    virtual std::unique_ptr<const IHost> find_host(const std::string &name) = 0;
    virtual std::unique_ptr<const IHost> getHostByDesignation(
        const std::string &designation) = 0;
    virtual bool all_of_hosts(
        const std::function<bool(const IHost &)> &pred) const = 0;

    virtual std::unique_ptr<const IService> find_service(
        const std::string &host_name,
        const std::string &service_description) = 0;
    virtual std::unique_ptr<const IContactGroup> find_contactgroup(
        const std::string &name) = 0;

    virtual std::unique_ptr<const IServiceGroup> find_servicegroup(
        const std::string &name) = 0;

    [[nodiscard]] virtual std::unique_ptr<const IContact> find_contact(
        const std::string &name) const = 0;
    virtual bool all_of_contacts(
        const std::function<bool(const IContact &)> &pred) const = 0;

    virtual std::unique_ptr<User> find_user(const std::string &name) = 0;

    [[nodiscard]] virtual std::chrono::system_clock::time_point
    last_logfile_rotation() const = 0;
    [[nodiscard]] virtual std::chrono::system_clock::time_point
    last_config_change() const = 0;
    [[nodiscard]] virtual size_t maxLinesPerLogFile() const = 0;

    [[nodiscard]] virtual Command find_command(
        const std::string &name) const = 0;
    [[nodiscard]] virtual std::vector<Command> commands() const = 0;

    [[nodiscard]] virtual std::vector<std::unique_ptr<const IComment>> comments(
        const IHost &) const = 0;
    [[nodiscard]] virtual std::vector<std::unique_ptr<const IComment>> comments(
        const IService &) const = 0;
    bool virtual all_of_comments(
        const std::function<bool(const IComment &)> &pred) const = 0;
    [[nodiscard]] virtual std::vector<std::unique_ptr<const IDowntime>>
    downtimes(const IHost &) const = 0;
    [[nodiscard]] virtual std::vector<std::unique_ptr<const IDowntime>>
    downtimes(const IService &) const = 0;
    bool virtual all_of_downtimes(
        const std::function<bool(const IDowntime &)> &pred) const = 0;

    bool virtual all_of_timeperiods(
        const std::function<bool(const ITimeperiod &)> &pred) const = 0;

    virtual bool all_of_contact_groups(
        const std::function<bool(const IContactGroup &)> &pred) const = 0;

    virtual bool all_of_host_groups(
        const std::function<bool(const IHostGroup &)> &pred) const = 0;

    virtual bool all_of_service_groups(
        const std::function<bool(const IServiceGroup &)> &pred) const = 0;

    virtual bool mkeventdEnabled() = 0;

    [[nodiscard]] virtual int32_t pid() const = 0;
    [[nodiscard]] virtual GlobalFlags globalFlags() const = 0;
    [[nodiscard]] virtual Paths paths() const = 0;
    [[nodiscard]] virtual std::chrono::system_clock::time_point
    programStartTime() const = 0;
    [[nodiscard]] virtual std::chrono::system_clock::time_point
    lastCommandCheckTime() const = 0;
    [[nodiscard]] virtual int32_t intervalLength() const = 0;
    [[nodiscard]] virtual int32_t numHosts() const = 0;
    [[nodiscard]] virtual int32_t numServices() const = 0;
    [[nodiscard]] virtual std::string programVersion() const = 0;

    [[nodiscard]] virtual int32_t externalCommandBufferSlots() const = 0;
    [[nodiscard]] virtual int32_t externalCommandBufferUsage() const = 0;
    [[nodiscard]] virtual int32_t externalCommandBufferMax() const = 0;

    [[nodiscard]] virtual int32_t livestatusActiveConnectionsNum() const = 0;
    [[nodiscard]] virtual std::string livestatusVersion() const = 0;
    [[nodiscard]] virtual int32_t livestatusQueuedConnectionsNum() const = 0;
    [[nodiscard]] virtual int32_t livestatusThreadsNum() const = 0;
    [[nodiscard]] virtual double livestatusUsage() const = 0;

    [[nodiscard]] virtual double averageLatencyGeneric() const = 0;
    [[nodiscard]] virtual double averageLatencyCmk() const = 0;
    [[nodiscard]] virtual double averageLatencyFetcher() const = 0;
    [[nodiscard]] virtual double averageLatencyRealTime() const = 0;

    [[nodiscard]] virtual double helperUsageGeneric() const = 0;
    [[nodiscard]] virtual double helperUsageCmk() const = 0;
    [[nodiscard]] virtual double helperUsageFetcher() const = 0;
    [[nodiscard]] virtual double helperUsageChecker() const = 0;
    [[nodiscard]] virtual double helperUsageRealTime() const = 0;

    [[nodiscard]] virtual bool hasEventHandlers() const = 0;

    [[nodiscard]] virtual bool isTrialExpired(
        std::chrono::system_clock::time_point now) const = 0;

    [[nodiscard]] virtual double averageRunnableJobsFetcher() const = 0;
    [[nodiscard]] virtual double averageRunnableJobsChecker() const = 0;

    [[nodiscard]] virtual std::chrono::system_clock::time_point
    stateFileCreatedTime() const = 0;

    virtual Encoding dataEncoding() = 0;
    virtual size_t maxResponseSize() = 0;
    virtual size_t maxCachedMessages() = 0;

    virtual Logger *loggerCore() = 0;
    virtual Logger *loggerLivestatus() = 0;
    virtual Logger *loggerRRD() = 0;

    virtual Triggers &triggers() = 0;

    virtual size_t numQueuedNotifications() = 0;
    virtual size_t numQueuedAlerts() = 0;
    virtual size_t numCachedLogMessages() = 0;

    [[nodiscard]] virtual MetricLocation metricLocation(
        const std::string &host_name, const std::string &service_description,
        const Metric::Name &var) const = 0;
    [[nodiscard]] virtual bool pnp4nagiosEnabled() const = 0;

    // Our escape hatch, this should die in the long run...
    template <typename T>
    [[nodiscard]] T *impl() const {
        return static_cast<T *>(implInternal());
    }

private:
    [[nodiscard]] virtual void *implInternal() const = 0;
};

#endif  // MonitoringCore_h
