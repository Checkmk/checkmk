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
#include <cstdlib>
#include <cstring>
#include <unordered_map>
#include <utility>
#include "MonitoringCore.h"
#include "StringUtils.h"

using mk::starts_with;
using std::string;
using std::unordered_map;

LogEntry::LogEntry(MonitoringCore *mc, unsigned lineno, char *line) {
    // TODO(sp) Fix classifyLogMessage() below to always set all fields and
    // remove this set-me-to-zero-to-be-sure-block.
    _state = 0;
    _attempt = 0;
    _host = nullptr;
    _service = nullptr;
    _contact = nullptr;
    _lineno = lineno;

    // make a copy of the message and strip trailing newline
    size_t linelen = strlen(line);
    while (linelen > 0 && line[linelen - 1] == '\n') {
        line[--linelen] = '\0';
    }

    // keep unsplit copy of the message (needs lots of memory, maybe we could
    // optimize that one day...)
    _complete = line;

    // pointer to options (everything after ':')
    size_t pos = _complete.find(':');
    if (pos != string::npos) {
        pos = _complete.find_first_not_of(' ', pos + 1);
    }
    if (pos == string::npos) {
        pos = _complete.size();
    }
    _options = &_complete[pos];

    // [1260722267] xxx - extract timestamp, validate message
    if (linelen < 13 || line[0] != '[' || line[11] != ']') {
        _logclass = Class::invalid;
        _type = LogEntryType::none;
        return;  // ignore invalid lines silently
    }
    line[11] = 0;  // zero-terminate time stamp
    _time = atoi(line + 1);

    // also skip space after timestamp
    classifyLogMessage(line + 13);
    applyWorkarounds();
    updateReferences(mc);
}

bool LogEntry::assign(Param par, const string &field) {
    switch (par) {
        case Param::HostName:
            this->_host_name = field;
            break;
        case Param::SvcDesc:
            this->_svc_desc = field;
            break;
        case Param::HostState:
            this->_state = static_cast<int>(parseHostState(field));
            break;
        case Param::ServiceState:
            this->_state = static_cast<int>(parseServiceState(field));
            break;
        case Param::State:
            this->_state = atoi(field.c_str());
            break;
        case Param::StateType:
            this->_state_type = field;
            break;
        case Param::Attempt:
            this->_attempt = atoi(field.c_str());
            break;
        case Param::Comment:
            this->_comment = field;
            break;
        case Param::CommandName:
            this->_command_name = field;
            break;
        case Param::ContactName:
            this->_contact_name = field;
            break;
        case Param::CheckOutput:
            this->_check_output = field;
            break;
    }

    return true;
};

// False positive in clang-tidy-4.0, see https://reviews.llvm.org/D27048
std::vector<LogEntry::LogDef> LogEntry::log_definitions  // NOLINT
    {LogDef{"INITIAL HOST STATE",
            Class::alert,
            LogEntryType::alert_host,
            {Param::HostName, Param::HostState, Param::StateType,
             Param::Attempt, Param::CheckOutput}},
     ////////////////
     LogDef{"CURRENT HOST STATE",
            Class::state,
            LogEntryType::state_host_initial,
            {Param::HostName, Param::HostState, Param::StateType,
             Param::Attempt, Param::CheckOutput}},
     ////////////////
     LogDef{"HOST ALERT",
            Class::state,
            LogEntryType::state_host,
            {Param::HostName, Param::HostState, Param::StateType,
             Param::Attempt, Param::CheckOutput}},
     ////////////////
     LogDef{"HOST DOWNTIME ALERT",
            Class::alert,
            LogEntryType::downtime_alert_host,
            {Param::HostName, Param::StateType, Param::Comment}},
     ////////////////
     LogDef{"HOST ACKNOWLEDGE ALERT",
            Class::alert,
            LogEntryType::acknowledge_alert_host,
            {Param::HostName, Param::StateType, Param::ContactName,
             Param::Comment}},
     ////////////////
     LogDef{"HOST FLAPPING ALERT",
            Class::alert,
            LogEntryType::flapping_host,
            {Param::HostName, Param::StateType, Param::Comment}},
     ////////////////
     LogDef{"INITIAL SERVICE STATE",
            Class::state,
            LogEntryType::state_service_initial,
            {Param::HostName, Param::SvcDesc, Param::ServiceState,
             Param::StateType, Param::Attempt, Param::CheckOutput}},
     ////////////////
     LogDef{"CURRENT SERVICE STATE",
            Class::state,
            LogEntryType::state_service,
            {Param::HostName, Param::SvcDesc, Param::ServiceState,
             Param::StateType, Param::Attempt, Param::CheckOutput}},
     ////////////////
     LogDef{"SERVICE ALERT",
            Class::alert,
            LogEntryType::alert_service,
            {Param::HostName, Param::SvcDesc, Param::ServiceState,
             Param::StateType, Param::Attempt, Param::CheckOutput}},
     ////////////////
     LogDef{
         "SERVICE DOWNTIME ALERT",
         Class::alert,
         LogEntryType::downtime_alert_service,
         {Param::HostName, Param::SvcDesc, Param::StateType, Param::Comment}},
     ////////////////
     LogDef{"SERVICE ACKNOWLEDGE ALERT",
            Class::alert,
            LogEntryType::acknowledge_alert_service,
            {Param::HostName, Param::SvcDesc, Param::StateType,
             Param::ContactName, Param::Comment}},
     ////////////////
     LogDef{
         "SERVICE FLAPPING ALERT",
         Class::alert,
         LogEntryType::flapping_service,
         {Param::HostName, Param::SvcDesc, Param::StateType, Param::Comment}},
     ////////////////
     LogDef{"TIMEPERIOD TRANSITION",
            Class::state,
            LogEntryType::timeperiod_transition,
            {}},
     ////////////////
     LogDef{"HOST NOTIFICATION",
            Class::hs_notification,
            LogEntryType::none,
            {Param::ContactName, Param::HostName, Param::StateType,
             Param::CommandName, Param::CheckOutput}},
     ////////////////
     LogDef{"SERVICE NOTIFICATION",
            Class::hs_notification,
            LogEntryType::none,
            {Param::ContactName, Param::HostName, Param::SvcDesc,
             Param::StateType, Param::CommandName, Param::CheckOutput}},
     ////////////////
     LogDef{"HOST NOTIFICATION RESULT",
            Class::hs_notification,
            LogEntryType::none,
            {Param::ContactName, Param::HostName, Param::StateType,
             Param::CommandName, Param::CheckOutput, Param::Comment}},
     ////////////////
     LogDef{
         "SERVICE NOTIFICATION RESULT",
         Class::hs_notification,
         LogEntryType::none,
         {Param::ContactName, Param::HostName, Param::SvcDesc, Param::StateType,
          Param::CommandName, Param::CheckOutput, Param::Comment}},
     ////////////////
     LogDef{"HOST NOTIFICATION PROGRESS",
            Class::hs_notification,
            LogEntryType::none,
            {Param::ContactName, Param::HostName, Param::StateType,
             Param::CommandName, Param::CheckOutput}},
     ////////////////
     LogDef{"SERVICE NOTIFICATION PROGRESS",
            Class::hs_notification,
            LogEntryType::none,
            {Param::ContactName, Param::HostName, Param::SvcDesc,
             Param::StateType, Param::CommandName, Param::CheckOutput}},
     ////////////////
     LogDef{"HOST ALERT HANDLER STARTED",
            Class::alert_handlers,
            LogEntryType::none,
            {Param::HostName, Param::CommandName}},
     ////////////////
     LogDef{"SERVICE ALERT HANDLER STARTED",
            Class::alert_handlers,
            LogEntryType::none,
            {Param::HostName, Param::SvcDesc, Param::CommandName}},
     ////////////////
     LogDef{"HOST ALERT HANDLER STOPPED",
            Class::alert_handlers,
            LogEntryType::none,
            {Param::HostName, Param::CommandName, Param::ServiceState,
             Param::CheckOutput}},
     ////////////////
     LogDef{"SERVICE ALERT HANDLER STOPPED",
            Class::alert_handlers,
            LogEntryType::none,
            {Param::HostName, Param::SvcDesc, Param::CommandName,
             Param::ServiceState, Param::CheckOutput}},
     ////////////////
     LogDef{
         "PASSIVE SERVICE CHECK",
         Class::passivecheck,
         LogEntryType::none,
         {Param::HostName, Param::SvcDesc, Param::State, Param::CheckOutput}},
     ////////////////
     LogDef{"PASSIVE HOST CHECK",
            Class::passivecheck,
            LogEntryType::none,
            {Param::HostName, Param::State, Param::CheckOutput}},
     ////////////////
     LogDef{"EXTERNAL COMMAND", Class::ext_command, LogEntryType::none, {}}};

void LogEntry::classifyLogMessage(const string &text) {
    for (const auto &def : log_definitions) {
        if (starts_with(text, def.prefix) &&
            text.compare(def.prefix.size(), 2, ": ") == 0) {
            _text = def.prefix;
            _logclass = def.log_class;
            _type = def.log_type;
            // TODO(sp) Use boost::tokenizer instead of this index fiddling
            size_t pos = def.prefix.size() + 2;
            for (Param par : def.params) {
                size_t sep_pos = text.find(';', pos);
                size_t end_pos =
                    sep_pos == string::npos ? text.size() : sep_pos;
                assign(par, text.substr(pos, end_pos - pos));
                pos = sep_pos == string::npos ? text.size() : (sep_pos + 1);
            }
            return;
        }
    }
    _text = text;
    if (starts_with(text, "LOG VERSION: 2.0")) {
        _logclass = Class::program;
        _type = LogEntryType::log_version;
        return;
    }
    if (starts_with(text, "logging initial states") ||
        starts_with(text, "logging intitial states")) {
        _logclass = Class::program;
        _type = LogEntryType::log_initial_states;
        return;
    }
    if (text.find("starting...") != string::npos ||
        text.find("active mode...") != string::npos) {
        _logclass = Class::program;
        _type = LogEntryType::core_starting;
        return;
    }
    if (text.find("shutting down...") != string::npos ||
        text.find("Bailing out") != string::npos ||
        text.find("standby mode...") != string::npos) {
        _logclass = Class::program;
        _type = LogEntryType::core_stopping;
        return;
    }
    if (text.find("restarting...") != string::npos) {
        _logclass = Class::program;
        _type = LogEntryType::none;
        return;
    }
    _logclass = Class::info;
    _type = LogEntryType::none;
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
        _state_type.empty()) {                  // extremely broken line
        return;
    }

    if (_state_type == "check-mk-notify") {
        // Ooops, we encounter one of our own buggy lines...
        std::swap(_state_type, _command_name);
    }

    if (_state_type.empty()) {
        return;  // extremely broken line, even after a potential swap
    }

    _state = _svc_desc.empty()
                 ? static_cast<int>(parseHostState(_state_type))
                 : static_cast<int>(parseServiceState(_state_type));
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
    if (!_host_name.empty()) {
        // Older Nagios headers are not const-correct... :-P
        _host = find_host(const_cast<char *>(_host_name.c_str()));
        updated++;
    }
    if (!_svc_desc.empty()) {
        // Older Nagios headers are not const-correct... :-P
        _service = find_service(const_cast<char *>(_host_name.c_str()),
                                const_cast<char *>(_svc_desc.c_str()));
        updated++;
    }
    if (!_contact_name.empty()) {
        // Older Nagios headers are not const-correct... :-P
        _contact = find_contact(const_cast<char *>(_contact_name.c_str()));
        updated++;
    }
    if (!_command_name.empty()) {
        _command = mc->find_command(_command_name);
        updated++;
    }
    return updated;
}
