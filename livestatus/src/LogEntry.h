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
#include <ctime>
#include <string>
#include <vector>
#include "CommandsHolder.h"
#include "nagios.h"

#define LOGCLASS_INFO 0          // all messages not in any other class
#define LOGCLASS_ALERT 1         // alerts: the change service/host state
#define LOGCLASS_PROGRAM 2       // important programm events (restart, ...)
#define LOGCLASS_NOTIFICATION 3  // host/service notifications
#define LOGCLASS_PASSIVECHECK 4  // passive checks
#define LOGCLASS_COMMAND 5       // external commands
#define LOGCLASS_STATE 6         // initial or current states
#define LOGCLASS_TEXT 7  // specific text passages. e.g "logging initial states"
#define LOGCLASS_ALERT_HANDLERS 8  // Started and stopped alert handlers
// TODO: This LOGCLASS sets different logclasses on match -> fix this
#define LOGCLASS_INVALID 0x7fffffff  // never stored
#define LOGCLASS_ALL 0xffff

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
    unsigned _lineno;  // line number in file
    time_t _time;
    unsigned _logclass;
    LogEntryType _type;
    char *_complete;   // copy of complete unsplit message
    char *_options;    // points into _complete after ':'
    char *_msg;        // split up with binary zeroes
    unsigned _msglen;  // size of _msg
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
    CommandsHolder::Command _command;

    LogEntry(const CommandsHolder &commands_holder, unsigned lineno,
             const char *line);
    ~LogEntry();
    unsigned updateReferences(const CommandsHolder &commands_holder);
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
        unsigned log_class;
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
