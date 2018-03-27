#include "MockLogger.h"
#include "SectionHeader.h"
#include "gmock/gmock.h"
#include "gtest/gtest.h"

using ::testing::NiceMock;

namespace {

struct FunnyBrackets {
    static constexpr auto left = "o§<|"; // a pedestrian
    static constexpr auto right = "C|:-="; // Charlie Chaplin
};

}  // namespace

class wa_SectionHeaderTest : public ::testing::Test {
public:
    virtual ~wa_SectionHeaderTest() = default;

protected:
    NiceMock<MockLogger> _mocklogger;
};

TEST_F(wa_SectionHeaderTest, DefaultHeader) {
    const std::string testName{"foobar"};
    DefaultHeader testHeader(testName, &_mocklogger);
    const std::string expected{"<<<foobar>>>\n"};
    std::ostringstream oss;
    oss << testHeader;
    ASSERT_EQ(expected, oss.str());
}

TEST_F(wa_SectionHeaderTest, SubSectionHeader) {
    const std::string testName{"foobar"};
    SubSectionHeader testHeader(testName, &_mocklogger);
    const std::string expected{"[foobar]\n"};
    std::ostringstream oss;
    oss << testHeader;
    ASSERT_EQ(expected, oss.str());
}

TEST_F(wa_SectionHeaderTest, HiddenHeader) {
    HiddenHeader testHeader(&_mocklogger);
    std::ostringstream oss;
    oss << testHeader;
    ASSERT_TRUE(oss.str().empty());
}

TEST_F(wa_SectionHeaderTest, SectionHeader_fwdSlashSeparator) {
    const std::string testName{"foobar"};
    SectionHeader<'/', SectionBrackets> testHeader(testName, &_mocklogger);
    const std::string expected{"<<<foobar:sep(47)>>>\n"};
    std::ostringstream oss;
    oss << testHeader;
    ASSERT_EQ(expected, oss.str());
}

TEST_F(wa_SectionHeaderTest, FunnyBrackets_tildeSeparator) {
    const std::string testName{"foobar"};
    SectionHeader<'~', FunnyBrackets> testHeader(testName, &_mocklogger);
    const std::string expected{"o§<|foobar:sep(126)C|:-=\n"};
    std::ostringstream oss;
    oss << testHeader;
    ASSERT_EQ(expected, oss.str());
}

