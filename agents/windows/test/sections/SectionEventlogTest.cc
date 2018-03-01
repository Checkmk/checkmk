#include "SectionEventlog.h"
#include "gmock/gmock.h"
#include "gtest/gtest.h"
#include "types.h"

using namespace ::testing;

namespace eventlog {

bool operator==(const state &s1, const state &s2) {
    return s1.name == s2.name && s1.record_no == s2.record_no &&
           s1.newly_discovered == s2.newly_discovered;
}

}  // namespace eventlog

/* Contents of an example eventstate.txt:
Application|19881
HardwareEvents|0
Internet Explorer|0
Key Management Service|0
Security|93338
System|29014
Windows PowerShell|240
*/

TEST(wa_SectionEventlogTest, parseStateLine_Application_valid) {
    char line[] = "Application|19881";
    const eventlog::state expected{"Application", 19881, false};
    ASSERT_EQ(expected, parseStateLine(line));
}

TEST(wa_SectionEventlogTest, parseStateLine_Application_missing_name) {
    char line[] = "|19881";
    ASSERT_THROW(parseStateLine(line), StateParseError);
}

TEST(wa_SectionEventlogTest, parseStateLine_Application_missing_value) {
    char line[] = "Application|";
    ASSERT_THROW(parseStateLine(line), StateParseError);
}

TEST(wa_SectionEventlogTest,
     parseStateLine_Application_missing_separator_and_value) {
    char line[] = "Application";
    ASSERT_THROW(parseStateLine(line), StateParseError);
}

TEST(wa_SectionEventlogTest, parseStateLine_Application_invalid_separator) {
    char line[] = "Application 19881";
    ASSERT_THROW(parseStateLine(line), StateParseError);
}

TEST(wa_SectionEventlogTest, parseStateLine_Internet_Explorer_zero_valid) {
    char line[] = "Internet Explorer|0";
    const eventlog::state expected{"Internet Explorer", 0, false};
    ASSERT_EQ(expected, parseStateLine(line));
}

TEST(wa_SectionEventlogTest, parseStateLine_Internet_Explorer_negative) {
    char line[] = "Internet Explorer|-1";
    const eventlog::state expected{
        "Internet Explorer", std::numeric_limits<unsigned long long>::max(),
        false};
    ASSERT_EQ(expected, parseStateLine(line));
}

TEST(wa_SectionEventlogTest,
     parseStateLine_Internet_Explorer_conversion_error) {
    char line[] = "Internet Explorer|garbage";
    ASSERT_THROW(parseStateLine(line), StateParseError);
}
