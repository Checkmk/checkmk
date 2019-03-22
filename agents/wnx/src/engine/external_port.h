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

#include "cfg.h"
#include "encryption.h"

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
                auto crypt = cma::encrypt::MakeCrypt();
                do_write(send_back.data(), send_back.size(), crypt.get());
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
    size_t allocCryptBuffer(const cma::encrypt::Commander* Crypt) noexcept;
    void do_write(const void* Data, std::size_t Length,
                  cma::encrypt::Commander* Crypt);

    asio::ip::tcp::socket socket_;
    enum { kMaxLength = 1024 };
    char data_[kMaxLength];
    const bool mode_one_shot_ = cma::cfg::IsOneShotMode();
    const size_t segment_size_ = 48 * 1024;
    std::unique_ptr<char> crypt_buf_;
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
    ExternalPort(wtools::BaseServiceProcessor* Owner, uint16_t Port = 0)
        : default_port_(Port)
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

    auto defaultPort() const { return default_port_; }

private:
    wtools::BaseServiceProcessor* owner_ = nullptr;
    // Internal class from  ASIO documentation
    class server {
    public:
        server(asio::io_context& io_context, bool Ipv6, short port,
               cma::world::ReplyFunc Reply)
            : acceptor_(
                  io_context,
                  asio::ip::tcp::endpoint(
                      Ipv6 ? asio::ip::tcp::v6() : asio::ip::tcp::v4(), port))
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
                if (ec.value()) {
                    XLOG::l("Error on connection {} '{}'", ec.value(),
                            ec.message());
                } else {
                    try {
                        auto remote_ep = socket_.remote_endpoint();
                        auto addr = remote_ep.address();
                        auto ip = addr.to_string();
                        XLOG::d.i("Connected from '{}' ipv6 {}", ip,
                                  addr.is_v6());

                        auto x =
                            std::make_shared<AsioSession>(std::move(socket_));

                        // only_from checking
                        // we are doping it always
                        if (!cma::cfg::groups::global.isIpAddressAllowed(ip)) {
                            XLOG::d.i("Address '{}' is not allowed", ip);
                            return;
                        }

                        // #TODO blocking call here. This is not a good idea
                        x->start(Reply);
                    } catch (const std::system_error& e) {
                        if (e.code().value() == WSAECONNRESET)
                            XLOG::l.i(XLOG_FLINE + " Client closed connection");
                        else
                            XLOG::l(
                                XLOG_FLINE +
                                    " Thrown unexpected exception '{}' with value {}",
                                e.what(), e.code().value());
                    } catch (const std::exception& e) {
                        XLOG::l(
                            XLOG_FLINE + " Thrown unexpected exception '{}'",
                            e.what());
                    }
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

    uint16_t default_port_ = 0;  // work port
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
