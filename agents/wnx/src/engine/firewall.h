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

/// Remove *one* rule by 'name'
bool RemoveRule(std::wstring_view rule_name);

/// Remove *one* rule by 'name' and 'app_name'
bool RemoveRule(std::wstring_view rule_name, std::wstring_view app_name);

/// If raw_app_name is empty, then ignore check app name in rule
int CountRules(std::wstring_view name, std::wstring_view raw_app_name);

/// Find a rule by 'name'
INetFwRule *FindRule(std::wstring_view name);

/// Find a rule by 'name' and 'app_name'
INetFwRule *FindRule(std::wstring_view name, std::wstring_view app_name);

// "Proxy" class to keep Windows Firewall API isolated
class Policy {
public:
    Policy(const Policy &p) = delete;
    Policy &operator=(const Policy &p) = delete;
    Policy(const Policy &&p) = delete;
    Policy &operator=(Policy &&p) = delete;

    Policy();
    ~Policy();

    INetFwRules *getRules() { return rules_; }
    long getRulesCount();
    long getCurrentProfileTypes();

    IEnumVARIANT *getEnum();

private:
    INetFwPolicy2 *policy_ = nullptr;
    INetFwRules *rules_ = nullptr;
};

}  // namespace cma::fw

#endif  // firewall_h__
