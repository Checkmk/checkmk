// watest.cpp : This file contains the 'main' function. Program execution begins
// and ends there.

//
#include "pch.h"

#include <processthreadsapi.h>  // for GetCurrentProcess, SetPriorityClass
#include <winbase.h>            // for HIGH_PRIORITY_CLASS

#include "wnx/carrier.h"  // for CarrierDataHeader, CoreCarrier, DataType, DataType::kLog, carrier
#include "common/wtools.h"  // for SecurityLevel, SecurityLevel::admin, SecurityLevel::standard
#include "gtest/gtest.h"  // for InitGoogleTest, RUN_ALL_TESTS
#include "wnx/logger.h"       // for ColoredOutputOnStdio
#include "wnx/on_start.h"     // for OnStart, AppType, AppType::test

using namespace std::chrono_literals;

namespace cma {
AppType AppDefaultType() { return AppType::test; }

}  // namespace cma

int wmain(int argc, wchar_t **argv) {
    using namespace std::literals;
    if (argc == 2 && argv[1] == L"wait"s) {
        cma::tools::sleep(1h);
        return 1;
    }

    std::set_terminate([] {
        //
        XLOG::details::LogWindowsEventCritical(999, "Win Agent is Terminated.");
        XLOG::stdio.crit("Win Agent is Terminated.");
        XLOG::l.bp("WaTest is Terminated.");
        abort();
    });

    XLOG::setup::ColoredOutputOnStdio(true);

    ::SetPriorityClass(GetCurrentProcess(), HIGH_PRIORITY_CLASS);
    if (!cma::OnStartTest()) {
        std::cout << "Fail Create Folders\n";
        return 33;
    }
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
    auto r = RUN_ALL_TESTS();
    if (!r) XLOG::stdio("Win Agent is exited with {}.", r);
    return r;
}
