// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <memory>
#include <string>

#include "DoubleColumn.h"
#include "Row.h"
#include "gtest/gtest.h"

using namespace std::string_literals;

struct DummyRow : Row {
    using Row::Row;
};

struct DummyValue {};

TEST(DoubleColumn, GetValueLambda) {
    const auto v = 5.0;

    const auto val = DummyValue{};
    const auto row = DummyRow{&val};
    const auto col = DoubleColumn<DummyRow>{
        "name"s, "description"s, {}, [v](const DummyRow& /*row*/) {
            return v;
        }};

    EXPECT_EQ(v, col.getValue(row));
}

TEST(DoubleColumn, GetValueDefault) {
    const auto v = 5.0;

    const auto row = DummyRow{nullptr};
    const auto col = DoubleColumn<DummyRow>{
        "name"s, "description"s, {}, [v](const DummyRow& /*row*/) {
            return v;
        }};

    EXPECT_NE(v, col.getValue(row));
    EXPECT_EQ(0.0, col.getValue(row));
}
