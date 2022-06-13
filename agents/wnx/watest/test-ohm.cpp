// test-ohm.cpp
// and ends there.
//
#include "pch.h"

#include <filesystem>
#include <string_view>

#include "cfg.h"
#include "cfg_details.h"
#include "cma_core.h"
#include "common/cfg_info.h"
#include "providers/ohm.h"
#include "service_processor.h"
#include "test_tools.h."
#include "tools/_process.h"

namespace fs = std::filesystem;

namespace {
void CopyOhmToBin() {
    const auto src_dir =
        tst::MakePathToTestsFiles(fs::path{SOLUTION_DIR}) / "ohm" / "cli";
    for (const auto &name :
         {"OpenHardwareMonitorCLI.exe", "OpenHardwareMonitorLib.dll"}) {
        fs::copy_file(src_dir / name,
                      fs::path{cma::cfg::GetUserBinDir()} / name);
    }
}

int CalcOhmCount() {
    int count = 0;
    wtools::ScanProcessList([&count](const PROCESSENTRY32 &entry) {
        if (cma::tools::IsEqual(wtools::ToUtf8(entry.szExeFile),
                                cma::provider::ohm::kExeModule)) {
            count++;
        }
        return true;
    });
    return count;
}

bool SkipTest() {
    if (!cma::tools::win::IsElevated()) {
        XLOG::l(XLOG::kStdio).w("Program must be elevated. Test is SKIPPED");
        return true;
    }
    cma::tools::RunCommandAndWait(L"net.exe", L"stop WinRing0_1_2_0");
    wtools::KillProcess(cma::provider::ohm::kExeModuleWide, 1);
    if (CalcOhmCount() != 0) {
        XLOG::l(XLOG::kStdio).w("OHM is already started, TESTING IS SKIPPED");
        return true;
    }

    return false;
}

}  // namespace

namespace cma::provider {

TEST(SectionProviderOhm, Construction) {
    OhmProvider ohm(kOhm, ',');
    EXPECT_EQ(ohm.getUniqName(), cma::section::kOhm);
}

TEST(SectionProviderOhm, ReadDataIntegration) {
    if (SkipTest()) {
        GTEST_SKIP();
    }
    auto temp_fs = tst::TempCfgFs::Create();
    CopyOhmToBin();
    srv::TheMiniProcess oprocess;
    fs::path ohm_exe = GetOhmCliPath();
    ASSERT_TRUE(oprocess.start(ohm_exe.wstring()));
    ::Sleep(1000);
    EXPECT_TRUE(oprocess.running());

    OhmProvider ohm(provider::kOhm, ',');
    std::string out;
    for (auto i = 0; i < 100; ++i) {
        out = ohm.generateContent(section::kUseEmbeddedName, true);
        if (!out.empty()) {
            break;
        }
        XLOG::SendStringToStdio(".", XLOG::Colors::yellow);
        if (i == 50) {
            XLOG::SendStringToStdio(" reset OHM ", XLOG::Colors::red);
            oprocess.stop();
            XLOG::SendStringToStdio(".", XLOG::Colors::red);
            srv::ServiceProcessor::resetOhm();
            XLOG::SendStringToStdio(".", XLOG::Colors::red);
            wtools::KillProcess(L"Openhardwaremonitorcli.exe", 1);
            XLOG::SendStringToStdio(".", XLOG::Colors::red);
            oprocess.start(ohm_exe.wstring());
            XLOG::SendStringToStdio(".", XLOG::Colors::red);
        }
        ::Sleep(200);
    }
    XLOG::SendStringToStdio("\n", XLOG::Colors::yellow);
    ASSERT_TRUE(!out.empty());
    // testing output
    auto table = tools::SplitString(out, "\n");

    // section header:
    EXPECT_TRUE(table.size() > 2);
    EXPECT_EQ(table[0], "<<<openhardwaremonitor:sep(44)>>>");

    // table header:
    auto header = tools::SplitString(table[1], ",");
    ASSERT_EQ(header.size(), 6);
    std::vector<std::string> expected_strings{
        "Index", "Name", "Parent", "SensorType", "Value", "WMIStatus"};
    int index = 0;
    for (const auto &str : expected_strings) {
        EXPECT_EQ(str, header[index++]);
    }

    for (size_t i = 2; i < table.size(); i++) {
        auto f_line = tools::SplitString(table[i], ",");
        EXPECT_EQ(f_line.size(), 6U);
    }

    EXPECT_TRUE(oprocess.stop());
    EXPECT_FALSE(oprocess.running());
}

TEST(SectionProviderOhm, ErrorReportingIntegration) {
    if (SkipTest()) {
        GTEST_SKIP();
    }

    auto temp_fs = tst::TempCfgFs::Create();
    CopyOhmToBin();
    fs::path ohm_exe = GetOhmCliPath();
    OhmProvider ohm(kOhm, ohm::kSepChar);
    auto x = ohm.generateContent("buzz", true);
    EXPECT_TRUE(x.empty());
    EXPECT_EQ(ohm.errorCount(), 1);
}

}  // namespace cma::provider

namespace cma::srv {

TEST(SectionProviderOhm, DoubleStartIntegration) {
    if (SkipTest()) {
        GTEST_SKIP();
    }

    auto temp_fs = tst::TempCfgFs::Create();
    CopyOhmToBin();
    auto ohm_path = provider::GetOhmCliPath();

    auto p = std::make_unique<TheMiniProcess>();
    p->start(ohm_path);
    EXPECT_EQ(CalcOhmCount(), 1);
    p->start(ohm_path);
    EXPECT_EQ(CalcOhmCount(), 1);
    p.reset();

    EXPECT_EQ(CalcOhmCount(), 0) << "OHM is not killed";
}

TEST(SectionProviderOhm, StartStopIntegration) {
    if (SkipTest()) {
        GTEST_SKIP();
    }

    auto temp_fs = tst::TempCfgFs::Create();
    CopyOhmToBin();

    TheMiniProcess oprocess;
    EXPECT_EQ(oprocess.processId(), 0);
    fs::path ohm_exe = provider::GetOhmCliPath();
    ASSERT_TRUE(oprocess.start(ohm_exe.wstring()));
    ::Sleep(500);
    EXPECT_TRUE(oprocess.running());
    EXPECT_TRUE(oprocess.stop());
    EXPECT_FALSE(oprocess.running());
    EXPECT_EQ(oprocess.processId(), 0);
}

TEST(SectionProviderOhm, ConditionallyStartOhmIntegration) {
    XLOG::setup::DuplicateOnStdio(true);
    ON_OUT_OF_SCOPE(XLOG::setup::DuplicateOnStdio(false));
    if (SkipTest()) {
        GTEST_SKIP();
    }

    auto temp_fs = tst::TempCfgFs::Create();
    CopyOhmToBin();
    ServiceProcessor sp;
    wtools::KillProcess(provider::ohm::kExeModuleWide, 1);
    ASSERT_EQ(wtools::FindProcess(provider::ohm::kExeModuleWide), 0);
    EXPECT_FALSE(sp.stopRunningOhmProcess());
    EXPECT_FALSE(sp.isOhmStarted());
    EXPECT_TRUE(sp.conditionallyStartOhm());
    ASSERT_EQ(wtools::FindProcess(provider::ohm::kExeModuleWide), 1);
    EXPECT_TRUE(sp.conditionallyStartOhm());
    ASSERT_EQ(wtools::FindProcess(provider::ohm::kExeModuleWide), 1);

    EXPECT_TRUE(sp.stopRunningOhmProcess());
    ASSERT_EQ(wtools::FindProcess(provider::ohm::kExeModuleWide), 0);
}
}  // namespace cma::srv
