// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>

#include "gtest/gtest.h"
#include "livestatus/opids.h"

namespace {
using NameAndCanonicalName = std::pair<std::string, std::string>;

std::string printParsed(const std::string &name) {
    std::ostringstream os;
    os << relationalOperatorForName(name);
    return os.str();
}

class OperatorNameTest : public ::testing::TestWithParam<NameAndCanonicalName> {
};
}  // namespace

TEST_P(OperatorNameTest, IsPrintedAsItsCanonicalName) {
    const auto &[name, canonical_name] = GetParam();

    EXPECT_EQ(printParsed(name), canonical_name);
}

INSTANTIATE_TEST_SUITE_P(
    OpidsTest, OperatorNameTest,
    ::testing::Values(NameAndCanonicalName{"=", "="},      //
                      NameAndCanonicalName{"!=", "!="},    //
                      NameAndCanonicalName{"~", "~"},      //
                      NameAndCanonicalName{"!~", "!~"},    //
                      NameAndCanonicalName{"=~", "=~"},    //
                      NameAndCanonicalName{"!=~", "!=~"},  //
                      NameAndCanonicalName{"~~", "~~"},    //
                      NameAndCanonicalName{"!~~", "!~~"},  //
                      NameAndCanonicalName{"<", "<"},      //
                      NameAndCanonicalName{">=", ">="},    //
                      NameAndCanonicalName{">", ">"},      //
                      NameAndCanonicalName{"<=", "<="},    //
                      NameAndCanonicalName{"!<", ">="},    //
                      NameAndCanonicalName{"!>=", "<"},    //
                      NameAndCanonicalName{"!>", "<="},    //
                      NameAndCanonicalName{"!<=", ">"}));

TEST(OpidsTest, RejectsUnknownOperatorNames) {
    EXPECT_THROW(static_cast<void>(relationalOperatorForName("!!=")),
                 std::runtime_error);
}
