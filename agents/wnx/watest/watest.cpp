// watest.cpp : This file contains the 'main' function. Program execution begins
// and ends there.

//
#include "pch.h"

#include <filesystem>
#include <iostream>

#include "cfg.h"
#include "cfg_details.h"
#include "common/cfg_info.h"
#include "common/mailslot_transport.h"
#include "common/wtools.h"
#include "read_file.h"
#include "tools/_misc.h"
#include "tools/_process.h"
#include "tools/_tgt.h"
#include "yaml-cpp/yaml.h"
namespace cma {
AppType AppDefaultType() { return AppType::test; }

}  // namespace cma

namespace cma::cfg::details {
TEST(StartTest, CheckStatus) {
    OnStart(cma::AppType::test);
    auto& info = details::G_ConfigInfo;
    ASSERT_TRUE(!info.exe_command_paths_.empty());
    ASSERT_TRUE(!info.config_dirs_.empty());
    ASSERT_TRUE(!info.getDataDir().empty());
    ASSERT_TRUE(!info.getRootDir().empty());
    ASSERT_TRUE(info.getConfig().IsMap());
    /*
        ASSERT_TRUE(!info.getRootPath().empty());
        ASSERT_TRUE(!info.getRootPath().empty());
        ASSERT_TRUE(!info.getRootPath().empty());
    */
}
}  // namespace cma::cfg::details

int wmain(int argc, wchar_t** argv) {
    XLOG::setup::ColoredOutputOnStdio(true);
    ::SetPriorityClass(GetCurrentProcess(), HIGH_PRIORITY_CLASS);
    if (!cma::OnStart(cma::AppType::test)) {
        std::cout << "Fail Create Folders\n";
        return 33;
    }
    OnStart(cma::AppType::test);
    ::testing::InitGoogleTest(&argc, argv);
#if defined(_DEBUG)
    //::testing::GTEST_FLAG(filter) = "EventLogTest*";
    //::testing::GTEST_FLAG(filter) = "LogWatchEventTest*";  // CURRENT
    //::testing::GTEST_FLAG(filter) = "WinPerfTest*";
    //::testing::GTEST_FLAG(filter) = "AgentConfig*";
    //::testing::GTEST_FLAG(filter) = "PluginTest*";
    //::testing::GTEST_FLAG(filter) = "ExternalPortTest*";
    //::testing::GTEST_FLAG(filter) = "SectionProviderMrpe*";
    //::testing::GTEST_FLAG(filter) = "SectionProviderOhm*";
    // ::testing::GTEST_FLAG(filter) = "SectionProviderSpool*";
    //::testing::GTEST_FLAG(filter) = "SectionProviderSkype*";
    //::testing::GTEST_FLAG(filter) = "CvtTest*";
    //::testing::GTEST_FLAG(filter) = "ProviderTest*";
    //::testing::GTEST_FLAG(filter) = "ProviderTest.WmiAll*";
    //::testing::GTEST_FLAG(filter) = "SectionProviderSkype*";
    //::testing::GTEST_FLAG(filter) = "Wtools*";
    //::testing::GTEST_FLAG(filter) = "CapTest*";
    // ::testing::GTEST_FLAG(filter) = "UpgradeTest*";
    // ::testing::GTEST_FLAG(filter) = "*Mrpe*";
    //::testing::GTEST_FLAG(filter) = "*OnlyFrom*";
    //::testing::GTEST_FLAG(filter) = "EncryptionT*";
#endif
    return RUN_ALL_TESTS();
}
