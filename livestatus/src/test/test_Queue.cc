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

    EXPECT_TRUE(queue.try_push(1));
    EXPECT_TRUE(queue.try_push(2));
    EXPECT_TRUE(queue.try_push(42));
    EXPECT_EQ(3UL, queue.approx_size());

    EXPECT_EQ(1, queue.try_pop());
    EXPECT_EQ(2, queue.try_pop());
    EXPECT_EQ(42, queue.try_pop());
    EXPECT_EQ(0UL, queue.approx_size());
}

TEST_F(UnboundedQueueFixture, PushWaitAndPopWait) {
    EXPECT_EQ(0UL, queue.approx_size());

    // This is non blocking as long as we stay within [0-limit] elements.
    EXPECT_TRUE(queue.push(1));
    EXPECT_TRUE(queue.push(2));
    EXPECT_TRUE(queue.push(42));
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

    EXPECT_TRUE(queue.try_push(1));
    EXPECT_TRUE(queue.try_push(2));
    EXPECT_TRUE(queue.try_push(3));
    EXPECT_TRUE(queue.try_push(4));
    EXPECT_TRUE(queue.try_push(5));
    EXPECT_EQ(5UL, queue.approx_size());

    // Now the queue should be full.

    EXPECT_TRUE(queue.try_push(6));
    EXPECT_TRUE(queue.try_push(7));
    EXPECT_TRUE(queue.try_push(8));
    EXPECT_TRUE(queue.try_push(9));
    EXPECT_TRUE(queue.try_push(0));
    EXPECT_EQ(5UL, queue.approx_size());

    // The first five elements should be gone.

    EXPECT_EQ(6, queue.try_pop());
    EXPECT_EQ(7, queue.try_pop());
    EXPECT_EQ(8, queue.try_pop());
    EXPECT_EQ(9, queue.try_pop());
    EXPECT_EQ(0, queue.try_pop());
    EXPECT_EQ(0UL, queue.approx_size());
}
