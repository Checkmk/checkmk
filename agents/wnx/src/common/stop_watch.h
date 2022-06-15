// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// wtools.h
//
// Windows Specific Tools
//
#pragma once

#ifndef stop_watch_h__
#define stop_watch_h__
#include <chrono>
#include <cstdint>
#include <mutex>
#include <string>
#include <string_view>
#include <tuple>

#include "tools/_raii.h"

namespace wtools {
class StopWatch {
public:
    StopWatch() = default;
    StopWatch(const StopWatch &sw) {
        auto [c, t] = sw.get();
        counter_ = c;
        time_ = t;
        started_ = false;
    }
    StopWatch(StopWatch &&sw) noexcept {
        auto [c, t] = sw.getAndReset();
        counter_ = c;
        time_ = t;
        started_ = false;
    }
    StopWatch &operator=(const StopWatch &sw) {
        std::lock_guard lk(lock_);
        auto [c, t] = sw.get();
        counter_ = c;
        time_ = t;
        started_ = false;
        return *this;
    }
    StopWatch &operator=(StopWatch &&sw) noexcept {
        std::lock_guard lk(lock_);
        auto [c, t] = sw.getAndReset();
        counter_ = c;
        time_ = t;
        started_ = false;
        return *this;
    }

    void start() {
        std::lock_guard lk(lock_);
        if (started_) {
            return;
        }
        started_ = true;
        pos_ = std::chrono::steady_clock::now();
    }

    uint64_t stop() {
        std::lock_guard lk(lock_);
        if (!started_) {
            return 0;
        }
        started_ = false;
        counter_++;
        auto t = std::chrono::steady_clock::now();
        last_ = std::chrono::duration_cast<std::chrono::microseconds>(t - pos_);
        time_ += last_;
        return last_.count();
    }

    void skip() {
        std::lock_guard lk(lock_);
        started_ = false;
    }

    uint64_t check() const {
        std::lock_guard lk(lock_);
        if (!started_) {
            return 0;
        }
        auto t = std::chrono::steady_clock::now();
        auto c =
            std::chrono::duration_cast<std::chrono::microseconds>(t - pos_);
        return c.count();
    }

    bool isStarted() const { return started_; }

    uint64_t getUsCount() const {
        std::lock_guard lk(lock_);
        return time_.count();
    }

    uint64_t getLastUsCount() const {
        std::lock_guard lk(lock_);
        return last_.count();
    }

    uint64_t getCount() const {
        std::lock_guard lk(lock_);
        return counter_;
    }
    uint64_t getAverage() const {
        std::lock_guard lk(lock_);
        return counter_ != 0u ? time_.count() / counter_ : 0;
    }

    std::pair<uint64_t, std::chrono::microseconds> get() const {
        std::lock_guard lk(lock_);
        return {counter_, time_};
    }

    std::pair<uint64_t, std::chrono::microseconds> getAndReset() {
        std::lock_guard lk(lock_);
        ON_OUT_OF_SCOPE(counter_ = 0; time_ = std::chrono::milliseconds());
        started_ = false;
        return {counter_, time_};
    }

    void reset() {
        std::lock_guard lk(lock_);
        counter_ = 0;
        last_ = time_ = std::chrono::milliseconds();
        started_ = false;
        pos_ = std::chrono::time_point<std::chrono::steady_clock>();
    }

private:
    mutable std::mutex lock_;
    uint64_t counter_ = 0;
    std::chrono::microseconds time_{};
    std::chrono::microseconds last_{};
    bool started_ = false;
    std::chrono::time_point<std::chrono::steady_clock> pos_;
#if defined(GTEST_INCLUDE_GTEST_GTEST_H_)
    friend class Wtools;
    FRIEND_TEST(Wtools, StopWatch);
#endif
};

}  // namespace wtools

#endif  // stop_watch_h__
