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
#include "MonitoringCore.h"
#include "nagios.h"

enum class ServiceState { ok = 0, warning = 1, critical = 2, unknown = 3 };

enum class HostState { up = 0, down = 1, unreachable = 2 };

enum class LogEntryType {
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

        // TODO: This class sets different logclasses on match -> fix this
        invalid = 0x7fffffff  // never stored
    };
    static constexpr uint32_t all_classes = 0xffffu;

    unsigned _lineno;  // line number in file
    time_t _time;
    Class _logclass;
    LogEntryType _type;
    char *_complete;   // copy of complete unsplit message
    char *_options;    // points into _complete after ':'
    char *_msg;        // split up with binary zeroes
    char *_text;       // points into msg
    char *_host_name;  // points into msg or is 0
    char *_svc_desc;   // points into msg or is 0
    const char *_command_name;
    char *_contact_name;
    int _state;
    const char *_state_type;
    int _attempt;
    char *_check_output;
    char *_comment;

    host *_host;
    service *_service;
    contact *_contact;
    Command _command;

    LogEntry(MonitoringCore *mc, unsigned lineno, const char *line);
    ~LogEntry();
    unsigned updateReferences(MonitoringCore *mc);
    static ServiceState parseServiceState(const std::string &str);
    static HostState parseHostState(const std::string &str);

private:
    enum class Param {
        HostName,
        SvcDesc,
        CommandName,
        ContactName,
        HostState,
        ServiceState,
        State,
        StateType,
        Attempt,
        Comment,
        CheckOutput
    };

    struct LogDef {
        std::string prefix;
        Class log_class;
        LogEntryType log_type;
        std::vector<Param> params;
    };

    static std::vector<LogDef> log_definitions;

    bool assign(Param par, char **scan);
    void applyWorkarounds();
    bool classifyLogMessage();

    bool handleProgrammEntry();
    bool handleTextEntry();
};

#endif  // LogEntry_h
