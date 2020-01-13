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

#ifndef LogEntry_h
#define LogEntry_h

#include "config.h"  // IWYU pragma: keep
#include <cstdint>
#include <ctime>
#include <string>
#include <vector>

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
    enum class Class {
        info = 0,             // all messages not in any other class
        alert = 1,            // alerts: the change service/host state
        program = 2,          // important programm events (restart, ...)
        hs_notification = 3,  // host/service notifications
        passivecheck = 4,     // passive checks
        ext_command = 5,      // external commands
        state = 6,            // initial or current states
        text = 7,             // specific text passages
        alert_handlers = 8,   // Started and stopped alert handlers

        // TODO(sp): This class sets different logclasses on match -> fix this
        invalid = 0x7fffffff  // never stored
    };
    static constexpr uint32_t all_classes = 0xffffu;

    // TODO(sp): Wrong type, caused by TableLog accessing it via
    // OffsetIntColumn, should be size_t
    int _lineno;  // line number in file
    time_t _time;
    Class _class;
    LogEntryKind _kind;
    std::string _message;  // copy of complete unsplit message
    const char *_options;  // points into _complete after ':'
    const char *_type;     // points into _complete or into static data
    std::string _host_name;
    std::string _service_description;
    std::string _command_name;
    std::string _contact_name;
    int _state;
    std::string _state_type;
    int _attempt;
    std::string _comment;
    std::string _plugin_output;
    std::string _long_plugin_output;

    // NOTE: line gets modified!
    LogEntry(size_t lineno, std::string line);
    [[nodiscard]] std::string state_info() const;
    static ServiceState parseServiceState(const std::string &str);
    static HostState parseHostState(const std::string &str);

private:
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

    static std::vector<LogDef> log_definitions;

    void assign(Param par, const std::string &field);
    void classifyLogMessage();
    bool textStartsWith(const std::string &what);
    bool textContains(const std::string &what);
};

#endif  // LogEntry_h
