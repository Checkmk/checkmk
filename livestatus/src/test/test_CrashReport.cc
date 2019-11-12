#include <filesystem>
#include <fstream>
#include <optional>
#include <string>
#include "CrashReport.h"
#include "Logger.h"
#include "NagiosCore.h"
#include "TableCrashReports.h"
#include "data_encoding.h"
#include "gtest/gtest.h"

namespace fs = std::filesystem;

class CrashReportFixture : public ::testing::Test {
public:
    const std::string uuid{"8966a88e-e369-11e9-981a-acbc328d0e0b"};
    const std::string component{"gui"};
    const std::string crash_info{"crash.info"};
    const std::string json{"{}\n"};
    const fs::path basepath{fs::temp_directory_path() / "crash_report_tests"};
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

    mk::crash_report::any(basepath, [&result](const CrashReport& cr) {
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
    Logger* const logger{Logger::getLogger("test")};
    EXPECT_TRUE(mk::crash_report::delete_id(basepath, uuid, logger));
    EXPECT_FALSE(fs::exists(fullpath));
}

TEST_F(CrashReportFixture, TestDeleteIdWithNonExistingId) {
    ASSERT_TRUE(fs::exists(fullpath));
    const std::string other{"01234567-0123-4567-89ab-0123456789abc"};
    ASSERT_NE(uuid, other);
    Logger* const logger{Logger::getLogger("test")};
    EXPECT_FALSE(mk::crash_report::delete_id(basepath, other, logger));
    EXPECT_TRUE(fs::exists(fullpath));
}

class CrashReportCoreFixture : public CrashReportFixture {
public:
    CrashReportCoreFixture()
        : core{NagiosCore{paths_(), NagiosLimits{}, NagiosAuthorization{},
                          Encoding::utf8}}
        , table(&core){};

    NagiosCore core;
    TableCrashReports table;

private:
    NagiosPaths paths_() {
        NagiosPaths paths{};
        paths._crash_reports_path = basepath;
        return paths;
    }
};

TEST_F(CrashReportCoreFixture, TestTable) {
    ASSERT_TRUE(fs::exists(basepath));
    ASSERT_EQ(basepath, core.crashReportPath());
    ASSERT_EQ("crashreports", table.name());
    ASSERT_EQ("crashreport_", table.namePrefix());
}
