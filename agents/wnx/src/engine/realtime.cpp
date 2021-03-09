// Windows Tools
#include "stdafx.h"

#include "realtime.h"

#include <time.h>

#include <chrono>
#include <string>
#include <string_view>

#include "asio.h"
#include "cfg.h"
#include "encryption.h"
#include "fmt/format.h"
#include "logger.h"
#include "providers/df.h"
#include "providers/mem.h"
#include "providers/p_perf_counters.h"
#include "service_processor.h"
#include "tools/_misc.h"

namespace cma::rt {

// gathers all data in one packet, optionally encrypt
// on error returns empty block
// also empty block on no data
RtBlock PackData(std::string_view Output,
                 const cma::encrypt::Commander* Crypt) {
    if (Output.empty()) {
        XLOG::d("No data to pack");
        return {};
    }

    auto encrypted = Crypt != nullptr;
    auto hdr = encrypted ? kEncryptedHeader : kPlainHeader;

    RtBlock block;
    block.resize(kHeaderSize + kTimeStampSize + Output.size());
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

    memcpy(p, Output.data(), Output.size());

    if (!encrypted) return block;

    // encryption block
    // check for size increase
    auto nc_size = Crypt->CalcBufferOverhead(Output.size());
    if (!nc_size) return {};

    block.resize(kHeaderSize + kTimeStampSize + Output.size() + *nc_size);
    p = block.data();

    auto [success, sz] =
        Crypt->encode(p + kTimeStampSize + kHeaderSize, Output.size(),
                      Output.size() + *nc_size, true);

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

void Device::connectFrom(std::string_view Address, int Port,
                         const RtTable& Sections, std::string_view Passphrase,
                         int Timeout) {
    std::lock_guard lk(lock_);
    if (!started_) {
        XLOG::l(XLOG_FLINE + " Out  of Order call");
        return;
    }

    kick_time_ = std::chrono::steady_clock::now();
    ip_address_ = Address;
    port_ = Port;
    timeout_ = Timeout;
    kick_count_++;
    working_period_ = true;
    passphrase_ = Passphrase;
    resetSections();

    for (const auto& section : Sections) {
        if (cma::tools::IsEqual(section, "df")) {
            use_df_ = true;
        } else if (cma::tools::IsEqual(section, "mem")) {
            use_mem_ = true;
        } else if (cma::tools::IsEqual(section, "winperf_processor")) {
            use_winperf_processor_ = true;
        } else if (cma::tools::IsEqual(section, "test")) {
            use_test_ = true;
        } else {
            XLOG::d("Invalid real time section name '{}'", section);
        }
    }

    XLOG::d.i("Realtime kick from '{}' mem:{} df:{} winperf:{}", Address,
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

    if (thread_.joinable()) thread_.join();
}

// to decrease noise in source code
static void mainThreadReporter(std::string_view Text, const std::error_code& Ec,
                               std::string_view Address, int Port) {
    XLOG::l("{} - '{}':{}. Eror [{}], '{}'", Text, Address, Port, Ec.value(),
            Ec.message());
}

static bool connectSocket(asio::io_context& IoContext,
                          asio::ip::udp::socket& Socket,
                          std::string_view Address, int Port) {
    using namespace asio::ip;

    std::error_code ec;
    udp::resolver resolver(IoContext);
    auto res = resolver.resolve(Address, std::to_string(Port), ec);
    if (ec.value()) {
        mainThreadReporter("Can't Resolve", ec, Address, Port);
        return false;
    }
    asio::connect(Socket, res, ec);
    if (ec.value()) {
        mainThreadReporter("Can't Connect", ec, Address, Port);
        return false;
    }

    return true;
}

std::string Device::generateData() {
    std::string result;

    if (use_df_) {
        cma::provider::Df df;
        result += df.generateContent(cma::section::kUseEmbeddedName, true);
    }

    if (use_mem_) {
        cma::provider::Mem mem;
        result += mem.generateContent(cma::section::kUseEmbeddedName, true);
    }

    if (use_winperf_processor_) {
        result += cma::provider::BuildWinPerfSection(L"winperf", L"processor",
                                                     L"238");
    }

    if (use_test_) result += "<<<test>>>\n";

    return result;
}

static void UpdateCounterByEc(size_t& counter, std::error_code& ec) {
    if (ec.value())
        counter++;  // error, this is not good
    else
        counter = 0;
}

// #TODO overcomplicated function, to be re-factored
void Device::mainThread() noexcept {
    std::unique_lock lk(lock_);
    auto port = port_;
    auto ip_address = ip_address_;
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

    using namespace std::chrono;
    using namespace asio::ip;
    try {
        asio::io_context io_context;
        udp::socket sock(io_context);
        bool connected = false;
        bool connect_required =
            false;  // true on first connect or on change connect address
        size_t counter = 0;

        auto crypt = std::make_unique<cma::encrypt::Commander>(passphrase);
        if (passphrase.empty()) crypt.reset(nullptr);

        while (1) {
            std::unique_lock lk(lock_);
            connect_required = port != port_ || ip_address != ip_address_;
            port = port_;
            if (port == 0) connected = false;
            ip_address = ip_address_;
            auto last_moment = kick_time_ + std::chrono::seconds(timeout_);
            working_period_ = std::chrono::steady_clock::now() <= last_moment;
            if (passphrase != passphrase_) {
                // reallocate crypt engine
                passphrase = passphrase_;
                if (passphrase.empty())
                    crypt.reset(nullptr);
                else
                    crypt.reset(new cma::encrypt::Commander(passphrase));
            }

            lk.unlock();

            if (port && connect_required) {
                connected = connectSocket(io_context, sock, ip_address, port);
                counter = 0;
                if (connected) connect_required = false;
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
                    UpdateCounterByEc(counter, ec);

                    if (counter > 3)
                        mainThreadReporter("Can't Send", ec, ip_address, port);

                } else if (port == 0)
                    XLOG::l.i("Trace out '{}' Address='{}'", raw_data,
                              ip_address);
            }

            // wait for stop here TOO
            // check for 1000 ms timeout
            lk.lock();
            auto delay = 1000ms;
            cv_.wait_until(lk, steady_clock::now() + delay,
                           [this]() -> bool { return !started_; });

            if (!started_) break;
        }
    } catch (std::exception& e) {
        XLOG::l("Exception in RT thread: '{}'", e.what());
    }
}  // namespace cma::rt

}  // namespace cma::rt
