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
#include <unordered_map>
#include <utility>
#include "MonitoringCore.h"
#include "StringUtils.h"
#include "strutil.h"

using mk::starts_with;
using std::string;
using std::unordered_map;

LogEntry::LogEntry(MonitoringCore *mc, unsigned lineno, const char *line)
    : _logclass(Class::info), _type(LogEntryType::none) {
    // TODO(sp) Fix all handleFooEntry() member functions below to always set
    // all fields and remove this set-me-to-zero-to-be-sure-block.
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
        _logclass = Class::invalid;
        return;  // ignore invalid lines silently
    }
    _msg[11] = 0;  // zero-terminate time stamp
    _time = atoi(_msg + 1);
    _text = _msg + 13;  // also skip space after timestamp

    if (classifyLogMessage()) {
        updateReferences(mc);
    } else {
        handleTextEntry() || handleProgrammEntry();  // Performance killer
                                                     // strstr in
                                                     // handleProgrammEntry!
    }
    // rest is Class::INFO
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
            this->_state =
                static_cast<int>(parseHostState(safe_next_token(scan, ';')));
            break;
        case Param::ServiceState:
            this->_state =
                static_cast<int>(parseServiceState(safe_next_token(scan, ';')));
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

// False positive in clang-tidy-4.0, see https://reviews.llvm.org/D27048
std::vector<LogEntry::LogDef> LogEntry::log_definitions  // NOLINT
    {LogDef{"INITIAL HOST STATE: ",
            Class::state,
            LogEntryType::state_host_initial,
            {Param::HostName, Param::HostState, Param::StateType,
             Param::Attempt, Param::CheckOutput}},
     ////////////////
     LogDef{"CURRENT HOST STATE: ",
            Class::state,
            LogEntryType::state_host,
            {Param::HostName, Param::HostState, Param::StateType,
             Param::Attempt, Param::CheckOutput}},
     ////////////////
     LogDef{"HOST ALERT: ",
            Class::alert,
            LogEntryType::alert_host,
            {Param::HostName, Param::HostState, Param::StateType,
             Param::Attempt, Param::CheckOutput}},
     ////////////////
     LogDef{"HOST DOWNTIME ALERT: ",
            Class::alert,
            LogEntryType::downtime_alert_host,
            {Param::HostName, Param::StateType, Param::Comment}},
     ////////////////
     LogDef{"HOST ACKNOWLEDGE ALERT: ",
            Class::alert,
            LogEntryType::acknowledge_alert_host,
            {Param::HostName, Param::StateType, Param::ContactName,
             Param::Comment}},
     ////////////////
     LogDef{"HOST FLAPPING ALERT: ",
            Class::alert,
            LogEntryType::flapping_host,
            {Param::HostName, Param::StateType, Param::Comment}},
     ////////////////
     LogDef{"INITIAL SERVICE STATE: ",
            Class::state,
            LogEntryType::state_service_initial,
            {Param::HostName, Param::SvcDesc, Param::ServiceState,
             Param::StateType, Param::Attempt, Param::CheckOutput}},
     ////////////////
     LogDef{"CURRENT SERVICE STATE: ",
            Class::state,
            LogEntryType::state_service,
            {Param::HostName, Param::SvcDesc, Param::ServiceState,
             Param::StateType, Param::Attempt, Param::CheckOutput}},
     ////////////////
     LogDef{"SERVICE ALERT: ",
            Class::alert,
            LogEntryType::alert_service,
            {Param::HostName, Param::SvcDesc, Param::ServiceState,
             Param::StateType, Param::Attempt, Param::CheckOutput}},
     ////////////////
     LogDef{
         "SERVICE DOWNTIME ALERT: ",
         Class::alert,
         LogEntryType::downtime_alert_service,
         {Param::HostName, Param::SvcDesc, Param::StateType, Param::Comment}},
     ////////////////
     LogDef{"SERVICE ACKNOWLEDGE ALERT: ",
            Class::alert,
            LogEntryType::acknowledge_alert_service,
            {Param::HostName, Param::SvcDesc, Param::StateType,
             Param::ContactName, Param::Comment}},
     ////////////////
     LogDef{
         "SERVICE FLAPPING ALERT: ",
         Class::alert,
         LogEntryType::flapping_service,
         {Param::HostName, Param::SvcDesc, Param::StateType, Param::Comment}},
     ////////////////
     LogDef{"TIMEPERIOD TRANSITION: ",
            Class::state,
            LogEntryType::timeperiod_transition,
            {}},
     ////////////////
     LogDef{"HOST NOTIFICATION: ",
            Class::hs_notification,
            LogEntryType::none,
            {Param::ContactName, Param::HostName, Param::StateType,
             Param::CommandName, Param::CheckOutput}},
     ////////////////
     LogDef{"SERVICE NOTIFICATION: ",
            Class::hs_notification,
            LogEntryType::none,
            {Param::ContactName, Param::HostName, Param::SvcDesc,
             Param::StateType, Param::CommandName, Param::CheckOutput}},
     ////////////////
     LogDef{"HOST NOTIFICATION RESULT: ",
            Class::hs_notification,
            LogEntryType::none,
            {Param::ContactName, Param::HostName, Param::StateType,
             Param::CommandName, Param::CheckOutput, Param::Comment}},
     ////////////////
     LogDef{
         "SERVICE NOTIFICATION RESULT: ",
         Class::hs_notification,
         LogEntryType::none,
         {Param::ContactName, Param::HostName, Param::SvcDesc, Param::StateType,
          Param::CommandName, Param::CheckOutput, Param::Comment}},
     ////////////////
     LogDef{"HOST NOTIFICATION PROGRESS: ",
            Class::hs_notification,
            LogEntryType::none,
            {Param::ContactName, Param::HostName, Param::StateType,
             Param::CommandName, Param::CheckOutput}},
     ////////////////
     LogDef{"SERVICE NOTIFICATION PROGRESS: ",
            Class::hs_notification,
            LogEntryType::none,
            {Param::ContactName, Param::HostName, Param::SvcDesc,
             Param::StateType, Param::CommandName, Param::CheckOutput}},
     ////////////////
     LogDef{"HOST ALERT HANDLER STARTED: ",
            Class::alert_handlers,
            LogEntryType::none,
            {Param::HostName, Param::CommandName}},
     ////////////////
     LogDef{"SERVICE ALERT HANDLER STARTED: ",
            Class::alert_handlers,
            LogEntryType::none,
            {Param::HostName, Param::SvcDesc, Param::CommandName}},
     ////////////////
     LogDef{"HOST ALERT HANDLER STOPPED: ",
            Class::alert_handlers,
            LogEntryType::none,
            {Param::HostName, Param::CommandName, Param::ServiceState,
             Param::CheckOutput}},
     ////////////////
     LogDef{"SERVICE ALERT HANDLER STOPPED: ",
            Class::alert_handlers,
            LogEntryType::none,
            {Param::HostName, Param::SvcDesc, Param::CommandName,
             Param::ServiceState, Param::CheckOutput}},
     ////////////////
     LogDef{
         "PASSIVE SERVICE CHECK: ",
         Class::passivecheck,
         LogEntryType::none,
         {Param::HostName, Param::SvcDesc, Param::State, Param::CheckOutput}},
     ////////////////
     LogDef{"PASSIVE HOST CHECK: ",
            Class::passivecheck,
            LogEntryType::none,
            {Param::HostName, Param::State, Param::CheckOutput}},
     ////////////////
     LogDef{"EXTERNAL COMMAND: ", Class::ext_command, LogEntryType::none, {}}};

bool LogEntry::classifyLogMessage() {
    string text = _text;
    for (const auto &def : log_definitions) {
        if (starts_with(text, def.prefix)) {
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

    return false;
}

// The NotifyHelper class has a long, tragic history: Through a long series of
// commits, it suffered from spelling mistakes like "HOST_NOTIFICATION" or "HOST
// NOTIFICATION" (without a colon), parameter lists not matching the
// corresponding format strings, and last but not least wrong ordering of
// fields. The net result of this tragedy is that due to legacy reasons, we have
// to support parsing an incorrect ordering of "state type" and "command name"
// fields. :-P
void LogEntry::applyWorkarounds() {
    if (_logclass != Class::hs_notification ||  // no need for any workaround
        _state_type == nullptr) {               // extremely broken line
        return;
    }

    if (strcmp(_state_type, "check-mk-notify") == 0) {
        // Ooops, we encounter one of our own buggy lines...
        std::swap(_state_type, _command_name);
    }

    if (_state_type == nullptr) {
        return;  // extremely broken line, even after a potential swap
    }

    _state = (_svc_desc == nullptr)
                 ? static_cast<int>(parseHostState(_state_type))
                 : static_cast<int>(parseServiceState(_state_type));
}

bool LogEntry::handleTextEntry() {
    if (strncmp(_text, "LOG VERSION: 2.0", 16) == 0) {
        _logclass = Class::program;
        _type = LogEntryType::log_version;
        return true;
    }
    if ((strncmp(_text, "logging initial states", 22) == 0) ||
        (strncmp(_text, "logging intitial states", 23) == 0)) {
        _logclass = Class::program;
        _type = LogEntryType::log_initial_states;
        return true;
    }
    return false;
}

bool LogEntry::handleProgrammEntry() {
    if ((strstr(_text, "starting...") != nullptr) ||
        (strstr(_text, "active mode...") != nullptr)) {
        _logclass = Class::program;
        _type = LogEntryType::core_starting;
        return true;
    }
    if ((strstr(_text, "shutting down...") != nullptr) ||
        (strstr(_text, "Bailing out") != nullptr) ||
        (strstr(_text, "standby mode...") != nullptr)) {
        _logclass = Class::program;
        _type = LogEntryType::core_stopping;
        return true;
    }
    if (strstr(_text, "restarting...") != nullptr) {
        _logclass = Class::program;
        return true;
    }
    return false;
}

namespace {
// Ugly: Depending on where we're called, the actual state type can be in
// parentheses at the end, e.g. "ALERTHANDLER (OK)".
string extractStateType(const string &str) {
    if (!str.empty() && str[str.size() - 1] == ')') {
        size_t lparen = str.rfind('(');
        if (lparen != string::npos) {
            return str.substr(lparen + 1, str.size() - lparen - 2);
        }
    }
    return str;
}

unordered_map<string, ServiceState> serviceStateTypes{
    // normal states
    {"OK", ServiceState::ok},
    {"WARNING", ServiceState::warning},
    {"CRITICAL", ServiceState::critical},
    {"UNKNOWN", ServiceState::unknown},
    // states from "... ALERT"/"... NOTIFICATION"
    {"RECOVERY", ServiceState::ok}};

unordered_map<string, HostState> hostStateTypes{
    // normal states
    {"UP", HostState::up},
    {"DOWN", HostState::down},
    {"UNREACHABLE", HostState::unreachable},
    // states from "... ALERT"/"... NOTIFICATION"
    {"RECOVERY", HostState::up},
    // states from "... ALERT HANDLER STOPPED" and "(HOST|SERVICE) NOTIFICATION
    // (RESULT|PROGRESS)"
    {"OK", HostState::up},
    {"WARNING", HostState::down},
    {"CRITICAL", HostState::unreachable},
    {"UNKNOWN", HostState::up}};
}  // namespace

ServiceState LogEntry::parseServiceState(const string &str) {
    auto it = serviceStateTypes.find(extractStateType(str));
    return it == serviceStateTypes.end() ? ServiceState::ok : it->second;
}

HostState LogEntry::parseHostState(const string &str) {
    auto it = hostStateTypes.find(extractStateType(str));
    return it == hostStateTypes.end() ? HostState::up : it->second;
}

unsigned LogEntry::updateReferences(MonitoringCore *mc) {
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
        _command = mc->find_command(_command_name);
        updated++;
    }
    return updated;
}
