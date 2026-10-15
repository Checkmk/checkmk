// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <bitset>
#include <chrono>
#include <cstdint>
#include <functional>
#include <memory>
#include <optional>
#include <stdexcept>
#include <string>
#include <vector>

#include "gtest/gtest.h"
#include "livestatus/Column.h"
#include "livestatus/Filter.h"
#include "livestatus/IntColumn.h"
#include "livestatus/ParsedQuery.h"

using namespace std::chrono_literals;
using namespace std::string_literals;

namespace {
struct DummyRow {};

std::shared_ptr<Column> makeIntColumn(const std::string &name) {
    return std::make_shared<IntColumn<DummyRow>>(
        name, ""s, ColumnOffsets{}, [](const DummyRow & /*row*/) { return 0; });
}

// A filter refers to its column, so the columns must outlive the filters.
const std::vector<std::shared_ptr<Column>> &columns() {
    static const std::vector<std::shared_ptr<Column>> columns{
        makeIntColumn("x"s), makeIntColumn("y"s)};
    return columns;
}

std::shared_ptr<Column> column(const std::string &name) {
    for (const auto &col : columns()) {
        if (col->name() == name) {
            return col;
        }
    }
    throw std::runtime_error("invalid column '" + name + "'");
}

std::unique_ptr<Filter> parseFilter(const std::vector<std::string> &lines) {
    return ParsedQuery{lines, columns, column}.filter;
}
}  // namespace

TEST(AndingFilterTest, GreatestLowerBoundIsTheHighestOfTheBoundedConjuncts) {
    const auto filter = parseFilter(
        {"Filter: x >= 5", "Filter: x >= 10", "Filter: y = 1", "And: 3"});

    EXPECT_EQ(filter->greatestLowerBoundFor("x", 0s),
              std::optional<int32_t>{10});
}

TEST(AndingFilterTest, LeastUpperBoundIsTheLowestOfTheBoundedConjuncts) {
    const auto filter = parseFilter(
        {"Filter: x <= 5", "Filter: x <= 10", "Filter: y = 1", "And: 3"});

    EXPECT_EQ(filter->leastUpperBoundFor("x", 0s), std::optional<int32_t>{5});
}

TEST(AndingFilterTest, ValueSetIsTheIntersectionOfTheBoundedConjuncts) {
    const auto filter = parseFilter(
        {"Filter: x <= 3", "Filter: x != 1", "Filter: y = 1", "And: 3"});

    EXPECT_EQ(filter->valueSetLeastUpperBoundFor("x", 0s),
              std::optional<std::bitset<32>>{0b1101});
}

TEST(OringFilterTest, GreatestLowerBoundIsTheLowestOfTheDisjuncts) {
    const auto filter =
        parseFilter({"Filter: x >= 5", "Filter: x = 10", "Or: 2"});

    EXPECT_EQ(filter->greatestLowerBoundFor("x", 0s),
              std::optional<int32_t>{5});
}

TEST(OringFilterTest, NoGreatestLowerBoundIfADisjunctHasNone) {
    const auto filter =
        parseFilter({"Filter: x >= 10", "Filter: x <= 5", "Or: 2"});

    EXPECT_EQ(filter->greatestLowerBoundFor("x", 0s), std::nullopt);
}

TEST(OringFilterTest, LeastUpperBoundIsTheHighestOfTheDisjuncts) {
    const auto filter =
        parseFilter({"Filter: x <= 5", "Filter: x = 10", "Or: 2"});

    EXPECT_EQ(filter->leastUpperBoundFor("x", 0s), std::optional<int32_t>{10});
}

TEST(OringFilterTest, NoLeastUpperBoundIfADisjunctHasNone) {
    const auto filter =
        parseFilter({"Filter: x <= 5", "Filter: x >= 10", "Or: 2"});

    EXPECT_EQ(filter->leastUpperBoundFor("x", 0s), std::nullopt);
}

TEST(OringFilterTest, ValueSetIsTheUnionOfTheDisjuncts) {
    const auto filter =
        parseFilter({"Filter: x = 1", "Filter: x = 3", "Or: 2"});

    EXPECT_EQ(filter->valueSetLeastUpperBoundFor("x", 0s),
              std::optional<std::bitset<32>>{0b1010});
}

TEST(OringFilterTest, NoValueSetIfADisjunctHasNone) {
    const auto filter =
        parseFilter({"Filter: x = 1", "Filter: y = 1", "Or: 2"});

    EXPECT_EQ(filter->valueSetLeastUpperBoundFor("x", 0s), std::nullopt);
}
