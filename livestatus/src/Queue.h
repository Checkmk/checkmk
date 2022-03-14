// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef Queue_h
#define Queue_h

#include "config.h"  // IWYU pragma: keep

#include <condition_variable>
#include <deque>
#include <mutex>
#include <optional>
#include <utility>

enum class queue_status { ok, overflow, joinable };
enum class queue_overflow_strategy { wait, pop_oldest, dont_push };
// queue_join_strategy::shutdown_pop does not seem useful.
enum class queue_join_strategy { shutdown_push_pop, shutdown_push };

template <typename T, typename Q = std::deque<T>>
class Queue {
public:
    using value_type = T;
    using size_type = typename Q::size_type;
    using reference = T &;
    using const_reference = const T &;

    Queue() = default;
    Queue(queue_join_strategy join_strategy, size_type limit);
    Queue(const Queue &) = delete;
    Queue &operator=(const Queue &) = delete;
    Queue(Queue &&) noexcept = default;
    Queue &operator=(Queue &&) noexcept = default;
    ~Queue();
    [[nodiscard]] size_type approx_size() const;
    [[nodiscard]] std::optional<size_type> limit() const;
    [[nodiscard]] queue_status push(const_reference elem,
                                    queue_overflow_strategy strategy);
    [[nodiscard]] queue_status push(value_type &&elem,
                                    queue_overflow_strategy strategy);
    std::optional<value_type> try_pop();
    std::optional<value_type> pop();
    void join();
    [[nodiscard]] bool joinable() const;

private:
    Q q_;
    queue_join_strategy join_strategy_ = queue_join_strategy::shutdown_push_pop;
    std::optional<size_type> limit_;
    mutable std::mutex mutex_;
    std::condition_variable not_full_;
    std::condition_variable not_empty_;
    bool joinable_{false};
    bool done() const;
};

template <typename T, typename Q>
Queue<T, Q>::Queue(queue_join_strategy join_strategy, size_type limit)
    : join_strategy_{join_strategy}, limit_{limit} {}

template <typename T, typename Q>
Queue<T, Q>::~Queue() {
    join();
}

template <typename T, typename Q>
typename Queue<T, Q>::size_type Queue<T, Q>::approx_size() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return q_.size();
}

template <typename T, typename Q>
std::optional<typename Queue<T, Q>::size_type> Queue<T, Q>::limit() const {
    return limit_;
}

template <typename T, typename Q>
queue_status Queue<T, Q>::push(const_reference elem,
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

template <typename T, typename Q>
queue_status Queue<T, Q>::push(value_type &&elem,
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

template <typename T, typename Q>
std::optional<typename Queue<T, Q>::value_type> Queue<T, Q>::try_pop() {
    std::lock_guard<std::mutex> lock(mutex_);
    if (q_.empty() || done()) {
        return std::nullopt;
    }
    auto elem = std::move(q_.front());
    q_.pop_front();
    not_full_.notify_one();
    return elem;
};

template <typename T, typename Q>
std::optional<typename Queue<T, Q>::value_type> Queue<T, Q>::pop() {
    std::unique_lock<std::mutex> lock(mutex_);
    not_empty_.wait(lock, [&] { return !q_.empty() || joinable_; });
    if (q_.empty() || done()) {
        return std::nullopt;
    }
    auto elem = std::move(q_.front());
    q_.pop_front();
    not_full_.notify_one();
    return elem;
};

template <typename T, typename Q>
void Queue<T, Q>::join() {
    {
        std::lock_guard<std::mutex> lock(mutex_);
        joinable_ = true;
    }
    not_full_.notify_all();
    not_empty_.notify_all();
}

template <typename T, typename Q>
bool Queue<T, Q>::joinable() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return joinable_;
}

template <typename T, typename Q>
bool Queue<T, Q>::done() const {
    switch (join_strategy_) {
        case queue_join_strategy::shutdown_push_pop:
            return joinable_;
        case queue_join_strategy::shutdown_push:
            return false;
    }
    // unreachable
    return false;
}

#endif
