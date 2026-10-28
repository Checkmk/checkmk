// test-ohm.cpp
// and ends there.
//
#include "pch.h"

#include <chrono>
#include <filesystem>

#include "common/cfg_info.h"
#include "providers/ohm.h"
#include "tools/_misc.h"
#include "tools/_process.h"
#include "watest/test_tools.h"
#include "wnx/cfg.h"
#include "wnx/cma_core.h"
#include "wnx/service_processor.h"

namespace fs = std::filesystem;

namespace {
void CopyOhmToBin() {
    const auto src_dir = fs::path{SOLUTION_DIR} / ".." / ".." / "doc" /
                         "treasures" / "windows" / "ohm";
    for (const auto &name :
         {"OpenHardwareMonitorCLI.exe", "OpenHardwareMonitorLib.dll"}) {
        fs::copy_file(src_dir / name,
                      fs::path{cma::cfg::GetUserBinDir()} / name);
    }
}

std::vector<DWORD> OhmPids() {
    std::vector<DWORD> pids;
    wtools::ScanProcessList([&pids](const PROCESSENTRY32 &entry) {
        if (cma::tools::IsEqual(wtools::ToUtf8(entry.szExeFile),
                                cma::provider::ohm::kExeModule)) {
            pids.push_back(entry.th32ProcessID);
        }
        return wtools::ScanAction::advance;
    });
    return pids;
}

constexpr auto kOhmSettleTimeout = std::chrono::seconds{5};

// OHM's first start after boot is slow: before it registers its WMI
// namespace it reads the SMBIOS tables from root\WMI, and the first query
// there keeps the WMI service busy for 10 to 20 s. Its sensors appear
// about half a minute after the start, later on a loaded machine, hence
// the generous deadline.
constexpr auto kOhmDataTimeout = std::chrono::seconds{120};
constexpr auto kOhmPollInterval = std::chrono::milliseconds{500};

// OHM process starts and kills are asynchronous, so asserting on the
// process count right after either is a race (the lifecycle tests below
// flipped between pass, skip and fail: the old "why doesn't this work on
// CI" TODO). Returns the last count seen, so a failure shows how many OHM
// processes were running.
size_t WaitForOhmCount(size_t expected) {
    size_t count = 0;
    tst::WaitForSuccessSilent(kOhmSettleTimeout, [expected, &count] {
        count = OhmPids().size();
        return count == expected;
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
    // The previous test's OHM may still be dying.
    if (WaitForOhmCount(0) != 0) {
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

TEST(SectionProviderOhm, ReadDataComponent) {
    XLOG::setup::DuplicateOnStdio(true);
    ON_OUT_OF_SCOPE(XLOG::setup::DuplicateOnStdio(false));
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
    int polls = 0;
    const auto start = std::chrono::steady_clock::now();
    while (true) {
        out = ohm.generateContent(section::kUseEmbeddedName, true);
        ++polls;
        if (!out.empty() ||
            std::chrono::steady_clock::now() - start >= kOhmDataTimeout) {
            break;
        }
        XLOG::SendStringToStdio(".", XLOG::Colors::yellow);
        tools::sleep(kOhmPollInterval);
    }
    XLOG::SendStringToStdio("\n", XLOG::Colors::yellow);
    const auto waited = std::chrono::duration_cast<std::chrono::seconds>(
        std::chrono::steady_clock::now() - start);
    ASSERT_FALSE(out.empty()) << "no OHM data after polling for "
                              << waited.count() << " s (" << polls << " polls)";
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

TEST(SectionProviderOhm, ErrorReportingComponentExt) {
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
TEST(SectionProviderOhm, DoubleStartComponentExt) {
    if (SkipTest()) {
        GTEST_SKIP();
    }

    auto temp_fs = tst::TempCfgFs::Create();
    CopyOhmToBin();
    auto ohm_path = provider::GetOhmCliPath();

    auto p = std::make_unique<TheMiniProcess>();
    p->start(ohm_path);
    ASSERT_EQ(WaitForOhmCount(1), 1U);
    // A second start must neither spawn another OHM nor replace the first:
    // CreateProcess returns with the new process already listed.
    const auto pids = OhmPids();
    p->start(ohm_path);
    EXPECT_EQ(OhmPids(), pids);
    p.reset();

    EXPECT_EQ(WaitForOhmCount(0), 0U) << "OHM is not killed";
}

TEST(SectionProviderOhm, StartStopComponentExt) {
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

TEST(SectionProviderOhm, ConditionallyStartOhmComponentExt) {
    if (SkipTest()) {
        GTEST_SKIP();
    }

    auto temp_fs = tst::TempCfgFs::Create();
    CopyOhmToBin();
    ServiceProcessor sp;
    EXPECT_FALSE(sp.stopRunningOhmProcess());
    EXPECT_FALSE(sp.isOhmStarted());
    EXPECT_TRUE(sp.conditionallyStartOhm());
    ASSERT_EQ(WaitForOhmCount(1), 1U);
    const auto pids = OhmPids();
    ASSERT_TRUE(sp.conditionallyStartOhm());
    EXPECT_EQ(OhmPids(), pids);

    ASSERT_TRUE(sp.stopRunningOhmProcess());
    EXPECT_EQ(WaitForOhmCount(0), 0U);
}
}  // namespace cma::srv
