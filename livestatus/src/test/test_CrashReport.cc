#include <filesystem>
#include <fstream>
#include <memory>
#include <sstream>
#include <string>
#include <vector>
#include "CrashReport.h"
#include "gtest/gtest.h"

namespace fs = std::filesystem;

class CrashReportTest : public ::testing::Test {
protected:
    CrashReportTest() = default;

    // Accessors in fixtures make clang tidy happy :-)
    [[nodiscard]] fs::path basepath() const { return basepath_; }
    [[nodiscard]] fs::path uuid() const { return uuid_; }
    [[nodiscard]] fs::path component() const { return component_; }
    [[nodiscard]] fs::path crash_info() const { return crash_info_; }
    [[nodiscard]] fs::path json() const { return json_; }
    [[nodiscard]] fs::path fullpath() const {
        return basepath() / component() / uuid() / crash_info();
    }

    void SetUp() override {
        fs::create_directories(fullpath().parent_path());
        std::ofstream ofs(fullpath());
        ofs << json();
        ofs.close();
    }
    void TearDown() override { fs::remove_all(basepath_); }

private:
    fs::path basepath_ = fs::temp_directory_path() / "crash_report_tests";
    // This could use `mkstemp()` instead of fixed strings.
    const fs::path uuid_{"8966a88e-e369-11e9-981a-acbc328d0e0b"};
    const fs::path component_{"gui"};
    const fs::path crash_info_{"crash.info"};
    const std::string json_{"{}\n"};
};

TEST_F(CrashReportTest, DirectoryAndFileExist) {
    ASSERT_TRUE(fs::exists(fullpath()));
    EXPECT_TRUE(fs::is_regular_file(fullpath()));
}

TEST_F(CrashReportTest, AccessorsAreCorrect) {
    ASSERT_TRUE(fs::exists(fullpath()));
    CrashReport cr{uuid(), component()};
    EXPECT_EQ(uuid(), cr.id());
    EXPECT_EQ(component(), cr.component());
}

TEST_F(CrashReportTest, ForEachCrashReport) {
    ASSERT_TRUE(fs::exists(basepath()));
    std::vector<CrashReport> result{};

    for_each_crash_report(basepath(), [&result](const CrashReport &cr) {
        result.emplace_back(cr);
    });
    ASSERT_EQ(1UL, result.size());
    EXPECT_EQ(uuid(), result[0].id());
    EXPECT_EQ(component(), result[0].component());
}
