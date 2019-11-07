// watest.cpp : This file contains the 'main' function. Program execution begins
// and ends there.
//
#include "pch.h"

#include "firewall.h"
#include "logger.h"
#include "on_start.h"

namespace cma::fw {
static std::wstring_view rule_name = L"test_CMK_rule";

TEST(Firewall, PolicyTest) {
    Policy p;
    ASSERT_TRUE(p.policy_ != nullptr);
    ASSERT_TRUE(p.rules_ != nullptr);
    ASSERT_GE(p.getRulesCount(), 10);
}

TEST(Firewall, CreateFindDelete) {
    OnStartTest();
    RemoveRule(rule_name);  // to be sure that no rules are
    ASSERT_FALSE(FindRule(rule_name));
    ASSERT_TRUE(CreateInboundRule(
        L"test_CMK_rule",
        L"%ProgramFiles%\\checkmk\\service\\check_mk_agent.exe", 9999));
    ASSERT_TRUE(FindRule(rule_name));
    ASSERT_TRUE(RemoveRule(rule_name));
    ASSERT_FALSE(FindRule(rule_name));
    // the_test();
}

}  // namespace cma::fw
