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
#include <stdexcept>
#include <unordered_map>
#include <utility>
#include "StringUtils.h"

// 0123456789012345678901234567890
// [1234567890] FOO BAR: blah blah
static constexpr size_t timestamp_prefix_length = 13;

// TODO(sp) Fix classifyLogMessage() below to always set all fields and remove
// this set-me-to-zero-to-be-sure-block.
LogEntry::LogEntry(size_t lineno, std::string line)
    : _lineno(static_cast<int32_t>(lineno))
    , _message(std::move(line))
    , _state(0)
    , _attempt(0) {
    // pointer to options (everything after ':')
    size_t pos = _message.find(':');
    if (pos != std::string::npos) {
        pos = _message.find_first_not_of(' ', pos + 1);
    }
    if (pos == std::string::npos) {
        pos = _message.size();
    }
    _options = &_message[pos];

    try {
        if (_message.size() < timestamp_prefix_length || _message[0] != '[' ||
            _message[11] != ']' || _message[12] != ' ') {
            throw std::invalid_argument("timestamp delimiter");
        }
        _time = std::stoi(_message.substr(1, 10));
    } catch (const std::logic_error &e) {
        _class = Class::invalid;
        _kind = LogEntryKind::none;
        return;  // ignore invalid lines silently
    }

    classifyLogMessage();
    applyWorkarounds();
}

bool LogEntry::assign(Param par, const std::string &field) {
    switch (par) {
        case Param::HostName:
            this->_host_name = field;
            break;
        case Param::ServiceDescription:
            this->_service_description = field;
            break;
        case Param::CommandName:
            this->_command_name = field;
            break;
        case Param::ContactName:
            this->_contact_name = field;
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
        case Param::PluginOutput:
            this->_plugin_output = field;
            break;
        case Param::LongPluginOutput:
            this->_long_plugin_output = mk::to_multi_line(field);
            break;
        case Param::Ignore:
            break;
    }

    return true;
};

std::vector<LogEntry::LogDef> LogEntry::log_definitions{
    LogDef{"INITIAL HOST STATE",
           Class::state,
           LogEntryKind::state_host_initial,
           {Param::HostName, Param::HostState, Param::StateType, Param::Attempt,
            Param::PluginOutput, Param::LongPluginOutput}},
    ////////////////
    LogDef{"CURRENT HOST STATE",
           Class::state,
           LogEntryKind::state_host,
           {Param::HostName, Param::HostState, Param::StateType, Param::Attempt,
            Param::PluginOutput, Param::LongPluginOutput}},
    ////////////////
    LogDef{"HOST ALERT",
           Class::alert,
           LogEntryKind::alert_host,
           {Param::HostName, Param::HostState, Param::StateType, Param::Attempt,
            Param::PluginOutput, Param::LongPluginOutput}},
    ////////////////
    LogDef{"HOST DOWNTIME ALERT",
           Class::alert,
           LogEntryKind::downtime_alert_host,
           {Param::HostName, Param::StateType, Param::Comment}},
    ////////////////
    LogDef{"HOST ACKNOWLEDGE ALERT",
           Class::alert,
           LogEntryKind::acknowledge_alert_host,
           {Param::HostName, Param::StateType, Param::ContactName,
            Param::Comment}},
    ////////////////
    LogDef{"HOST FLAPPING ALERT",
           Class::alert,
           LogEntryKind::flapping_host,
           {Param::HostName, Param::StateType, Param::Comment}},
    ////////////////
    LogDef{"INITIAL SERVICE STATE",
           Class::state,
           LogEntryKind::state_service_initial,
           {Param::HostName, Param::ServiceDescription, Param::ServiceState,
            Param::StateType, Param::Attempt, Param::PluginOutput,
            Param::LongPluginOutput}},
    ////////////////
    LogDef{"CURRENT SERVICE STATE",
           Class::state,
           LogEntryKind::state_service,
           {Param::HostName, Param::ServiceDescription, Param::ServiceState,
            Param::StateType, Param::Attempt, Param::PluginOutput,
            Param::LongPluginOutput}},
    ////////////////
    LogDef{"SERVICE ALERT",
           Class::alert,
           LogEntryKind::alert_service,
           {Param::HostName, Param::ServiceDescription, Param::ServiceState,
            Param::StateType, Param::Attempt, Param::PluginOutput,
            Param::LongPluginOutput}},
    ////////////////
    LogDef{"SERVICE DOWNTIME ALERT",
           Class::alert,
           LogEntryKind::downtime_alert_service,
           {Param::HostName, Param::ServiceDescription, Param::StateType,
            Param::Comment}},
    ////////////////
    LogDef{"SERVICE ACKNOWLEDGE ALERT",
           Class::alert,
           LogEntryKind::acknowledge_alert_service,
           {Param::HostName, Param::ServiceDescription, Param::StateType,
            Param::ContactName, Param::Comment}},
    ////////////////
    LogDef{"SERVICE FLAPPING ALERT",
           Class::alert,
           LogEntryKind::flapping_service,
           {Param::HostName, Param::ServiceDescription, Param::StateType,
            Param::Comment}},
    ////////////////
    LogDef{"TIMEPERIOD TRANSITION",
           Class::state,
           LogEntryKind::timeperiod_transition,
           {
               Param::Ignore,  // name
               Param::Ignore,  // from
               Param::Ignore   // to
           }},
    ////////////////
    LogDef{"HOST NOTIFICATION",
           Class::hs_notification,
           LogEntryKind::none,
           {Param::ContactName, Param::HostName, Param::StateType,
            Param::CommandName, Param::PluginOutput,  //
            Param::Ignore,                            // author
            Param::Comment, Param::LongPluginOutput}},
    ////////////////
    LogDef{"SERVICE NOTIFICATION",
           Class::hs_notification,
           LogEntryKind::none,
           {Param::ContactName, Param::HostName, Param::ServiceDescription,
            Param::StateType, Param::CommandName, Param::PluginOutput,  //
            Param::Ignore,  // author
            Param::Comment, Param::LongPluginOutput}},
    ////////////////
    LogDef{"HOST NOTIFICATION RESULT",
           Class::hs_notification,
           LogEntryKind::none,
           {Param::ContactName, Param::HostName, Param::StateType,
            Param::CommandName, Param::PluginOutput, Param::Comment}},
    ////////////////
    LogDef{"SERVICE NOTIFICATION RESULT",
           Class::hs_notification,
           LogEntryKind::none,
           {Param::ContactName, Param::HostName, Param::ServiceDescription,
            Param::StateType, Param::CommandName, Param::PluginOutput,
            Param::Comment}},
    ////////////////
    LogDef{"HOST NOTIFICATION PROGRESS",
           Class::hs_notification,
           LogEntryKind::none,
           {Param::ContactName, Param::HostName, Param::StateType,
            Param::CommandName, Param::PluginOutput}},
    ////////////////
    LogDef{"SERVICE NOTIFICATION PROGRESS",
           Class::hs_notification,
           LogEntryKind::none,
           {Param::ContactName, Param::HostName, Param::ServiceDescription,
            Param::StateType, Param::CommandName, Param::PluginOutput}},
    ////////////////
    LogDef{"HOST ALERT HANDLER STARTED",
           Class::alert_handlers,
           LogEntryKind::none,
           {Param::HostName, Param::CommandName}},
    ////////////////
    LogDef{"SERVICE ALERT HANDLER STARTED",
           Class::alert_handlers,
           LogEntryKind::none,
           {Param::HostName, Param::ServiceDescription, Param::CommandName}},
    ////////////////
    LogDef{"HOST ALERT HANDLER STOPPED",
           Class::alert_handlers,
           LogEntryKind::none,
           {Param::HostName, Param::CommandName, Param::ServiceState,
            Param::PluginOutput}},
    ////////////////
    LogDef{"SERVICE ALERT HANDLER STOPPED",
           Class::alert_handlers,
           LogEntryKind::none,
           {Param::HostName, Param::ServiceDescription, Param::CommandName,
            Param::ServiceState, Param::PluginOutput}},
    ////////////////
    // NOTE: Only Nagios writes such lines if configured to do so.
    LogDef{"PASSIVE SERVICE CHECK",
           Class::passivecheck,
           LogEntryKind::none,
           {Param::HostName, Param::ServiceDescription, Param::State,
            Param::PluginOutput}},
    ////////////////
    // NOTE: Only Nagios writes such lines if configured to do so.
    LogDef{"PASSIVE HOST CHECK",
           Class::passivecheck,
           LogEntryKind::none,
           {Param::HostName, Param::State, Param::PluginOutput}},
    ////////////////
    LogDef{"EXTERNAL COMMAND",
           Class::ext_command,
           LogEntryKind::none,
           {
               Param::Ignore  // command
           }}};

// A bit verbose, but we avoid unnecessary string copies below.
void LogEntry::classifyLogMessage() {
    for (const auto &def : log_definitions) {
        if (textStartsWith(def.prefix) &&
            _message.compare(timestamp_prefix_length + def.prefix.size(), 2,
                             ": ") == 0) {
            _type = &def.prefix[0];
            _class = def.log_class;
            _kind = def.log_type;
            // TODO(sp) Use boost::tokenizer instead of this index fiddling
            size_t pos = timestamp_prefix_length + def.prefix.size() + 2;
            for (Param par : def.params) {
                size_t sep_pos = _message.find(';', pos);
                size_t end_pos =
                    sep_pos == std::string::npos ? _message.size() : sep_pos;
                assign(par, _message.substr(pos, end_pos - pos));
                pos = sep_pos == std::string::npos ? _message.size()
                                                   : (sep_pos + 1);
            }
            return;
        }
    }
    _type = &_message[timestamp_prefix_length];
    if (textStartsWith("LOG VERSION: 2.0")) {
        _class = Class::program;
        _kind = LogEntryKind::log_version;
        return;
    }
    if (textStartsWith("logging initial states") ||
        textStartsWith("logging intitial states")) {
        _class = Class::program;
        _kind = LogEntryKind::log_initial_states;
        return;
    }
    if (textContains("starting...") || textContains("active mode...")) {
        _class = Class::program;
        _kind = LogEntryKind::core_starting;
        return;
    }
    if (textContains("shutting down...") || textContains("Bailing out") ||
        textContains("standby mode...")) {
        _class = Class::program;
        _kind = LogEntryKind::core_stopping;
        return;
    }
    if (textContains("restarting...")) {
        _class = Class::program;
        _kind = LogEntryKind::none;
        return;
    }
    _class = Class::info;
    _kind = LogEntryKind::none;
}

bool LogEntry::textStartsWith(const std::string &what) {
    return _message.compare(timestamp_prefix_length, what.size(), what) == 0;
}

bool LogEntry::textContains(const std::string &what) {
    return _message.find(what, timestamp_prefix_length) != std::string::npos;
}

// The NotifyHelper class has a long, tragic history: Through a long series of
// commits, it suffered from spelling mistakes like "HOST_NOTIFICATION" or "HOST
// NOTIFICATION" (without a colon), parameter lists not matching the
// corresponding format strings, and last but not least wrong ordering of
// fields. The net result of this tragedy is that due to legacy reasons, we have
// to support parsing an incorrect ordering of "state type" and "command name"
// fields. :-P
void LogEntry::applyWorkarounds() {
    if (_class != Class::hs_notification ||  // no need for any workaround
        _state_type.empty()) {               // extremely broken line
        return;
    }

    if (_state_type == "check-mk-notify") {
        // Ooops, we encounter one of our own buggy lines...
        std::swap(_state_type, _command_name);
    }

    if (_state_type.empty()) {
        return;  // extremely broken line, even after a potential swap
    }

    _state = _service_description.empty()
                 ? static_cast<int>(parseHostState(_state_type))
                 : static_cast<int>(parseServiceState(_state_type));
}

namespace {
// Ugly: Depending on where we're called, the actual state type can be in
// parentheses at the end, e.g. "ALERTHANDLER (OK)".
std::string extractStateType(const std::string &str) {
    if (!str.empty() && str[str.size() - 1] == ')') {
        size_t lparen = str.rfind('(');
        if (lparen != std::string::npos) {
            return str.substr(lparen + 1, str.size() - lparen - 2);
        }
    }
    return str;
}

std::unordered_map<std::string, ServiceState> fl_service_state_types{
    // normal states
    {"OK", ServiceState::ok},
    {"WARNING", ServiceState::warning},
    {"CRITICAL", ServiceState::critical},
    {"UNKNOWN", ServiceState::unknown},
    // states from "... ALERT"/"... NOTIFICATION"
    {"RECOVERY", ServiceState::ok}};

std::unordered_map<std::string, HostState> fl_host_state_types{
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

// static
ServiceState LogEntry::parseServiceState(const std::string &str) {
    auto it = fl_service_state_types.find(extractStateType(str));
    return it == fl_service_state_types.end() ? ServiceState::ok : it->second;
}

// static
HostState LogEntry::parseHostState(const std::string &str) {
    auto it = fl_host_state_types.find(extractStateType(str));
    return it == fl_host_state_types.end() ? HostState::up : it->second;
}
