// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <string>

#include "gtest/gtest.h"
#include "livestatus/RRDFetch.h"
#include "livestatus/StringUtils.h"

TEST(TestRRDFetchHeader, Header) {
    const char *raw =
        "FlushVersion: 1\n"
        "Start: 1733220000\n"
        "End: 1736245800\n"
        "Step: 1800\n"
        "DSCount: 2\n";
    auto header = mk::split(raw, '\n');
    EXPECT_EQ(header, RRDFetchHeader::parse(header).unparse());
}

TEST(TestRRDFetchBinPayloadHeader, Header) {
    const char *raw = "DSName-1 BinaryData 1234 8 LITTLE";
    EXPECT_EQ(RRDFetchBinPayloadHeader::parse(raw).unparse(), raw);
}
