// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <filesystem>
#include <string>
#include <tuple>
#include <variant>

#include "TemporaryDirectory.h"
#include "gtest/gtest.h"
#include "livestatus/FileSystemHelper.h"

namespace fs = std::filesystem;

// A directory and a path, both relative to a temporary directory, and whether
// the directory contains the path when both are created and when they aren't.
class PathContainsTest : public ::testing::TestWithParam<
                             std::tuple<fs::path, fs::path, bool, bool>> {
protected:
    void SetUp() override {
        // operator/ would drop the temporary directory for absolute paths.
        ASSERT_TRUE(std::get<0>(GetParam()).is_relative());
        ASSERT_TRUE(std::get<1>(GetParam()).is_relative());
    }

    [[nodiscard]] fs::path directory() const {
        return basedir_.path() / std::get<0>(GetParam());
    }
    [[nodiscard]] fs::path path() const {
        return basedir_.path() / std::get<1>(GetParam());
    }
    [[nodiscard]] static bool contained_when_created() {
        return std::get<2>(GetParam());
    }
    [[nodiscard]] static bool contained_when_not_created() {
        return std::get<3>(GetParam());
    }

private:
    TemporaryDirectory basedir_{"file_system_helper_tests"};
};

TEST_P(PathContainsTest, PathsCreated) {
    fs::create_directories(directory());
    fs::create_directories(path());
    ASSERT_EQ(contained_when_created(), mk::path_contains(directory(), path()));
}

TEST_P(PathContainsTest, PathsNotCreated) {
    ASSERT_EQ(contained_when_not_created(),
              mk::path_contains(directory(), path()));
}

INSTANTIATE_TEST_SUITE_P(
    PathContainsTests, PathContainsTest,
    ::testing::Values(std::make_tuple("", "", true, true),
                      std::make_tuple("abc/def", "abc/def", true, false),
                      std::make_tuple("xyz/../def", "def", true, false),
                      std::make_tuple("abc/def", "xyz/../abc/def", true, false),
                      std::make_tuple("", "abc/def", true, false),
                      std::make_tuple("abc/def", "", false, false),
                      std::make_tuple("abc/def", "xyz/abc", false, false),
                      std::make_tuple("abc/def", "xyz", false, false),
                      std::make_tuple("xyz", "abc/def", false, false)));

class UnescapeFileNameFixture
    : public ::testing::TestWithParam<std::tuple<std::string, std::string>> {};

TEST_P(UnescapeFileNameFixture, TestUnescapeFileName) {
    ASSERT_EQ(mk::unescape_filename(std::get<0>(GetParam())),
              std::get<1>(GetParam()));
}

INSTANTIATE_TEST_SUITE_P(
    TestUnescapeFileName, UnescapeFileNameFixture,
    ::testing::Values(std::make_tuple(R"(/a/b/c)", R"(/a/b/c)"),
                      std::make_tuple(R"(/a/b\\c)", R"(/a/b\c)"),
                      std::make_tuple(R"(\\a\\b\\c)", R"(\a\b\c)"),
                      std::make_tuple(R"(/a/b\sc)", R"(/a/b c)"),
                      std::make_tuple(R"(\sa\sb\sc)", R"( a b c)"),
                      std::make_tuple(R"(\\\sa\\\sb\\\sc)", R"(\ a\ b\ c)"),
                      std::make_tuple(R"(\\sa\\sb\\sc)", R"(\sa\sb\sc)"),
                      std::make_tuple(R"(\\\sa\\\sb\\\sc)", R"(\ a\ b\ c)"),
                      std::make_tuple(R"(a\xb)", R"(axb)"),
                      std::make_tuple(R"(abc\)", R"(abc)")));
