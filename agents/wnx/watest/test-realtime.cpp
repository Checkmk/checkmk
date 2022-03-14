// test-realtime.cpp

//
#include "pch.h"

#include <string_view>
#include <thread>

#include "asio.h"
#include "cfg.h"
#include "common/cfg_info.h"
#include "realtime.h"
#include "tools/_misc.h"

namespace tst {
void DisableSectionsNode(std::string_view Str) {
    using namespace cma::cfg;
    YAML::Node config = GetLoadedConfig();
    auto disabled_string = cma::cfg::GetVal(
        groups::kGlobal, vars::kSectionsDisabled, std::string(""));
    {
        disabled_string += " ";

        disabled_string += std::string(Str);
    }
    config[groups::kGlobal][vars::kSectionsDisabled] = disabled_string;
}
}  // namespace tst

namespace cma::rt {

using asio::ip::udp;
static std::vector<RtBlock> TestTable;

// test server for the checking output from realtime main thread
// do NOT use in production
class UdpServer {
public:
    UdpServer(asio::io_context &io_context, short port)
        : socket_(io_context, udp::endpoint(udp::v4(), port)) {
        do_receive();
    }

    void do_receive() {
        socket_.async_receive_from(
            asio::buffer(data_, max_length), sender_endpoint_,
            [this](std::error_code ec, std::size_t bytes_recvd) {
                do_store(bytes_recvd);
                do_receive();
            });
    }

private:
    void do_store(size_t Length) {
        TestTable.emplace_back(data_, data_ + Length);
    }

    udp::socket socket_;
    udp::endpoint sender_endpoint_;
    enum { max_length = 16000 };
    char data_[max_length];
};

void StartTestServer(asio::io_context *IoContext, int Port) {
    try {
        ;

        UdpServer s(*IoContext, Port);

        IoContext->run();
    } catch (std::exception &e) {
        std::cerr << "Exception: " << e.what() << "\n";
    }
}

TEST(RealtimeTest, LowLevel) {
    // stub
    Device dev;
    auto ret = dev.start();
    ASSERT_TRUE(dev.started());
    EXPECT_FALSE(dev.use_df_);
    EXPECT_FALSE(dev.use_mem_);
    EXPECT_FALSE(dev.use_winperf_processor_);
    EXPECT_FALSE(dev.use_test_);
    EXPECT_TRUE(dev.port_ == 0);
    EXPECT_FALSE(dev.working_period_);
    EXPECT_TRUE(dev.kick_count_ == 0);
    auto tm = dev.kick_time_;

    dev.connectFrom("1.0.0.1", 555, {"mem", "df", "tesT", "winpErf_processor"},
                    "", 91);
    EXPECT_TRUE(dev.use_df_);
    EXPECT_TRUE(dev.use_mem_);
    EXPECT_TRUE(dev.use_winperf_processor_);
    EXPECT_TRUE(dev.use_test_);
    EXPECT_TRUE(dev.port_ == 555);
    EXPECT_TRUE(dev.kick_count_ == 1);
    EXPECT_TRUE(dev.kick_time_ > tm);
    EXPECT_TRUE(dev.timeout_ == 91);
    EXPECT_TRUE(dev.working_period_);
    tm = dev.kick_time_;

    dev.connectFrom("1.0.0.1", 999, {"tesT"}, "", 0);
    EXPECT_FALSE(dev.use_df_);
    EXPECT_FALSE(dev.use_mem_);
    EXPECT_FALSE(dev.use_winperf_processor_);
    EXPECT_TRUE(dev.use_test_);
    EXPECT_TRUE(dev.port_ == 999);
    EXPECT_TRUE(dev.kick_time_ > tm);
    cma::tools::sleep(2000);
    EXPECT_FALSE(dev.working_period_);
}

TEST(RealtimeTest, StaticCheck) {
    // prtects again occasional consats change
    EXPECT_EQ(kEncryptedHeader, "00");
    EXPECT_EQ(kPlainHeader, "99");
    EXPECT_EQ(kHeaderSize, 2);
    EXPECT_EQ(kTimeStampSize, 10);
    EXPECT_EQ(kDataOffset, 12);
    EXPECT_EQ(cma::cfg::kDefaultRealtimeTimeout, 90);
    EXPECT_EQ(cma::cfg::kDefaultRealtimePort, 6559);
}

TEST(RealtimeTest, PackData) {
    // stub
    std::string_view output = "123456789";
    {
        auto tstamp1 = time(nullptr);
        auto no_crypt_result = PackData(output, nullptr);
        auto tstamp2 = time(nullptr);
        ASSERT_TRUE(no_crypt_result.size() ==
                    output.size() + kHeaderSize + kTimeStampSize);
        auto data = no_crypt_result.data();
        EXPECT_TRUE(0 == memcmp(data, kPlainHeader.data(), kHeaderSize));
        EXPECT_TRUE(0 == memcmp(data + kHeaderSize + kTimeStampSize,
                                output.data(), output.size()));
        auto char_data = reinterpret_cast<char *>(data);
        std::string_view ts(char_data + kHeaderSize, kTimeStampSize);
        std::string timestamp(ts);
        auto timestamp_mid = std::atoll(timestamp.c_str());
        EXPECT_TRUE(tstamp1 <= timestamp_mid);
        EXPECT_TRUE(tstamp2 >= timestamp_mid);
    }

    {
        cma::encrypt::Commander crypto("873fre)%d\\-QA");
        auto tstamp1 = time(nullptr);
        auto crypt_result = PackData(output, &crypto);
        auto tstamp2 = time(nullptr);
        ASSERT_TRUE(!crypt_result.empty());
        EXPECT_TRUE(0 == memcmp(crypt_result.data(), kEncryptedHeader.data(),
                                kHeaderSize));
        ASSERT_TRUE(crypt_result.size() >
                    output.size() + kHeaderSize + kTimeStampSize);
        auto data = crypt_result.data();
        auto char_data = reinterpret_cast<char *>(data);
        std::string_view ts(char_data + kHeaderSize, kTimeStampSize);
        std::string timestamp(ts);
        auto timestamp_mid = std::atoll(timestamp.c_str());
        EXPECT_TRUE(tstamp1 <= timestamp_mid);
        EXPECT_TRUE(tstamp2 >= timestamp_mid);

        auto [success, size] =
            crypto.decode(data + kHeaderSize + kTimeStampSize,
                          crypt_result.size() - (kHeaderSize + kTimeStampSize));

        ASSERT_TRUE(success);
        ASSERT_TRUE(size > 0);
        EXPECT_EQ(size, output.size());

        EXPECT_TRUE(0 == memcmp(data + kHeaderSize + kTimeStampSize,
                                output.data(), output.size()));
    }
}

template <typename T, typename B>
void WaitFor(std::function<bool()> predicat,
             std::chrono::duration<T, B> max_dur) noexcept {
    using namespace std::chrono;
    auto end = steady_clock::now() + max_dur;

    while (!predicat()) {
        auto cur = steady_clock::now();
        if (cur > end) break;
        std::this_thread::sleep_until(cur + 100ms);
    }
}

TEST(RealtimeTest, Base_Long) {
    // stub
    using namespace std::chrono;

    cma::OnStart(cma::AppType::test);
    ON_OUT_OF_SCOPE(
        cma::OnStart(cma::AppType::test));  // restore original config
    {
        // we disable sections to be sure that realtime sections are executed
        // even being disabled
        tst::DisableSectionsNode("df");
        tst::DisableSectionsNode("mem");
        tst::DisableSectionsNode("winperf");
        cma::cfg::ProcessKnownConfigGroups();
        cma::cfg::SetupEnvironmentFromGroups();

        Device dev;
        asio::io_context context;
        TestTable.clear();
        std::thread first(StartTestServer, &context, 555);
        auto ret = dev.start();

        EXPECT_TRUE(dev.started_);
        dev.connectFrom("127.0.0.1", 555, {"mem", "df", "winperf_processor"},
                        "");

        EXPECT_TRUE(ret);
        WaitFor([]() { return TestTable.size() >= 6; }, 20s);

        EXPECT_TRUE(dev.started_);
        dev.stop();
        EXPECT_FALSE(dev.started_);

        context.stop();
        if (first.joinable()) first.join();
        EXPECT_GT(TestTable.size(), static_cast<size_t>(3));

        for (const auto &packet : TestTable) {
            auto d = reinterpret_cast<const char *>(packet.data());
            std::string p(d, packet.size());
            EXPECT_TRUE(p.find(kPlainHeader) == 0);
            EXPECT_TRUE(p.find("<<<df") != std::string::npos);
            EXPECT_TRUE(p.find("<<<mem") != std::string::npos);
            EXPECT_TRUE(p.find("<<<winperf_processor") != std::string::npos);
        }
    }
    {
        Device dev;
        asio::io_context context;
        TestTable.clear();
        std::thread first(StartTestServer, &context, 555);
        auto ret = dev.start();

        EXPECT_TRUE(dev.started_);
        dev.connectFrom("127.0.0.1", 555, {"mem", "df", "winperf_processor"},
                        "encrypt");

        EXPECT_TRUE(ret);
        WaitFor([]() { return TestTable.size() >= 6; }, 20s);
        EXPECT_TRUE(dev.started_);
        dev.stop();
        EXPECT_FALSE(dev.started_);

        context.stop();
        if (first.joinable()) first.join();
        EXPECT_TRUE(TestTable.size() > 3);
        cma::encrypt::Commander dec("encrypt");
        for (auto &packet : TestTable) {
            auto d = reinterpret_cast<char *>(packet.data());
            auto [success, size] =
                dec.decode(d + kHeaderSize + kTimeStampSize,
                           packet.size() - kHeaderSize - kTimeStampSize, true);
            ASSERT_TRUE(success);
            std::string p(d, packet.size());
            ASSERT_TRUE(p.find(kEncryptedHeader) == 0);

            EXPECT_TRUE(p.find("<<<df") != std::string::npos);
            EXPECT_TRUE(p.find("<<<mem") != std::string::npos);
            EXPECT_TRUE(p.find("<<<winperf_processor") != std::string::npos);
        }
    }
}
}  // namespace cma::rt
