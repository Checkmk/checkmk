// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <chrono>
#include <cstddef>
#include <optional>
#include <string>
#include <utility>

#include "gtest/gtest.h"
#include "livestatus/Queue.h"

using namespace std::chrono_literals;

class UnboundedQueueTest
    : public ::testing::TestWithParam<queue_overflow_strategy> {
public:
    Queue<int> queue;
};

TEST_P(UnboundedQueueTest, LimitIsNotSet) {
    EXPECT_EQ(std::nullopt, queue.limit());
}

// Note: Throwing an exception in std::optional::value() is totally fine here,
// the corresponding test will fail in that case.
// NOLINTBEGIN(bugprone-unchecked-optional-access)
TEST_P(UnboundedQueueTest, PushAndPopDontOverflow) {
    auto strategy = GetParam();

    EXPECT_EQ(0UL, queue.approx_size());

    EXPECT_EQ(std::make_pair(queue_status::ok, 1UL), queue.push(1, strategy));
    EXPECT_EQ(std::make_pair(queue_status::ok, 2UL), queue.push(2, strategy));
    EXPECT_EQ(std::make_pair(queue_status::ok, 3UL), queue.push(42, strategy));
    EXPECT_EQ(3UL, queue.approx_size());

    EXPECT_EQ(std::make_pair(1, 2UL),
              queue.pop(queue_pop_strategy::nonblocking, {}).value());
    EXPECT_EQ(std::make_pair(2, 1UL),
              queue.pop(queue_pop_strategy::nonblocking, {}).value());
    EXPECT_EQ(std::make_pair(42, 0UL),
              queue.pop(queue_pop_strategy::nonblocking, {}).value());
    EXPECT_EQ(0UL, queue.approx_size());
}

TEST_P(UnboundedQueueTest, PopFromEmptyReturnsNullOpt) {
    EXPECT_EQ(0UL, queue.approx_size());

    EXPECT_EQ(std::nullopt, queue.pop(queue_pop_strategy::nonblocking, {}));
    EXPECT_EQ(std::nullopt, queue.pop(queue_pop_strategy::nonblocking, {}));
    EXPECT_EQ(std::nullopt, queue.pop(queue_pop_strategy::nonblocking, {}));
    EXPECT_EQ(std::nullopt, queue.pop(queue_pop_strategy::nonblocking, {}));
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

    EXPECT_EQ(std::make_pair(queue_status::ok, 1UL), queue.push(1, strategy));
    EXPECT_EQ(std::make_pair(queue_status::ok, 2UL), queue.push(2, strategy));
    EXPECT_EQ(std::make_pair(queue_status::ok, 3UL), queue.push(3, strategy));
    EXPECT_EQ(std::make_pair(queue_status::ok, 4UL), queue.push(4, strategy));
    EXPECT_EQ(std::make_pair(queue_status::ok, 5UL), queue.push(5, strategy));
    EXPECT_EQ(5UL, queue.approx_size());

    // Now the queue should be full.

    EXPECT_EQ(std::make_pair(queue_status::overflow, 5UL),
              queue.push(6, strategy));
    EXPECT_EQ(std::make_pair(queue_status::overflow, 5UL),
              queue.push(7, strategy));
    EXPECT_EQ(std::make_pair(queue_status::overflow, 5UL),
              queue.push(8, strategy));
    EXPECT_EQ(std::make_pair(queue_status::overflow, 5UL),
              queue.push(9, strategy));
    EXPECT_EQ(std::make_pair(queue_status::overflow, 5UL),
              queue.push(0, strategy));
    EXPECT_EQ(5UL, queue.approx_size());

    // The first five elements should be gone.

    EXPECT_EQ(std::make_pair(6, 4UL),
              queue.pop(queue_pop_strategy::nonblocking, {}).value());
    EXPECT_EQ(std::make_pair(7, 3UL),
              queue.pop(queue_pop_strategy::nonblocking, {}).value());
    EXPECT_EQ(std::make_pair(8, 2UL),
              queue.pop(queue_pop_strategy::nonblocking, {}).value());
    EXPECT_EQ(std::make_pair(9, 1UL),
              queue.pop(queue_pop_strategy::nonblocking, {}).value());
    EXPECT_EQ(std::make_pair(0, 0UL),
              queue.pop(queue_pop_strategy::nonblocking, {}).value());
    EXPECT_EQ(0UL, queue.approx_size());
}

TEST_F(BoundedQueueTest, DontPushWhenFull) {
    auto strategy = queue_overflow_strategy::dont_push;
    EXPECT_EQ(0UL, queue.approx_size());

    EXPECT_EQ(std::make_pair(queue_status::ok, 1UL), queue.push(1, strategy));
    EXPECT_EQ(std::make_pair(queue_status::ok, 2UL), queue.push(2, strategy));
    EXPECT_EQ(std::make_pair(queue_status::ok, 3UL), queue.push(3, strategy));
    EXPECT_EQ(std::make_pair(queue_status::ok, 4UL), queue.push(4, strategy));
    EXPECT_EQ(std::make_pair(queue_status::ok, 5UL), queue.push(5, strategy));
    EXPECT_EQ(5UL, queue.approx_size());

    // Now the queue should be full.

    EXPECT_EQ(std::make_pair(queue_status::overflow, 5UL),
              queue.push(6, strategy));
    EXPECT_EQ(std::make_pair(queue_status::overflow, 5UL),
              queue.push(7, strategy));
    EXPECT_EQ(std::make_pair(queue_status::overflow, 5UL),
              queue.push(8, strategy));
    EXPECT_EQ(std::make_pair(queue_status::overflow, 5UL),
              queue.push(9, strategy));
    EXPECT_EQ(std::make_pair(queue_status::overflow, 5UL),
              queue.push(0, strategy));
    EXPECT_EQ(5UL, queue.approx_size());

    // The last five elements should not be there.

    EXPECT_EQ(std::make_pair(1, 4UL),
              queue.pop(queue_pop_strategy::nonblocking, {}).value());
    EXPECT_EQ(std::make_pair(2, 3UL),
              queue.pop(queue_pop_strategy::nonblocking, {}).value());
    EXPECT_EQ(std::make_pair(3, 2UL),
              queue.pop(queue_pop_strategy::nonblocking, {}).value());
    EXPECT_EQ(std::make_pair(4, 1UL),
              queue.pop(queue_pop_strategy::nonblocking, {}).value());
    EXPECT_EQ(std::make_pair(5, 0UL),
              queue.pop(queue_pop_strategy::nonblocking, {}).value());
    EXPECT_EQ(0UL, queue.approx_size());
}
// NOLINTEND(bugprone-unchecked-optional-access)

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

    Queue<MoveOnly> queue;
};

TEST_F(MoveOnlyQueueTest, MoveOnlyTest) {
    auto strategy = queue_overflow_strategy::dont_push;

    EXPECT_EQ(std::make_pair(queue_status::ok, 1UL),
              queue.push(MoveOnly{"1st"}, strategy));
    EXPECT_EQ(std::make_pair(queue_status::ok, 2UL),
              queue.push(MoveOnly{"2nd"}, strategy));
    EXPECT_EQ(std::make_pair(queue_status::ok, 3UL),
              queue.push(MoveOnly{"3rd"}, strategy));

    auto o1 = queue.pop(queue_pop_strategy::nonblocking, {});
    EXPECT_TRUE(o1 && "1st" == o1->first.id());

    auto o2 = queue.pop(queue_pop_strategy::blocking, {});
    EXPECT_TRUE(o2 && "2nd" == o2->first.id());

    auto o3 = queue.pop(queue_pop_strategy::blocking, 0ms);
    EXPECT_TRUE(o3 && "3rd" == o3->first.id());
}
