#pragma once
#if !defined(external_port_h__)
#define external_port_h__

#include <chrono>
#include <cstdint>
#include <functional>

#include "tools/_xlog.h"

#include "logger.h"

#include "asio.h"

#include "common/cfg_info.h"

namespace cma::world {
using ReplyFunc =
    std::function<std::vector<uint8_t>(const std::string IpAddress)>;
}  // namespace cma::world

namespace test {
inline std::vector<uint8_t> generateData() {
    std::string t =
        "abcdefghabcdefghabcdefghabcdefghabcdefghabcdefghabcdefghabcdefgh\n";
    std::vector<uint8_t> a;
    a.reserve(400000);
    for (;;) {
        if (a.size() > 400000) break;
        a.insert(a.end(), t.begin(), t.end());
    }
    return a;
}

}  // namespace test

namespace cma::world {
// below is working example from asio
// verified and working
// try not damage it

// implements asio logic for the low level TCP transport:
// read and write
class AsioSession : public std::enable_shared_from_this<AsioSession> {
public:
    AsioSession(asio::ip::tcp::socket socket) : socket_(std::move(socket)) {
        /*
                auto h = socket_.native_handle();
                auto cleared_socket = RemoveSocketInheritance(h);
                socket_.native_handle() = cleared_socket;
        */
    }

    void start(cma::world::ReplyFunc Reply) {
        if (mode_one_shot_) {
            // typical functionality of current agent
            // accept connection, get data, write data, close connection
            std::vector<unsigned char> send_back;

            // #TODO move to gtest
            constexpr bool internal_test = false;
            if (internal_test) {
                send_back = test::generateData();
                const bool simulate_delay = true;
                if (simulate_delay) {
                    using namespace std::chrono;
                    std::this_thread::sleep_until(steady_clock::now() +
                                                  15000ms);
                }
            } else {
                send_back = Reply(getCurrentRemoteIp());
                // send_back = test::generateData();
            }

            if (send_back.size()) {
                do_write(send_back.data(), send_back.size());
                XLOG::l.i("Send {} bytes of data", send_back.size());

                if (tgt::IsDebug()) {
                    std::string s(send_back.begin(), send_back.end());
                    auto t = cma::tools::SplitString(s, std::string("\n"));
                    XLOG::t.i("Send {} last string is {}", send_back.size(),
                              t.back());
                }
            }
        } else {
            // continuous working, for the future
            do_read();
        }
    }

private:
    std::string getCurrentRemoteIp() const noexcept {
        std::string ip = "";
        try {
            ip = socket_.remote_endpoint().address().to_string();
        } catch (const std::exception& e) {
            XLOG::l.bp("Unexpected exception hits '{}'", e.what());
        }
        return ip;
    }
    void do_read();
    void do_write(const void* Data, std::size_t Length);

    asio::ip::tcp::socket socket_;
    enum { kMaxLength = 1024 };
    char data_[kMaxLength];
    const bool mode_one_shot_ = cma::cfg::IsOneShotMode();
};

}  // namespace cma::world

// =====================================================
// Main executive module of the service
// implements logic of the transport Agent <- > Monitor at
// the top most level.
// exists as a share pointer enable_shared_from_this !!!
// API is simple and must be simple
// This ASIO Based
// =====================================================
namespace cma::world {
class ExternalPort : public std::enable_shared_from_this<ExternalPort> {
public:
    // ctor&dtor
    ExternalPort(wtools::BaseServiceProcessor* Owner,
                 uint16_t Port = cma::cfg::kMainPort)
        : port_(Port)
        , shutdown_thread_(false)
        , io_started_(false)
        , owner_(Owner) {}

    virtual ~ExternalPort() {}

    // no copy, no move
    ExternalPort(const ExternalPort&) = delete;
    ExternalPort(ExternalPort&&) = delete;
    ExternalPort& operator=(const ExternalPort&) = delete;
    ExternalPort& operator=(ExternalPort&&) = delete;

    // Main API
    bool startIo(cma::world::ReplyFunc Reply);
    void shutdownIo();
    int xmain(int PORT);

    // Supplementary API
    void reloadConfig() {}
    bool isIoStarted() const { return io_started_; }

private:
    wtools::BaseServiceProcessor* owner_ = nullptr;
    // Internal class from  ASIO documentation
    class server {
    public:
        server(asio::io_context& io_context, short port,
               cma::world::ReplyFunc Reply)
            : acceptor_(io_context,
                        asio::ip::tcp::endpoint(asio::ip::tcp::v4(), port))
            , socket_(io_context) {
#if 0
            // Binding from ASIO example
            asio::ip::tcp::resolver resolver(io_context);
            asio::ip::tcp::endpoint endpoint =
                *resolver.resolve(address, port).begin();
            acceptor_.open(endpoint.protocol());
            acceptor_.set_option(asio::ip::tcp::acceptor::reuse_address(true));
            acceptor_.bind(endpoint);
            acceptor_.listen();
#endif

            do_accept(Reply);
        }

    private:
        // this is the only entry point
        void do_accept(cma::world::ReplyFunc Reply) {
            acceptor_.async_accept(socket_, [this, Reply](std::error_code ec) {
                if (!ec) {
                    auto x = std::make_shared<world::AsioSession>(
                        std::move(socket_));
                    x->start(Reply);
                }

                if (!mode_one_shot_)
                    do_accept(Reply);  // only one accept is allowed
            });
        }

        // ASIO magic
        asio::ip::tcp::acceptor acceptor_;
        asio::ip::tcp::socket socket_;

        // configures mode Shot and Forget or Continuous
        // Continuous mode is not supported
        // copied from the owner
        const bool mode_one_shot_ = cma::cfg::IsOneShotMode();
    };

protected:
    // returns thread continue status
    bool registerContext(asio::io_context* Context) {
        std::lock_guard<std::mutex> lk(io_thread_lock_);
        if (shutdown_thread_) {
            context_ = nullptr;
            return false;
        }
        context_ = Context;
        return true;
    }

    void stopExecution() {
        // call of the function SIgnal under lock
        std::lock_guard<std::mutex> lk(io_thread_lock_);
        XLOG::l.t("Stopping execution");
        if (context_) {
            context_->stop();  // non blocking call to stop IO
        }
        shutdown_thread_ = true;
    }

    uint16_t port_ = cma::cfg::kMainPort;  // work port
    const bool mode_one_shot_ = cma::cfg::IsOneShotMode();

    void ioThreadProc(cma::world::ReplyFunc Reply);

    // critical data is below this mutex
    mutable std::mutex data_lock_;
    // at the moment we have no critical data

    // probably overkill, but we want to restart and want to be sure that
    // everything is going smooth
    mutable std::mutex io_thread_lock_;
    std::thread io_thread_;
    bool shutdown_thread_;
    bool io_started_;

    asio::io_context*
        context_;  // NOT reusable, should not be locked, not OWNED

#if defined(GTEST_INCLUDE_GTEST_GTEST_H_)
    friend class ExternalPortTest;
    FRIEND_TEST(ExternalPortTest, CreateDelete);
    FRIEND_TEST(ExternalPortTest, StartStop);
#endif
};

}  // namespace cma::world

#endif  // external_port_h__
