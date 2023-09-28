// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#pragma once
#ifndef EXTERNAL_PORT_H
#define EXTERNAL_PORT_H

#include <chrono>
#include <cstdint>
#include <functional>
#include <queue>

#include "asio.h"
#include "cfg.h"
#include "common/cfg_info.h"
#include "encryption.h"
#include "logger.h"

namespace cma::world {
using ReplyFunc =
    std::function<std::vector<uint8_t>(const std::string &ip_addr)>;
}  // namespace cma::world

namespace cma::world {

/// Defines visibility of local socket for external world
enum class LocalOnly { yes, no };
constexpr size_t kMaxSessionQueueLength{16};

bool IsIpAllowedAsException(const std::string &ip) noexcept;

/// prints last line of the output in the log
/// to see how correct was an answer
void LogWhenDebugging(const ByteVector &send_back) noexcept;

/// implements asio logic for the low level TCP transport:
/// based on ASIO example
/// NOT THREAD SAFE
class AsioSession : public std::enable_shared_from_this<AsioSession> {
public:
    using s_ptr = std::shared_ptr<AsioSession>;

    explicit AsioSession(asio::ip::tcp::socket socket)
        : socket_(std::move(socket)) {}
    ~AsioSession() { XLOG::d("destroy connection"); }

    void start(const ReplyFunc &reply_func) {
        auto send_back = reply_func(getCurrentRemoteIp());

        if (send_back.empty()) {
            XLOG::d.i("No data to send");
            return;
        }
        auto crypt = cma::encrypt::MakeCrypt();
        do_write(send_back.data(), send_back.size(), crypt.get());
        XLOG::d.i("Send [{}] bytes of data", send_back.size());

        LogWhenDebugging(send_back);
    }

    const asio::ip::tcp::socket &currentSocket() const noexcept {
        return socket_;
    }

    /// `hack` to obtain ip from controller
    void read_ip();

private:
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
                  const encrypt::Commander *crypto_commander);

    asio::ip::tcp::socket socket_;

    constexpr static size_t kMaxLength{1024};
    char data_[kMaxLength] = {0};
    std::optional<size_t> received_;
    std::condition_variable cv_ready_;
    mutable std::mutex data_lock_;
    std::optional<std::string> remote_ip_;

    const size_t segment_size_ = size_t{48} * 1024;
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

enum class IpMode {
    ipv4,
    ipv6

};

struct SocketInfo {
    std::string peer_ip;
    uint16_t peer_port;
    IpMode ip_mode;
    static SocketInfo empty() {
        return {.peer_ip{""}, .peer_port = 0U, .ip_mode = IpMode::ipv4};
    }
};

inline SocketInfo GetSocketInfo(const asio::ip::tcp::socket &sock) noexcept {
    std::error_code ec;
    const auto remote_ep = sock.remote_endpoint(ec);
    if (ec) {
        XLOG::l("Error on socket [{}] with '{}'", ec.value(), ec.message());
        return SocketInfo::empty();
    }

    try {
        auto addr = remote_ep.address();
        auto ip = addr.to_string();
        auto mode = addr.is_v6() ? IpMode::ipv6 : IpMode::ipv4;
        return {.peer_ip{ip}, .peer_port = remote_ep.port(), .ip_mode = mode};
    } catch (const std::exception &e) {
        XLOG::d("Something goes wrong with socket '{}'", e);
    }
    return SocketInfo::empty();
}

class ExternalPort final : public std::enable_shared_from_this<ExternalPort> {
public:
    // ctor&dtor
    explicit ExternalPort(wtools::BaseServiceProcessor * /* owner*/) {}

    ~ExternalPort() = default;

    ExternalPort(const ExternalPort &) = delete;
    ExternalPort(ExternalPort &&) = delete;
    ExternalPort &operator=(const ExternalPort &) = delete;
    ExternalPort &operator=(ExternalPort &&) = delete;

    struct IoParam {
        uint16_t port{0};  /// can be 0 for mailslot
        LocalOnly local_only{false};
        std::optional<uint32_t> pid;
    };

    // Main API
    bool startIo(const ReplyFunc &reply_func, const IoParam &io_param);
    bool startIoTcpPort(const ReplyFunc &reply_func, uint16_t port) {
        return startIo(
            reply_func,
            {.port = port, .local_only = LocalOnly::no, .pid = std::nullopt});
    }
    bool startIoMailSlot(const ReplyFunc &reply_func, uint32_t pid) {
        return startIo(reply_func,
                       {.port = 0U, .local_only = LocalOnly::yes, .pid = pid});
    }
    void shutdownIo();

    // Supplementary API
    bool isIoStarted() const noexcept { return io_started_; }

    void putOnQueue(AsioSession::s_ptr asio_session);
    void putOnQueue(const std::string &request);
    size_t entriesInQueue() const;

private:
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
        void run_accept(const SinkFunc &sink, ExternalPort *ext_port);

    private:
        uint16_t port_{0U};
        std::optional<uint32_t> controller_pid_;
        // ASIO magic
        asio::ip::tcp::acceptor acceptor_;
        asio::ip::tcp::socket socket_;

        // the only supported now
        const bool mode_one_shot_{cfg::IsOneShotMode()};
    };

protected:
    // asio sessions API
    AsioSession::s_ptr getSession();
    std::string getRequest();
    void processQueue(const cma::world::ReplyFunc &reply);
    void wakeThreadConditionally(bool wake, size_t sz);
    void wakeThread();
    void timedWaitForSession();
    void processSession(const ReplyFunc &reply, AsioSession::s_ptr session);
    void processRequest(const ReplyFunc &reply, const std::string &request,
                        const encrypt::Commander *commander) const;

    bool isShutdown() const noexcept {
        std::lock_guard lk(io_thread_lock_);
        return shutdown_thread_;
    }

    /// returns thread continue status
    bool registerAsioContext(asio::io_context *context) {
        std::lock_guard lk(io_thread_lock_);
        if (shutdown_thread_) {
            context_ = nullptr;
            return false;
        }
        context_ = context;
        return true;
    }

    void stopExecution() {
        std::lock_guard lk(io_thread_lock_);
        XLOG::l.t("Stopping execution");
        if (context_ != nullptr) {
            context_->stop();  // non blocking call to stop IO
        }
        shutdown_thread_ = true;
    }

    void ioThreadProc(const ReplyFunc &reply_func, uint16_t port,
                      LocalOnly local_only,
                      std::optional<uint32_t> controller_pid);

    void mailslotThreadProc(const ReplyFunc &reply_func,
                            uint32_t controller_pid);

    // probably overkill, but we want to restart and want to be sure that
    // everything is going smooth
    mutable std::mutex io_thread_lock_;
    std::thread io_thread_;
    bool shutdown_thread_{false};
    bool io_started_{false};

    asio::io_context *context_{nullptr};

    // asio sessions queue data
    mutable std::mutex queue_lock_;
    std::queue<std::shared_ptr<AsioSession>> session_queue_;  // fallback mode
    std::queue<std::string> request_queue_;                   // standard mode

    // asio sessions waker
    mutable std::mutex wake_lock_;
    std::condition_variable wake_thread_;
    std::chrono::milliseconds wake_delay_{500};

    asio::io_context io_context_;  // may be used by ioThreadProc
};

bool SendDataToMailSlot(const std::string &mailslot_name,
                        const std::vector<uint8_t> &data_block,
                        const encrypt::Commander *commander);

}  // namespace cma::world

#endif  // EXTERNAL_PORT_H
