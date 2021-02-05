// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <iterator>
#include <memory>
#include <string>
#include <vector>

#include "BlobColumn.h"
#include "Row.h"
#include "gtest/gtest.h"

using namespace std::string_literals;

struct DummyRow : Row {
    using Row::Row;
};

struct DummyValue {};

std::vector<char> to_value(const std::string& s) {
    return {std::begin(s), std::end(s)};
}

TEST(BlobColumn, ConstantBlob) {
    const auto v = to_value("hello"s);

    const auto val = DummyValue{};
    const auto row = DummyRow{&val};
    const auto col =
        BlobLambdaColumn<DummyRow>::Constant{"name"s, "description"s, v};

    ASSERT_NE(nullptr, col.getValue(row));
    EXPECT_EQ(v, *col.getValue(row));
}

TEST(BlobColumn, ConstantDefaultRow) {
    const auto v = to_value("hello"s);

    const auto row = DummyRow{nullptr};
    const auto col =
        BlobLambdaColumn<DummyRow>::Constant{"name"s, "description"s, v};

    ASSERT_NE(nullptr, col.getValue(row));
    EXPECT_EQ(v, *col.getValue(row));
}

TEST(BlobColumn, Reference) {
    const auto s = "hello"s;
    auto v = to_value(s);

    const auto row = DummyRow{nullptr};
    const auto col =
        BlobLambdaColumn<DummyRow>::Reference{"name"s, "description"s, v};

    ASSERT_NE(nullptr, col.getValue(row));
    EXPECT_EQ(v, *col.getValue(row));
    EXPECT_EQ(s.size(), col.getValue(row)->size());

    auto extra = "xxx"s;
    v.insert(std::end(v), std::begin(extra), std::end(extra));

    ASSERT_NE(nullptr, col.getValue(row));
    EXPECT_EQ(v, *col.getValue(row));
    EXPECT_EQ(s.size() + extra.size(), col.getValue(row)->size());
}
