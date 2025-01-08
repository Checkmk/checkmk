// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <cmath>
#include <limits>
#include <memory>
#include <numeric>
#include <string>
#include <vector>

#include "gtest/gtest.h"
#include "livestatus/RRDConsolidate.h"

namespace {
constexpr auto NaN = std::numeric_limits<double>::quiet_NaN();
}  // namespace

TEST(TestRRDConsolidate, Constant) {
    const auto value = 2.0;
    const auto input = std::vector<double>(200, value);
    EXPECT_EQ(input, rrd_consolidate(std::make_unique<MinCF>(), input, 10, 10));
    EXPECT_EQ(input, rrd_consolidate(std::make_unique<MaxCF>(), input, 10, 10));
    EXPECT_EQ(input, rrd_consolidate(std::make_unique<AvgCF>(), input, 10, 10));
    EXPECT_EQ(input,
              rrd_consolidate(std::make_unique<LastCF>(), input, 10, 10));

    {
        const auto min_ =
            rrd_consolidate(std::make_unique<MinCF>(), input, 10, 20);
        ASSERT_EQ(input.size() / 2, min_.size());
        EXPECT_EQ(std::vector<double>(min_.size(), value), min_);
    }
    {
        const auto max_ =
            rrd_consolidate(std::make_unique<MaxCF>(), input, 10, 20);
        ASSERT_EQ(input.size() / 2, max_.size());
        EXPECT_EQ(std::vector<double>(max_.size(), value), max_);
    }
    {
        const auto avg_ =
            rrd_consolidate(std::make_unique<MinCF>(), input, 10, 20);
        ASSERT_EQ(input.size() / 2, avg_.size());
        EXPECT_EQ(std::vector<double>(avg_.size(), value), avg_);
    }
    {
        const auto last_ =
            rrd_consolidate(std::make_unique<LastCF>(), input, 10, 20);
        ASSERT_EQ(input.size() / 2, last_.size());
        EXPECT_EQ(std::vector<double>(last_.size(), value), last_);
    }
}

TEST(TestRRDConsolidate, NaN) {
    const auto value = NaN;
    const auto input = std::vector<double>(20, value);

    {
        const auto min_ =
            rrd_consolidate(std::make_unique<MinCF>(), input, 10, 20);
        ASSERT_EQ(input.size() / 2, min_.size());
        EXPECT_TRUE(std::accumulate(
            input.begin(), input.end(), true,
            [](auto &&lhs, auto &&rhs) { return lhs && std::isnan(rhs); }));
    }
    {
        const auto max_ =
            rrd_consolidate(std::make_unique<MaxCF>(), input, 10, 20);
        ASSERT_EQ(input.size() / 2, max_.size());
        EXPECT_TRUE(std::accumulate(
            input.begin(), input.end(), true,
            [](auto &&lhs, auto &&rhs) { return lhs && std::isnan(rhs); }));
    }
    {
        const auto avg_ =
            rrd_consolidate(std::make_unique<MinCF>(), input, 10, 20);
        ASSERT_EQ(input.size() / 2, avg_.size());
        EXPECT_TRUE(std::accumulate(
            input.begin(), input.end(), true,
            [](auto &&lhs, auto &&rhs) { return lhs && std::isnan(rhs); }));
    }
    {
        const auto last_ =
            rrd_consolidate(std::make_unique<MinCF>(), input, 10, 20);
        ASSERT_EQ(input.size() / 2, last_.size());
        EXPECT_TRUE(std::accumulate(
            input.begin(), input.end(), true,
            [](auto &&lhs, auto &&rhs) { return lhs && std::isnan(rhs); }));
    }
}

TEST(TestRRDConsolidate, SimpleCases) {
    const auto input = std::vector<double>{1, 2, 1, 2, 1, 2, 1, 2};
    EXPECT_EQ(std::vector<double>(4, 1.0),
              rrd_consolidate(std::make_unique<MinCF>(), input, 10, 20));
    EXPECT_EQ(std::vector<double>(4, 2.0),
              rrd_consolidate(std::make_unique<MaxCF>(), input, 10, 20));
    EXPECT_EQ(std::vector<double>(4, 1.5),
              rrd_consolidate(std::make_unique<AvgCF>(), input, 10, 20));
    EXPECT_EQ(std::vector<double>(4, 2.0),
              rrd_consolidate(std::make_unique<LastCF>(), input, 10, 20));
}

TEST(TestRRDConsolidate, ComplexCases) {
    const auto input = std::vector<double>{1, NaN, 1, 2};
    {
        const auto min_ = std::vector<double>{1, 1};
        EXPECT_EQ(min_,
                  rrd_consolidate(std::make_unique<MinCF>(), input, 10, 20));
    }
    {
        const auto max_ = std::vector<double>{1, 2};
        EXPECT_EQ(max_,
                  rrd_consolidate(std::make_unique<MaxCF>(), input, 10, 20));
    }
    {
        const auto avg_ = std::vector<double>{1, 1.5};
        EXPECT_EQ(avg_,
                  rrd_consolidate(std::make_unique<AvgCF>(), input, 10, 20));
    }
    {
        const auto last_ =
            rrd_consolidate(std::make_unique<LastCF>(), input, 10, 20);
        EXPECT_EQ(2, last_.size());
        EXPECT_TRUE(std::isnan(last_[0]));
        EXPECT_DOUBLE_EQ(2.0, last_[1]);
    }
}
