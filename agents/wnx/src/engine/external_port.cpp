#include "stdafx.h"

#include <iostream>

#include "asio.h"
#include "external_port.h"

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
                do_write(internal_data, strlen(internal_data) + 1);
            }
        });
}

// To send data
void AsioSession::do_write(const void *Data, std::size_t Length) {
    auto self(shared_from_this());

    const size_t segment_size = 48 * 1024;
    const char *data = static_cast<const char *>(Data);

    while (Length) {
        // we will send data in relatively small chunks
        // asio is stupid enough and cannot send big data blocks
        auto to_send = std::min(Length, segment_size);

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
            auto ret = asio::write(socket_, asio::buffer(data, to_send),
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
    try {
        // all threads must control exceptions
        XLOG::l.t("Starting IO...");  // important and rare, place in the log
        for (;;) {
            // this is gtested, be sure you will get data here
            if (owner_) owner_->preContextCall();

            // asio magic here
            asio::io_context context;
            ExternalPort::server s(context, port_, Reply);

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
