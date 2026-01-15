// test-section_processor.cpp

//
#include "pch.h"

#include <numeric>
#include <ranges>

#include "common/wtools.h"
#include "tools/_misc.h"
#include "tools/_raii.h"
#include "watest/test_tools.h"
#include "wnx/carrier.h"
#include "wnx/cfg.h"
#include "wnx/service_processor.h"
using namespace std::chrono_literals;
namespace rs = std::ranges;
namespace fs = std::filesystem;

namespace cma::provider {
class Empty final : public Synchronous {
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
    auto s1 = sp.generate<provider::CheckMk>();
    auto t1 = tools::SplitString(s1, "\n");
    EXPECT_FALSE(t1.empty());

    auto s2 = sp.generate<provider::SystemTime>();
    auto t2 = tools::SplitString(s2, "\n");
    EXPECT_FALSE(t2.empty());

    auto s3 = sp.generate<provider::Empty>();
    auto t3 = tools::SplitString(s3, "\n");
    EXPECT_TRUE(t3.empty());

    AsyncAnswer::DataBlock db;
    auto ret = sp.wrapResultWithStaticSections(db);
    ret.push_back(0);
    std::string data = reinterpret_cast<const char *>(ret.data());
    ASSERT_TRUE(ret.size() > 5);
    auto t = tools::SplitString(data, "\n");
    EXPECT_EQ(t[0] + "\n", section::MakeHeader(section::kCheckMk));
    EXPECT_EQ(t[t.size() - 2] + "\n", section::MakeHeader(section::kSystemTime))
        << "data:\n"
        << data;
}

TEST(ServiceProcessorTest, StartStopExe) {
    int counter = 0;
    auto temp_fs{tst::TempCfgFs::CreateNoIo()};
    ASSERT_TRUE(temp_fs->loadContent(tst::GetFabricYmlContent()));

    auto processor = new ServiceProcessor(100ms, [&counter] {
        counter++;
        return true;
    });
    ON_OUT_OF_SCOPE(delete processor);

    mailslot::Slot mailbox(cfg::kTestingMailSlot, 0);
    mailbox.ConstructThread(SystemMailboxCallback, 20, processor,
                            wtools::SecurityLevel::admin);
    ON_OUT_OF_SCOPE(mailbox.DismantleThread());
    processor->internal_port_ = carrier::BuildPortName(
        carrier::kCarrierMailslotName, mailbox.GetName());

    auto tp = processor->openAnswer("127.0.0.1");

    // make command line
    auto cmd_line = cfg::groups::g_winperf.buildCmdLine();
    ASSERT_TRUE(!cmd_line.empty());
    auto count = cfg::groups::g_winperf.countersCount();
    auto count_of_colon = rs::count(cmd_line, L':');
    auto count_of_spaces = rs::count(cmd_line, L' ');
    ASSERT_TRUE(count_of_colon == count);
    ASSERT_EQ(count_of_spaces, count - 1);

    auto exe_name = cfg::groups::g_winperf.exe();
    ASSERT_TRUE(!exe_name.empty());
    auto wide_exe_name = wtools::ConvertToUtf16(exe_name);
    auto prefix = cfg::groups::g_winperf.prefix();
    ASSERT_TRUE(!prefix.empty());
    auto wide_prefix = wtools::ConvertToUtf16(prefix);

    processor->kickExe(true, wide_exe_name, tp.value(), processor, wide_prefix,
                       10, cmd_line);

    auto result = processor->getAnswer(1);
    EXPECT_TRUE(!result.empty());
}

namespace {
void DisableUptime() {
    auto cfg = cfg::GetLoadedConfig();
    cfg["global"]["disabled_sections"] = YAML::Load("[uptime]");
    cfg::ProcessKnownConfigGroups();
}
}  // namespace

TEST(ServiceProcessorTest, Base) {
    const tst::TempFolder folder{test_info_->name()};
    auto tmp = folder.path();
    tmp /= "out.txt";

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
    ServiceProcessor sp_2;
    EXPECT_TRUE(sp_2.max_wait_time_ == 0);
    sp_2.checkMaxWaitTime();
    EXPECT_EQ(sp_2.max_wait_time_, cfg::kDefaultAgentMinWait);

    auto temp_fs{tst::TempCfgFs::CreateNoIo()};
    ASSERT_TRUE(temp_fs->loadContent(tst::GetFabricYmlContent()));

    SectionProvider<provider::UptimeSync> uptime_provider;
    AsyncAnswer a;
    a.prepareAnswer("aaa");

    // STEP 1
    sp.internal_port_ = carrier::BuildPortName(carrier::kCarrierFileName,
                                               wtools::ToUtf8(tmp.wstring()));
    sp.tryToDirectCall(uptime_provider, a.getId(), "0");
    auto table = tst::ReadFileAsTable(wtools::ToUtf8(tmp.wstring()));
    ASSERT_EQ(table.size(), 2);
    EXPECT_EQ(table[0] + "\n", section::MakeHeader(section::kUptimeName));
    fs::remove(tmp);
    // STEP 2
    DisableUptime();
    sp.internal_port_ = carrier::BuildPortName(carrier::kCarrierFileName,
                                               wtools::ToUtf8(tmp.wstring()));
    sp.tryToDirectCall(uptime_provider, a.getId(), "0");
    EXPECT_TRUE(tst::ReadFileAsTable(wtools::ToUtf8(tmp.wstring())).empty());
}

namespace {
struct MailData {
    std::vector<char> data;
};

bool MailboxCallback(const cma::mailslot::Slot *slot, const void *data, int len,
                     void *context) {
    auto mail_data = static_cast<MailData *>(context);
    mail_data->data =
        std::vector(static_cast<const char *>(data),
                    static_cast<const char *>(data) + static_cast<size_t>(len));
    return true;
}
}  // namespace

// TODO(sk): move this function in test_tools
/// Not easy to test
std::optional<uint16_t> findFreePort(uint16_t start, uint16_t range) {
    for (auto port_num = start; port_num < start + range; ++port_num) {
        asio::ip::tcp::endpoint ep(asio::ip::address_v6::any(), port_num);
        asio::io_context context;
        try {
            asio::ip::tcp::acceptor acceptor(context, ep.protocol());
            acceptor.bind(ep);
            return port_num;
        } catch (std::exception &) {
            // not available
        }
    }

    return {};
}

class ServiceProcessorTestFixture : public ::testing::Test {
public:
    void SetUp() override {
        temp_fs = tst::TempCfgFs::CreateNoIo();
        const auto port = findFreePort(21550, 100);
        ASSERT_TRUE(port.has_value());
        ASSERT_TRUE(
            temp_fs->loadContent(fmt::format("global:\n"
                                             "  enabled: yes\n"
                                             "  sections: check_mk\n"
                                             "  port: {}\n"
                                             "system:\n"
                                             "  controller:\n"
                                             "    agent_channel: mailslot\n",
                                             *port)));
        mailbox.ConstructThread(MailboxCallback, 20, &md,
                                wtools::SecurityLevel::standard);
        sp.startService();
        ASSERT_TRUE(
            tst::WaitForSuccessSilent(1000ms, [this] { return ready; }));
    }
    void TearDown() override {
        cc.shutdownCommunication();
        sp.stopService(wtools::StopMode::ignore);
        mailbox.DismantleThread();
    }
    tst::TempCfgFs::ptr temp_fs;
    MailData md;
    mailslot::Slot mailbox{mailslot::BuildMailSlotNameRoot() + "local_test"};
    const std::string cmd{
        fmt::format("monitoring_request:\n"
                    "  text: '127.0.0.1 {}'\n"
                    "  id: 0\n",
                    "local_test")};
    bool ready{false};
    ServiceProcessor sp{100ms, [this] {
                            ready = true;
                            return true;
                        }};
    carrier::CoreCarrier cc;
};
TEST_F(ServiceProcessorTestFixture, YamlOverMailSlotComponent) {
    ASSERT_TRUE(cc.establishCommunication(sp.getInternalPort()));
    cc.sendYaml("TestSite", cmd);
    tst::WaitForSuccessSilent(2000ms, [this] { return !md.data.empty(); });
    EXPECT_GE(md.data.size(), 100U);
    std::string s{md.data.data(), md.data.size()};
    EXPECT_TRUE(s.starts_with("<<<check_mk>>>"));
}

TEST(ServiceProcessorTest, DirectCallUptime) {
    const tst::TempFolder folder{test_info_->name()};
    auto tmp = folder.path();
    tmp /= "out.txt";

    SectionProvider<provider::UptimeSync> uptime_provider;
    AsyncAnswer a;
    a.prepareAnswer("aaa");
    uptime_provider.directCall(
        "0", a.getId(),
        carrier::BuildPortName(carrier::kCarrierFileName,
                               wtools::ToUtf8(tmp.wstring())));
    const auto table = tst::ReadFileAsTable(wtools::ToUtf8(tmp.wstring()));
    EXPECT_EQ(table.size(), 2);
    EXPECT_EQ(table[0] + "\n", section::MakeHeader(section::kUptimeName));
}

std::vector<std::string> getWmiCpuLoad(
    SectionProvider<provider::Wmi> &wmi_cpuload_provider, const fs::path &tmp,
    int attempts) {
    AsyncAnswer a;
    a.prepareAnswer("aaa");
    // In Windows wmi access to CPU data may fail we retry it three times
    for (int i = 0; i < attempts; i++) {
        wmi_cpuload_provider.directCall(
            "0", a.getId(),
            carrier::BuildPortName(carrier::kCarrierFileName,
                                   wtools::ToUtf8(tmp.wstring())));
        auto table = tst::ReadFileAsTable(wtools::ToUtf8(tmp.wstring()));
        if (table.size() >= 7) {
            return table;
        }
        XLOG::SendStringToStdio("?", XLOG::Colors::pink);
        tools::sleep(1000ms);
    }

    return {};
}

TEST(ServiceProcessorTest, DirectCallWmi) {
    const tst::TempFolder folder{test_info_->name()};
    auto tmp = folder.path();
    tmp /= "out.txt";

    SectionProvider<provider::Wmi> wmi_cpuload_provider{
        provider::kWmiCpuLoad, provider::wmi::kSepChar};
    const auto table = getWmiCpuLoad(wmi_cpuload_provider, tmp, 3);

    EXPECT_EQ(table[0] + "\n", section::MakeHeader(provider::kWmiCpuLoad,
                                                   provider::wmi::kSepChar));
    EXPECT_EQ(table[1] + "\n",
              section::MakeSubSectionHeader(provider::kSubSectionSystemPerf));
    EXPECT_EQ(table[4] + "\n", section::MakeSubSectionHeader(
                                   provider::kSubSectionComputerSystem));
}

TEST(ServiceProcessorTest, FindWinPerfDefault) {
    const auto temp_fs = tst::TempCfgFs::Create();
    ASSERT_TRUE(temp_fs->loadFactoryConfig());
    tst::CreateTextFile(temp_fs->root() / "check-mk-service32.exe", "");
    EXPECT_TRUE(FindWinPerfExe("agent").empty());
    tst::CreateTextFile(temp_fs->root() / "check_mk_service32.exe", "");
    EXPECT_EQ(FindWinPerfExe("agent"),
              temp_fs->root() / "check_mk_service32.exe");
    tst::CreateTextFile(temp_fs->root() / "check_mk_agent.exe", "");
    EXPECT_EQ(FindWinPerfExe("agent"), temp_fs->root() / "check_mk_agent.exe");
}

TEST(ServiceProcessorTest, FindWinPerfCustom) {
    EXPECT_TRUE(FindWinPerfExe("agent").empty());
    EXPECT_EQ(FindWinPerfExe("agent.exe"), "agent.exe");
}

}  // namespace cma::srv
