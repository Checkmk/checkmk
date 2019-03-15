#include "stdafx.h"

#include <iostream>

#include "asio.h"

#include "cfg.h"

#include "external_port.h"

#include "encryption.h"

using asio::ip::tcp;

// This namespace contains classes used for external communication, for example
// with Monitor
namespace cma::world {

// below is working example from asio
// verified and working, Example is Echo TCP
// try not damage it

// will not used normally by agent
void AsioSession::do_read() {
    auto self(shared_from_this());
    socket_.async_read_some(
        asio::buffer(data_, kMaxLength),  // data will be ignored
        [this, self](std::error_code ec, std::size_t length) {
            if (!ec) {
                char internal_data[124] = "Answer!\n";
                do_write(internal_data, strlen(internal_data) + 1, nullptr);
            }
        });
}

size_t AsioSession::allocCryptBuffer(
    const cma::encrypt::Commander *Crypt) noexcept {
    if (!Crypt) return 0;

    if (!Crypt->blockSize().has_value()) {
        XLOG::l("Impossible situation, crypt engine is absent");
        return 0;
    }

    if (!Crypt->blockSize().value()) {
        XLOG::l("Impossible situation, block is too short");
        return 0;
    }

    size_t crypt_segment_size = 0;
    try {
        // calculating length and allocating persistent memory
        auto block_size = Crypt->blockSize().value();
        crypt_segment_size = (segment_size_ / block_size + 1) * block_size;
        crypt_buf_.reset(new char[crypt_segment_size]);
        XLOG::d.i("Encrypted output block {} bytes, crypt buffer {} bytes...",
                  block_size, crypt_segment_size);

    } catch (const std::exception &e) {
        XLOG::l.crit(XLOG_FUNC + " unexpected, but exception '{}'", e.what());
        return 0;
    }
    return crypt_segment_size;
}
// To send data
void AsioSession::do_write(const void *Data, std::size_t Length,
                           cma::encrypt::Commander *Crypt) {
    auto self(shared_from_this());

    auto data = static_cast<const char *>(Data);
    auto crypt_buf_len = allocCryptBuffer(Crypt);

    while (Length) {
        // we will send data in relatively small chunks
        // asio is stupid enough and cannot send big data blocks
        auto to_send = std::min(Length, segment_size_);

        const bool async = false;
        if (async) {
            // code below is written in theory correct, but performance is
            // terrible and absolutely unpredictable
            asio::async_write(
                socket_, asio::buffer(data, to_send),
                [this, self, to_send, Length](std::error_code ec,
                                              std::size_t length) {
                    XLOG::t.i(
                        "Send {} from {} data with code {} left to send {}",
                        length, to_send, ec.value(), Length);
                    if (!ec && !mode_one_shot_ && length == Length) {
                        do_read();
                    }
                });
        } else {
            // correct code is here
            size_t ret = 0;
            if (Crypt) {
                if (!crypt_buf_len) {
                    XLOG::l(
                        "No data sending, encrypt is requested, but encryption is failed");
                    return;
                }
                // encryption
                auto buf = crypt_buf_.get();
                memcpy(buf, data, to_send);
                auto [success, len] = Crypt->encode(buf, to_send, crypt_buf_len,
                                                    Length == to_send);
                // sending
                if (success) {
                    ret = asio::write(socket_, asio::buffer(buf, len),
                                      asio::transfer_exactly(len));
                } else {
                    ret = 0;
                    XLOG::l.crit("CANNOT ENCRYPT {}.", len);
                    return;
                }
            } else
                ret = asio::write(socket_, asio::buffer(data, to_send),
                                  asio::transfer_exactly(to_send));
            XLOG::t.i("Send {} from {} data to send {}", ret, to_send, Length);
        }

        // send;
        Length -= to_send;
        data += to_send;
    }
}

}  // namespace cma::world

namespace cma::world {

// Main IO thread
// OneShot - true, CMK way, connect, send data back, disconnect
//         - false, accept send data back, no disconnect
void ExternalPort::ioThreadProc(cma::world::ReplyFunc Reply) {
    XLOG::t(XLOG_FUNC + " started");
    // all threads must control exceptions
    try {
        auto ipv6 = cma::cfg::groups::global.ipv6();

        XLOG::l.t("Starting IO ipv6:{}, proposed port:{}...", ipv6,
                  default_port_);  // important and rare, place in the log
        for (;;) {
            auto ipv6 = cma::cfg::groups::global.ipv6();
            auto port = default_port_ == 0 ? cma::cfg::groups::global.port()
                                           : default_port_;
            // this is gtested, be sure you will get data here
            if (owner_) owner_->preContextCall();

            // asio magic here
            asio::io_context context;
            ExternalPort::server s(context, ipv6, port, Reply);

            // execution of listen - accept - disconnect
            if (mode_one_shot_) {
                // to be able from outside thread stop the context
                if (!registerContext(&context)) {
                    XLOG::l.i(XLOG_FUNC + " terminated from outside 1");
                    break;
                }

                // tcp body
                auto ret = context.run();  // run itself
                XLOG::t(XLOG_FUNC + " one shot ended {}", ret);

                // now wait for end of sending data

                // no more reliable context here, delete it
                if (!registerContext(nullptr))  // no more stopping
                {
                    XLOG::l.i(XLOG_FUNC + " terminated from outside 2");
                    break;
                }
            } else {
                // for the future
                context.run_one();
                break;
            }
        }
        XLOG::l.i("IO ends...");
    } catch (std::exception &e) {
        registerContext(nullptr);  // cleanup
        std::cerr << "Exception: " << e.what() << "\n";
        XLOG::l(XLOG::kCritError)("IO broken with exception {}", e.what());
    }
}

// runs thread
// can fail when thread is already running
bool ExternalPort::startIo(cma::world::ReplyFunc Reply) {
    std::lock_guard lk(io_thread_lock_);
    if (io_thread_.joinable()) return false;  // thread is in exec state

    shutdown_thread_ = false;  // reset potentially dropped flag

    io_thread_ = std::thread(&ExternalPort::ioThreadProc, this, Reply);
    io_started_ = true;
    return true;
}

// blocking call, signals thread and wait
void ExternalPort::shutdownIo() {
    // we just stopping, object is thread safe
    XLOG::l.i("Shutting down IO...");
    stopExecution();

    bool should_wait = false;
    {
        std::lock_guard lk(io_thread_lock_);
        should_wait = io_thread_.joinable();  // normal execution
        io_started_ = false;
    }

    if (should_wait) {
        io_thread_.join();
    }
}

}  // namespace cma::world
