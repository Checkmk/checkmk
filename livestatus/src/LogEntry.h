// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef LogEntry_h
#define LogEntry_h

#include "config.h"  // IWYU pragma: keep

#include <chrono>
#include <cstddef>
#include <string>
#include <string_view>
#include <vector>

#include "StringUtils.h"

enum class ServiceState { ok = 0, warning = 1, critical = 2, unknown = 3 };

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
    alert_host,
    alert_service,
    downtime_alert_host,
    downtime_alert_service,
    state_host,
    state_host_initial,
    state_service,
    state_service_initial,
    flapping_host,
    flapping_service,
    timeperiod_transition,
    core_starting,
    core_stopping,
    log_version,
    log_initial_states,
    acknowledge_alert_host,
    acknowledge_alert_service
};

class LogEntry {
public:
    // NOTE: We have to keep this enum in sync with the table in
    // cmk.gui.plugins.visuals.filters.FilterLogClass on the Python side.
    enum class Class {
        info = 0,             // all messages not in any other class
        alert = 1,            // alerts: the change service/host state
        program = 2,          // important programm events (restart, ...)
        hs_notification = 3,  // host/service notifications
        passivecheck = 4,     // passive checks
        ext_command = 5,      // external commands
        state = 6,            // initial or current states
        // text = 7,          // specific text passages, seems to be unused
        alert_handlers = 8,  // Started and stopped alert handlers
    };

    // Constructed by Logfile::processLogLine(). All instances owned by
    // Logfile::_entries.
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
    [[nodiscard]] std::string long_plugin_output() const {
        return mk::to_multi_line(std::string{long_plugin_output_});
    }

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

    enum class Param {
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

    struct LogDef {
        std::string prefix;
        Class log_class;
        LogEntryKind log_type;
        std::vector<Param> params;
    };

    // NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
    static std::vector<LogDef> log_definitions;

    void assign(Param par, std::string_view field);
    void classifyLogMessage();
    [[nodiscard]] bool textStartsWith(const std::string &what) const;
    [[nodiscard]] bool textContains(const std::string &what) const;
};

#endif  // LogEntry_h
