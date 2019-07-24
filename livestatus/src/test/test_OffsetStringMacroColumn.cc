#include <algorithm>
#include <cstddef>
#include <iterator>
#include <string>
#include "Column.h"
#include "NagiosCore.h"
#include "OffsetStringHostMacroColumn.h"
#include "OffsetStringServiceMacroColumn.h"
#include "Row.h"
#include "Store.h"
#include "data_encoding.h"
#include "gtest/gtest.h"
#include "nagios.h"
#include "test_utilities.h"

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
struct OffsetStringHostMacroColumnTest : public ::testing::Test {
    void SetUp() override {
        std::fill(std::begin(macro_user), std::end(macro_user), nullptr);
        macro_user[10] = cc("I drink and I know things");
    }

    void set_host_notes(const char *notes) { test_host.notes = cc(notes); }

    std::string expanded_host_notes() const {
        return oshmc.getValue(Row{&test_host});
    }

    TestHost test_host{{{"ERNIE", "Bert"},  //
                        {"HARRY", "Hirsch"},
                        {"_TAG_GUT", "Guten Tag!"}}};
    NagiosCore core{NagiosPaths{}, NagiosLimits{}, NagiosAuthorization{},
                    Encoding::utf8};
    OffsetStringHostMacroColumn oshmc{
        "funny_column_name",  "Cool description!", -1, -1, -1, &core,
        offsetof(host, notes)};
};  // namespace

// Second test fixture: A single host with a single service
struct OffsetStringServiceMacroColumnTest
    : public OffsetStringHostMacroColumnTest {
    void set_service_notes(const char *notes) {
        test_service.notes = cc(notes);
    }

    std::string expanded_service_notes() const {
        return ossmc.getValue(Row{&test_service});
    }

    TestService test_service{&test_host,
                             {{"STATLER", "Boo!"},
                              {"WALDORF", "Terrible!"},
                              {"_LABEL_LO", "Labello"}}};
    OffsetStringServiceMacroColumn ossmc{
        "navn", "Beskrivelse", -1, -1, -1, &core, offsetof(service, notes)};
};
}  // namespace

TEST_F(OffsetStringHostMacroColumnTest, misc) {
    EXPECT_EQ("funny_column_name", oshmc.name());
    EXPECT_EQ("Cool description!", oshmc.description());
    EXPECT_EQ(ColumnType::string, oshmc.type());
    EXPECT_EQ(&test_host, oshmc.columnData<void>(Row{&test_host}));
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
    test_host.name = nullptr;
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

    set_host_notes("checking $GUT$...");
    EXPECT_EQ("checking $GUT$...", expanded_host_notes());
}

TEST_F(OffsetStringServiceMacroColumnTest, misc) {
    EXPECT_EQ("navn", ossmc.name());
    EXPECT_EQ("Beskrivelse", ossmc.description());
    EXPECT_EQ(ColumnType::string, ossmc.type());
    EXPECT_EQ(&test_service, ossmc.columnData<void>(Row{&test_service}));
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
    test_service.description = nullptr;
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

    set_service_notes("checking $LO$...");
    EXPECT_EQ("checking $LO$...", expanded_service_notes());
}
