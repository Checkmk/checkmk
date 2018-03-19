#include "SectionEventlog.h"
#include "gmock/gmock.h"
#include "gtest/gtest.h"
#include "types.h"

using std::string;
using std::vector;
using std::wstring;

TEST(wa_stringutilTest, tokenize_Eventlog_Application_state_valid) {
    const string input{"Application|19881"};
    const vector<string> expected{"Application", "19881"};
    ASSERT_EQ(expected, tokenize(input, "\\|"));
}

TEST(wa_stringutilTest, tokenize_wstring_Eventlog_Application_state_valid) {
    const wstring input{L"Application|19881"};
    const vector<wstring> expected{L"Application", L"19881"};
    ASSERT_EQ(expected, tokenize(input, L"\\|"));
}

TEST(wa_stringutilTest, tokenize_Eventlog_Application_state_missing_value) {
    const string input{"Application|"};
    const vector<string> expected{"Application"};
    ASSERT_EQ(expected, tokenize(input, {"\\|"}));
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

// Note intentional mixture of tabs and spaces.
TEST(wa_stringutilTest, tokenize_whitespace_separator) {
    const string input{"This is   an	example sentence."};
    const vector<string> expected{"This", "is", "an", "example", "sentence."};
    ASSERT_EQ(expected, tokenize(input, "\\s+"));
}

// Note intentional mixture of tabs and spaces.
TEST(wa_stringutilTest, tokenizePossiblyQuoted_no_quoted) {
    const string input{"This is   an	example sentence."};
    const vector<string> expected{"This", "is", "an", "example", "sentence."};
    ASSERT_EQ(expected, tokenizePossiblyQuoted(input));
}

// Note intentional mixture of tabs and spaces.
TEST(wa_stringutilTest, tokenizePossiblyQuoted_double_quoted) {
    const string input{"\"This	is 	 an\" \"example sentence.\""};
    const vector<string> expected{"\"This	is 	 an\"",
                                  "\"example sentence.\""};
    ASSERT_EQ(expected, tokenizePossiblyQuoted(input));
}

// Note intentional mixture of tabs and spaces.
TEST(wa_stringutilTest, tokenizePossiblyQuoted_single_quoted) {
    const string input{"'This	is 	 an' 'example sentence.'"};
    const vector<string> expected{"'This	is 	 an'",
                                  "'example sentence.'"};
    ASSERT_EQ(expected, tokenizePossiblyQuoted(input));
}

// Note intentional mixture of tabs and spaces.
TEST(wa_stringutilTest, tokenizePossiblyQuoted_mixed_double_single_non_quoted) {
    const string input{"This	'is 	 an' \"example sentence.\""};
    const vector<string> expected{"This", "'is 	 an'", "\"example sentence.\""};
    ASSERT_EQ(expected, tokenizePossiblyQuoted(input));
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

TEST(wa_stringutilTest, ci_equal__equal_cases_equal) {
    const std::string s1{"asdfgh"};
    const std::string s2{s1};
    ASSERT_TRUE(ci_equal(s1, s2)) << "Expected " << s1 << " == " << s2;
}

TEST(wa_stringutilTest, ci_equal__equal_cases_unequal) {
    const std::string s1{"asdfgh§$"};
    const std::string s2{"aSdFgH§$"};
    ASSERT_TRUE(ci_equal(s1, s2)) << "Expected " << s1 << " == " << s2;
}

TEST(wa_stringutilTest, ci_equal__unequal_first_shorter) {
    const std::string s1{"asdfgh"};
    const std::string s2{"aSdFgH§$"};
    ASSERT_FALSE(ci_equal(s1, s2)) << "Expected " << s1 << " != " << s2;
}

TEST(wa_stringutilTest, ci_equal__unequal_first_longer) {
    const std::string s1{"asdfgh§$"};
    const std::string s2{"aSdFgH"};
    ASSERT_FALSE(ci_equal(s1, s2)) << "Expected " << s1 << " != " << s2;
}

TEST(wa_stringutilTest, ci_equal__unequal) {
    const std::string s1{"asdfg$"};
    const std::string s2{"aSdFgH"};
    ASSERT_FALSE(ci_equal(s1, s2)) << "Expected " << s1 << " != " << s2;
}

TEST(wa_stringutilTest, ci_compare__equal) {
    const std::string s1{"asdfgh"};
    const std::string s2{"aSdFgH"};
    ASSERT_FALSE(ci_compare(s1, s2)) << "Expected " << s1 << " == " << s2;
}

TEST(wa_stringutilTest, ci_compare__true) {
    const std::string s1{"asdfgg"};
    const std::string s2{"aSdFgH"};
    ASSERT_TRUE(ci_compare(s1, s2)) << "Expected " << s1 << " < " << s2;
}

TEST(wa_stringutilTest, ci_compare__false) {
    const std::string s1{"asdfgH"};
    const std::string s2{"aSdFgg"};
    ASSERT_FALSE(ci_compare(s1, s2)) << "Expected " << s1 << " > " << s2;
}

TEST(wa_stringutilTest, ci_compare__first_shorter) {
    const std::string s1{"asdfg"};
    const std::string s2{"aSdFgg"};
    ASSERT_TRUE(ci_compare(s1, s2)) << "Expected " << s1 << " < " << s2;
}

TEST(wa_stringutilTest, ci_compare__second_shorter) {
    const std::string s1{"aSdfgh"};
    const std::string s2{"asdFg"};
    ASSERT_FALSE(ci_compare(s1, s2)) << "Expected " << s1 << " > " << s2;
}

// Tests for char version of globmatch:

TEST(wa_stringutilTest, globmatch_exact_word) {
    ASSERT_TRUE(globmatch(std::string{"hello"}, std::string{"hello"}));
}

TEST(wa_stringutilTest, globmatch_string_longer) {
    ASSERT_FALSE(globmatch(std::string{"hello"}, std::string{"hello!"}));
}

TEST(wa_stringutilTest, globmatch_different_words) {
    ASSERT_FALSE(globmatch(std::string{"hello"}, std::string{"hi"}));
}

TEST(wa_stringutilTest, globmatch_question_mark_begin) {
    ASSERT_TRUE(globmatch(std::string{"?ello"}, std::string{"hello"}));
}

TEST(wa_stringutilTest, globmatch_question_mark_middle) {
    ASSERT_TRUE(globmatch(std::string{"he?lo"}, std::string{"hello"}));
}

TEST(wa_stringutilTest, globmatch_question_mark_end) {
    ASSERT_TRUE(globmatch(std::string{"hell?"}, std::string{"hello"}));
}

TEST(wa_stringutilTest, globmatch_several_question_marks_begin) {
    ASSERT_TRUE(globmatch(std::string{"??llo"}, std::string{"hello"}));
}

TEST(wa_stringutilTest, globmatch_several_question_marks_middle_1) {
    ASSERT_TRUE(globmatch(std::string{"he??o"}, std::string{"hello"}));
}

TEST(wa_stringutilTest, globmatch_several_question_marks_middle_2) {
    ASSERT_TRUE(globmatch(std::string{"h?l?o"}, std::string{"hello"}));
}

TEST(wa_stringutilTest, globmatch_several_question_marks_end) {
    ASSERT_TRUE(globmatch(std::string{"hell?"}, std::string{"hello"}));
}

TEST(wa_stringutilTest, globmatch_asterisk_middle) {
    ASSERT_TRUE(globmatch(std::string{"h*o"}, std::string{"hello"}));
}

TEST(wa_stringutilTest, globmatch_several_asterisks_middle) {
    ASSERT_TRUE(globmatch(std::string{"h******o"}, std::string{"hello"}));
}

TEST(wa_stringutilTest, globmatch_several_asterisks_question_mark_middle) {
    ASSERT_TRUE(globmatch(std::string{"h***?***o"}, std::string{"hello"}));
}

TEST(wa_stringutilTest, globmatch_asterisk_begin) {
    ASSERT_TRUE(globmatch(std::string{"*o"}, std::string{"hello"}));
}

TEST(wa_stringutilTest, globmatch_asterisk_end) {
    ASSERT_TRUE(globmatch(std::string{"h*"}, std::string{"hello"}));
}

TEST(wa_stringutilTest, globmatch_empty_pattern) {
    ASSERT_FALSE(globmatch(std::string{""}, std::string{"hello"}));
}

TEST(wa_stringutilTest, globmatch_both_empty) {
    ASSERT_TRUE(globmatch(std::string{""}, std::string{""}));
}

TEST(wa_stringutilTest, globmatch_asterisk_pattern_empty_string) {
    ASSERT_TRUE(globmatch(std::string{"*"}, std::string{""}));
}

TEST(wa_stringutilTest, globmatch_match_all) {
    ASSERT_TRUE(globmatch(std::string{"*"}, std::string{"hello"}));
}

TEST(wa_stringutilTest, globmatch_match_single_char_string) {
    ASSERT_FALSE(globmatch(std::string{"?"}, std::string{""}));
}

TEST(wa_stringutilTest, globmatch_exact_word_case_diff) {
    ASSERT_TRUE(globmatch(std::string{"hello"}, std::string{"HELLO"}));
}

TEST(wa_stringutilTest, globmatch_asterisk_question_mark_case_diff) {
    ASSERT_TRUE(globmatch(std::string{"h*L?"}, std::string{"hello"}));
}

TEST(wa_stringutilTest, globmatch_Windows_path) {
    ASSERT_TRUE(globmatch(std::string{"d:\\log\\sample_*.txt"},
                          std::string{"D:\\log\\sample_file.txt"}));
}

TEST(wa_stringutilTest, globmatch_Windows_path_with_space) {
    ASSERT_TRUE(globmatch(std::string{"d:\\logs and stuff\\sample_*.txt"},
                          std::string{"D:\\Logs and Stuff\\sample_file.txt"}));
}

TEST(wa_stringutilTest, globmatch_special_characters) {
    ASSERT_TRUE(
        globmatch(std::string{"$()+.[]^{|}"}, std::string{"$()+.[]^{|}"}));
}

// Tests for wchar_t version of globmatch:

TEST(wa_stringutilTest, globmatch_exact_word_wchar_t) {
    ASSERT_TRUE(globmatch(std::wstring{L"hello"}, std::wstring{L"hello"}));
}

TEST(wa_stringutilTest, globmatch_string_longer_wchar_t) {
    ASSERT_FALSE(globmatch(std::wstring{L"hello"}, std::wstring{L"hello!"}));
}

TEST(wa_stringutilTest, globmatch_different_words_wchar_t) {
    ASSERT_FALSE(globmatch(std::wstring{L"hello"}, std::wstring{L"hi"}));
}

TEST(wa_stringutilTest, globmatch_question_mark_begin_wchar_t) {
    ASSERT_TRUE(globmatch(std::wstring{L"?ello"}, std::wstring{L"hello"}));
}

TEST(wa_stringutilTest, globmatch_question_mark_middle_wchar_t) {
    ASSERT_TRUE(globmatch(std::wstring{L"he?lo"}, std::wstring{L"hello"}));
}

TEST(wa_stringutilTest, globmatch_question_mark_end_wchar_t) {
    ASSERT_TRUE(globmatch(std::wstring{L"hell?"}, std::wstring{L"hello"}));
}

TEST(wa_stringutilTest, globmatch_several_question_marks_begin_wchar_t) {
    ASSERT_TRUE(globmatch(std::wstring{L"??llo"}, std::wstring{L"hello"}));
}

TEST(wa_stringutilTest, globmatch_several_question_marks_middle_1_wchar_t) {
    ASSERT_TRUE(globmatch(std::wstring{L"he??o"}, std::wstring{L"hello"}));
}

TEST(wa_stringutilTest, globmatch_several_question_marks_middle_2_wchar_t) {
    ASSERT_TRUE(globmatch(std::wstring{L"h?l?o"}, std::wstring{L"hello"}));
}

TEST(wa_stringutilTest, globmatch_several_question_marks_end_wchar_t) {
    ASSERT_TRUE(globmatch(std::wstring{L"hell?"}, std::wstring{L"hello"}));
}

TEST(wa_stringutilTest, globmatch_asterisk_middle_wchar_t) {
    ASSERT_TRUE(globmatch(std::wstring{L"h*o"}, std::wstring{L"hello"}));
}

TEST(wa_stringutilTest, globmatch_several_asterisks_middle_wchar_t) {
    ASSERT_TRUE(globmatch(std::wstring{L"h******o"}, std::wstring{L"hello"}));
}

TEST(wa_stringutilTest,
     globmatch_several_asterisks_question_mark_middle_wchar_t) {
    ASSERT_TRUE(globmatch(std::wstring{L"h***?***o"}, std::wstring{L"hello"}));
}

TEST(wa_stringutilTest, globmatch_asterisk_begin_wchar_t) {
    ASSERT_TRUE(globmatch(std::wstring{L"*o"}, std::wstring{L"hello"}));
}

TEST(wa_stringutilTest, globmatch_asterisk_end_wchar_t) {
    ASSERT_TRUE(globmatch(std::wstring{L"h*"}, std::wstring{L"hello"}));
}

TEST(wa_stringutilTest, globmatch_empty_pattern_wchar_t) {
    ASSERT_FALSE(globmatch(std::wstring{L""}, std::wstring{L"hello"}));
}

TEST(wa_stringutilTest, globmatch_both_empty_wchar_t) {
    ASSERT_TRUE(globmatch(std::wstring{L""}, std::wstring{L""}));
}

TEST(wa_stringutilTest, globmatch_asterisk_pattern_empty_string_wchar_t) {
    ASSERT_TRUE(globmatch(std::wstring{L"*"}, std::wstring{L""}));
}

TEST(wa_stringutilTest, globmatch_match_all_wchar_t) {
    ASSERT_TRUE(globmatch(std::wstring{L"*"}, std::wstring{L"hello"}));
}

TEST(wa_stringutilTest, globmatch_match_single_char_string_wchar_t) {
    ASSERT_FALSE(globmatch(std::wstring{L"?"}, std::wstring{L""}));
}

TEST(wa_stringutilTest, globmatch_exact_word_case_diff_wchar_t) {
    ASSERT_TRUE(globmatch(std::wstring{L"hello"}, std::wstring{L"HELLO"}));
}

TEST(wa_stringutilTest, globmatch_asterisk_question_mark_case_diff_wchar_t) {
    ASSERT_TRUE(globmatch(std::wstring{L"h*L?"}, std::wstring{L"hello"}));
}

TEST(wa_stringutilTest, globmatch_Windows_path_wchar_t) {
    ASSERT_TRUE(globmatch(std::wstring{L"d:\\log\\sample_*.txt"},
                          std::wstring{L"D:\\log\\sample_file.txt"}));
}

TEST(wa_stringutilTest, globmatch_Windows_path_with_space_wchar_t) {
    ASSERT_TRUE(
        globmatch(std::wstring{L"d:\\logs and stuff\\sample_*.txt"},
                  std::wstring{L"D:\\Logs and Stuff\\sample_file.txt"}));
}

TEST(wa_stringutilTest, globmatch_special_characters_wchar_t) {
    ASSERT_TRUE(
        globmatch(std::wstring{L"$()+.[]^{|}"}, std::wstring{L"$()+.[]^{|}"}));
}

TEST(wa_stringutilTest, extractIPAddress_IPv4_with_port) {
    const std::string input{"10.1.2.3:456"};
    const std::string expected{"10.1.2.3"};
    ASSERT_EQ(expected, extractIPAddress(input));
}

TEST(wa_stringutilTest, extractIPAddress_IPv4_without_port) {
    const std::string input{"10.1.2.3"};
    const std::string expected{"10.1.2.3"};
    ASSERT_EQ(expected, extractIPAddress(input));
}

TEST(wa_stringutilTest, extractIPAddress_IPv6mapped_with_port_1) {
    const std::string input{"[::10.1.2.3]:456"};
    const std::string expected{"10.1.2.3"};
    ASSERT_EQ(expected, extractIPAddress(input));
}

TEST(wa_stringutilTest, extractIPAddress_IPv6mapped_without_port_1) {
    const std::string input{"::10.1.2.3"};
    const std::string expected{"10.1.2.3"};
    ASSERT_EQ(expected, extractIPAddress(input));
}

TEST(wa_stringutilTest, extractIPAddress_IPv6mapped_with_port_2) {
    const std::string input{"[::ffff:10.1.2.3]:456"};
    const std::string expected{"10.1.2.3"};
    ASSERT_EQ(expected, extractIPAddress(input));
}

TEST(wa_stringutilTest, extractIPAddress_IPv6mapped_without_port_2) {
    const std::string input{"::ffff:10.1.2.3"};
    const std::string expected{"10.1.2.3"};
    ASSERT_EQ(expected, extractIPAddress(input));
}

TEST(wa_stringutilTest, extractIPAddress_IPv6mapped_with_port_3) {
    const std::string input{"[::ffff:0:10.1.2.3]:456"};
    const std::string expected{"10.1.2.3"};
    ASSERT_EQ(expected, extractIPAddress(input));
}

TEST(wa_stringutilTest, extractIPAddress_IPv6mapped_without_port_3) {
    const std::string input{"::ffff:0:10.1.2.3"};
    const std::string expected{"10.1.2.3"};
    ASSERT_EQ(expected, extractIPAddress(input));
}

TEST(wa_stringutilTest, extractIPAddress_IPv6_all_segments_with_port) {
    const std::string input{"[ab:cd:ef:12:34:56:78:90]:12"};
    const std::string expected{"ab:cd:ef:12:34:56:78:90"};
    ASSERT_EQ(expected, extractIPAddress(input));
}

TEST(wa_stringutilTest, extractIPAddress_IPv6_all_segments_without_port) {
    const std::string input{"ab:cd:ef:12:34:56:78:90"};
    const std::string expected{"ab:cd:ef:12:34:56:78:90"};
    ASSERT_EQ(expected, extractIPAddress(input));
}

TEST(wa_stringutilTest, extractIPAddress_IPv6_7_segments_with_port_1) {
    const std::string input{"[ab:cd:ef:12:34:56:78::]:12"};
    const std::string expected{"ab:cd:ef:12:34:56:78::"};
    ASSERT_EQ(expected, extractIPAddress(input));
}

TEST(wa_stringutilTest, extractIPAddress_IPv6_7_segments_without_port_1) {
    const std::string input{"ab:cd:ef:12:34:56:78::"};
    const std::string expected{"ab:cd:ef:12:34:56:78::"};
    ASSERT_EQ(expected, extractIPAddress(input));
}

TEST(wa_stringutilTest, extractIPAddress_IPv6_7_segments_with_port_2) {
    const std::string input{"[ab:cd:ef:12:34:56::78]:12"};
    const std::string expected{"ab:cd:ef:12:34:56::78"};
    ASSERT_EQ(expected, extractIPAddress(input));
}

TEST(wa_stringutilTest, extractIPAddress_IPv6_7_segments_without_port_2) {
    const std::string input{"ab:cd:ef:12:34:56::78"};
    const std::string expected{"ab:cd:ef:12:34:56::78"};
    ASSERT_EQ(expected, extractIPAddress(input));
}

TEST(wa_stringutilTest, extractIPAddress_IPv6_7_segments_with_port_3) {
    const std::string input{"[ab::ef:12:34:56:78:90]:12"};
    const std::string expected{"ab::ef:12:34:56:78:90"};
    ASSERT_EQ(expected, extractIPAddress(input));
}

TEST(wa_stringutilTest, extractIPAddress_IPv6_7_segments_without_port_3) {
    const std::string input{"ab::ef:12:34:56:78:90"};
    const std::string expected{"ab::ef:12:34:56:78:90"};
    ASSERT_EQ(expected, extractIPAddress(input));
}

TEST(wa_stringutilTest, extractIPAddress_IPv6_3_segments_with_port) {
    const std::string input{"[ab:cd::90]:12"};
    const std::string expected{"ab:cd::90"};
    ASSERT_EQ(expected, extractIPAddress(input));
}

TEST(wa_stringutilTest, extractIPAddress_IPv6_3_segments_without_port) {
    const std::string input{"ab:cd::90"};
    const std::string expected{"ab:cd::90"};
    ASSERT_EQ(expected, extractIPAddress(input));
}

TEST(wa_stringutilTest, extractIPAddress_IPv6_one_segment_start_with_port) {
    const std::string input{"[ab::]:12"};
    const std::string expected{"ab::"};
    ASSERT_EQ(expected, extractIPAddress(input));
}

TEST(wa_stringutilTest, extractIPAddress_IPv6_one_segment_start_without_port) {
    const std::string input{"ab::"};
    const std::string expected{"ab::"};
    ASSERT_EQ(expected, extractIPAddress(input));
}

TEST(wa_stringutilTest, extractIPAddress_IPv6_one_segment_end_with_port) {
    const std::string input{"[::90]:12"};
    const std::string expected{"::90"};
    ASSERT_EQ(expected, extractIPAddress(input));
}

TEST(wa_stringutilTest, extractIPAddress_IPv6_one_segment_end_without_port) {
    const std::string input{"::90"};
    const std::string expected{"::90"};
    ASSERT_EQ(expected, extractIPAddress(input));
}

TEST(wa_stringutilTest, extractIPAddress_IPv6_no_segments_with_port) {
    const std::string input{"[::]:12"};
    const std::string expected{"::"};
    ASSERT_EQ(expected, extractIPAddress(input));
}

TEST(wa_stringutilTest, extractIPAddress_IPv6_no_segments_without_port) {
    const std::string input{"::"};
    const std::string expected{"::"};
    ASSERT_EQ(expected, extractIPAddress(input));
}

TEST(wa_stringutilTest, extractIPAddress_IPv6embedded_4_segments_with_port) {
    const std::string input{"[ab:cd:ef:12::10.1.2.3]:456"};
    const std::string expected{"ab:cd:ef:12::10.1.2.3"};
    ASSERT_EQ(expected, extractIPAddress(input));
}

TEST(wa_stringutilTest, extractIPAddress_IPv6embedded_4_segments_without_port) {
    const std::string input{"ab:cd:ef:12::10.1.2.3"};
    const std::string expected{"ab:cd:ef:12::10.1.2.3"};
    ASSERT_EQ(expected, extractIPAddress(input));
}

TEST(wa_stringutilTest, extractIPAddress_IPv6embedded_3_segments_with_port) {
    const std::string input{"[ab:cd:ef::10.1.2.3]:456"};
    const std::string expected{"ab:cd:ef::10.1.2.3"};
    ASSERT_EQ(expected, extractIPAddress(input));
}

TEST(wa_stringutilTest, extractIPAddress_IPv6embedded_3_segments_without_port) {
    const std::string input{"ab:cd:ef::10.1.2.3"};
    const std::string expected{"ab:cd:ef::10.1.2.3"};
    ASSERT_EQ(expected, extractIPAddress(input));
}

TEST(wa_stringutilTest, extractIPAddress_IPv6embedded_2_segments_with_port) {
    const std::string input{"[ab:cd::10.1.2.3]:456"};
    const std::string expected{"ab:cd::10.1.2.3"};
    ASSERT_EQ(expected, extractIPAddress(input));
}

TEST(wa_stringutilTest, extractIPAddress_IPv6embedded_2_segments_without_port) {
    const std::string input{"ab:cd::10.1.2.3"};
    const std::string expected{"ab:cd::10.1.2.3"};
    ASSERT_EQ(expected, extractIPAddress(input));
}

TEST(wa_stringutilTest, extractIPAddress_IPv6embedded_1_segment_with_port) {
    const std::string input{"[ab::10.1.2.3]:456"};
    const std::string expected{"ab::10.1.2.3"};
    ASSERT_EQ(expected, extractIPAddress(input));
}

TEST(wa_stringutilTest, extractIPAddress_IPv6embedded_1_segment_without_port) {
    const std::string input{"ab::10.1.2.3"};
    const std::string expected{"ab::10.1.2.3"};
    ASSERT_EQ(expected, extractIPAddress(input));
}
