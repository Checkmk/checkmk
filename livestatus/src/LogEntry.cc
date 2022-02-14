// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "LogEntry.h"

#include <algorithm>
#include <array>
#include <charconv>
#include <ctime>
#include <iterator>
#include <stdexcept>
#include <system_error>
#include <utility>

using namespace std::string_view_literals;

// 0123456789012345678901234567890
// [1234567890] FOO BAR: blah blah
static constexpr size_t timestamp_prefix_length = 13;

// TODO(sp) Fix classifyLogMessage() below to always set all fields and remove
// this set-me-to-zero-to-be-sure-block.
LogEntry::LogEntry(size_t lineno, std::string line)
    : lineno_(lineno), message_(std::move(line)), state_(0), attempt_(0) {
    size_t pos = message_.find(':');
    if (pos != std::string::npos) {
        pos = message_.find_first_not_of(' ', pos + 1);
    }
    if (pos == std::string::npos) {
        pos = message_.size();
    }
    options_ = std::string_view{message_}.substr(pos);

    time_t timestamp{};
    if (message_.size() < timestamp_prefix_length ||  //
        message_[0] != '[' || message_[11] != ']' || message_[12] != ' ' ||
        std::from_chars(&message_[1], &message_[11], timestamp).ec !=
            std::errc{}) {
        throw std::invalid_argument{"invalid log line"};
    }
    time_ = std::chrono::system_clock::from_time_t(timestamp);

    classifyLogMessage();
}

void LogEntry::assign(Param par, std::string_view field) {
    switch (par) {
        case Param::HostName:
            host_name_ = field;
            return;
        case Param::ServiceDescription:
            service_description_ = field;
            return;
        case Param::CommandName:
            command_name_ = field;
            return;
        case Param::CommandNameWithWorkaround:
            command_name_ = field;
            // The NotifyHelper class has a long, tragic history: Through a long
            // series of commits, it suffered from spelling mistakes like
            // "HOST_NOTIFICATION" or "HOST NOTIFICATION" (without a colon),
            // parameter lists not matching the corresponding format strings,
            // and last but not least wrong ordering of fields. The net result
            // of this tragedy is that due to legacy reasons, we have to support
            // parsing an incorrect ordering of "state type" and "command name"
            // fields. :-P
            if (state_type_.empty()) {
                return;  // extremely broken line
            }
            if (state_type_ == "check-mk-notify"sv) {
                // Ooops, we encounter one of our own buggy lines...
                std::swap(state_type_, command_name_);
                if (state_type_.empty()) {
                    return;  // extremely broken line, even after swapping
                }
            }
            state_ = service_description_.empty()
                         ? static_cast<int>(parseHostState(state_type_))
                         : static_cast<int>(parseServiceState(state_type_));
            return;
        case Param::ContactName:
            contact_name_ = field;
            return;
        case Param::HostState:
            state_ = static_cast<int>(parseHostState(field));
            return;
        case Param::ServiceState:
        case Param::ExitCode:  // HACK: Encoded as a service state! :-P
            state_ = static_cast<int>(parseServiceState(field));
            return;
        case Param::State:
            state_ = 0;
            std::from_chars(field.data(), field.data() + field.size(), state_);
            return;
        case Param::StateType:
            state_type_ = field;
            return;
        case Param::Attempt:
            attempt_ = 0;
            std::from_chars(field.data(), field.data() + field.size(),
                            attempt_);
            return;
        case Param::Comment:
            comment_ = field;
            return;
        case Param::PluginOutput:
            plugin_output_ = field;
            return;
        case Param::LongPluginOutput:
            long_plugin_output_ = field;
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
    std::string_view message_sv{message_};
    for (const auto &def : log_definitions) {
        if (textStartsWith(def.prefix) &&
            message_.compare(timestamp_prefix_length + def.prefix.size(), 2,
                             ": ") == 0) {
            type_ = def.prefix;
            class_ = def.log_class;
            kind_ = def.log_type;
            // TODO(sp) Use boost::tokenizer instead of this index fiddling
            size_t pos = timestamp_prefix_length + def.prefix.size() + 2;
            for (Param par : def.params) {
                size_t sep_pos = message_.find(';', pos);
                size_t end_pos =
                    sep_pos == std::string::npos ? message_.size() : sep_pos;
                assign(par, message_sv.substr(pos, end_pos - pos));
                pos = sep_pos == std::string::npos ? message_.size()
                                                   : (sep_pos + 1);
            }
            return;
        }
    }
    type_ = message_sv.substr(timestamp_prefix_length);
    if (textStartsWith("LOG VERSION: 2.0")) {
        class_ = Class::program;
        kind_ = LogEntryKind::log_version;
        return;
    }
    if (textStartsWith("logging initial states") ||
        textStartsWith("logging intitial states")) {
        class_ = Class::program;
        kind_ = LogEntryKind::log_initial_states;
        return;
    }
    if (textContains("starting...") || textContains("active mode...")) {
        class_ = Class::program;
        kind_ = LogEntryKind::core_starting;
        return;
    }
    if (textContains("shutting down...") || textContains("Bailing out") ||
        textContains("standby mode...")) {
        class_ = Class::program;
        kind_ = LogEntryKind::core_stopping;
        return;
    }
    class_ = Class::info;
    kind_ = LogEntryKind::none;
}

bool LogEntry::textStartsWith(const std::string &what) const {
    return message_.compare(timestamp_prefix_length, what.size(), what) == 0;
}

bool LogEntry::textContains(const std::string &what) const {
    return message_.find(what, timestamp_prefix_length) != std::string::npos;
}

namespace {
// TODO(sp) copy-n-paste from FetcherHelperChannel!
template <class T, size_t N>
using one_of = std::array<std::pair<std::string_view, T>, N>;

// As complicated and inefficient as it looks, the function below is completely
// unfolded in code: It basically results in very fast if-then-else cascades,
// guarded by the lengths, see: https://www.youtube.com/watch?v=INn3xa4pMfg
template <class T, size_t N>
T parseState(std::string_view str, const one_of<T, N> &table, T default_value) {
    // Ugly: Depending on where we're called, the actual state type can be in
    // parentheses at the end, e.g. "ALERTHANDLER (OK)".
    if (!str.empty() && str[str.size() - 1] == ')') {
        size_t lparen = str.rfind('(');
        if (lparen != std::string::npos) {
            str = str.substr(lparen + 1, str.size() - lparen - 2);
        }
    }
    auto it = std::find_if(begin(table), end(table),
                           [&](const auto &v) { return v.first == str; });
    return it == table.end() ? default_value : it->second;
}

}  // namespace

// static
ServiceState LogEntry::parseServiceState(std::string_view str) {
    static constexpr one_of<ServiceState, 5> states{
        {// normal states
         {"OK"sv, ServiceState::ok},
         {"WARNING"sv, ServiceState::warning},
         {"CRITICAL"sv, ServiceState::critical},
         {"UNKNOWN"sv, ServiceState::unknown},
         // states from "... ALERT"/"... NOTIFICATION"
         {"RECOVERY"sv, ServiceState::ok}}};
    return parseState(str, states, ServiceState::ok);
}

// static
HostState LogEntry::parseHostState(std::string_view str) {
    static constexpr one_of<HostState, 8> states{
        {// normal states
         {"UP"sv, HostState::up},
         {"DOWN"sv, HostState::down},
         {"UNREACHABLE"sv, HostState::unreachable},
         // states from "... ALERT"/"... NOTIFICATION"
         {"RECOVERY"sv, HostState::up},
         // states from "... ALERT HANDLER STOPPED" and "(HOST|SERVICE)
         // NOTIFICATION
         // (RESULT|PROGRESS)"
         {"OK"sv, HostState::up},
         {"WARNING"sv, HostState::down},
         {"CRITICAL"sv, HostState::unreachable},
         {"UNKNOWN"sv, static_cast<HostState>(3)}}};  // Horrible HACK
    return parseState(str, states, HostState::up);
}

namespace {
std::string parens(std::string_view fun, std::string_view arg) {
    return std::string{fun} + " (" + std::string{arg} + ")";
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
    switch (kind_) {
        case LogEntryKind::state_host_initial:
        case LogEntryKind::state_host:
        case LogEntryKind::alert_host:
            return parens(state_type_, to_host_state(state_));

        case LogEntryKind::state_service_initial:
        case LogEntryKind::state_service:
        case LogEntryKind::alert_service:
            return parens(state_type_, to_service_state(state_));

        case LogEntryKind::none:
            if (type_ == "HOST NOTIFICATION RESULT"sv ||
                type_ == "SERVICE NOTIFICATION RESULT"sv ||
                type_ == "HOST NOTIFICATION PROGRESS"sv ||
                type_ == "SERVICE NOTIFICATION PROGRESS"sv ||
                type_ == "HOST ALERT HANDLER STOPPED"sv ||
                type_ == "SERVICE ALERT HANDLER STOPPED"sv) {
                return parens("EXIT_CODE"sv, to_exit_code(state_));
            }
            if (type_ == "HOST NOTIFICATION"sv) {
                if (state_type_ == "UP"sv ||    //
                    state_type_ == "DOWN"sv ||  //
                    state_type_ == "UNREACHABLE"sv) {
                    return parens("NOTIFY"sv, state_type_);
                }
                if (mk::starts_with(state_type_, "ALERTHANDLER (")) {
                    return parens("EXIT_CODE"sv, to_exit_code(state_));
                }
                return std::string{state_type_};
            }
            if (type_ == "SERVICE NOTIFICATION"sv) {
                if (state_type_ == "OK"sv ||        //
                    state_type_ == "WARNING"sv ||   //
                    state_type_ == "CRITICAL"sv ||  //
                    state_type_ == "UNKNOWN"sv) {
                    return parens("NOTIFY"sv, state_type_);
                }
                if (mk::starts_with(state_type_, "ALERTHANDLER ("sv)) {
                    return parens("EXIT_CODE"sv, to_exit_code(state_));
                }
                return std::string{state_type_};
            }
            if (type_ == "PASSIVE HOST CHECK"sv) {
                return parens("PASSIVE"sv, to_host_state(state_));
            }
            if (type_ == "PASSIVE SERVICE CHECK"sv) {
                return parens("PASSIVE"sv, to_service_state(state_));
            }
            return "";

        case LogEntryKind::downtime_alert_host:
        case LogEntryKind::downtime_alert_service:
        case LogEntryKind::flapping_host:
        case LogEntryKind::flapping_service:
        case LogEntryKind::acknowledge_alert_host:
        case LogEntryKind::acknowledge_alert_service:
            return std::string{state_type_};

        case LogEntryKind::timeperiod_transition:
        case LogEntryKind::core_starting:
        case LogEntryKind::core_stopping:
        case LogEntryKind::log_version:
        case LogEntryKind::log_initial_states:
            return "";
    }
    return "";  // unreachable, make the compiler happy
}
