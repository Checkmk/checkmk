// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#pragma once

#ifndef STOP_WATCH_H
#define STOP_WATCH_H
#include <chrono>
#include <cstdint>
#include <mutex>

#include "tools/_raii.h"

namespace wtools {
class StopWatch {
public:
    StopWatch() = default;
    StopWatch(const StopWatch &sw) {
        const auto [c, t] = sw.get();
        counter_ = c;
        time_ = t;
        started_ = false;
    }
    StopWatch(StopWatch &&sw) noexcept {
        const auto [c, t] = sw.getAndReset();
        counter_ = c;
        time_ = t;
        started_ = false;
    }
    StopWatch &operator=(const StopWatch &sw) {
        std::lock_guard lk(lock_);
        const auto [c, t] = sw.get();
        counter_ = c;
        time_ = t;
        started_ = false;
        return *this;
    }
    StopWatch &operator=(StopWatch &&sw) noexcept {
        std::lock_guard lk(lock_);
        const auto [c, t] = sw.getAndReset();
        counter_ = c;
        time_ = t;
        started_ = false;
        return *this;
    }
    ~StopWatch() = default;

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
        const auto t = std::chrono::steady_clock::now();
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
        const auto t = std::chrono::steady_clock::now();
        const auto c =
            std::chrono::duration_cast<std::chrono::microseconds>(t - pos_);
        return c.count();
    }

    bool isStarted() const noexcept { return started_; }

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
        return counter_ != 0U ? time_.count() / counter_ : 0;
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

    std::chrono::time_point<std::chrono::steady_clock> pos() const {
        std::lock_guard lk(lock_);
        return pos_;
    }

private:
    mutable std::mutex lock_;
    uint64_t counter_ = 0;
    std::chrono::microseconds time_{};
    std::chrono::microseconds last_{};
    bool started_ = false;
    std::chrono::time_point<std::chrono::steady_clock> pos_;
};

}  // namespace wtools

#endif  // STOP_WATCH_H
