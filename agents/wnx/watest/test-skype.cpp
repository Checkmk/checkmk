// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "pch.h"

#include "providers/skype.h"

namespace cma::provider {

TEST(SectionProviderSkype, Construction) {
    SkypeProvider skype;
    EXPECT_EQ(skype.getUniqName(), cma::section::kSkype);
}

TEST(SectionProviderSkype, Counters) {
    auto vec = internal::GetSkypeCountersVector();
    EXPECT_EQ(vec->size(), 30);
    for (const auto &entry : *vec) {
        EXPECT_EQ(entry.substr(0, 3), L"LS:");
        EXPECT_TRUE(entry.find(L" - ") != std::string::npos);
    }
}

TEST(SectionProviderSkype, StandardRunIntegration) {
    SkypeProvider skype;
    EXPECT_TRUE(skype.generateContent().empty());
}

// Skype is tested with simulated data
// We have no possibilities to install Skype Business on testing, dev and
// integration machines.
// We will use first best Windows counters as a base for our Skype provider
TEST(SectionProviderSkype, SimulatedIntegration) {
    constexpr size_t base_size = 2U + 2U * 3U;
    constexpr size_t asp_size = 3U;
    constexpr size_t full_size = base_size + asp_size;

    auto skype_counters = internal::GetSkypeCountersVector();
    auto skype_asp_some_counter = internal::GetSkypeAspSomeCounter();

    SkypeProvider skype;

    // verify registry keys
    EXPECT_EQ(skype.getUniqName(), cma::section::kSkype);
    EXPECT_EQ(skype_counters->size(), 30);

    // store old values
    const std::vector<std::wstring> save = *skype_counters;
    ON_OUT_OF_SCOPE(*skype_counters = save;
                    EXPECT_TRUE(internal::GetSkypeCountersVector()->size() ==
                                30));  // recover

    // prepare testing keys array
    skype_counters->clear();
    skype_counters->push_back(L"Memory");
    skype_counters->push_back(L"510");

    auto ret = skype.generateContent();
    ASSERT_FALSE(ret.empty());

    auto table = tools::SplitString(ret, "\n");

    ASSERT_GE(table.size(), base_size);
    EXPECT_EQ(table[0], "<<<skype:sep(44)>>>");
    auto hdr1 = tools::SplitString(table[1], ",");
    ASSERT_EQ(hdr1.size(), 3);
    EXPECT_EQ(hdr1[0], "sampletime");
    EXPECT_TRUE(std::atoll(hdr1[1].c_str()) > 0);
    EXPECT_TRUE(std::atoll(hdr1[2].c_str()) > 0);
    EXPECT_EQ(table[2],
              fmt::format("[{}]", wtools::ToUtf8((*skype_counters)[0])));
    EXPECT_EQ(table[5],
              fmt::format("[{}]", wtools::ToUtf8((*skype_counters)[1])));
    if (table.size() >= full_size) {
        EXPECT_EQ(table[table.size() - 3U],
                  fmt::format("[{}]", wtools::ToUtf8(skype_asp_some_counter)));
    }
}

}  // namespace cma::provider
