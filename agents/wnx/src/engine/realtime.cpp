// Windows Tools
#include "stdafx.h"

#include "realtime.h"

#include <fmt/format.h>
#include <time.h>

#include <chrono>
#include <string>
#include <string_view>

#include "asio.h"
#include "cfg.h"
#include "encryption.h"
#include "logger.h"
#include "providers/df.h"
#include "providers/mem.h"
#include "providers/p_perf_counters.h"
#include "service_processor.h"
#include "tools/_misc.h"

using namespace std::string_literals;
using namespace std::chrono_literals;

namespace cma::rt {

// gathers all data in one packet, optionally encrypt
// on error returns empty block
// also empty block on no data
RtBlock PackData(std::string_view output, const encrypt::Commander *crypt) {
    if (output.empty()) {
        XLOG::d("No data to pack");
        return {};
    }

    auto encrypted = crypt != nullptr;
    auto hdr = encrypted ? kEncryptedHeader : kPlainHeader;

    RtBlock block;
    block.resize(kHeaderSize + kTimeStampSize + output.size());
    auto p = block.data();

    // header
    memcpy(p, hdr.data(), kHeaderSize);
    p += kHeaderSize;

    // timestamp
    auto timestamp_buffer = fmt::format("{}", time(nullptr));

    auto allowed_to_copy =
        std::min(timestamp_buffer.size() + 1,  // trailing zero
                 static_cast<size_t>(kTimeStampSize));

    memcpy(p, timestamp_buffer.c_str(), allowed_to_copy);

    p += kTimeStampSize;

    memcpy(p, output.data(), output.size());

    if (!encrypted) {
        return block;
    }

    // encryption block
    // check for size increase
    auto nc_size = crypt->CalcBufferOverhead(output.size());
    if (!nc_size) {
        XLOG::l("Failed to calc buffer overhead");
        return {};
    }

    block.resize(kHeaderSize + kTimeStampSize + output.size() + *nc_size);
    p = block.data();

    auto [success, sz] =
        crypt->encode(p + kTimeStampSize + kHeaderSize, output.size(),
                      output.size() + *nc_size, true);

    if (success) {
        block.resize(sz + kTimeStampSize + kHeaderSize);
        return block;
    }

    XLOG::l("Failed to compress");

    return {};
}

void Device::clear() { stop(); }

void Device::resetSections() {
    use_df_ = false;
    use_mem_ = false;
    use_winperf_processor_ = false;
    use_test_ = false;
}

bool Device::start() {
    auto already_started = started_.exchange(true);
    if (already_started) {
        XLOG::d("RT Thread already started.");
        return false;
    }

    thread_ = std::thread(&Device::mainThread, this);
    return true;
}

void Device::connectFrom(std::string_view address, int port,
                         const RtTable &sections, std::string_view passphrase,
                         int timeout) {
    std::lock_guard lk(lock_);
    if (!started_) {
        XLOG::l("Out  of Order call");
        return;
    }

    kick_time_ = std::chrono::steady_clock::now();
    ip_address_ = address;
    port_ = port;
    timeout_ = timeout;
    kick_count_++;
    working_period_ = true;
    passphrase_ = passphrase;
    resetSections();

    for (const auto &section : sections) {
        if (tools::IsEqual(section, "df")) {
            use_df_ = true;
        } else if (tools::IsEqual(section, "mem")) {
            use_mem_ = true;
        } else if (tools::IsEqual(section, "winperf_processor")) {
            use_winperf_processor_ = true;
        } else if (tools::IsEqual(section, "test")) {
            use_test_ = true;
        } else {
            XLOG::d("Invalid real time section name '{}'", section);
        }
    }

    XLOG::d.i("Realtime kick from '{}' mem:{} df:{} winperf:{}", address,
              use_mem_, use_df_, use_winperf_processor_);

    cv_.notify_one();
}

void Device::stop() {
    std::unique_lock lk(lock_);
    if (started_) {
        started_ = false;
        cv_.notify_one();
    }
    lk.unlock();

    if (thread_.joinable()) {
        thread_.join();
    }
}

namespace {
void logError(std::string_view text, const std::error_code &ec,
              std::string_view address, int port) {
    XLOG::l("{} - '{}':{}. Eror [{}], '{}'", text, address, port, ec.value(),
            ec.message());
}

bool connectSocket(asio::io_context &io_context, asio::ip::udp::socket &socket,
                   std::string_view address, int port) {
    std::error_code ec;
    asio::ip::udp::resolver resolver(io_context);
    auto res = resolver.resolve(address, std::to_string(port), ec);
    if (ec.value()) {
        logError("Can't Resolve", ec, address, port);
        return false;
    }
    asio::connect(socket, res, ec);
    if (ec.value()) {
        logError("Can't Connect", ec, address, port);
        return false;
    }

    return true;
}

}  // namespace

std::string Device::generateData() {
    std::string result;

    if (use_df_) {
        provider::Df df;
        result += df.generateContent(section::kUseEmbeddedName, true);
    }

    if (use_mem_) {
        provider::Mem mem;
        result += mem.generateContent(section::kUseEmbeddedName, true);
    }

    if (use_winperf_processor_) {
        result +=
            provider::BuildWinPerfSection(L"winperf", L"processor", L"238");
    }

    if (use_test_) {
        result += "<<<test>>>\n";
    }

    return result;
}

// #TODO overcomplicated function, to be re-factored
void Device::mainThread() noexcept {
    std::unique_lock lk(lock_);
    auto port = port_;
    auto ip_address = ""s;  // set to invalid value, prevents race
    auto passphrase = passphrase_;
    lk.unlock();

    // on exit from thread we should drop/clear resources
    ON_OUT_OF_SCOPE({
        std::lock_guard lk(lock_);
        started_ = false;
        working_period_ = false;
        resetSections();
        port_ = 0;
    });

    try {
        asio::io_context io_context;
        asio::ip::udp::socket sock(io_context);
        bool connected = false;
        bool connect_required =
            false;  // true on first connect or on change connect address
        size_t counter = 0;

        auto crypt = std::make_unique<encrypt::Commander>(passphrase);
        if (passphrase.empty()) {
            crypt.reset(nullptr);
        }

        while (true) {
            std::unique_lock lk(lock_);
            connect_required = port != port_ || ip_address != ip_address_;
            port = port_;
            if (port == 0) {
                connected = false;
            }
            ip_address = ip_address_;
            auto last_moment = kick_time_ + std::chrono::seconds(timeout_);
            working_period_ = std::chrono::steady_clock::now() <= last_moment;
            if (passphrase != passphrase_) {
                passphrase = passphrase_;
                crypt.reset(passphrase.empty()
                                ? nullptr
                                : new encrypt::Commander(passphrase));
            }

            lk.unlock();

            if (port && connect_required) {
                connected = connectSocket(io_context, sock, ip_address, port);
                counter = 0;
                if (connected) {
                    connect_required = false;
                }
            }

            if (working_period_) {
                // transmit data to server
                auto raw_data = generateData();
                if (connected) {
                    auto packed_data = PackData(raw_data, crypt.get());

                    std::error_code ec;
                    sock.send(
                        asio::buffer(packed_data.data(), packed_data.size()), 0,
                        ec);

                    // errors reporting
                    if (ec.value()) {
                        counter++;  // error, this is not good
                        if (counter > 3) {
                            logError("Can't Send", ec, ip_address, port);
                        }
                    } else
                        counter = 0;
                }
            }

            // wait for stop here TOO
            // check for 1000 ms timeout
            lk.lock();
            auto delay = 1000ms;
            cv_.wait_until(lk, std::chrono::steady_clock::now() + delay,
                           [this]() -> bool { return !started_; });

            if (!started_) {
                break;
            }
        }
    } catch (std::exception &e) {
        XLOG::l("Exception in RT thread: '{}'", e.what());
    }
}

}  // namespace cma::rt
