#include <cstddef>
#include <string>
#include "CustomVarsDictColumn.h"
#include "CustomVarsDictFilter.h"
#include "Filter.h"
#include "MonitoringCore.h"
#include "NagiosCore.h"
#include "Row.h"
#include "data_encoding.h"
#include "gtest/gtest.h"
#include "nagios.h"
#include "opids.h"
#include "test_utilities.h"

namespace {
struct CustomVarsDictFilterTest : public ::testing::Test {
    TestHost test_host{{{"ERNIE", "Bert"},  //
                        {"HARRY", "Hirsch"},
                        {"_TAG_GUT", "Guten Tag!"}}};
    NagiosCore core{NagiosPaths{}, NagiosLimits{}, NagiosAuthorization{},
                    Encoding::utf8};
    CustomVarsDictColumn cvdc{"name", "description",
                              -1,     -1,
                              -1,     offsetof(host, custom_variables),
                              &core,  AttributeKind::tags};
};
}  // namespace

TEST_F(CustomVarsDictFilterTest, simple) {
    CustomVarsDictFilter filter{Filter::Kind::row, cvdc,
                                RelationalOperator::equal, "GUT Guten Tag!"};
    EXPECT_EQ(true, filter.accepts(Row{&test_host}, {}, {}));
}
