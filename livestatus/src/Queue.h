// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef Queue_h
#define Queue_h

#include "config.h"  // IWYU pragma: keep

#include <condition_variable>
#include <mutex>
#include <optional>
#include <utility>

enum class queue_status { ok, overflow, joinable };
enum class queue_overflow_strategy { wait, pop_oldest, dont_push };

template <typename Storage>
class Queue {
    using storage_t = Storage;

public:
    using value_type = typename storage_t::value_type;
    using size_type = typename storage_t::size_type;
    using reference = typename storage_t::reference;
    using const_reference = typename storage_t::const_reference;

    Queue() = default;
    explicit Queue(size_type limit);
    Queue(const Queue&) = delete;
    Queue& operator=(const Queue&) = delete;
    Queue(Queue&&) noexcept = default;
    Queue& operator=(Queue&&) noexcept = default;
    ~Queue();
    [[nodiscard]] size_type approx_size() const;
    [[nodiscard]] std::optional<size_type> limit() const;
    [[nodiscard]] queue_status push(const_reference elem,
                                    queue_overflow_strategy strategy);
    [[nodiscard]] queue_status push(value_type&& elem,
                                    queue_overflow_strategy strategy);
    std::optional<value_type> try_pop();
    std::optional<value_type> pop();
    void join();
    [[nodiscard]] bool joinable() const;

private:
    Storage q_;
    std::optional<size_type> limit_;
    mutable std::mutex mutex_;
    std::condition_variable not_full_;
    std::condition_variable not_empty_;
    bool joinable_{false};
};

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
queue_status Queue<S>::push(const_reference elem,
                            queue_overflow_strategy strategy) {
    auto status{queue_status::ok};
    std::unique_lock<std::mutex> lock(mutex_);
    switch (strategy) {
        case queue_overflow_strategy::wait:
            not_full_.wait(lock,
                           [&] { return limit_ != q_.size() || joinable_; });
            if (joinable_) {
                return queue_status::joinable;
            }
            break;
        case queue_overflow_strategy::pop_oldest:
            if (joinable_) {
                return queue_status::joinable;
            }
            if (limit_ == q_.size()) {
                q_.pop_front();
                status = queue_status::overflow;
            }
            break;
        case queue_overflow_strategy::dont_push:
            if (joinable_) {
                return queue_status::joinable;
            }
            if (limit_ == q_.size()) {
                return queue_status::overflow;
            }
            break;
    }
    q_.push_back(elem);
    not_empty_.notify_one();
    return status;
}

template <typename S>
queue_status Queue<S>::push(value_type&& elem,
                            queue_overflow_strategy strategy) {
    auto status{queue_status::ok};
    std::unique_lock<std::mutex> lock(mutex_);
    switch (strategy) {
        case queue_overflow_strategy::wait:
            not_full_.wait(lock,
                           [&] { return limit_ != q_.size() || joinable_; });
            if (joinable_) {
                return queue_status::joinable;
            }
            break;
        case queue_overflow_strategy::pop_oldest:
            if (joinable_) {
                return queue_status::joinable;
            }
            if (limit_ == q_.size()) {
                q_.pop_front();
                status = queue_status::overflow;
            }
            break;
        case queue_overflow_strategy::dont_push:
            if (joinable_) {
                return queue_status::joinable;
            }
            if (limit_ == q_.size()) {
                return queue_status::overflow;
            }
            break;
    }
    q_.push_back(std::move(elem));
    not_empty_.notify_one();
    return status;
}

template <typename S>
std::optional<typename Queue<S>::value_type> Queue<S>::try_pop() {
    std::lock_guard<std::mutex> lock(mutex_);
    if (q_.empty()) {
        return std::nullopt;
    }
    value_type elem = q_.front();
    q_.pop_front();
    not_full_.notify_one();
    return elem;
};

template <typename S>
std::optional<typename Queue<S>::value_type> Queue<S>::pop() {
    std::unique_lock<std::mutex> lock(mutex_);
    not_empty_.wait(lock, [&] { return !q_.empty() || joinable_; });
    if (joinable_) {
        return std::nullopt;
    }
    value_type elem = q_.front();
    q_.pop_front();
    not_full_.notify_one();
    return elem;
};

template <typename S>
void Queue<S>::join() {
    {
        std::lock_guard<std::mutex> lock(mutex_);
        joinable_ = true;
    }
    not_full_.notify_all();
    not_empty_.notify_all();
}

template <typename S>
bool Queue<S>::joinable() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return joinable_;
}

#endif
