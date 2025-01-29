// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "pch.h"

#include <ranges>

#include "common/wtools.h"
#include "providers/check_mk.h"
#include "providers/df.h"
#include "providers/wmi.h"
#include "tools/_misc.h"
#include "watest/test_tools.h"
#include "wnx/cfg.h"
#include "wnx/service_processor.h"

namespace fs = std::filesystem;
namespace rs = std::ranges;
using namespace std::chrono_literals;
namespace {
const std::wstring web_services_service{L"AppHostSvc"};
}

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

TEST_F(WmiWrapperFixture, QueryTableTimeout) {
    auto [result, status] = wmi.queryTable({}, L"Win32_Process", L",", 0);
    EXPECT_EQ(status, WmiStatus::timeout);
    EXPECT_TRUE(result.empty());
}

TEST_F(WmiWrapperFixture, TablePostProcess) {
    auto [result, status] = wmi.queryTable(
        {}, L"Win32_Process", L",", cma::cfg::groups::g_global.getWmiTimeout());
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
        {}, L"Win32_Process", L",", cma::cfg::groups::g_global.getWmiTimeout());
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

TEST(WmiProviderTest, OhmComponent) {
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
    EXPECT_TRUE(IsHeaderless(kMsExch));
    EXPECT_FALSE(IsHeaderless(kWmiCpuLoad));
    EXPECT_FALSE(IsHeaderless("xdf"));

    auto type = GetSubSectionType(kMsExch);
    EXPECT_TRUE(type == SubSection::Type::full);
    type = GetSubSectionType(kWmiCpuLoad);
    EXPECT_TRUE(type == SubSection::Type::sub);
    type = GetSubSectionType("xdf");
    EXPECT_TRUE(type == SubSection::Type::sub);
}

constexpr std::array exch_names = {kMsExchActiveSync,     //
                                   kMsExchAvailability,   //
                                   kMsExchOwa,            //
                                   kMsExchAutoDiscovery,  //
                                   kMsExchIsClientType,   //
                                   kMsExchIsStore,        //
                                   kMsExchRpcClientAccess};
constexpr size_t exch_count{exch_names.size()};

TEST(WmiProviderTest, WmiSubSection_Component) {
    for (auto n : exch_names) {
        SubSection ss(n, SubSection::Type::full);
        auto ret = ss.generateContent(SubSection::Mode::standard);
        EXPECT_TRUE(ret.empty()) << "expected we do not have ms exchange";
        ret = ss.generateContent(SubSection::Mode::forced);
        EXPECT_FALSE(ret.empty());
        EXPECT_NE(ret.find(":sep(124)"), std::string::npos)
            << "bad situation with " << n << "\n";
    }

    SubSection ss(kSubSectionSystemPerf, SubSection::Type::sub);
    auto ret = ss.generateContent(SubSection::Mode::forced);
    ret = ss.generateContent(SubSection::Mode::forced);
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
    EXPECT_EQ(table[0],
              std::string{"["} + std::string{kSubSectionSystemPerf} + "]");
}

TEST(WmiProviderTest, SubSectionMsExchComponent) {
    auto temp_fs = tst::TempCfgFs::CreateNoIo();
    EXPECT_TRUE(
        temp_fs->loadContent("global:\n"
                             "  enabled: yes\n"
                             "  sections:\n"
                             "  - msexch\n"));
    Wmi msexch_production(kMsExch, wmi::kSepChar);
    EXPECT_TRUE(msexch_production.generateContent(kMsExch, true).empty())
        << "expected we do not have ms exchange";

    Wmi msexch_forced(kMsExch, wmi::kSepChar, SubSection::Mode::forced);
    const auto ret = msexch_forced.generateContent(kMsExch, true);
    const auto table = tools::SplitString(ret, "\n");
    EXPECT_EQ(table.size(), exch_count);
    for (size_t k = 0; k < exch_count; ++k) {
        const auto expected = fmt::format("<<<{}:sep({})>>>", exch_names[k],
                                          static_cast<uint32_t>(wmi::kSepChar));
        EXPECT_EQ(table[k], expected);
    }
}

TEST(WmiProviderTest, SimulationComponent) {
    auto temp_fs = tst::TempCfgFs::CreateNoIo();
    EXPECT_TRUE(
        temp_fs->loadContent("global:\n"
                             "  enabled: yes\n"
                             "  sections:\n"
                             "  - msexch\n"
                             "  - dotnet_clrmemory\n"
                             "  - wmi_webservices\n"
                             "  - wmi_cpuload\n"
                             "  - bad_wmi"));
    constexpr std::wstring_view sep(wmi::kSepString);
    const std::string sep_ascii{wtools::ToUtf8(sep)};
    {
        const auto &[r, status] =
            GenerateWmiTable(kWmiPathStd, L"Win32_ComputerSystem", {}, sep);
        EXPECT_EQ(status, wtools::WmiStatus::ok);
        EXPECT_TRUE(!r.empty());
    }

    {
        const auto &[r, status] =
            GenerateWmiTable(L"", L"Win32_ComputerSystemZ", {}, sep);
        EXPECT_EQ(status, wtools::WmiStatus::bad_param)
            << "should be ok, invalid name means NOTHING";
        EXPECT_TRUE(r.empty());
    }

    {
        const auto &[r, status] =
            GenerateWmiTable(kWmiPathStd, L"Win32_ComputerSystemZ", {}, sep);
        EXPECT_EQ(status, wtools::WmiStatus::error)
            << "should be ok, invalid name means NOTHING";
        EXPECT_TRUE(r.empty());
    }

    {
        const auto &[r, status] = GenerateWmiTable(
            std::wstring(kWmiPathStd) + L"A", L"Win32_ComputerSystem", {}, sep);
        EXPECT_EQ(status, wtools::WmiStatus::fail_connect);
        EXPECT_TRUE(r.empty());
    }

    {
        Wmi dotnet_clr(kDotNetClrMemory, wmi::kSepChar);
        EXPECT_EQ(dotnet_clr.subsectionMode(), SubSection::Mode::standard);
        EXPECT_EQ(dotnet_clr.delayOnFail(), 0s);
        EXPECT_EQ(dotnet_clr.object(),
                  L"Win32_PerfRawData_NETFramework_NETCLRMemory");
        EXPECT_TRUE(dotnet_clr.isAllowedByCurrentConfig());
        EXPECT_TRUE(dotnet_clr.isAllowedByTime());

        EXPECT_EQ(dotnet_clr.nameSpace(), L"Root\\Cimv2");
        std::string body;
        bool damned_windows = true;
        for (int i = 0; i < 5; i++) {
            body = dotnet_clr.generateContent();
            if (!body.empty()) {
                damned_windows = false;
                break;
            }
        }
        ASSERT_FALSE(damned_windows)
            << "please, run start_wmi.cmd\n 1 bad output from wmi:\n"
            << body << "\n";  // more than 1 line should be present;
        auto table = cma::tools::SplitString(body, "\n");
        table.erase(table.begin());
        ASSERT_GT(table.size(), 1U)
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
        Wmi bad_wmi(kBadWmi, wmi::kSepChar);
        EXPECT_EQ(bad_wmi.object(), L"BadSensor");
        EXPECT_EQ(bad_wmi.nameSpace(), L"Root\\BadWmiPath");

        auto body = bad_wmi.generateContent();
        auto tp_expected =
            std::chrono::steady_clock::now() + cma::cfg::G_DefaultDelayOnFail;
        EXPECT_FALSE(bad_wmi.isAllowedByTime())
            << "bad wmi must failed and wait";
        auto tp_low = bad_wmi.allowedFromTime() - 50s;
        auto tp_high = bad_wmi.allowedFromTime() + 50s;
        EXPECT_TRUE(tp_expected > tp_low && tp_expected < tp_high);
    }

    {
        Wmi cpu(kWmiCpuLoad, wmi::kSepChar);
        EXPECT_EQ(cpu.subsectionMode(), SubSection::Mode::standard);
        ASSERT_FALSE(cpu.headerless());
        EXPECT_EQ(cpu.delayOnFail(), 0s);

        // this is empty section
        EXPECT_EQ(cpu.object(), L"");
        EXPECT_EQ(cpu.nameSpace(), L"");
        EXPECT_EQ(cpu.columns().size(), 0);

        // sub section count
        EXPECT_EQ(cpu.subObjects().size(), 2);
        EXPECT_EQ(cpu.subObjects()[0].getUniqName(), kSubSectionSystemPerf);
        EXPECT_EQ(cpu.subObjects()[1].getUniqName(), kSubSectionComputerSystem);

        EXPECT_FALSE(cpu.subObjects()[0].nameSpace().empty());
        EXPECT_FALSE(cpu.subObjects()[0].object().empty());
        EXPECT_FALSE(cpu.subObjects()[1].nameSpace().empty());
        EXPECT_FALSE(cpu.subObjects()[1].object().empty());

        // other:
        EXPECT_TRUE(cpu.isAllowedByCurrentConfig());
        EXPECT_TRUE(cpu.isAllowedByTime());
        EXPECT_EQ(cpu.delayOnFail(), 0s);
    }
    {
        Wmi msexch(kMsExch, wmi::kSepChar);
        ASSERT_TRUE(msexch.headerless());
        EXPECT_EQ(msexch.subsectionMode(), SubSection::Mode::standard);
        EXPECT_EQ(msexch.delayOnFail(), cma::cfg::G_DefaultDelayOnFail);
        // this is empty section
        EXPECT_EQ(msexch.object(), L"");
        EXPECT_EQ(msexch.nameSpace(), L"");
        EXPECT_EQ(msexch.columns().size(), 0);

        // sub section count
        constexpr int count = 7;
        auto &subs = msexch.subObjects();
        EXPECT_EQ(subs.size(), count);
        for (int k = 0; k < count; ++k)
            EXPECT_EQ(subs[k].getUniqName(), exch_names[k]);

        for (auto &sub : subs) {
            EXPECT_TRUE(!sub.nameSpace().empty());
            EXPECT_TRUE(!sub.object().empty());
        }

        // other:
        EXPECT_TRUE(msexch.isAllowedByCurrentConfig());
        EXPECT_TRUE(msexch.isAllowedByTime());

        EXPECT_EQ(msexch.delayOnFail(), 3600s);
    }
}

TEST(WmiProviderTest, WmiWebServicesDefaults) {
    Wmi wmi_web(kWmiWebservices, wmi::kSepChar);

    EXPECT_EQ(wmi_web.object(), L"Win32_PerfRawData_W3SVC_WebService");
    EXPECT_EQ(wmi_web.nameSpace(), L"Root\\Cimv2");
    EXPECT_TRUE(wmi_web.isAllowedByCurrentConfig());
    EXPECT_TRUE(wmi_web.isAllowedByTime());
}

TEST(WmiProviderTest, WmiWebServicesComponent) {
    Wmi wmi_web(kWmiWebservices, wmi::kSepChar);
    auto body = wmi_web.generateContent();

    if (wtools::GetServiceStatus(web_services_service) == 0) {
        EXPECT_TRUE(body.empty());
    } else {
        EXPECT_GE(tools::SplitString(body, "\n").size(), 4U);
    }
}

static const std::string section_name{cma::section::kUseEmbeddedName};
#define FNAME_USE "x.xxx"
TEST(WmiProviderTest, WmiDotnet_Component) {
    using namespace cma::section;
    using namespace cma::provider;

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

    auto cmd_line = std::to_string(12345) + " " + std::string{wmi_name} + " ";
    e2.startExecution("file:" FNAME_USE, cmd_line);

    std::error_code ec;
    ASSERT_TRUE(fs::exists(f, ec));  // check that file is exists
    {
        auto table = tst::ReadFileAsTable(f);
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

namespace {
auto MeasureTimeOnGenerate(Wmi &wmi) {
    const auto old_time = wmi.allowedFromTime();
    wmi.generateContent();
    return wmi.allowedFromTime() - old_time;
}
}  // namespace

TEST(WmiProviderTest, BasicWmi) {
    Wmi b("a", ',');
    EXPECT_EQ(MeasureTimeOnGenerate(b), 0s);
    EXPECT_EQ(b.delayOnFail(), 0s);
}

TEST(WmiProviderTest, DelayOnFailDefault) {
    for (const auto name : {kOhm, kWmiWebservices, kMsExch}) {
        Wmi b(name, ',');
        EXPECT_EQ(b.delayOnFail(), 3600s)
            << "bad delay for section by default " << name;
    }
    for (const auto name : {kWmiCpuLoad, kDotNetClrMemory}) {
        Wmi b(name, ',');
        EXPECT_EQ(b.delayOnFail(), 0s)
            << "bad delay for section by default " << name;
    }
}

TEST(WmiProviderTest, DelayOnFailShift) {
    auto temp_fs = tst::TempCfgFs::CreateNoIo();
    EXPECT_TRUE(
        temp_fs->loadContent("global:\n"
                             "  enabled: yes\n"
                             "  sections:\n"
                             "  - OhmBad\n"
                             "  - msexch\n"));
    Wmi ms_exch(kMsExch, ',');  // must be absent
    EXPECT_GE(MeasureTimeOnGenerate(ms_exch), 0s);

    Wmi ohm("OhmBad", ',');  // must be absent
    EXPECT_GE(MeasureTimeOnGenerate(ohm), 1500s);
}

TEST(WmiProviderTest, BasicWmiDefaults) {
    Wmi tst(kOhm, ',');

    EXPECT_EQ(tst.delayOnFail(), 3600s);
    EXPECT_EQ(tst.timeout(), 0);
    EXPECT_TRUE(tst.enabled());
    EXPECT_FALSE(tst.headerless());
    EXPECT_EQ(tst.separator(), ',');
    EXPECT_EQ(tst.errorCount(), 0);
}

TEST(WmiProviderTest, RegisterAndResetError) {
    auto temp_fs = tst::TempCfgFs::CreateNoIo();
    EXPECT_TRUE(
        temp_fs->loadContent("global:\n"
                             "  enabled: yes\n"
                             "  sections:\n"
                             "  - openhardwaremonitor\n"));
    OhmProvider tst(kOhm, ',');

    tst.generateContent();
    EXPECT_EQ(tst.errorCount(), 1);
    tst.resetError();
    EXPECT_EQ(tst.errorCount(), 0);
}

class WmiProviderTestFixture : public ::testing::Test {
public:
    void SetUp() override {
        temp_fs_ = tst::TempCfgFs::CreateNoIo();
        ASSERT_TRUE(temp_fs_->loadConfig(tst::GetFabricYml()));
    }

protected:
    [[nodiscard]] std::vector<std::string> execWmiProvider(
        std::string_view wmi_name, const std::string &test_name) const {
        auto f = tst::GetTempDir() / test_name;

        cma::srv::SectionProvider<Wmi> wmi_provider(wmi_name, wmi::kSepChar);
        EXPECT_EQ(wmi_provider.getEngine().getUniqName(), wmi_name);

        auto &e2 = wmi_provider.getEngine();
        EXPECT_TRUE(e2.isAllowedByCurrentConfig());
        EXPECT_TRUE(e2.isAllowedByTime());

        auto cmd_line = std::to_string(12345) + " " + wmi_name.data() + " ";
        e2.startExecution(fmt::format("file:{}", f), cmd_line);

        std::error_code ec;
        if (!fs::exists(f, ec)) {
            return {};
        }
        return tst::ReadFileAsTable(f);
    }

private:
    tst::TempCfgFs::ptr temp_fs_;
};

TEST_F(WmiProviderTestFixture, WmiMsExch) {
    auto table = execWmiProvider(kMsExch, tst::GetUnitTestName());
    if (table.empty()) {
        return;
    }

    ASSERT_TRUE(table.size() > 1);  // more than 1 line should be present
    EXPECT_EQ(table[0] + "\n",
              cma::section::MakeHeader(kMsExch, wmi::kSepChar));
}

TEST_F(WmiProviderTestFixture, WmiWebServicesAbsentComponent) {
    if (wtools::GetServiceStatus(web_services_service) != 0) {
        GTEST_SKIP() << fmt::format(L"'{}' is presented", web_services_service);
    }

    const auto table = execWmiProvider(kWmiWebservices, tst::GetUnitTestName());
    ASSERT_TRUE(table.empty());
}

TEST_F(WmiProviderTestFixture, WmiWebServicesPresentedComponent) {
    if (wtools::GetServiceStatus(web_services_service) == 0) {
        GTEST_SKIP() << fmt::format(L"'{}' is absent", web_services_service);
    }

    const auto table = execWmiProvider(kWmiWebservices, tst::GetUnitTestName());
    ASSERT_GT(table.size(), 3U);
    EXPECT_EQ(table[0] + "\n",
              section::MakeHeader(kWmiWebservices, wmi::kSepChar));
}

TEST_F(WmiProviderTestFixture, WmiCpu) {
    auto table = execWmiProvider(kWmiCpuLoad, tst::GetUnitTestName());

    ASSERT_TRUE(table.size() >= 5);  // header, two subheaders and two lines
    EXPECT_EQ(table[0] + "\n", section::MakeHeader(kWmiCpuLoad, wmi::kSepChar));

    for (const auto section :
         {kSubSectionSystemPerf, kSubSectionComputerSystem}) {
        auto header = section::MakeSubSectionHeader(section);
        header.pop_back();
        EXPECT_TRUE(
            rs::any_of(table, [header](auto const &e) { return e == header; }));
    }
}

}  // namespace cma::provider
