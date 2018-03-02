#include "MockEnvironment.h"
#include "MockLogger.h"
#include "MockWinApi.h"
#include "SectionEventlog.h"
#include "gmock/gmock.h"
#include "gtest/gtest.h"
#include "types.h"

using ::testing::NiceMock;
using ::testing::Return;
using ::testing::StrictMock;

namespace eventlog {

bool operator==(const state &s1, const state &s2) {
    return s1.name == s2.name && s1.record_no == s2.record_no &&
           s1.newly_discovered == s2.newly_discovered;
}

}  // namespace eventlog

class wa_SectionEventlogTest : public ::testing::Test {
public:
    wa_SectionEventlogTest() : _mockenv(&_mocklogger, _mockwinapi) {}
    virtual ~wa_SectionEventlogTest() = default;

protected:
    NiceMock<MockLogger> _mocklogger;
    NiceMock<MockWinApi> _mockwinapi;
    StrictMock<MockEnvironment> _mockenv;
};

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
    const eventlog::state expected{"Application", 19881, false};
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
    const eventlog::state expected{"Internet Explorer", 0, false};
    ASSERT_EQ(expected, parseStateLine(line));
}

TEST_F(wa_SectionEventlogTest, parseStateLine_Internet_Explorer_negative) {
    char line[] = "Internet Explorer|-1";
    const eventlog::state expected{
        "Internet Explorer", std::numeric_limits<unsigned long long>::max(),
        false};
    ASSERT_EQ(expected, parseStateLine(line));
}

TEST_F(wa_SectionEventlogTest,
       parseStateLine_Internet_Explorer_conversion_error) {
    char line[] = "Internet Explorer|garbage";
    ASSERT_THROW(parseStateLine(line), StateParseError);
}

TEST_F(wa_SectionEventlogTest, getIPSpecificStatefileName_no_remoteIP) {
    ASSERT_FALSE(getIPSpecificStatefileName(_mockenv, std::nullopt));
}

TEST_F(wa_SectionEventlogTest, getIPSpecificStatefileName_IPv4) {
    const auto testIP = std::make_optional(std::string{"127.0.0.1"});
    const std::string testPath = "C:\\foo\\bar\\baz.txt";
    EXPECT_CALL(_mockenv, eventlogStatefile()).WillOnce(Return(testPath));
    const auto expected =
        std::make_optional(std::string{"C:\\foo\\bar\\baz_127_0_0_1.txt"});
    const auto actual = getIPSpecificStatefileName(_mockenv, testIP);
    ASSERT_EQ(expected, actual)
        << "Expected: " << expected.value() << " [" << std::boolalpha
        << bool(expected) << "], actual: " << actual.value_or("[no value!]")
        << " [" << bool(actual) << "]";
}

TEST_F(wa_SectionEventlogTest, getIPSpecificStatefileName_IPv6) {
    const auto testIP =
        std::make_optional(std::string{"fe80::20ff:1410:91d0:90f9"});
    const std::string testPath = "C:\\foo\\bar\\baz.txt";
    EXPECT_CALL(_mockenv, eventlogStatefile()).WillOnce(Return(testPath));
    const auto expected = std::make_optional(
        std::string{"C:\\foo\\bar\\baz_fe80__20ff_1410_91d0_90f9.txt"});
    const auto actual = getIPSpecificStatefileName(_mockenv, testIP);
    ASSERT_EQ(expected, actual)
        << "Expected: " << expected.value() << " [" << std::boolalpha
        << bool(expected) << "], actual: " << actual.value_or("[no value!]")
        << " [" << bool(actual) << "]";
}
