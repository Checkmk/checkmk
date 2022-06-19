// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#pragma once
#if !defined(external_port_h__)
#define external_port_h__

#include <chrono>
#include <cstdint>
#include <functional>
#include <queue>

#include "asio.h"
#include "cfg.h"
#include "common/cfg_info.h"
#include "encryption.h"
#include "logger.h"
#include "tools/_xlog.h"

namespace cma::world {
using ReplyFunc =
    std::function<std::vector<uint8_t>(const std::string IpAddress)>;
}  // namespace cma::world

namespace cma::world {

/// Defines visibility of local socket for external world
enum class LocalOnly { yes, no };

bool IsIpAllowedAsException(const std::string &ip);

/// implements asio logic for the low level TCP transport:
/// based on ASIO example
/// NOT THREAD SAFE
class AsioSession : public std::enable_shared_from_this<AsioSession> {
public:
    using s_ptr = std::shared_ptr<AsioSession>;

    explicit AsioSession(asio::ip::tcp::socket socket)
        : socket_(std::move(socket)) {}
    virtual ~AsioSession() { XLOG::d("destroy connection"); }

    void start(const ReplyFunc &reply_func) {
        // standard functionality of current agent
        // accept connection, get data, write data, close connection
        auto send_back = reply_func(getCurrentRemoteIp());

        if (send_back.empty()) {
            XLOG::d.i("No data to send");
            return;
        }

        auto crypt = cma::encrypt::MakeCrypt();
        do_write(send_back.data(), send_back.size(), crypt.get());
        XLOG::d.i("Send [{}] bytes of data", send_back.size());

        logWhenDebugging(send_back);
    }

    const asio::ip::tcp::socket &currentSocket() const { return socket_; }
    void read_ip();

private:
    // prints last line of the output in the log
    // to see how correct was an answer
    static void logWhenDebugging(const ByteVector &send_back) noexcept {
        if (!tgt::IsDebug()) {
            return;
        }

        std::string s(send_back.begin(), send_back.end());
        auto t = tools::SplitString(s, "\n");
        XLOG::t.i("Send {} last string is {}", send_back.size(), t.back());
    }

    std::string getCurrentRemoteIp() const noexcept {
        {
            std::scoped_lock l(data_lock_);
            if (remote_ip_.has_value()) {
                return *remote_ip_;
            }
        }
        try {
            std::error_code ec;
            auto remote_ep = socket_.remote_endpoint(ec);
            if (!ec) {
                return remote_ep.address().to_string();
            }

            XLOG::d(
                "No remote endpoint, error = [{}], may happen only in <GTEST>",
                ec.value());
        } catch (const std::exception &e) {
            XLOG::l("Unexpected exception hits '{}'", e.what());
        }
        return {};
    }
    size_t allocCryptBuffer(const encrypt::Commander *commander);
    void do_write(const void *data_block, std::size_t data_length,
                  encrypt::Commander *crypto_commander);

    asio::ip::tcp::socket socket_;

    constexpr static size_t kMaxLength{1024};
    char data_[kMaxLength];
    std::optional<size_t> received_;
    std::condition_variable cv_ready_;
    mutable std::mutex data_lock_;
    std::optional<std::string> remote_ip_;

    const size_t segment_size_ = 48 * 1024;
    std::vector<char> crypt_buf_;
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
class ExternalPort;  // forward

// store incoming session into the queue
using SinkFunc = std::function<bool(AsioSession::s_ptr, ExternalPort *)>;

inline std::tuple<std::string, uint16_t, bool> GetSocketInfo(
    const asio::ip::tcp::socket &sock) noexcept {
    std::error_code ec;
    auto remote_ep = sock.remote_endpoint(ec);
    if (ec.value() != 0) {
        XLOG::l("Error on socket [{}] with '{}'", ec.value(), ec.message());
        return {};  // empty socket
    }
    try {
        auto addr = remote_ep.address();
        auto ip = addr.to_string();
        bool ipv6 = addr.is_v6();
        return {ip, remote_ep.port(), ipv6};
    } catch (const std::exception &e) {
        XLOG::d("Something goes wrong with socket '{}'", e.what());
    }
    return {};
}

class ExternalPort : public std::enable_shared_from_this<ExternalPort> {
public:
    // ctor&dtor
    explicit ExternalPort(wtools::BaseServiceProcessor *owner)
        : owner_(owner) {}

    virtual ~ExternalPort() = default;

    // no copy, no move
    ExternalPort(const ExternalPort &) = delete;
    ExternalPort(ExternalPort &&) = delete;
    ExternalPort &operator=(const ExternalPort &) = delete;
    ExternalPort &operator=(ExternalPort &&) = delete;

    // Main API
    bool startIo(const ReplyFunc &reply_func, uint16_t port,
                 LocalOnly local_only, std::optional<uint32_t> controller_pid);
    bool startIo(const ReplyFunc &reply_func, uint16_t port) {
        return startIo(reply_func, port, LocalOnly::no, {});
    }
    void shutdownIo();

    // Supplementary API
    bool isIoStarted() const noexcept { return io_started_; }

    void putOnQueue(AsioSession::s_ptr asio_session);
    size_t sessionsInQueue();

    const size_t kMaxSessionQueueLength = 16;

private:
    wtools::BaseServiceProcessor *owner_ = nullptr;
    class server {
        static asio::ip::tcp::endpoint makeEndpoint(bool ipv6, uint16_t port,
                                                    LocalOnly local_only) {
            return local_only == LocalOnly::yes
                       ? asio::ip::tcp::endpoint(
                             asio::ip::make_address("127.0.0.1"), port)
                       : asio::ip::tcp::endpoint(
                             ipv6 ? asio::ip::tcp::v6() : asio::ip::tcp::v4(),
                             port);
        }

        // Internal class from  ASIO documentation
    public:
        server(asio::io_context &io_context, bool Ipv6, uint16_t port,
               LocalOnly local_only, std::optional<uint32_t> pid)
            : port_{port}
            , controller_pid_{pid}
            , acceptor_(io_context, makeEndpoint(Ipv6, port, local_only))
            , socket_(io_context) {}

        // this is the only entry point
        // based on the code example from asio
        void run_accept(SinkFunc sink, ExternalPort *ext_port);

    private:
        uint16_t port_;
        std::optional<uint32_t> controller_pid_;
        // ASIO magic
        asio::ip::tcp::acceptor acceptor_;
        asio::ip::tcp::socket socket_;

        // configures mode Shot and Forget or Continuous
        // Continuous mode is not supported
        // copied from the owner
        const bool mode_one_shot_ = cma::cfg::IsOneShotMode();
    };

protected:
    // asio sessions API
    std::shared_ptr<AsioSession> getSession();
    void processQueue(const cma::world::ReplyFunc &reply);
    void wakeThread();
    void timedWaitForSession();

    // check for end
    bool isShutdown() const noexcept {
        std::lock_guard lk(io_thread_lock_);
        return shutdown_thread_;
    }

    // returns thread continue status
    bool registerContext(asio::io_context *Context) {
        std::lock_guard<std::mutex> lk(io_thread_lock_);
        if (shutdown_thread_) {
            context_ = nullptr;
            return false;
        }
        context_ = Context;
        return true;
    }

    void stopExecution() {
        // call of the function Signal under lock
        std::lock_guard<std::mutex> lk(io_thread_lock_);
        XLOG::l.t("Stopping execution");
        if (context_ != nullptr) {
            context_->stop();  // non blocking call to stop IO
        }
        shutdown_thread_ = true;
    }

    void ioThreadProc(const ReplyFunc &Reply, uint16_t port,
                      LocalOnly local_only, std::optional<uint32_t> pid);

    // probably overkill, but we want to restart and want to be sure that
    // everything is going smooth
    mutable std::mutex io_thread_lock_;
    std::thread io_thread_;
    bool shutdown_thread_{false};
    bool io_started_{false};

    asio::io_context *context_;  // NOT OWNED, should not be locked

    // asio sessions queue data
    mutable std::mutex queue_lock_;
    std::queue<std::shared_ptr<AsioSession>> session_queue_;

    // asio sessions waker
    mutable std::mutex wake_lock_;
    std::condition_variable wake_thread_;
    std::chrono::milliseconds wake_delay_{500};

#if defined(GTEST_INCLUDE_GTEST_GTEST_H_)
    friend class ExternalPortTest;
    FRIEND_TEST(ExternalPortTest, CreateDelete);
    FRIEND_TEST(ExternalPortTest, StartStop);
    FRIEND_TEST(ExternalPortTest, LowLevelApiBase);
    FRIEND_TEST(ExternalPortTest, ProcessQueue);
#endif
};

}  // namespace cma::world

#endif  // external_port_h__
