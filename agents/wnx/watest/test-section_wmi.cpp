// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "pch.h"

#include <ranges>

#include "cfg.h"
#include "common/wtools.h"
#include "providers/check_mk.h"
#include "providers/df.h"
#include "providers/mem.h"
#include "providers/p_perf_counters.h"
#include "providers/services.h"
#include "providers/system_time.h"
#include "providers/wmi.h"
#include "service_processor.h"
#include "test_tools.h"
#include "tools/_misc.h"
#include "tools/_process.h"
namespace fs = std::filesystem;
using namespace std::chrono_literals;

namespace wtools {

TEST(WmiWrapper, WmiPostProcess) {
    const std::string s = "name,val\nzeze,5\nzeze,5\n";

    {
        auto ok = WmiPostProcess(s, StatusColumn::ok, ',');
        auto table = cma::tools::SplitString(ok, "\n");
        ASSERT_TRUE(table.size() == 3);

        auto hdr = cma::tools::SplitString(table[0], ",");
        ASSERT_TRUE(hdr.size() == 3);
        EXPECT_TRUE(hdr[2] == "WMIStatus");

        auto row1 = cma::tools::SplitString(table[1], ",");
        ASSERT_TRUE(row1.size() == 3);
        EXPECT_TRUE(row1[2] == StatusColumnText(StatusColumn::ok));

        auto row2 = cma::tools::SplitString(table[2], ",");
        ASSERT_TRUE(row2.size() == 3);
        EXPECT_TRUE(row2[2] == StatusColumnText(StatusColumn::ok));
    }
    {
        auto timeout = WmiPostProcess(s, StatusColumn::timeout, ',');
        auto table = cma::tools::SplitString(timeout, "\n");
        ASSERT_TRUE(table.size() == 3);

        auto hdr = cma::tools::SplitString(table[0], ",");
        ASSERT_TRUE(hdr.size() == 3);
        EXPECT_TRUE(hdr[2] == "WMIStatus");

        auto row1 = cma::tools::SplitString(table[1], ",");
        ASSERT_TRUE(row1.size() == 3);
        EXPECT_TRUE(row1[2] == StatusColumnText(StatusColumn::timeout));

        auto row2 = cma::tools::SplitString(table[2], ",");
        ASSERT_TRUE(row2.size() == 3);
        EXPECT_TRUE(row2[2] == StatusColumnText(StatusColumn::timeout));
    }
}

class WmiWrapperFixture : public ::testing::Test {
protected:
    void SetUp() override {
        wmi.open();
        wmi.connect(L"ROOT\\CIMV2");
        wmi.impersonate();
    }

    void TearDown() override {}
    WmiWrapper wmi;
};

TEST_F(WmiWrapperFixture, Enumerating) {
    auto result = wmi.queryEnumerator({}, L"Win32_Process");
    ON_OUT_OF_SCOPE(if (result) result->Release(););
    EXPECT_TRUE(result != nullptr);

    ULONG returned = 0;
    IWbemClassObject *wmi_object = nullptr;
    auto hres = result->Next(WBEM_INFINITE, 1, &wmi_object, &returned);
    EXPECT_EQ(hres, 0);
    EXPECT_NE(returned, 0);

    auto header = wtools::WmiGetNamesFromObject(wmi_object);
    EXPECT_TRUE(header.size() > 20);
    EXPECT_EQ(header[0], L"Caption");
    EXPECT_EQ(header[1], L"CommandLine");
}

TEST_F(WmiWrapperFixture, TablePostProcess) {
    auto [result, status] = wmi.queryTable(
        {}, L"Win32_Process", L",", cma::cfg::groups::global.getWmiTimeout());
    ASSERT_TRUE(!result.empty());
    EXPECT_EQ(status, WmiStatus::ok);
    EXPECT_TRUE(result.back() == L'\n');

    auto table = cma::tools::SplitString(result, L"\n");
    ASSERT_TRUE(table.size() > 10);
    auto header_array = cma::tools::SplitString(table[0], L",");
    EXPECT_EQ(header_array[0], L"Caption");
    EXPECT_EQ(header_array[1], L"CommandLine");
    auto line1 = cma::tools::SplitString(table[1], L",");
    const auto base_count = line1.size();
    auto line2 = cma::tools::SplitString(table[2], L",");
    EXPECT_EQ(line1.size(), line2.size());
    EXPECT_EQ(line1.size(), header_array.size());
    auto last_line = cma::tools::SplitString(table[table.size() - 1], L",");
    EXPECT_LE(line1.size(), last_line.size());

    {
        auto str = WmiPostProcess(ToUtf8(result), StatusColumn::ok, ',');
        XLOG::l.i("string is {}", str);
        EXPECT_TRUE(!str.empty());
        auto t1 = cma::tools::SplitString(str, "\n");
        EXPECT_EQ(table.size(), t1.size());
        auto t1_0 = cma::tools::SplitString(t1[0], ",");
        EXPECT_EQ(t1_0.size(), base_count + 1);
        EXPECT_EQ(t1_0.back(), "WMIStatus");
        auto t1_1 = cma::tools::SplitString(t1[1], ",");
        EXPECT_EQ(t1_1.back(), "OK");
        auto t1_last = cma::tools::SplitString(t1.back(), ",");
        EXPECT_EQ(t1_last.back(), "OK");
    }
    {
        auto str = WmiPostProcess(ToUtf8(result), StatusColumn::timeout, ',');
        XLOG::l("{}", str);
        EXPECT_TRUE(!str.empty());
        auto t1 = cma::tools::SplitString(str, "\n");
        EXPECT_EQ(table.size(), t1.size());
        auto t1_0 = cma::tools::SplitString(t1[0], ",");
        EXPECT_EQ(t1_0.size(), base_count + 1);
        EXPECT_EQ(t1_0.back(), "WMIStatus");
        auto t1_1 = cma::tools::SplitString(t1[1], ",");
        EXPECT_EQ(t1_1.back(), "Timeout");
        auto t1_last = cma::tools::SplitString(t1.back(), ",");
        EXPECT_EQ(t1_last.back(), "Timeout");
    }
}

TEST_F(WmiWrapperFixture, Table) {
    auto [result, status] = wmi.queryTable(
        {}, L"Win32_Process", L",", cma::cfg::groups::global.getWmiTimeout());
    ASSERT_TRUE(!result.empty());
    EXPECT_EQ(status, WmiStatus::ok);
    EXPECT_TRUE(result.back() == L'\n');

    auto table = cma::tools::SplitString(result, L"\n");
    ASSERT_TRUE(table.size() > 10);
    auto header_array = cma::tools::SplitString(table[0], L",");
    EXPECT_EQ(header_array[0], L"Caption");
    EXPECT_EQ(header_array[1], L"CommandLine");
    auto line1 = cma::tools::SplitString(table[1], L",");
    auto line2 = cma::tools::SplitString(table[2], L",");
    EXPECT_EQ(line1.size(), line2.size());
    EXPECT_EQ(line1.size(), header_array.size());
}

}  // namespace wtools

namespace cma::provider {

TEST(WmiProviderTest, WmiBadName) {  //
    cma::OnStart(cma::AppType::test);

    Wmi badname("badname", wmi::kSepChar);
    EXPECT_EQ(badname.object(), L"");
    EXPECT_EQ(badname.nameSpace(), L"");
    EXPECT_FALSE(badname.isAllowedByCurrentConfig());
    EXPECT_TRUE(badname.isAllowedByTime());

    Wmi x("badname", '.');
    x.registerCommandLine("1.1.1.1 wefwef rfwrwer rwerw");
    EXPECT_EQ(x.ip(), "1.1.1.1");
}

TEST(WmiProviderTest, OhmCtor) {
    Wmi ohm(kOhm, ohm::kSepChar);
    EXPECT_EQ(ohm.object(), L"Sensor");
    EXPECT_EQ(ohm.nameSpace(), L"Root\\OpenHardwareMonitor");
    EXPECT_EQ(ohm.columns().size(), 5);
}

TEST(WmiProviderTest, OhmIntegration) {
    auto temp_fs{tst::TempCfgFs::Create()};
    ASSERT_TRUE(temp_fs->loadConfig(tst::GetFabricYml()));
    Wmi ohm(kOhm, ohm::kSepChar);
    EXPECT_TRUE(ohm.isAllowedByCurrentConfig());
    tst::EnableSectionsNode(provider::kOhm, true);
    EXPECT_TRUE(ohm.isAllowedByCurrentConfig());
    tst::DisableSectionsNode(provider::kOhm, true);
    EXPECT_FALSE(ohm.isAllowedByCurrentConfig());
}

TEST(WmiProviderTest, WmiConfiguration) {
    {
        EXPECT_TRUE(IsHeaderless(kMsExch));
        EXPECT_FALSE(IsHeaderless(kWmiCpuLoad));
        EXPECT_FALSE(IsHeaderless("xdf"));
    }
    {
        auto type = GetSubSectionType(kMsExch);
        EXPECT_TRUE(type == SubSection::Type::full);
        type = GetSubSectionType(kWmiCpuLoad);
        EXPECT_TRUE(type == SubSection::Type::sub);
        type = GetSubSectionType("xdf");
        EXPECT_TRUE(type == SubSection::Type::sub);
    }
}

const char *exch_names[] = {kMsExchActiveSync,     //
                            kMsExchAvailability,   //
                            kMsExchOwa,            //
                            kMsExchAutoDiscovery,  //
                            kMsExchIsClientType,   //
                            kMsExchIsStore,        //
                            kMsExchRpcClientAccess};
TEST(WmiProviderTest, WmiSubSection_Integration) {
    for (auto n : exch_names) {
        SubSection ss(n, SubSection::Type::full);
        auto ret = ss.generateContent(SubSection::Mode::standard);
        EXPECT_TRUE(ret.empty()) << "expected we do not have ms exchange";
        ret = ss.generateContent(SubSection::Mode::debug_forced);
        EXPECT_FALSE(ret.empty());
        EXPECT_NE(ret.find(":sep(124)"), std::string::npos)
            << "bad situation with " << n << "\n";
    }

    SubSection ss(kSubSectionSystemPerf, SubSection::Type::sub);
    auto ret = ss.generateContent(SubSection::Mode::debug_forced);
    ret = ss.generateContent(SubSection::Mode::debug_forced);
    auto table = cma::tools::SplitString(ret, "\n");
    ASSERT_EQ(table.size(), 3);
    EXPECT_FALSE(table[0].empty());
    EXPECT_FALSE(table[1].empty());
    EXPECT_FALSE(table[2].empty());
    {
        auto headers =
            cma::tools::SplitString(table[1], wtools::ToUtf8(wmi::kSepString));
        auto values =
            cma::tools::SplitString(table[2], wtools::ToUtf8(wmi::kSepString));
        EXPECT_FALSE(headers.empty());
        EXPECT_FALSE(values.empty());
        ASSERT_TRUE(headers.size() > 10);
        EXPECT_EQ(headers.size(), values.size());
    }
    EXPECT_EQ(table[0], std::string("[") + kSubSectionSystemPerf + "]");
}

TEST(WmiProviderTest, SubSectionSimulateExchange_Integration) {
    Wmi msexch(kMsExch, wmi::kSepChar);
    msexch.generateContent(kMsExch, true);
    auto ret = msexch.generateContent(kMsExch, true);
    EXPECT_TRUE(ret.empty()) << "expected we do not have ms exchange";
    msexch.subsection_mode_ = SubSection::Mode::debug_forced;
    ret = msexch.generateContent(kMsExch, true);
    EXPECT_FALSE(ret.empty());
    auto table = cma::tools::SplitString(ret, "\n");
    EXPECT_EQ(table.size(), 7);
    const int count = 7;
    for (int k = 0; k < count; ++k) {
        auto expected = fmt::format("<<<{}:sep({})>>>", exch_names[k],
                                    static_cast<uint32_t>(wmi::kSepChar));
        EXPECT_EQ(table[k], expected);
    }
}

TEST(WmiProviderTest, SimulationIntegration) {  //
    std::wstring sep(wmi::kSepString);
    std::string sep_ascii = wtools::ToUtf8(sep);
    {
        auto [r, status] =
            GenerateWmiTable(kWmiPathStd, L"Win32_ComputerSystem", {}, sep);
        EXPECT_EQ(status, wtools::WmiStatus::ok);
        EXPECT_TRUE(!r.empty());
    }

    {
        auto [r, status] =
            GenerateWmiTable(L"", L"Win32_ComputerSystemZ", {}, sep);
        EXPECT_EQ(status, wtools::WmiStatus::bad_param)
            << "should be ok, invalid name means NOTHING";
        EXPECT_TRUE(r.empty());
    }

    {
        auto [r, status] =
            GenerateWmiTable(kWmiPathStd, L"Win32_ComputerSystemZ", {}, sep);
        EXPECT_EQ(status, wtools::WmiStatus::error)
            << "should be ok, invalid name means NOTHING";
        EXPECT_TRUE(r.empty());
    }

    {
        auto [r, status] = GenerateWmiTable(std::wstring(kWmiPathStd) + L"A",
                                            L"Win32_ComputerSystem", {}, sep);
        EXPECT_EQ(status, wtools::WmiStatus::fail_connect);
        EXPECT_TRUE(r.empty());
    }

    {
        Wmi dotnet_clr(kDotNetClrMemory, wmi::kSepChar);
        EXPECT_EQ(dotnet_clr.subsection_mode_, SubSection::Mode::standard);
        EXPECT_EQ(dotnet_clr.delay_on_fail_, cma::cfg::G_DefaultDelayOnFail);
        EXPECT_EQ(dotnet_clr.object(),
                  L"Win32_PerfRawData_NETFramework_NETCLRMemory");
        EXPECT_TRUE(dotnet_clr.isAllowedByCurrentConfig());
        EXPECT_TRUE(dotnet_clr.isAllowedByTime());
        EXPECT_EQ(dotnet_clr.delay_on_fail_, 3600s);

        EXPECT_EQ(dotnet_clr.nameSpace(), L"Root\\Cimv2");
        std::string body;
        bool damned_windows = true;
        for (int i = 0; i < 5; i++) {
            body = dotnet_clr.makeBody();
            if (!body.empty()) {
                damned_windows = false;
                break;
            }
        }
        ASSERT_FALSE(damned_windows)
            << "please, run start_wmi.cmd\n 1 bad output from wmi:\n"
            << body << "\n";  // more than 1 line should be present;
        auto table = cma::tools::SplitString(body, "\n");
        ASSERT_GT(table.size(), (size_t)(1))
            << "2 bad output from wmi:\n"
            << body << "\n";  // more than 1 line should be present

        auto header = cma::tools::SplitString(table[0], sep_ascii);
        ASSERT_GT(header.size(), static_cast<size_t>(5));
        EXPECT_EQ(header[0], "AllocatedBytesPersec");
        EXPECT_EQ(header[13], "Name");

        auto line1 = cma::tools::SplitString(table[1], sep_ascii);
        EXPECT_EQ(line1.size(), header.size());
    }

    {
        Wmi wmi_web(kWmiWebservices, wmi::kSepChar);
        EXPECT_EQ(wmi_web.subsection_mode_, SubSection::Mode::standard);
        EXPECT_EQ(wmi_web.delay_on_fail_, cma::cfg::G_DefaultDelayOnFail);

        EXPECT_EQ(wmi_web.object(), L"Win32_PerfRawData_W3SVC_WebService");
        EXPECT_EQ(wmi_web.nameSpace(), L"Root\\Cimv2");
        auto body = wmi_web.makeBody();
        EXPECT_TRUE(wmi_web.isAllowedByCurrentConfig());
        EXPECT_TRUE(wmi_web.isAllowedByTime());
        EXPECT_EQ(wmi_web.delay_on_fail_, 3600s);
    }

    {
        using namespace std::chrono;
        Wmi bad_wmi(kBadWmi, wmi::kSepChar);
        EXPECT_EQ(bad_wmi.object(), L"BadSensor");
        EXPECT_EQ(bad_wmi.nameSpace(), L"Root\\BadWmiPath");

        auto body = bad_wmi.makeBody();
        auto tp_expected = steady_clock::now() + cma::cfg::G_DefaultDelayOnFail;
        EXPECT_FALSE(bad_wmi.isAllowedByTime())
            << "bad wmi must failed and wait";
        auto tp_low = bad_wmi.allowed_from_time_ - 50s;
        auto tp_high = bad_wmi.allowed_from_time_ + 50s;
        EXPECT_TRUE(tp_expected > tp_low && tp_expected < tp_high);
    }

    {
        Wmi cpu(kWmiCpuLoad, wmi::kSepChar);
        EXPECT_EQ(cpu.subsection_mode_, SubSection::Mode::standard);
        ASSERT_FALSE(cpu.headerless_);
        EXPECT_EQ(cpu.delay_on_fail_, cma::cfg::G_DefaultDelayOnFail);

        // this is empty section
        EXPECT_EQ(cpu.object(), L"");
        EXPECT_EQ(cpu.nameSpace(), L"");
        EXPECT_EQ(cpu.columns().size(), 0);

        // sub section count
        EXPECT_EQ(cpu.sub_objects_.size(), 2);
        EXPECT_EQ(cpu.sub_objects_[0].getUniqName(), kSubSectionSystemPerf);
        EXPECT_EQ(cpu.sub_objects_[1].getUniqName(), kSubSectionComputerSystem);

        EXPECT_FALSE(cpu.sub_objects_[0].name_space_.empty());
        EXPECT_FALSE(cpu.sub_objects_[0].object_.empty());
        EXPECT_FALSE(cpu.sub_objects_[1].name_space_.empty());
        EXPECT_FALSE(cpu.sub_objects_[1].object_.empty());

        // other:
        EXPECT_TRUE(cpu.isAllowedByCurrentConfig());
        EXPECT_TRUE(cpu.isAllowedByTime());
        EXPECT_EQ(cpu.delay_on_fail_, 3600s);
    }
    {
        Wmi msexch(kMsExch, wmi::kSepChar);
        ASSERT_TRUE(msexch.headerless_);
        EXPECT_EQ(msexch.subsection_mode_, SubSection::Mode::standard);
        EXPECT_EQ(msexch.delay_on_fail_, cma::cfg::G_DefaultDelayOnFail);
        // this is empty section
        EXPECT_EQ(msexch.object(), L"");
        EXPECT_EQ(msexch.nameSpace(), L"");
        EXPECT_EQ(msexch.columns().size(), 0);

        // sub section count
        const int count = 7;
        auto &subs = msexch.sub_objects_;
        EXPECT_EQ(subs.size(), count);
        for (int k = 0; k < count; ++k)
            EXPECT_EQ(subs[k].getUniqName(), exch_names[k]);

        for (auto &sub : subs) {
            EXPECT_TRUE(!sub.name_space_.empty());
            EXPECT_TRUE(!sub.object_.empty());
        }

        // other:
        EXPECT_TRUE(msexch.isAllowedByCurrentConfig());
        EXPECT_TRUE(msexch.isAllowedByTime());

        EXPECT_EQ(msexch.delay_on_fail_, 3600s);
    }
}

static const std::string section_name{cma::section::kUseEmbeddedName};
#define FNAME_USE "x.xxx"
auto ReadFileAsTable(const std::string Name) {
    std::ifstream in(Name.c_str());
    std::stringstream sstr;
    sstr << in.rdbuf();
    auto content = sstr.str();
    return cma::tools::SplitString(content, "\n");
}

TEST(WmiProviderTest, WmiDotnet_Integration) {
    using namespace cma::section;
    using namespace cma::provider;
    namespace fs = std::filesystem;

    auto wmi_name = kDotNetClrMemory;
    fs::path f(FNAME_USE);
    fs::remove(f);

    cma::srv::SectionProvider<Wmi> wmi_provider(wmi_name, ',');
    EXPECT_EQ(wmi_provider.getEngine().getUniqName(), wmi_name);

    auto &e2 = wmi_provider.getEngine();
    EXPECT_TRUE(e2.isAllowedByCurrentConfig());
    EXPECT_TRUE(e2.isAllowedByTime());

    bool damned_windows = true;
    for (int i = 0; i < 10; i++) {
        auto data = e2.generateContent(section_name);
        if (!data.empty()) {
            damned_windows = false;
            break;
        }
    }
    EXPECT_FALSE(damned_windows)
        << "please, run start_wmi.cmd\n dot net clr not found\n";

    auto cmd_line = std::to_string(12345) + " " + wmi_name + " ";
    e2.startExecution("file:" FNAME_USE, cmd_line);

    std::error_code ec;
    ASSERT_TRUE(fs::exists(f, ec));  // check that file is exists
    {
        auto table = ReadFileAsTable(f.u8string());
        ASSERT_TRUE(table.size() > 1);  // more than 1 line should be present
        EXPECT_EQ(table[0] + "\n", cma::section::MakeHeader(wmi_name, ','));

        auto header = cma::tools::SplitString(table[1], ",");
        EXPECT_EQ(header[0], "AllocatedBytesPersec");
        EXPECT_EQ(header[13], "Name");

        auto line1 = cma::tools::SplitString(table[2], ",");
        EXPECT_EQ(line1.size(), header.size());
    }
    fs::remove(f);
}

TEST(WmiProviderTest, BasicWmi) {
    {
        Wmi b("a", ',');
        auto old_time = b.allowed_from_time_;
        b.delay_on_fail_ = 900s;
        b.disableSectionTemporary();
        auto new_time = b.allowed_from_time_;
        auto delta = new_time - old_time;
        EXPECT_TRUE(delta >= 900s);
        b.setupDelayOnFail();
        EXPECT_EQ(b.delay_on_fail_, 0s);
    }

    for (auto name :
         {kOhm, kWmiCpuLoad, kWmiWebservices, kDotNetClrMemory, kMsExch}) {
        Wmi b(name, ',');
        EXPECT_EQ(b.delay_on_fail_, cma::cfg::G_DefaultDelayOnFail)
            << "bad delay for section by default " << name;
        b.delay_on_fail_ = 1s;
        b.setupDelayOnFail();
        EXPECT_EQ(b.delay_on_fail_, cma::cfg::G_DefaultDelayOnFail)
            << "bad delay for section in func call " << name;
    }
}

TEST(WmiProviderTest, BasicWmiDefaultsAndError) {
    Wmi tst("check", '|');

    EXPECT_EQ(tst.delay_on_fail_, 0s);
    EXPECT_EQ(tst.timeout_, 0);
    EXPECT_TRUE(tst.enabled_);
    EXPECT_FALSE(tst.headerless_);

    EXPECT_EQ(tst.separator_, '|');
    EXPECT_EQ(tst.error_count_, 0);
    EXPECT_EQ(tst.errorCount(), 0);
    tst.registerError();
    EXPECT_EQ(tst.error_count_, 1);
    EXPECT_EQ(tst.errorCount(), 1);
    tst.registerError();
    EXPECT_EQ(tst.error_count_, 2);
    EXPECT_EQ(tst.errorCount(), 2);
    tst.resetError();
    EXPECT_EQ(tst.error_count_, 0);
    EXPECT_EQ(tst.errorCount(), 0);
}

class WmiProviderTestFixture : public ::testing::Test {
public:
    void SetUp() override {
        temp_fs_ = tst::TempCfgFs::CreateNoIo();
        ASSERT_TRUE(temp_fs_->loadConfig(tst::GetFabricYml()));
    }

protected:
    std::vector<std::string> execWmiProvider(const std::string &wmi_name,
                                             const std::string &test_name) {
        auto f = tst::GetTempDir() / test_name;

        cma::srv::SectionProvider<Wmi> wmi_provider(wmi_name, wmi::kSepChar);
        EXPECT_EQ(wmi_provider.getEngine().getUniqName(), wmi_name);

        auto &e2 = wmi_provider.getEngine();
        EXPECT_TRUE(e2.isAllowedByCurrentConfig());
        EXPECT_TRUE(e2.isAllowedByTime());

        auto cmd_line = std::to_string(12345) + " " + wmi_name + " ";
        e2.startExecution(fmt::format("file:{}", f.u8string()), cmd_line);

        std::error_code ec;
        if (!fs::exists(f, ec)) {
            return {};
        }
        return ReadFileAsTable(f.u8string());
    }

private:
    tst::TempCfgFs::ptr temp_fs_;
};

TEST_F(WmiProviderTestFixture, WmiMsExch) {
    auto table = execWmiProvider(
        kMsExch,
        ::testing::UnitTest::GetInstance()->current_test_info()->name());
    if (table.empty()) {
        return;
    }

    ASSERT_TRUE(table.size() > 1);  // more than 1 line should be present
    EXPECT_EQ(table[0] + "\n",
              cma::section::MakeHeader(kMsExch, wmi::kSepChar));
}

// Test is integration because wmi web services may be not available
TEST_F(WmiProviderTestFixture, WmiWebIntegration) {
    auto table = execWmiProvider(
        kWmiWebservices,
        ::testing::UnitTest::GetInstance()->current_test_info()->name());
    ASSERT_TRUE(table.size() > 1);  // more than 1 line should be present
    EXPECT_EQ(table[0] + "\n",
              cma::section::MakeHeader(kWmiWebservices, wmi::kSepChar));
}

TEST_F(WmiProviderTestFixture, WmiCpu) {
    auto table = execWmiProvider(
        kWmiCpuLoad,
        ::testing::UnitTest::GetInstance()->current_test_info()->name());

    ASSERT_TRUE(table.size() >= 5);  // header, two subheaders and two lines
    EXPECT_EQ(table[0] + "\n",
              cma::section::MakeHeader(kWmiCpuLoad, wmi::kSepChar));

    for (const auto &section :
         {kSubSectionSystemPerf, kSubSectionComputerSystem}) {
        auto header = cma::section::MakeSubSectionHeader(section);
        header.pop_back();
        EXPECT_TRUE(std::ranges::any_of(
            table, [header](auto const &e) { return e == header; }));
    }
}

}  // namespace cma::provider
