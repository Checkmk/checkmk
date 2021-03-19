// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "LogEntry.h"

#include <algorithm>
#include <cstdlib>
#include <cstring>
#include <functional>
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
        _time = 0;
        _type = "";
        return;  // ignore invalid lines silently
    }

    classifyLogMessage();
}

void LogEntry::assign(Param par, const std::string &field) {
    switch (par) {
        case Param::HostName:
            _host_name = field;
            return;
        case Param::ServiceDescription:
            _service_description = field;
            return;
        case Param::CommandName:
            _command_name = field;
            return;
        case Param::CommandNameWithWorkaround:
            _command_name = field;
            // The NotifyHelper class has a long, tragic history: Through a long
            // series of commits, it suffered from spelling mistakes like
            // "HOST_NOTIFICATION" or "HOST NOTIFICATION" (without a colon),
            // parameter lists not matching the corresponding format strings,
            // and last but not least wrong ordering of fields. The net result
            // of this tragedy is that due to legacy reasons, we have to support
            // parsing an incorrect ordering of "state type" and "command name"
            // fields. :-P
            if (_state_type.empty()) {
                return;  // extremely broken line
            }
            if (_state_type == "check-mk-notify") {
                // Ooops, we encounter one of our own buggy lines...
                std::swap(_state_type, _command_name);
                if (_state_type.empty()) {
                    return;  // extremely broken line, even after swapping
                }
            }
            _state = _service_description.empty()
                         ? static_cast<int>(parseHostState(_state_type))
                         : static_cast<int>(parseServiceState(_state_type));
            return;
        case Param::ContactName:
            _contact_name = field;
            return;
        case Param::HostState:
            _state = static_cast<int>(parseHostState(field));
            return;
        case Param::ServiceState:
        case Param::ExitCode:  // HACK: Encoded as a service state! :-P
            _state = static_cast<int>(parseServiceState(field));
            return;
        case Param::State:
            _state = atoi(field.c_str());
            return;
        case Param::StateType:
            _state_type = field;
            return;
        case Param::Attempt:
            _attempt = atoi(field.c_str());
            return;
        case Param::Comment:
            _comment = field;
            return;
        case Param::PluginOutput:
            _plugin_output = field;
            return;
        case Param::LongPluginOutput:
            _long_plugin_output = mk::to_multi_line(field);
            return;
        case Param::Ignore:
            return;
    }
};

// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
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
            Param::CommandNameWithWorkaround, Param::PluginOutput,
            Param::Ignore,  // author
            Param::Comment, Param::LongPluginOutput}},
    ////////////////
    LogDef{"SERVICE NOTIFICATION",
           Class::hs_notification,
           LogEntryKind::none,
           {Param::ContactName, Param::HostName, Param::ServiceDescription,
            Param::StateType, Param::CommandNameWithWorkaround,
            Param::PluginOutput,
            Param::Ignore,  // author
            Param::Comment, Param::LongPluginOutput}},
    ////////////////
    LogDef{"HOST NOTIFICATION RESULT",
           Class::hs_notification,
           LogEntryKind::none,
           {Param::ContactName, Param::HostName, Param::StateType,
            Param::CommandNameWithWorkaround, Param::PluginOutput,
            Param::Comment}},
    ////////////////
    LogDef{"SERVICE NOTIFICATION RESULT",
           Class::hs_notification,
           LogEntryKind::none,
           {Param::ContactName, Param::HostName, Param::ServiceDescription,
            Param::StateType, Param::CommandNameWithWorkaround,
            Param::PluginOutput, Param::Comment}},
    ////////////////
    LogDef{"HOST NOTIFICATION PROGRESS",
           Class::hs_notification,
           LogEntryKind::none,
           {Param::ContactName, Param::HostName, Param::StateType,
            Param::CommandNameWithWorkaround, Param::PluginOutput}},
    ////////////////
    LogDef{"SERVICE NOTIFICATION PROGRESS",
           Class::hs_notification,
           LogEntryKind::none,
           {Param::ContactName, Param::HostName, Param::ServiceDescription,
            Param::StateType, Param::CommandNameWithWorkaround,
            Param::PluginOutput}},
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
           {Param::HostName, Param::CommandName, Param::ExitCode,
            Param::PluginOutput}},
    ////////////////
    LogDef{"SERVICE ALERT HANDLER STOPPED",
           Class::alert_handlers,
           LogEntryKind::none,
           {Param::HostName, Param::ServiceDescription, Param::CommandName,
            Param::ExitCode, Param::PluginOutput}},
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

bool LogEntry::textStartsWith(const std::string &what) const {
    return _message.compare(timestamp_prefix_length, what.size(), what) == 0;
}

bool LogEntry::textContains(const std::string &what) const {
    return _message.find(what, timestamp_prefix_length) != std::string::npos;
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

const std::unordered_map<std::string, ServiceState> fl_service_state_types{
    // normal states
    {"OK", ServiceState::ok},
    {"WARNING", ServiceState::warning},
    {"CRITICAL", ServiceState::critical},
    {"UNKNOWN", ServiceState::unknown},
    // states from "... ALERT"/"... NOTIFICATION"
    {"RECOVERY", ServiceState::ok}};

const std::unordered_map<std::string, HostState> fl_host_state_types{
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
    {"UNKNOWN", static_cast<HostState>(3)}};  // Horrible HACK
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

namespace {
std::string parens(const std::string &fun, const std::string &arg) {
    return fun + " (" + arg + ")";
}

// TODO(sp) Centralized these mappings and their inverses...
std::string to_host_state(int state) {
    switch (state) {
        case 0:
            return "UP";
        case 1:
            return "DOWN";
        case 2:
            return "UNREACHABLE";
        default:
            return "FUNNY_HOST_STATE_" + std::to_string(state);
    }
}

std::string to_service_state(int state) {
    switch (state) {
        case 0:
            return "OK";
        case 1:
            return "WARNING";
        case 2:
            return "CRITICAL";
        case 3:
            return "UNKNOWN";
        default:
            return "FUNNY_HOST_STATE_" + std::to_string(state);
    }
}

std::string to_exit_code(int state) {
    switch (state) {
        case 0:
            return "SUCCESS";
        case 1:
            return "TEMPORARY_FAILURE";
        case 2:
            return "PERMANENT_FAILURE";
        default:
            return "FUNNY_EXIT_CODE_" + std::to_string(state);
    }
}
}  // namespace

std::string LogEntry::state_info() const {
    switch (_kind) {
        case LogEntryKind::state_host_initial:
        case LogEntryKind::state_host:
        case LogEntryKind::alert_host:
            return parens(_state_type, to_host_state(_state));

        case LogEntryKind::state_service_initial:
        case LogEntryKind::state_service:
        case LogEntryKind::alert_service:
            return parens(_state_type, to_service_state(_state));

        case LogEntryKind::none:
            if (strcmp(_type, "HOST NOTIFICATION RESULT") == 0 ||
                strcmp(_type, "SERVICE NOTIFICATION RESULT") == 0 ||
                strcmp(_type, "HOST NOTIFICATION PROGRESS") == 0 ||
                strcmp(_type, "SERVICE NOTIFICATION PROGRESS") == 0 ||
                strcmp(_type, "HOST ALERT HANDLER STOPPED") == 0 ||
                strcmp(_type, "SERVICE ALERT HANDLER STOPPED") == 0) {
                return parens("EXIT_CODE", to_exit_code(_state));
            }
            if (strcmp(_type, "HOST NOTIFICATION") == 0) {
                if (_state_type == "UP" ||    //
                    _state_type == "DOWN" ||  //
                    _state_type == "UNREACHABLE") {
                    return parens("NOTIFY", _state_type);
                }
                if (mk::starts_with(_state_type, "ALERTHANDLER (")) {
                    return parens("EXIT_CODE", to_exit_code(_state));
                }
                return _state_type;
            }
            if (strcmp(_type, "SERVICE NOTIFICATION") == 0) {
                if (_state_type == "OK" ||        //
                    _state_type == "WARNING" ||   //
                    _state_type == "CRITICAL" ||  //
                    _state_type == "UNKNOWN") {
                    return parens("NOTIFY", _state_type);
                }
                if (mk::starts_with(_state_type, "ALERTHANDLER (")) {
                    return parens("EXIT_CODE", to_exit_code(_state));
                }
                return _state_type;
            }
            if (strcmp(_type, "PASSIVE HOST CHECK") == 0) {
                return parens("PASSIVE", to_host_state(_state));
            }
            if (strcmp(_type, "PASSIVE SERVICE CHECK") == 0) {
                return parens("PASSIVE", to_service_state(_state));
            }
            return "";

        case LogEntryKind::downtime_alert_host:
        case LogEntryKind::downtime_alert_service:
        case LogEntryKind::flapping_host:
        case LogEntryKind::flapping_service:
        case LogEntryKind::acknowledge_alert_host:
        case LogEntryKind::acknowledge_alert_service:
            return _state_type;

        case LogEntryKind::timeperiod_transition:
        case LogEntryKind::core_starting:
        case LogEntryKind::core_stopping:
        case LogEntryKind::log_version:
        case LogEntryKind::log_initial_states:
            return "";
    }
    return "";  // unreachable, make the compiler happy
}
