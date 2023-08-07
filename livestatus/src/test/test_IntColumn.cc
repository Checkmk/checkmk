// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <string>
#include <variant>

#include "IntLambdaColumn.h"
#include "Row.h"
#include "gtest/gtest.h"

using namespace std::string_literals;

struct DummyRow : Row {
    using Row::Row;
};

struct DummyValue {};

TEST(IntColumn, ConstantInteger) {
    const auto v = 1337;

    const auto val = DummyValue{};
    const auto row = DummyRow{&val};
    const auto col =
        IntLambdaColumn<DummyRow>::Constant{"name"s, "description"s, v};

    EXPECT_EQ(v, col.getValue(row, nullptr));
}

TEST(IntColumn, ConstantDefaultRow) {
    const auto v = 1337;

    const auto row = DummyRow{nullptr};
    const auto col =
        IntLambdaColumn<DummyRow>::Constant{"name"s, "description"s, v};

    EXPECT_EQ(v, col.getValue(row, nullptr));
}

TEST(IntColumn, Reference) {
    auto v = 1337;

    const auto row = DummyRow{nullptr};
    const auto col =
        IntLambdaColumn<DummyRow>::Reference{"name"s, "description"s, v};

    EXPECT_EQ(v, col.getValue(row, nullptr));

    v *= 42;
    EXPECT_EQ(v, col.getValue(row, nullptr));
}

TEST(IntColumn, GetValueLambda) {
    auto v = 1337;

    const auto val = DummyValue{};
    const auto row = DummyRow{&val};
    const auto col = IntLambdaColumn<DummyRow>{
        "name"s, "description"s, {}, [v](const DummyRow& /*row*/) {
            return v;
        }};

    EXPECT_EQ(v, col.getValue(row, nullptr));
}

TEST(IntColumn, GetValueDefault) {
    auto v = 1337;

    const auto row = DummyRow{nullptr};
    const auto col = IntLambdaColumn<DummyRow>{
        "name"s, "description"s, {}, [v](const DummyRow& /*row*/) {
            return v;
        }};

    EXPECT_NE(v, col.getValue(row, nullptr));
    EXPECT_EQ(0, col.getValue(row, nullptr));
}
