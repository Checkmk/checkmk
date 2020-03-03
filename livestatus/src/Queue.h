// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

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
    [[nodiscard]] size_type approx_size() const;
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
typename Queue<S>::size_type Queue<S>::approx_size() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return q_.size();
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
