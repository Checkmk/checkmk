// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/LogEntry.h"

#include <algorithm>
#include <array>
#include <charconv>
#include <ctime>
#include <iterator>
#include <stdexcept>
#include <system_error>
#include <utility>
#include <vector>

#include "livestatus/StringUtils.h"

using namespace std::string_view_literals;

namespace {
struct LogDef {
    std::string prefix;
    LogEntry::Class log_class;
    LogEntryKind log_type;
    std::vector<LogEntryParam> params;
};

// NOLINTNEXTLINE(cert-err58-cpp)
const std::vector<LogDef> log_definitions{
    LogDef{.prefix = "INITIAL HOST STATE",
           .log_class = LogEntry::Class::state,
           .log_type = LogEntryKind::initial_host_state,
           .params = {LogEntryParam::HostName, LogEntryParam::HostState,
                      LogEntryParam::StateType, LogEntryParam::Attempt,
                      LogEntryParam::PluginOutput,
                      LogEntryParam::LongPluginOutput}},
    LogDef{.prefix = "CURRENT HOST STATE",
           .log_class = LogEntry::Class::state,
           .log_type = LogEntryKind::current_host_state,
           .params = {LogEntryParam::HostName, LogEntryParam::HostState,
                      LogEntryParam::StateType, LogEntryParam::Attempt,
                      LogEntryParam::PluginOutput,
                      LogEntryParam::LongPluginOutput}},
    LogDef{.prefix = "HOST ALERT",
           .log_class = LogEntry::Class::alert,
           .log_type = LogEntryKind::host_alert,
           .params = {LogEntryParam::HostName, LogEntryParam::HostState,
                      LogEntryParam::StateType, LogEntryParam::Attempt,
                      LogEntryParam::PluginOutput,
                      LogEntryParam::LongPluginOutput}},
    LogDef{.prefix = "HOST DOWNTIME ALERT",
           .log_class = LogEntry::Class::alert,
           .log_type = LogEntryKind::host_downtime_alert,
           .params = {LogEntryParam::HostName, LogEntryParam::StateType,
                      LogEntryParam::Comment}},
    LogDef{.prefix = "HOST ACKNOWLEDGE ALERT",
           .log_class = LogEntry::Class::alert,
           .log_type = LogEntryKind::host_acknowledge_alert,
           .params = {LogEntryParam::HostName, LogEntryParam::StateType,
                      LogEntryParam::ContactName, LogEntryParam::Comment}},
    LogDef{.prefix = "HOST FLAPPING ALERT",
           .log_class = LogEntry::Class::alert,
           .log_type = LogEntryKind::host_flapping_alert,
           .params = {LogEntryParam::HostName, LogEntryParam::StateType,
                      LogEntryParam::Comment}},
    LogDef{
        .prefix = "INITIAL SERVICE STATE",
        .log_class = LogEntry::Class::state,
        .log_type = LogEntryKind::initial_service_state,
        .params = {LogEntryParam::HostName, LogEntryParam::ServiceDescription,
                   LogEntryParam::ServiceState, LogEntryParam::StateType,
                   LogEntryParam::Attempt, LogEntryParam::PluginOutput,
                   LogEntryParam::LongPluginOutput}},
    LogDef{
        .prefix = "CURRENT SERVICE STATE",
        .log_class = LogEntry::Class::state,
        .log_type = LogEntryKind::current_service_state,
        .params = {LogEntryParam::HostName, LogEntryParam::ServiceDescription,
                   LogEntryParam::ServiceState, LogEntryParam::StateType,
                   LogEntryParam::Attempt, LogEntryParam::PluginOutput,
                   LogEntryParam::LongPluginOutput}},
    LogDef{
        .prefix = "SERVICE ALERT",
        .log_class = LogEntry::Class::alert,
        .log_type = LogEntryKind::service_alert,
        .params = {LogEntryParam::HostName, LogEntryParam::ServiceDescription,
                   LogEntryParam::ServiceState, LogEntryParam::StateType,
                   LogEntryParam::Attempt, LogEntryParam::PluginOutput,
                   LogEntryParam::LongPluginOutput}},
    LogDef{
        .prefix = "SERVICE DOWNTIME ALERT",
        .log_class = LogEntry::Class::alert,
        .log_type = LogEntryKind::service_downtime_alert,
        .params = {LogEntryParam::HostName, LogEntryParam::ServiceDescription,
                   LogEntryParam::StateType, LogEntryParam::Comment}},
    LogDef{
        .prefix = "SERVICE ACKNOWLEDGE ALERT",
        .log_class = LogEntry::Class::alert,
        .log_type = LogEntryKind::service_acknowledge_alert,
        .params = {LogEntryParam::HostName, LogEntryParam::ServiceDescription,
                   LogEntryParam::StateType, LogEntryParam::ContactName,
                   LogEntryParam::Comment}},
    LogDef{
        .prefix = "SERVICE FLAPPING ALERT",
        .log_class = LogEntry::Class::alert,
        .log_type = LogEntryKind::service_flapping_alert,
        .params = {LogEntryParam::HostName, LogEntryParam::ServiceDescription,
                   LogEntryParam::StateType, LogEntryParam::Comment}},
    LogDef{.prefix = "TIMEPERIOD TRANSITION",
           .log_class = LogEntry::Class::state,
           .log_type = LogEntryKind::timeperiod_transition,
           .params =
               {
                   LogEntryParam::Ignore,  // name
                   LogEntryParam::Ignore,  // from
                   LogEntryParam::Ignore   // to
               }},
    // NOTE: Generated by CMC & mknotifyd, see cmk.utils.notification_message
    LogDef{.prefix = "HOST NOTIFICATION",
           .log_class = LogEntry::Class::hs_notification,
           .log_type = LogEntryKind::none,
           .params = {LogEntryParam::ContactName, LogEntryParam::HostName,
                      LogEntryParam::StateType,
                      LogEntryParam::CommandNameWithWorkaround,
                      LogEntryParam::PluginOutput,
                      LogEntryParam::Ignore,  // author
                      LogEntryParam::Comment, LogEntryParam::LongPluginOutput}},
    // NOTE: Generated by CMC & mknotifyd, see cmk.utils.notification_message
    LogDef{
        .prefix = "SERVICE NOTIFICATION",
        .log_class = LogEntry::Class::hs_notification,
        .log_type = LogEntryKind::none,
        .params = {LogEntryParam::ContactName, LogEntryParam::HostName,
                   LogEntryParam::ServiceDescription, LogEntryParam::StateType,
                   LogEntryParam::CommandNameWithWorkaround,
                   LogEntryParam::PluginOutput,
                   LogEntryParam::Ignore,  // author
                   LogEntryParam::Comment, LogEntryParam::LongPluginOutput}},
    // NOTE: Generated by mknotifyd & notification helper, see
    // cmk.utils.notification_result_message
    LogDef{.prefix = "HOST NOTIFICATION RESULT",
           .log_class = LogEntry::Class::hs_notification,
           .log_type = LogEntryKind::none,
           .params = {LogEntryParam::ContactName, LogEntryParam::HostName,
                      LogEntryParam::StateType,
                      LogEntryParam::CommandNameWithWorkaround,
                      LogEntryParam::PluginOutput, LogEntryParam::Comment}},
    // NOTE: Generated by mknotifyd & notification helper, see
    // cmk.utils.notification_result_message
    LogDef{
        .prefix = "SERVICE NOTIFICATION RESULT",
        .log_class = LogEntry::Class::hs_notification,
        .log_type = LogEntryKind::none,
        .params = {LogEntryParam::ContactName, LogEntryParam::HostName,
                   LogEntryParam::ServiceDescription, LogEntryParam::StateType,
                   LogEntryParam::CommandNameWithWorkaround,
                   LogEntryParam::PluginOutput, LogEntryParam::Comment}},
    LogDef{.prefix = "HOST NOTIFICATION PROGRESS",
           .log_class = LogEntry::Class::hs_notification,
           .log_type = LogEntryKind::none,
           .params = {LogEntryParam::ContactName, LogEntryParam::HostName,
                      LogEntryParam::StateType,
                      LogEntryParam::CommandNameWithWorkaround,
                      LogEntryParam::PluginOutput}},
    // NOTE: Generated by mknotifyd, see cmk.utils.notification_progress_message
    LogDef{
        .prefix = "SERVICE NOTIFICATION PROGRESS",
        .log_class = LogEntry::Class::hs_notification,
        .log_type = LogEntryKind::none,
        .params = {LogEntryParam::ContactName, LogEntryParam::HostName,
                   LogEntryParam::ServiceDescription, LogEntryParam::StateType,
                   LogEntryParam::CommandNameWithWorkaround,
                   LogEntryParam::PluginOutput}},
    // NOTE: Generated by mknotifyd, see cmk.utils.notification_progress_message
    LogDef{.prefix = "HOST ALERT HANDLER STARTED",
           .log_class = LogEntry::Class::alert_handlers,
           .log_type = LogEntryKind::none,
           .params = {LogEntryParam::HostName, LogEntryParam::CommandName}},
    LogDef{
        .prefix = "SERVICE ALERT HANDLER STARTED",
        .log_class = LogEntry::Class::alert_handlers,
        .log_type = LogEntryKind::none,
        .params = {LogEntryParam::HostName, LogEntryParam::ServiceDescription,
                   LogEntryParam::CommandName}},
    LogDef{.prefix = "HOST ALERT HANDLER STOPPED",
           .log_class = LogEntry::Class::alert_handlers,
           .log_type = LogEntryKind::none,
           .params = {LogEntryParam::HostName, LogEntryParam::CommandName,
                      LogEntryParam::ExitCode, LogEntryParam::PluginOutput}},
    LogDef{
        .prefix = "SERVICE ALERT HANDLER STOPPED",
        .log_class = LogEntry::Class::alert_handlers,
        .log_type = LogEntryKind::none,
        .params = {LogEntryParam::HostName, LogEntryParam::ServiceDescription,
                   LogEntryParam::CommandName, LogEntryParam::ExitCode,
                   LogEntryParam::PluginOutput}},
    // NOTE: Generated by Nagios only
    LogDef{
        .prefix = "PASSIVE SERVICE CHECK",
        .log_class = LogEntry::Class::passivecheck,
        .log_type = LogEntryKind::none,
        .params = {LogEntryParam::HostName, LogEntryParam::ServiceDescription,
                   LogEntryParam::State, LogEntryParam::PluginOutput}},
    // NOTE: Generated by Nagios only
    LogDef{.prefix = "PASSIVE HOST CHECK",
           .log_class = LogEntry::Class::passivecheck,
           .log_type = LogEntryKind::none,
           .params = {LogEntryParam::HostName, LogEntryParam::State,
                      LogEntryParam::PluginOutput}},
    LogDef{.prefix = "EXTERNAL COMMAND",
           .log_class = LogEntry::Class::ext_command,
           .log_type = LogEntryKind::none,
           .params = {
               LogEntryParam::Ignore  // command
           }}};

}  // namespace
// 0123456789012345678901234567890
// [1234567890] FOO BAR: blah blah
static constexpr size_t timestamp_prefix_length = 13;

// TODO(sp) Fix classifyLogMessage() below to always set all fields and remove
// this set-me-to-zero-to-be-sure-block.
// NOLINTNEXTLINE(cppcoreguidelines-pro-type-member-init)
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

std::string LogEntry::long_plugin_output() const {
    return LogEntry::encode(std::string{long_plugin_output_});
}

std::string LogEntry::encode(const std::string &str) {
    return mk::replace_all(str, R"(\n)", "\n");
}

void LogEntry::assign(LogEntryParam par, std::string_view field) {
    switch (par) {
        case LogEntryParam::HostName:
            host_name_ = field;
            return;
        case LogEntryParam::ServiceDescription:
            service_description_ = field;
            return;
        case LogEntryParam::CommandName:
            command_name_ = field;
            return;
        case LogEntryParam::CommandNameWithWorkaround:
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
        case LogEntryParam::ContactName:
            contact_name_ = field;
            return;
        case LogEntryParam::HostState:
            state_ = static_cast<int>(parseHostState(field));
            return;
        case LogEntryParam::ServiceState:
        case LogEntryParam::ExitCode:  // HACK: Encoded as a service state! :-P
            state_ = static_cast<int>(parseServiceState(field));
            return;
        case LogEntryParam::State:
            state_ = 0;
            std::from_chars(field.data(), field.data() + field.size(), state_);
            return;
        case LogEntryParam::StateType:
            state_type_ = field;
            return;
        case LogEntryParam::Attempt:
            attempt_ = 0;
            std::from_chars(field.data(), field.data() + field.size(),
                            attempt_);
            return;
        case LogEntryParam::Comment:
            comment_ = field;
            return;
        case LogEntryParam::PluginOutput:
            plugin_output_ = field;
            return;
        case LogEntryParam::LongPluginOutput:
            long_plugin_output_ = field;
            return;
        case LogEntryParam::Ignore:
            return;
    }
};

// A bit verbose, but we avoid unnecessary string copies below.
void LogEntry::classifyLogMessage() {
    const std::string_view message_sv{message_};
    for (const auto &def : log_definitions) {
        if (textStartsWith(def.prefix) &&
            message_.compare(timestamp_prefix_length + def.prefix.size(), 2,
                             ": ") == 0) {
            type_ = def.prefix;
            class_ = def.log_class;
            kind_ = def.log_type;
            // TODO(sp) Use boost::tokenizer instead of this index fiddling
            size_t pos = timestamp_prefix_length + def.prefix.size() + 2;
            for (LogEntryParam const par : def.params) {
                const size_t sep_pos = message_.find(';', pos);
                const size_t end_pos =
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
        class_ = LogEntry::Class::program;
        kind_ = LogEntryKind::log_version;
        return;
    }
    if (textStartsWith("logging initial states") ||
        textStartsWith("logging intitial states")) {
        class_ = LogEntry::Class::program;
        kind_ = LogEntryKind::logging_initial_states;
        return;
    }
    if (textContains("starting...") || textContains("active mode...")) {
        class_ = LogEntry::Class::program;
        kind_ = LogEntryKind::core_starting;
        return;
    }
    if (textContains("shutting down...") || textContains("Bailing out") ||
        textContains("standby mode...")) {
        class_ = LogEntry::Class::program;
        kind_ = LogEntryKind::core_stopping;
        return;
    }
    class_ = LogEntry::Class::info;
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
template <typename T, size_t N>
using one_of = std::array<std::pair<std::string_view, T>, N>;

// As complicated and inefficient as it looks, the function below is completely
// unfolded in code: It basically results in very fast if-then-else cascades,
// guarded by the lengths, see: https://www.youtube.com/watch?v=INn3xa4pMfg
template <typename T, size_t N>
T parseState(std::string_view str, const one_of<T, N> &table, T default_value) {
    // Ugly: Depending on where we're called, the actual state type can be in
    // parentheses at the end, e.g. "ALERTHANDLER (OK)".
    if (!str.empty() && str[str.size() - 1] == ')') {
        const size_t lparen = str.rfind('(');
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

// NOLINTNEXTLINE(readability-function-cognitive-complexity)
std::string LogEntry::state_info() const {
    switch (kind_) {
        case LogEntryKind::initial_host_state:
        case LogEntryKind::current_host_state:
        case LogEntryKind::host_alert:
            return parens(state_type_, to_host_state(state_));

        case LogEntryKind::initial_service_state:
        case LogEntryKind::current_service_state:
        case LogEntryKind::service_alert:
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
                if (state_type_.starts_with("ALERTHANDLER (")) {
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
                if (state_type_.starts_with("ALERTHANDLER ("sv)) {
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

        case LogEntryKind::host_downtime_alert:
        case LogEntryKind::service_downtime_alert:
        case LogEntryKind::host_flapping_alert:
        case LogEntryKind::service_flapping_alert:
        case LogEntryKind::host_acknowledge_alert:
        case LogEntryKind::service_acknowledge_alert:
            return std::string{state_type_};

        case LogEntryKind::timeperiod_transition:
        case LogEntryKind::core_starting:
        case LogEntryKind::core_stopping:
        case LogEntryKind::log_version:
        case LogEntryKind::logging_initial_states:
            return "";
    }
    return "";  // unreachable, make the compiler happy
}
