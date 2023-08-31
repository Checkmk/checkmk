// Testing external port

// TODO
//
#include "pch.h"

#include <numeric>

#include "common/mailslot_transport.h"
#include "watest/test_tools.h"
#include "wnx/agent_controller.h"
#include "wnx/asio.h"
#include "wnx/carrier.h"
#include "wnx/external_port.h"
#include "wnx/realtime.h"

using namespace std::chrono_literals;
using namespace std::string_literals;
namespace views = std::views;
namespace rs = std::ranges;
using asio::ip::tcp;

namespace wtools {
class TestProcessor2 final : public wtools::BaseServiceProcessor {
public:
    TestProcessor2() { s_counter++; }
    ~TestProcessor2() override { s_counter--; }

    // Standard Windows API to Service hit here
    void stopService(wtools::StopMode /*stop_mode*/) override {
        stopped_ = true;
    }
    void startService() override { started_ = true; }
    void pauseService() override { paused_ = true; }
    void continueService() override { continued_ = true; }
    void shutdownService(wtools::StopMode /*stop_mode*/) override {
        shutdowned_ = true;
    }
    [[nodiscard]] const wchar_t *getMainLogName() const override {
        return L"log.log";
    }

    wtools::InternalUsersDb *getInternalUsers() override { return nullptr; }

    bool stopped_ = false;
    bool started_ = false;
    bool paused_ = false;
    bool shutdowned_ = false;
    bool continued_ = false;
    static int s_counter;
};
int TestProcessor2::s_counter = 0;
}  // namespace wtools

namespace cma::world {

TEST(ExternalPortTest, StartStop) {
    world::ReplyFunc reply =
        [](const std::string & /*ip */) -> std::vector<uint8_t> { return {}; };
    wtools::TestProcessor2 tp;
    world::ExternalPort test_port(&tp);  //

    ExternalPort::IoParam io_param{
        .port = tst::TestPort(),
        .local_only = LocalOnly::yes,
        .pid = 0U,
    };
    EXPECT_TRUE(test_port.startIo(reply, io_param));
    EXPECT_TRUE(test_port.isIoStarted());
    EXPECT_FALSE(test_port.startIo(reply, io_param));

    EXPECT_TRUE(tst::WaitForSuccessSilent(
        1000ms, [&test_port] { return test_port.isIoStarted(); }));

    cma::tools::sleep(50);
    test_port.shutdownIo();  // this is long operation
    EXPECT_FALSE(test_port.isIoStarted());
}

class ExternalPortCheckProcessFixture : public ::testing::Test {
public:
    ReplyFunc reply = [this](const std::string &ip) -> std::vector<uint8_t> {
        this->remote_ip = ip;
        return {};
    };
    void SetUp() override {
        temp_fs = tst::TempCfgFs::CreateNoIo();
        ASSERT_TRUE(temp_fs->loadFactoryConfig());
    }
    void TearDown() override { remote_ip.clear(); }
    std::string remote_ip;
    wtools::TestProcessor2 tp;
    world::ExternalPort test_port{&tp};
    const std::string text{"abcdef"};
    [[nodiscard]] size_t writeToSocket(uint16_t port) const {
        asio::io_context ios;
        tcp::endpoint endpoint{asio::ip::make_address("127.0.0.1"), port};
        tcp::socket socket{ios};
        asio::error_code ec;
        socket.connect(endpoint, ec);
        if (ec) {
            fmt::print("connect: '{}'  [{}]\n", ec.message(), ec.value());
            return 0;
        }
        auto count = socket.write_some(asio::buffer(text, 6), ec);
        if (ec) {
            fmt::print("write: '{}'  [{}]\n", ec.message(), ec.value());
            return 0;
        }
        socket.close();
        return count;
    }
    tst::TempCfgFs::ptr temp_fs;
    void disableElevatedAllowed() const {
        auto cfg = cfg::GetLoadedConfig();
        cfg[cfg::groups::kSystem][cfg::vars::kController]
           [cfg::vars::kControllerAllowElevated] = YAML::Load("no");
    }
};

namespace {
ExternalPort::IoParam makeIoParam(std::optional<uint32_t> pid) {
    return {
        .port = tst::TestPort(),
        .local_only = LocalOnly::yes,
        .pid = pid,
    };
}
}  // namespace

TEST_F(ExternalPortCheckProcessFixture, AnyProcessComponent) {
    disableElevatedAllowed();
    EXPECT_TRUE(test_port.startIo(reply, makeIoParam({})));

    EXPECT_EQ(writeToSocket(tst::TestPort()), 6U);
    tst::WaitForSuccessSilent(100ms, [this] { return !remote_ip.empty(); });
    test_port.shutdownIo();  // this is long operation
    EXPECT_EQ(remote_ip, text);
}

TEST_F(ExternalPortCheckProcessFixture, InvalidProcessComponent) {
    disableElevatedAllowed();
    EXPECT_TRUE(test_port.startIo(reply, makeIoParam(1)));

    EXPECT_EQ(writeToSocket(tst::TestPort()), 6U);
    std::this_thread::sleep_for(300ms);
    test_port.shutdownIo();  // this is long operation
    EXPECT_TRUE(remote_ip.empty());
}

TEST_F(ExternalPortCheckProcessFixture, InvalidProcessDefaultComponent) {
    EXPECT_TRUE(test_port.startIo(reply, makeIoParam(1)));

    EXPECT_EQ(writeToSocket(tst::TestPort()), 6U);
    tst::WaitForSuccessSilent(100ms, [this] { return !remote_ip.empty(); });
    test_port.shutdownIo();  // this is long operation
    EXPECT_EQ(remote_ip, text);
}

TEST_F(ExternalPortCheckProcessFixture, ValidProcessComponent) {
    disableElevatedAllowed();
    EXPECT_TRUE(test_port.startIo(reply, makeIoParam(::GetCurrentProcessId())));

    EXPECT_EQ(writeToSocket(tst::TestPort()), 6U);
    tst::WaitForSuccessSilent(100ms, [this] { return !remote_ip.empty(); });
    test_port.shutdownIo();  // this is long operation
    EXPECT_EQ(remote_ip, text);
}

class ExternalPortTestFixture : public ::testing::Test {
public:
    ReplyFunc reply = [this](const std::string & /*ip*/) {
        std::vector<uint8_t> data(this->reply_text_.begin(),
                                  this->reply_text_.end());
        if (this->delay_) {
            std::this_thread::sleep_for(50ms);
        }

        return data;
    };
    void SetUp() override {
        test_port_.startIo(
            reply,
            {.port = tst::TestPort(), .local_only = LocalOnly::no, .pid = 0U});
    }

    void TearDown() override {
        sock_.close();
        test_port_.shutdownIo();
    }

    std::string readSock() {
        asio::error_code error;
        char text[256];
        auto count = sock_.read_some(asio::buffer(text), error);
        text[count] = 0;
        return text;
    }

    const std::string_view reply_text_{"I am test\r\n"};
    world::ExternalPort test_port_{nullptr};
    tcp::endpoint endpoint_{asio::ip::make_address("127.0.0.1"),
                            tst::TestPort()};

    asio::io_context ios_;
    tcp::socket sock_{ios_};
    bool delay_{false};
};

TEST_F(ExternalPortTestFixture, ReadComponent) {
    tst::FirewallOpener fwo;
    ASSERT_TRUE(tst::WaitForSuccessSilent(1000ms, [this] {
        std::error_code ec;
        this->sock_.connect(this->endpoint_, ec);
        return ec.value() == 0;
    }));

    auto info = GetSocketInfo(sock_);
    EXPECT_EQ(info.peer_ip, "127.0.0.1");
    EXPECT_NE(info.peer_port, 0U);
    EXPECT_EQ(info.ip_mode, IpMode::ipv4);

    auto text = readSock();
    EXPECT_EQ(reply_text_, text);
}

class ExternalPortQueueFixture : public ::testing::Test {
public:
    void TearDown() override { test_port_.shutdownIo(); }
    void putSessionsInPort() {
        for (int i = 0; i < 32; i++) {
            asio::ip::tcp::socket s(io_);
            sessions_.emplace_back(std::make_shared<AsioSession>(std::move(s)));
        }

        for (const auto &as : sessions_) {
            test_port_.putOnQueue(as);
        }
    }
    void putRequestsInPort() {
        std::array<std::string, kMaxSessionQueueLength * 2U> commands;
        int cur = 0;
        std::ranges::generate(
            commands, [&cur] { return fmt::format("{} comment", cur++); });
        for (const auto &c : commands) {
            test_port_.putOnQueue(c);
        }
    }
    ExternalPort test_port_{nullptr};
    asio::io_context io_;
    std::vector<AsioSession::s_ptr> sessions_;
    std::vector<std::string> result_;
};

TEST_F(ExternalPortQueueFixture, FillAndConsumeAsioSessions) {
    EXPECT_EQ(test_port_.entriesInQueue(), 0);
    putSessionsInPort();
    EXPECT_EQ(test_port_.entriesInQueue(), kMaxSessionQueueLength);

    test_port_.startIoTcpPort(
        [](const std::string & /*_*/) { return std::vector<uint8_t>{}; },
        10000);
    EXPECT_TRUE(tst::WaitForSuccessSilent(
        1000ms, [this] { return test_port_.entriesInQueue() == 0; }));
}

TEST_F(ExternalPortQueueFixture, FillAndConsumeMailSlotRequests) {
    putRequestsInPort();
    EXPECT_EQ(test_port_.entriesInQueue(), kMaxSessionQueueLength);

    test_port_.startIo(
        [this](const std::string &r) {
            result_.emplace_back(r);
            return std::vector<uint8_t>{};
        },
        ExternalPort::IoParam{
            .port = 0U,
            .local_only = LocalOnly::no,
            .pid = ::GetCurrentProcessId(),
        });
    EXPECT_TRUE(tst::WaitForSuccessSilent(
        1000ms, [this] { return test_port_.entriesInQueue() == 0; }));
    EXPECT_EQ(std::accumulate(result_.begin(), result_.end(), ""s),
              "0123456789101112131415"s);
}

namespace {
size_t g_count{0};
std::mutex g_lock;
void runThread(uint16_t port) {
    asio::io_context ios;
    tcp::endpoint endpoint(asio::ip::make_address("127.0.0.1"), port);

    tcp::socket socket(ios);

    EXPECT_NO_THROW(socket.connect(endpoint));

    asio::error_code error;
    char text[256];
    auto count = socket.read_some(asio::buffer(text), error);
    socket.close();

    std::lock_guard lk(g_lock);
    g_count += count;
}
}  // namespace

TEST_F(ExternalPortTestFixture, MultiConnectComponent) {
    tst::FirewallOpener fwo;
    constexpr int thread_count{8};
    delay_ = true;

    std::vector<std::future<void>> futures;
    for (int i = 0; i < thread_count; ++i) {
        futures.push_back(
            std::async(std::launch::async, runThread, tst::TestPort()));
    }

    for (auto &f : futures) {
        f.get();
    }

    EXPECT_EQ(g_count, thread_count * 11);
}

namespace {
const std::string base{
    "controller:\n"
    "  run: {}\n"};

const std::pair<std::string, bool> ip_allowed[] = {
    {"127.0.0.1", true},
    {"::1", true},
    {"127.0.0.2", false},
};
}  // namespace

TEST(ExternalPortTest, IsIpAllowedAsExceptionYes) {
    auto test_fs = tst::TempCfgFs::CreateNoIo();
    cfg::GetLoadedConfig()[cfg::groups::kSystem] =
        YAML::Load(fmt::format(fmt::runtime(base), "yes"));
    for (const auto &[ip, allowed] : ip_allowed) {
        EXPECT_EQ(IsIpAllowedAsException(ip), allowed);
    }
}

TEST(ExternalPortTest, IsIpAllowedAsExceptionNo) {
    auto test_fs = tst::TempCfgFs::CreateNoIo();
    cfg::GetLoadedConfig()[cfg::groups::kSystem] =
        YAML::Load(fmt::format(fmt::runtime(base), "no"));
    for (const auto &ip : ip_allowed | std::views::keys) {
        EXPECT_FALSE(IsIpAllowedAsException(ip));
    }
}

class ExternalPortMailSlotFixture : public ::testing::Test {
public:
    static bool MailboxCallback(const mailslot::Slot * /*slot*/,
                                const void *data, int len, void *context) {
        auto storage = static_cast<std::vector<uint8_t> *>(context);

        const auto *d = static_cast<const uint8_t *>(data);
        storage->assign(d, d + len);

        return true;
    }
    void SetUp() override {
        temp_fs = tst::TempCfgFs::CreateNoIo();
        ASSERT_TRUE(temp_fs->loadFactoryConfig());
        mailbox_.ConstructThread(&ExternalPortMailSlotFixture::MailboxCallback,
                                 20, &result_, wtools::SecurityLevel::admin);
        std::this_thread::sleep_for(100ms);  // wait for thread start
    }

    void TearDown() override { mailbox_.DismantleThread(); }

    tst::TempCfgFs::ptr temp_fs;
    mailslot::Slot mailbox_{"WinAgentExternalPortTest",
                            ::GetCurrentProcessId()};
    std::vector<uint8_t> result_;
    std::vector<uint8_t> data_ = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9};
    void wait_for_effect() {
        std::this_thread::sleep_for(100ms);  // wait for thread
        tst::WaitForSuccessSilent(2000ms, [this] { return !result_.empty(); });
    }

    std::tuple<std::vector<uint8_t>, std::vector<uint8_t>> split_result()
        const {
        std::vector h(result_.begin(), result_.begin() + 2);
        std::vector r(result_.begin() + 2, result_.end());
        return {h, r};
    }
};

TEST_F(ExternalPortMailSlotFixture, NonEncryptedComponent) {
    EXPECT_TRUE(SendDataToMailSlot(mailbox_.GetName(), data_, nullptr));
    wait_for_effect();
    EXPECT_EQ(data_, result_);
}

TEST_F(ExternalPortMailSlotFixture, EncryptedComponent) {
    const auto commander = std::make_unique<encrypt::Commander>("aa");
    ASSERT_TRUE(SendDataToMailSlot(mailbox_.GetName(), data_, commander.get()));
    wait_for_effect();
    auto [h, r] = split_result();
    ASSERT_EQ(h[0], rt::kEncryptedHeader[0]);
    ASSERT_EQ(h[1], rt::kEncryptedHeader[1]);
    const auto [success, sz] = commander->decode(r.data(), r.size());
    EXPECT_TRUE(success);
    EXPECT_TRUE(rs::equal(views::take(r, sz), views::all(data_)));
}

}  // namespace cma::world
