// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <filesystem>
#include <functional>
#include <iterator>
#include <memory>
#include <sstream>
#include <string>
#include <vector>

#include "BlobColumn.h"
#include "Row.h"
#include "gtest/gtest.h"

using namespace std::string_literals;
namespace fs = std::filesystem;

class FileFixture : public ::testing::Test {
public:
    const std::string content{"file\ncontent\n"};
    const std::vector<char> content_b{std::begin(content), std::end(content)};
    const fs::path basepath{fs::temp_directory_path() / "blob_column_tests"};
    const fs::path filename{"file.txt"};
    const fs::path fullpath{basepath / filename};

    void SetUp() override {
        fs::create_directories(basepath);
        std::ofstream ofs(fullpath);
        ofs << content;
        ofs.close();
    }
    void TearDown() override { fs::remove_all(basepath); }
};

struct DummyRow : Row {
    using Row::Row;
};

struct DummyValue {};

std::vector<char> to_value(const std::string &s) {
    return {std::begin(s), std::end(s)};
}

TEST_F(FileFixture, BlobColumnReadFile) {
    const auto val = DummyValue{};
    const auto row = DummyRow{&val};
    const auto col = BlobColumn<DummyRow>{
        "name"s,
        "description"s,
        {},
        BlobFileReader<DummyRow>{
            [this]() { return basepath; },
            [this](const DummyRow & /*row*/) { return filename; },
        }};

    ASSERT_NE(nullptr, col.getValue(row));
    EXPECT_FALSE(col.getValue(row)->empty());
    EXPECT_EQ(content_b, *col.getValue(row));
}
