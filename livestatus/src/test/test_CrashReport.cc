// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <filesystem>
#include <fstream>
#include <map>
#include <memory>
#include <optional>
#include <string>

#include "CrashReport.h"
#include "Logger.h"
#include "NagiosCore.h"
#include "TableCrashReports.h"
#include "TableQueryHelper.h"
#include "data_encoding.h"
#include "gtest/gtest.h"
#include "test/Utilities.h"
class Comment;
class Downtime;

namespace fs = std::filesystem;

class CrashReportFixture : public ::testing::Test {
public:
    const std::string uuid{"8966a88e-e369-11e9-981a-acbc328d0e0b"};
    const std::string component{"gui"};
    const std::string crash_info{"crash.info"};
    const std::string json{"{}\n"};
    const fs::path basepath{fs::temp_directory_path() / "crash_report_tests" /
                            random_string(12)};
    const fs::path fullpath{basepath / component / uuid / crash_info};

    void SetUp() override {
        fs::create_directories(fullpath.parent_path());
        std::ofstream ofs(fullpath);
        ofs << json;
        ofs.close();
    }
    void TearDown() override { fs::remove_all(basepath); }
};

TEST_F(CrashReportFixture, DirectoryAndFileExist) {
    ASSERT_TRUE(fs::exists(fullpath));
    EXPECT_TRUE(fs::is_regular_file(fullpath));
}

TEST_F(CrashReportFixture, AccessorsAreCorrect) {
    ASSERT_TRUE(fs::exists(fullpath));
    CrashReport cr{uuid, component};
    EXPECT_EQ(uuid, cr.id());
    EXPECT_EQ(component, cr.component());
}

TEST_F(CrashReportFixture, ForEachCrashReport) {
    ASSERT_TRUE(fs::exists(basepath));
    std::optional<CrashReport> result;

    mk::crash_report::any(basepath, [&result](const CrashReport &cr) {
        result = cr;
        return true;
    });
    ASSERT_NE(std::nullopt, result);
    EXPECT_EQ(uuid, result->id());
    EXPECT_EQ(component, result->component());
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
    NagiosCore core{downtimes_,
                    comments_,
                    paths_(),
                    NagiosLimits{},
                    NagiosAuthorization{},
                    Encoding::utf8};
    TableCrashReports table{&core};
    const std::string header{"component;id\n"};

private:
    [[nodiscard]] NagiosPaths paths_() const {
        NagiosPaths p{};
        p._crash_reports_path = basepath;
        return p;
    }
};

TEST_F(CrashReportTableFixture, TestTable) {
    EXPECT_EQ(basepath, core.crashReportPath());
    EXPECT_EQ("crashreports", table.name());
    EXPECT_EQ("crashreport_", table.namePrefix());
}

TEST_F(CrashReportTableFixture, TestListCrashReports) {
    ASSERT_TRUE(fs::exists(basepath));
    EXPECT_EQ(header + component + ";" + uuid + "\n",
              mk::test::query(table, {}));
}

TEST_F(CrashReportTableFixture, TestGetOneCrashReport) {
    ASSERT_TRUE(fs::exists(basepath));
    EXPECT_EQ(json + "\n",
              mk::test::query(table, {"Columns: file:f0:" + component + "/" +
                                          uuid + "/" + crash_info + "\n",
                                      "Filter: id = " + uuid + "\n"}));
}
