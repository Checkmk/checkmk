// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <cctype>
#include <chrono>
#include <cmath>
#include <iomanip>
#include <memory>
#include <sstream>
#include <string>
#include <vector>

#include "gtest/gtest.h"
#include "livestatus/Logger.h"
#include "livestatus/OStreamStateSaver.h"
#include "livestatus/Renderer.h"
#include "livestatus/RendererBrokenCSV.h"
#include "livestatus/data_encoding.h"

using namespace std::chrono_literals;

namespace {
// This class is just a workaround for encoding bugs in googletest where
// test_details.xml might end up containing invalid XML.
struct Blob {
    std::string contents;
    auto operator<=>(const Blob &) const = default;
};

std::ostream &operator<<(std::ostream &os, const Blob &blob) {
    const OStreamStateSaver s(os);
    for (auto ch : blob.contents) {
        if (std::isprint(ch) != 0) {
            os << ch;
        } else {
            os << R"(\x)" << std::hex << std::setw(2) << std::setfill('0')
               << static_cast<unsigned>(static_cast<unsigned char>(ch));
        }
    }
    return os;
}

struct Param {
    OutputFormat format;
    std::string query;
    std::string row;
    std::string list;
    std::string sublist;
    std::string dict;
    std::string unicode;
    std::string null;
    Blob blob;
    std::string string;
};

std::ostream &operator<<(std::ostream &os, const Param &p) {
    return os << "Param{" << static_cast<int>(p.format) << ", " << p.query
              << ", " << p.row << ", " << p.list << ", " << p.sublist << ", "
              << p.dict << ", " << p.null << ", " << p.blob << ", " << p.string
              << "}";
}
};  // namespace

class Fixture : public ::testing::TestWithParam<Param> {
    std::ostringstream out_;

public:
    std::unique_ptr<Renderer> make_renderer(OutputFormat format) {
        return Renderer::make(format, out_, Logger::getLogger("test"),
                              CSVSeparators{"\n", ";", ",", "|"},
                              Encoding::utf8);
    }
    void clear_result() { out_.str(""); }
    std::string result() const { return out_.str(); }
};

TEST_P(Fixture, QuerySeparators) {
    auto renderer = make_renderer(GetParam().format);
    renderer->beginQuery();
    renderer->output(1);
    renderer->separateQueryElements();
    renderer->output(2);
    renderer->endQuery();
    EXPECT_EQ(GetParam().query, result());
}

TEST_P(Fixture, RowSeparators) {
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

TEST_P(Fixture, ListSeparators) {
    auto renderer = make_renderer(GetParam().format);
    renderer->beginList();
    renderer->output(1);
    renderer->separateListElements();
    renderer->output(2);
    renderer->endList();
    EXPECT_EQ(GetParam().list, result());
}

TEST_P(Fixture, SublistSeparators) {
    auto renderer = make_renderer(GetParam().format);
    renderer->beginSublist();
    renderer->output(1);
    renderer->separateSublistElements();
    renderer->output(2);
    renderer->endSublist();
    EXPECT_EQ(GetParam().sublist, result());
}

TEST_P(Fixture, DictSeparators) {
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

TEST_P(Fixture, Integrals) {
    auto renderer = make_renderer(GetParam().format);

    clear_result();
    renderer->output(-4711);
    EXPECT_EQ("-4711", result());

    clear_result();
    renderer->output(12345678U);
    EXPECT_EQ("12345678", result());

    clear_result();
    renderer->output(-9876543210L);
    EXPECT_EQ("-9876543210", result());

    clear_result();
    renderer->output(876543212345UL);
    EXPECT_EQ("876543212345", result());
}

TEST_P(Fixture, Double) {
    auto renderer = make_renderer(GetParam().format);

    clear_result();
    renderer->output(-1.25);
    EXPECT_EQ("-1.25", result());

    clear_result();
    renderer->output(1234.5);
    EXPECT_EQ("1234.5", result());

    clear_result();
    renderer->output(std::nan(""));
    EXPECT_EQ(GetParam().null, result());
}

TEST_P(Fixture, UnicodeChar) {
    auto renderer = make_renderer(GetParam().format);

    clear_result();
    renderer->outputUnicodeChar(0x57U);
    EXPECT_EQ("\\u0057", result());

    clear_result();
    renderer->outputUnicodeChar(0x3b5U);
    EXPECT_EQ("\\u03b5", result());

    clear_result();
    renderer->outputUnicodeChar(0x1f60bU);
    EXPECT_EQ(GetParam().unicode, result());
}

TEST_P(Fixture, RowFragment) {
    auto renderer = make_renderer(GetParam().format);
    renderer->output(RowFragment{"Blöhööööd!\nMöp...\t\x47\x11"});
    EXPECT_EQ("Blöhööööd!\nMöp...\t\x47\x11", result());
}

TEST_P(Fixture, Null) {
    auto renderer = make_renderer(GetParam().format);
    renderer->output(Null{});
    EXPECT_EQ(GetParam().null, result());
}

TEST_P(Fixture, Blob) {
    auto renderer = make_renderer(GetParam().format);
    renderer->output(std::vector<char>{'p', '\\', '\x0a', '\xff', '\x0e'});
    EXPECT_EQ(GetParam().blob, Blob{result()});
}

TEST_P(Fixture, String) {
    auto renderer = make_renderer(GetParam().format);
    renderer->output(std::string{"A small\nt\u03b5st...\U0001f60b"});
    EXPECT_EQ(GetParam().string, result());
}

TEST_P(Fixture, TimePoint) {
    auto renderer = make_renderer(GetParam().format);
    renderer->output(std::chrono::system_clock::time_point{31415926s});
    EXPECT_EQ("31415926", result());
}

INSTANTIATE_TEST_SUITE_P(
    RendererTests, Fixture,
    ::testing::Values(
        Param{.format = OutputFormat::csv,
              .query = "12",
              .row = "\"1\",\"2\"\r\n",
              .list = "1,2",
              .sublist = "1|2",
              .dict = "1|2,3|4",
              .unicode = "\\U0001f60b",
              .null = "",
              .blob = {"p\\\n\xFF\xE"},
              .string = "A small\nt\xCE\xB5st...\xF0\x9F\x98\x8B"},
        Param{.format = OutputFormat::broken_csv,
              .query = "12",
              .row = "1;2\n",
              .list = "1,2",
              .sublist = "1|2",
              .dict = "1|2,3|4",
              .unicode = "\\U0001f60b",
              .null = "",
              .blob = {"p\\\n\xFF\xE"},
              .string = "A small\nt\xCE\xB5st...\xF0\x9F\x98\x8B"},
        Param{.format = OutputFormat::json,
              .query = "[1,\n2]\n",
              .row = "[1,2]",
              .list = "[1,2]",
              .sublist = "[1,2]",
              .dict = "{1:2,3:4}",
              .unicode = "\\ud83d\\ude0b",
              .null = "null",
              .blob = {"\"p\\u005c\\u000a\\u00ff\\u000e\""},
              .string = "\"A small\\u000at\\u03b5st...\\ud83d\\ude0b\""},
        Param{.format = OutputFormat::python3,
              .query = "[1,\n2]\n",
              .row = "[1,2]",
              .list = "[1,2]",
              .sublist = "[1,2]",
              .dict = "{1:2,3:4}",
              .unicode = "\\U0001f60b",
              .null = "None",
              .blob = {"b\"p\\x5c\\x0a\\xff\\x0e\""},
              .string = "\"A small\\u000at\\u03b5st...\\U0001f60b\""}));

namespace {
class RecordingHandler : public Handler {
public:
    explicit RecordingHandler(std::vector<std::string> &messages)
        : messages_{messages} {}

    void publish(const LogRecord &record) override {
        messages_.push_back(record.getMessage());
    }

private:
    std::vector<std::string> &messages_;
};

struct StringCase {
    std::string name;
    Encoding encoding;
    std::string input;
    std::string output;
    std::vector<std::string> warnings;
};

// Only the name, the input is not valid UTF-8, see Blob above.
std::ostream &operator<<(std::ostream &os, const StringCase &c) {
    return os << c.name;
}

std::string case_name(const ::testing::TestParamInfo<StringCase> &info) {
    return info.param.name;
}
}  // namespace

class JSONString : public ::testing::TestWithParam<StringCase> {
public:
    void SetUp() override {
        logger_->setHandler(std::make_unique<RecordingHandler>(warnings_));
        logger_->setUseParentHandlers(false);
    }

    void TearDown() override {
        logger_->setUseParentHandlers(true);
        logger_->setHandler(nullptr);
    }

    [[nodiscard]] std::string render(Encoding encoding,
                                     const std::string &value) const {
        std::ostringstream out;
        Renderer::make(OutputFormat::json, out, logger_,
                       CSVSeparators{"\n", ";", ",", "|"}, encoding)
            ->output(value);
        return out.str();
    }

    [[nodiscard]] const std::vector<std::string> &warnings() const {
        return warnings_;
    }

private:
    Logger *const logger_{Logger::getLogger("test.Renderer")};
    std::vector<std::string> warnings_;
};

TEST_P(JSONString, EscapesUpToFirstMalformedByte) {
    const auto &param = GetParam();

    const auto output = render(param.encoding, param.input);

    EXPECT_EQ(param.output, output);
    EXPECT_EQ(param.warnings, warnings());
}

INSTANTIATE_TEST_SUITE_P(
    CompleteUTF8AtEnd, JSONString,
    ::testing::Values(StringCase{.name = "TwoBytes",
                                 .encoding = Encoding::utf8,
                                 .input = "a\xCE\xB5",
                                 .output = R"("a\u03b5")",
                                 .warnings = {}},
                      StringCase{.name = "ThreeBytes",
                                 .encoding = Encoding::utf8,
                                 .input = "a\xE2\x82\xAC",
                                 .output = R"("a\u20ac")",
                                 .warnings = {}},
                      StringCase{.name = "FourBytes",
                                 .encoding = Encoding::utf8,
                                 .input = "a\xF0\x9F\x98\x8B",
                                 .output = R"("a\ud83d\ude0b")",
                                 .warnings = {}}),
    case_name);

INSTANTIATE_TEST_SUITE_P(
    TruncatedUTF8, JSONString,
    ::testing::Values(StringCase{.name = "TwoBytes",
                                 .encoding = Encoding::utf8,
                                 .input = "a\xCE",
                                 .output = R"("a")",
                                 .warnings = {"UTF-8 sequence too short"}},
                      StringCase{.name = "ThreeBytes",
                                 .encoding = Encoding::utf8,
                                 .input = "a\xE2\x82",
                                 .output = R"("a")",
                                 .warnings = {"UTF-8 sequence too short"}},
                      StringCase{.name = "FourBytes",
                                 .encoding = Encoding::utf8,
                                 .input = "a\xF0\x9F\x98",
                                 .output = R"("a")",
                                 .warnings = {"UTF-8 sequence too short"}}),
    case_name);

INSTANTIATE_TEST_SUITE_P(
    InvalidUTF8, JSONString,
    ::testing::Values(
        StringCase{.name = "SecondOfTwoBytes",
                   .encoding = Encoding::utf8,
                   .input = "a\xCEzz",
                   .output = R"("a")",
                   .warnings = {"invalid byte 122 in UTF-8 sequence"}},
        StringCase{.name = "SecondOfThreeBytes",
                   .encoding = Encoding::utf8,
                   .input = "a\xE2z\xACz",
                   .output = R"("a")",
                   .warnings = {"invalid byte 122 in UTF-8 sequence"}},
        StringCase{.name = "ThirdOfThreeBytes",
                   .encoding = Encoding::utf8,
                   .input = "a\xE2\x82zz",
                   .output = R"("a")",
                   .warnings = {"invalid byte 122 in UTF-8 sequence"}},
        StringCase{.name = "SecondOfFourBytes",
                   .encoding = Encoding::utf8,
                   .input = "a\xF0z\x98\x8Bz",
                   .output = R"("a")",
                   .warnings = {"invalid byte 122 in UTF-8 sequence"}},
        StringCase{.name = "ThirdOfFourBytes",
                   .encoding = Encoding::utf8,
                   .input = "a\xF0\x9Fz\x8Bz",
                   .output = R"("a")",
                   .warnings = {"invalid byte 122 in UTF-8 sequence"}},
        StringCase{.name = "FourthOfFourBytes",
                   .encoding = Encoding::utf8,
                   .input = "a\xF0\x9F\x98zz",
                   .output = R"("a")",
                   .warnings = {"invalid byte 122 in UTF-8 sequence"}},
        StringCase{.name = "OverlongLeadByte",
                   .encoding = Encoding::utf8,
                   .input = "a\xC0\xAFz",
                   .output = R"("a")",
                   .warnings = {"invalid byte 192 in UTF-8 sequence"}},
        StringCase{.name = "TooLargeLeadByte",
                   .encoding = Encoding::utf8,
                   .input = "a\xF5\x80\x80\x80z",
                   .output = R"("a")",
                   .warnings = {"invalid byte 245 in UTF-8 sequence"}},
        StringCase{.name = "ContinuationAsLeadByte",
                   .encoding = Encoding::utf8,
                   .input = "a\x80z",
                   .output = R"("a")",
                   .warnings = {"invalid byte 128 in UTF-8 sequence"}}),
    case_name);

INSTANTIATE_TEST_SUITE_P(
    MixedEncoding, JSONString,
    ::testing::Values(StringCase{.name = "UTF8AtEnd",
                                 .encoding = Encoding::mixed,
                                 .input = "a\xC3\xA4",
                                 .output = R"("a\u00e4")",
                                 .warnings = {}},
                      StringCase{.name = "Latin1",
                                 .encoding = Encoding::mixed,
                                 .input = "a\xE4z",
                                 .output = R"("a\u00e4z")",
                                 .warnings = {}},
                      StringCase{.name = "TruncatedUTF8",
                                 .encoding = Encoding::mixed,
                                 .input = "a\xC3",
                                 .output = R"("a")",
                                 .warnings = {"UTF-8 sequence too short"}},
                      StringCase{
                          .name = "InvalidUTF8",
                          .encoding = Encoding::mixed,
                          .input = "a\xC3zz",
                          .output = R"("a")",
                          .warnings = {"invalid byte 122 in UTF-8 sequence"}}),
    case_name);
