// Testing external port

// TODO
//
#include "pch.h"

#include "asio.h"
#include "external_port.h"

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
    using namespace std::chrono;
    using namespace xlog::internal;

    {
        cma::world::ReplyFunc reply =
            [](const std::string Ip) -> std::vector<uint8_t> {
            char reply_text[] = "I am test\n";
            auto len = strlen(reply_text) + 1;
            std::vector<uint8_t> v;
            v.resize(len);
            for (unsigned int i = 0; i < len; i++) v[i] = reply_text[i];
            return v;
        };
        wtools::TestProcessor2 tp;
        cma::world::ExternalPort test_port(&tp, 64351);  //
        auto ret = test_port.startIo(reply);             //
        EXPECT_TRUE(ret);
        EXPECT_TRUE(test_port.io_thread_.joinable());
        ret = test_port.startIo(reply);  //
        EXPECT_FALSE(ret);

        xlog::sendStringToStdio("sleeping for 1000ms\n", Colors::dflt);
        cma::tools::sleep(1000);
        xlog::sendStringToStdio("end of sleep\n", Colors::dflt);
        EXPECT_TRUE(test_port.io_thread_.joinable());
        test_port.shutdownIo();  //
        EXPECT_TRUE(!test_port.io_thread_.joinable());
        EXPECT_TRUE(tp.pre_context_call_);
    }
}

TEST(ExternalPortTest, Read) {
    using namespace std::chrono;
    using namespace xlog::internal;

    {
        cma::world::ExternalPort test_port(nullptr, 0);  //
        EXPECT_EQ(test_port.defaultPort(), 0);
    }

    {
        cma::world::ExternalPort test_port(nullptr);  //
        EXPECT_EQ(test_port.defaultPort(), 0);
    }

    {
        cma::world::ExternalPort test_port(nullptr, 555);  //
        EXPECT_EQ(test_port.defaultPort(), 555);
    }
    {
        char reply_text[] = "I am test\n";
        int port = 64351;
        cma::world::ReplyFunc reply =
            [reply_text](const std::string Ip) -> std::vector<uint8_t> {
            auto len = strlen(reply_text) + 1;
            std::vector<uint8_t> v;
            v.resize(len);
            for (unsigned int i = 0; i < len; i++) {
                v[i] = reply_text[i];
            }
            return v;
        };
        cma::world::ExternalPort test_port(nullptr, port);  //
        auto ret = test_port.startIo(reply);                //
        EXPECT_TRUE(ret);
        ret = test_port.startIo(reply);  //
        EXPECT_FALSE(ret);

        xlog::sendStringToStdio("sleeping for 1000ms\n", Colors::dflt);
        cma::tools::sleep(1000);
        xlog::sendStringToStdio("end of sleep\n", Colors::dflt);

        using namespace asio;

        io_context ios;

        ip::tcp::endpoint endpoint(ip::make_address("127.0.0.1"), port);

        asio::ip::tcp::socket sock(ios);

        sock.connect(endpoint);
        auto [ip, ipv6] = GetSocketInfo(sock);
        EXPECT_TRUE(ip == "127.0.0.1");
        EXPECT_FALSE(ipv6);

        error_code error;
        char text[256];
        auto count = sock.read_some(asio::buffer(text), error);
        EXPECT_EQ(count, strlen(reply_text) + 1);
        EXPECT_EQ(0, strcmp(text, reply_text));
        sock.close();

        test_port.shutdownIo();  //
    }
}

TEST(ExternalPortTest, LowLevelApiBase) {
    asio::io_context io;
    {
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
        while (!test_port.session_queue_.empty()) {
            auto as = test_port.getSession();
            if (as) ++count;
        }
        EXPECT_TRUE(count == test_port.kMaxSessionQueueLength);
        auto as = test_port.getSession();
        EXPECT_TRUE(!as);
    }
}

TEST(ExternalPortTest, LowLevelApiEx) {
    asio::io_context io;
    {
        cma::world::ExternalPort test_port(nullptr, 111);
        std::vector<AsioSession::s_ptr> a;
        int reply_cont_calls = 0;
        cma::world::ReplyFunc reply =
            [&reply_cont_calls,
             &test_port](const std::string Ip) -> std::vector<uint8_t> {
            reply_cont_calls++;
            if (reply_cont_calls == test_port.kMaxSessionQueueLength)
                test_port.shutdownIo();

            return {};
        };
        constexpr size_t max_count = 8;
        for (size_t i = 0; i < max_count; i++) {
            asio::ip::tcp::socket s(io);
            EXPECT_NO_THROW(GetSocketInfo(s));
            a.emplace_back(std::make_shared<AsioSession>(std::move(s)));
        }

        {
            EXPECT_EQ(test_port.session_queue_.size(), 0);

            for (auto as : a) {
                test_port.putOnQueue(as);
            }
            EXPECT_EQ(test_port.session_queue_.size(), 8)
                << "need for processing";

            auto f = std::async(std::launch::async, &ExternalPort::processQueue,
                                &test_port, reply);

            for (size_t i = 0; i < test_port.kMaxSessionQueueLength; i++) {
                if (test_port.session_queue_.empty()) break;
                cma::tools::sleep(1000);
            }

            EXPECT_EQ(test_port.session_queue_.size(), 0)
                << "must 0 after processing";
            ASSERT_NO_THROW(test_port.getSession());
            auto as = test_port.getSession();
            EXPECT_TRUE(!as);
            test_port.shutdownIo();
        }
    }
}

static size_t g_count = 0;
static std::mutex g_lock;
void runThread(int port) {
    using namespace asio;
    io_context ios;
    ip::tcp::endpoint endpoint(ip::make_address("127.0.0.1"), port);

    asio::ip::tcp::socket socket(ios);

    EXPECT_NO_THROW(socket.connect(endpoint));

    error_code error;
    char text[256];
    auto count = socket.read_some(asio::buffer(text), error);
    socket.close();
    EXPECT_TRUE(count == 9);

    std::lock_guard lk(g_lock);
    g_count += count;
}

TEST(ExternalPortTest, MultiConnect) {
    using namespace cma::cfg;
    using namespace asio;
    auto yaml = GetLoadedConfig();

    groups::global.loadFromMainConfig();
    int port = 64351;
    g_count = 0;
    // inside light delay
    cma::world::ReplyFunc reply =
        [](const std::string Ip) -> std::vector<uint8_t> {
        std::error_code ec;
        const char *s = "012345678";
        auto data = reinterpret_cast<const uint8_t *>(s);
        cma::tools::sleep(500);
        std::vector<uint8_t> v(data, data + strlen(s));
        return v;
    };

    //  ipv4 connected successfully
    {
        cma::world::ExternalPort test_port(nullptr, port);  //
        auto ret = test_port.startIo(reply);                //
        ASSERT_TRUE(ret);

        static int thread_count = 8;

        std::vector<std::future<void>> futures;
        for (int i = 0; i < thread_count; ++i) {
            futures.push_back(std::async(std::launch::async, runThread, port));
        }

        for (int i = 0; i < thread_count; ++i) {
            futures[i].get();
        }

        EXPECT_TRUE(g_count == thread_count * 9);
        test_port.shutdownIo();  //
    }
}

}  // namespace cma::world
