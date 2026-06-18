// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <functional>
#include <memory>
#include <string>
#include <vector>

#include "gtest/gtest.h"
#include "livestatus/Column.h"
#include "livestatus/ParsedQuery.h"
#include "livestatus/Renderer.h"
#include "livestatus/StringColumn.h"

using namespace std::string_literals;

namespace {
struct DummyRow {};

std::shared_ptr<Column> makeStringColumn(const std::string &name) {
    return std::make_shared<StringColumn<DummyRow>>(
        name, ""s, ColumnOffsets{},
        [](const DummyRow & /*row*/) { return ""s; });
}

ParsedQuery parse(const std::vector<std::string> &lines) {
    return ParsedQuery{lines,
                       []() -> std::vector<std::shared_ptr<Column>> {
                           return {makeStringColumn("name"s),
                                   makeStringColumn("alias"s)};
                       },
                       makeStringColumn};
}
}  // namespace

TEST(ParsedQueryTest, EmptyQueryUsesAllColumns) {
    const auto q = parse({});
    EXPECT_FALSE(q.error.has_value());
    EXPECT_EQ(q.columns.size(), 2U);
    EXPECT_TRUE(q.show_column_headers);
    EXPECT_TRUE(q.all_column_names.contains("name"));
    EXPECT_TRUE(q.all_column_names.contains("alias"));
}

TEST(ParsedQueryTest, ColumnsLineSelectsColumns) {
    const auto q = parse({"Columns: name alias"});
    EXPECT_FALSE(q.error.has_value());
    ASSERT_EQ(q.columns.size(), 2U);
    EXPECT_EQ(q.columns[0]->name(), "name");
    EXPECT_EQ(q.columns[1]->name(), "alias");
    EXPECT_FALSE(q.show_column_headers);
}

TEST(ParsedQueryTest, LimitIsParsed) {
    const auto q = parse({"Limit: 42"});
    EXPECT_FALSE(q.error.has_value());
    ASSERT_TRUE(q.limit.has_value());
    EXPECT_EQ(*q.limit, 42);
}

TEST(ParsedQueryTest, NegativeLimitIsAnError) {
    const auto q = parse({"Limit: -1"});
    EXPECT_TRUE(q.error.has_value());
    EXPECT_FALSE(q.limit.has_value());
}

TEST(ParsedQueryTest, ColumnHeadersOffIsHonored) {
    const auto q = parse({"Columns: name", "ColumnHeaders: off"});
    EXPECT_FALSE(q.error.has_value());
    EXPECT_FALSE(q.show_column_headers);
}

TEST(ParsedQueryTest, OutputFormatIsParsed) {
    const auto q = parse({"OutputFormat: json"});
    EXPECT_FALSE(q.error.has_value());
    EXPECT_EQ(q.output_format, OutputFormat::json);
}

TEST(ParsedQueryTest, KeepAliveOnIsParsed) {
    const auto q = parse({"KeepAlive: on"});
    EXPECT_FALSE(q.error.has_value());
    EXPECT_TRUE(q.keepalive);
}

TEST(ParsedQueryTest, UndefinedHeaderIsAnError) {
    const auto q = parse({"Bogus: whatever"});
    EXPECT_TRUE(q.error.has_value());
}

TEST(ParsedQueryTest, OrderByDefaultsToAscendingLexicographic) {
    const auto q = parse({"OrderBy: name"});
    EXPECT_FALSE(q.error.has_value());
    ASSERT_EQ(q.order_by.size(), 1U);
    EXPECT_EQ(q.order_by[0].column->name(), "name");
    EXPECT_FALSE(q.order_by[0].key.has_value());
    EXPECT_EQ(q.order_by[0].direction, OrderByDirection::ascending);
    EXPECT_EQ(q.order_by[0].sorting, OrderBySorting::lexicographic);
}

TEST(ParsedQueryTest, OrderByAscending) {
    const auto q = parse({"OrderBy: name asc"});
    EXPECT_FALSE(q.error.has_value());
    ASSERT_EQ(q.order_by.size(), 1U);
    EXPECT_EQ(q.order_by[0].direction, OrderByDirection::ascending);
    EXPECT_EQ(q.order_by[0].sorting, OrderBySorting::lexicographic);
}

TEST(ParsedQueryTest, OrderByDescending) {
    const auto q = parse({"OrderBy: name desc"});
    EXPECT_FALSE(q.error.has_value());
    ASSERT_EQ(q.order_by.size(), 1U);
    EXPECT_EQ(q.order_by[0].direction, OrderByDirection::descending);
    EXPECT_EQ(q.order_by[0].sorting, OrderBySorting::lexicographic);
}

TEST(ParsedQueryTest, OrderByNatural) {
    const auto q = parse({"OrderBy: name natural"});
    EXPECT_FALSE(q.error.has_value());
    ASSERT_EQ(q.order_by.size(), 1U);
    EXPECT_EQ(q.order_by[0].direction, OrderByDirection::ascending);
    EXPECT_EQ(q.order_by[0].sorting, OrderBySorting::natural);
}

TEST(ParsedQueryTest, OrderByDescendingNatural) {
    const auto q = parse({"OrderBy: name desc natural"});
    EXPECT_FALSE(q.error.has_value());
    ASSERT_EQ(q.order_by.size(), 1U);
    EXPECT_EQ(q.order_by[0].direction, OrderByDirection::descending);
    EXPECT_EQ(q.order_by[0].sorting, OrderBySorting::natural);
}

TEST(ParsedQueryTest, OrderByDictColumnKey) {
    const auto q = parse({"OrderBy: labels.foo"});
    EXPECT_FALSE(q.error.has_value());
    ASSERT_EQ(q.order_by.size(), 1U);
    EXPECT_EQ(q.order_by[0].column->name(), "labels");
    ASSERT_TRUE(q.order_by[0].key.has_value());
    EXPECT_EQ(*q.order_by[0].key, "foo");
}

TEST(ParsedQueryTest, MultipleOrderByLinesArePreserved) {
    const auto q = parse({"OrderBy: name asc", "OrderBy: alias desc natural"});
    EXPECT_FALSE(q.error.has_value());
    ASSERT_EQ(q.order_by.size(), 2U);
    EXPECT_EQ(q.order_by[0].column->name(), "name");
    EXPECT_EQ(q.order_by[0].direction, OrderByDirection::ascending);
    EXPECT_EQ(q.order_by[1].column->name(), "alias");
    EXPECT_EQ(q.order_by[1].direction, OrderByDirection::descending);
    EXPECT_EQ(q.order_by[1].sorting, OrderBySorting::natural);
}

TEST(ParsedQueryTest, OrderByMissingColumnIsAnError) {
    const auto q = parse({"OrderBy:"});
    EXPECT_TRUE(q.error.has_value());
    EXPECT_TRUE(q.order_by.empty());
}

TEST(ParsedQueryTest, OrderBySuperfluousArgumentIsAnError) {
    const auto q = parse({"OrderBy: name asc desc"});
    EXPECT_TRUE(q.error.has_value());
    EXPECT_TRUE(q.order_by.empty());
}

TEST(ParsedQueryTest, OrderBySortingMustFollowDirection) {
    const auto q = parse({"OrderBy: name natural asc"});
    EXPECT_TRUE(q.error.has_value());
    EXPECT_TRUE(q.order_by.empty());
}
