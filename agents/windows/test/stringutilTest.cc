#include "gmock/gmock.h"
#include "gtest/gtest.h"
#include "sections/SectionEventlog.h"
#include "types.h"

using namespace ::testing;
using std::string;
using std::vector;

class wa_stringutilTest : public Test {};

TEST_F(wa_stringutilTest, tokenize_Eventlog_Application_state_valid) {
    const string input{"Application|19881"};
    const vector<string> expected{"Application", "19881"};
    ASSERT_EQ(expected, tokenize(input, "\\|"));
}

TEST_F(wa_stringutilTest, tokenize_Eventlog_Application_state_missing_value) {
    const string input{"Application|"};
    const vector<string> expected{"Application"};
    ASSERT_EQ(expected, tokenize(input, "\\|"));
}

TEST_F(wa_stringutilTest,
       tokenize_Eventlog_Application_state_missing_separator_and_value) {
    const string input{"Application"};
    const vector<string> expected{"Application"};
    ASSERT_EQ(expected, tokenize(input, "\\|"));
}

TEST_F(wa_stringutilTest, tokenize_logfile_state_valid) {
    const string input{"M://log1.log|98374598374|0|16"};
    const vector<string> expected{"M://log1.log", "98374598374", "0", "16"};
    ASSERT_EQ(expected, tokenize(input, "\\|"));
}

TEST_F(wa_stringutilTest, tokenize_whitespace_separator) {
    const string input{"This is   an	example sentence."};
    const vector<string> expected{"This", "is", "an", "example", "sentence."};
    ASSERT_EQ(expected, tokenize(input, "\\s+"));
}
