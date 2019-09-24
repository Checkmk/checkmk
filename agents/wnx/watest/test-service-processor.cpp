// test-section_processor.cpp

//
#include "pch.h"

#include "carrier.h"
#include "cfg.h"
#include "common/wtools.h"
#include "service_processor.h"
#include "test_tools.h"
#include "tools/_misc.h"
#include "tools/_process.h"

namespace cma::srv {

TEST(AsyncAnswerTest, Base) {
    AsyncAnswer aa;
    EXPECT_EQ(aa.order_, AsyncAnswer::Order::plugins_last);
    EXPECT_EQ(aa.sw_.isStarted(), false);
    aa.prepareAnswer("aaa");
    EXPECT_EQ(aa.sw_.isStarted(), true);

    EXPECT_EQ(aa.external_ip_, "aaa");
    EXPECT_EQ(aa.awaited_segments_, 0);
    EXPECT_EQ(aa.received_segments_, 0);
    EXPECT_TRUE(aa.data_.empty());
    EXPECT_TRUE(aa.segments_.empty());
    EXPECT_TRUE(aa.plugins_.empty());
    EXPECT_TRUE(aa.local_.empty());
    EXPECT_FALSE(aa.prepareAnswer("aaa"));
    aa.external_ip_ = "";
    aa.awaited_segments_ = 1;
    EXPECT_FALSE(aa.prepareAnswer("aaa"));
    aa.external_ip_ = "";
    aa.awaited_segments_ = 0;
    aa.received_segments_ = 1;
    EXPECT_FALSE(aa.prepareAnswer("aaa"));
}

TEST(ServiceControllerTest, StartStopExe) {
    using namespace cma::srv;
    using namespace cma::cfg;
    using namespace std::chrono;
    int counter = 0;
    auto processor =
        new ServiceProcessor(100ms, [&counter](const void* Processor) {
            xlog::l("pip").print();
            counter++;
            return true;
        });
    ON_OUT_OF_SCOPE(delete processor;);

    cma::MailSlot mailbox(kServiceMailSlot, 0);
    mailbox.ConstructThread(SystemMailboxCallback, 20, processor);
    ON_OUT_OF_SCOPE(mailbox.DismantleThread());
    using namespace cma::carrier;
    processor->internal_port_ =
        BuildPortName(kCarrierMailslotName, mailbox.GetName());

    auto tp = processor->openAnswer("127.0.0.1");

    // make command line
    auto cmd_line = groups::winperf.buildCmdLine();
    ASSERT_TRUE(!cmd_line.empty());
    auto count = groups::winperf.countersCount();
    auto count_of_colon = std::count(cmd_line.begin(), cmd_line.end(), L':');
    auto count_of_spaces = std::count(cmd_line.begin(), cmd_line.end(), L' ');
    ASSERT_TRUE(count_of_colon == count);
    ASSERT_EQ(count_of_spaces, count - 1);

    auto exe_name = groups::winperf.exe();
    ASSERT_TRUE(!exe_name.empty());
    auto wide_exe_name = wtools::ConvertToUTF16(exe_name);
    auto prefix = groups::winperf.prefix();
    ASSERT_TRUE(!prefix.empty());
    auto wide_prefix = wtools::ConvertToUTF16(prefix);

    processor->kickExe(true, wide_exe_name, tp.value(), processor, wide_prefix,
                       10, cmd_line);

    auto result = processor->getAnswer(1);
    EXPECT_TRUE(!result.empty());
}

TEST(ServiceProcessorTest, Base) {
    OnStartTest();
    ServiceProcessor sp;
    EXPECT_TRUE(sp.max_wait_time_ == 0);
    sp.updateMaxWaitTime(-1);
    EXPECT_TRUE(sp.max_wait_time_ == 0);
    sp.updateMaxWaitTime(10);
    EXPECT_TRUE(sp.max_wait_time_ == 10);
    sp.updateMaxWaitTime(8);
    EXPECT_TRUE(sp.max_wait_time_ == 10);
    sp.updateMaxWaitTime(20);
    EXPECT_TRUE(sp.max_wait_time_ == 20);
    sp.updateMaxWaitTime(0);
    EXPECT_TRUE(sp.max_wait_time_ == 20);
    {
        ServiceProcessor sp;
        EXPECT_TRUE(sp.max_wait_time_ == 0);
        sp.checkMaxWaitTime();
        EXPECT_EQ(sp.max_wait_time_, cma::cfg::kDefaultAgentMinWait);
    }

    using namespace cma::section;
    using namespace cma::provider;
    tst::SafeCleanTempDir();
    ON_OUT_OF_SCOPE(tst::SafeCleanTempDir(););
    ON_OUT_OF_SCOPE(OnStartTest(););
    {
        std::filesystem::path tmp = cma::cfg::GetTempDir();
        tmp /= "out.txt";

        SectionProvider<provider::Uptime> uptime_provider;
        AsyncAnswer a;
        a.prepareAnswer("aaa");
        sp.internal_port_ = cma::carrier::BuildPortName(
            cma::carrier::kCarrierFileName, tmp.u8string());
        sp.tryToDirectCall(uptime_provider, a.getId(), "0");
        auto table = tst::ReadFileAsTable(tmp.u8string());
        EXPECT_EQ(table.size(), 2);
        EXPECT_EQ(table[0] + "\n", MakeHeader(cma::section::kUptimeName));
    }

    {
        std::filesystem::path tmp = cma::cfg::GetTempDir();
        tmp /= "out.txt";
        std::error_code ec;
        std::filesystem::remove(tmp, ec);

        auto cfg = cma::cfg::GetLoadedConfig();
        cfg["global"]["disabled_sections"] = YAML::Load("[uptime]");
        cfg::ProcessKnownConfigGroups();

        SectionProvider<provider::Uptime> uptime_provider;
        AsyncAnswer a;
        a.prepareAnswer("aaa");
        sp.internal_port_ = cma::carrier::BuildPortName(
            cma::carrier::kCarrierFileName, tmp.u8string());
        sp.tryToDirectCall(uptime_provider, a.getId(), "0");
        auto table = tst::ReadFileAsTable(tmp.u8string());
        EXPECT_TRUE(table.empty());
    }
}

TEST(ServiceProcessorTest, DirectCall) {
    using namespace cma::section;
    using namespace cma::provider;
    OnStartTest();
    tst::SafeCleanTempDir();
    ON_OUT_OF_SCOPE(tst::SafeCleanTempDir(););

    std::filesystem::path tmp = cma::cfg::GetTempDir();
    tmp /= "out.txt";
    {
        SectionProvider<provider::Uptime> uptime_provider;
        AsyncAnswer a;
        a.prepareAnswer("aaa");
        uptime_provider.directCall(
            "0", a.getId(),
            cma::carrier::BuildPortName(cma::carrier::kCarrierFileName,
                                        tmp.u8string()));
        auto table = tst::ReadFileAsTable(tmp.u8string());
        EXPECT_EQ(table.size(), 2);
        EXPECT_EQ(table[0] + "\n", MakeHeader(cma::section::kUptimeName));
    }

    {
        SectionProvider<provider::Wmi> wmi_cpuload_provider{kWmiCpuLoad,
                                                            wmi::kSepChar};
        AsyncAnswer a;
        a.prepareAnswer("aaa");
        wmi_cpuload_provider.directCall(
            "0", a.getId(),
            cma::carrier::BuildPortName(cma::carrier::kCarrierFileName,
                                        tmp.u8string()));
        auto table = tst::ReadFileAsTable(tmp.u8string());
        EXPECT_EQ(table.size(), 7);
        EXPECT_EQ(table[0] + "\n",
                  cma::section::MakeHeader(cma::provider::kWmiCpuLoad,
                                           cma::provider::wmi::kSepChar));

        EXPECT_EQ(table[1] + "\n", cma::section::MakeSubSectionHeader(
                                       cma::provider::kSubSectionSystemPerf));
        EXPECT_EQ(table[4] + "\n",
                  cma::section::MakeSubSectionHeader(
                      cma::provider::kSubSectionComputerSystem));
    }
}

}  // namespace cma::srv
