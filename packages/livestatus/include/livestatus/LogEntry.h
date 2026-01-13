// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef LogEntry_h
#define LogEntry_h

#include <chrono>
#include <cstddef>
#include <string>
#include <string_view>

#include "livestatus/Interface.h"

inline double badness(ServiceState state) {
    // unknown is effectively between warning and critical
    return state == ServiceState::unknown
               ? (static_cast<double>(ServiceState::warning) +
                  static_cast<double>(ServiceState::critical)) /
                     2.0
               : static_cast<double>(state);
}

inline bool worse(ServiceState state1, ServiceState state2) {
    return badness(state1) > badness(state2);
}

enum class HostState { up = 0, down = 1, unreachable = 2 };

inline double badness(HostState state) {
    // unreachable is effectively between up and down
    return state == HostState::unreachable
               ? (static_cast<double>(HostState::up) +
                  static_cast<double>(HostState::down)) /
                     2.0
               : static_cast<double>(state);
}

inline bool worse(HostState state1, HostState state2) {
    return badness(state1) > badness(state2);
}

enum class LogEntryKind {
    none,
    host_alert,
    service_alert,
    host_downtime_alert,
    service_downtime_alert,
    current_host_state,
    initial_host_state,
    current_service_state,
    initial_service_state,
    host_flapping_alert,
    service_flapping_alert,
    timeperiod_transition,
    core_starting,
    core_stopping,
    log_version,
    logging_initial_states,
    host_acknowledge_alert,
    service_acknowledge_alert
};

enum class LogEntryParam {
    HostName,
    ServiceDescription,
    CommandName,
    CommandNameWithWorkaround,
    ContactName,
    HostState,
    ServiceState,
    ExitCode,
    State,
    StateType,
    Attempt,
    Comment,
    PluginOutput,
    LongPluginOutput,
    Ignore
};

class LogEntry {
public:
    // NOTE: We have to keep this enum in sync with the table in
    // cmk.gui.query_filters.log_class_options() on the Python side.
    enum class Class {
        // all messages not in any other class
        info = 0,

        // {HOST,SERVICE}{, DOWNTIME, ACKNOWLEDGE, FLAPPING} ALERT
        alert = 1,

        // LOG VERSION: 2.0*, logging in{,t}itial states*,
        // *starting...*, *active mode...*,
        // *shutting down...*, *Bailing out*, *standby mode...*
        program = 2,

        // {HOST,SERVICE} NOTIFICATION{, RESULT, PROGRESS}
        hs_notification = 3,

        // PASSIVE {HOST,SERVICE} CHECK
        passivecheck = 4,

        // EXTERNAL COMMAND
        ext_command = 5,

        // {INITIAL,CURRENT} {HOST,SERVICE} STATE, TIMEPERIOD TRANSITION
        state = 6,

        // specific text passages, seems to be unused
        // text = 7

        // {HOST,SERVICE} ALERT HANDLER {STARTED,STOPPED}
        alert_handlers = 8,
    };

    /// Constructed by Logfile::processLogLine(). All instances owned by
    /// Logfile::_entries.
    /// Throws invalid_argument on malformed line
    LogEntry(size_t lineno, std::string line);

    [[nodiscard]] std::string state_info() const;
    static ServiceState parseServiceState(std::string_view str);
    static HostState parseHostState(std::string_view str);

    [[nodiscard]] size_t lineno() const { return lineno_; }
    [[nodiscard]] std::chrono::system_clock::time_point time() const {
        return time_;
    }
    [[nodiscard]] Class log_class() const { return class_; }
    [[nodiscard]] LogEntryKind kind() const { return kind_; }
    [[nodiscard]] std::string message() const { return message_; }
    [[nodiscard]] std::string options() const { return std::string{options_}; }
    [[nodiscard]] std::string type() const { return std::string{type_}; }
    [[nodiscard]] std::string host_name() const {
        return std::string{host_name_};
    }
    [[nodiscard]] std::string service_description() const {
        return std::string{service_description_};
    }
    [[nodiscard]] std::string command_name() const {
        return std::string{command_name_};
    }
    [[nodiscard]] std::string contact_name() const {
        return std::string{contact_name_};
    }
    [[nodiscard]] int state() const { return state_; }
    [[nodiscard]] std::string state_type() const {
        return std::string{state_type_};
    }
    [[nodiscard]] int attempt() const { return attempt_; }
    [[nodiscard]] std::string comment() const { return std::string{comment_}; }
    [[nodiscard]] std::string plugin_output() const {
        return std::string{plugin_output_};
    }
    [[nodiscard]] std::string long_plugin_output() const;
    // See also `cmc::MonitoringLog::decode()`
    static std::string encode(const std::string &str);

private:
    size_t lineno_;
    std::chrono::system_clock::time_point time_;
    Class class_;
    LogEntryKind kind_;
    std::string message_;
    // NOTE: The string_views below all reference message_.
    std::string_view options_;
    std::string_view type_;
    std::string_view host_name_;
    std::string_view service_description_;
    std::string_view command_name_;
    std::string_view contact_name_;
    int state_;
    std::string_view state_type_;
    int attempt_;
    std::string_view comment_;
    std::string_view plugin_output_;
    std::string_view long_plugin_output_;

    void assign(LogEntryParam par, std::string_view field);
    void classifyLogMessage();
    [[nodiscard]] bool textStartsWith(const std::string &what) const;
    [[nodiscard]] bool textContains(const std::string &what) const;
};

#endif  // LogEntry_h
