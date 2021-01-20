// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// engine to install/remove firewall rule
// namespace cma::fw

// ***************************************************
// #ATTENTION:
// THIS API WASN'T TESTED ON MEMORY LEAKS
// USE IT CAREFULLY and ONLY ONCE DURING PROCESS LIFE
// THANK YOU FOR UNDERSTANDING
// ***************************************************

#ifndef firewall_h__
#define firewall_h__

#pragma once

#include <netfw.h>

#include <functional>

#include "tools/_raii.h"

namespace cma::fw {

constexpr std::wstring_view kRuleGroup = L"Checkmk Agent";
constexpr std::wstring_view kRuleDescription =
    L"Allow inbound network traffic to the Checkmk Agent";

bool CreateInboundRule(std::wstring_view rule_name, std::wstring_view app_name,
                       int port);

bool RemoveRule(std::wstring_view rule_name);
bool RemoveRule(std::wstring_view rule_name, std::wstring_view app_name);

// mid-level API to be used with functor
// functor should find an appropriate rule anf return it to stop scanning
INetFwRule* ScanAllRules(std::function<INetFwRule*(INetFwRule*)> processor);

int CountRules(std::wstring_view name, std::wstring_view raw_app_name);

// Dump API, do not use it production
INetFwRule* DumpFWRulesInCollection(INetFwRule* fw_rule);
inline void DumpAllRules() { ScanAllRules(DumpFWRulesInCollection); }

// type A: find random rule with 'name'
INetFwRule* FindRule(std::wstring_view name);
// type B: find random rule with 'name' and 'app_name'
INetFwRule* FindRule(std::wstring_view name, std::wstring_view app_name);

// proxy class to keep Windows Firewall API maximally isolated
class Policy {
public:
    Policy(const Policy& p) = delete;
    Policy& operator=(const Policy& p) = delete;
    Policy(const Policy&& p) = delete;
    Policy& operator=(Policy&& p) = delete;

    Policy();
    ~Policy();

    INetFwRules* getRules() { return rules_; }
    long getRulesCount();
    long getCurrentProfileTypes();

    IEnumVARIANT* getEnum();

private:
    INetFwPolicy2* policy_ = nullptr;
    INetFwRules* rules_ = nullptr;

#if defined(GTEST_INCLUDE_GTEST_GTEST_H_)
    friend class Firewall;
    FRIEND_TEST(Firewall, PolicyTest);
#endif
};

}  // namespace cma::fw

#endif  // firewall_h__
