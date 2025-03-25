// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef ICore_h
#define ICore_h

#include <chrono>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <memory>
#include <string>
#include <vector>

#include "livestatus/Metric.h"
enum class Encoding;
class IComment;
class IContact;
class IContactGroup;
class IDowntime;
class IGlobalFlags;
class IHost;
class IHostGroup;
class IPaths;
class IService;
class IServiceGroup;
class ITimeperiod;
class Triggers;
class Logger;
class User;

// Livestatus view onto a command definition, regardless of the monitoring core
struct Command {
    std::string _name;
    std::string _command_line;
};

/// An abstraction layer for the monitoring core (nagios or cmc)
class ICore {
public:
    virtual ~ICore() = default;

    [[nodiscard]] virtual const IHost *find_host(
        const std::string &name) const = 0;
    [[nodiscard]] virtual const IHostGroup *find_hostgroup(
        const std::string &name) const = 0;
    [[nodiscard]] virtual const IHost *getHostByDesignation(
        const std::string &designation) const = 0;
    virtual bool all_of_hosts(
        const std::function<bool(const IHost &)> &pred) const = 0;
    virtual bool all_of_services(
        const std::function<bool(const IService &)> &pred) const = 0;

    [[nodiscard]] virtual const IService *find_service(
        const std::string &host_name,
        const std::string &service_description) const = 0;
    [[nodiscard]] virtual const IContactGroup *find_contactgroup(
        const std::string &name) const = 0;

    [[nodiscard]] virtual const IServiceGroup *find_servicegroup(
        const std::string &name) const = 0;

    [[nodiscard]] virtual const IContact *find_contact(
        const std::string &name) const = 0;
    virtual bool all_of_contacts(
        const std::function<bool(const IContact &)> &pred) const = 0;

    [[nodiscard]] virtual std::unique_ptr<const User> find_user(
        const std::string &name) const = 0;

    [[nodiscard]] virtual std::chrono::system_clock::time_point
    last_logfile_rotation() const = 0;
    [[nodiscard]] virtual std::chrono::system_clock::time_point
    last_config_change() const = 0;
    [[nodiscard]] virtual size_t maxLinesPerLogFile() const = 0;

    [[nodiscard]] virtual Command find_command(
        const std::string &name) const = 0;
    [[nodiscard]] virtual std::vector<Command> commands() const = 0;

    [[nodiscard]] virtual std::vector<std::unique_ptr<const IComment>>
    comments_unlocked(const IHost &) const = 0;
    [[nodiscard]] virtual std::vector<std::unique_ptr<const IComment>> comments(
        const IHost &) const = 0;
    [[nodiscard]] virtual std::vector<std::unique_ptr<const IComment>>
    comments_unlocked(const IService &) const = 0;
    [[nodiscard]] virtual std::vector<std::unique_ptr<const IComment>> comments(
        const IService &) const = 0;
    bool virtual all_of_comments(
        const std::function<bool(const IComment &)> &pred) const = 0;

    [[nodiscard]] virtual std::vector<std::unique_ptr<const IDowntime>>
    downtimes_unlocked(const IHost &) const = 0;
    [[nodiscard]] virtual std::vector<std::unique_ptr<const IDowntime>>
    downtimes(const IHost &) const = 0;
    [[nodiscard]] virtual std::vector<std::unique_ptr<const IDowntime>>
    downtimes_unlocked(const IService &) const = 0;
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

    [[nodiscard]] virtual bool mkeventdEnabled() const = 0;

    [[nodiscard]] virtual int32_t pid() const = 0;
    [[nodiscard]] virtual std::unique_ptr<const IGlobalFlags> globalFlags()
        const = 0;
    [[nodiscard]] virtual std::unique_ptr<const IPaths> paths() const = 0;
    virtual void dumpPaths(Logger *logger) const;
    [[nodiscard]] virtual std::chrono::system_clock::time_point
    programStartTime() const = 0;
    [[nodiscard]] virtual std::chrono::system_clock::time_point
    lastCommandCheckTime() const = 0;
    [[nodiscard]] virtual int32_t intervalLength() const = 0;
    [[nodiscard]] virtual int32_t maxLongOutputSize() const = 0;
    [[nodiscard]] virtual int32_t numHosts() const = 0;
    [[nodiscard]] virtual int32_t numServices() const = 0;
    [[nodiscard]] virtual std::string programVersion() const = 0;
    [[nodiscard]] virtual std::string edition() const = 0;

    [[nodiscard]] virtual int32_t externalCommandBufferSlots() const = 0;
    [[nodiscard]] virtual int32_t externalCommandBufferUsage() const = 0;
    [[nodiscard]] virtual int32_t externalCommandBufferMax() const = 0;

    [[nodiscard]] virtual int32_t livestatusActiveConnectionsNum() const = 0;
    [[nodiscard]] virtual std::string livestatusVersion() const = 0;
    [[nodiscard]] virtual int32_t livestatusQueuedConnectionsNum() const = 0;
    [[nodiscard]] virtual int32_t livestatusThreadsNum() const = 0;
    [[nodiscard]] virtual double livestatusUsage() const = 0;

    [[nodiscard]] virtual double averageLatencyGeneric() const = 0;
    [[nodiscard]] virtual double averageLatencyRealTime() const = 0;
    [[nodiscard]] virtual double averageLatencyFetcher() const = 0;
    [[nodiscard]] virtual double averageLatencyChecker() const = 0;

    [[nodiscard]] virtual double helperUsageGeneric() const = 0;
    [[nodiscard]] virtual double helperUsageRealTime() const = 0;
    [[nodiscard]] virtual double helperUsageFetcher() const = 0;
    [[nodiscard]] virtual double helperUsageChecker() const = 0;

    [[nodiscard]] virtual bool hasEventHandlers() const = 0;

    [[nodiscard]] virtual double averageRunnableJobsFetcher() const = 0;
    [[nodiscard]] virtual double averageRunnableJobsChecker() const = 0;

    [[nodiscard]] virtual std::chrono::system_clock::time_point
    stateFileCreatedTime() const = 0;
    [[nodiscard]] virtual std::vector<std::string> metrics(
        const IHost &) const = 0;
    [[nodiscard]] virtual std::vector<std::string> metrics(
        const IService &) const = 0;

    [[nodiscard]] virtual Encoding dataEncoding() const = 0;
    [[nodiscard]] virtual size_t maxResponseSize() const = 0;
    [[nodiscard]] virtual size_t maxCachedMessages() const = 0;

    [[nodiscard]] virtual Logger *loggerCore() const = 0;
    [[nodiscard]] virtual Logger *loggerLivestatus() const = 0;
    [[nodiscard]] virtual Logger *loggerRRD() const = 0;

    virtual Triggers &triggers() = 0;

    [[nodiscard]] virtual size_t numQueuedNotifications() const = 0;
    [[nodiscard]] virtual size_t numQueuedAlerts() const = 0;
    // TODO(sp) This should really be const!
    [[nodiscard]] virtual size_t numCachedLogMessages() = 0;

    [[nodiscard]] virtual bool isPnpGraphPresent(const IHost &) const = 0;
    [[nodiscard]] virtual bool isPnpGraphPresent(const IService &s) const = 0;

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

#endif  // ICore_h
