// Testing external port

// TODO
//
#include "pch.h"

#include <chrono>

#include "agent_controller.h"
#include "asio.h"
#include "external_port.h"
#include "test_tools.h"

using namespace std::chrono_literals;
using asio::ip::tcp;

namespace wtools {  // to become friendly for wtools classes
class TestProcessor2 : public wtools::BaseServiceProcessor {
public:
    TestProcessor2() { s_counter++; }
    virtual ~TestProcessor2() { s_counter--; }

    // Standard Windows API to Service hit here
    void stopService() { stopped_ = true; }
    void startService() { started_ = true; }
    void pauseService() { paused_ = true; }
    void continueService() { continued_ = true; }
    void shutdownService() { shutdowned_ = true; }
    const wchar_t *getMainLogName() const { return L"log.log"; }

    bool stopped_ = false;
    bool started_ = false;
    bool paused_ = false;
    bool shutdowned_ = false;
    bool continued_ = false;
    static int s_counter;
};  // namespace wtoolsclassTestProcessor:publiccma::srv::BaseServiceProcessor
int TestProcessor2::s_counter = 0;
}  // namespace wtools

namespace cma::world {  // to become friendly for wtools classes
#include <iostream>

TEST(ExternalPortTest, StartStop) {
    world::ReplyFunc reply =
        [](const std::string /*ip */) -> std::vector<uint8_t> { return {}; };
    wtools::TestProcessor2 tp;
    world::ExternalPort test_port(&tp);  //

    EXPECT_TRUE(
        test_port.startIo(reply, tst::TestPort(), world::LocalOnly::yes, {}));
    EXPECT_TRUE(test_port.io_thread_.joinable());
    EXPECT_FALSE(
        test_port.startIo(reply, tst::TestPort(), world::LocalOnly::yes, {}));

    EXPECT_TRUE(tst::WaitForSuccessSilent(
        1000ms, [&test_port]() { return test_port.io_thread_.joinable(); }));

    cma::tools::sleep(50);
    test_port.shutdownIo();  // this is long operation
    EXPECT_TRUE(!test_port.io_thread_.joinable());
}

class ExternalPortCheckProcessFixture : public ::testing::Test {
public:
    ReplyFunc reply = [this](const std::string ip) -> std::vector<uint8_t> {
        remote_ip = ip;
        return {};
    };
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
};

TEST_F(ExternalPortCheckProcessFixture, AnyProcess) {
    EXPECT_TRUE(
        test_port.startIo(reply, tst::TestPort(), world::LocalOnly::yes, {}));

    EXPECT_EQ(writeToSocket(tst::TestPort()), 6U);
    tst::WaitForSuccessSilent(100ms, [this]() { return !remote_ip.empty(); });
    test_port.shutdownIo();  // this is long operation
    EXPECT_EQ(remote_ip, text);
}

TEST_F(ExternalPortCheckProcessFixture, InvalidProcess) {
    EXPECT_TRUE(test_port.startIo(reply, tst::TestPort(), LocalOnly::yes, 1));

    EXPECT_EQ(writeToSocket(tst::TestPort()), 6U);
    std::this_thread::sleep_for(300ms);
    test_port.shutdownIo();  // this is long operation
    EXPECT_TRUE(remote_ip.empty());
}

TEST_F(ExternalPortCheckProcessFixture, ValidProcess) {
    EXPECT_TRUE(test_port.startIo(reply, tst::TestPort(), LocalOnly::yes,
                                  ::GetCurrentProcessId()));

    EXPECT_EQ(writeToSocket(tst::TestPort()), 6U);
    tst::WaitForSuccessSilent(100ms, [this]() { return !remote_ip.empty(); });
    test_port.shutdownIo();  // this is long operation
    EXPECT_EQ(remote_ip, text);
}

class ExternalPortTestFixture : public ::testing::Test {
public:
    ReplyFunc reply = [this](const std::string & /*ip*/) {
        std::vector<uint8_t> data(reply_text_.begin(), reply_text_.end());
        if (delay_) {
            std::this_thread::sleep_for(50ms);
        }

        return data;
    };
    void SetUp() override {
        test_port_.startIo(reply, tst::TestPort(), world::LocalOnly::no,
                           {});  //
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

TEST_F(ExternalPortTestFixture, ReadIntegration) {
    tst::FirewallOpener fwo;
    ASSERT_TRUE(tst::WaitForSuccessSilent(1000ms, [this]() {
        std::error_code ec;
        this->sock_.connect(this->endpoint_, ec);
        return ec.value() == 0;
    }));

    auto [ip, p, ipv6] = GetSocketInfo(sock_);
    EXPECT_TRUE(ip == "127.0.0.1");
    EXPECT_TRUE(p != 0U);
    EXPECT_FALSE(ipv6);

    auto text = readSock();
    EXPECT_EQ(reply_text_, text);
}

TEST(ExternalPortTest, LowLevelApiBase) {
    asio::io_context io;

    ExternalPort test_port(nullptr);
    std::vector<AsioSession::s_ptr> a;
    for (int i = 0; i < 32; i++) {
        asio::ip::tcp::socket s(io);
        a.emplace_back(std::make_shared<AsioSession>(std::move(s)));
    }

    EXPECT_EQ(test_port.session_queue_.size(), 0);

    for (auto as : a) {
        test_port.putOnQueue(as);
    }
    EXPECT_TRUE(test_port.session_queue_.size() ==
                test_port.kMaxSessionQueueLength);

    int count = 0;

    ASSERT_TRUE(tst::WaitForSuccessSilent(1000ms, [&count, &test_port]() {
        while (!test_port.session_queue_.empty()) {
            if (test_port.getSession()) {
                ++count;
            }
        }

        return count == test_port.kMaxSessionQueueLength;
    }));

    auto as = test_port.getSession();
    EXPECT_TRUE(!as);
}

TEST(ExternalPortTest, ProcessQueue) {
    asio::io_context io;

    ExternalPort test_port(nullptr);
    std::vector<AsioSession::s_ptr> a;
    ReplyFunc reply =
        [&test_port](const std::string /*ip*/) -> std::vector<uint8_t> {
        return {};
    };

    constexpr size_t max_count = 8;
    for (size_t i = 0; i < max_count; i++) {
        asio::ip::tcp::socket s(io);
        EXPECT_NO_THROW(GetSocketInfo(s));
        a.emplace_back(std::make_shared<AsioSession>(std::move(s)));
    }

    {
        EXPECT_EQ(test_port.sessionsInQueue(), 0);

        for (auto as : a) {
            test_port.putOnQueue(as);
        }
        EXPECT_EQ(test_port.sessionsInQueue(), 8);

        auto f = std::async(std::launch::async, &ExternalPort::processQueue,
                            &test_port, reply);

        tst::WaitForSuccessSilent(1000ms, [&test_port]() {
            return test_port.sessionsInQueue() == 0;
        });

        EXPECT_EQ(test_port.sessionsInQueue(), 0);
        test_port.shutdownIo();
    }
}

namespace {
size_t g_count{0};
std::mutex g_lock;
void runThread(int port) {
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

TEST_F(ExternalPortTestFixture, MultiConnectIntegration) {
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
        YAML::Load(fmt::format(base, "yes"));
    for (const auto &t : ip_allowed) {
        EXPECT_EQ(IsIpAllowedAsException(t.first), t.second);
    }
}

TEST(ExternalPortTest, IsIpAllowedAsExceptionNo) {
    auto test_fs = tst::TempCfgFs::CreateNoIo();
    cfg::GetLoadedConfig()[cfg::groups::kSystem] =
        YAML::Load(fmt::format(base, "no"));
    for (const auto &t : ip_allowed) {
        EXPECT_FALSE(IsIpAllowedAsException(t.first));
    }
}

}  // namespace cma::world
