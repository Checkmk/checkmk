#include "stdafx.h"

#include "external_port.h"

#include <chrono>
#include <iostream>
#include <ranges>

#include "agent_controller.h"
#include "asio.h"
#include "cfg.h"
#include "encryption.h"
#include "realtime.h"

using asio::ip::tcp;
using namespace std::chrono_literals;
namespace rs = std::ranges;

// This namespace contains classes used for external communication, for example
// with Monitor
namespace cma::world {

void LogWhenDebugging(const ByteVector &send_back) noexcept {
    if (!tgt::IsDebug()) {
        return;
    }

    std::string s(send_back.begin(), send_back.end());
    auto t = tools::SplitString(s, "\n");
    XLOG::t.i("Send {} last string is {}", send_back.size(), t.back());
}

void AsioSession::read_ip() {
    XLOG::t("Get ip");
    auto self(shared_from_this());
    {
        std::scoped_lock l(data_lock_);
        received_.reset();
        remote_ip_.reset();
    }
    socket_.async_read_some(asio::buffer(data_, kMaxLength - 1),
                            [this, self](std::error_code ec, size_t length) {
                                std::scoped_lock l(data_lock_);
                                received_ = ec ? 0U : length;
                                cv_ready_.notify_one();
                            });
    std::unique_lock lk(data_lock_);
    bool timeout = cv_ready_.wait_until(
        lk, std::chrono::steady_clock::now() + 1000ms,
        [this]() -> bool { return received_.has_value(); });
    if (received_.has_value() &&
        received_.value() >= std::string_view{"::1"}.length()) {
        remote_ip_ = std::string{data_, *received_};
        XLOG::d.i("Get ip = {}", *remote_ip_);

    } else {
        socket_.cancel();
        received_.reset();
        XLOG::d("Get ip = Nothing {}", timeout ? "timeout" : "some error");
    }
}

size_t AsioSession::allocCryptBuffer(const cma::encrypt::Commander *commander) {
    if (nullptr == commander) return 0;

    if (!commander->blockSize().has_value()) {
        XLOG::l("Impossible situation, crypt engine is absent");
        return 0;
    }

    if (0 == commander->blockSize().value()) {
        XLOG::l("Impossible situation, block is too short");
        return 0;
    }

    size_t crypt_segment_size = 0;
    try {
        // calculating length and allocating persistent memory
        auto block_size = commander->blockSize().value();
        crypt_segment_size = (segment_size_ / block_size + 1) * block_size;
        crypt_buf_.resize(crypt_segment_size);
        XLOG::d.i("Encrypted output block {} bytes, crypt buffer {} bytes...",
                  block_size, crypt_segment_size);

    } catch (const std::exception &e) {
        XLOG::l.crit(XLOG_FUNC + " unexpected, but exception '{}'", e.what());
        return 0;
    }
    return crypt_segment_size;
}

// returns 0 on failure
static size_t WriteDataToSocket(asio::ip::tcp::socket &sock, const char *data,
                                size_t sz) {
    using namespace asio;

    if (nullptr == data) {
        XLOG::l.bp(XLOG_FUNC + " nullptr in");
        return 0;
    }

    // asio execution
    std::error_code ec;
    auto written_bytes =
        write(sock, buffer(data, sz), transfer_exactly(sz), ec);

    // error processing
    if (ec.value() != 0) {
        XLOG::l(XLOG_FUNC + " write [{}] bytes to socket failed [{}] '{}'", sz,
                ec.value(), ec.message());
        return 0;
    }

    return written_bytes;
}

// returns 0 on failure
static size_t WriteStringToSocket(asio::ip::tcp::socket &sock,
                                  std::string_view str) {
    return WriteDataToSocket(sock, str.data(), str.size());
}

// To send data
void AsioSession::do_write(const void *data_block, std::size_t data_length,
                           cma::encrypt::Commander *crypto_commander) {
    auto self(shared_from_this());

    const auto *data = static_cast<const char *>(data_block);
    auto crypt_buf_len = allocCryptBuffer(crypto_commander);

    while (0 != data_length) {
        // we will send data in relatively small chunks
        // asio is stupid enough and cannot send big data blocks
        auto to_send = std::min(data_length, segment_size_);

        constexpr bool async = false;
        if constexpr (async) {
            // code below is written in theory correct, but performance is
            // terrible and absolutely unpredictable. Left as a non working
            // reference
            asio::async_write(
                socket_, asio::buffer(data, to_send),
                [self, to_send, data_length](std::error_code ec,
                                             std::size_t length) {
                    XLOG::t.i(
                        "Send [{}] from [{}] data with code [{}] left to send [{}]",
                        length, to_send, ec.value(), data_length);
                });
        } else {
            // correct code is here
            size_t written_bytes = 0;
            if (nullptr != crypto_commander) {
                if (0 == crypt_buf_len) {
                    XLOG::l("Encrypt is requested, but encryption is failed");
                    return;
                }

                // encryption
                auto *buf = crypt_buf_.data();
                memcpy(buf, data, to_send);
                auto [success, len] = crypto_commander->encode(
                    buf, to_send, crypt_buf_len, data_length == to_send);
                // checking
                if (!success) {
                    XLOG::l.crit(XLOG_FUNC + "CANNOT ENCRYPT {}.", len);
                    return;
                }

                // sending
                // suboptimal method, but one additional packet pro 1 minute
                // means for TCP nothing. Still candidate to optimize
                if (static_cast<const void *>(data) == data_block)
                    WriteStringToSocket(socket_, cma::rt::kEncryptedHeader);

                written_bytes = WriteDataToSocket(socket_, buf, len);

            } else
                written_bytes = WriteDataToSocket(socket_, data, to_send);

            XLOG::t.i("Send [{}] from [{}] data to send [{}]", written_bytes,
                      to_send, data_length);
        }

        // send;
        data_length -= to_send;
        data += to_send;
    }
}

}  // namespace cma::world

namespace cma::world {

namespace {
template <typename V>
std::pair<bool, size_t> PutOnQueue(std::mutex &lock, std::queue<V> &queue,
                                   V value) {
    bool loaded = false;
    std::unique_lock lk(lock);
    auto size = queue.size();
    if (size < kMaxSessionQueueLength) {
        queue.push(std::move(value));
        loaded = true;
        size = queue.size();
    }
    lk.unlock();
    return {loaded, size};
}

template <typename V>
V GetFromQueue(std::mutex &lock, std::queue<V> &queue) {
    std::unique_lock lk(lock);

    if (queue.empty()) {
        return {};
    }
    auto v = queue.front();
    queue.pop();
    auto sz = queue.size();
    lk.unlock();

    XLOG::t.i("Found connection on queue, in queue left[{}]", sz);
    return v;
}

}  // namespace

void ExternalPort::wakeThreadConditionally(bool wake, size_t sz) {
    if (wake) {
        wakeThread();
        XLOG::t.i("Put on queue, size is [{}]", sz);
    } else {
        XLOG::l("queue is overflown");
    }
}

void ExternalPort::putOnQueue(AsioSession::s_ptr asio_session) {
    const auto [stored, size] =
        PutOnQueue(queue_lock_, session_queue_, std::move(asio_session));

    wakeThreadConditionally(stored, size);
}

void ExternalPort::putOnQueue(const std::string &request) {
    const auto [stored, size] =
        PutOnQueue(queue_lock_, request_queue_, request);

    wakeThreadConditionally(stored, size);
}

namespace {}

/// may return empty shared ptr
AsioSession::s_ptr ExternalPort::getSession() {
    return GetFromQueue(queue_lock_, session_queue_);
}

std::string ExternalPort::getRequest() {
    return GetFromQueue(queue_lock_, request_queue_);
}

void ExternalPort::timedWaitForSession() {
    using namespace std::chrono;
    std::unique_lock lk(wake_lock_);
    wake_thread_.wait_until(lk, steady_clock::now() + wake_delay_,
                            [this]() { return entriesInQueue() != 0; });
}
#define TEST_RESTART_OVERLOAD  // should be defined in production

//#define TEST_OVERLOAD_MEMORY
// internal testing code
#if defined(TEST_OVERLOAD_MEMORY)
// a bit complicated method to eat memory in release target
static std::vector<std::unique_ptr<char>> bad_vector;
#endif

static void OverLoadMemory() {
#if defined(TEST_OVERLOAD_MEMORY)
#pragma message("**************************************")
#pragma message("ATTENTION: Your code tries to eat RAM!")
#pragma message("**************************************")
    // this code is intentionally left here as example
    // how to allocate a lot of memory and to verify protection
    bad_vector.emplace_back(new char[20'000'000]);
    auto data = bad_vector.back().get();
    memset(data, 1, 20'000'000);  // must for the release
#endif
}

bool IsIpAllowedAsException(const std::string &ip) {
    return ac::IsRunController(cfg::GetLoadedConfig()) &&
           (ip == "127.0.0.1" || ip == "::1");
}

namespace {
std::vector<Modus> local_connection_moduses{Modus::service, Modus::test,
                                            Modus::integration};

bool AllowLocalConnection() {
    return rs::find(local_connection_moduses, GetModus()) !=
           local_connection_moduses.end();
}
}  // namespace

void ExternalPort::processSession(const ReplyFunc &reply,
                                  AsioSession::s_ptr session) {
    const auto [ip, p, ipv6] = GetSocketInfo(session->currentSocket());
    XLOG::d.i("Connected from '{}' ipv6:{} port: {} <- queue", ip, ipv6, p);

    OverLoadMemory();
    // controller can contact us
    const bool local_connection = ip == "127.0.0.1" || ip == "::1";
    if (cfg::groups::global.isIpAddressAllowed(ip) || local_connection) {
        if (local_connection && AllowLocalConnection()) {
            session->read_ip();
        }
        session->start(reply);

        // check memory block, terminate service if memory is
        // overused
        if (!wtools::monitor::IsAgentHealthy()) {
            XLOG::l.crit("Memory usage is too high [{}]",
                         wtools::GetOwnVirtualSize());
#if defined(TEST_RESTART_OVERLOAD)
            if (GetModus() == Modus::service) {
                std::terminate();
            }
#else
#pragma message("**************************************")
#pragma message("ATTENTION: Your has no RESTART on overload")
#pragma message("**************************************")
#endif
        }
    } else {
        XLOG::d("Address '{}' is not allowed, this call should happen", ip);
    }
}

namespace {
/// Requests are normally supplied through main mailslot
struct RequestInfo {
    std::string ip;
    std::string comment;
};
RequestInfo ParseRequest(const std::string &request) {
    std::string s = request;
    tools::AllTrim(s);
    auto table = tools::SplitString(s, " ", 1);
    if (table.size() != 2) {
        XLOG::l.e("Invalid request '{}'", request);
        return {.ip = {}, .comment = {}};
    }
    return {.ip{table[0]}, .comment{table[1]}};
}
}  // namespace

void ExternalPort::processRequest(const ReplyFunc &reply,
                                  const std::string &request) {
    XLOG::d.i("Request is '{}'", request);
    auto r = ParseRequest(request);
    if (r.ip.empty()) {
        XLOG::l.e("Invalid request '{}'", request);
        return;
    }

    auto send_back = reply(r.ip);
    if (send_back.empty()) {
        XLOG::d.i("No data to send");
        return;
    }

    // TODO: SEND DATA TO MAILSLOT
    // auto crypt = encrypt::MakeCrypt();
    //  do_write(send_back.data(), send_back.size(), crypt.get());
    XLOG::d.i("Send [{}] bytes of data", send_back.size());

    LogWhenDebugging(send_back);
}

/// singleton thread
void ExternalPort::processQueue(const world::ReplyFunc &reply) {
    while (true) {
        try {
            if (auto as = getSession(); as) {
                processSession(reply, std::move(as));
            }
            if (auto r = getRequest(); !r.empty()) {
                processRequest(reply, r);
            }
            timedWaitForSession();

            if (isShutdown()) {
                break;
            }
        } catch (const std::exception &e) {
            XLOG::l.bp(XLOG_FUNC + " Unexpected exception '{}'", e.what());
        }
    }

    XLOG::l.i("Exiting process queue");
}

void ExternalPort::wakeThread() {
    std::lock_guard l(wake_lock_);
    wake_thread_.notify_one();
}

bool sinkProc(const cma::world::AsioSession::s_ptr &asio_session,
              ExternalPort *ex_port) {
    if (ex_port != nullptr) {
        ex_port->putOnQueue(asio_session);
    }
    return true;
}

// Main IO thread
// MAY BE RESTARTED if we have new port/ipv6 mode in config
void ExternalPort::ioThreadProc(const ReplyFunc &reply_func, uint16_t port,
                                LocalOnly local_only,
                                std::optional<uint32_t> controller_pid) {
    XLOG::d.i(XLOG_FUNC + " started");
    // all threads must control exceptions
    try {
        asio::io_context context;
        auto ipv6 = cfg::groups::global.ipv6();

        // Asio IO server start
        XLOG::l.i("Starting IO ipv6:{}, used port:{}", ipv6, port);
        ExternalPort::server sock(context, ipv6, port, local_only,
                                  controller_pid);
        sock.run_accept(sinkProc, this);
        registerAsioContext(&context);

        // server thread start
        auto processor_thread =
            std::thread(&ExternalPort::processQueue, this, reply_func);

        // tcp body
        auto ret = context.run();  // run itself
        XLOG::t(XLOG_FUNC + " ended context with code[{}]", ret);

        if (processor_thread.joinable()) {
            processor_thread.join();
        }

        // no more reliable context here, delete it
        if (!registerAsioContext(nullptr)) {
            XLOG::l.i(XLOG_FUNC + " terminated from outside");
        }
        XLOG::l.i("IO ends...");

    } catch (std::exception &e) {
        registerAsioContext(nullptr);  // cleanup
        std::cerr << "Exception: " << e.what() << "\n";
        XLOG::l(XLOG::kCritError)("IO broken with exception {}", e.what());
    }
}

// Main mailslot thread
void ExternalPort::mailslotThreadProc(const ReplyFunc &reply_func,
                                      uint32_t controller_pid) {
    XLOG::d.i(XLOG_FUNC + " started");
    try {
        auto processor_thread =
            std::thread(&ExternalPort::processQueue, this, reply_func);

        if (processor_thread.joinable()) {
            processor_thread.join();
        }
        XLOG::l.i("IO ends...");

    } catch (std::exception &e) {
        std::cerr << "Exception: " << e.what() << "\n";
        XLOG::l(XLOG::kCritError)("IO broken with exception {}", e.what());
    }
}

/// starts thread
/// can fail when thread is already running
bool ExternalPort::startIo(const ReplyFunc &reply_func,
                           const IoParam &io_param) {
    std::lock_guard lk(io_thread_lock_);
    if (io_thread_.joinable()) {  // thread is in exec state
        return false;
    }

    shutdown_thread_ = false;  // reset potentially dropped flag

    if (io_param.port == 0 && !io_param.pid.has_value()) {
        XLOG::l("This is not allowed, fix code");
        return false;
    }

    io_thread_ =
        io_param.port == 0
            ? std::thread(&ExternalPort::mailslotThreadProc, this, reply_func,
                          io_param.pid.value())
            : std::thread(&ExternalPort::ioThreadProc, this, reply_func,
                          io_param.port, io_param.local_only, io_param.pid);
    io_started_ = true;
    return true;
}

/// blocking call, signals thread and wait
void ExternalPort::shutdownIo() {
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

size_t ExternalPort::entriesInQueue() const {
    std::scoped_lock lk(io_thread_lock_);
    return std::max(session_queue_.size(), request_queue_.size());
}

void ExternalPort::server::run_accept(SinkFunc sink, ExternalPort *ext_port) {
    acceptor_.async_accept(socket_, [this, sink, ext_port](std::error_code ec) {
        if (ec.value()) {
            XLOG::l("Error on connection [{}] '{}'", ec.value(), ec.message());
        } else {
            try {
                auto [peer_ip, peer_port, ipv6] = GetSocketInfo(socket_);
                XLOG::d.i("Connected from '{}:{}' ipv6 :{} -> queue", peer_ip,
                          peer_port, ipv6);
                auto x = std::make_shared<AsioSession>(std::move(socket_));

                auto process_allowed = !controller_pid_.has_value() ||
                                       wtools::CheckProcessUsePort(
                                           port_, *controller_pid_, peer_port);

                if (process_allowed &&
                    (cfg::groups::global.isIpAddressAllowed(peer_ip) ||
                     IsIpAllowedAsException(peer_ip)))
                    sink(x, ext_port);
                else {
                    XLOG::d("Connection forbidden: address '{}' process {}",
                            process_allowed ? "allowed" : "not allowed");
                }

            } catch (const std::system_error &e) {
                if (e.code().value() == WSAECONNRESET) {
                    XLOG::l(" Client closed connection");
                } else {
                    XLOG::l(" Thrown unexpected exception '{}' with value {}",
                            e.what(), e.code().value());
                }
            } catch (const std::exception &e) {
                XLOG::l(" Thrown unexpected exception '{}'", e.what());
            }
        }

        // inside we have async call, this is not recursion
        run_accept(sink, ext_port);
    });
}

}  // namespace cma::world
