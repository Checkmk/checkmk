// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef Queue_h
#define Queue_h

#include <atomic>
#include <condition_variable>
#include <deque>
#include <mutex>
#include <optional>
#include <utility>

enum class queue_status { ok, overflow, joinable };
enum class queue_overflow_strategy { wait, pop_oldest, dont_push };
// queue_join_strategy::shutdown_pop does not seem useful.
enum class queue_join_strategy { shutdown_push_pop, shutdown_push };
enum class queue_pop_strategy { blocking, nonblocking };

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
    [[nodiscard]] std::pair<queue_status, size_type> push(
        const_reference elem, queue_overflow_strategy strategy);
    [[nodiscard]] std::pair<queue_status, size_type> push(
        value_type &&elem, queue_overflow_strategy strategy);
    std::optional<std::pair<value_type, size_type>> pop(
        queue_pop_strategy pop_strategy,
        std::optional<std::chrono::nanoseconds> timeout);
    void join();
    [[nodiscard]] bool joinable() const;

private:
    Q q_;
    queue_join_strategy join_strategy_ = queue_join_strategy::shutdown_push_pop;
    std::optional<size_type> limit_;
    mutable std::mutex mutex_;
    std::condition_variable not_full_;
    std::condition_variable not_empty_;
    std::atomic<bool> joinable_{false};
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
    const std::scoped_lock sl{mutex_};
    return q_.size();
}

template <typename T, typename Q>
std::optional<typename Queue<T, Q>::size_type> Queue<T, Q>::limit() const {
    return limit_;
}

template <typename T, typename Q>
std::pair<queue_status, typename Queue<T, Q>::size_type> Queue<T, Q>::push(
    const_reference elem, queue_overflow_strategy strategy) {
    auto status{queue_status::ok};
    std::unique_lock<std::mutex> lock(mutex_);
    switch (strategy) {
        case queue_overflow_strategy::wait:
            not_full_.wait(lock,
                           [&] { return limit_ != q_.size() || joinable_; });
            if (joinable_) {
                return std::make_pair(queue_status::joinable, q_.size());
            }
            break;
        case queue_overflow_strategy::pop_oldest:
            if (joinable_) {
                return std::make_pair(queue_status::joinable, q_.size());
            }
            if (limit_ == q_.size()) {
                q_.pop_front();
                status = queue_status::overflow;
            }
            break;
        case queue_overflow_strategy::dont_push:
            if (joinable_) {
                return std::make_pair(queue_status::joinable, q_.size());
            }
            if (limit_ == q_.size()) {
                return std::make_pair(queue_status::overflow, q_.size());
            }
            break;
    }
    q_.push_back(elem);
    not_empty_.notify_one();
    return std::make_pair(status, q_.size());
}

template <typename T, typename Q>
std::pair<queue_status, typename Queue<T, Q>::size_type> Queue<T, Q>::push(
    value_type &&elem, queue_overflow_strategy strategy) {
    auto status{queue_status::ok};
    std::unique_lock<std::mutex> lock(mutex_);
    switch (strategy) {
        case queue_overflow_strategy::wait:
            not_full_.wait(lock,
                           [&] { return limit_ != q_.size() || joinable_; });
            if (joinable_) {
                return std::make_pair(queue_status::joinable, q_.size());
            }
            break;
        case queue_overflow_strategy::pop_oldest:
            if (joinable_) {
                return std::make_pair(queue_status::joinable, q_.size());
            }
            if (limit_ == q_.size()) {
                q_.pop_front();
                status = queue_status::overflow;
            }
            break;
        case queue_overflow_strategy::dont_push:
            if (joinable_) {
                return std::make_pair(queue_status::joinable, q_.size());
            }
            if (limit_ == q_.size()) {
                return std::make_pair(queue_status::overflow, q_.size());
            }
            break;
    }
    q_.push_back(std::move(elem));
    not_empty_.notify_one();
    return std::make_pair(status, q_.size());
}

template <typename T, typename Q>
std::optional<std::pair<typename Queue<T, Q>::value_type,
                        typename Queue<T, Q>::size_type>>
Queue<T, Q>::pop(queue_pop_strategy pop_strategy,
                 std::optional<std::chrono::nanoseconds> timeout) {
    std::unique_lock<std::mutex> lock(mutex_);
    if (pop_strategy == queue_pop_strategy::blocking) {
        if (timeout) {
            not_empty_.wait_for(lock, *timeout,
                                [&] { return !q_.empty() || joinable_; });
        } else {
            not_empty_.wait(lock, [&] { return !q_.empty() || joinable_; });
        }
    }
    if (q_.empty() || done()) {
        return std::nullopt;
    }
    auto elem = std::move(q_.front());
    q_.pop_front();
    not_full_.notify_one();
    return std::make_pair(std::move(elem), q_.size());
};

template <typename T, typename Q>
void Queue<T, Q>::join() {
    joinable_ = true;
    not_full_.notify_all();
    not_empty_.notify_all();
}

template <typename T, typename Q>
bool Queue<T, Q>::joinable() const {
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
