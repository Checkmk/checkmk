// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <functional>
#include <memory>
#include <string>

#include "Row.h"
#include "StringColumn.h"
#include "gtest/gtest.h"

using namespace std::string_literals;

struct DummyRow : Row {
    using Row::Row;
};

struct DummyValue {};

TEST(StringColumn, GetValueLambda) {
    auto v = "hello"s;

    const auto val = DummyValue{};
    const auto row = DummyRow{&val};
    const auto col = StringColumn<DummyRow>{
        "name"s, "description"s, {}, [v](const DummyRow & /*row*/) {
            return v;
        }};

    EXPECT_EQ(v, col.getValue(row));
}

TEST(StringColumn, GetValueDefault) {
    auto v = "hello"s;

    const auto row = DummyRow{nullptr};
    const auto col = StringColumn<DummyRow>{
        "name"s, "description"s, {}, [v](const DummyRow & /*row*/) {
            return v;
        }};

    EXPECT_NE(v, col.getValue(row));
    EXPECT_EQ(""s, col.getValue(row));
}
