// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <bitset>
#include <chrono>
#include <memory>
#include <optional>
#include <string>

#include "gtest/gtest.h"
#include "livestatus/Column.h"
#include "livestatus/Filter.h"
#include "livestatus/Row.h"
#include "livestatus/TimeColumn.h"
#include "livestatus/opids.h"

using namespace std::chrono_literals;
using namespace std::string_literals;

namespace {
struct DummyRow : Row {
    using Row::Row;
};

class TimeFilterTest : public ::testing::Test {
protected:
    const TimeColumn<DummyRow> column_{
        "x"s, ""s, ColumnOffsets{}, [](const DummyRow & /*row*/) {
            return std::chrono::system_clock::time_point{};
        }};

    [[nodiscard]] std::unique_ptr<Filter> filter(
        RelationalOperator op, const std::string &value) const {
        return column_.createFilter(Filter::Kind::row, op, value);
    }
};
}  // namespace

TEST_F(TimeFilterTest, GreaterThanTheMaximumHasNoGreatestLowerBound) {
    EXPECT_EQ(filter(RelationalOperator::greater, "2147483647")
                  ->greatestLowerBoundFor("x", 0s),
              std::nullopt);
}

TEST_F(TimeFilterTest, LessThanTheMinimumHasNoLeastUpperBound) {
    EXPECT_EQ(filter(RelationalOperator::less, "-2147483648")
                  ->leastUpperBoundFor("x", 0s),
              std::nullopt);
}

// A timezone offset can move the reference value beyond the range of int32_t.

TEST_F(TimeFilterTest, LessOrEqualBeyondTheMaximumHasNoLeastUpperBound) {
    EXPECT_EQ(filter(RelationalOperator::less_or_equal, "2147483647")
                  ->leastUpperBoundFor("x", -5h),
              std::nullopt);
}

TEST_F(TimeFilterTest, GreaterOrEqualBeyondTheMinimumHasNoGreatestLowerBound) {
    EXPECT_EQ(filter(RelationalOperator::greater_or_equal, "-2147483648")
                  ->greatestLowerBoundFor("x", 5h),
              std::nullopt);
}

TEST_F(TimeFilterTest, LessOrEqualBeyondTheMaximumAllowsAllValues) {
    EXPECT_EQ(filter(RelationalOperator::less_or_equal, "2147483647")
                  ->valueSetLeastUpperBoundFor("x", -5h),
              std::optional<std::bitset<32>>{~std::bitset<32>{}});
}
