// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
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

#ifndef FIREWALL_H
#define FIREWALL_H

#pragma once

#include <netfw.h>

namespace cma::fw {

constexpr std::wstring_view kRuleGroup = L"Checkmk Agent";
constexpr std::wstring_view kRuleDescription =
    L"Allow inbound network traffic to the Checkmk Agent";

bool CreateInboundRule(std::wstring_view rule_name,
                       std::wstring_view raw_app_name, int port);

/// Remove *one* rule by 'rule_name'
bool RemoveRule(std::wstring_view rule_name);

/// Remove *one* rule by 'rule_name' and 'raw_app_name'
bool RemoveRule(std::wstring_view rule_name, std::wstring_view raw_app_name);

/// If raw_app_name is empty, then ignore check app name in rule
int CountRules(std::wstring_view rule_name, std::wstring_view raw_app_name);

/// Find a rule by 'name'
INetFwRule *FindRule(std::wstring_view rule_name);

/// Find a rule by 'rule_name' and 'app_name'
INetFwRule *FindRule(std::wstring_view rule_name,
                     std::wstring_view raw_app_name);

// "Proxy" class to keep Windows Firewall API isolated
class Policy {
public:
    Policy(const Policy &p) = delete;
    Policy &operator=(const Policy &p) = delete;
    Policy(const Policy &&p) = delete;
    Policy &operator=(Policy &&p) = delete;

    Policy();
    ~Policy();

    [[nodiscard]] INetFwRules *getRules() const noexcept { return rules_; }
    [[nodiscard]] long getRulesCount() const;
    [[nodiscard]] long getCurrentProfileTypes() const;

    [[nodiscard]] IEnumVARIANT *getEnum() const;

private:
    INetFwPolicy2 *policy_ = nullptr;
    INetFwRules *rules_ = nullptr;
};

}  // namespace cma::fw

#endif  // FIREWALL_H
