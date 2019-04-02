#include <algorithm>
#include <cstddef>
#include <iterator>
#include <string>
#include "Column.h"
#include "OffsetStringHostMacroColumn.h"
#include "Row.h"
#include "gtest/gtest.h"
#include "nagios.h"

extern char *macro_user[MAX_USER_MACROS];

namespace {
class OffsetStringMacroColumnTest : public ::testing::Test {
protected:
    void SetUp() override {
        std::fill(std::begin(macro_user), std::end(macro_user), nullptr);
        macro_user[10] = cc("I drink and I know things");

        // g++'s -Wmissing-field-initializers warning incorrectly fires if we
        // use designated initializers for this. :-P
        host_.name = cc("sesame_street");
        host_.display_name = cc("the display name");
        host_.alias = cc("the alias");
        host_.address = cc("the address");
        host_.host_check_command = cc("the host check command");
        host_.custom_variables = &cvm2_;
        host_.plugin_output = cc("the plugin output");
        host_.long_plugin_output = cc("the long plugin output");
        host_.perf_data = cc("the perf data");
    }

    void set_host_notes(const char *notes) { host_.notes = cc(notes); }

    std::string expanded_host_notes() const { return oshmc_.getValue(row_); }

    // Backwards the list you must build, my young padawan...
    customvariablesmember cvm1_{.variable_name = cc("ERNIE"),
                                .variable_value = cc("Bert"),
                                .has_been_modified = 0,
                                .next = nullptr};
    customvariablesmember cvm2_{.variable_name = cc("HARRY"),
                                .variable_value = cc("Hirsch"),
                                .has_been_modified = 0,
                                .next = &cvm1_};
    host host_{};
    Row row_{&host_};
    OffsetStringHostMacroColumn oshmc_{
        "funny_column_name",  "Cool description!", -1, -1, -1, nullptr,
        offsetof(host, notes)};

private:
    // Nagios and const-correctness: A Tale of Two Worlds...
    static char *cc(const char *str) { return const_cast<char *>(str); }

};  // namespace

}  // namespace

TEST_F(OffsetStringMacroColumnTest, simple) {
    EXPECT_EQ("funny_column_name", oshmc_.name());
    EXPECT_EQ("Cool description!", oshmc_.description());
    EXPECT_EQ(ColumnType::string, oshmc_.type());
    EXPECT_EQ(&host_, oshmc_.columnData<void>(row_));
}

TEST_F(OffsetStringMacroColumnTest, getValue_basic) {
    set_host_notes("checking $HOSTNAME$...");
    EXPECT_EQ("checking sesame_street...", expanded_host_notes());

    set_host_notes("checking $HOSTDISPLAYNAME$...");
    EXPECT_EQ("checking the display name...", expanded_host_notes());

    set_host_notes("checking $HOSTALIAS$...");
    EXPECT_EQ("checking the alias...", expanded_host_notes());

    set_host_notes("checking $HOSTADDRESS$...");
    EXPECT_EQ("checking the address...", expanded_host_notes());

    set_host_notes("checking $HOSTOUTPUT$...");
    EXPECT_EQ("checking the plugin output...", expanded_host_notes());

    set_host_notes("checking $LONGHOSTOUTPUT$...");
    EXPECT_EQ("checking the long plugin output...", expanded_host_notes());

    set_host_notes("checking $HOSTPERFDATA$...");
    EXPECT_EQ("checking the perf data...", expanded_host_notes());

    set_host_notes("checking $HOSTCHECKCOMMAND$...");
    EXPECT_EQ("checking the host check command...", expanded_host_notes());

    set_host_notes("Hi, I'm $_HOSTERNIE$!");
    EXPECT_EQ("Hi, I'm Bert!", expanded_host_notes());

    set_host_notes("Hi, I'm $_HOSTKERMIT$!");
    EXPECT_EQ("Hi, I'm $_HOSTKERMIT$!", expanded_host_notes());

    set_host_notes("checking $SERVICEDESC$...");
    EXPECT_EQ("checking $SERVICEDESC$...", expanded_host_notes());

    set_host_notes("checking $SERVICEDISPLAYNAME$...");
    EXPECT_EQ("checking $SERVICEDISPLAYNAME$...", expanded_host_notes());

    set_host_notes("checking $SERVICEOUTPUT$...");
    EXPECT_EQ("checking $SERVICEOUTPUT$...", expanded_host_notes());

    set_host_notes("checking $LONGSERVICEOUTPUT$...");
    EXPECT_EQ("checking $LONGSERVICEOUTPUT$...", expanded_host_notes());

    set_host_notes("checking $SERVICEPERFDATA$...");
    EXPECT_EQ("checking $SERVICEPERFDATA$...", expanded_host_notes());

    set_host_notes("checking $SERVICECHECKCOMMAND$...");
    EXPECT_EQ("checking $SERVICECHECKCOMMAND$...", expanded_host_notes());

    set_host_notes("checking $_SERVICEERNIE$...");
    EXPECT_EQ("checking $_SERVICEERNIE$...", expanded_host_notes());

    set_host_notes("checking $_SERVICEKERMIT$...");
    EXPECT_EQ("checking $_SERVICEKERMIT$...", expanded_host_notes());

    set_host_notes("checking $USER11$...");
    EXPECT_EQ("checking I drink and I know things...", expanded_host_notes());

    set_host_notes("checking $USER42$...");
    EXPECT_EQ("checking $USER42$...", expanded_host_notes());

    set_host_notes("checking $NONSENSE$...");
    EXPECT_EQ("checking $NONSENSE$...", expanded_host_notes());
}

TEST_F(OffsetStringMacroColumnTest, getValue_border_cases) {
    host_.name = nullptr;
    set_host_notes("checking $HOSTNAME$...");
    EXPECT_EQ("checking $HOSTNAME$...", expanded_host_notes());

    host_.notes = nullptr;
    EXPECT_EQ("", expanded_host_notes());

    set_host_notes("");
    EXPECT_EQ("", expanded_host_notes());

    set_host_notes("checking $HOSTALIAS$$HOSTADDRESS$...");
    EXPECT_EQ("checking the aliasthe address...", expanded_host_notes());

    set_host_notes("$HOSTALIAS$$HOSTADDRESS$");
    EXPECT_EQ("the aliasthe address", expanded_host_notes());

    set_host_notes("$");
    EXPECT_EQ("$", expanded_host_notes());

    set_host_notes("foo$bar");
    EXPECT_EQ("foofoo$bar", expanded_host_notes());  // TODO(sp) WRONG!!!

    set_host_notes("checking $USER0$...");
    EXPECT_EQ("checking $USER0$...", expanded_host_notes());

    set_host_notes("checking $USER1$...");
    EXPECT_EQ("checking $USER1$...", expanded_host_notes());

    set_host_notes("checking $USER256$...");
    EXPECT_EQ("checking $USER256$...", expanded_host_notes());

    set_host_notes("checking $USER257$...");
    EXPECT_EQ("checking $USER257$...", expanded_host_notes());
}
