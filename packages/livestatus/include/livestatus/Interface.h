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
class IHostGroup;
class IServiceGroup;

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

enum class ServiceState { ok = 0, warning = 1, critical = 2, unknown = 3 };

class IContact {
public:
    virtual ~IContact() = default;
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

class IContactGroup {
public:
    virtual ~IContactGroup() = default;
    [[nodiscard]] virtual bool isMember(const IContact &) const = 0;
    [[nodiscard]] virtual std::string name() const = 0;
    [[nodiscard]] virtual std::string alias() const = 0;
    [[nodiscard]] virtual std::vector<std::string> contactNames() const = 0;
};

class IHost {
public:
    virtual ~IHost() = default;
    [[nodiscard]] virtual const void *handleForStateHistory() const = 0;
    [[nodiscard]] virtual bool hasContact(const IContact &) const = 0;
    [[nodiscard]] virtual std::string notificationPeriodName() const = 0;
    [[nodiscard]] virtual std::string servicePeriodName() const = 0;

    [[nodiscard]] virtual std::string name() const = 0;
    [[nodiscard]] virtual std::string display_name() const = 0;
    [[nodiscard]] virtual std::string alias() const = 0;
    [[nodiscard]] virtual std::string ip_address() const = 0;
    [[nodiscard]] virtual std::string check_command() const = 0;
    [[nodiscard]] virtual std::string check_command_expanded() const = 0;
    [[nodiscard]] virtual std::string event_handler() const = 0;
    [[nodiscard]] virtual std::string notification_period() const = 0;
    [[nodiscard]] virtual std::string check_period() const = 0;
    [[nodiscard]] virtual std::string notes() const = 0;
    [[nodiscard]] virtual std::string notes_expanded() const = 0;
    [[nodiscard]] virtual std::string notes_url() const = 0;
    [[nodiscard]] virtual std::string notes_url_expanded() const = 0;
    [[nodiscard]] virtual std::string action_url() const = 0;
    [[nodiscard]] virtual std::string action_url_expanded() const = 0;
    [[nodiscard]] virtual std::string plugin_output() const = 0;
    [[nodiscard]] virtual std::string perf_data() const = 0;
    [[nodiscard]] virtual std::string icon_image() const = 0;
    [[nodiscard]] virtual std::string icon_image_expanded() const = 0;
    [[nodiscard]] virtual std::string icon_image_alt() const = 0;
    [[nodiscard]] virtual std::string status_map_image() const = 0;
    [[nodiscard]] virtual std::string long_plugin_output() const = 0;
    [[nodiscard]] virtual int32_t initial_state() const = 0;
    [[nodiscard]] virtual int32_t max_check_attempts() const = 0;
    [[nodiscard]] virtual bool flap_detection_enabled() const = 0;
    [[nodiscard]] virtual bool check_freshness() const = 0;
    [[nodiscard]] virtual bool process_performance_data() const = 0;
    [[nodiscard]] virtual bool accept_passive_host_checks() const = 0;
    [[nodiscard]] virtual int32_t event_handler_enabled() const = 0;
    [[nodiscard]] virtual int32_t acknowledgement_type() const = 0;
    [[nodiscard]] virtual int32_t check_type() const = 0;
    [[nodiscard]] virtual int32_t last_state() const = 0;
    [[nodiscard]] virtual int32_t last_hard_state() const = 0;
    [[nodiscard]] virtual int32_t current_attempt() const = 0;
    [[nodiscard]] virtual std::chrono::system_clock::time_point
    last_notification() const = 0;
    [[nodiscard]] virtual std::chrono::system_clock::time_point
    next_notification() const = 0;
    [[nodiscard]] virtual std::chrono::system_clock::time_point next_check()
        const = 0;
    [[nodiscard]] virtual std::chrono::system_clock::time_point
    last_hard_state_change() const = 0;
    [[nodiscard]] virtual bool has_been_checked() const = 0;
    [[nodiscard]] virtual int32_t current_notification_number() const = 0;
    [[nodiscard]] virtual int32_t pending_flex_downtime() const = 0;
    [[nodiscard]] virtual int32_t total_services() const = 0;
    [[nodiscard]] virtual bool notifications_enabled() const = 0;
    [[nodiscard]] virtual bool problem_has_been_acknowledged() const = 0;
    [[nodiscard]] virtual int32_t current_state() const = 0;
    [[nodiscard]] virtual int32_t hard_state() const = 0;
    [[nodiscard]] virtual int32_t state_type() const = 0;
    [[nodiscard]] virtual int32_t no_more_notifications() const = 0;
    [[nodiscard]] virtual int32_t check_flapping_recovery_notification()
        const = 0;
    [[nodiscard]] virtual std::chrono::system_clock::time_point last_check()
        const = 0;
    [[nodiscard]] virtual std::chrono::system_clock::time_point
    last_state_change() const = 0;
    [[nodiscard]] virtual std::chrono::system_clock::time_point last_time_up()
        const = 0;
    [[nodiscard]] virtual std::chrono::system_clock::time_point last_time_down()
        const = 0;
    [[nodiscard]] virtual std::chrono::system_clock::time_point
    last_time_unreachable() const = 0;

    [[nodiscard]] virtual bool is_flapping() const = 0;
    [[nodiscard]] virtual int32_t scheduled_downtime_depth() const = 0;
    [[nodiscard]] virtual bool is_executing() const = 0;
    [[nodiscard]] virtual bool active_checks_enabled() const = 0;
    [[nodiscard]] virtual int32_t check_options() const = 0;
    [[nodiscard]] virtual int32_t obsess_over_host() const = 0;
    [[nodiscard]] virtual uint32_t modified_attributes() const = 0;
    [[nodiscard]] virtual double check_interval() const = 0;
    [[nodiscard]] virtual double retry_interval() const = 0;
    [[nodiscard]] virtual double notification_interval() const = 0;
    [[nodiscard]] virtual double first_notification_delay() const = 0;
    [[nodiscard]] virtual double low_flap_threshold() const = 0;
    [[nodiscard]] virtual double high_flap_threshold() const = 0;
    [[nodiscard]] virtual double x_3d() const = 0;
    [[nodiscard]] virtual double y_3d() const = 0;
    [[nodiscard]] virtual double z_3d() const = 0;
    [[nodiscard]] virtual double latency() const = 0;
    [[nodiscard]] virtual double execution_time() const = 0;
    [[nodiscard]] virtual double percent_state_change() const = 0;
    [[nodiscard]] virtual double staleness() const = 0;
    [[nodiscard]] virtual double flappiness() const = 0;
    [[nodiscard]] virtual bool in_notification_period() const = 0;
    [[nodiscard]] virtual bool in_check_period() const = 0;
    [[nodiscard]] virtual bool in_service_period() const = 0;
    [[nodiscard]] virtual std::vector<std::string> contacts() const = 0;
    [[nodiscard]] virtual Attributes attributes(AttributeKind kind) const = 0;
    [[nodiscard]] virtual std::string filename() const = 0;
    [[nodiscard]] virtual std::string notification_postponement_reason()
        const = 0;
    [[nodiscard]] virtual int32_t previous_hard_state() const = 0;
    [[nodiscard]] virtual int32_t smartping_timeout() const = 0;

    virtual bool all_of_services(
        std::function<bool(const IService &)> pred) const = 0;
    virtual bool all_of_labels(
        const std::function<bool(const Attribute &)> &pred) const = 0;
    virtual bool all_of_parents(
        std::function<bool(const IHost &)> pred) const = 0;
    virtual bool all_of_children(
        std::function<bool(const IHost &)> pred) const = 0;
    virtual bool all_of_host_groups(
        std::function<bool(const IHostGroup &)> pred) const = 0;
    virtual bool all_of_contact_groups(
        std::function<bool(const IContactGroup &)> pred) const = 0;
};

class IService {
public:
    virtual ~IService() = default;
    [[nodiscard]] virtual const void *handleForStateHistory() const = 0;
    [[nodiscard]] virtual const IHost &host() const = 0;
    [[nodiscard]] virtual bool hasContact(const IContact &) const = 0;

    [[nodiscard]] virtual bool in_custom_time_period() const = 0;

    [[nodiscard]] virtual std::string host_name() const = 0;
    [[nodiscard]] virtual std::string description() const = 0;
    [[nodiscard]] virtual std::string display_name() const = 0;
    [[nodiscard]] virtual std::string check_command() const = 0;
    [[nodiscard]] virtual std::string check_command_expanded() const = 0;
    [[nodiscard]] virtual std::filesystem::path robotmk_dir() const = 0;
    [[nodiscard]] virtual std::string event_handler() const = 0;
    [[nodiscard]] virtual std::string plugin_output() const = 0;
    [[nodiscard]] virtual std::string long_plugin_output() const = 0;
    [[nodiscard]] virtual std::string perf_data() const = 0;
    [[nodiscard]] virtual std::string notificationPeriodName() const = 0;
    [[nodiscard]] virtual std::string check_period() const = 0;
    [[nodiscard]] virtual std::string servicePeriodName() const = 0;
    [[nodiscard]] virtual std::string notes() const = 0;
    [[nodiscard]] virtual std::string notes_expanded() const = 0;
    [[nodiscard]] virtual std::string notes_url() const = 0;
    [[nodiscard]] virtual std::string notes_url_expanded() const = 0;
    [[nodiscard]] virtual std::string action_url() const = 0;
    [[nodiscard]] virtual std::string action_url_expanded() const = 0;
    [[nodiscard]] virtual std::string icon_image() const = 0;
    [[nodiscard]] virtual std::string icon_image_expanded() const = 0;
    [[nodiscard]] virtual std::string icon_image_alt() const = 0;
    [[nodiscard]] virtual int32_t initial_state() const = 0;
    [[nodiscard]] virtual int32_t max_check_attempts() const = 0;
    [[nodiscard]] virtual int32_t current_attempt() const = 0;
    [[nodiscard]] virtual int32_t current_state() const = 0;
    [[nodiscard]] virtual bool has_been_checked() const = 0;
    [[nodiscard]] virtual int32_t last_state() const = 0;
    [[nodiscard]] virtual int32_t last_hard_state() const = 0;
    [[nodiscard]] virtual int32_t state_type() const = 0;
    [[nodiscard]] virtual int32_t check_type() const = 0;
    [[nodiscard]] virtual bool problem_has_been_acknowledged() const = 0;
    [[nodiscard]] virtual int32_t acknowledgement_type() const = 0;
    [[nodiscard]] virtual bool no_more_notifications() const = 0;
    [[nodiscard]] virtual std::chrono::system_clock::time_point last_time_ok()
        const = 0;
    [[nodiscard]] virtual std::chrono::system_clock::time_point
    last_time_warning() const = 0;
    [[nodiscard]] virtual std::chrono::system_clock::time_point
    last_time_critical() const = 0;
    [[nodiscard]] virtual std::chrono::system_clock::time_point
    last_time_unknown() const = 0;
    [[nodiscard]] virtual std::chrono::system_clock::time_point last_check()
        const = 0;
    [[nodiscard]] virtual std::chrono::system_clock::time_point next_check()
        const = 0;
    [[nodiscard]] virtual std::chrono::system_clock::time_point
    last_notification() const = 0;
    [[nodiscard]] virtual std::chrono::system_clock::time_point
    next_notification() const = 0;
    [[nodiscard]] virtual int32_t current_notification_number() const = 0;
    [[nodiscard]] virtual std::chrono::system_clock::time_point
    last_state_change() const = 0;
    [[nodiscard]] virtual std::chrono::system_clock::time_point
    last_hard_state_change() const = 0;
    [[nodiscard]] virtual int32_t scheduled_downtime_depth() const = 0;
    [[nodiscard]] virtual bool is_flapping() const = 0;
    [[nodiscard]] virtual bool checks_enabled() const = 0;
    [[nodiscard]] virtual bool accept_passive_checks() const = 0;
    [[nodiscard]] virtual bool event_handler_enabled() const = 0;
    [[nodiscard]] virtual bool notifications_enabled() const = 0;
    [[nodiscard]] virtual bool process_performance_data() const = 0;
    [[nodiscard]] virtual bool is_executing() const = 0;
    [[nodiscard]] virtual bool active_checks_enabled() const = 0;
    [[nodiscard]] virtual int32_t check_options() const = 0;
    [[nodiscard]] virtual bool flap_detection_enabled() const = 0;
    [[nodiscard]] virtual bool check_freshness() const = 0;
    [[nodiscard]] virtual bool obsess_over_service() const = 0;
    [[nodiscard]] virtual uint32_t modified_attributes() const = 0;
    [[nodiscard]] virtual int32_t hard_state() const = 0;
    [[nodiscard]] virtual double staleness() const = 0;
    [[nodiscard]] virtual double check_interval() const = 0;
    [[nodiscard]] virtual double retry_interval() const = 0;
    [[nodiscard]] virtual double notification_interval() const = 0;
    [[nodiscard]] virtual double first_notification_delay() const = 0;
    [[nodiscard]] virtual double low_flap_threshold() const = 0;
    [[nodiscard]] virtual double high_flap_threshold() const = 0;
    [[nodiscard]] virtual double latency() const = 0;
    [[nodiscard]] virtual double execution_time() const = 0;
    [[nodiscard]] virtual double percent_state_change() const = 0;
    [[nodiscard]] virtual bool in_check_period() const = 0;
    [[nodiscard]] virtual bool in_service_period() const = 0;
    [[nodiscard]] virtual bool in_notification_period() const = 0;
    [[nodiscard]] virtual std::vector<std::string> contacts() const = 0;
    [[nodiscard]] virtual Attributes attributes(AttributeKind kind) const = 0;

    virtual bool all_of_service_groups(
        std::function<bool(const IServiceGroup &)> pred) const = 0;
    virtual bool all_of_contact_groups(
        std::function<bool(const IContactGroup &)> pred) const = 0;

    [[nodiscard]] virtual std::chrono::system_clock::time_point cached_at()
        const = 0;
    [[nodiscard]] virtual int32_t cache_interval() const = 0;
    [[nodiscard]] virtual bool in_passive_check_period() const = 0;
    [[nodiscard]] virtual std::string passive_check_period() const = 0;
    [[nodiscard]] virtual double flappiness() const = 0;
    [[nodiscard]] virtual std::string notification_postponement_reason()
        const = 0;
    [[nodiscard]] virtual int32_t previous_hard_state() const = 0;
    [[nodiscard]] virtual int32_t pending_flex_downtime() const = 0;
    [[nodiscard]] virtual bool check_flapping_recovery_notification() const = 0;

    virtual bool all_of_labels(
        const std::function<bool(const Attribute &)> &pred) const = 0;
};

class IHostGroup {
public:
    virtual ~IHostGroup() = default;
    [[nodiscard]] virtual std::string name() const = 0;
    [[nodiscard]] virtual std::string alias() const = 0;
    [[nodiscard]] virtual std::string notes() const = 0;
    [[nodiscard]] virtual std::string notes_url() const = 0;
    [[nodiscard]] virtual std::string action_url() const = 0;
    virtual bool all(const std::function<bool(const IHost &)> &pred) const = 0;
};

class IServiceGroup {
public:
    virtual ~IServiceGroup() = default;
    [[nodiscard]] virtual std::string name() const = 0;
    [[nodiscard]] virtual std::string alias() const = 0;
    [[nodiscard]] virtual std::string notes() const = 0;
    [[nodiscard]] virtual std::string notes_url() const = 0;
    [[nodiscard]] virtual std::string action_url() const = 0;
    virtual bool all(
        const std::function<bool(const IService &)> &pred) const = 0;
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
    [[nodiscard]] virtual std::filesystem::path prediction_directory()
        const = 0;
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
