// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef realtime_h__
#define realtime_h__

#include <condition_variable>
#include <mutex>
#include <string_view>
#include <thread>

#include "common/cfg_info.h"
#include "encryption.h"
#include "logger.h"

namespace cma::rt {

enum {
    kHeaderSize = 2,
    kTimeStampSize = 10,
    kDataOffset = kHeaderSize + kTimeStampSize
};

constexpr const std::string_view kEncryptedHeader = "00";
constexpr const std::string_view kPlainHeader = "99";

using RtBlock = std::vector<uint8_t>;
using RtTable = std::vector<std::string_view>;

// Crypt is nullptr when encryption is not required
RtBlock PackData(std::string_view Output, const cma::encrypt::Commander *Crypt);

// has internal thread
// should be start-stopped
// connectFrom is signal to start actual work thread
class Device {
public:
    Device() = default;
    ~Device() { clear(); }

    Device(const Device &) = delete;
    Device &operator=(const Device &) = delete;

    Device(Device &&) = delete;
    Device &operator=(Device &&) = delete;

    void stop();
    bool start();

    void connectFrom(std::string_view Address, int Port,
                     const RtTable &Sections, std::string_view Passphrase,
                     int Timeout = cma::cfg::kDefaultRealtimeTimeout);

    bool started() const noexcept { return started_; }

    bool working() const noexcept { return working_period_; }

private:
    void mainThread() noexcept;
    std::string generateData();

    void clear();
    void resetSections();

    // multi threading area
    mutable std::mutex lock_;
    std::thread thread_;
    std::condition_variable cv_;
    std::atomic<bool> started_ = false;
    std::chrono::steady_clock::time_point kick_time_;
    std::string ip_address_;
    std::string passphrase_;
    int port_ = 0;

    int timeout_ = cma::cfg::kDefaultRealtimeTimeout;
    uint64_t kick_count_ = 0;

    bool working_period_ = false;

    bool use_df_ = false;
    bool use_mem_ = false;
    bool use_winperf_processor_ = false;
    bool use_test_ = false;

#if defined(GTEST_INCLUDE_GTEST_GTEST_H_)
    friend class RealtimeTest;
    FRIEND_TEST(RealtimeTest, Base_Long);
    FRIEND_TEST(RealtimeTest, LowLevel);
#endif
};

}  // namespace cma::rt
#endif  // realtime_h__
