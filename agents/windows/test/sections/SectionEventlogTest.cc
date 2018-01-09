#include "gmock/gmock.h"
#include "gtest/gtest.h"
#include "sections/SectionEventlog.h"
#include "types.h"

using namespace ::testing;

class wa_SectionEventlogTest : public Test {};

bool operator==(const eventlog_hint_t &h1, const eventlog_hint_t &h2) {
    return h1.name == h2.name && h1.record_no == h2.record_no;
}

/* Contents of an example eventstate.txt:
Application|19881
HardwareEvents|0
Internet Explorer|0
Key Management Service|0
Security|93338
System|29014
Windows PowerShell|240
*/

TEST_F(wa_SectionEventlogTest, parseStateLine_Application_valid) {
    char line[] = "Application|19881";
    const eventlog_hint_t expected{"Application", 19881};
    ASSERT_EQ(expected, parseStateLine(line));
}

TEST_F(wa_SectionEventlogTest, parseStateLine_Application_missing_name) {
    char line[] = "|19881";
    ASSERT_THROW(parseStateLine(line), StateParseError);
}

TEST_F(wa_SectionEventlogTest, parseStateLine_Application_missing_value) {
    char line[] = "Application|";
    ASSERT_THROW(parseStateLine(line), StateParseError);
}

TEST_F(wa_SectionEventlogTest,
       parseStateLine_Application_missing_separator_and_value) {
    char line[] = "Application";
    ASSERT_THROW(parseStateLine(line), StateParseError);
}

TEST_F(wa_SectionEventlogTest, parseStateLine_Application_invalid_separator) {
    char line[] = "Application 19881";
    ASSERT_THROW(parseStateLine(line), StateParseError);
}

TEST_F(wa_SectionEventlogTest, parseStateLine_Internet_Explorer_zero_valid) {
    char line[] = "Internet Explorer|0";
    const eventlog_hint_t expected{"Internet Explorer", 0};
    ASSERT_EQ(expected, parseStateLine(line));
}

TEST_F(wa_SectionEventlogTest, parseStateLine_Internet_Explorer_negative) {
    char line[] = "Internet Explorer|-1";
    const eventlog_hint_t expected{
        "Internet Explorer", std::numeric_limits<unsigned long long>::max()};
    ASSERT_EQ(expected, parseStateLine(line));
}

TEST_F(wa_SectionEventlogTest,
       parseStateLine_Internet_Explorer_conversion_error) {
    char line[] = "Internet Explorer|garbage";
    ASSERT_THROW(parseStateLine(line), StateParseError);
}
