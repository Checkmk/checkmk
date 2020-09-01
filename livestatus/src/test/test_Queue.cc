// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <cstddef>
#include <deque>
#include <memory>
#include <optional>

#include "Queue.h"
#include "gtest/gtest.h"

class UnboundedQueueFixture : public ::testing::Test {
public:
    Queue<std::deque<int>> queue{};
};

TEST_F(UnboundedQueueFixture, LimitIsNotSet) {
    EXPECT_EQ(std::nullopt, queue.limit());
}

TEST_F(UnboundedQueueFixture, PushAndPop) {
    EXPECT_EQ(0UL, queue.approx_size());

    EXPECT_EQ(queue_status::ok,
              queue.push(1, queue_overflow_strategy::pop_oldest));
    EXPECT_EQ(queue_status::ok,
              queue.push(2, queue_overflow_strategy::pop_oldest));
    EXPECT_EQ(queue_status::ok,
              queue.push(42, queue_overflow_strategy::pop_oldest));
    EXPECT_EQ(3UL, queue.approx_size());

    EXPECT_EQ(1, queue.try_pop());
    EXPECT_EQ(2, queue.try_pop());
    EXPECT_EQ(42, queue.try_pop());
    EXPECT_EQ(0UL, queue.approx_size());
}

TEST_F(UnboundedQueueFixture, PushWaitAndPopWait) {
    EXPECT_EQ(0UL, queue.approx_size());

    // This is non blocking as long as we stay within [0-limit] elements.
    EXPECT_EQ(queue_status::ok, queue.push(1, queue_overflow_strategy::wait));
    EXPECT_EQ(queue_status::ok, queue.push(2, queue_overflow_strategy::wait));
    EXPECT_EQ(queue_status::ok, queue.push(42, queue_overflow_strategy::wait));
    EXPECT_EQ(3UL, queue.approx_size());

    EXPECT_EQ(1, queue.pop());
    EXPECT_EQ(2, queue.pop());
    EXPECT_EQ(42, queue.pop());
    EXPECT_EQ(0UL, queue.approx_size());
}

TEST_F(UnboundedQueueFixture, PopFromEmptyReturnsNullOpt) {
    EXPECT_EQ(0UL, queue.approx_size());
    EXPECT_EQ(std::nullopt, queue.try_pop());
    EXPECT_EQ(std::nullopt, queue.try_pop());
    EXPECT_EQ(std::nullopt, queue.try_pop());
    EXPECT_EQ(std::nullopt, queue.try_pop());
    EXPECT_EQ(0UL, queue.approx_size());
}

class BoundedQueueFixture : public ::testing::Test {
public:
    Queue<std::deque<int>> queue{5};
};

TEST_F(BoundedQueueFixture, LimitIsSet) {
    EXPECT_EQ(std::size_t{5}, queue.limit());
}

TEST_F(BoundedQueueFixture, FullDiscardsOldest) {
    EXPECT_EQ(0UL, queue.approx_size());

    EXPECT_EQ(queue_status::ok,
              queue.push(1, queue_overflow_strategy::pop_oldest));
    EXPECT_EQ(queue_status::ok,
              queue.push(2, queue_overflow_strategy::pop_oldest));
    EXPECT_EQ(queue_status::ok,
              queue.push(3, queue_overflow_strategy::pop_oldest));
    EXPECT_EQ(queue_status::ok,
              queue.push(4, queue_overflow_strategy::pop_oldest));
    EXPECT_EQ(queue_status::ok,
              queue.push(5, queue_overflow_strategy::pop_oldest));
    EXPECT_EQ(5UL, queue.approx_size());

    // Now the queue should be full.

    EXPECT_EQ(queue_status::overflow,
              queue.push(6, queue_overflow_strategy::pop_oldest));
    EXPECT_EQ(queue_status::overflow,
              queue.push(7, queue_overflow_strategy::pop_oldest));
    EXPECT_EQ(queue_status::overflow,
              queue.push(8, queue_overflow_strategy::pop_oldest));
    EXPECT_EQ(queue_status::overflow,
              queue.push(9, queue_overflow_strategy::pop_oldest));
    EXPECT_EQ(queue_status::overflow,
              queue.push(0, queue_overflow_strategy::pop_oldest));
    EXPECT_EQ(5UL, queue.approx_size());

    // The first five elements should be gone.

    EXPECT_EQ(6, queue.try_pop());
    EXPECT_EQ(7, queue.try_pop());
    EXPECT_EQ(8, queue.try_pop());
    EXPECT_EQ(9, queue.try_pop());
    EXPECT_EQ(0, queue.try_pop());
    EXPECT_EQ(0UL, queue.approx_size());
}
