#include "gmock/gmock.h"
#include "gtest/gtest.h"
#include "sections/SectionEventlog.h"
#include "types.h"

using std::string;
using std::vector;
using std::wstring;

TEST(wa_stringutilTest, tokenize_Eventlog_Application_state_valid) {
    const string input{"Application|19881"};
    const vector<string> expected{"Application", "19881"};
    ASSERT_EQ(expected, tokenize(input, "\\|"));
}

TEST(wa_stringutilTest, tokenize_Eventlog_Application_state_missing_value) {
    const string input{"Application|"};
    const vector<string> expected{"Application"};
    ASSERT_EQ(expected, tokenize(input, "\\|"));
}

TEST(wa_stringutilTest,
     tokenize_Eventlog_Application_state_missing_separator_and_value) {
    const string input{"Application"};
    const vector<string> expected{"Application"};
    ASSERT_EQ(expected, tokenize(input, "\\|"));
}

TEST(wa_stringutilTest, tokenize_logfile_state_valid) {
    const string input{"M://log1.log|98374598374|0|16"};
    const vector<string> expected{"M://log1.log", "98374598374", "0", "16"};
    ASSERT_EQ(expected, tokenize(input, "\\|"));
}

TEST(wa_stringutilTest, tokenize_whitespace_separator) {
    const string input{"This is   an	example sentence."};
    const vector<string> expected{"This", "is", "an", "example", "sentence."};
    ASSERT_EQ(expected, tokenize(input, "\\s+"));
}

TEST(wa_stringutilTest, join_strings_space_separator) {
    const vector<string> input{"This", "is", "an", "example", "sentence."};
    const string expected{"This is an example sentence."};
    ASSERT_EQ(expected, join(input.cbegin(), input.cend(), " "));
}

TEST(wa_stringutilTest, join_strings_empty_separator) {
    const vector<string> input{"This", "is", "an", "example", "sentence."};
    const string expected{"Thisisanexamplesentence."};
    ASSERT_EQ(expected, join(input.cbegin(), input.cend(), ""));
}

TEST(wa_stringutilTest, join_wstrings_colon_separator) {
    const vector<wstring> input{L"This", L"is", L"an", L"example",
                                L"sentence."};
    const wstring expected{L"This:is:an:example:sentence."};
    ASSERT_EQ(expected, join(input.cbegin(), input.cend(), L":"));
}

TEST(wa_stringutilTest, join_ints_decimal_colon_separator) {
    const vector<int> input{1, 17, 273};
    const string expected{"1:17:273"};
    ASSERT_EQ(expected, join(input.cbegin(), input.cend(), ":"));
}

TEST(wa_stringutilTest, join_ints_hexadecimal_colon_separator) {
    const vector<int> input{1, 17, 273};
    const string expected{"1:11:111"};
    ASSERT_EQ(expected, join(input.cbegin(), input.cend(), ":", std::ios::hex));
}

TEST(wa_stringutilTest, isPathRelative_absolute_with_drive_letter_windows) {
    const std::string path{"C:\\foo\\bar"};
    ASSERT_FALSE(isPathRelative(path)) << path << " recognized as relative";
}

TEST(wa_stringutilTest, isPathRelative_absolute_without_drive_letter_windows) {
    const std::string path{"\\foo\\bar"};
    ASSERT_FALSE(isPathRelative(path)) << path << " recognized as relative";
}

TEST(wa_stringutilTest, isPathRelative_absolute_unc_windows) {
    const std::string path{"\\\\foo\\bar"};
    ASSERT_FALSE(isPathRelative(path)) << path << " recognized as relative";
}

TEST(wa_stringutilTest,
     isPathRelative_absolute_with_whitespace_quotes_windows) {
    const std::string path{"\"C:\\foo bar\\baz\""};
    ASSERT_FALSE(isPathRelative(path)) << path << " recognized as relative";
}

TEST(wa_stringutilTest,
     isPathRelative_absolute_unc_with_whitespace_quotes_windows) {
    const std::string path{"\"\\\\foo bar\\baz\""};
    ASSERT_FALSE(isPathRelative(path)) << path << " recognized as relative";
}

TEST(wa_stringutilTest, isPathRelative_relative_without_drive_letter_windows) {
    const std::string path{"foo\\bar"};
    ASSERT_TRUE(isPathRelative(path)) << path << " recognized as absolute";
}

TEST(wa_stringutilTest, isPathRelative_relative_with_drive_letter_windows) {
    const std::string path{"C:foo\\bar"};
    ASSERT_TRUE(isPathRelative(path)) << path << " recognized as absolute";
}

TEST(wa_stringutilTest,
     isPathRelative_relative_with_whitespace_quotes_windows) {
    const std::string path{"\"foo bar\\baz\""};
    ASSERT_TRUE(isPathRelative(path)) << path << " recognized as relative";
}

TEST(wa_stringutilTest, isPathRelative_absolute_with_drive_letter_unix) {
    const std::string path{"C:/foo/bar"};
    ASSERT_FALSE(isPathRelative(path)) << path << " recognized as relative";
}

TEST(wa_stringutilTest, isPathRelative_absolute_without_drive_letter_unix) {
    const std::string path{"/foo/bar"};
    ASSERT_FALSE(isPathRelative(path)) << path << " recognized as relative";
}

TEST(wa_stringutilTest, isPathRelative_absolute_unc_unix) {
    const std::string path{"//foo/bar"};
    ASSERT_FALSE(isPathRelative(path)) << path << " recognized as relative";
}

TEST(wa_stringutilTest, isPathRelative_absolute_with_whitespace_quotes_unix) {
    const std::string path{"\"C:/foo bar/baz\""};
    ASSERT_FALSE(isPathRelative(path)) << path << " recognized as relative";
}

TEST(wa_stringutilTest,
     isPathRelative_absolute_unc_with_whitespace_quotes_unix) {
    const std::string path{"\"//foo bar/baz\""};
    ASSERT_FALSE(isPathRelative(path)) << path << " recognized as relative";
}

TEST(wa_stringutilTest, isPathRelative_relative_without_drive_letter_unix) {
    const std::string path{"foo/bar"};
    ASSERT_TRUE(isPathRelative(path)) << path << " recognized as absolute";
}

TEST(wa_stringutilTest, isPathRelative_relative_with_drive_letter_unix) {
    const std::string path{"C:foo/bar"};
    ASSERT_TRUE(isPathRelative(path)) << path << " recognized as absolute";
}

TEST(wa_stringutilTest, isPathRelative_relative_with_whitespace_quotes_unix) {
    const std::string path{"\"foo bar/baz\""};
    ASSERT_TRUE(isPathRelative(path)) << path << " recognized as relative";
}
