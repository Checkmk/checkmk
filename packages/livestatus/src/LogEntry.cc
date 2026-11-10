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
#include <tuple>
#include <utility>
#include <vector>

#include "livestatus/StringUtils.h"

using namespace std::string_view_literals;

namespace {
// Same as text.starts_with(prefix), but without a memcmp() call when the first
// characters differ, which is the common case when classifying a log line.
bool has_prefix(std::string_view text, std::string_view prefix) {
    return prefix.empty() || (!text.empty() && text.front() == prefix.front() &&
                              text.starts_with(prefix));
}

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
    // NOTE: The command is parsed by external_command_target().
    LogDef{.prefix = "EXTERNAL COMMAND",
           .log_class = LogEntry::Class::ext_command,
           .log_type = LogEntryKind::none,
           .params = {}}};

enum class CommandTarget { none, host, service };

struct CommandDef {
    std::string_view name;
    CommandTarget target;
};

// The external commands whose arguments start with a host name, followed by a
// service description for service commands. If a service command has no
// service description, it refers to the host. All other commands, e.g. global,
// group, contact or ID-based ones, refer to no host, just like unknown ones.
// So does LOG (_LOG with Nagios): The core writes the logged line to the
// history right after the command, and that line is authorized on its own.
constexpr auto command_defs = std::to_array<CommandDef>({
    {.name = "ACKNOWLEDGE_HOST_PROBLEM"sv, .target = CommandTarget::host},
    {.name = "ACKNOWLEDGE_SVC_PROBLEM"sv, .target = CommandTarget::service},
    {.name = "ADD_HOST_COMMENT"sv, .target = CommandTarget::host},
    {.name = "ADD_SVC_COMMENT"sv, .target = CommandTarget::service},
    {.name = "CHANGE_CUSTOM_HOST_VAR"sv, .target = CommandTarget::host},
    {.name = "CHANGE_CUSTOM_SVC_VAR"sv, .target = CommandTarget::service},
    {.name = "CHANGE_HOST_CHECK_COMMAND"sv, .target = CommandTarget::host},
    {.name = "CHANGE_HOST_CHECK_TIMEPERIOD"sv, .target = CommandTarget::host},
    {.name = "CHANGE_HOST_EVENT_HANDLER"sv, .target = CommandTarget::host},
    {.name = "CHANGE_HOST_MODATTR"sv, .target = CommandTarget::host},
    {.name = "CHANGE_HOST_NOTIFICATION_TIMEPERIOD"sv,
     .target = CommandTarget::host},
    {.name = "CHANGE_MAX_HOST_CHECK_ATTEMPTS"sv, .target = CommandTarget::host},
    {.name = "CHANGE_MAX_SVC_CHECK_ATTEMPTS"sv,
     .target = CommandTarget::service},
    {.name = "CHANGE_NORMAL_HOST_CHECK_INTERVAL"sv,
     .target = CommandTarget::host},
    {.name = "CHANGE_NORMAL_SVC_CHECK_INTERVAL"sv,
     .target = CommandTarget::service},
    {.name = "CHANGE_RETRY_HOST_CHECK_INTERVAL"sv,
     .target = CommandTarget::host},
    {.name = "CHANGE_RETRY_SVC_CHECK_INTERVAL"sv,
     .target = CommandTarget::service},
    {.name = "CHANGE_SVC_CHECK_COMMAND"sv, .target = CommandTarget::service},
    {.name = "CHANGE_SVC_CHECK_TIMEPERIOD"sv, .target = CommandTarget::service},
    {.name = "CHANGE_SVC_EVENT_HANDLER"sv, .target = CommandTarget::service},
    {.name = "CHANGE_SVC_MODATTR"sv, .target = CommandTarget::service},
    {.name = "CHANGE_SVC_NOTIFICATION_TIMEPERIOD"sv,
     .target = CommandTarget::service},
    {.name = "DELAY_HOST_NOTIFICATION"sv, .target = CommandTarget::host},
    {.name = "DELAY_SVC_NOTIFICATION"sv, .target = CommandTarget::service},
    {.name = "DEL_ALL_HOST_COMMENTS"sv, .target = CommandTarget::host},
    {.name = "DEL_ALL_SVC_COMMENTS"sv, .target = CommandTarget::service},
    // host[;service[;start[;comment]]]
    {.name = "DEL_DOWNTIME_BY_HOST_NAME"sv, .target = CommandTarget::service},
    {.name = "DISABLE_ALL_NOTIFICATIONS_BEYOND_HOST"sv,
     .target = CommandTarget::host},
    {.name = "DISABLE_HOST_AND_CHILD_NOTIFICATIONS"sv,
     .target = CommandTarget::host},
    {.name = "DISABLE_HOST_CHECK"sv, .target = CommandTarget::host},
    {.name = "DISABLE_HOST_EVENT_HANDLER"sv, .target = CommandTarget::host},
    {.name = "DISABLE_HOST_FLAP_DETECTION"sv, .target = CommandTarget::host},
    {.name = "DISABLE_HOST_NOTIFICATIONS"sv, .target = CommandTarget::host},
    {.name = "DISABLE_HOST_SVC_CHECKS"sv, .target = CommandTarget::host},
    {.name = "DISABLE_HOST_SVC_NOTIFICATIONS"sv, .target = CommandTarget::host},
    {.name = "DISABLE_PASSIVE_HOST_CHECKS"sv, .target = CommandTarget::host},
    {.name = "DISABLE_PASSIVE_SVC_CHECKS"sv, .target = CommandTarget::service},
    {.name = "DISABLE_SVC_CHECK"sv, .target = CommandTarget::service},
    {.name = "DISABLE_SVC_EVENT_HANDLER"sv, .target = CommandTarget::service},
    {.name = "DISABLE_SVC_FLAP_DETECTION"sv, .target = CommandTarget::service},
    {.name = "DISABLE_SVC_NOTIFICATIONS"sv, .target = CommandTarget::service},
    {.name = "EC_DELETE_EVENTS_OF_HOST"sv, .target = CommandTarget::host},
    {.name = "ENABLE_ALL_NOTIFICATIONS_BEYOND_HOST"sv,
     .target = CommandTarget::host},
    {.name = "ENABLE_HOST_AND_CHILD_NOTIFICATIONS"sv,
     .target = CommandTarget::host},
    {.name = "ENABLE_HOST_CHECK"sv, .target = CommandTarget::host},
    {.name = "ENABLE_HOST_EVENT_HANDLER"sv, .target = CommandTarget::host},
    {.name = "ENABLE_HOST_FLAP_DETECTION"sv, .target = CommandTarget::host},
    {.name = "ENABLE_HOST_NOTIFICATIONS"sv, .target = CommandTarget::host},
    {.name = "ENABLE_HOST_SVC_CHECKS"sv, .target = CommandTarget::host},
    {.name = "ENABLE_HOST_SVC_NOTIFICATIONS"sv, .target = CommandTarget::host},
    {.name = "ENABLE_PASSIVE_HOST_CHECKS"sv, .target = CommandTarget::host},
    {.name = "ENABLE_PASSIVE_SVC_CHECKS"sv, .target = CommandTarget::service},
    {.name = "ENABLE_SVC_CHECK"sv, .target = CommandTarget::service},
    {.name = "ENABLE_SVC_EVENT_HANDLER"sv, .target = CommandTarget::service},
    {.name = "ENABLE_SVC_FLAP_DETECTION"sv, .target = CommandTarget::service},
    {.name = "ENABLE_SVC_NOTIFICATIONS"sv, .target = CommandTarget::service},
    {.name = "MK_LOGWATCH_ACKNOWLEDGE"sv, .target = CommandTarget::host},
    {.name = "PROCESS_HOST_CHECK_RESULT"sv, .target = CommandTarget::host},
    {.name = "PROCESS_HOST_PERFDATA"sv, .target = CommandTarget::host},
    {.name = "PROCESS_SERVICE_CHECK_RESULT"sv,
     .target = CommandTarget::service},
    {.name = "PROCESS_SVC_PERFDATA"sv, .target = CommandTarget::service},
    {.name = "REMOVE_HOST_ACKNOWLEDGEMENT"sv, .target = CommandTarget::host},
    {.name = "REMOVE_SVC_ACKNOWLEDGEMENT"sv, .target = CommandTarget::service},
    {.name = "SCHEDULE_AND_PROPAGATE_HOST_DOWNTIME"sv,
     .target = CommandTarget::host},
    {.name = "SCHEDULE_AND_PROPAGATE_TRIGGERED_HOST_DOWNTIME"sv,
     .target = CommandTarget::host},
    {.name = "SCHEDULE_FORCED_HOST_CHECK"sv, .target = CommandTarget::host},
    {.name = "SCHEDULE_FORCED_HOST_SVC_CHECKS"sv,
     .target = CommandTarget::host},
    {.name = "SCHEDULE_FORCED_SVC_CHECK"sv, .target = CommandTarget::service},
    {.name = "SCHEDULE_HOST_CHECK"sv, .target = CommandTarget::host},
    {.name = "SCHEDULE_HOST_DOWNTIME"sv, .target = CommandTarget::host},
    {.name = "SCHEDULE_HOST_SVC_CHECKS"sv, .target = CommandTarget::host},
    {.name = "SCHEDULE_HOST_SVC_DOWNTIME"sv, .target = CommandTarget::host},
    {.name = "SCHEDULE_SVC_CHECK"sv, .target = CommandTarget::service},
    {.name = "SCHEDULE_SVC_DOWNTIME"sv, .target = CommandTarget::service},
    {.name = "SEND_CUSTOM_HOST_NOTIFICATION"sv, .target = CommandTarget::host},
    {.name = "SEND_CUSTOM_SVC_NOTIFICATION"sv,
     .target = CommandTarget::service},
    {.name = "SET_HOST_NOTIFICATION_NUMBER"sv, .target = CommandTarget::host},
    {.name = "SET_SVC_NOTIFICATION_NUMBER"sv, .target = CommandTarget::service},
    {.name = "START_OBSESSING_OVER_HOST"sv, .target = CommandTarget::host},
    {.name = "START_OBSESSING_OVER_SVC"sv, .target = CommandTarget::service},
    {.name = "STOP_OBSESSING_OVER_HOST"sv, .target = CommandTarget::host},
    {.name = "STOP_OBSESSING_OVER_SVC"sv, .target = CommandTarget::service},
});

// The order of std::ranges::less, but inlined: Comparing names via memcmp()
// calls made parsing a command line up to 15% slower.
constexpr bool name_less(std::string_view a, std::string_view b) {
    const auto n = std::min(a.size(), b.size());
    for (size_t i = 0; i < n; ++i) {
        if (a[i] != b[i]) {
            return static_cast<unsigned char>(a[i]) <
                   static_cast<unsigned char>(b[i]);
        }
    }
    return a.size() < b.size();
}

static_assert(std::ranges::is_sorted(command_defs, name_less,
                                     &CommandDef::name),
              "command_defs must be sorted for the binary search");

// A command targets a host or a service, the latter exactly if its name has SVC
// or SERVICE, but not HOST in it. The only exception is
// DEL_DOWNTIME_BY_HOST_NAME with its optional service. This catches a wrong
// target in command_defs at compile time.
constexpr bool has_plausible_target(const CommandDef &def) {
    if (def.target == CommandTarget::none) {
        return false;
    }
    if (def.name == "DEL_DOWNTIME_BY_HOST_NAME"sv) {
        return def.target == CommandTarget::service;
    }
    auto has = [&def](std::string_view part) {
        return def.name.find(part) != std::string_view::npos;
    };
    return (def.target == CommandTarget::service) ==
           ((has("SVC") || has("SERVICE")) && !has("HOST"));
}

static_assert(std::ranges::all_of(command_defs, has_plausible_target),
              "command_defs must target a host, or a service for SVC/SERVICE");

CommandTarget command_target(std::string_view command) {
    const auto *it = std::ranges::lower_bound(command_defs, command, name_less,
                                              &CommandDef::name);
    return it != command_defs.end() && it->name == command
               ? it->target
               : CommandTarget::none;
}

// Returns the definition whose prefix, followed by ": ", starts the text.
const LogDef *find_log_def(std::string_view text) {
    for (const auto &def : log_definitions) {
        if (has_prefix(text, def.prefix) &&
            text.substr(def.prefix.size()).starts_with(": "sv)) {
            return &def;
        }
    }
    return nullptr;
}

// Removes the first field from a ';'-separated text and returns it.
std::string_view next_field(std::string_view &text) {
    const auto field = text.substr(0, text.find(';'));
    text.remove_prefix(std::min(text.size(), field.size() + 1));
    return field;
}

// Returns the host and service an external command refers to, if any, so that
// its entry can be authorized like the host and service entries.
std::pair<std::string_view, std::string_view> external_command_target(
    std::string_view command) {
    // e.g. ADD_SVC_COMMENT;host;service;... or ADD_HOST_COMMENT;host;...
    const auto target = command_target(next_field(command));
    if (target == CommandTarget::none) {
        return {};
    }
    const auto host_name = next_field(command);
    if (target == CommandTarget::host) {
        return {host_name, {}};
    }
    return {host_name, next_field(command)};
}

// Nagios logs commands it doesn't know as a warning instead of an EXTERNAL
// COMMAND line, e.g. MODIFY_HOST_DOWNTIME from the REST API.
constexpr auto unrecognized_command_prefix =
    "Warning: Unrecognized external command -> "sv;

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
            // NOLINTNEXTLINE(cppcoreguidelines-pro-bounds-pointer-arithmetic)
            std::from_chars(field.data(), field.data() + field.size(), state_);
            return;
        case LogEntryParam::StateType:
            state_type_ = field;
            return;
        case LogEntryParam::Attempt:
            attempt_ = 0;
            // NOLINTNEXTLINE(cppcoreguidelines-pro-bounds-pointer-arithmetic)
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
    if (const auto *def =
            find_log_def(message_sv.substr(timestamp_prefix_length))) {
        type_ = def->prefix;
        class_ = def->log_class;
        kind_ = def->log_type;
        // TODO(sp) Use boost::tokenizer instead of this index fiddling
        size_t pos = timestamp_prefix_length + def->prefix.size() + 2;
        for (LogEntryParam const par : def->params) {
            const size_t sep_pos = message_.find(';', pos);
            const size_t end_pos =
                sep_pos == std::string::npos ? message_.size() : sep_pos;
            assign(par, message_sv.substr(pos, end_pos - pos));
            pos =
                sep_pos == std::string::npos ? message_.size() : (sep_pos + 1);
        }
        if (class_ == LogEntry::Class::ext_command) {
            std::tie(host_name_, service_description_) =
                external_command_target(options_);
        }
        return;
    }
    type_ = message_sv.substr(timestamp_prefix_length);
    if (has_prefix(type_, unrecognized_command_prefix)) {
        class_ = LogEntry::Class::ext_command;
        kind_ = LogEntryKind::none;
        std::tie(host_name_, service_description_) = external_command_target(
            type_.substr(unrecognized_command_prefix.size()));
        return;
    }
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
    // All markers except "Bailing out" end in "...", so most lines need only
    // two scans instead of five.
    const bool has_ellipsis = textContains("...");
    if (has_ellipsis &&
        (textContains("starting...") || textContains("active mode..."))) {
        class_ = LogEntry::Class::program;
        kind_ = LogEntryKind::core_starting;
        return;
    }
    if (textContains("Bailing out") ||
        (has_ellipsis && (textContains("shutting down...") ||
                          textContains("standby mode...")))) {
        class_ = LogEntry::Class::program;
        kind_ = LogEntryKind::core_stopping;
        return;
    }
    class_ = LogEntry::Class::info;
    kind_ = LogEntryKind::none;
}

bool LogEntry::textStartsWith(std::string_view what) const {
    return has_prefix(
        std::string_view{message_}.substr(timestamp_prefix_length), what);
}

bool LogEntry::textContains(std::string_view what) const {
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
