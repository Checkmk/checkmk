// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <cstddef>
#include <filesystem>
#include <fstream>
#include <functional>
#include <map>
#include <memory>
#include <sstream>
#include <string>
#include <unordered_set>
#include <utility>
#include <vector>

#include "DummyMonitoringCore.h"
#include "StubObjects.h"
#include "TemporaryDirectory.h"
#include "gtest/gtest.h"
#include "livestatus/ICore.h"
#include "livestatus/Interface.h"
#include "livestatus/LogCache.h"
#include "livestatus/Logger.h"
#include "livestatus/OutputBuffer.h"
#include "livestatus/ParsedQuery.h"
#include "livestatus/Query.h"
#include "livestatus/TableLog.h"
#include "livestatus/User.h"

namespace {
// A core with a history file, some hosts and services, and a single contact as
// AuthUser.
class HistoryCore : public DummyMonitoringCore {
public:
    using Services =
        std::map<std::pair<std::string, std::string>, const IService *>;
    HistoryCore(std::filesystem::path history_file, const IContact &contact,
                ServiceAuthorization service_auth,
                std::map<std::string, const IHost *> hosts, Services services)
        : history_file_{std::move(history_file)}
        , contact_{contact}
        , service_auth_{service_auth}
        , hosts_{std::move(hosts)}
        , services_{std::move(services)} {}
    [[nodiscard]] const IHost *find_host(
        const std::string &name) const override {
        auto it = hosts_.find(name);
        return it == hosts_.end() ? nullptr : it->second;
    }
    [[nodiscard]] const IService *find_service(
        const std::string &host_name,
        const std::string &service_description) const override {
        auto it = services_.find({host_name, service_description});
        return it == services_.end() ? nullptr : it->second;
    }
    [[nodiscard]] std::unique_ptr<const User> find_user(
        const std::string &name) const override {
        if (name != contact_.name()) {
            return std::make_unique<UnknownUser>();
        }
        return std::make_unique<AuthUser>(
            contact_, service_auth_, GroupAuthorization::loose,
            [](const std::string &) { return nullptr; });
    }
    [[nodiscard]] std::unique_ptr<const IPaths> paths() const override {
        return std::make_unique<StubPaths>(
            StubPaths::Values{.history_file = history_file_,
                              .history_archive_directory =
                                  history_file_.parent_path() / "archive"});
    }
    [[nodiscard]] size_t maxLinesPerLogFile() const override { return 1000; }
    [[nodiscard]] size_t maxCachedMessages() const override { return 1000; }
    [[nodiscard]] size_t maxResponseSize() const override { return 100000; }
    [[nodiscard]] Logger *loggerLivestatus() const override {
        return Logger::getLogger("test");
    }

private:
    std::filesystem::path history_file_;
    const IContact &contact_;
    ServiceAuthorization service_auth_;
    std::map<std::string, const IHost *> hosts_;
    Services services_;
};

std::vector<std::string> answerLines(ICore &core,
                                     const std::vector<std::string> &request) {
    LogCache log_cache{&core};
    TableLog table{&core, &log_cache};
    OutputBuffer output{-1, [] { return false; }, core.loggerLivestatus()};
    Query query{ParsedQuery{request, [&table] { return table.allColumns(); },
                            [&table](const auto &colname) {
                                return table.column(colname);
                            }},
                table, core, output};
    query.process();
    EXPECT_EQ("", output.getError());
    std::vector<std::string> lines;
    std::istringstream is{output.str()};
    for (std::string line; std::getline(is, line);) {
        lines.push_back(line);
    }
    return lines;
}
}  // namespace

TEST(TableLogTest, AuthUserSeesOnlyExternalCommandsForItsHosts) {
    const TemporaryDirectory basedir{"table_log_tests"};
    const auto history_file = basedir.path() / "history";
    std::ofstream{history_file}
        << "[1551424305] EXTERNAL COMMAND: ADD_HOST_COMMENT;mine;0;alice;hi\n"
           "[1551424306] EXTERNAL COMMAND: ADD_HOST_COMMENT;other;0;bob;no\n"
           "[1551424307] EXTERNAL COMMAND: "
           "SCHEDULE_HOSTGROUP_HOST_DOWNTIME;linux;1;2;1;0;0;bob;no\n";
    const StubContact alice{"alice"};
    const StubHost mine{{&alice}};
    const StubHost other{{}};
    HistoryCore core{history_file,
                     alice,
                     ServiceAuthorization::loose,
                     {{"mine", &mine}, {"other", &other}},
                     {}};

    const auto lines =
        answerLines(core, {"Columns: options", "AuthUser: alice"});

    EXPECT_EQ(std::vector<std::string>{"ADD_HOST_COMMENT;mine;0;alice;hi"},
              lines);
}

TEST(TableLogTest, StrictAuthUserSeesOnlyExternalCommandsForItsServices) {
    const TemporaryDirectory basedir{"table_log_tests"};
    const auto history_file = basedir.path() / "history";
    std::ofstream{history_file}
        << "[1551424305] EXTERNAL COMMAND: ADD_SVC_COMMENT;web01;mine;0;bob;hi\n"
           "[1551424306] EXTERNAL COMMAND: ADD_SVC_COMMENT;web01;other;0;bob;no\n";
    const StubContact alice{"alice"};
    const StubHost web01{{&alice}};
    const StubService mine{web01, {&alice}};
    const StubService other{web01, {}};
    HistoryCore core{
        history_file,
        alice,
        ServiceAuthorization::strict,
        {{"web01", &web01}},
        {{{"web01", "mine"}, &mine}, {{"web01", "other"}, &other}}};

    const auto lines =
        answerLines(core, {"Columns: options", "AuthUser: alice"});

    EXPECT_EQ(std::vector<std::string>{"ADD_SVC_COMMENT;web01;mine;0;bob;hi"},
              lines);
}

TEST(TableLogTest, AuthUserSeesUnrecognizedNagiosCommandsOnlyForItsHosts) {
    const TemporaryDirectory basedir{"table_log_tests"};
    const auto history_file = basedir.path() / "history";
    std::ofstream{history_file}
        << "[1551424305] Warning: Unrecognized external command -> "
           "PROCESS_HOST_PERFDATA;mine;1551424305;load=1\n"
           "[1551424306] Warning: Unrecognized external command -> "
           "PROCESS_HOST_PERFDATA;other;1551424305;load=2\n"
           "[1551424307] Warning: Unrecognized external command -> "
           "MODIFY_HOST_DOWNTIME;42;1551424305;+3600;0;0;0;bob;no\n";
    const StubContact alice{"alice"};
    const StubHost mine{{&alice}};
    const StubHost other{{}};
    HistoryCore core{history_file,
                     alice,
                     ServiceAuthorization::loose,
                     {{"mine", &mine}, {"other", &other}},
                     {}};

    const auto lines = answerLines(core, {"Columns: type", "AuthUser: alice"});

    EXPECT_EQ(std::vector<std::string>{"Warning: Unrecognized external command "
                                       "-> PROCESS_HOST_PERFDATA;mine;"
                                       "1551424305;load=1"},
              lines);
}
