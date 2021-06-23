// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <algorithm>
#include <chrono>
#include <string>
#include <vector>

#include "ListLambdaColumn.h"
#include "Row.h"
#include "gtest/gtest.h"

using namespace std::chrono_literals;
using namespace std::string_literals;

struct DummyRow : Row {
    using Row::Row;
};

struct DummyValue {};

TEST(ListColumn, ConstantList) {
    const auto v = ListColumn::value_type{"hello"s, "world"s};
    const auto val = DummyValue{};
    const auto row = DummyRow{&val};
    const auto col = ListColumn::Constant{"name"s, "description"s, v};

    EXPECT_EQ(v, col.getValue(row, nullptr, 0s));
}

TEST(ListColumn, ConstantDefaultRow) {
    const auto v = ListColumn::value_type{"hello"s, "world"s};
    const auto row = DummyRow{nullptr};
    const auto col = ListColumn::Constant{"name"s, "description"s, v};

    EXPECT_EQ(v, col.getValue(row, nullptr, 0s));
}

TEST(ListColumn, Reference) {
    auto v = ListColumn::value_type{"hello"s, "world"s};
    const auto row = DummyRow{nullptr};
    const auto col = ListColumn::Reference{"name"s, "description"s, v};

    EXPECT_EQ(v, col.getValue(row, nullptr, 0s));

    v.emplace_back("good morning"s);
    EXPECT_EQ(v, col.getValue(row, nullptr, 0s));
}

TEST(ListColumn, GetValueLambda) {
    auto v = ListColumn::value_type{"hello"s, "world"s};

    const auto val = DummyValue{};
    const auto row = DummyRow{&val};
    const auto col = ListColumn::Callback<DummyRow>{
        "name"s, "description"s, {}, [v](const DummyRow& /*row*/) {
            return v;
        }};

    EXPECT_EQ(v, col.getValue(row, nullptr, 0s));
}

TEST(ListColumn, GetValueDefault) {
    auto v = ListColumn::value_type{"hello"s, "world"s};

    const auto row = DummyRow{nullptr};
    const auto col = ListColumn::Callback<DummyRow>{
        "name"s, "description"s, {}, [v](const DummyRow& /*row*/) {
            return v;
        }};

    EXPECT_NE(v, col.getValue(row, nullptr, 0s));
    EXPECT_EQ(ListColumn::value_type{}, col.getValue(row, nullptr, 0s));
}
