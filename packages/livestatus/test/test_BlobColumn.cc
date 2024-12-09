// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <filesystem>
#include <fstream>
#include <functional>
#include <iterator>
#include <memory>
#include <string>
#include <string_view>
#include <vector>

#include "gtest/gtest.h"
#include "livestatus/BlobColumn.h"
#include "livestatus/Column.h"
#include "livestatus/Row.h"

namespace {
constexpr std::string_view content{"file\ncontent\n"};
constexpr std::string_view filename{"file.txt"};

std::filesystem::path basepath() {
    return std::filesystem::temp_directory_path() / "blob_column_tests";
}

std::vector<char> as_chars(std::string_view sv) {
    return {std::begin(sv), std::end(sv)};
}
}  // namespace

class FileFixture : public ::testing::Test {
public:
    void SetUp() override {
        std::filesystem::create_directories(basepath());
        std::ofstream ofs{basepath() / filename};
        ofs << content;
        ofs.close();
    }

    void TearDown() override { std::filesystem::remove_all(basepath()); }
};

struct DummyRow : Row {
    using Row::Row;
};

struct DummyValue {};

TEST_F(FileFixture, BlobColumnReadFile) {
    auto val = DummyValue{};
    auto row = DummyRow{&val};
    auto col = BlobColumn<DummyRow>{
        "name",
        "description",
        {},
        BlobFileReader<DummyRow>{
            [](const DummyRow & /*row*/) { return basepath() / filename; },
        }};

    ASSERT_NE(nullptr, col.getValue(row));
    EXPECT_FALSE(col.getValue(row)->empty());
    EXPECT_EQ(as_chars(content), *col.getValue(row));
}
