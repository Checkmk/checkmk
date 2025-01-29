// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <chrono>
#include <string>

#include "gtest/gtest.h"
#include "livestatus/Column.h"
#include "livestatus/ListColumn.h"
#include "livestatus/Row.h"
#include "livestatus/User.h"

using namespace std::chrono_literals;
using namespace std::string_literals;

struct DummyRow : Row {
    using Row::Row;
};

struct DummyValue {};

TEST(ListColumn, GetValueLambda) {
    using value_type = ListColumn<DummyRow>::value_type;
    value_type v{"hello"s, "world"s};  // NOLINT(misc-const-correctness)

    const auto val = DummyValue{};
    const auto row = DummyRow{&val};
    const auto col = ListColumn<DummyRow>{
        "name"s, "description"s, {}, [v](const DummyRow & /*row*/) {
            return v;
        }};

    EXPECT_EQ(v, col.getValue(row, NoAuthUser{}, 0s));
}

TEST(ListColumn, GetValueDefault) {
    using value_type = ListColumn<DummyRow>::value_type;
    value_type v{"hello"s, "world"s};  // NOLINT(misc-const-correctness)

    const auto row = DummyRow{nullptr};
    const auto col = ListColumn<DummyRow>{
        "name"s, "description"s, {}, [v](const DummyRow & /*row*/) {
            return v;
        }};

    EXPECT_NE(v, col.getValue(row, NoAuthUser{}, 0s));
    EXPECT_EQ(value_type{}, col.getValue(row, NoAuthUser{}, 0s));
}
