// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// tails. You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#ifndef Queue_h
#define Queue_h

#include "config.h"  // IWYU pragma: keep
#include <atomic>
#include <condition_variable>
#include <mutex>
#include <optional>
#include <utility>

template <typename Storage>
class Queue {
    using storage_t = Storage;

public:
    using value_type = typename storage_t::value_type;
    using size_type = typename storage_t::size_type;
    using reference = typename storage_t::reference;
    using const_reference = typename storage_t::const_reference;

    Queue();
    explicit Queue(size_type limit);
    Queue(const Queue&) = delete;
    Queue& operator=(const Queue&) = delete;
    Queue(Queue&&) = default;
    Queue& operator=(Queue&&) = default;
    ~Queue();
    [[nodiscard]] std::optional<size_type> limit() const;
    [[nodiscard]] bool try_push(const_reference);
    [[nodiscard]] bool try_push(value_type&&);
    [[nodiscard]] bool push(const_reference);
    [[nodiscard]] bool push(value_type&&);
    std::optional<value_type> try_pop();
    std::optional<value_type> pop();
    void join();
    [[nodiscard]] bool joinable() const;

private:
    Storage q_;
    std::optional<size_type> limit_;
    mutable std::mutex mutex_;
    std::condition_variable cv_;
    std::atomic_bool joinable_ = false;
};

template <typename S>
Queue<S>::Queue() {}

template <typename S>
Queue<S>::Queue(size_type limit) : limit_{limit} {}

template <typename S>
Queue<S>::~Queue() {
    join();
}

template <typename S>
std::optional<typename Queue<S>::size_type> Queue<S>::limit() const {
    return limit_;
}

template <typename S>
bool Queue<S>::try_push(const_reference elem) {
    std::lock_guard<std::mutex> lock(mutex_);
    if (limit_ == q_.size()) {
        q_.pop_front();
    }
    q_.push_back(elem);
    cv_.notify_one();
    return true;
}

template <typename S>
bool Queue<S>::try_push(value_type&& elem) {
    std::lock_guard<std::mutex> lock(mutex_);
    if (limit_ == q_.size()) {
        q_.pop_front();
    }
    q_.push_back(std::move(elem));
    cv_.notify_one();
    return true;
}

template <typename S>
bool Queue<S>::push(const_reference elem) {
    std::unique_lock<std::mutex> lock(mutex_);
    cv_.wait(lock, [&] { return limit_ != q_.size() || joinable_; });
    if (joinable_) {
        return false;
    }
    q_.push_back(elem);
    cv_.notify_one();
    return true;
}

template <typename S>
bool Queue<S>::push(value_type&& elem) {
    std::unique_lock<std::mutex> lock(mutex_);
    cv_.wait(lock, [&] { return limit_ != q_.size() || joinable_; });
    if (joinable_) {
        return false;
    }
    q_.push_back(std::move(elem));
    cv_.notify_one();
    return true;
}

template <typename S>
std::optional<typename Queue<S>::value_type> Queue<S>::try_pop() {
    std::lock_guard<std::mutex> lock(mutex_);
    if (q_.empty()) {
        return std::nullopt;
    }
    value_type elem = q_.front();
    q_.pop_front();
    return elem;
};

template <typename S>
std::optional<typename Queue<S>::value_type> Queue<S>::pop() {
    std::unique_lock<std::mutex> lock(mutex_);
    cv_.wait(lock, [&] { return !q_.empty() || joinable_; });
    if (joinable_) {
        return std::nullopt;
    }
    value_type elem = q_.front();
    q_.pop_front();
    return elem;
};

template <typename S>
void Queue<S>::join() {
    joinable_ = true;
    cv_.notify_all();
}

template <typename S>
bool Queue<S>::joinable() const {
    return joinable_;
}

#endif
