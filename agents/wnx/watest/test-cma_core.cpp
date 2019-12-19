//
// test-tools.cpp :

#include "pch.h"

#include "cfg.h"
#include "cma_core.h"

namespace cma {
extern std::unordered_map<std::wstring, wtools::InternalUser> G_Users;

TEST(CmaCore, InternalUsers) {
    using namespace std::string_literals;
    const wchar_t* t[] = {L"a.exe", L"b", L"c"};

    auto x = ObtainInternalUser(L"Users");
    EXPECT_TRUE(!x.first.empty());
    EXPECT_EQ(x.first, L"cmk_TST_Users"s);
    EXPECT_EQ(G_Users.size(), 1);

    auto x2 = ObtainInternalUser(L"Users");
    EXPECT_TRUE(!x2.first.empty());
    EXPECT_EQ(x2.first, L"cmk_TST_Users"s);
    EXPECT_TRUE(x == x2);

    EXPECT_EQ(G_Users.size(), 1);

    KillAllInternalUsers();
    EXPECT_TRUE(G_Users.empty());
};

TEST(CmaCore, Misc) {
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

}  // namespace cma
