// watest.cpp : This file contains the 'main' function. Program execution begins
// and ends there.
//
#include "pch.h"

#include "firewall.h"
#include "logger.h"
#include "on_start.h"
#include "tools/_misc.h"

namespace cma::fw {
static std::wstring_view rule_name = L"test_CMK_rule";
static std::wstring_view rule_name_bad = L"test_CMK_rule_";
static std::wstring app_name_base =
    std::wstring(L"%ProgramFiles%") + L"\\checkmk\\service\\check_mk_agent.exe";
static std::wstring app_name_canonical =
    cma::tools::win::GetEnv(L"ProgramFiles") +
    L"\\checkmk\\service\\check_mk_agent.exe";
static std::wstring app_name_canonical_bad =
    cma::tools::win::GetEnv(L"ProgramFiles") +
    L"\\checkmk\\service\\check_mk_agent.exe_";

TEST(Firewall, PolicyTest) {
    Policy p;
    ASSERT_TRUE(p.policy_ != nullptr);
    ASSERT_TRUE(p.rules_ != nullptr);
    ASSERT_GE(p.getRulesCount(), 10);
}

class FirewallTest : public ::testing::Test {
    void SetUp() override {
        OnStartTest();
        RemoveRule(rule_name);  // to be sure that no rules are
        RemoveRule(rule_name);  // Microsoft :( same names
    }

    void TearDown() override {
        // cleanup on failed tests
        RemoveRule(rule_name);
    }
};

TEST_F(FirewallTest, CreateFindDelete) {
    ASSERT_FALSE(FindRule(rule_name));
    EXPECT_EQ(CountRules(rule_name, L""), 0);
    ASSERT_TRUE(CreateInboundRule(rule_name, app_name_base, 9999));
    EXPECT_EQ(CountRules(rule_name, L""), 1);
    EXPECT_EQ(CountRules(rule_name, app_name_canonical), 1)
        << "Rule " << rule_name.data() << " for " << app_name_canonical.data()
        << "not found/1";
    EXPECT_EQ(CountRules(rule_name, app_name_canonical_bad), 0);
    ASSERT_NE(FindRule(rule_name), nullptr);
    EXPECT_FALSE(FindRule(rule_name_bad));

    auto rule = FindRule(rule_name, app_name_canonical);
    ASSERT_NE(rule, nullptr) << "Rule " << rule_name.data() << " for "
                             << app_name_canonical.data() << "not found/2";

    long types = 0;
    rule->get_Profiles(&types);
    EXPECT_EQ(types, NET_FW_PROFILE2_DOMAIN | NET_FW_PROFILE2_PRIVATE |
                         NET_FW_PROFILE2_PUBLIC);

    EXPECT_FALSE(FindRule(rule_name, app_name_canonical_bad));

    ASSERT_FALSE(RemoveRule(rule_name, app_name_canonical_bad));
    ASSERT_TRUE(RemoveRule(rule_name, app_name_canonical));
    EXPECT_EQ(CountRules(rule_name, app_name_canonical), 0);
    EXPECT_FALSE(FindRule(rule_name));
}

}  // namespace cma::fw
