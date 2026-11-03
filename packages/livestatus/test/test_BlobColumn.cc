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

#include "DummyMonitoringCore.h"
#include "TemporaryDirectory.h"
#include "gtest/gtest.h"
#include "livestatus/BlobColumn.h"
#include "livestatus/Column.h"
#include "livestatus/Row.h"

class ICore;

namespace {
constexpr std::string_view content{"file\ncontent\n"};
constexpr std::string_view filename{"file.txt"};

std::vector<char> as_chars(std::string_view sv) {
    return {std::begin(sv), std::end(sv)};
}
}  // namespace

class FileFixture : public ::testing::Test {
public:
    void SetUp() override {
        std::ofstream ofs{basepath() / filename};
        ofs << content;
        ofs.close();
    }

protected:
    [[nodiscard]] const std::filesystem::path &basepath() const {
        return basedir_.path();
    }

private:
    TemporaryDirectory basedir_{"blob_column_tests"};
};

struct DummyRow : Row {
    using Row::Row;
};

struct DummyValue {};

TEST_F(FileFixture, BlobColumnReadFile) {
    auto core = DummyMonitoringCore{};
    auto val = DummyValue{};
    auto row = DummyRow{&val};
    auto path = basepath() / filename;
    auto col = BlobColumn<DummyRow>{
        "name",
        "description",
        {},
        BlobFileReader<DummyRow>{
            [path](const DummyRow & /*row*/, const ICore & /*core*/) {
                return path;
            },
        }};

    ASSERT_NE(nullptr, col.getValue(row, core));
    EXPECT_FALSE(col.getValue(row, core)->empty());
    EXPECT_EQ(as_chars(content), *col.getValue(row, core));
}
