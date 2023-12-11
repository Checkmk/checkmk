// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <memory>
#include <string_view>

#include "gtest/gtest.h"
#include "livestatus/strutil.h"

using namespace std::string_view_literals;

// next_token() tests ----------------------------------------------------------

TEST(StrutilTest, NextTokenEmptyText) {
    char text[] = "";
    char *current = text;

    char *token = next_token(&current, ';');

    EXPECT_EQ(current, text);
    EXPECT_EQ(token, nullptr);
}

TEST(StrutilTest, NextTokenDelimNotFound) {
    char text[] = "foo";
    char *current = text;

    char *token = next_token(&current, ';');

    EXPECT_EQ(current, text + "foo"sv.size());
    EXPECT_STREQ(current, "");
    EXPECT_STREQ(token, "foo");
}

TEST(StrutilTest, NextTokenEmptyToken) {
    char text[] = ";foo";
    char *current = text;

    char *token = next_token(&current, ';');

    EXPECT_EQ(current, text + 1);
    EXPECT_STREQ(current, "foo");
    EXPECT_STREQ(token, "");
}

TEST(StrutilTest, NextTokenDelimFoundAtEnd) {
    char text[] = "foo;";
    char *current = text;

    char *token = next_token(&current, ';');

    EXPECT_EQ(current, text + "foo"sv.size() + 1);
    EXPECT_STREQ(current, "");
    EXPECT_STREQ(token, "foo");
}

TEST(StrutilTest, NextTokenDelimFound) {
    char text[] = "foo;bar;baz";
    char *current = text;

    char *token = next_token(&current, ';');

    EXPECT_EQ(current, text + "foo"sv.size() + 1);
    EXPECT_STREQ(current, "bar;baz");
    EXPECT_STREQ(token, "foo");
}
