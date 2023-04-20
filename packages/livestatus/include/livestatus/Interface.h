// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef Interface_h
#define Interface_h

#include <chrono>
#include <filesystem>
#include <functional>
#include <memory>
#include <string>
#include <unordered_map>
#include <vector>

class IService;

using Attributes = std::unordered_map<std::string, std::string>;
enum class AttributeKind { custom_variables, tags, labels, label_sources };

struct Attribute {
    const std::string &name;
    const std::string &value;

    bool operator==(const Attribute &other) const {
        return name == other.name && value == other.value;
    }
    bool operator!=(const Attribute &other) const { return !(*this == other); }
};

template <>
struct std::hash<Attribute> {
    std::size_t operator()(const Attribute &a) const {
        std::size_t seed{0};
        // Taken from WG21 P0814R2, an epic story about a triviality...
        auto hash_combine = [&seed](const std::string &val) {
            seed ^= std::hash<std::string>{}(val) + 0x9e3779b9 + (seed << 6) +
                    (seed >> 2);
        };
        hash_combine(a.name);
        hash_combine(a.value);
        return seed;
    }
};

class IContact {
public:
    virtual ~IContact() = default;
    [[nodiscard]] virtual const void *handle() const = 0;
    [[nodiscard]] virtual std::string name() const = 0;
    [[nodiscard]] virtual std::string alias() const = 0;
    [[nodiscard]] virtual std::string email() const = 0;
    [[nodiscard]] virtual std::string pager() const = 0;
    [[nodiscard]] virtual std::string hostNotificationPeriod() const = 0;
    [[nodiscard]] virtual std::string serviceNotificationPeriod() const = 0;
    [[nodiscard]] virtual std::string address(int32_t index) const = 0;
    [[nodiscard]] virtual bool canSubmitCommands() const = 0;
    [[nodiscard]] virtual bool isHostNotificationsEnabled() const = 0;
    [[nodiscard]] virtual bool isServiceNotificationsEnabled() const = 0;
    [[nodiscard]] virtual bool isInHostNotificationPeriod() const = 0;
    [[nodiscard]] virtual bool isInServiceNotificationPeriod() const = 0;
    [[nodiscard]] virtual Attributes customVariables() const = 0;
    [[nodiscard]] virtual Attributes tags() const = 0;
    [[nodiscard]] virtual Attributes labels() const = 0;
    [[nodiscard]] virtual Attributes labelSources() const = 0;
    [[nodiscard]] virtual uint32_t modifiedAttributes() const = 0;
    virtual bool all_of_labels(
        const std::function<bool(const Attribute &)> &pred) const = 0;
};

class IHost {
public:
    virtual ~IHost() = default;
    [[nodiscard]] virtual bool hasContact(const IContact &) const = 0;
    [[nodiscard]] virtual const void *handle() const = 0;
    [[nodiscard]] virtual std::string notificationPeriodName() const = 0;
    [[nodiscard]] virtual std::string servicePeriodName() const = 0;
    virtual bool all_of_services(
        std::function<bool(const IService &)> pred) const = 0;
    virtual bool all_of_labels(
        const std::function<bool(const Attribute &)> &pred) const = 0;
};

class IService {
public:
    virtual ~IService() = default;
    [[nodiscard]] virtual bool hasContact(const IContact &) const = 0;
    [[nodiscard]] virtual bool hasHostContact(const IContact &) const = 0;
    [[nodiscard]] virtual const void *handle() const = 0;
    [[nodiscard]] virtual std::string notificationPeriodName() const = 0;
    [[nodiscard]] virtual std::string servicePeriodName() const = 0;
    virtual bool all_of_labels(
        const std::function<bool(const Attribute &)> &pred) const = 0;
};

class IHostGroup {
public:
    virtual ~IHostGroup() = default;
    [[nodiscard]] virtual const void *handle() const = 0;
    virtual bool all(const std::function<bool(const IHost &)> &pred) const = 0;
};

class IServiceGroup {
public:
    virtual ~IServiceGroup() = default;
    [[nodiscard]] virtual const void *handle() const = 0;
    virtual bool all(
        const std::function<bool(const IService &)> &pred) const = 0;
};

class IContactGroup {
public:
    virtual ~IContactGroup() = default;
    [[nodiscard]] virtual const void *handle() const = 0;
    [[nodiscard]] virtual bool isMember(const IContact &) const = 0;
    [[nodiscard]] virtual std::string name() const = 0;
    [[nodiscard]] virtual std::string alias() const = 0;
    [[nodiscard]] virtual std::vector<std::string> contactNames() const = 0;
};

class ITimeperiod {
public:
    virtual ~ITimeperiod() = default;
    [[nodiscard]] virtual std::string name() const = 0;
    [[nodiscard]] virtual std::string alias() const = 0;
    [[nodiscard]] virtual bool isActive() const = 0;
    [[nodiscard]] virtual std::vector<std::chrono::system_clock::time_point>
    transitions(std::chrono::seconds timezone_offset) const = 0;
    [[nodiscard]] virtual int32_t numTransitions() const = 0;
    [[nodiscard]] virtual int32_t nextTransitionId() const = 0;
    [[nodiscard]] virtual std::chrono::system_clock::time_point
    nextTransitionTime() const = 0;
};

enum class CommentType : int32_t {
    user = 1,
    downtime = 2,
    flapping = 3,
    acknowledgement = 4
};

enum class CommentSource : int32_t { internal = 0, external = 1 };

class IComment {
public:
    virtual ~IComment() = default;
    [[nodiscard]] virtual int32_t id() const = 0;
    [[nodiscard]] virtual std::string author() const = 0;
    [[nodiscard]] virtual std::string comment() const = 0;
    [[nodiscard]] virtual CommentType entry_type() const = 0;
    [[nodiscard]] virtual std::chrono::system_clock::time_point entry_time()
        const = 0;

    [[nodiscard]] virtual bool isService() const = 0;
    [[nodiscard]] bool isHost() const { return !isService(); };
    [[nodiscard]] virtual bool persistent() const = 0;
    [[nodiscard]] virtual CommentSource source() const = 0;
    [[nodiscard]] virtual std::chrono::system_clock::time_point expire_time()
        const = 0;
    [[nodiscard]] virtual bool expires() const = 0;

    [[nodiscard]] virtual const IHost &host() const = 0;
    [[nodiscard]] virtual const IService *service() const = 0;
};

enum class RecurringKind : int32_t {
    none = 0,
    hourly = 1,
    daily = 2,
    weekly = 3,
    biweekly = 4,
    every_4weeks = 5,
    nth_weekday = 6,
    nth_weekday_from_end = 7,
    day_of_month = 8,
    every_5min = 999  // just for testing
};

class IDowntime {
public:
    virtual ~IDowntime() = default;
    [[nodiscard]] virtual int32_t id() const = 0;
    [[nodiscard]] virtual std::string author() const = 0;
    [[nodiscard]] virtual std::string comment() const = 0;
    [[nodiscard]] virtual bool origin_is_rule() const = 0;
    [[nodiscard]] virtual std::chrono::system_clock::time_point entry_time()
        const = 0;
    [[nodiscard]] virtual std::chrono::system_clock::time_point start_time()
        const = 0;
    [[nodiscard]] virtual std::chrono::system_clock::time_point end_time()
        const = 0;

    [[nodiscard]] virtual bool isService() const = 0;
    [[nodiscard]] bool isHost() const { return !isService(); };

    [[nodiscard]] virtual bool fixed() const = 0;
    [[nodiscard]] virtual std::chrono::nanoseconds duration() const = 0;
    [[nodiscard]] virtual RecurringKind recurring() const = 0;
    [[nodiscard]] virtual bool pending() const = 0;
    [[nodiscard]] virtual int32_t triggered_by() const = 0;

    [[nodiscard]] virtual const IHost &host() const = 0;
    [[nodiscard]] virtual const IService *service() const = 0;
};

class IPaths {
public:
    virtual ~IPaths() = default;
    [[nodiscard]] virtual std::filesystem::path log_file() const = 0;
    [[nodiscard]] virtual std::filesystem::path crash_reports_directory()
        const = 0;
    [[nodiscard]] virtual std::filesystem::path license_usage_history_file()
        const = 0;
    [[nodiscard]] virtual std::filesystem::path inventory_directory() const = 0;
    [[nodiscard]] virtual std::filesystem::path structured_status_directory()
        const = 0;
    [[nodiscard]] virtual std::filesystem::path robotmk_html_log_directory()
        const = 0;
    [[nodiscard]] virtual std::filesystem::path logwatch_directory() const = 0;
    [[nodiscard]] virtual std::filesystem::path event_console_status_socket()
        const = 0;
    [[nodiscard]] virtual std::filesystem::path livestatus_socket() const = 0;
    [[nodiscard]] virtual std::filesystem::path history_file() const = 0;
    [[nodiscard]] virtual std::filesystem::path history_archive_directory()
        const = 0;
    [[nodiscard]] virtual std::filesystem::path rrd_multiple_directory()
        const = 0;
    [[nodiscard]] virtual std::filesystem::path rrdcached_socket() const = 0;
};

class IGlobalFlags {
public:
    virtual ~IGlobalFlags() = default;
    [[nodiscard]] virtual bool enable_notifications() const = 0;
    [[nodiscard]] virtual bool execute_service_checks() const = 0;
    [[nodiscard]] virtual bool accept_passive_service_checks() const = 0;
    [[nodiscard]] virtual bool execute_host_checks() const = 0;
    [[nodiscard]] virtual bool accept_passive_hostchecks() const = 0;
    [[nodiscard]] virtual bool obsess_over_services() const = 0;
    [[nodiscard]] virtual bool obsess_over_hosts() const = 0;
    [[nodiscard]] virtual bool check_service_freshness() const = 0;
    [[nodiscard]] virtual bool check_host_freshness() const = 0;
    [[nodiscard]] virtual bool enable_flap_detection() const = 0;
    [[nodiscard]] virtual bool process_performance_data() const = 0;
    [[nodiscard]] virtual bool enable_event_handlers() const = 0;
    [[nodiscard]] virtual bool check_external_commands() const = 0;
};

#endif  // Interface_h
