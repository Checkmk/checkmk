// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// provides basic api to start and stop service

#pragma once
#ifndef answer_h__
#define answer_h__

#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <mutex>
#include <string>
#include <vector>

#include "common/stop_watch.h"

namespace cma::srv {
using AnswerId = std::chrono::time_point<std::chrono::steady_clock>;
inline AnswerId GenerateAnswerId() { return std::chrono::steady_clock::now(); }

inline auto AnswerIdToNumber(AnswerId id) {
    return id.time_since_epoch().count();
}
inline std::wstring AnswerIdToWstring(AnswerId id) {
    return std::to_wstring(AnswerIdToNumber(id));
}

// MAIN CLASS to gather all data for CMA on kick from Monitoring Site
// During creation assigned unique id to be used for communication with
// plugins and providers
// Answer consists from 0 or more segments
// Segments is provide from execution unit(exe or internal thread)
class AsyncAnswer {
public:
    using DataBlock = std::vector<uint8_t>;
    enum class Order { random, plugins_last };
    AsyncAnswer()
        : tp_id_(GenerateAnswerId()), awaited_segments_(0), timeout_(5) {}

    bool isAnswerOlder(std::chrono::milliseconds period) const;

    auto getId() const { return tp_id_; }

    bool isAnswerInUse() const {
        std::lock_guard lk(lock_);
        return isAnswerInUseNoLock();
    }

    void dropAnswer();

    bool waitAnswer(std::chrono::milliseconds to_wait);

    void exeKickedCount(int count) {
        std::lock_guard lk(lock_);
        awaited_segments_ = count;
    }

    DataBlock getDataAndClear();

    bool prepareAnswer(std::string_view ip);
    bool addSegment(const std::string &section_name,  // name
                    const AnswerId &answer_id,        // "password"
                    const std::vector<uint8_t> &data  // data for section
    );

    bool tryBreakWait();

    std::vector<std::string> segmentNameList() const;

    auto awaitingSegments() const {
        std::lock_guard lk(lock_);
        return awaited_segments_;
    }
    auto receivedSegments() const {
        std::lock_guard lk(lock_);
        return received_segments_;
    }
    void newTimeout(int timeout) {
        std::lock_guard lk(lock_);
        if (timeout > timeout_) {
            timeout_ = timeout;
        }
    }
    int timeout() const {
        std::lock_guard lk(lock_);
        return timeout_;
    }

    std::string getIp() const {
        std::lock_guard lk(lock_);
        return external_ip_;
    }

    const wtools::StopWatch &getStopWatch() const { return sw_; }

private:
    wtools::StopWatch sw_;

    bool isAnswerInUseNoLock() const {
        return !external_ip_.empty() || !segments_.empty() ||
               awaited_segments_ != 0 || received_segments_ != 0;
    }

    struct SegmentInfo {
        std::string name_;
        size_t length_;
    };

    void dropDataNoLock();

    mutable std::mutex lock_;

    std::string external_ip_;  // who initiated request
    AnswerId tp_id_;           // time when request hit processing,
                               // also used as a password
                               // for plugins and providers too late or too lazy
    DataBlock data_;           // our pretty data

    uint32_t awaited_segments_;   // how many sections are awaited
    uint32_t received_segments_;  // how many sections are received

    int timeout_;  // seconds

    std::vector<SegmentInfo> segments_;

    // awaiting_sections_ used for predicate
    std::condition_variable cv_ready_;

    DataBlock plugins_;
    DataBlock local_;

    const Order order_{Order::plugins_last};
};
}  // namespace cma::srv

#endif  // answer_h__
