// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <chrono>
#include <functional>
#include <memory>
#include <string>

#include "Row.h"
#include "TimeColumn.h"
#include "gtest/gtest.h"

using namespace std::chrono_literals;
using namespace std::string_literals;
using Clock = std::chrono::system_clock;

struct DummyRow : Row {
    using Row::Row;
};

struct DummyValue {};

TEST(TimeColumn, GetValueLambda) {
    const auto v = Clock::now();
    const auto tz = 1h;
    const auto val = DummyValue{};
    const auto row = DummyRow{&val};
    const auto col = TimeColumn<DummyRow>{
        "name"s, "description"s, {}, [v](const DummyRow & /*row*/) {
            return v;
        }};

    EXPECT_EQ(v + tz, col.getValue(row, tz));
}

TEST(TimeColumn, GetValueDefault) {
    const auto v = Clock::now();
    const auto tz = 1h;
    const auto row = DummyRow{nullptr};
    const auto col = TimeColumn<DummyRow>{
        "name"s, "description"s, {}, [v](const DummyRow & /*row*/) {
            return v;
        }};

    EXPECT_NE(v + tz, col.getValue(row, tz));
    EXPECT_EQ(TimeColumn<DummyRow>::value_type{} + tz, col.getValue(row, tz));
}
