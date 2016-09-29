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

#include "LogEntry.h"
#include <algorithm>
#include <cstdlib>
#include <cstring>
#include <string>
#include "StringUtils.h"
#include "strutil.h"

using mk::starts_with;
using std::string;

LogEntry::LogEntry(const CommandsHolder &commands_holder, unsigned lineno,
                   const char *line)
    : _type(NONE) {
    // TODO(sp) Fix all handleFooEntry() member functions below to always set
    // all fields and remove this set-me-to-zero-to-be-sure-block.
    _logclass = LOGCLASS_INFO;
    _host_name = nullptr;
    _svc_desc = nullptr;
    _command_name = nullptr;
    _contact_name = nullptr;
    _state = 0;
    _state_type = nullptr;
    _attempt = 0;
    _check_output = nullptr;
    _comment = nullptr;
    _host = nullptr;
    _service = nullptr;
    _contact = nullptr;

    _lineno = lineno;

    // make a copy of the message and strip trailing newline
    _msg = strdup(line);
    _msglen = strlen(line);
    while (_msglen > 0 && _msg[_msglen - 1] == '\n') {
        _msg[--_msglen] = '\0';

        // keep unsplitted copy of the message (needs lots of memory,
        // maybe we could optimize that one day...)
    }
    _complete = strdup(_msg);

    // pointer to options (everything after ':')
    _options = _complete;
    while (*_options != 0 && *_options != ':') {
        _options++;
    }
    if (*_options != 0)  // line contains colon
    {
        _options++;  // skip ':'
        while (*_options == ' ') {
            _options++;  // skip space after ':'
        }
    }

    // [1260722267] xxx - extract timestamp, validate message
    if (_msglen < 13 || _msg[0] != '[' || _msg[11] != ']') {
        _logclass = LOGCLASS_INVALID;
        return;  // ignore invalid lines silently
    }
    _msg[11] = 0;  // zero-terminate time stamp
    _time = atoi(_msg + 1);
    _text = _msg + 13;  // also skip space after timestamp

    if (classifyLogMessage()) {
        updateReferences(commands_holder);
    } else {
        handleTextEntry() || handleProgrammEntry();  // Performance killer
                                                     // strstr in
                                                     // handleProgrammEntry!
    }
    // rest is LOGCLASS_INFO
}

LogEntry::~LogEntry() {
    free(_msg);
    free(_complete);
}

bool LogEntry::assign(Param par, char **scan) {
    switch (par) {
        case Param::HostName:
            this->_host_name = next_token(scan, ';');
            break;
        case Param::SvcDesc:
            this->_svc_desc = next_token(scan, ';');
            break;
        case Param::HostState:
            // textual host state (UP, DOWN, ...)
            this->_state = hostStateToInt(safe_next_token(scan, ';'));
            break;
        case Param::ServiceState:
            // textual service state (OK, WARN, ...)
            this->_state = serviceStateToInt(safe_next_token(scan, ';'));
            break;
        case Param::State:
            // numeric state
            this->_state = atoi(safe_next_token(scan, ';'));
            break;
        case Param::StateType:
            this->_state_type = next_token(scan, ';');
            break;
        case Param::Attempt:
            this->_attempt = atoi(safe_next_token(scan, ';'));
            break;
        case Param::Comment:
            this->_comment = next_token(scan, ';');
            break;
        case Param::CommandName:
            this->_command_name = next_token(scan, ';');
            break;
        case Param::ContactName:
            this->_contact_name = next_token(scan, ';');
            break;
        case Param::CheckOutput:
            this->_check_output = next_token(scan, ';');
            break;
    }

    return true;
};

std::vector<LogEntry::LogDef> LogEntry::log_definitions{
    ////////////////
    LogDef{"INITIAL HOST STATE: ",
           LOGCLASS_ALERT,
           ALERT_HOST,
           {Param::HostName, Param::HostState, Param::StateType, Param::Attempt,
            Param::CheckOutput}},
    ////////////////
    LogDef{"CURRENT HOST STATE: ",
           LOGCLASS_STATE,
           STATE_HOST_INITIAL,
           {Param::HostName, Param::HostState, Param::StateType, Param::Attempt,
            Param::CheckOutput}},
    ////////////////
    LogDef{"HOST ALERT: ",
           LOGCLASS_STATE,
           STATE_HOST,
           {Param::HostName, Param::HostState, Param::StateType, Param::Attempt,
            Param::CheckOutput}},
    ////////////////
    LogDef{"HOST DOWNTIME ALERT: ",
           LOGCLASS_ALERT,
           DOWNTIME_ALERT_HOST,
           {Param::HostName, Param::StateType, Param::Comment}},
    ////////////////
    LogDef{"HOST ACKNOWLEDGE ALERT: ",
           LOGCLASS_ALERT,
           ACKNOWLEDGE_ALERT_HOST,
           {Param::HostName, Param::StateType, Param::ContactName,
            Param::Comment}},
    ////////////////
    LogDef{"HOST FLAPPING ALERT: ",
           LOGCLASS_ALERT,
           FLAPPING_HOST,
           {Param::HostName, Param::StateType, Param::Comment}},
    ////////////////
    LogDef{"INITIAL SERVICE STATE: ",
           LOGCLASS_STATE,
           STATE_SERVICE_INITIAL,
           {Param::HostName, Param::SvcDesc, Param::ServiceState,
            Param::StateType, Param::Attempt, Param::CheckOutput}},
    ////////////////
    LogDef{"CURRENT SERVICE STATE: ",
           LOGCLASS_STATE,
           STATE_SERVICE,
           {Param::HostName, Param::SvcDesc, Param::ServiceState,
            Param::StateType, Param::Attempt, Param::CheckOutput}},
    ////////////////
    LogDef{"SERVICE ALERT: ",
           LOGCLASS_ALERT,
           ALERT_SERVICE,
           {Param::HostName, Param::SvcDesc, Param::ServiceState,
            Param::StateType, Param::Attempt, Param::CheckOutput}},
    ////////////////
    LogDef{"SERVICE DOWNTIME ALERT: ",
           LOGCLASS_ALERT,
           DOWNTIME_ALERT_SERVICE,
           {Param::HostName, Param::SvcDesc, Param::StateType, Param::Comment}},
    ////////////////
    LogDef{"SERVICE ACKNOWLEDGE ALERT: ",
           LOGCLASS_ALERT,
           ACKNOWLEDGE_ALERT_SERVICE,
           {Param::HostName, Param::SvcDesc, Param::StateType,
            Param::ContactName, Param::Comment}},
    ////////////////
    LogDef{"SERVICE FLAPPING ALERT: ",
           LOGCLASS_ALERT,
           FLAPPING_SERVICE,
           {Param::HostName, Param::SvcDesc, Param::StateType, Param::Comment}},
    ////////////////
    LogDef{
        "TIMEPERIOD_TRANSITION: ", LOGCLASS_STATE, TIMEPERIOD_TRANSITION, {}},
    ////////////////
    LogDef{"HOST NOTIFICATION: ",
           LOGCLASS_NOTIFICATION,
           NONE,
           {Param::ContactName, Param::HostName, Param::StateType,
            Param::CommandName, Param::CheckOutput}},
    ////////////////
    LogDef{"SERVICE NOTIFICATION: ",
           LOGCLASS_NOTIFICATION,
           NONE,
           {Param::ContactName, Param::HostName, Param::SvcDesc,
            Param::StateType, Param::CommandName, Param::CheckOutput}},
    ////////////////
    LogDef{"HOST NOTIFICATION RESULT: ",
           LOGCLASS_NOTIFICATION,
           NONE,
           {Param::ContactName, Param::HostName, Param::StateType,
            Param::CommandName, Param::Comment}},
    ////////////////
    LogDef{"SERVICE NOTIFICATION RESULT: ",
           LOGCLASS_NOTIFICATION,
           NONE,
           {Param::ContactName, Param::HostName, Param::SvcDesc,
            Param::StateType, Param::CommandName, Param::Comment}},
    ////////////////
    LogDef{"HOST ALERT HANDLER STARTED: ",
           8,  // LOGCLASS_ALERT_HANDLERS,
           NONE,
           {Param::HostName, Param::CommandName}},
    ////////////////
    LogDef{"SERVICE ALERT HANDLER STARTED: ",
           8,  // LOGCLASS_ALERT_HANDLERS,
           NONE,
           {Param::HostName, Param::SvcDesc, Param::CommandName}},
    ////////////////
    LogDef{"HOST ALERT HANDLER STOPPED: ",
           8,  // LOGCLASS_ALERT_HANDLERS
           NONE,
           {Param::HostName, Param::CommandName, Param::ServiceState,
            Param::CheckOutput}},
    ////////////////
    LogDef{"SERVICE ALERT HANDLER STOPPED: ",
           8,  // LOGCLASS_ALERT_HANDLERS,
           NONE,
           {Param::HostName, Param::SvcDesc, Param::CommandName,
            Param::ServiceState, Param::CheckOutput}},
    ////////////////
    LogDef{"PASSIVE SERVICE CHECK: ",
           LOGCLASS_PASSIVECHECK,
           NONE,
           {Param::HostName, Param::SvcDesc, Param::State, Param::CheckOutput}},
    ////////////////
    LogDef{"PASSIVE HOST CHECK: ",
           LOGCLASS_PASSIVECHECK,
           NONE,
           {Param::HostName, Param::State, Param::CheckOutput}},
    ////////////////
    LogDef{"EXTERNAL COMMAND: ", LOGCLASS_COMMAND, NONE, {}}};

bool LogEntry::classifyLogMessage() {
    for (const auto &def : log_definitions) {
        if (starts_with(string(_text), string(def.prefix))) {
            _logclass = def.log_class;
            _type = def.log_type;
            char *scan = _text;
            _text = next_token(&scan, ':');
            ++scan;

            for (Param par : def.params) {
                assign(par, &scan);
            }

            applyWorkarounds();

            return true;
        }
    }

    return true;
}

void LogEntry::applyWorkarounds() {
    if (_logclass == LOGCLASS_NOTIFICATION) {
        // The NotifyHelper class has a long, tragic history: Through a long
        // series of commits, it suffered from spelling mistakes like
        // "HOST_NOTIFICATION" or "HOST NOTIFICATION" (without a colon),
        // parameter lists not matching the corresponding format strings, and
        // last but not least wrong ordering of fields. The net result of this
        // tragedy is that due to legacy reasons, we have to support parsing an
        // incorrect ordering of "state type" and "command name" fields. :-P
        _state = (_svc_desc == nullptr) ? hostStateToInt(_state_type)
                                        : serviceStateToInt(_state_type);

        if (((_svc_desc == nullptr) && (_state == 3)) ||
            ((_svc_desc != nullptr) && (_state == 4))) {
            std::swap(_state_type, _command_name);
            _state = (_svc_desc == nullptr) ? hostStateToInt(_state_type)
                                            : serviceStateToInt(_state_type);
        }
    }
}

bool LogEntry::handleTextEntry() {
    if (strncmp(_text, "LOG VERSION: 2.0", 16) == 0) {
        _logclass = LOGCLASS_PROGRAM;
        _type = LOG_VERSION;
        return true;
    }
    if ((strncmp(_text, "logging initial states", 22) == 0) ||
        (strncmp(_text, "logging intitial states", 23) == 0)) {
        _logclass = LOGCLASS_PROGRAM;
        _type = LOG_INITIAL_STATES;
        return true;
    }
    return false;
}

bool LogEntry::handleProgrammEntry() {
    if ((strstr(_text, "starting...") != nullptr) ||
        (strstr(_text, "active mode...") != nullptr)) {
        _logclass = LOGCLASS_PROGRAM;
        _type = CORE_STARTING;
        return true;
    }
    if ((strstr(_text, "shutting down...") != nullptr) ||
        (strstr(_text, "Bailing out") != nullptr) ||
        (strstr(_text, "standby mode...") != nullptr)) {
        _logclass = LOGCLASS_PROGRAM;
        _type = CORE_STOPPING;
        return true;
    }
    if (strstr(_text, "restarting...") != nullptr) {
        _logclass = LOGCLASS_PROGRAM;
        return true;
    }
    return false;
}

int LogEntry::serviceStateToInt(const char *s) {
    if (s == nullptr) {
        return 3;  // can happen at garbled log line
    }

    const char *last = s + strlen(s) - 1;
    // Ugly: Depending on where we're called, the actual state can be in
    // parentheses at the end, e.g. "ALERTHANDLER (OK)".
    if (*last == ')') {
        last--;
    }

    // normal states: OK, WARNING, CRITICAL, UNKNOWN
    // states from "... ALERT"/"... NOTIFICATION": RECOVERY
    switch (*last) {
        case 'K':
            return 0;
        case 'Y':
            return 0;
        case 'G':
            return 1;
        case 'L':
            return 2;
        case 'N':
            return 3;
        default:
            return 4;
    }
}

int LogEntry::hostStateToInt(const char *s) {
    if (s == nullptr) {
        return 2;  // can happen at garbled log line
    }

    const char *last = s + strlen(s) - 1;
    // Ugly: Depending on where we're called, the actual state can be in
    // parentheses at the end, e.g. "ALERTHANDLER (OK)".
    if (*last == ')') {
        last--;
    }

    // normal states: UP, DOWN, UNREACHABLE
    // states from "... ALERT"/"... NOTIFICATION": RECOVERY
    // states from "... ALERT HANDLER STOPPED": OK, WARNING, CRITICAL, UNKNOWN
    switch (*last) {
        case 'P':
            return 0;
        case 'Y':
            return 0;
        case 'E':
            return 2;
        case 'K':
            return 0;
        case 'G':
            return 1;
        case 'L':
            return 2;
        case 'N':
            if (*(last - 1) == 'W') {
                return 3;  // UNKNOWN
            } else {
                return 2;  // DOWN
            }
        default:
            return 3;
    }
}

unsigned LogEntry::updateReferences(const CommandsHolder &commands_holder) {
    unsigned updated = 0;
    if (_host_name != nullptr) {
        _host = find_host(_host_name);
        updated++;
    }
    if (_svc_desc != nullptr) {
        _service = find_service(_host_name, _svc_desc);
        updated++;
    }
    if (_contact_name != nullptr) {
        _contact = find_contact(_contact_name);
        updated++;
    }
    if (_command_name != nullptr) {
        _command = commands_holder.find(_command_name);
        updated++;
    }
    return updated;
}
