#include "Environment.h"
#include "MockLogger.h"
#include "MockWinApi.h"
#include "SectionMRPE.h"
#include "gmock/gmock.h"
#include "gtest/gtest.h"

using namespace ::testing;

bool operator==(const mrpe_entry &e1, const mrpe_entry &e2) {
    return e1.run_as_user == e2.run_as_user &&
           e1.command_line == e2.command_line &&
           e1.plugin_name == e2.plugin_name &&
           e1.service_description == e2.service_description;
}

class wa_SectionMRPETest : public Test {
protected:
    NiceMock<MockLogger> _mocklogger;
    NiceMock<MockWinApi> _mockwinapi;
};

TEST_F(wa_SectionMRPETest, from_string__absolute_path_no_params_no_quotes) {
    const std::string input{"foo \\bar\\baz"};
    const mrpe_entry expected{"", "\\bar\\baz", "baz", "foo"};
    ASSERT_EQ(expected, from_string<mrpe_entry>(_mockwinapi, input));
}

TEST_F(wa_SectionMRPETest, from_string__absolute_path_no_params_quotes) {
    const std::string input{"foo \"\\bar\\baz\""};
    const mrpe_entry expected{"", "\"\\bar\\baz\"", "baz", "foo"};
    ASSERT_EQ(expected, from_string<mrpe_entry>(_mockwinapi, input));
}

TEST_F(wa_SectionMRPETest, from_string__absolute_path_params_no_quotes) {
    const std::string input{"foo \\bar\\baz qux quux"};
    const mrpe_entry expected{"", "\\bar\\baz qux quux", "baz", "foo"};
    ASSERT_EQ(expected, from_string<mrpe_entry>(_mockwinapi, input));
}

TEST_F(wa_SectionMRPETest, from_string__relative_path_params_no_quotes) {
    const std::string cwd{"C:\\corge"};
    EXPECT_CALL(_mockwinapi, GetCurrentDirectoryA(32767, _))
        .WillOnce(DoAll(SetArrayArgument<1>(cwd.cbegin(), cwd.cend()),
                        Return(cwd.size())));
    ::Environment testEnv{true, false, &_mocklogger, _mockwinapi};
    const std::string input{"foo bar\\baz qux quux"};
    const mrpe_entry expected{"", "C:\\corge\\bar\\baz qux quux", "baz", "foo"};
    ASSERT_EQ(expected, from_string<mrpe_entry>(_mockwinapi, input));
}

TEST_F(wa_SectionMRPETest,
       from_string__absolute_path__with_spaces_params_with_quotes) {
    const std::string input{
        "\"foo bar\" \"\\baz qux\\quux\" corge \"grault garply\""};
    const mrpe_entry expected{"", "\"\\baz qux\\quux\" corge \"grault garply\"",
                              "quux", "foo bar"};
    ASSERT_EQ(expected, from_string<mrpe_entry>(_mockwinapi, input));
}

TEST_F(wa_SectionMRPETest, from_string__relative_path_params_with_quotes) {
    const std::string cwd{"C:\\corge"};
    EXPECT_CALL(_mockwinapi, GetCurrentDirectoryA(32767, _))
        .WillOnce(DoAll(SetArrayArgument<1>(cwd.cbegin(), cwd.cend()),
                        Return(cwd.size())));
    ::Environment testEnv{true, false, &_mocklogger, _mockwinapi};
    const std::string input{"foo \"bar baz\\qux\" quux"};
    const mrpe_entry expected{"", "\"C:\\corge\\bar baz\\qux\" quux", "qux",
                              "foo"};
    ASSERT_EQ(expected, from_string<mrpe_entry>(_mockwinapi, input));
}
