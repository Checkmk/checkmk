// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "pch.h"

#include "providers/skype.h"

namespace cma::provider {

namespace {
auto g_skype_counters = internal::GetSkypeCountersVector();
auto g_skype_asp_some_counter = internal::GetSkypeAspSomeCounter();
}  // namespace

TEST(SectionProviderSkype, Construction) {
    SkypeProvider skype;
    EXPECT_EQ(skype.getUniqName(), cma::section::kSkype);
}

TEST(SectionProviderSkype, Counters) {
    auto vec = internal::GetSkypeCountersVector();
    EXPECT_EQ(vec->size(), 30);
    for (auto entry : *g_skype_counters) {
        EXPECT_EQ(entry.substr(0, 3), L"LS:");
        EXPECT_TRUE(entry.find(L" - ") != std::string::npos);
    }
}

TEST(SectionProviderSkype, StandardRun) {
    SkypeProvider skype;
    EXPECT_TRUE(skype.generateContent().empty());
}

// Skype is tested with simulated data
// We have no possibilities to install Skype Business on testing, dev and
// integration machines So. Sorry. Guys. Your SK
// We will use first best Windows counters as a base for our Skype provider
TEST(SectionProviderSkype, SimulatedIntegration) {
    SkypeProvider skype;

    // verify registry keys
    EXPECT_EQ(skype.getUniqName(), cma::section::kSkype);
    EXPECT_EQ(g_skype_counters->size(), 30);

    // store old values
    auto save = *g_skype_counters;
    ON_OUT_OF_SCOPE(*g_skype_counters = save;
                    EXPECT_TRUE(internal::GetSkypeCountersVector()->size() ==
                                30));  // recover

    // prepare testing keys array
    g_skype_counters->clear();
    g_skype_counters->push_back(L"Memory");
    g_skype_counters->push_back(L"510");

    // run
    auto ret = skype.generateContent();
    ASSERT_FALSE(ret.empty());

    // verify
    auto table = cma::tools::SplitString(ret, "\n");
    if (table.size() < (size_t)(2 + 2 * 3 + 3)) {
        for (auto &e : table) std::cout << e << std::endl;
    }
    ASSERT_GE(table.size(), (size_t)(2 + 2 * 3 + 3))
        << "Probably You have to install ASP.NET";
    EXPECT_EQ(table[0], "<<<skype:sep(44)>>>");
    auto hdr1 = cma::tools::SplitString(table[1], ",");
    ASSERT_EQ(hdr1.size(), 3);
    EXPECT_EQ(hdr1[0], "sampletime");
    EXPECT_TRUE(std::atoll(hdr1[1].c_str()) > 0);
    EXPECT_TRUE(std::atoll(hdr1[2].c_str()) > 0);
    EXPECT_EQ(table[2],
              fmt::format("[{}]", wtools::ToUtf8((*g_skype_counters)[0])));
    EXPECT_EQ(table[5],
              fmt::format("[{}]", wtools::ToUtf8((*g_skype_counters)[1])));
    EXPECT_EQ(table[table.size() - 3],
              fmt::format("[{}]", wtools::ToUtf8(g_skype_asp_some_counter)));
}

}  // namespace cma::provider
