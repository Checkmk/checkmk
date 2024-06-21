// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <filesystem>
#include <fstream>
#include <functional>
#include <map>
#include <memory>
#include <optional>
#include <random>
#include <string>
#include <vector>

#include "gtest/gtest.h"
#include "livestatus/CrashReport.h"
#include "livestatus/ICore.h"
#include "livestatus/Interface.h"
#include "livestatus/Logger.h"
#include "livestatus/OutputBuffer.h"
#include "livestatus/ParsedQuery.h"
#include "livestatus/Query.h"
#include "livestatus/Table.h"
#include "livestatus/TableCrashReports.h"
#include "livestatus/data_encoding.h"
#include "neb/Comment.h"   // IWYU pragma: keep
#include "neb/Downtime.h"  // IWYU pragma: keep
#include "neb/NebCore.h"

namespace fs = std::filesystem;

namespace {
// https://stackoverflow.com/questions/440133/how-do-i-create-a-random-alpha-numeric-string-in-c
std::string random_string(const std::string::size_type length) {
    static const auto &chrs =
        "0123456789"
        "abcdefghijklmnopqrstuvwxyz"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ";

    thread_local static std::mt19937 rg{std::random_device{}()};
    thread_local static std::uniform_int_distribution<std::string::size_type>
        pick(0, sizeof(chrs) - 2);

    std::string str(length, 0);
    for (auto &c : str) {
        c = chrs[pick(rg)];
    };
    return str;
}
}  // namespace

class CrashReportFixture : public ::testing::Test {
public:
    std::string uuid;
    std::string component;
    std::string crash_info;
    std::string json;
    fs::path basepath;
    fs::path fullpath;

    CrashReportFixture()
        : uuid{"8966a88e-e369-11e9-981a-acbc328d0e0b"}
        , component{"gui"}
        , crash_info{"crash.info"}
        , json{"{}\n"}
        , basepath{fs::temp_directory_path() / "crash_report_tests" /
                   random_string(12)}
        , fullpath{basepath / component / uuid / crash_info} {
        fs::create_directories(fullpath.parent_path());
        std::ofstream ofs(fullpath);
        ofs << json;
        ofs.close();
    }

    ~CrashReportFixture() override { fs::remove_all(basepath); }
};

TEST_F(CrashReportFixture, DirectoryAndFileExist) {
    ASSERT_TRUE(fs::exists(fullpath));
    EXPECT_TRUE(fs::is_regular_file(fullpath));
}

TEST_F(CrashReportFixture, ForEachCrashReport) {
    ASSERT_TRUE(fs::exists(basepath));
    std::optional<CrashReport> result;

    mk::crash_report::any(basepath, [&result](const CrashReport &cr) {
        result = cr;
        return true;
    });
    EXPECT_TRUE(result && uuid == result->id);
    EXPECT_TRUE(result && component == result->component);
}

TEST_F(CrashReportFixture, TestDeleteId) {
    ASSERT_TRUE(fs::exists(fullpath));
    const std::string other{"01234567-0123-4567-89ab-0123456789abc"};
    ASSERT_NE(uuid, other);
    Logger *const logger{Logger::getLogger("test")};
    EXPECT_TRUE(mk::crash_report::delete_id(basepath, uuid, logger));
    EXPECT_FALSE(fs::exists(fullpath));
}

TEST_F(CrashReportFixture, TestDeleteIdWithNonExistingId) {
    ASSERT_TRUE(fs::exists(fullpath));
    const std::string other{"01234567-0123-4567-89ab-0123456789abc"};
    ASSERT_NE(uuid, other);
    Logger *const logger{Logger::getLogger("test")};
    EXPECT_FALSE(mk::crash_report::delete_id(basepath, other, logger));
    EXPECT_TRUE(fs::exists(fullpath));
}

class CrashReportTableFixture : public CrashReportFixture {
    std::map<unsigned long, std::unique_ptr<Downtime>> downtimes_;
    std::map<unsigned long, std::unique_ptr<Comment>> comments_;

public:
    NebCore core{downtimes_,
                 comments_,
                 paths_(),
                 NagiosLimits{},
                 NagiosAuthorization{},
                 Encoding::utf8,
                 "enterprise",
                 {}};
    TableCrashReports table{&core};

private:
    [[nodiscard]] NagiosPathConfig paths_() const {
        NagiosPathConfig p{};
        p.crash_reports_directory = basepath;
        return p;
    }
};

TEST_F(CrashReportTableFixture, TestTable) {
    EXPECT_EQ(basepath, core.paths()->crash_reports_directory());
    EXPECT_EQ("crashreports", table.name());
    EXPECT_EQ("crashreport_", table.namePrefix());
}

namespace {
std::string query(Table &table, ICore &core,
                  const std::vector<std::string> &lines) {
    OutputBuffer output{-1, [] { return false; }, core.loggerLivestatus()};
    Query{ParsedQuery{
              lines, [&table]() { return table.allColumns(); },
              [&table](const auto &colname) { return table.column(colname); }},
          table, core, output}
        .process();
    return output.str();
}
}  // namespace

TEST_F(CrashReportTableFixture, TestListCrashReports) {
    ASSERT_TRUE(fs::exists(basepath));
    EXPECT_EQ("component;id\n" + component + ";" + uuid + "\n",
              query(table, core, {}));
}

TEST_F(CrashReportTableFixture, TestGetOneCrashReport) {
    ASSERT_TRUE(fs::exists(basepath));
    EXPECT_EQ(json + "\n", query(table, core,
                                 {"Columns: file:f0:" + component + "/" + uuid +
                                      "/" + crash_info,
                                  "Filter: id = " + uuid}));
}
