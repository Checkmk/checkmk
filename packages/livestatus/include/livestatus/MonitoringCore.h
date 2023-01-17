// Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef MonitoringCore_h
#define MonitoringCore_h

#include <chrono>
#include <filesystem>
#include <string>
#include <tuple>
#include <unordered_map>
#include <vector>

#include "livestatus/Attributes.h"
#include "livestatus/Interface.h"
#include "livestatus/Metric.h"
#include "livestatus/StringUtils.h"
#include "livestatus/Triggers.h"
#include "livestatus/User.h"
enum class Encoding;
class Logger;

// Livestatus view onto a command definition, regardless of the monitoring core
struct Command {
    std::string _name;
    std::string _command_line;
};

// Livestatus view onto a downtime, regardless of the monitoring core
struct DowntimeData {
    unsigned long _id;
    std::string _author;
    std::string _comment;
    bool _origin_is_rule;
    std::chrono::system_clock::time_point _entry_time;
    std::chrono::system_clock::time_point _start_time;
    std::chrono::system_clock::time_point _end_time;
    bool _fixed;
    std::chrono::nanoseconds _duration;
    int32_t _recurring;
    bool _pending;
};

// Livestatus view onto a comment, regardless of the monitoring core
struct CommentData {
    unsigned long _id;
    std::string _author;
    std::string _comment;
    uint32_t _entry_type;  // CMC: Comment::Type
    std::chrono::system_clock::time_point _entry_time;
};

/// An abstraction layer for the monitoring core (nagios or cmc)
class MonitoringCore {
public:
    virtual ~MonitoringCore() = default;

    virtual std::unique_ptr<const IHost> find_host(const std::string &name) = 0;
    virtual std::unique_ptr<const IHost> getHostByDesignation(
        const std::string &designation) = 0;
    virtual std::unique_ptr<const IService> find_service(
        const std::string &host_name,
        const std::string &service_description) = 0;
    virtual std::unique_ptr<const IContactGroup> find_contactgroup(
        const std::string &name) = 0;
    virtual std::unique_ptr<const IContact> find_contact(
        const std::string &name) = 0;
    virtual std::unique_ptr<User> find_user(const std::string &name) = 0;

    virtual std::chrono::system_clock::time_point last_logfile_rotation() = 0;
    virtual std::chrono::system_clock::time_point last_config_change() = 0;
    [[nodiscard]] virtual size_t maxLinesPerLogFile() const = 0;

    [[nodiscard]] virtual Command find_command(
        const std::string &name) const = 0;
    [[nodiscard]] virtual std::vector<Command> commands() const = 0;

    virtual std::vector<DowntimeData> downtimes(const IHost &) const = 0;
    virtual std::vector<DowntimeData> downtimes(const IService &) const = 0;
    virtual std::vector<CommentData> comments(const IHost &) const = 0;
    virtual std::vector<CommentData> comments(const IService &) const = 0;

    virtual bool mkeventdEnabled() = 0;

    [[nodiscard]] virtual std::filesystem::path mkeventdSocketPath() const = 0;
    [[nodiscard]] virtual std::filesystem::path mkLogwatchPath() const = 0;
    [[nodiscard]] virtual std::filesystem::path mkInventoryPath() const = 0;
    [[nodiscard]] virtual std::filesystem::path structuredStatusPath()
        const = 0;
    [[nodiscard]] virtual std::filesystem::path robotMkHtmlLogPath() const = 0;
    [[nodiscard]] virtual std::filesystem::path crashReportPath() const = 0;
    [[nodiscard]] virtual std::filesystem::path licenseUsageHistoryPath()
        const = 0;
    [[nodiscard]] virtual std::filesystem::path pnpPath() const = 0;
    [[nodiscard]] virtual std::filesystem::path historyFilePath() const = 0;
    [[nodiscard]] virtual std::filesystem::path logArchivePath() const = 0;
    [[nodiscard]] virtual std::filesystem::path rrdcachedSocketPath() const = 0;

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

    // TODO(sp) Horrible and fragile typing of the parameter, we need to fix
    // this: The type of the holder is either 'customvariablesmember *const *'
    // (NEB) or 'const Entity *' (CMC). Furthermore, all we need is a range for
    // iteration, not a copy. The kind parameter is not really OO, either...
    virtual Attributes customAttributes(const void *holder,
                                        AttributeKind kind) const = 0;

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
