// test-section_wmi.cpp

//
#include "pch.h"

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

namespace wtools {

TEST(WmiWrapper, EnumeratorOnly) {
    using namespace std;
    {
        wtools::InitWindowsCom();
        if (!wtools::IsWindowsComInitialized()) {
            XLOG::l.crit("COM faaaaaaaiiled");
            return;
        }
        ON_OUT_OF_SCOPE(wtools::CloseWindowsCom());

        WmiWrapper wmi;
        wmi.open();
        wmi.connect(L"ROOT\\CIMV2");
        wmi.impersonate();
        // Use the IWbemServices pointer to make requests of WMI.
        // Make requests here:
        auto result = wmi.queryEnumerator({}, L"Win32_Process");
        ON_OUT_OF_SCOPE(if (result) result->Release(););
        EXPECT_TRUE(result != nullptr);

        ULONG returned = 0;
        IWbemClassObject* wmi_object = nullptr;
        auto hres = result->Next(WBEM_INFINITE, 1, &wmi_object, &returned);
        EXPECT_EQ(hres, 0);
        EXPECT_NE(returned, 0);

        auto header = wtools::WmiGetNamesFromObject(wmi_object);
        EXPECT_TRUE(header.size() > 20);
        EXPECT_EQ(header[0], L"Caption");
        EXPECT_EQ(header[1], L"CommandLine");
    }
}

TEST(WmiWrapper, Table) {
    using namespace std;
    {
        wtools::InitWindowsCom();
        if (!wtools::IsWindowsComInitialized()) {
            XLOG::l.crit("COM faaaaaaaiiled");
            return;
        }
        ON_OUT_OF_SCOPE(wtools::CloseWindowsCom());

        WmiWrapper wmi;
        wmi.open();
        wmi.connect(L"ROOT\\CIMV2");
        wmi.impersonate();
        // Use the IWbemServices pointer to make requests of WMI.
        // Make requests here:
        auto result = wmi.queryTable({}, L"Win32_Process");
        ASSERT_TRUE(!result.empty());
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
        auto last_line = cma::tools::SplitString(table[table.size() - 1], L",");
        EXPECT_EQ(line1.size(), last_line.size());
    }
}

}  // namespace wtools

namespace cma::provider {

TEST(ProviderTest, WmiBadName) {  //
    using namespace std::chrono;

    cma::OnStart(cma::AppType::test);
    {
        Wmi badname("badname");
        EXPECT_EQ(badname.object(), L"");
        EXPECT_EQ(badname.nameSpace(), L"");
        EXPECT_FALSE(badname.isAllowedByCurrentConfig());
        EXPECT_TRUE(badname.isAllowedByTime());
    }
    {
        Wmi x("badname", '.');
        x.registerCommandLine("1.1.1.1 wefwef rfwrwer rwerw");
        EXPECT_EQ(x.ip(), "1.1.1.1");
    }
}

TEST(ProviderTest, WmiAll) {  //
    using namespace std::chrono;
    {
        auto r = GenerateTable(cma::provider::kWmiPathStd,
                               L"Win32_ComputerSystem", {});
        EXPECT_TRUE(!r.empty());
    }

    {
        auto r = GenerateTable(cma::provider::kWmiPathStd,
                               L"Win32_ComputerSystemZ", {});
        EXPECT_TRUE(r.empty());
    }

    {
        auto r = GenerateTable(std::wstring(cma::provider::kWmiPathStd) + L"A",
                               L"Win32_ComputerSystem", {});
        EXPECT_TRUE(r.empty());
    }

    {
        Wmi dotnet_clr(kDotNetClrMemory);
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

        auto header = cma::tools::SplitString(table[0], ",");
        EXPECT_EQ(header[0], "AllocatedBytesPersec");
        EXPECT_EQ(header[13], "Name");

        auto line1 = cma::tools::SplitString(table[1], ",");
        EXPECT_EQ(line1.size(), header.size());
    }

    {
        Wmi wmi_web(kWmiWebservices);
        EXPECT_EQ(wmi_web.delay_on_fail_, cma::cfg::G_DefaultDelayOnFail);

        EXPECT_EQ(wmi_web.object(), L"Win32_PerfRawData_W3SVC_WebService");
        EXPECT_EQ(wmi_web.nameSpace(), L"Root\\Cimv2");
        auto body = wmi_web.makeBody();
        EXPECT_TRUE(wmi_web.isAllowedByCurrentConfig());
        EXPECT_TRUE(wmi_web.isAllowedByTime());
        EXPECT_EQ(wmi_web.delay_on_fail_, 3600s);
    }

    {
        Wmi ohm(kOhm);
        EXPECT_EQ(ohm.object(), L"Sensor");
        EXPECT_EQ(ohm.nameSpace(), L"Root\\OpenHardwareMonitor");
        EXPECT_EQ(ohm.columns().size(), 5);
        auto body = ohm.makeBody();
        EXPECT_TRUE(!ohm.isAllowedByCurrentConfig());
        tst::EnableSectionsNode(cma::provider::kOhm);
        EXPECT_TRUE(ohm.isAllowedByCurrentConfig());
        ON_OUT_OF_SCOPE(cma::OnStart(cma::AppType::test));
        EXPECT_TRUE(ohm.isAllowedByTime());
    }

    {
        Wmi cpu(kWmiCpuLoad);
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
        Wmi msexch(kMsExch);
        EXPECT_EQ(msexch.delay_on_fail_, cma::cfg::G_DefaultDelayOnFail);
        // this is empty section
        EXPECT_EQ(msexch.object(), L"");
        EXPECT_EQ(msexch.nameSpace(), L"");
        EXPECT_EQ(msexch.columns().size(), 0);

        // sub section count
        const int count = 7;
        auto& subs = msexch.sub_objects_;
        EXPECT_EQ(subs.size(), count);
        EXPECT_EQ(subs[0].getUniqName(), "msexch_activesync");
        EXPECT_EQ(subs[1].getUniqName(), "msexch_availability");
        EXPECT_EQ(subs[2].getUniqName(), "msexch_owa");
        EXPECT_EQ(subs[3].getUniqName(), "msexch_autodiscovery");
        EXPECT_EQ(subs[4].getUniqName(), "msexch_isclienttype");
        EXPECT_EQ(subs[5].getUniqName(), "msexch_isstore");
        EXPECT_EQ(subs[6].getUniqName(), "msexch_rpcclientaccess");

        for (auto& sub : subs) {
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

TEST(ProviderTest, WmiDotnet) {
    using namespace cma::section;
    using namespace cma::provider;
    namespace fs = std::filesystem;

    auto wmi_name = kDotNetClrMemory;
    fs::path f(FNAME_USE);
    fs::remove(f);

    cma::srv::SectionProvider<Wmi> wmi_provider(wmi_name, ',');
    EXPECT_EQ(wmi_provider.getEngine().getUniqName(), wmi_name);

    auto& e2 = wmi_provider.getEngine();
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
    e2.startSynchronous("file:" FNAME_USE, cmd_line);

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

TEST(ProviderTest, BasicWmi) {
    using namespace std::chrono;
    Wmi b("a", ',');
    auto old_time = b.allowed_from_time_;
    b.delay_on_fail_ = 900s;
    b.updateDelayTime();
    auto new_time = b.allowed_from_time_;
    auto delta = new_time - old_time;
    EXPECT_TRUE(delta >= 900s);
}

TEST(ProviderTest, WmiMsExch) {
    using namespace cma::section;
    using namespace cma::provider;
    namespace fs = std::filesystem;

    auto wmi_name = kMsExch;
    fs::path f(FNAME_USE);
    fs::remove(f);

    cma::srv::SectionProvider<Wmi> wmi_provider(wmi_name, ',');
    EXPECT_EQ(wmi_provider.getEngine().getUniqName(), wmi_name);

    auto& e2 = wmi_provider.getEngine();
    EXPECT_TRUE(e2.isAllowedByCurrentConfig());
    EXPECT_TRUE(e2.isAllowedByTime());

    auto cmd_line = std::to_string(12345) + " " + wmi_name + " ";
    e2.startSynchronous("file:" FNAME_USE, cmd_line);

    std::error_code ec;
    ASSERT_TRUE(fs::exists(f, ec));
    auto table = ReadFileAsTable(f.u8string());
    if (table.empty()) {
        EXPECT_FALSE(e2.isAllowedByTime());
    } else {
        ASSERT_TRUE(table.size() > 1);  // more than 1 line should be present
        EXPECT_EQ(table[0] + "\n", cma::section::MakeHeader(wmi_name, ','));
    }
    fs::remove(f);
}

TEST(ProviderTest, WmiWeb) {
    using namespace cma::section;
    using namespace cma::provider;
    namespace fs = std::filesystem;

    auto wmi_name = kWmiWebservices;
    fs::path f(FNAME_USE);
    fs::remove(f);

    cma::srv::SectionProvider<Wmi> wmi_provider(wmi_name, ',');
    EXPECT_EQ(wmi_provider.getEngine().getUniqName(), wmi_name);

    auto& e2 = wmi_provider.getEngine();
    EXPECT_TRUE(e2.isAllowedByCurrentConfig());
    EXPECT_TRUE(e2.isAllowedByTime());

    auto cmd_line = std::to_string(12345) + " " + wmi_name + " ";
    e2.startSynchronous("file:" FNAME_USE, cmd_line);

    std::error_code ec;
    ASSERT_TRUE(fs::exists(f, ec));
    auto table = ReadFileAsTable(f.u8string());
    if (table.empty()) {
        EXPECT_FALSE(e2.isAllowedByTime());
    } else {
        ASSERT_TRUE(table.size() > 1);  // more than 1 line should be present
        EXPECT_EQ(table[0] + "\n", cma::section::MakeHeader(wmi_name, ','));
    }
    fs::remove(f);
}
TEST(ProviderTest, WmiCpu) {
    using namespace cma::section;
    using namespace cma::provider;
    namespace fs = std::filesystem;

    auto wmi_name = kWmiCpuLoad;
    fs::path f(FNAME_USE);
    fs::remove(f);

    cma::srv::SectionProvider<Wmi> wmi_provider(wmi_name, ',');
    EXPECT_EQ(wmi_provider.getEngine().getUniqName(), wmi_name);

    auto& e2 = wmi_provider.getEngine();
    EXPECT_TRUE(e2.isAllowedByCurrentConfig());
    EXPECT_TRUE(e2.isAllowedByTime());
    auto data = e2.generateContent(section_name);
    EXPECT_TRUE(!data.empty());

    auto cmd_line = std::to_string(12345) + " " + wmi_name + " ";
    e2.startSynchronous("file:" FNAME_USE, cmd_line);

    std::error_code ec;
    ASSERT_TRUE(fs::exists(f, ec));
    auto table = ReadFileAsTable(f.u8string());
    ASSERT_TRUE(table.size() >= 5);  // header, two subheaders and two lines
    EXPECT_EQ(table[0] + "\n", cma::section::MakeHeader(wmi_name, ','));

    int system_perf_found = 0;
    int computer_system_found = 0;
    for (auto& entry : table) {
        if (entry + "\n" == MakeSubSectionHeader(kSubSectionSystemPerf))
            ++system_perf_found;
        if (entry + "\n" == MakeSubSectionHeader(kSubSectionComputerSystem))
            ++computer_system_found;
    }
    EXPECT_EQ(computer_system_found, 1);
    EXPECT_EQ(system_perf_found, 1);

    fs::remove(f);
}

}  // namespace cma::provider
