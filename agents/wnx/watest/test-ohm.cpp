// test-ohm.cpp
// and ends there.
//
#include "pch.h"

#include <time.h>

#include <chrono>
#include <filesystem>
#include <future>
#include <string_view>

#include "cfg.h"
#include "cfg_details.h"
#include "cma_core.h"
#include "common/cfg_info.h"
#include "providers/ohm.h"
#include "read_file.h"
#include "service_processor.h"

namespace cma::provider {  // to become friendly for wtools classes
TEST(SectionProviderOhm, Construction) {
    OhmProvider ohm(kOhm, ',');
    EXPECT_EQ(ohm.getUniqName(), cma::section::kOhm);
}

TEST(SectionProviderOhm, ReadData) {
    namespace fs = std::filesystem;
    using namespace xlog::internal;
    cma::srv::TheMiniProcess oprocess;

    wtools::KillProcess(L"Openhardwaremonitorcli.exe", 1);

    fs::path ohm_exe = GetOhmCliPath();

    ASSERT_TRUE(cma::tools::IsValidRegularFile(ohm_exe))
        << "not found " << ohm_exe.u8string()
        << " probably directories are not ready to test\n";

    auto ret = oprocess.start(ohm_exe.wstring());
    ASSERT_TRUE(ret);
    ::Sleep(1000);
    EXPECT_TRUE(oprocess.running());

    OhmProvider ohm(provider::kOhm, ',');

    if (cma::tools::win::IsElevated()) {
        std::string out;
        for (auto i = 0; i < 50; ++i) {
            out = ohm.generateContent(section::kUseEmbeddedName, true);
            if (!out.empty()) break;
            XLOG::SendStringToStdio(".", Colors::yellow);
            if (i == 20) {
                XLOG::SendStringToStdio(" reset OHM ", Colors::red);
                oprocess.stop();
                XLOG::SendStringToStdio(".", Colors::red);
                cma::srv::ServiceProcessor::resetOhm();
                XLOG::SendStringToStdio(".", Colors::red);
                wtools::KillProcess(L"Openhardwaremonitorcli.exe", 1);
                XLOG::SendStringToStdio(".", Colors::red);
                oprocess.start(ohm_exe.wstring());
                XLOG::SendStringToStdio(".", Colors::red);
            }
            ::Sleep(500);
        }
        xlog::sendStringToStdio("\n", Colors::yellow);
        EXPECT_TRUE(!out.empty()) << "Probably you have to clean ohm";
        if (!out.empty()) {
            // testing output
            auto table = cma::tools::SplitString(out, "\n");

            // section header:
            EXPECT_TRUE(table.size() > 2);
            EXPECT_EQ(table[0], "<<<openhardwaremonitor:sep(44)>>>");

            // table header:
            auto header = cma::tools::SplitString(table[1], ",");
            EXPECT_EQ(header.size(), 6);
            if (header.size() >= 6) {
                const char *expected_strings[] = {"Index",  "Name",
                                                  "Parent", "SensorType",
                                                  "Value",  "WMIStatus"};
                int index = 0;
                for (auto &str : expected_strings) {
                    EXPECT_EQ(str, header[index++]);
                }
            }

            // table body:
            for (size_t i = 2; i < table.size(); i++) {
                auto f_line = cma::tools::SplitString(table[i], ",");
                EXPECT_EQ(f_line.size(), 6);
            }
        }

    } else {
        XLOG::l(XLOG::kStdio)
            .w("No testing of OpenHardwareMonitor. Program must be elevated");
    }

    ret = oprocess.stop();
    EXPECT_FALSE(oprocess.running());
    EXPECT_TRUE(ret);
}

}  // namespace cma::provider

// START STOP testing
namespace cma::srv {

// simple foo to calc processes by names in the PC
int CalcOhmCount() {
    using namespace cma::tools;
    int count = 0;
    std::string ohm_name{cma::provider::ohm::kExeModule};
    StringLower(ohm_name);

    wtools::ScanProcessList(
        [ohm_name, &count](const PROCESSENTRY32 &entry) -> bool {
            std::string incoming_name = wtools::ToUtf8(entry.szExeFile);
            StringLower(incoming_name);
            if (ohm_name == incoming_name) count++;
            return true;
        });
    return count;
}

TEST(SectionProviderOhm, DoubleStartIntegration) {
    using namespace cma::tools;
    if (!win::IsElevated()) {
        XLOG::l(XLOG::kStdio)
            .w("No testing of OpenHardwareMonitor. Program must be elevated");
        return;
    }
    auto ohm_path = cma::provider::GetOhmCliPath();
    ASSERT_TRUE(IsValidRegularFile(ohm_path));

    auto count = CalcOhmCount();
    if (count != 0) {
        XLOG::l(XLOG::kStdio)
            .w("OpenHardwareMonitor already started, TESTING IS NOT POSSIBLE");
        return;
    }

    {
        TheMiniProcess oprocess;
        oprocess.start(ohm_path);
        count = CalcOhmCount();
        EXPECT_EQ(count, 1);
        oprocess.start(ohm_path);
        count = CalcOhmCount();
        EXPECT_EQ(count, 1);
    }
    count = CalcOhmCount();
    EXPECT_EQ(count, 0) << "OHM is not killed";
}

TEST(SectionProviderOhm, ErrorReportingIntegration) {
    using namespace cma::provider;
    namespace fs = std::filesystem;

    XLOG::l.t("Killing open hardware monitor...");
    auto test_count = wtools::FindProcess(L"Explorer.exe");
    EXPECT_TRUE(test_count > 0);

    auto ohm_count = wtools::FindProcess(ohm::kExeModuleWide);
    fs::path ohm_exe = GetOhmCliPath();
    if (ohm_count) {
        XLOG::SendStringToStdio("OHM is running...", XLOG::Colors::yellow);

        // Presence
        auto result = cma::tools::IsValidRegularFile(ohm_exe);
        if (!result) {
            XLOG::SendStringToStdio(
                "OHM exe not found, will not stop running OHM, test skipped",
                XLOG::Colors::yellow);
            return;
        }

        for (int i = 0; i < ohm_count; ++i) {
            wtools::KillProcess(ohm::kExeModuleWide, 1);
        }
    }

    OhmProvider ohm(provider::kOhm, ohm::kSepChar);
    auto x = ohm.generateContent("buzz", true);
    EXPECT_TRUE(x.empty());
    EXPECT_EQ(ohm.errorCount(), 1);
    if (ohm_count) {
        cma::tools::RunDetachedCommand(ohm_exe.u8string());
    }
}

TEST(SectionProviderOhm, ResetOhm) {
    std::wstring x(cma::provider::ohm::kResetCommand);
    XLOG::l.i("out = {}", wtools::ToUtf8(x));
    EXPECT_FALSE(x.empty());
}

TEST(SectionProviderOhm, StartStopIntegration) {
    namespace fs = std::filesystem;
    TheMiniProcess oprocess;
    EXPECT_EQ(oprocess.process_id_, 0);
    EXPECT_EQ(oprocess.process_handle_, INVALID_HANDLE_VALUE);
    EXPECT_EQ(oprocess.thread_handle_, INVALID_HANDLE_VALUE);

    // this approximate logic to find OHM executable
    fs::path ohm_exe = cma::cfg::GetUserDir();
    ohm_exe /= cma::cfg::dirs::kUserBin;
    ohm_exe /= cma::provider::ohm::kExeModule;
    // Now check this logic vs API
    EXPECT_EQ(cma::provider::GetOhmCliPath(), ohm_exe);
    // Presence
    ASSERT_TRUE(cma::tools::IsValidRegularFile(ohm_exe))
        << "not found " << ohm_exe.u8string()
        << " probably directories are not ready to test\n";

    auto ret = oprocess.start(ohm_exe.wstring());
    ASSERT_TRUE(ret);
    ::Sleep(500);
    EXPECT_TRUE(oprocess.running());

    ret = oprocess.stop();
    EXPECT_FALSE(oprocess.running());
    EXPECT_EQ(oprocess.process_id_, 0);
    EXPECT_EQ(oprocess.process_handle_, INVALID_HANDLE_VALUE);
    EXPECT_EQ(oprocess.thread_handle_, INVALID_HANDLE_VALUE);
    EXPECT_TRUE(ret);
}

TEST(SectionProviderOhm, ConditionallyStartOhmIntegration) {
    ServiceProcessor sp;
    wtools::KillProcess(cma::provider::ohm::kExeModuleWide, 1);
    auto found = wtools::FindProcess(cma::provider::ohm::kExeModuleWide);
    ASSERT_EQ(found, 0);
    EXPECT_FALSE(sp.stopRunningOhmProcess());
    EXPECT_FALSE(sp.ohm_started_);
    EXPECT_FALSE(sp.ohm_process_.running());
    auto ret = sp.conditionallyStartOhm();
    found = wtools::FindProcess(cma::provider::ohm::kExeModuleWide);
    ASSERT_EQ(found, 1);
    ret = sp.conditionallyStartOhm();
    found = wtools::FindProcess(cma::provider::ohm::kExeModuleWide);
    ASSERT_EQ(found, 1);

    EXPECT_FALSE(sp.ohm_started_) << "may be changed only outside";
    EXPECT_TRUE(sp.ohm_process_.running());
    EXPECT_TRUE(sp.stopRunningOhmProcess());
    found = wtools::FindProcess(cma::provider::ohm::kExeModuleWide);
    ASSERT_EQ(found, 0);
}
}  // namespace cma::srv
