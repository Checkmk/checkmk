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
using namespace std::chrono_literals;

namespace cma::provider {
class Empty : public Synchronous {
public:
    Empty() : Synchronous("empty") {}
    std::string makeBody() override { return "****"; }
};
}  // namespace cma::provider

namespace cma::srv {

TEST(AsyncAnswerTest, Ctor) {
    AsyncAnswer aa;
    EXPECT_EQ(aa.getStopWatch().isStarted(), false);
    EXPECT_EQ(aa.awaitingSegments(), 0);
    EXPECT_EQ(aa.receivedSegments(), 0);
    EXPECT_FALSE(aa.isAnswerInUse());
    EXPECT_EQ(aa.getIp(), std::string{});
    EXPECT_GT(aa.getId().time_since_epoch().count(), 1000);
}

TEST(AsyncAnswerTest, Prepare) {
    AsyncAnswer aa;
    auto id = aa.getId();
    EXPECT_TRUE(aa.prepareAnswer("aaa"));
    EXPECT_NE(aa.getId(), id);
    EXPECT_EQ(aa.getIp(), "aaa");
    EXPECT_FALSE(aa.prepareAnswer("aaa"));
}

TEST(AsyncAnswerTest, Run) {
    AsyncAnswer aa;
    aa.prepareAnswer("aaa");
    aa.exeKickedCount(2);
    EXPECT_EQ(aa.getStopWatch().isStarted(), true);
    EXPECT_TRUE(aa.isAnswerInUse());
    EXPECT_EQ(aa.awaitingSegments(), 2);
    EXPECT_EQ(aa.receivedSegments(), 0);
}

TEST(AsyncAnswerTest, Timeout) {
    AsyncAnswer aa;
    EXPECT_GT(aa.timeout(), 0);
    aa.newTimeout(1000);
    EXPECT_EQ(aa.timeout(), 1000);
    aa.newTimeout(90);
    EXPECT_EQ(aa.timeout(), 1000);
}

class AsyncAnswerTestFixture : public ::testing::Test {
public:
    const int kicked_count{2};
    const std::string segment_name{"A"};
    void SetUp() override {
        aa.prepareAnswer("aaa");
        aa.exeKickedCount(kicked_count);
        aa.addSegment(segment_name, aa.getId(), db);
    }
    AsyncAnswer aa;
    AsyncAnswer::DataBlock db{0, 1};
    AsyncAnswer::DataBlock db_result{0, 1, '\n'};
    const std::vector<std::string> segments{segment_name};
};

TEST_F(AsyncAnswerTestFixture, Start) {
    EXPECT_EQ(aa.awaitingSegments(), kicked_count);
    EXPECT_EQ(aa.receivedSegments(), 1);
    EXPECT_EQ(aa.segmentNameList(), segments);
}

TEST_F(AsyncAnswerTestFixture, Receive) {
    EXPECT_EQ(aa.getDataAndClear(), db_result);
    EXPECT_EQ(aa.awaitingSegments(), 0);
    EXPECT_EQ(aa.receivedSegments(), 0);
    EXPECT_EQ(aa.getIp(), "");
}

TEST_F(AsyncAnswerTestFixture, Drop) {
    aa.dropAnswer();
    EXPECT_EQ(aa.getDataAndClear(), AsyncAnswer::DataBlock{});
    EXPECT_EQ(aa.awaitingSegments(), 0);
    EXPECT_EQ(aa.receivedSegments(), 0);
    EXPECT_EQ(aa.getIp(), "");
}

TEST_F(AsyncAnswerTestFixture, WaitFail) {
    EXPECT_FALSE(aa.waitAnswer(1ms));  // one segment should miss
}

TEST_F(AsyncAnswerTestFixture, WaitSuccess) {
    aa.addSegment("B", aa.getId(), db);
    EXPECT_TRUE(aa.waitAnswer(1ms));
}

TEST(ServiceProcessorTest, Generate) {
    ServiceProcessor sp;
    auto s1 = sp.generate<cma::provider::CheckMk>();
    auto t1 = cma::tools::SplitString(s1, "\n");
    ASSERT_FALSE(t1.empty());

    auto s2 = sp.generate<cma::provider::SystemTime>();
    auto t2 = cma::tools::SplitString(s2, "\n");
    ASSERT_FALSE(t2.empty());

    auto s3 = sp.generate<cma::provider::Empty>();
    auto t3 = cma::tools::SplitString(s3, "\n");
    ASSERT_TRUE(t3.empty());

    AsyncAnswer::DataBlock db;
    auto ret = sp.wrapResultWithStaticSections(db);
    ret.push_back(0);
    std::string data = reinterpret_cast<const char *>(ret.data());
    ASSERT_TRUE(ret.size() > 5);
    auto t = cma::tools::SplitString(data, "\n");
    EXPECT_EQ(t[0] + "\n", cma::section::MakeHeader(cma::section::kCheckMk));
    EXPECT_EQ(t[t.size() - 2] + "\n",
              cma::section::MakeHeader(cma::section::kSystemTime))
        << "data:\n"
        << data;
}

TEST(ServiceProcessorTest, StartStopExe) {
    using namespace cma::cfg;
    int counter = 0;
    auto temp_fs{tst::TempCfgFs::CreateNoIo()};
    ASSERT_TRUE(temp_fs->loadContent(tst::GetFabricYmlContent()));

    auto processor = new ServiceProcessor(100ms, [&counter]() {
        xlog::l("pip").print();
        counter++;
        return true;
    });
    ON_OUT_OF_SCOPE(delete processor;);

    cma::MailSlot mailbox(kTestingMailSlot, 0);
    mailbox.ConstructThread(SystemMailboxCallback, 20, processor,
                            wtools::SecurityLevel::admin);
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

        SectionProvider<provider::UptimeSync> uptime_provider;
        AsyncAnswer a;
        a.prepareAnswer("aaa");
        sp.internal_port_ = cma::carrier::BuildPortName(
            cma::carrier::kCarrierFileName, tmp.u8string());
        sp.tryToDirectCall(uptime_provider, a.getId(), "0");
        auto table = tst::ReadFileAsTable(tmp.u8string());
        ASSERT_EQ(table.size(), 2);
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

        SectionProvider<provider::UptimeSync> uptime_provider;
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
        SectionProvider<provider::UptimeSync> uptime_provider;
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
        std::vector<std::string> table;
        for (int i = 0; i < 3; i++) {
            wmi_cpuload_provider.directCall(
                "0", a.getId(),
                cma::carrier::BuildPortName(cma::carrier::kCarrierFileName,
                                            tmp.u8string()));
            table = tst::ReadFileAsTable(tmp.u8string());

            if (table.size() < 7) {
                using namespace std::chrono;
                XLOG::SendStringToStdio("?", XLOG::Colors::pink);
                cma::tools::sleep(1000ms);
                continue;
            }

            EXPECT_EQ(table[0] + "\n",
                      cma::section::MakeHeader(cma::provider::kWmiCpuLoad,
                                               cma::provider::wmi::kSepChar));

            EXPECT_EQ(table[1] + "\n",
                      cma::section::MakeSubSectionHeader(
                          cma::provider::kSubSectionSystemPerf));
            EXPECT_EQ(table[4] + "\n",
                      cma::section::MakeSubSectionHeader(
                          cma::provider::kSubSectionComputerSystem));
            return;
        }
        EXPECT_TRUE(false) << "CpuLoad returns not enough data, size = "
                           << table.size();
    }
}

}  // namespace cma::srv
