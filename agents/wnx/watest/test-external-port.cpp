// Testing external port

// TODO
//
#include "pch.h"

#include <chrono>

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
    const wchar_t* getMainLogName() const { return L"log.log"; }
    void preContextCall() { pre_context_call_ = true; }

    bool stopped_ = false;
    bool started_ = false;
    bool paused_ = false;
    bool shutdowned_ = false;
    bool continued_ = false;
    bool pre_context_call_ = false;
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
    world::ExternalPort test_port(&tp, tst::TestPort());  //

    EXPECT_TRUE(test_port.startIo(reply));
    EXPECT_TRUE(test_port.io_thread_.joinable());
    EXPECT_FALSE(test_port.startIo(reply));

    EXPECT_TRUE(tst::WaitForSuccessSilent(
        1000ms, [&test_port]() { return test_port.io_thread_.joinable(); }));

    cma::tools::sleep(50);
    test_port.shutdownIo();  // this is long operation
    EXPECT_TRUE(!test_port.io_thread_.joinable());
    EXPECT_TRUE(tp.pre_context_call_);
}

TEST(ExternalPortTest, CtorPort) {
    world::ExternalPort test_port(nullptr);  //
    EXPECT_EQ(test_port.defaultPort(), 0);

    world::ExternalPort test_port_0(nullptr, 0);  //
    EXPECT_EQ(test_port_0.defaultPort(), 0);

    world::ExternalPort test_port_555(nullptr, 555);  //
    EXPECT_EQ(test_port_555.defaultPort(), 555);
}

class ExternalPortTestFixture : public ::testing::Test {
public:
    cma::world::ReplyFunc reply =
        [this](const std::string /*ip*/) -> std::vector<uint8_t> {
        std::vector<uint8_t> data(reply_text_.begin(), reply_text_.end());
        if (delay_) {
            std::this_thread::sleep_for(50ms);
        }

        return data;
    };
    void SetUp() override {
        test_port_.startIo(reply);  //
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
    world::ExternalPort test_port_{nullptr, tst::TestPort()};
    tcp::endpoint endpoint_{asio::ip::make_address("127.0.0.1"),
                            tst::TestPort()};

    asio::io_context ios_;
    tcp::socket sock_{ios_};
    bool delay_{false};
};

TEST_F(ExternalPortTestFixture, Read) {
    ASSERT_TRUE(tst::WaitForSuccessSilent(1000ms, [this]() {
        std::error_code ec;
        this->sock_.connect(this->endpoint_, ec);
        return ec.value() == 0;
    }));

    auto [ip, ipv6] = GetSocketInfo(sock_);
    EXPECT_TRUE(ip == "127.0.0.1");
    EXPECT_FALSE(ipv6);

    auto text = readSock();
    EXPECT_EQ(reply_text_, text);
}

TEST(ExternalPortTest, LowLevelApiBase) {
    asio::io_context io;

    cma::world::ExternalPort test_port(nullptr, 111);
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

    cma::world::ExternalPort test_port(nullptr, 111);
    std::vector<AsioSession::s_ptr> a;
    cma::world::ReplyFunc reply =
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
    constexpr int thread_count{8};
    delay_ = true;

    std::vector<std::future<void>> futures;
    for (int i = 0; i < thread_count; ++i) {
        futures.push_back(
            std::async(std::launch::async, runThread, tst::TestPort()));
    }

    for (auto& f : futures) {
        f.get();
    }

    EXPECT_EQ(g_count, thread_count * 11);
}

}  // namespace cma::world
