// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <chrono>
#include <ctime>
#include <stdexcept>
#include <string>
#include <tuple>
#include <utility>
#include <variant>
#include <vector>

#include "LogEntry.h"
#include "gtest/gtest.h"

using namespace std::string_literals;

namespace {
template <class T>
using table = std::vector<std::tuple<std::string, T>>;

const table<HostState> host_states{{"UP", HostState::up},
                                   {"DOWN", HostState::down},
                                   {"UNREACHABLE", HostState::unreachable}};

const table<ServiceState> service_states{{"OK", ServiceState::ok},
                                         {"WARNING", ServiceState::warning},
                                         {"CRITICAL", ServiceState::critical},
                                         {"UNKNOWN", ServiceState::unknown}};

using info_table = std::vector<std::tuple<std::string, int, std::string>>;

// NOTE: A few LogEntry types abuse a service state when actually the exit code
// of a process is meant.
const info_table exit_codes{
    {"OK", static_cast<int>(ServiceState::ok), "SUCCESS"},
    {"WARNING", static_cast<int>(ServiceState::warning), "TEMPORARY_FAILURE"},
    {"CRITICAL", static_cast<int>(ServiceState::critical), "PERMANENT_FAILURE"},
    {"UNKNOWN", static_cast<int>(ServiceState::unknown), "FUNNY_EXIT_CODE_3"}};

using strings = std::vector<std::string>;

const strings host_service_state_types{"HARD", "SOFT"};

const strings downtime_flapping_state_types{"STARTED", "STOPPED"};

const strings acknowledge_state_types{"STARTED", "EXPIRED", "CANCELLED", "END"};

const strings reasons{"CUSTOM",      "ACKNOWLEDGEMENT",   "DOWNTIMESTART",
                      "DOWNTIMEEND", "DOWNTIMECANCELLED", "FLAPPINGSTART",
                      "FLAPPINGSTOP"};

std::string parens(const std::string &f, const std::string &arg) {
    return f + " (" + arg + ")";
}

std::chrono::system_clock::time_point tp(time_t t) {
    return std::chrono::system_clock::from_time_t(t);
}

// host_or_svc_state | reason (host_or_svc_state) | ALERTHANDLER (exit_code)
template <class T>
info_table notification_state_types(const table<T> &states) {
    info_table result;
    for (const auto &[state_name, state] : states) {
        result.push_back({state_name,  //
                          static_cast<int>(state),
                          parens("NOTIFY", state_name)});
        for (const auto &reason : reasons) {
            result.push_back({parens(reason, state_name),
                              static_cast<int>(state),
                              parens(reason, state_name)});
        }
    }
    for (const auto &[code_name, code, info] : exit_codes) {
        result.push_back({parens("ALERTHANDLER", code_name),  //
                          code,                               //
                          parens("EXIT_CODE", info)});
    }
    return result;
}
}  // namespace

TEST(LogEntry, InitialHostState) {
    // The host state string is directly taken from a log line field.
    for (const auto &[state_name, state] : host_states) {
        for (const auto &state_type : host_service_state_types) {
            auto line =
                "[1551424305] INITIAL HOST STATE: huey;"s.append(state_name)
                    .append(";")
                    .append(state_type)
                    .append(";7;Krasser Output;Laaang");
            LogEntry e{42, line};
            EXPECT_EQ(size_t{42}, e.lineno());
            EXPECT_EQ(tp(1551424305), e.time());
            EXPECT_EQ(LogEntry::Class::state, e.log_class());
            EXPECT_EQ(LogEntryKind::state_host_initial, e.kind());
            EXPECT_EQ(line, e.message());
            EXPECT_EQ("huey;"s.append(state_name)
                          .append(";")
                          .append(state_type)
                          .append(";7;Krasser Output;Laaang"),
                      e.options());
            EXPECT_EQ("INITIAL HOST STATE"s, e.type());
            EXPECT_EQ("huey", e.host_name());
            EXPECT_EQ("", e.service_description());
            EXPECT_EQ("", e.command_name());
            EXPECT_EQ("", e.contact_name());
            EXPECT_EQ(static_cast<int>(state), e.state());
            EXPECT_EQ(state_type, e.state_type());
            EXPECT_EQ(7, e.attempt());
            EXPECT_EQ("Krasser Output", e.plugin_output());
            EXPECT_EQ("Laaang", e.long_plugin_output());
            EXPECT_EQ("", e.comment());
            EXPECT_EQ(parens(state_type, state_name), e.state_info());
        }
    }
}

TEST(LogEntry, InitialHostStateWithoutLongOutput) {
    auto line =
        "[1551424305] INITIAL HOST STATE: huey;UP;HARD;7;Krasser Output"s;
    LogEntry e{42, line};
    EXPECT_EQ(size_t{42}, e.lineno());
    EXPECT_EQ(tp(1551424305), e.time());
    EXPECT_EQ(LogEntry::Class::state, e.log_class());
    EXPECT_EQ(LogEntryKind::state_host_initial, e.kind());
    EXPECT_EQ(line, e.message());
    EXPECT_EQ("huey;UP;HARD;7;Krasser Output"s, e.options());
    EXPECT_EQ("INITIAL HOST STATE"s, e.type());
    EXPECT_EQ("huey", e.host_name());
    EXPECT_EQ("", e.service_description());
    EXPECT_EQ("", e.command_name());
    EXPECT_EQ("", e.contact_name());
    EXPECT_EQ(static_cast<int>(HostState::up), e.state());
    EXPECT_EQ("HARD", e.state_type());
    EXPECT_EQ(7, e.attempt());
    EXPECT_EQ("Krasser Output", e.plugin_output());
    EXPECT_EQ("", e.long_plugin_output());
    EXPECT_EQ("", e.comment());
    EXPECT_EQ("HARD (UP)", e.state_info());
}

TEST(LogEntry, InitialHostStateWithMultiLine) {
    const auto *line =
        R"([1551424305] INITIAL HOST STATE: huey;UP;HARD;7;Krasser Output;Laaanger\nLong\nOutput)";
    LogEntry e{42, line};
    EXPECT_EQ(size_t{42}, e.lineno());
    EXPECT_EQ(tp(1551424305), e.time());
    EXPECT_EQ(LogEntry::Class::state, e.log_class());
    EXPECT_EQ(LogEntryKind::state_host_initial, e.kind());
    EXPECT_EQ(line, e.message());
    EXPECT_EQ("huey;UP;HARD;7;Krasser Output;Laaanger\\nLong\\nOutput"s,
              e.options());
    EXPECT_EQ("INITIAL HOST STATE"s, e.type());
    EXPECT_EQ("huey", e.host_name());
    EXPECT_EQ("", e.service_description());
    EXPECT_EQ("", e.command_name());
    EXPECT_EQ("", e.contact_name());
    EXPECT_EQ(static_cast<int>(HostState::up), e.state());
    EXPECT_EQ("HARD", e.state_type());
    EXPECT_EQ(7, e.attempt());
    EXPECT_EQ("Krasser Output", e.plugin_output());
    EXPECT_EQ("Laaanger\nLong\nOutput", e.long_plugin_output());
    EXPECT_EQ("", e.comment());
    EXPECT_EQ("HARD (UP)", e.state_info());
}

TEST(LogEntry, CurrentHostState) {
    // The host state string is directly taken from a log line field.
    for (const auto &[state_name, state] : host_states) {
        for (const auto &state_type : host_service_state_types) {
            auto line =
                "[1551424315] CURRENT HOST STATE: dewey;"s.append(state_name)
                    .append(";")
                    .append(state_type)
                    .append(";8;Voll krasser Output;long");
            LogEntry e{43, line};
            EXPECT_EQ(size_t{43}, e.lineno());
            EXPECT_EQ(tp(1551424315), e.time());
            EXPECT_EQ(LogEntry::Class::state, e.log_class());
            EXPECT_EQ(LogEntryKind::state_host, e.kind());
            EXPECT_EQ(line, e.message());
            EXPECT_EQ("dewey;"s.append(state_name)
                          .append(";")
                          .append(state_type)
                          .append(";8;Voll krasser Output;long"),
                      e.options());
            EXPECT_EQ("CURRENT HOST STATE"s, e.type());
            EXPECT_EQ("dewey", e.host_name());
            EXPECT_EQ("", e.service_description());
            EXPECT_EQ("", e.command_name());
            EXPECT_EQ("", e.contact_name());
            EXPECT_EQ(static_cast<int>(state), e.state());
            EXPECT_EQ(state_type, e.state_type());
            EXPECT_EQ(8, e.attempt());
            EXPECT_EQ("Voll krasser Output", e.plugin_output());
            EXPECT_EQ("long", e.long_plugin_output());
            EXPECT_EQ("", e.comment());
            EXPECT_EQ(parens(state_type, state_name), e.state_info());
        }
    }
}

TEST(LogEntry, HostAlert) {
    // The host state string is directly taken from a log line field.
    for (const auto &[state_name, state] : host_states) {
        for (const auto &state_type : host_service_state_types) {
            auto line = "[1551424323] HOST ALERT: huey;"s.append(state_name)
                            .append(";")
                            .append(state_type)
                            .append(";1234;Komisch...;Lalalang");
            LogEntry e{123456, line};
            EXPECT_EQ(size_t{123456}, e.lineno());
            EXPECT_EQ(tp(1551424323), e.time());
            EXPECT_EQ(LogEntry::Class::alert, e.log_class());
            EXPECT_EQ(LogEntryKind::alert_host, e.kind());
            EXPECT_EQ(line, e.message());
            EXPECT_EQ("huey;"s.append(state_name)
                          .append(";")
                          .append(state_type)
                          .append(";1234;Komisch...;Lalalang"),
                      e.options());
            EXPECT_EQ("HOST ALERT"s, e.type());
            EXPECT_EQ("huey", e.host_name());
            EXPECT_EQ("", e.service_description());
            EXPECT_EQ("", e.command_name());
            EXPECT_EQ("", e.contact_name());
            EXPECT_EQ(static_cast<int>(state), e.state());
            EXPECT_EQ(state_type, e.state_type());
            EXPECT_EQ(1234, e.attempt());
            EXPECT_EQ("Komisch...", e.plugin_output());
            EXPECT_EQ("Lalalang", e.long_plugin_output());
            EXPECT_EQ("", e.comment());
            EXPECT_EQ(parens(state_type, state_name), e.state_info());
        }
    }
}

TEST(LogEntry, HostDowntimeAlert) {
    for (const auto &state_type : downtime_flapping_state_types) {
        auto line = "[1551424323] HOST DOWNTIME ALERT: huey;" + state_type +
                    ";Komisch...";
        LogEntry e{123456, line};
        EXPECT_EQ(size_t{123456}, e.lineno());
        EXPECT_EQ(tp(1551424323), e.time());
        EXPECT_EQ(LogEntry::Class::alert, e.log_class());
        EXPECT_EQ(LogEntryKind::downtime_alert_host, e.kind());
        EXPECT_EQ(line, e.message());
        EXPECT_EQ("huey;" + state_type + ";Komisch...", e.options());
        EXPECT_EQ("HOST DOWNTIME ALERT"s, e.type());
        EXPECT_EQ("huey", e.host_name());
        EXPECT_EQ("", e.service_description());
        EXPECT_EQ("", e.command_name());
        EXPECT_EQ("", e.contact_name());
        EXPECT_EQ(static_cast<int>(HostState::up), e.state());
        EXPECT_EQ(state_type, e.state_type());
        EXPECT_EQ(0, e.attempt());
        EXPECT_EQ("", e.plugin_output());
        EXPECT_EQ("", e.long_plugin_output());
        EXPECT_EQ("Komisch...", e.comment());
        EXPECT_EQ(state_type, e.state_info());
    }
}

TEST(LogEntry, HostAcknowledgeAlert) {
    for (const auto &state_type : acknowledge_state_types) {
        auto line = "[1551424323] HOST ACKNOWLEDGE ALERT: huey;" + state_type +
                    ";King Kong;foo bar";
        LogEntry e{123456, line};
        EXPECT_EQ(size_t{123456}, e.lineno());
        EXPECT_EQ(tp(1551424323), e.time());
        EXPECT_EQ(LogEntry::Class::alert, e.log_class());
        EXPECT_EQ(LogEntryKind::acknowledge_alert_host, e.kind());
        EXPECT_EQ(line, e.message());
        EXPECT_EQ("huey;" + state_type + ";King Kong;foo bar", e.options());
        EXPECT_EQ("HOST ACKNOWLEDGE ALERT"s, e.type());
        EXPECT_EQ("huey", e.host_name());
        EXPECT_EQ("", e.service_description());
        EXPECT_EQ("", e.command_name());
        EXPECT_EQ("King Kong", e.contact_name());
        EXPECT_EQ(static_cast<int>(HostState::up), e.state());
        EXPECT_EQ(state_type, e.state_type());
        EXPECT_EQ(0, e.attempt());
        EXPECT_EQ("", e.plugin_output());
        EXPECT_EQ("", e.long_plugin_output());
        EXPECT_EQ("foo bar", e.comment());
        EXPECT_EQ(state_type, e.state_info());
    }
}

TEST(LogEntry, HostFlappingAlert) {
    for (const auto &state_type : downtime_flapping_state_types) {
        auto line =
            "[1551424323] HOST FLAPPING ALERT: huey;" + state_type + ";foo bar";
        LogEntry e{123456, line};
        EXPECT_EQ(size_t{123456}, e.lineno());
        EXPECT_EQ(tp(1551424323), e.time());
        EXPECT_EQ(LogEntry::Class::alert, e.log_class());
        EXPECT_EQ(LogEntryKind::flapping_host, e.kind());
        EXPECT_EQ(line, e.message());
        EXPECT_EQ("huey;" + state_type + ";foo bar", e.options());
        EXPECT_EQ("HOST FLAPPING ALERT"s, e.type());
        EXPECT_EQ("huey", e.host_name());
        EXPECT_EQ("", e.service_description());
        EXPECT_EQ("", e.command_name());
        EXPECT_EQ("", e.contact_name());
        EXPECT_EQ(static_cast<int>(HostState::up), e.state());
        EXPECT_EQ(state_type, e.state_type());
        EXPECT_EQ(0, e.attempt());
        EXPECT_EQ("", e.plugin_output());
        EXPECT_EQ("", e.long_plugin_output());
        EXPECT_EQ("foo bar", e.comment());
        EXPECT_EQ(state_type, e.state_info());
    }
}

TEST(LogEntry, InitialServiceState) {
    // The service state string is directly taken from a log line field.
    for (const auto &[state_name, state] : service_states) {
        for (const auto &state_type : host_service_state_types) {
            auto line = "[1551424325] INITIAL SERVICE STATE: louie;servus 1;"s
                            .append(state_name)
                            .append(";")
                            .append(state_type)
                            .append(";1;Langweiliger Output;long");
            LogEntry e{1234567, line};
            EXPECT_EQ(size_t{1234567}, e.lineno());
            EXPECT_EQ(tp(1551424325), e.time());
            EXPECT_EQ(LogEntry::Class::state, e.log_class());
            EXPECT_EQ(LogEntryKind::state_service_initial, e.kind());
            EXPECT_EQ(line, e.message());
            EXPECT_EQ("louie;servus 1;"s.append(state_name)
                          .append(";")
                          .append(state_type)
                          .append(";1;Langweiliger Output;long"),
                      e.options());
            EXPECT_EQ("INITIAL SERVICE STATE"s, e.type());
            EXPECT_EQ("louie", e.host_name());
            EXPECT_EQ("servus 1", e.service_description());
            EXPECT_EQ("", e.command_name());
            EXPECT_EQ("", e.contact_name());
            EXPECT_EQ(static_cast<int>(state), e.state());
            EXPECT_EQ(state_type, e.state_type());
            EXPECT_EQ(1, e.attempt());
            EXPECT_EQ("Langweiliger Output", e.plugin_output());
            EXPECT_EQ("long", e.long_plugin_output());
            EXPECT_EQ("", e.comment());
            EXPECT_EQ(parens(state_type, state_name), e.state_info());
        }
    }
}

TEST(LogEntry, CurrentServiceState) {
    // The service state string is directly taken from a log line field.
    for (const auto &[state_name, state] : service_states) {
        for (const auto &state_type : host_service_state_types) {
            auto line = "[1551424335] CURRENT SERVICE STATE: donald;gruezi 2;"s
                            .append(state_name)
                            .append(";")
                            .append(state_type)
                            .append(";2;Irgendein Output;lang");
            LogEntry e{1234567, line};
            EXPECT_EQ(size_t{1234567}, e.lineno());
            EXPECT_EQ(tp(1551424335), e.time());
            EXPECT_EQ(LogEntry::Class::state, e.log_class());
            EXPECT_EQ(LogEntryKind::state_service, e.kind());
            EXPECT_EQ(line, e.message());
            EXPECT_EQ("donald;gruezi 2;"s.append(state_name)
                          .append(";")
                          .append(state_type)
                          .append(";2;Irgendein Output;lang"),
                      e.options());
            EXPECT_EQ("CURRENT SERVICE STATE"s, e.type());
            EXPECT_EQ("donald", e.host_name());
            EXPECT_EQ("gruezi 2", e.service_description());
            EXPECT_EQ("", e.command_name());
            EXPECT_EQ("", e.contact_name());
            EXPECT_EQ(static_cast<int>(state), e.state());
            EXPECT_EQ(state_type, e.state_type());
            EXPECT_EQ(2, e.attempt());
            EXPECT_EQ("Irgendein Output", e.plugin_output());
            EXPECT_EQ("lang", e.long_plugin_output());
            EXPECT_EQ("", e.comment());
            EXPECT_EQ(parens(state_type, state_name), e.state_info());
        }
    }
}

TEST(LogEntry, ServiceAlert) {
    // The service state string is directly taken from a log line field.
    for (const auto &[state_name, state] : service_states) {
        for (const auto &state_type : host_service_state_types) {
            auto line =
                "[1551424323] SERVICE ALERT: huey;hi!;"s.append(state_name)
                    .append(";")
                    .append(state_type)
                    .append(+";1234;Komisch...;lang");
            LogEntry e{123456, line};
            EXPECT_EQ(size_t{123456}, e.lineno());
            EXPECT_EQ(tp(1551424323), e.time());
            EXPECT_EQ(LogEntry::Class::alert, e.log_class());
            EXPECT_EQ(LogEntryKind::alert_service, e.kind());
            EXPECT_EQ(line, e.message());
            EXPECT_EQ("huey;hi!;"s.append(state_name)
                          .append(";")
                          .append(state_type)
                          .append(";1234;Komisch...;lang"),
                      e.options());
            EXPECT_EQ("SERVICE ALERT"s, e.type());
            EXPECT_EQ("huey", e.host_name());
            EXPECT_EQ("hi!", e.service_description());
            EXPECT_EQ("", e.command_name());
            EXPECT_EQ("", e.contact_name());
            EXPECT_EQ(static_cast<int>(state), e.state());
            EXPECT_EQ(state_type, e.state_type());
            EXPECT_EQ(1234, e.attempt());
            EXPECT_EQ("Komisch...", e.plugin_output());
            EXPECT_EQ("lang", e.long_plugin_output());
            EXPECT_EQ("", e.comment());
            EXPECT_EQ(parens(state_type, state_name), e.state_info());
        }
    }
}

TEST(LogEntry, ServiceDowntimeAlert) {
    for (const auto &state_type : downtime_flapping_state_types) {
        auto line = "[1551424323] SERVICE DOWNTIME ALERT: huey;hi, ho!;" +
                    state_type + ";Komisch...";
        LogEntry e{123456, line};
        EXPECT_EQ(size_t{123456}, e.lineno());
        EXPECT_EQ(tp(1551424323), e.time());
        EXPECT_EQ(LogEntry::Class::alert, e.log_class());
        EXPECT_EQ(LogEntryKind::downtime_alert_service, e.kind());
        EXPECT_EQ(line, e.message());
        EXPECT_EQ("huey;hi, ho!;" + state_type + ";Komisch...", e.options());
        EXPECT_EQ("SERVICE DOWNTIME ALERT"s, e.type());
        EXPECT_EQ("huey", e.host_name());
        EXPECT_EQ("hi, ho!", e.service_description());
        EXPECT_EQ("", e.command_name());
        EXPECT_EQ("", e.contact_name());
        EXPECT_EQ(static_cast<int>(ServiceState::ok), e.state());
        EXPECT_EQ(state_type, e.state_type());
        EXPECT_EQ(0, e.attempt());
        EXPECT_EQ("", e.plugin_output());
        EXPECT_EQ("", e.long_plugin_output());
        EXPECT_EQ("Komisch...", e.comment());
        EXPECT_EQ(state_type, e.state_info());
    }
}

TEST(LogEntry, ServiceAcknowledgeAlert) {
    for (const auto &state_type : acknowledge_state_types) {
        auto line = "[1551424323] SERVICE ACKNOWLEDGE ALERT: huey;hi!;" +
                    state_type + ";King Kong;foo bar";
        LogEntry e{123456, line};
        EXPECT_EQ(size_t{123456}, e.lineno());
        EXPECT_EQ(tp(1551424323), e.time());
        EXPECT_EQ(LogEntry::Class::alert, e.log_class());
        EXPECT_EQ(LogEntryKind::acknowledge_alert_service, e.kind());
        EXPECT_EQ(line, e.message());
        EXPECT_EQ("huey;hi!;" + state_type + ";King Kong;foo bar", e.options());
        EXPECT_EQ("SERVICE ACKNOWLEDGE ALERT"s, e.type());
        EXPECT_EQ("huey", e.host_name());
        EXPECT_EQ("hi!", e.service_description());
        EXPECT_EQ("", e.command_name());
        EXPECT_EQ("King Kong", e.contact_name());
        EXPECT_EQ(static_cast<int>(ServiceState::ok), e.state());
        EXPECT_EQ(state_type, e.state_type());
        EXPECT_EQ(0, e.attempt());
        EXPECT_EQ("", e.plugin_output());
        EXPECT_EQ("", e.long_plugin_output());
        EXPECT_EQ("foo bar", e.comment());
        EXPECT_EQ(state_type, e.state_info());
    }
}

TEST(LogEntry, ServiceFlappingAlert) {
    for (const auto &state_type : downtime_flapping_state_types) {
        auto line = "[1551424323] SERVICE FLAPPING ALERT: huey;hi!;" +
                    state_type + ";foo bar";
        LogEntry e{123456, line};
        EXPECT_EQ(size_t{123456}, e.lineno());
        EXPECT_EQ(tp(1551424323), e.time());
        EXPECT_EQ(LogEntry::Class::alert, e.log_class());
        EXPECT_EQ(LogEntryKind::flapping_service, e.kind());
        EXPECT_EQ(line, e.message());
        EXPECT_EQ("huey;hi!;" + state_type + ";foo bar", e.options());
        EXPECT_EQ("SERVICE FLAPPING ALERT"s, e.type());
        EXPECT_EQ("huey", e.host_name());
        EXPECT_EQ("hi!", e.service_description());
        EXPECT_EQ("", e.command_name());
        EXPECT_EQ("", e.contact_name());
        EXPECT_EQ(static_cast<int>(ServiceState::ok), e.state());
        EXPECT_EQ(state_type, e.state_type());
        EXPECT_EQ(0, e.attempt());
        EXPECT_EQ("", e.plugin_output());
        EXPECT_EQ("", e.long_plugin_output());
        EXPECT_EQ("foo bar", e.comment());
        EXPECT_EQ(state_type, e.state_info());
    }
}

TEST(LogEntry, TimeperiodTransition) {
    auto line = "[1551424323] TIMEPERIOD TRANSITION: denominazione;-1;1"s;
    LogEntry e{123456, line};
    EXPECT_EQ(size_t{123456}, e.lineno());
    EXPECT_EQ(tp(1551424323), e.time());
    EXPECT_EQ(LogEntry::Class::state, e.log_class());
    EXPECT_EQ(LogEntryKind::timeperiod_transition, e.kind());
    EXPECT_EQ(line, e.message());
    EXPECT_EQ("denominazione;-1;1"s, e.options());
    EXPECT_EQ("TIMEPERIOD TRANSITION"s, e.type());
    EXPECT_EQ("", e.host_name());
    EXPECT_EQ("", e.service_description());
    EXPECT_EQ("", e.command_name());
    EXPECT_EQ("", e.contact_name());
    EXPECT_EQ(0, e.state());
    EXPECT_EQ("", e.state_type());
    EXPECT_EQ(0, e.attempt());
    EXPECT_EQ("", e.plugin_output());
    EXPECT_EQ("", e.long_plugin_output());
    EXPECT_EQ("", e.comment());
    EXPECT_EQ("", e.state_info());
}

TEST(LogEntry, HostNotification) {
    for (const auto &[state_name, state, info] :
         notification_state_types(host_states)) {
        auto line = "[1551424305] HOST NOTIFICATION: King Kong;donald;"s +
                    state_name +
                    ";commando;viel output...;Tolkien;The Hobbit;lalala"s;
        LogEntry e{42, line};
        EXPECT_EQ(size_t{42}, e.lineno());
        EXPECT_EQ(tp(1551424305), e.time());
        EXPECT_EQ(LogEntry::Class::hs_notification, e.log_class());
        EXPECT_EQ(LogEntryKind::none, e.kind());
        EXPECT_EQ(line, e.message());
        EXPECT_EQ("King Kong;donald;"s + state_name +
                      ";commando;viel output...;Tolkien;The Hobbit;lalala"s,
                  e.options());
        EXPECT_EQ("HOST NOTIFICATION"s, e.type());
        EXPECT_EQ("donald", e.host_name());
        EXPECT_EQ("", e.service_description());
        EXPECT_EQ("commando", e.command_name());
        EXPECT_EQ("King Kong", e.contact_name());
        EXPECT_EQ(state, e.state());
        EXPECT_EQ(state_name, e.state_type());
        EXPECT_EQ(0, e.attempt());
        EXPECT_EQ("viel output...", e.plugin_output());
        EXPECT_EQ("lalala", e.long_plugin_output());
        EXPECT_EQ("The Hobbit", e.comment());
        EXPECT_EQ(info, e.state_info());
    }
}

TEST(LogEntry, ServiceNotification) {
    for (const auto &[state_name, state, info] :
         notification_state_types(service_states)) {
        auto line =
            "[1551424305] SERVICE NOTIFICATION: King Kong;donald;duck;"s +
            state_name + ";commando;viel output...;Tolkien;The Hobbit;lalala"s;
        LogEntry e{42, line};
        EXPECT_EQ(size_t{42}, e.lineno());
        EXPECT_EQ(tp(1551424305), e.time());
        EXPECT_EQ(LogEntry::Class::hs_notification, e.log_class());
        EXPECT_EQ(LogEntryKind::none, e.kind());
        EXPECT_EQ(line, e.message());
        EXPECT_EQ("King Kong;donald;duck;"s + state_name +
                      ";commando;viel output...;Tolkien;The Hobbit;lalala"s,
                  e.options());
        EXPECT_EQ("SERVICE NOTIFICATION"s, e.type());
        EXPECT_EQ("donald", e.host_name());
        EXPECT_EQ("duck", e.service_description());
        EXPECT_EQ("commando", e.command_name());
        EXPECT_EQ("King Kong", e.contact_name());
        EXPECT_EQ(state, e.state());
        EXPECT_EQ(state_name, e.state_type());
        EXPECT_EQ(0, e.attempt());
        EXPECT_EQ("viel output...", e.plugin_output());
        EXPECT_EQ("lalala", e.long_plugin_output());
        EXPECT_EQ("The Hobbit", e.comment());
        EXPECT_EQ(info, e.state_info());
    }
}

TEST(LogEntry, HostNotificationResult) {
    // The exit code string is directly taken from a log line field, where it is
    // encoded as a service result (HACK).
    for (const auto &[code_name, code, info] : exit_codes) {
        auto line = "[1551424305] HOST NOTIFICATION RESULT: King Kong;donald;" +
                    code_name + ";commando;viel output...;blah blubb";
        LogEntry e{42, line};
        EXPECT_EQ(size_t{42}, e.lineno());
        EXPECT_EQ(tp(1551424305), e.time());
        EXPECT_EQ(LogEntry::Class::hs_notification, e.log_class());
        EXPECT_EQ(LogEntryKind::none, e.kind());
        EXPECT_EQ(line, e.message());
        EXPECT_EQ("King Kong;donald;" + code_name +
                      ";commando;viel output...;blah blubb",
                  e.options());
        EXPECT_EQ("HOST NOTIFICATION RESULT"s, e.type());
        EXPECT_EQ("donald", e.host_name());
        EXPECT_EQ("", e.service_description());
        EXPECT_EQ("commando", e.command_name());
        EXPECT_EQ("King Kong", e.contact_name());
        EXPECT_EQ(code, e.state());
        EXPECT_EQ(code_name, e.state_type());
        EXPECT_EQ(0, e.attempt());
        EXPECT_EQ("viel output...", e.plugin_output());
        EXPECT_EQ("", e.long_plugin_output());
        EXPECT_EQ("blah blubb", e.comment());
        EXPECT_EQ(parens("EXIT_CODE", info), e.state_info());
    }
}

TEST(LogEntry, ServiceNotificationResult) {
    // The exit code string is directly taken from a log line field, where it is
    // encoded as a service result (HACK).
    for (const auto &[code_name, code, info] : exit_codes) {
        auto line =
            "[1551424305] SERVICE NOTIFICATION RESULT: King Kong;donald;duck;" +
            code_name + ";commando;viel output...;blah blubb";
        LogEntry e{42, line};
        EXPECT_EQ(size_t{42}, e.lineno());
        EXPECT_EQ(tp(1551424305), e.time());
        EXPECT_EQ(LogEntry::Class::hs_notification, e.log_class());
        EXPECT_EQ(LogEntryKind::none, e.kind());
        EXPECT_EQ(line, e.message());
        EXPECT_EQ("King Kong;donald;duck;" + code_name +
                      ";commando;viel output...;blah blubb",
                  e.options());
        EXPECT_EQ("SERVICE NOTIFICATION RESULT"s, e.type());
        EXPECT_EQ("donald", e.host_name());
        EXPECT_EQ("duck", e.service_description());
        EXPECT_EQ("commando", e.command_name());
        EXPECT_EQ("King Kong", e.contact_name());
        EXPECT_EQ(code, e.state());
        EXPECT_EQ(code_name, e.state_type());
        EXPECT_EQ(0, e.attempt());
        EXPECT_EQ("viel output...", e.plugin_output());
        EXPECT_EQ("", e.long_plugin_output());
        EXPECT_EQ("blah blubb", e.comment());
        EXPECT_EQ(parens("EXIT_CODE", info), e.state_info());
    }
}

TEST(LogEntry, HostNotificationProgress) {
    // The exit code string is directly taken from a log line field, where it is
    // encoded as a service result (HACK).
    for (const auto &[code_name, code, info] : exit_codes) {
        auto line =
            "[1551424305] HOST NOTIFICATION PROGRESS: King Kong;donald;" +
            code_name + ";commando;viel output...";
        LogEntry e{42, line};
        EXPECT_EQ(size_t{42}, e.lineno());
        EXPECT_EQ(tp(1551424305), e.time());
        EXPECT_EQ(LogEntry::Class::hs_notification, e.log_class());
        EXPECT_EQ(LogEntryKind::none, e.kind());
        EXPECT_EQ(line, e.message());
        EXPECT_EQ("King Kong;donald;" + code_name + ";commando;viel output...",
                  e.options());
        EXPECT_EQ("HOST NOTIFICATION PROGRESS"s, e.type());
        EXPECT_EQ("donald", e.host_name());
        EXPECT_EQ("", e.service_description());
        EXPECT_EQ("commando", e.command_name());
        EXPECT_EQ("King Kong", e.contact_name());
        EXPECT_EQ(code, e.state());
        EXPECT_EQ(code_name, e.state_type());
        EXPECT_EQ(0, e.attempt());
        EXPECT_EQ("viel output...", e.plugin_output());
        EXPECT_EQ("", e.long_plugin_output());
        EXPECT_EQ("", e.comment());
        EXPECT_EQ(parens("EXIT_CODE", info), e.state_info());
    }
}

TEST(LogEntry, ServiceNotificationProgress) {
    // The exit code string is directly taken from a log line field, where it is
    // encoded as a service result (HACK).
    for (const auto &[code_name, code, info] : exit_codes) {
        auto line =
            "[1551424305] SERVICE NOTIFICATION PROGRESS: King Kong;donald;duck;" +
            code_name + ";commando;viel output...";
        LogEntry e{42, line};
        EXPECT_EQ(size_t{42}, e.lineno());
        EXPECT_EQ(tp(1551424305), e.time());
        EXPECT_EQ(LogEntry::Class::hs_notification, e.log_class());
        EXPECT_EQ(LogEntryKind::none, e.kind());
        EXPECT_EQ(line, e.message());
        EXPECT_EQ(
            "King Kong;donald;duck;" + code_name + ";commando;viel output...",
            e.options());
        EXPECT_EQ("SERVICE NOTIFICATION PROGRESS"s, e.type());
        EXPECT_EQ("donald", e.host_name());
        EXPECT_EQ("duck", e.service_description());
        EXPECT_EQ("commando", e.command_name());
        EXPECT_EQ("King Kong", e.contact_name());
        EXPECT_EQ(code, e.state());
        EXPECT_EQ(code_name, e.state_type());
        EXPECT_EQ(0, e.attempt());
        EXPECT_EQ("viel output...", e.plugin_output());
        EXPECT_EQ("", e.long_plugin_output());
        EXPECT_EQ("", e.comment());
        EXPECT_EQ(parens("EXIT_CODE", info), e.state_info());
    }
}

TEST(LogEntry, HostAlertHandlerStarted) {
    auto line = "[1551424305] HOST ALERT HANDLER STARTED: donald;commando"s;
    LogEntry e{42, line};
    EXPECT_EQ(size_t{42}, e.lineno());
    EXPECT_EQ(tp(1551424305), e.time());
    EXPECT_EQ(LogEntry::Class::alert_handlers, e.log_class());
    EXPECT_EQ(LogEntryKind::none, e.kind());
    EXPECT_EQ(line, e.message());
    EXPECT_EQ("donald;commando"s, e.options());
    EXPECT_EQ("HOST ALERT HANDLER STARTED"s, e.type());
    EXPECT_EQ("donald", e.host_name());
    EXPECT_EQ("", e.service_description());
    EXPECT_EQ("commando", e.command_name());
    EXPECT_EQ("", e.contact_name());
    EXPECT_EQ(static_cast<int>(HostState::up), e.state());
    EXPECT_EQ("", e.state_type());
    EXPECT_EQ(0, e.attempt());
    EXPECT_EQ("", e.plugin_output());
    EXPECT_EQ("", e.comment());
    EXPECT_EQ("", e.state_info());
}

TEST(LogEntry, ServiceAlertHandlerStarted) {
    auto line =
        "[1551424305] SERVICE ALERT HANDLER STARTED: donald;duck;commando"s;
    LogEntry e{42, line};
    EXPECT_EQ(size_t{42}, e.lineno());
    EXPECT_EQ(tp(1551424305), e.time());
    EXPECT_EQ(LogEntry::Class::alert_handlers, e.log_class());
    EXPECT_EQ(LogEntryKind::none, e.kind());
    EXPECT_EQ(line, e.message());
    EXPECT_EQ("donald;duck;commando"s, e.options());
    EXPECT_EQ("SERVICE ALERT HANDLER STARTED"s, e.type());
    EXPECT_EQ("donald", e.host_name());
    EXPECT_EQ("duck", e.service_description());
    EXPECT_EQ("commando", e.command_name());
    EXPECT_EQ("", e.contact_name());
    EXPECT_EQ(static_cast<int>(ServiceState::ok), e.state());
    EXPECT_EQ("", e.state_type());
    EXPECT_EQ(0, e.attempt());
    EXPECT_EQ("", e.plugin_output());
    EXPECT_EQ("", e.comment());
    EXPECT_EQ("", e.state_info());
}

TEST(LogEntry, HostAlertHandlerStopped) {
    // The exit code string is directly taken from a log line field, where it is
    // encoded as a service result (HACK).
    for (const auto &[code_name, code, info] : exit_codes) {
        auto line =
            "[1551424305] HOST ALERT HANDLER STOPPED: donald;commando;"s +
            code_name + ";es war einmal...";
        LogEntry e{42, line};
        EXPECT_EQ(size_t{42}, e.lineno());
        EXPECT_EQ(tp(1551424305), e.time());
        EXPECT_EQ(LogEntry::Class::alert_handlers, e.log_class());
        EXPECT_EQ(LogEntryKind::none, e.kind());
        EXPECT_EQ(line, e.message());
        EXPECT_EQ("donald;commando;"s + code_name + ";es war einmal...",
                  e.options());
        EXPECT_EQ("HOST ALERT HANDLER STOPPED"s, e.type());
        EXPECT_EQ("donald", e.host_name());
        EXPECT_EQ("", e.service_description());
        EXPECT_EQ("commando", e.command_name());
        EXPECT_EQ("", e.contact_name());
        EXPECT_EQ(code, e.state());
        EXPECT_EQ("", e.state_type());
        EXPECT_EQ(0, e.attempt());
        EXPECT_EQ("es war einmal...", e.plugin_output());
        EXPECT_EQ("", e.long_plugin_output());
        EXPECT_EQ("", e.comment());
        EXPECT_EQ(parens("EXIT_CODE", info), e.state_info());
    }
}

TEST(LogEntry, ServiceAlertHandlerStopped) {
    // The exit code string is directly taken from a log line field, where it is
    // encoded as a service result (HACK).
    for (const auto &[code_name, code, info] : exit_codes) {
        auto line =
            "[1551424305] SERVICE ALERT HANDLER STOPPED: donald;duck;commando;"s +
            code_name + ";once upon a time...";
        LogEntry e{42, line};
        EXPECT_EQ(size_t{42}, e.lineno());
        EXPECT_EQ(tp(1551424305), e.time());
        EXPECT_EQ(LogEntry::Class::alert_handlers, e.log_class());
        EXPECT_EQ(LogEntryKind::none, e.kind());
        EXPECT_EQ(line, e.message());
        EXPECT_EQ("donald;duck;commando;"s + code_name + ";once upon a time...",
                  e.options());
        EXPECT_EQ("SERVICE ALERT HANDLER STOPPED"s, e.type());
        EXPECT_EQ("donald", e.host_name());
        EXPECT_EQ("duck", e.service_description());
        EXPECT_EQ("commando", e.command_name());
        EXPECT_EQ("", e.contact_name());
        EXPECT_EQ(code, e.state());
        EXPECT_EQ("", e.state_type());
        EXPECT_EQ(0, e.attempt());
        EXPECT_EQ("once upon a time...", e.plugin_output());
        EXPECT_EQ("", e.long_plugin_output());
        EXPECT_EQ("", e.comment());
        EXPECT_EQ(parens("EXIT_CODE", info), e.state_info());
    }
}

TEST(LogEntry, PassiveServiceCheck) {
    // The service state integer is directly taken from a log line field.
    for (const auto &[state_name, state] : service_states) {
        auto line = "[1551424305] PASSIVE SERVICE CHECK: donald;duck;" +
                    std::to_string(static_cast<int>(state)) +
                    ";Isch hab Ruecken!";
        LogEntry e{42, line};
        EXPECT_EQ(size_t{42}, e.lineno());
        EXPECT_EQ(tp(1551424305), e.time());
        EXPECT_EQ(LogEntry::Class::passivecheck, e.log_class());
        EXPECT_EQ(LogEntryKind::none, e.kind());
        EXPECT_EQ(line, e.message());
        EXPECT_EQ("donald;duck;"s + std::to_string(static_cast<int>(state)) +
                      ";Isch hab Ruecken!",
                  e.options());
        EXPECT_EQ("PASSIVE SERVICE CHECK"s, e.type());
        EXPECT_EQ("donald", e.host_name());
        EXPECT_EQ("duck", e.service_description());
        EXPECT_EQ("", e.command_name());
        EXPECT_EQ("", e.contact_name());
        EXPECT_EQ(static_cast<int>(state), e.state());
        EXPECT_EQ("", e.state_type());
        EXPECT_EQ(0, e.attempt());
        EXPECT_EQ("Isch hab Ruecken!", e.plugin_output());
        EXPECT_EQ("", e.comment());
        EXPECT_EQ(parens("PASSIVE", state_name), e.state_info());
    }
}

TEST(LogEntry, PassiveHostCheck) {
    // The host state integer is directly taken from a log line field.
    for (const auto &[state_name, state] : host_states) {
        auto line = "[1551424305] PASSIVE HOST CHECK: donald;" +
                    std::to_string(static_cast<int>(state)) +
                    ";Isch hab Ruecken!";
        LogEntry e{42, line};
        EXPECT_EQ(size_t{42}, e.lineno());
        EXPECT_EQ(tp(1551424305), e.time());
        EXPECT_EQ(LogEntry::Class::passivecheck, e.log_class());
        EXPECT_EQ(LogEntryKind::none, e.kind());
        EXPECT_EQ(line, e.message());
        EXPECT_EQ("donald;" + std::to_string(static_cast<int>(state)) +
                      ";Isch hab Ruecken!",
                  e.options());
        EXPECT_EQ("PASSIVE HOST CHECK"s, e.type());
        EXPECT_EQ("donald", e.host_name());
        EXPECT_EQ("", e.service_description());
        EXPECT_EQ("", e.command_name());
        EXPECT_EQ("", e.contact_name());
        EXPECT_EQ(static_cast<int>(state), e.state());
        EXPECT_EQ("", e.state_type());
        EXPECT_EQ(0, e.attempt());
        EXPECT_EQ("Isch hab Ruecken!", e.plugin_output());
        EXPECT_EQ("", e.comment());
        EXPECT_EQ(parens("PASSIVE", state_name), e.state_info());
    }
}

TEST(LogEntry, ExternalCommand) {
    auto line = "[1551424305] EXTERNAL COMMAND: commando"s;
    LogEntry e{42, line};
    EXPECT_EQ(size_t{42}, e.lineno());
    EXPECT_EQ(tp(1551424305), e.time());
    EXPECT_EQ(LogEntry::Class::ext_command, e.log_class());
    EXPECT_EQ(LogEntryKind::none, e.kind());
    EXPECT_EQ(line, e.message());
    EXPECT_EQ("commando"s, e.options());
    EXPECT_EQ("EXTERNAL COMMAND"s, e.type());
    EXPECT_EQ("", e.host_name());
    EXPECT_EQ("", e.service_description());
    EXPECT_EQ("", e.command_name());
    EXPECT_EQ("", e.contact_name());
    EXPECT_EQ(0, e.state());
    EXPECT_EQ("", e.state_type());
    EXPECT_EQ(0, e.attempt());
    EXPECT_EQ("", e.plugin_output());
    EXPECT_EQ("", e.comment());
    EXPECT_EQ("", e.state_info());
}

TEST(LogEntry, LogVersion) {
    auto line = "[1551424305] LOG VERSION: 2.0"s;
    LogEntry e{42, line};
    EXPECT_EQ(size_t{42}, e.lineno());
    EXPECT_EQ(tp(1551424305), e.time());
    EXPECT_EQ(LogEntry::Class::program, e.log_class());
    EXPECT_EQ(LogEntryKind::log_version, e.kind());
    EXPECT_EQ(line, e.message());
    EXPECT_EQ("2.0"s, e.options());
    EXPECT_EQ("LOG VERSION: 2.0"s, e.type());
    EXPECT_EQ("", e.host_name());
    EXPECT_EQ("", e.service_description());
    EXPECT_EQ("", e.command_name());
    EXPECT_EQ("", e.contact_name());
    EXPECT_EQ(0, e.state());
    EXPECT_EQ("", e.state_type());
    EXPECT_EQ(0, e.attempt());
    EXPECT_EQ("", e.plugin_output());
    EXPECT_EQ("", e.comment());
    EXPECT_EQ("", e.state_info());
}

TEST(LogEntry, LogInitialStates) {
    auto line = "[1551424305] logging initial states"s;
    LogEntry e{42, line};
    EXPECT_EQ(size_t{42}, e.lineno());
    EXPECT_EQ(tp(1551424305), e.time());
    EXPECT_EQ(LogEntry::Class::program, e.log_class());
    EXPECT_EQ(LogEntryKind::log_initial_states, e.kind());
    EXPECT_EQ(line, e.message());
    EXPECT_EQ(""s, e.options());
    EXPECT_EQ("logging initial states"s, e.type());
    EXPECT_EQ("", e.host_name());
    EXPECT_EQ("", e.service_description());
    EXPECT_EQ("", e.command_name());
    EXPECT_EQ("", e.contact_name());
    EXPECT_EQ(0, e.state());
    EXPECT_EQ("", e.state_type());
    EXPECT_EQ(0, e.attempt());
    EXPECT_EQ("", e.plugin_output());
    EXPECT_EQ("", e.comment());
    EXPECT_EQ("", e.state_info());
}

TEST(LogEntry, CoreStarting1) {
    auto line = "[1551424305] starting..."s;
    LogEntry e{42, line};
    EXPECT_EQ(size_t{42}, e.lineno());
    EXPECT_EQ(tp(1551424305), e.time());
    EXPECT_EQ(LogEntry::Class::program, e.log_class());
    EXPECT_EQ(LogEntryKind::core_starting, e.kind());
    EXPECT_EQ(line, e.message());
    EXPECT_EQ(""s, e.options());
    EXPECT_EQ("starting..."s, e.type());
    EXPECT_EQ("", e.host_name());
    EXPECT_EQ("", e.service_description());
    EXPECT_EQ("", e.command_name());
    EXPECT_EQ("", e.contact_name());
    EXPECT_EQ(0, e.state());
    EXPECT_EQ("", e.state_type());
    EXPECT_EQ(0, e.attempt());
    EXPECT_EQ("", e.plugin_output());
    EXPECT_EQ("", e.comment());
    EXPECT_EQ("", e.state_info());
}

TEST(LogEntry, CoreStarting2) {
    auto line = "[1551424305] active mode..."s;
    LogEntry e{42, line};
    EXPECT_EQ(size_t{42}, e.lineno());
    EXPECT_EQ(tp(1551424305), e.time());
    EXPECT_EQ(LogEntry::Class::program, e.log_class());
    EXPECT_EQ(LogEntryKind::core_starting, e.kind());
    EXPECT_EQ(line, e.message());
    EXPECT_EQ(""s, e.options());
    EXPECT_EQ("active mode..."s, e.type());
    EXPECT_EQ("", e.host_name());
    EXPECT_EQ("", e.service_description());
    EXPECT_EQ("", e.command_name());
    EXPECT_EQ("", e.contact_name());
    EXPECT_EQ(0, e.state());
    EXPECT_EQ("", e.state_type());
    EXPECT_EQ(0, e.attempt());
    EXPECT_EQ("", e.plugin_output());
    EXPECT_EQ("", e.comment());
    EXPECT_EQ("", e.state_info());
}

TEST(LogEntry, CoreStopping1) {
    auto line = "[1551424305] shutting down..."s;
    LogEntry e{42, line};
    EXPECT_EQ(size_t{42}, e.lineno());
    EXPECT_EQ(tp(1551424305), e.time());
    EXPECT_EQ(LogEntry::Class::program, e.log_class());
    EXPECT_EQ(LogEntryKind::core_stopping, e.kind());
    EXPECT_EQ(line, e.message());
    EXPECT_EQ(""s, e.options());
    EXPECT_EQ("shutting down..."s, e.type());
    EXPECT_EQ("", e.host_name());
    EXPECT_EQ("", e.service_description());
    EXPECT_EQ("", e.command_name());
    EXPECT_EQ("", e.contact_name());
    EXPECT_EQ(0, e.state());
    EXPECT_EQ("", e.state_type());
    EXPECT_EQ(0, e.attempt());
    EXPECT_EQ("", e.plugin_output());
    EXPECT_EQ("", e.comment());
    EXPECT_EQ("", e.state_info());
}

TEST(LogEntry, CoreStopping2) {
    auto line = "[1551424305] Bailing out"s;
    LogEntry e{42, line};
    EXPECT_EQ(size_t{42}, e.lineno());
    EXPECT_EQ(tp(1551424305), e.time());
    EXPECT_EQ(LogEntry::Class::program, e.log_class());
    EXPECT_EQ(LogEntryKind::core_stopping, e.kind());
    EXPECT_EQ(line, e.message());
    EXPECT_EQ(""s, e.options());
    EXPECT_EQ("Bailing out"s, e.type());
    EXPECT_EQ("", e.host_name());
    EXPECT_EQ("", e.service_description());
    EXPECT_EQ("", e.command_name());
    EXPECT_EQ("", e.contact_name());
    EXPECT_EQ(0, e.state());
    EXPECT_EQ("", e.state_type());
    EXPECT_EQ(0, e.attempt());
    EXPECT_EQ("", e.plugin_output());
    EXPECT_EQ("", e.comment());
    EXPECT_EQ("", e.state_info());
}

TEST(LogEntry, CoreStopping3) {
    auto line = "[1551424305] standby mode..."s;
    LogEntry e{42, line};
    EXPECT_EQ(size_t{42}, e.lineno());
    EXPECT_EQ(tp(1551424305), e.time());
    EXPECT_EQ(LogEntry::Class::program, e.log_class());
    EXPECT_EQ(LogEntryKind::core_stopping, e.kind());
    EXPECT_EQ(line, e.message());
    EXPECT_EQ(""s, e.options());
    EXPECT_EQ("standby mode..."s, e.type());
    EXPECT_EQ("", e.host_name());
    EXPECT_EQ("", e.service_description());
    EXPECT_EQ("", e.command_name());
    EXPECT_EQ("", e.contact_name());
    EXPECT_EQ(0, e.state());
    EXPECT_EQ("", e.state_type());
    EXPECT_EQ(0, e.attempt());
    EXPECT_EQ("", e.plugin_output());
    EXPECT_EQ("", e.comment());
    EXPECT_EQ("", e.state_info());
}

TEST(LogEntry, ShortMessage) {
    auto line = "[oh no..."s;
    EXPECT_THROW(LogEntry e(42, line), std::invalid_argument);
}

TEST(LogEntry, InvalidTimeStamp) {
    auto line = "[nonsense!!] this is total;nonsense"s;
    // NOLINTNEXTLINE(hicpp-avoid-goto)
    EXPECT_THROW(LogEntry e(42, line), std::invalid_argument);
}

TEST(LogEntry, NoColon) {
    auto line = "[1551424305] this is total;nonsense"s;
    LogEntry e{42, line};
    EXPECT_EQ(size_t{42}, e.lineno());
    EXPECT_EQ(tp(1551424305), e.time());
    EXPECT_EQ(LogEntry::Class::info, e.log_class());
    EXPECT_EQ(LogEntryKind::none, e.kind());
    EXPECT_EQ(line, e.message());
    EXPECT_EQ(""s, e.options());
    EXPECT_EQ("this is total;nonsense"s, e.type());
    EXPECT_EQ("", e.host_name());
    EXPECT_EQ("", e.service_description());
    EXPECT_EQ("", e.command_name());
    EXPECT_EQ("", e.contact_name());
    EXPECT_EQ(0, e.state());
    EXPECT_EQ("", e.state_type());
    EXPECT_EQ(0, e.attempt());
    EXPECT_EQ("", e.plugin_output());
    EXPECT_EQ("", e.comment());
    EXPECT_EQ("", e.state_info());
}

TEST(LogEntry, HostNotificationSwapped) {
    // Test that we handle buggy legacy log lines where the state_type and the
    // commando "check-mk-notify" are swapped.
    for (const auto &[state_name, state, info] :
         notification_state_types(host_states)) {
        auto line =
            "[1551424305] HOST NOTIFICATION: King Kong;donald;check-mk-notify;"s +
            state_name + ";viel output...;Tolkien;The Hobbit;lalala"s;
        LogEntry e{42, line};
        EXPECT_EQ(size_t{42}, e.lineno());
        EXPECT_EQ(tp(1551424305), e.time());
        EXPECT_EQ(LogEntry::Class::hs_notification, e.log_class());
        EXPECT_EQ(LogEntryKind::none, e.kind());
        EXPECT_EQ(line, e.message());
        EXPECT_EQ("King Kong;donald;check-mk-notify;"s + state_name +
                      ";viel output...;Tolkien;The Hobbit;lalala"s,
                  e.options());
        EXPECT_EQ("HOST NOTIFICATION"s, e.type());
        EXPECT_EQ("donald", e.host_name());
        EXPECT_EQ("", e.service_description());
        EXPECT_EQ("check-mk-notify", e.command_name());
        EXPECT_EQ("King Kong", e.contact_name());
        EXPECT_EQ(state, e.state());
        EXPECT_EQ(state_name, e.state_type());
        EXPECT_EQ(0, e.attempt());
        EXPECT_EQ("viel output...", e.plugin_output());
        EXPECT_EQ("lalala", e.long_plugin_output());
        EXPECT_EQ("The Hobbit", e.comment());
        EXPECT_EQ(info, e.state_info());
    }
}

TEST(LogEntry, ServiceNotificationSwapped) {
    // Test that we handle buggy legacy log lines where the state_type and the
    // commando "check-mk-notify" are swapped.
    for (const auto &[state_name, state, info] :
         notification_state_types(service_states)) {
        auto line =
            "[1551424305] SERVICE NOTIFICATION: King Kong;donald;duck;check-mk-notify;"s +
            state_name + ";viel output...;Tolkien;The Hobbit;lalala"s;
        LogEntry e{42, line};
        EXPECT_EQ(size_t{42}, e.lineno());
        EXPECT_EQ(tp(1551424305), e.time());
        EXPECT_EQ(LogEntry::Class::hs_notification, e.log_class());
        EXPECT_EQ(LogEntryKind::none, e.kind());
        EXPECT_EQ(line, e.message());
        EXPECT_EQ("King Kong;donald;duck;check-mk-notify;"s + state_name +
                      ";viel output...;Tolkien;The Hobbit;lalala"s,
                  e.options());
        EXPECT_EQ("SERVICE NOTIFICATION"s, e.type());
        EXPECT_EQ("donald", e.host_name());
        EXPECT_EQ("duck", e.service_description());
        EXPECT_EQ("check-mk-notify", e.command_name());
        EXPECT_EQ("King Kong", e.contact_name());
        EXPECT_EQ(state, e.state());
        EXPECT_EQ(state_name, e.state_type());
        EXPECT_EQ(0, e.attempt());
        EXPECT_EQ("viel output...", e.plugin_output());
        EXPECT_EQ("lalala", e.long_plugin_output());
        EXPECT_EQ("The Hobbit", e.comment());
        EXPECT_EQ(info, e.state_info());
    }
}

TEST(LogEntry, HostNotificationResultSwapped) {
    // Test that we handle buggy legacy log lines where the state_type and the
    // commando "check-mk-notify" are swapped.
    for (const auto &[code_name, code, info] : exit_codes) {
        auto line =
            "[1551424305] HOST NOTIFICATION RESULT: King Kong;donald;check-mk-notify;" +
            code_name + ";viel output...;blah blubb";
        LogEntry e{42, line};
        EXPECT_EQ(size_t{42}, e.lineno());
        EXPECT_EQ(tp(1551424305), e.time());
        EXPECT_EQ(LogEntry::Class::hs_notification, e.log_class());
        EXPECT_EQ(LogEntryKind::none, e.kind());
        EXPECT_EQ(line, e.message());
        EXPECT_EQ("King Kong;donald;check-mk-notify;" + code_name +
                      ";viel output...;blah blubb",
                  e.options());
        EXPECT_EQ("HOST NOTIFICATION RESULT"s, e.type());
        EXPECT_EQ("donald", e.host_name());
        EXPECT_EQ("", e.service_description());
        EXPECT_EQ("check-mk-notify", e.command_name());
        EXPECT_EQ("King Kong", e.contact_name());
        EXPECT_EQ(code, e.state());
        EXPECT_EQ(code_name, e.state_type());
        EXPECT_EQ(0, e.attempt());
        EXPECT_EQ("viel output...", e.plugin_output());
        EXPECT_EQ("", e.long_plugin_output());
        EXPECT_EQ("blah blubb", e.comment());
        EXPECT_EQ(parens("EXIT_CODE", info), e.state_info());
    }
}

TEST(LogEntry, ServiceNotificationResultSwapped) {
    // Test that we handle buggy legacy log lines where the state_type and the
    // commando "check-mk-notify" are swapped.
    for (const auto &[code_name, code, info] : exit_codes) {
        auto line =
            "[1551424305] SERVICE NOTIFICATION RESULT: King Kong;donald;duck;check-mk-notify;" +
            code_name + ";viel output...;blah blubb";
        LogEntry e{42, line};
        EXPECT_EQ(size_t{42}, e.lineno());
        EXPECT_EQ(tp(1551424305), e.time());
        EXPECT_EQ(LogEntry::Class::hs_notification, e.log_class());
        EXPECT_EQ(LogEntryKind::none, e.kind());
        EXPECT_EQ(line, e.message());
        EXPECT_EQ("King Kong;donald;duck;check-mk-notify;" + code_name +
                      ";viel output...;blah blubb",
                  e.options());
        EXPECT_EQ("SERVICE NOTIFICATION RESULT"s, e.type());
        EXPECT_EQ("donald", e.host_name());
        EXPECT_EQ("duck", e.service_description());
        EXPECT_EQ("check-mk-notify", e.command_name());
        EXPECT_EQ("King Kong", e.contact_name());
        EXPECT_EQ(code, e.state());
        EXPECT_EQ(code_name, e.state_type());
        EXPECT_EQ(0, e.attempt());
        EXPECT_EQ("viel output...", e.plugin_output());
        EXPECT_EQ("", e.long_plugin_output());
        EXPECT_EQ("blah blubb", e.comment());
        EXPECT_EQ(parens("EXIT_CODE", info), e.state_info());
    }
}

TEST(LogEntry, HostNotificationProgressSwapped) {
    // Test that we handle buggy legacy log lines where the state_type and the
    // commando "check-mk-notify" are swapped.
    for (const auto &[code_name, code, info] : exit_codes) {
        auto line =
            "[1551424305] HOST NOTIFICATION PROGRESS: King Kong;donald;check-mk-notify;" +
            code_name + ";viel output...";
        LogEntry e{42, line};
        EXPECT_EQ(size_t{42}, e.lineno());
        EXPECT_EQ(tp(1551424305), e.time());
        EXPECT_EQ(LogEntry::Class::hs_notification, e.log_class());
        EXPECT_EQ(LogEntryKind::none, e.kind());
        EXPECT_EQ(line, e.message());
        EXPECT_EQ(
            "King Kong;donald;check-mk-notify;" + code_name + ";viel output...",
            e.options());
        EXPECT_EQ("HOST NOTIFICATION PROGRESS"s, e.type());
        EXPECT_EQ("donald", e.host_name());
        EXPECT_EQ("", e.service_description());
        EXPECT_EQ("check-mk-notify", e.command_name());
        EXPECT_EQ("King Kong", e.contact_name());
        EXPECT_EQ(code, e.state());
        EXPECT_EQ(code_name, e.state_type());
        EXPECT_EQ(0, e.attempt());
        EXPECT_EQ("viel output...", e.plugin_output());
        EXPECT_EQ("", e.long_plugin_output());
        EXPECT_EQ("", e.comment());
        EXPECT_EQ(parens("EXIT_CODE", info), e.state_info());
    }
}

TEST(LogEntry, ServiceNotificationProgressSwapped) {
    // Test that we handle buggy legacy log lines where the state_type and the
    // commando "check-mk-notify" are swapped.
    for (const auto &[code_name, code, info] : exit_codes) {
        auto line =
            "[1551424305] SERVICE NOTIFICATION PROGRESS: King Kong;donald;duck;check-mk-notify;" +
            code_name + ";viel output...";
        LogEntry e{42, line};
        EXPECT_EQ(size_t{42}, e.lineno());
        EXPECT_EQ(tp(1551424305), e.time());
        EXPECT_EQ(LogEntry::Class::hs_notification, e.log_class());
        EXPECT_EQ(LogEntryKind::none, e.kind());
        EXPECT_EQ(line, e.message());
        EXPECT_EQ("King Kong;donald;duck;check-mk-notify;" + code_name +
                      ";viel output...",
                  e.options());
        EXPECT_EQ("SERVICE NOTIFICATION PROGRESS"s, e.type());
        EXPECT_EQ("donald", e.host_name());
        EXPECT_EQ("duck", e.service_description());
        EXPECT_EQ("check-mk-notify", e.command_name());
        EXPECT_EQ("King Kong", e.contact_name());
        EXPECT_EQ(code, e.state());
        EXPECT_EQ(code_name, e.state_type());
        EXPECT_EQ(0, e.attempt());
        EXPECT_EQ("viel output...", e.plugin_output());
        EXPECT_EQ("", e.long_plugin_output());
        EXPECT_EQ("", e.comment());
        EXPECT_EQ(parens("EXIT_CODE", info), e.state_info());
    }
}
