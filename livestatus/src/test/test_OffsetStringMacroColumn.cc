#include <algorithm>
#include <cstddef>
#include <iterator>
#include <string>
#include "Column.h"
#include "OffsetStringHostMacroColumn.h"
#include "OffsetStringServiceMacroColumn.h"
#include "Row.h"
#include "Store.h"
#include "gtest/gtest.h"
#include "nagios.h"

// TODO(sp) Move this to a better place.
TEST(Store, dont_use_mc) {
    // Make sure that the MonitoringCore abstraction is not accessed during the
    // construction of Store. This is a bit fragile, but it is needed to tie the
    // knot between NagiosCore and Store.
    Store store{nullptr};
}

extern char *macro_user[MAX_USER_MACROS];

namespace {
// First test fixture: A single host
class OffsetStringHostMacroColumnTest : public ::testing::Test {
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
        host_.custom_variables = &hcvm2_;
        host_.plugin_output = cc("the plugin output");
        host_.long_plugin_output = cc("the long plugin output");
        host_.perf_data = cc("the perf data");
    }

    // Nagios and const-correctness: A Tale of Two Worlds...
    static char *cc(const char *str) { return const_cast<char *>(str); }

    void set_host_notes(const char *notes) { host_.notes = cc(notes); }

    std::string expanded_host_notes() const {
        return oshmc_.getValue(host_row_);
    }

    // Backwards the list you must build, my young padawan...
    customvariablesmember hcvm1_{.variable_name = cc("ERNIE"),
                                 .variable_value = cc("Bert"),
                                 .has_been_modified = 0,
                                 .next = nullptr};
    customvariablesmember hcvm2_{.variable_name = cc("HARRY"),
                                 .variable_value = cc("Hirsch"),
                                 .has_been_modified = 0,
                                 .next = &hcvm1_};
    host host_{};
    Row host_row_{&host_};
    OffsetStringHostMacroColumn oshmc_{
        "funny_column_name",  "Cool description!", -1, -1, -1, nullptr,
        offsetof(host, notes)};
};

// Second test fixture: A single host with a single service
class OffsetStringServiceMacroColumnTest
    : public OffsetStringHostMacroColumnTest {
protected:
    void SetUp() override {
        OffsetStringHostMacroColumnTest::SetUp();

        // g++'s -Wmissing-field-initializers warning incorrectly fires if we
        // use designated initializers for this. :-P
        service_.description = cc("muppet_show");
        service_.display_name = cc("The Muppet Show");
        service_.service_check_command = cc("check_fozzie_bear");
        service_.custom_variables = &scvm2_;
        service_.plugin_output = cc("plug");
        service_.long_plugin_output = cc("long plug");
        service_.perf_data = cc("99%");
        service_.host_ptr = &host_;
    }

    void set_service_notes(const char *notes) { service_.notes = cc(notes); }

    std::string expanded_service_notes() const {
        return ossmc_.getValue(service_row_);
    }

    customvariablesmember scvm1_{.variable_name = cc("STATLER"),
                                 .variable_value = cc("Boo!"),
                                 .has_been_modified = 0,
                                 .next = nullptr};
    customvariablesmember scvm2_{.variable_name = cc("WALDORF"),
                                 .variable_value = cc("Terrible!"),
                                 .has_been_modified = 0,
                                 .next = &scvm1_};
    service service_{};
    Row service_row_{&service_};
    OffsetStringServiceMacroColumn ossmc_{
        "navn", "Beskrivelse", -1, -1, -1, nullptr, offsetof(service, notes)};

private:
    // Nagios and const-correctness: A Tale of Two Worlds...
    static char *cc(const char *str) { return const_cast<char *>(str); }
};
}  // namespace

TEST_F(OffsetStringHostMacroColumnTest, misc) {
    EXPECT_EQ("funny_column_name", oshmc_.name());
    EXPECT_EQ("Cool description!", oshmc_.description());
    EXPECT_EQ(ColumnType::string, oshmc_.type());
    EXPECT_EQ(&host_, oshmc_.columnData<void>(host_row_));
}

TEST_F(OffsetStringHostMacroColumnTest, expand_host_builtin) {
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
}

TEST_F(OffsetStringHostMacroColumnTest, expand_host_custom) {
    set_host_notes("Hi, I'm $_HOSTERNIE$!");
    EXPECT_EQ("Hi, I'm Bert!", expanded_host_notes());

    set_host_notes("Hi, I'm $_HOSTKERMIT$!");
    EXPECT_EQ("Hi, I'm $_HOSTKERMIT$!", expanded_host_notes());
}

TEST_F(OffsetStringHostMacroColumnTest, expand_service_builtin) {
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
}

TEST_F(OffsetStringHostMacroColumnTest, expand_service_custom) {
    set_host_notes("checking $_SERVICESTATLER$...");
    EXPECT_EQ("checking $_SERVICESTATLER$...", expanded_host_notes());

    set_host_notes("checking $_SERVICEFOZZIE$...");
    EXPECT_EQ("checking $_SERVICEFOZZIE$...", expanded_host_notes());
}

TEST_F(OffsetStringHostMacroColumnTest, expand_user) {
    set_host_notes("checking $USER11$...");
    EXPECT_EQ("checking I drink and I know things...", expanded_host_notes());

    set_host_notes("checking $USER42$...");
    EXPECT_EQ("checking $USER42$...", expanded_host_notes());

    set_host_notes("checking $NONSENSE$...");
    EXPECT_EQ("checking $NONSENSE$...", expanded_host_notes());
}

TEST_F(OffsetStringHostMacroColumnTest, border_cases) {
    host_.name = nullptr;
    set_host_notes("checking $HOSTNAME$...");
    EXPECT_EQ("checking $HOSTNAME$...", expanded_host_notes());

    set_host_notes(nullptr);
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
    EXPECT_EQ("foo$bar", expanded_host_notes());

    set_host_notes("checking $USER0$...");
    EXPECT_EQ("checking $USER0$...", expanded_host_notes());

    set_host_notes("checking $USER1$...");
    EXPECT_EQ("checking $USER1$...", expanded_host_notes());

    set_host_notes("checking $USER256$...");
    EXPECT_EQ("checking $USER256$...", expanded_host_notes());

    set_host_notes("checking $USER257$...");
    EXPECT_EQ("checking $USER257$...", expanded_host_notes());
}

TEST_F(OffsetStringServiceMacroColumnTest, misc) {
    EXPECT_EQ("navn", ossmc_.name());
    EXPECT_EQ("Beskrivelse", ossmc_.description());
    EXPECT_EQ(ColumnType::string, ossmc_.type());
    EXPECT_EQ(&service_, ossmc_.columnData<void>(service_row_));
}

TEST_F(OffsetStringServiceMacroColumnTest, expand_host_builtin) {
    set_service_notes("checking $HOSTNAME$...");
    EXPECT_EQ("checking sesame_street...", expanded_service_notes());

    set_service_notes("checking $HOSTDISPLAYNAME$...");
    EXPECT_EQ("checking the display name...", expanded_service_notes());

    set_service_notes("checking $HOSTALIAS$...");
    EXPECT_EQ("checking the alias...", expanded_service_notes());

    set_service_notes("checking $HOSTADDRESS$...");
    EXPECT_EQ("checking the address...", expanded_service_notes());

    set_service_notes("checking $HOSTOUTPUT$...");
    EXPECT_EQ("checking the plugin output...", expanded_service_notes());

    set_service_notes("checking $LONGHOSTOUTPUT$...");
    EXPECT_EQ("checking the long plugin output...", expanded_service_notes());

    set_service_notes("checking $HOSTPERFDATA$...");
    EXPECT_EQ("checking the perf data...", expanded_service_notes());

    set_service_notes("checking $HOSTCHECKCOMMAND$...");
    EXPECT_EQ("checking the host check command...", expanded_service_notes());
}

TEST_F(OffsetStringServiceMacroColumnTest, expand_host_custom) {
    set_service_notes("Hi, I'm $_HOSTERNIE$!");
    EXPECT_EQ("Hi, I'm Bert!", expanded_service_notes());

    set_service_notes("Hi, I'm $_HOSTKERMIT$!");
    EXPECT_EQ("Hi, I'm $_HOSTKERMIT$!", expanded_service_notes());
}

TEST_F(OffsetStringServiceMacroColumnTest, expand_service_builtin) {
    set_service_notes("checking $SERVICEDESC$...");
    EXPECT_EQ("checking muppet_show...", expanded_service_notes());

    set_service_notes("checking $SERVICEDISPLAYNAME$...");
    EXPECT_EQ("checking The Muppet Show...", expanded_service_notes());

    set_service_notes("checking $SERVICEOUTPUT$...");
    EXPECT_EQ("checking plug...", expanded_service_notes());

    set_service_notes("checking $LONGSERVICEOUTPUT$...");
    EXPECT_EQ("checking long plug...", expanded_service_notes());

    set_service_notes("checking $SERVICEPERFDATA$...");
    EXPECT_EQ("checking 99%...", expanded_service_notes());

    set_service_notes("checking $SERVICECHECKCOMMAND$...");
    EXPECT_EQ("checking check_fozzie_bear...", expanded_service_notes());
}

TEST_F(OffsetStringServiceMacroColumnTest, expand_service_custom) {
    set_service_notes("checking $_SERVICESTATLER$...");
    EXPECT_EQ("checking Boo!...", expanded_service_notes());

    set_service_notes("checking $_SERVICEFOZZIE$...");
    EXPECT_EQ("checking $_SERVICEFOZZIE$...", expanded_service_notes());
}

TEST_F(OffsetStringServiceMacroColumnTest, expand_user) {
    set_service_notes("checking $USER11$...");
    EXPECT_EQ("checking I drink and I know things...",
              expanded_service_notes());

    set_service_notes("checking $USER42$...");
    EXPECT_EQ("checking $USER42$...", expanded_service_notes());

    set_service_notes("checking $NONSENSE$...");
    EXPECT_EQ("checking $NONSENSE$...", expanded_service_notes());
}

TEST_F(OffsetStringServiceMacroColumnTest, border_cases) {
    service_.description = nullptr;
    set_service_notes("checking $SERVICEDESC$...");
    EXPECT_EQ("checking $SERVICEDESC$...", expanded_service_notes());

    set_service_notes(nullptr);
    EXPECT_EQ("", expanded_service_notes());

    set_service_notes("");
    EXPECT_EQ("", expanded_service_notes());

    set_service_notes("checking $LONGSERVICEOUTPUT$$SERVICEPERFDATA$...");
    EXPECT_EQ("checking long plug99%...", expanded_service_notes());

    set_service_notes("$LONGSERVICEOUTPUT$$SERVICEPERFDATA$");
    EXPECT_EQ("long plug99%", expanded_service_notes());

    set_service_notes("$");
    EXPECT_EQ("$", expanded_service_notes());

    set_service_notes("foo$bar");
    EXPECT_EQ("foo$bar", expanded_service_notes());

    set_service_notes("checking $USER0$...");
    EXPECT_EQ("checking $USER0$...", expanded_service_notes());

    set_service_notes("checking $USER1$...");
    EXPECT_EQ("checking $USER1$...", expanded_service_notes());

    set_service_notes("checking $USER256$...");
    EXPECT_EQ("checking $USER256$...", expanded_service_notes());

    set_service_notes("checking $USER257$...");
    EXPECT_EQ("checking $USER257$...", expanded_service_notes());
}
