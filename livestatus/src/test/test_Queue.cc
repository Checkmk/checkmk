// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <cstddef>
#include <optional>
#include <string>
#include <utility>

#include "Queue.h"
#include "gtest/gtest.h"

class UnboundedQueueTest
    : public ::testing::TestWithParam<queue_overflow_strategy> {
public:
    Queue<int> queue{};
};

TEST_P(UnboundedQueueTest, LimitIsNotSet) {
    EXPECT_EQ(std::nullopt, queue.limit());
}

TEST_P(UnboundedQueueTest, PushAndPopDontOverflow) {
    auto strategy = GetParam();
    EXPECT_EQ(0UL, queue.approx_size());

    EXPECT_EQ(queue_status::ok, queue.push(1, strategy));
    EXPECT_EQ(queue_status::ok, queue.push(2, strategy));
    EXPECT_EQ(queue_status::ok, queue.push(42, strategy));
    EXPECT_EQ(3UL, queue.approx_size());

    EXPECT_EQ(1, queue.try_pop());
    EXPECT_EQ(2, queue.try_pop());
    EXPECT_EQ(42, queue.try_pop());
    EXPECT_EQ(0UL, queue.approx_size());
}

TEST_P(UnboundedQueueTest, PopFromEmptyReturnsNullOpt) {
    EXPECT_EQ(0UL, queue.approx_size());
    EXPECT_EQ(std::nullopt, queue.try_pop());
    EXPECT_EQ(std::nullopt, queue.try_pop());
    EXPECT_EQ(std::nullopt, queue.try_pop());
    EXPECT_EQ(std::nullopt, queue.try_pop());
    EXPECT_EQ(0UL, queue.approx_size());
}

INSTANTIATE_TEST_SUITE_P(UnboundedQueueTests, UnboundedQueueTest,
                         testing::Values(queue_overflow_strategy::wait,
                                         queue_overflow_strategy::pop_oldest,
                                         queue_overflow_strategy::dont_push));

class BoundedQueueTest : public ::testing::Test {
public:
    Queue<int> queue{queue_join_strategy::shutdown_push_pop, 5};
};

TEST_F(BoundedQueueTest, LimitIsSet) {
    EXPECT_EQ(std::size_t{5}, queue.limit());
}

TEST_F(BoundedQueueTest, PopOldestWhenFull) {
    auto strategy = queue_overflow_strategy::pop_oldest;
    EXPECT_EQ(0UL, queue.approx_size());

    EXPECT_EQ(queue_status::ok, queue.push(1, strategy));
    EXPECT_EQ(queue_status::ok, queue.push(2, strategy));
    EXPECT_EQ(queue_status::ok, queue.push(3, strategy));
    EXPECT_EQ(queue_status::ok, queue.push(4, strategy));
    EXPECT_EQ(queue_status::ok, queue.push(5, strategy));
    EXPECT_EQ(5UL, queue.approx_size());

    // Now the queue should be full.

    EXPECT_EQ(queue_status::overflow, queue.push(6, strategy));
    EXPECT_EQ(queue_status::overflow, queue.push(7, strategy));
    EXPECT_EQ(queue_status::overflow, queue.push(8, strategy));
    EXPECT_EQ(queue_status::overflow, queue.push(9, strategy));
    EXPECT_EQ(queue_status::overflow, queue.push(0, strategy));
    EXPECT_EQ(5UL, queue.approx_size());

    // The first five elements should be gone.

    EXPECT_EQ(6, queue.try_pop());
    EXPECT_EQ(7, queue.try_pop());
    EXPECT_EQ(8, queue.try_pop());
    EXPECT_EQ(9, queue.try_pop());
    EXPECT_EQ(0, queue.try_pop());
    EXPECT_EQ(0UL, queue.approx_size());
}

TEST_F(BoundedQueueTest, DontPushWhenFull) {
    auto strategy = queue_overflow_strategy::dont_push;
    EXPECT_EQ(0UL, queue.approx_size());

    EXPECT_EQ(queue_status::ok, queue.push(1, strategy));
    EXPECT_EQ(queue_status::ok, queue.push(2, strategy));
    EXPECT_EQ(queue_status::ok, queue.push(3, strategy));
    EXPECT_EQ(queue_status::ok, queue.push(4, strategy));
    EXPECT_EQ(queue_status::ok, queue.push(5, strategy));
    EXPECT_EQ(5UL, queue.approx_size());

    // Now the queue should be full.

    EXPECT_EQ(queue_status::overflow, queue.push(6, strategy));
    EXPECT_EQ(queue_status::overflow, queue.push(7, strategy));
    EXPECT_EQ(queue_status::overflow, queue.push(8, strategy));
    EXPECT_EQ(queue_status::overflow, queue.push(9, strategy));
    EXPECT_EQ(queue_status::overflow, queue.push(0, strategy));
    EXPECT_EQ(5UL, queue.approx_size());

    // The last five elements should not be there.

    EXPECT_EQ(1, queue.try_pop());
    EXPECT_EQ(2, queue.try_pop());
    EXPECT_EQ(3, queue.try_pop());
    EXPECT_EQ(4, queue.try_pop());
    EXPECT_EQ(5, queue.try_pop());
    EXPECT_EQ(0UL, queue.approx_size());
}

class MoveOnlyQueueTest : public ::testing::Test {
public:
    class MoveOnly {
    public:
        explicit MoveOnly(std::string id) : id_{std::move(id)} {};
        MoveOnly(const MoveOnly &) = delete;
        MoveOnly &operator=(const MoveOnly &) = delete;
        MoveOnly(MoveOnly &&) noexcept = default;
        MoveOnly &operator=(MoveOnly &&) noexcept = default;
        [[nodiscard]] std::string id() const { return id_; }

    private:
        std::string id_;
    };

    Queue<MoveOnly> queue{};
};

TEST_F(MoveOnlyQueueTest, MoveOnlyTest) {
    auto strategy = queue_overflow_strategy::dont_push;

    EXPECT_EQ(queue_status::ok, queue.push(MoveOnly{"1st"}, strategy));
    EXPECT_EQ(queue_status::ok, queue.push(MoveOnly{"2nd"}, strategy));

    auto o1 = queue.try_pop();
    EXPECT_EQ("1st", o1->id());

    auto o2 = queue.pop();
    EXPECT_EQ("2nd", o2->id());
}
