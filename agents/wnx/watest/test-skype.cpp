// test-section_skype.cpp

//
#include "pch.h"

#include <time.h>

#include <chrono>
#include <filesystem>
#include <future>
#include <string_view>

#include "cfg.h"
#include "cfg_details.h"
#include "cma_core.h"
#include "common/cfg_info.h"
#include "providers/skype.h"
#include "read_file.h"

namespace cma::provider {  // to become friendly for wtools classes
auto SkypeCounters = internal::GetSkypeCountersVector();
extern std::wstring SkypeAspSomeCounter;

TEST(SectionProviderSkype, Construction) {
    SkypeProvider skype;
    EXPECT_EQ(skype.getUniqName(), cma::section::kSkype);
}

// Skype is tested with simulated data
// We have no possibilities to install Skype Business on testing, dev and
// integration machines So. Sorry. Guys. Your SK
TEST(SectionProviderSkype, Api) {
    SkypeProvider skype;

    // verify registry keys
    EXPECT_EQ(skype.getUniqName(), cma::section::kSkype);
    EXPECT_EQ(SkypeCounters->size(), 29);

    // store old values
    auto save = SkypeCounters;
    ON_OUT_OF_SCOPE(SkypeCounters = save;);  // recover

    // prepare testing keys array
    SkypeCounters->clear();
    SkypeCounters->push_back(L"Memory");
    SkypeCounters->push_back(L"510");

    // run
    auto ret = skype.generateContent();
    ASSERT_FALSE(ret.empty());

    // verify
    auto table = cma::tools::SplitString(ret, "\n");
    if (table.size() < (size_t)(2 + 2 * 3 + 3)) {
        for (auto& e : table) std::cout << e << std::endl;
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
              fmt::format("[{}]", wtools::ConvertToUTF8((*SkypeCounters)[0])));
    EXPECT_EQ(table[5],
              fmt::format("[{}]", wtools::ConvertToUTF8((*SkypeCounters)[1])));
    EXPECT_EQ(table[table.size() - 3],
              fmt::format("[{}]", wtools::ConvertToUTF8(SkypeAspSomeCounter)));
}

}  // namespace cma::provider
