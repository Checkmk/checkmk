//
// test-tools.cpp :

#include "pch.h"

#include "wnx/cfg.h"
#include "wnx/cma_core.h"

namespace cma {
extern std::unordered_map<std::wstring, wtools::InternalUser> g_users;

TEST(CmaCore, PluginsExecutionUser2Iu) {
    {
        auto iu = PluginsExecutionUser2Iu("");
        EXPECT_TRUE(iu.first.empty());
        EXPECT_TRUE(iu.second.empty());
    }
    {
        auto iu = PluginsExecutionUser2Iu("1 2");
        EXPECT_TRUE(iu.first == L"1");
        EXPECT_TRUE(iu.second == L"2");
    }
    {
        auto iu = PluginsExecutionUser2Iu("1  2");
        EXPECT_TRUE(iu.first == L"1");
        EXPECT_TRUE(iu.second == L" 2");
    }
    {
        auto iu = PluginsExecutionUser2Iu("1__2");
        EXPECT_TRUE(iu.first == L"1__2");
        EXPECT_TRUE(iu.second.empty());
    }
    {
        auto iu = PluginsExecutionUser2Iu("1__2 ");
        EXPECT_TRUE(iu.first == L"1__2");
        EXPECT_TRUE(iu.second.empty());
    }
    {
        auto iu = PluginsExecutionUser2Iu("1__2  ");
        EXPECT_TRUE(iu.first == L"1__2");
        EXPECT_TRUE(iu.second == L" ");
    }
}

namespace tools {
TEST(CapTest, CheckAreFilesSame) {
    EXPECT_TRUE(AreFilesSame("c:\\windows\\system32\\chcp.com",
                             "c:\\windows\\system32\\chcp.com"));
    EXPECT_FALSE(AreFilesSame("c:\\windows\\system32\\chcp.com",
                              "c:\\windows\\HelpPane.exe"));

    EXPECT_FALSE(AreFilesSame("c:\\windows\\system32\\chcp.com",
                              "c:\\windows\\ssd.exe"));
}

}  // namespace tools

}  // namespace cma
