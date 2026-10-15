// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <chrono>
#include <memory>
#include <optional>
#include <string>

#include "gtest/gtest.h"
#include "livestatus/Column.h"
#include "livestatus/Filter.h"
#include "livestatus/IntColumn.h"
#include "livestatus/opids.h"

using namespace std::chrono_literals;
using namespace std::string_literals;

namespace {
struct DummyRow {};

class IntFilterTest : public ::testing::Test {
protected:
    const IntColumn<DummyRow> column_{
        "x"s, ""s, ColumnOffsets{}, [](const DummyRow & /*row*/) { return 0; }};

    [[nodiscard]] std::unique_ptr<Filter> filter(
        RelationalOperator op, const std::string &value) const {
        return column_.createFilter(Filter::Kind::row, op, value);
    }
};
}  // namespace

TEST_F(IntFilterTest, GreaterThanTheMaximumHasNoGreatestLowerBound) {
    EXPECT_EQ(filter(RelationalOperator::greater, "2147483647")
                  ->greatestLowerBoundFor("x", 0s),
              std::nullopt);
}

TEST_F(IntFilterTest, LessThanTheMinimumHasNoLeastUpperBound) {
    EXPECT_EQ(filter(RelationalOperator::less, "-2147483648")
                  ->leastUpperBoundFor("x", 0s),
              std::nullopt);
}
