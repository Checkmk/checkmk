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
    bool accepts(AttributeKind kind, const std::string& value) {
        CustomVarsDictColumn cvdc{
            "name", "description", -1, -1, -1, offsetof(host, custom_variables),
            &core,  kind};
        CustomVarsDictFilter filter{Filter::Kind::row, cvdc,
                                    RelationalOperator::equal, value};
        return filter.accepts(Row{&test_host}, {}, {});
    }

    NagiosCore core{NagiosPaths{}, NagiosLimits{}, NagiosAuthorization{},
                    Encoding::utf8};

    TestHost test_host{{{"ERNIE", "Bert"},
                        {"GUT", "Mies"},
                        {"_TAG_Rock'n", "Rock'n Roll"},
                        {"_TAG_Rollin", "Rock'n Rollin'"},
                        {"_TAG_GUT", "Guten Tag!"},
                        {"_LABEL_GÓÐ", "Góðan dag!"},
                        {"_LABEL_GUT", "foo"},
                        {"_LABELSOURCE_GUT", "bar"}}};
};
}  // namespace

TEST_F(CustomVarsDictFilterTest, empty) {
    EXPECT_TRUE(accepts(AttributeKind::tags, ""));
    EXPECT_TRUE(accepts(AttributeKind::tags, " "));
    EXPECT_FALSE(accepts(AttributeKind::tags, "GUT"));
    EXPECT_FALSE(accepts(AttributeKind::tags, "GUT '' "));
}

TEST_F(CustomVarsDictFilterTest, unquoted_kinds) {
    EXPECT_TRUE(accepts(AttributeKind::custom_variables, "GUT Mies"));
    EXPECT_TRUE(accepts(AttributeKind::tags, "GUT Guten Tag!"));
    EXPECT_TRUE(accepts(AttributeKind::labels, "GUT foo"));
    EXPECT_TRUE(accepts(AttributeKind::label_sources, "GUT bar"));
    EXPECT_FALSE(accepts(AttributeKind::label_sources, "GUT bart"));
}

TEST_F(CustomVarsDictFilterTest, unquoted_splitting) {
    EXPECT_TRUE(accepts(AttributeKind::tags, "     GUT Guten Tag!"));
    EXPECT_TRUE(accepts(AttributeKind::tags, "     GUT    Guten Tag!"));
    EXPECT_FALSE(accepts(AttributeKind::tags, "    GUT    Guten Tag!    "));
}

TEST_F(CustomVarsDictFilterTest, unquoted_utf8) {
    EXPECT_TRUE(accepts(AttributeKind::labels, "GÓÐ Góðan dag!"));
    EXPECT_TRUE(accepts(AttributeKind::labels, "     GÓÐ Góðan dag!"));
    EXPECT_TRUE(accepts(AttributeKind::labels, "     GÓÐ    Góðan dag!"));
    EXPECT_FALSE(accepts(AttributeKind::labels, "    GÓÐ    Góðan dag!   "));
}

TEST_F(CustomVarsDictFilterTest, quoted_splitting) {
    EXPECT_TRUE(accepts(AttributeKind::tags, "'GUT' 'Guten Tag!'"));
    EXPECT_TRUE(accepts(AttributeKind::tags, "     'GUT' 'Guten Tag!'"));
    EXPECT_TRUE(accepts(AttributeKind::tags, "     'GUT'    'Guten Tag!'"));
    EXPECT_TRUE(accepts(AttributeKind::tags, "    'GUT'    'Guten Tag!'    "));
}

TEST_F(CustomVarsDictFilterTest, quoted_escape) {
    EXPECT_TRUE(accepts(AttributeKind::tags, "'Rock''n' 'Rock''n Roll'"));
    EXPECT_TRUE(accepts(AttributeKind::tags, "'Rock''n' 'Rock''n Roll"));
    EXPECT_TRUE(accepts(AttributeKind::tags, "'Rollin' 'Rock''n Rollin'''"));
    EXPECT_TRUE(accepts(AttributeKind::labels, "'GUT'foo"));
}
