// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <cassert>
#include <filesystem>
#include <memory>
#include <tuple>
#include <utility>

#include "FileSystemHelper.h"
#include "gtest/gtest.h"

namespace fs = std::filesystem;

class PathContainsFixtureBase
    : public ::testing::TestWithParam<std::tuple<fs::path, fs::path, bool>> {
protected:
    [[nodiscard]] fs::path basepath() const { return basepath_; };
    [[nodiscard]] fs::path directory() const {
        return basepath() / directory_;
    };
    [[nodiscard]] fs::path path() const { return basepath() / path_; };
    virtual void SetUp_(const fs::path &directory, const fs::path &path) = 0;
    void TearDown() override { fs::remove_all(basepath()); }

private:
    fs::path basepath_ = fs::temp_directory_path() / "crash_report_tests";
    fs::path directory_;
    fs::path path_;
};

void PathContainsFixtureBase::SetUp_(const fs::path &_directory,
                                     const fs::path &_path) {
    fs::create_directories(basepath());
    // Make sure the dirs are going to be under basepath.
    assert(_directory.is_relative() and _path.is_relative());
    directory_ = _directory;
    path_ = _path;
}

class PathContainsFixtureWithPathCreation : public PathContainsFixtureBase {
protected:
    void SetUp_(const fs::path &_directory, const fs::path &_path) final {
        PathContainsFixtureBase::SetUp_(_directory, _path);
        fs::create_directories(directory());
        fs::create_directories(path());
    }
};

class PathContainsFixtureWithoutPathCreation : public PathContainsFixtureBase {
protected:
    void SetUp_(const fs::path &_directory, const fs::path &_path) final {
        PathContainsFixtureBase::SetUp_(_directory, _path);
    }
};

TEST_P(PathContainsFixtureWithPathCreation, TestPathContains) {
    bool expected = std::get<2>(GetParam());
    SetUp_(std::get<0>(GetParam()), std::get<1>(GetParam()));
    ASSERT_EQ(expected, mk::path_contains(directory(), path()));
}

TEST_P(PathContainsFixtureWithoutPathCreation, TestPathContains) {
    bool expected = std::get<2>(GetParam());
    SetUp_(std::get<0>(GetParam()), std::get<1>(GetParam()));
    ASSERT_EQ(expected, mk::path_contains(directory(), path()));
}

INSTANTIATE_TEST_SUITE_P(
    PathContainsTestsWithPath, PathContainsFixtureWithPathCreation,
    ::testing::Values(std::make_tuple("", "", true),
                      std::make_tuple("abc/def", "abc/def", true),
                      std::make_tuple("xyz/../def", "def", true),
                      std::make_tuple("abc/def", "xyz/../abc/def", true),
                      std::make_tuple("", "abc/def", true),
                      std::make_tuple("abc/def", "", false),
                      std::make_tuple("abc/def", "xyz/abc", false),
                      std::make_tuple("abc/def", "xyz", false),
                      std::make_tuple("xyz", "abc/def", false)));

INSTANTIATE_TEST_SUITE_P(
    PathContainsTestsWithoutPath, PathContainsFixtureWithoutPathCreation,
    ::testing::Values(std::make_tuple("", "", true),
                      std::make_tuple("abc/def", "abc/def", false),
                      std::make_tuple("xyz/../def", "def", false),
                      std::make_tuple("abc/def", "xyz/../abc/def", false),
                      std::make_tuple("", "abc/def", false),
                      std::make_tuple("abc/def", "", false),
                      std::make_tuple("abc/def", "xyz/abc", false),
                      std::make_tuple("abc/def", "xyz", false),
                      std::make_tuple("xyz", "abc/def", false)));

class UnescapeFileNameFixture
    : public ::testing::TestWithParam<std::tuple<fs::path, fs::path>> {};

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
                      std::make_tuple(R"(\\\sa\\\sb\\\sc)", R"(\ a\ b\ c)")));
