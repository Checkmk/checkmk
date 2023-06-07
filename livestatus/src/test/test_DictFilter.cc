// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <iomanip>
#include <memory>
#include <sstream>
#include <string>

#include "Comment.h"  // IWYU pragma: keep
#include "NebHost.h"
#include "gtest/gtest.h"
#include "livestatus/Column.h"
#include "livestatus/DictColumn.h"
#include "livestatus/DictFilter.h"
#include "livestatus/Filter.h"
#include "livestatus/Interface.h"
#include "livestatus/Row.h"
#include "livestatus/User.h"
#include "livestatus/opids.h"
#include "test_utilities.h"

namespace {
std::string b16encode(const std::string &str) {
    std::ostringstream os;
    os << std::hex << std::uppercase << std::setfill('0');
    for (auto ch : str) {
        os << std::setw(2)
           << static_cast<unsigned>(static_cast<unsigned char>(ch));
    }
    return os.str();
}

struct DictFilterTest : public ::testing::Test {
    bool accepts(AttributeKind kind, const std::string &value) const {
        DictColumn<IHost> cvdc{
            "name", "description", ColumnOffsets{},
            [kind](const IHost &r) { return r.attributes(kind); }};
        const DictFilter filter{Filter::Kind::row, "name",
                                [&cvdc](Row row) { return cvdc.getValue(row); },
                                RelationalOperator::equal, value};
        NebHost h{test_host};
        return filter.accepts(Row{&h}, NoAuthUser{}, {});
    }

    TestHost test_host{
        {{"ERNIE", "Bert"},
         {"GUT", "Mies"},
         {"_TAG_" + b16encode("Rock'n"), b16encode("Rock'n Roll")},
         {"_TAG_" + b16encode("Rollin"), b16encode("Rock'n Rollin'")},
         {"_TAG_" + b16encode("GUT"), b16encode("Guten Tag!")},
         {"_LABEL_" + b16encode("GÓÐ"), b16encode("Góðan dag!")},
         {"_LABEL_" + b16encode("GUT"), b16encode("foo")},
         {"_LABELSOURCE_" + b16encode("GUT"), b16encode("bar")}}};
};
}  // namespace

TEST_F(DictFilterTest, empty) {
    EXPECT_TRUE(accepts(AttributeKind::tags, ""));
    EXPECT_TRUE(accepts(AttributeKind::tags, " "));
    EXPECT_FALSE(accepts(AttributeKind::tags, "GUT"));
    EXPECT_FALSE(accepts(AttributeKind::tags, "GUT '' "));
}

TEST_F(DictFilterTest, UnquotedKinds) {
    EXPECT_TRUE(accepts(AttributeKind::custom_variables, "GUT Mies"));
    EXPECT_TRUE(accepts(AttributeKind::tags, "GUT Guten Tag!"));
    EXPECT_TRUE(accepts(AttributeKind::labels, "GUT foo"));
    EXPECT_TRUE(accepts(AttributeKind::label_sources, "GUT bar"));
    EXPECT_FALSE(accepts(AttributeKind::label_sources, "GUT bart"));
}

TEST_F(DictFilterTest, UnquotedSplitting) {
    EXPECT_TRUE(accepts(AttributeKind::tags, "     GUT Guten Tag!"));
    EXPECT_TRUE(accepts(AttributeKind::tags, "     GUT    Guten Tag!"));
    EXPECT_FALSE(accepts(AttributeKind::tags, "    GUT    Guten Tag!    "));
}

TEST_F(DictFilterTest, UnquotedUTF8) {
    EXPECT_TRUE(accepts(AttributeKind::labels, "GÓÐ Góðan dag!"));
    EXPECT_TRUE(accepts(AttributeKind::labels, "     GÓÐ Góðan dag!"));
    EXPECT_TRUE(accepts(AttributeKind::labels, "     GÓÐ    Góðan dag!"));
    EXPECT_FALSE(accepts(AttributeKind::labels, "    GÓÐ    Góðan dag!   "));
}

TEST_F(DictFilterTest, QuotedSplitting) {
    EXPECT_TRUE(accepts(AttributeKind::tags, "'GUT' 'Guten Tag!'"));
    EXPECT_TRUE(accepts(AttributeKind::tags, "     'GUT' 'Guten Tag!'"));
    EXPECT_TRUE(accepts(AttributeKind::tags, "     'GUT'    'Guten Tag!'"));
    EXPECT_TRUE(accepts(AttributeKind::tags, "    'GUT'    'Guten Tag!'    "));
}

TEST_F(DictFilterTest, QuotedEscape) {
    EXPECT_TRUE(accepts(AttributeKind::tags, "'Rock''n' 'Rock''n Roll'"));
    EXPECT_TRUE(accepts(AttributeKind::tags, "'Rock''n' 'Rock''n Roll"));
    EXPECT_TRUE(accepts(AttributeKind::tags, "'Rollin' 'Rock''n Rollin'''"));
    EXPECT_TRUE(accepts(AttributeKind::labels, "'GUT'foo"));
}
