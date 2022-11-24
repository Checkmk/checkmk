// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <memory>
#include <ostream>
#include <string>

#include "Logger.h"
#include "Renderer.h"
#include "RendererBrokenCSV.h"
#include "data_encoding.h"
#include "gtest/gtest.h"

struct SeparatorsParam {
    OutputFormat format;
    std::string query;
    std::string row;
    std::string list;
    std::string sublist;
    std::string dict;

    friend std::ostream &operator<<(std::ostream &os,
                                    const SeparatorsParam &s) {
        return os << "SeparatorsParam{" << static_cast<int>(s.format) << ", "
                  << s.query << ", " << s.row << ", " << s.list << ", "
                  << s.sublist << "}";
    }
};

class SeparatorsTestFixture : public ::testing::TestWithParam<SeparatorsParam> {
    std::ostringstream out_;

public:
    std::unique_ptr<Renderer> make_renderer(OutputFormat format) {
        return Renderer::make(format, out_, Logger::getLogger("test"),
                              CSVSeparators{"\n", ";", ",", "|"},
                              Encoding::utf8);
    }
    std::string result() const { return out_.str(); }
};

TEST_P(SeparatorsTestFixture, QuerySeparators) {
    auto renderer = make_renderer(GetParam().format);
    renderer->beginQuery();
    renderer->output(1);
    renderer->separateQueryElements();
    renderer->output(2);
    renderer->endQuery();
    EXPECT_EQ(GetParam().query, result());
}

TEST_P(SeparatorsTestFixture, RowSeparators) {
    auto renderer = make_renderer(GetParam().format);
    renderer->beginRow();
    renderer->beginRowElement();
    renderer->output(1);
    renderer->endRowElement();
    renderer->separateRowElements();
    renderer->beginRowElement();
    renderer->output(2);
    renderer->endRowElement();
    renderer->endRow();
    EXPECT_EQ(GetParam().row, result());
}

TEST_P(SeparatorsTestFixture, ListSeparators) {
    auto renderer = make_renderer(GetParam().format);
    renderer->beginList();
    renderer->output(1);
    renderer->separateListElements();
    renderer->output(2);
    renderer->endList();
    EXPECT_EQ(GetParam().list, result());
}

TEST_P(SeparatorsTestFixture, SublistSeparators) {
    auto renderer = make_renderer(GetParam().format);
    renderer->beginSublist();
    renderer->output(1);
    renderer->separateSublistElements();
    renderer->output(2);
    renderer->endSublist();
    EXPECT_EQ(GetParam().sublist, result());
}

TEST_P(SeparatorsTestFixture, DictSeparators) {
    auto renderer = make_renderer(GetParam().format);
    renderer->beginDict();
    renderer->output(1);
    renderer->separateDictKeyValue();
    renderer->output(2);
    renderer->separateDictElements();
    renderer->output(3);
    renderer->separateDictKeyValue();
    renderer->output(4);
    renderer->endDict();
    EXPECT_EQ(GetParam().dict, result());
}

INSTANTIATE_TEST_SUITE_P(
    SeparatorsTests, SeparatorsTestFixture,
    ::testing::Values(
        SeparatorsParam{OutputFormat::csv,  //
                        "12", "\"1\",\"2\"\r\n", "1,2", "1|2", "1|2,3|4"},
        SeparatorsParam{OutputFormat::broken_csv,  //
                        "12", "1;2\n", "1,2", "1|2", "1|2,3|4"},
        SeparatorsParam{OutputFormat::json,  //
                        "[1,\n2]\n", "[1,2]", "[1,2]", "[1,2]", "{1:2,3:4}"},
        SeparatorsParam{OutputFormat::python,  //
                        "[1,\n2]\n", "[1,2]", "[1,2]", "[1,2]", "{1:2,3:4}"},
        SeparatorsParam{OutputFormat::python3,  //
                        "[1,\n2]\n", "[1,2]", "[1,2]", "[1,2]", "{1:2,3:4}"}));
