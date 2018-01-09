#include "gmock/gmock.h"
#include "gtest/gtest.h"
#include "sections/SectionLogwatch.h"
#include "test/MockWinApi.h"
#include "types.h"

using namespace ::testing;

class wa_SectionLogwatchTest : public Test {};

bool operator==(const condition_pattern &c1, const condition_pattern &c2) {
    return c1.state == c2.state && c1.glob_pattern == c2.glob_pattern;
}

bool operator==(const logwatch_textfile &t1, const logwatch_textfile &t2) {
    return t1.name == t2.name && t1.paths == t2.paths &&
           t1.file_id == t2.file_id && t1.file_size == t2.file_size &&
           t1.offset == t2.offset && t1.missing == t2.missing &&
           t1.nocontext == t2.nocontext && t1.rotated == t2.rotated &&
           t1.encoding == t2.encoding && t1.patterns.get() == t2.patterns.get();
}

bool operator==(const glob_token &t1, const glob_token &t2) {
    return t1.pattern == t2.pattern && t1.nocontext == t2.nocontext &&
           t1.from_start == t2.from_start && t1.rotated == t2.rotated &&
           t1.found_match == t2.found_match;
}

bool operator==(const globline_container &g1, const globline_container &g2) {
    return g1.tokens == g2.tokens && g1.patterns == g2.patterns;
}

TEST_F(wa_SectionLogwatchTest, parseLogwatchStateLine_valid) {
    char line[] = "M:\\log1.log|98374598374|0|16";
    const logwatch_textfile expected{"M:\\log1.log",
                                     std::vector<std::string>{"M:\\log1.log"},
                                     98374598374,
                                     0,
                                     16,
                                     false,
                                     false,
                                     condition_patterns_t()};
    ASSERT_EQ(expected, parseLogwatchStateLine(line));
}

TEST_F(wa_SectionLogwatchTest, parseLogwatchStateLine_missing_offset) {
    char line[] = "M:\\log1.log|98374598374|0|";
    ASSERT_THROW(parseLogwatchStateLine(line), StateParseError);
}

TEST_F(wa_SectionLogwatchTest, parseLogwatchStateLine_missing_file_size) {
    char line[] = "M:\\log1.log|98374598374|";
    ASSERT_THROW(parseLogwatchStateLine(line), StateParseError);
}

TEST_F(wa_SectionLogwatchTest, parseLogwatchStateLine_missing_file_id) {
    char line[] = "M:\\log1.log|";
    ASSERT_THROW(parseLogwatchStateLine(line), StateParseError);
}

TEST_F(wa_SectionLogwatchTest, parseLogwatchStateLine_missing_path) {
    char line[] = "|98374598374|0|16";
    ASSERT_THROW(parseLogwatchStateLine(line), StateParseError);
}

TEST_F(wa_SectionLogwatchTest, parseLogwatchStateLine_invalid_separator) {
    char line[] = "M:\\log1.log§98374598374§0§16";
    ASSERT_THROW(parseLogwatchStateLine(line), StateParseError);
}

TEST_F(wa_SectionLogwatchTest, parseLogwatchStateLine_negative) {
    char line[] = "M:\\log1.log|-1|-1|-1";
    const auto maxValue = std::numeric_limits<unsigned long long>::max();
    const logwatch_textfile expected{
        "M:\\log1.log", std::vector<std::string>{"M:\\log1.log"},
        maxValue,       maxValue,
        maxValue,       false,
        false,          condition_patterns_t()};
    ASSERT_EQ(expected, parseLogwatchStateLine(line));
}

TEST_F(wa_SectionLogwatchTest, parseLogwatchStateLine_conversion_error) {
    char line[] = "M:\\log1.log|foo|bar|baz";
    ASSERT_THROW(parseLogwatchStateLine(line), StateParseError);
}

TEST_F(wa_SectionLogwatchTest, from_string) {
    StrictMock<MockWinApi> mockwinapi;
    const std::string line =
        "from_start nocontext rotated C:\\foo\\bar"
        "| rotated D:\\baz\\qux*"
        "|nocontext from_start rotated E:\\quux\\corge*"
        "|  F:\\grault\\garply";
    const globline_container expected{
        {{"C:\\foo\\bar", true, true, true, false},
         {"D:\\baz\\qux*", false, false, true, false},
         {"E:\\quux\\corge*", true, true, true, false},
         {"F:\\grault\\garply", false, false, false, false}},
        {}};
    ASSERT_EQ(expected, from_string<globline_container>(mockwinapi, line));
}
