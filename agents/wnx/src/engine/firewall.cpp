// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "stdafx.h"

#include "firewall.h"

#include <comutil.h>
#include <netfw.h>

#include <filesystem>

#include "common/wtools.h"
#include "logger.h"
#include "tools/_misc.h"

#pragma comment(lib, "ole32.lib")
#pragma comment(lib, "oleaut32.lib")
namespace cma::fw {

#define NET_FW_IP_PROTOCOL_TCP_NAME L"TCP"
#define NET_FW_IP_PROTOCOL_UDP_NAME L"UDP"

#define NET_FW_RULE_DIR_IN_NAME L"In"
#define NET_FW_RULE_DIR_OUT_NAME L"Out"

#define NET_FW_RULE_ACTION_BLOCK_NAME L"Block"
#define NET_FW_RULE_ACTION_ALLOW_NAME L"Allow"

#define NET_FW_RULE_ENABLE_IN_NAME L"TRUE"
#define NET_FW_RULE_DISABLE_IN_NAME L"FALSE"

INetFwRule *CreateRule() {  // Create a new Firewall Rule object.
    INetFwRule *rule = nullptr;
    auto hr =
        CoCreateInstance(__uuidof(NetFwRule), nullptr, CLSCTX_INPROC_SERVER,
                         __uuidof(INetFwRule), (void **)&rule);
    if (FAILED(hr)) {
        XLOG::l("CoCreateInstance for Firewall Rule failed: [{:#X}]", hr);
        return nullptr;
    }

    return rule;
}

Policy::Policy() {
    auto hr =
        CoCreateInstance(__uuidof(NetFwPolicy2), NULL, CLSCTX_INPROC_SERVER,
                         __uuidof(INetFwPolicy2), (void **)&policy_);

    if (FAILED(hr)) {
        XLOG::l("CoCreateInstance for INetFwPolicy2 failed: [{:#X}]", hr);
        policy_ = nullptr;
    }

    policy_->get_Rules(&rules_);
    if (FAILED(hr)) {
        XLOG::l("get_Rules failed: [{:#X}]", hr);
    }
}

Policy::~Policy() {
    if (rules_) rules_->Release();
    if (policy_) policy_->Release();
}

long Policy::getCurrentProfileTypes() {
    if (policy_ == nullptr) {
        return -1;
    }

    long bit_mask = 0;
    auto hr = policy_->get_CurrentProfileTypes(&bit_mask);
    if (FAILED(hr)) {
        XLOG::l("get_CurrentProfileTypes failed: [{:#X}]", hr);
        return -1;
    }

    return bit_mask;
}

IEnumVARIANT *Policy::getEnum() {
    if (rules_ == nullptr) return nullptr;

    IUnknown *enumerator = nullptr;
    rules_->get__NewEnum(&enumerator);

    if (enumerator == nullptr) return nullptr;
    ON_OUT_OF_SCOPE(enumerator->Release());

    IEnumVARIANT *variant = nullptr;
    auto hr =
        enumerator->QueryInterface(__uuidof(IEnumVARIANT), (void **)&variant);

    if (SUCCEEDED(hr)) return variant;
    return nullptr;
}

long Policy::getRulesCount() {
    if (rules_ == nullptr) return 0;

    long rule_count = 0;
    auto hr = rules_->get_Count(&rule_count);
    if (FAILED(hr)) {
        XLOG::l.i("get_Count failed: [{:#X}]\n", hr);
        return 0;
    }

    return rule_count;
}

INetFwRule *ScanAllRules(std::function<INetFwRule *(INetFwRule *)> processor) {
    Policy policy;
    auto rules = policy.getRules();
    if (rules == nullptr) {
        return nullptr;
    }

    long rule_count = policy.getRulesCount();
    if (rule_count == 0) {
        return 0;
    }

    XLOG::t.i("Firewall Rules count is [{}]", rule_count);

    auto policies = policy.getEnum();
    if (policies == nullptr) {
        return nullptr;
    }
    ON_OUT_OF_SCOPE(policies->Release());

    ULONG cFetched = 0;
    VARIANT var;
    ::VariantClear(&var);

    while (true) {
        auto hr = policies->Next(1, &var, &cFetched);
        ON_OUT_OF_SCOPE(::VariantClear(&var););

        if (S_FALSE == hr || !SUCCEEDED(hr)) {
            break;
        }

        hr = ::VariantChangeType(&var, &var, 0, VT_DISPATCH);
        if (!SUCCEEDED(hr)) break;

        INetFwRule *rule = nullptr;

        auto dispatch = (V_DISPATCH(&var));
        hr = dispatch->QueryInterface(__uuidof(INetFwRule),
                                      reinterpret_cast<void **>(&rule));
        if (!SUCCEEDED(hr) || rule == nullptr) {
            continue;
        }

        // processing itself
        auto rule_candidate = processor(rule);

        // post processing
        if (rule != rule_candidate) rule->Release();

        if (rule_candidate) return rule_candidate;
    }

    return nullptr;
}

// Output properties of a Firewall rule
// ABSOLUTE INTERNAL
// FROM MSDN
// MAY HAVE MEMORY LEAKS!!!!
INetFwRule *DumpFWRulesInCollection(INetFwRule *fw_rule) {
    variant_t InterfaceArray;
    variant_t InterfaceString;

    VARIANT_BOOL bEnabled;
    BSTR bstrVal;

    long lVal = 0;
    long lProfileBitmask = 0;

    NET_FW_RULE_DIRECTION fwDirection;
    NET_FW_ACTION fwAction;

    struct ProfileMapElement {
        NET_FW_PROFILE_TYPE2 Id;
        LPCWSTR Name;
    };

    ProfileMapElement ProfileMap[3];
    ProfileMap[0].Id = NET_FW_PROFILE2_DOMAIN;
    ProfileMap[0].Name = L"Domain";
    ProfileMap[1].Id = NET_FW_PROFILE2_PRIVATE;
    ProfileMap[1].Name = L"Private";
    ProfileMap[2].Id = NET_FW_PROFILE2_PUBLIC;
    ProfileMap[2].Name = L"Public";

    XLOG::l.i("---------------------------------------------\n");
    auto to_utf8 = [](const auto bstr) -> auto {
        if (bstr == nullptr) return std::string("nullptr");
        return wtools::ToUtf8(bstr);
    };

    if (SUCCEEDED(fw_rule->get_Name(&bstrVal))) {
        XLOG::l.i("Name:             '{}'", to_utf8(bstrVal));
        ::SysFreeString(bstrVal);
    }

    if (SUCCEEDED(fw_rule->get_Description(&bstrVal))) {
        XLOG::l.i("Description:      '{}'", to_utf8(bstrVal));
        ::SysFreeString(bstrVal);
    }

    if (SUCCEEDED(fw_rule->get_ApplicationName(&bstrVal))) {
        XLOG::l.i("Application Name: '{}'", to_utf8(bstrVal));
        ::SysFreeString(bstrVal);
    }

    if (SUCCEEDED(fw_rule->get_ServiceName(&bstrVal))) {
        XLOG::l.i("Service Name:     '{}'", to_utf8(bstrVal));
        ::SysFreeString(bstrVal);
    }

    if (SUCCEEDED(fw_rule->get_Protocol(&lVal))) {
        switch (lVal) {
            case NET_FW_IP_PROTOCOL_TCP:

                XLOG::l.i("IP Protocol:      '{}'",
                          wtools::ToUtf8(NET_FW_IP_PROTOCOL_TCP_NAME));
                break;

            case NET_FW_IP_PROTOCOL_UDP:

                XLOG::l.i("IP Protocol:      '{}'",
                          wtools::ToUtf8(NET_FW_IP_PROTOCOL_UDP_NAME));
                break;

            default:

                break;
        }

        if (lVal != NET_FW_IP_VERSION_V4 && lVal != NET_FW_IP_VERSION_V6) {
            if (SUCCEEDED(fw_rule->get_LocalPorts(&bstrVal))) {
                XLOG::l.i("Local Ports:      '{}'", to_utf8(bstrVal));
                ::SysFreeString(bstrVal);
            }

            if (SUCCEEDED(fw_rule->get_RemotePorts(&bstrVal))) {
                XLOG::l.i("Remote Ports:      '{}'", to_utf8(bstrVal));
                ::SysFreeString(bstrVal);
            }
        } else {
            if (SUCCEEDED(fw_rule->get_IcmpTypesAndCodes(&bstrVal))) {
                XLOG::l.i("ICMP TypeCode:      '{}'", to_utf8(bstrVal));
                ::SysFreeString(bstrVal);
            }
        }
    }

    if (SUCCEEDED(fw_rule->get_LocalAddresses(&bstrVal))) {
        XLOG::l.i("LocalAddresses:   '{}'", to_utf8(bstrVal));
        ::SysFreeString(bstrVal);
    }

    if (SUCCEEDED(fw_rule->get_RemoteAddresses(&bstrVal))) {
        XLOG::l.i("RemoteAddresses:  '{}'", to_utf8(bstrVal));
        ::SysFreeString(bstrVal);
    }

    if (SUCCEEDED(fw_rule->get_Profiles(&lProfileBitmask))) {
        // The returned bitmask can have more than 1 bit set if multiple
        // profiles
        //   are active or current at the same time

        for (int i = 0; i < 3; i++) {
            if (lProfileBitmask & ProfileMap[i].Id) {
                XLOG::l.i("Profile:  '{}'", to_utf8(ProfileMap[i].Name));
            }
        }
    }

    if (SUCCEEDED(fw_rule->get_Direction(&fwDirection))) {
        switch (fwDirection) {
            case NET_FW_RULE_DIR_IN:

                XLOG::l.i("Direction:        '{}'",
                          wtools::ToUtf8(NET_FW_RULE_DIR_IN_NAME));
                break;

            case NET_FW_RULE_DIR_OUT:

                XLOG::l.i("Direction:        '{}'",
                          wtools::ToUtf8(NET_FW_RULE_DIR_OUT_NAME));
                break;

            default:

                break;
        }
    }

    if (SUCCEEDED(fw_rule->get_Action(&fwAction))) {
        switch (fwAction) {
            case NET_FW_ACTION_BLOCK:

                XLOG::l.i("Action:           '{}'",
                          wtools::ToUtf8(NET_FW_RULE_ACTION_BLOCK_NAME));
                break;

            case NET_FW_ACTION_ALLOW:

                XLOG::l.i("Action:           '{}'",
                          wtools::ToUtf8(NET_FW_RULE_ACTION_ALLOW_NAME));
                break;

            default:

                break;
        }
    }

    if (SUCCEEDED(fw_rule->get_Interfaces(&InterfaceArray))) {
        if (InterfaceArray.vt != VT_EMPTY) {
            SAFEARRAY *safe_arr = nullptr;

            safe_arr = InterfaceArray.parray;

            for (long index = safe_arr->rgsabound->lLbound;
                 index < (long)safe_arr->rgsabound->cElements; index++) {
                SafeArrayGetElement(safe_arr, &index, &InterfaceString);
                XLOG::l.i("Interfaces:       '{}'",
                          wtools::ToUtf8((BSTR)InterfaceString.bstrVal));
                InterfaceString.Clear();
            }
        }
    }

    if (SUCCEEDED(fw_rule->get_InterfaceTypes(&bstrVal))) {
        XLOG::l.i("Interface Types:  '{}'", to_utf8(bstrVal));
        ::SysFreeString(bstrVal);
    }

    if (SUCCEEDED(fw_rule->get_Enabled(&bEnabled))) {
        if (bEnabled) {
            XLOG::l.i("Enabled:          '{}'",
                      wtools::ToUtf8(NET_FW_RULE_ENABLE_IN_NAME));
        } else {
            XLOG::l.i("Enabled:          '{}'",
                      wtools::ToUtf8(NET_FW_RULE_DISABLE_IN_NAME));
        }
    }

    if (SUCCEEDED(fw_rule->get_Grouping(&bstrVal))) {
        XLOG::l.i("Grouping:         '{}'", to_utf8(bstrVal));
        ::SysFreeString(bstrVal);
    }

    if (SUCCEEDED(fw_rule->get_EdgeTraversal(&bEnabled))) {
        if (bEnabled) {
            XLOG::l.i("Edge Traversal:   '{}'",
                      wtools::ToUtf8(NET_FW_RULE_ENABLE_IN_NAME));
        } else {
            XLOG::l.i("Edge Traversal:   '{}'",
                      wtools::ToUtf8(NET_FW_RULE_DISABLE_IN_NAME));
        }
    }

    return nullptr;  // continue enumeration
}

// Instantiate INetFwPolicy2
INetFwPolicy2 *WFCOMInitialize() {
    INetFwPolicy2 *net_fw_policy2 = nullptr;

    auto hr =
        CoCreateInstance(__uuidof(NetFwPolicy2), nullptr, CLSCTX_INPROC_SERVER,
                         __uuidof(INetFwPolicy2), (void **)&net_fw_policy2);

    if (FAILED(hr)) {
        XLOG::l("CoCreateInstance for INetFwPolicy2 failed: [{:#X}]", hr);
        return nullptr;
    }

    return net_fw_policy2;
}

namespace {
long CorrectFirewallBitMask() {
    // According to CMK-6669
    return NET_FW_PROFILE2_DOMAIN | NET_FW_PROFILE2_PRIVATE |
           NET_FW_PROFILE2_PUBLIC;
}

std::optional<std::wstring> GetRuleName(INetFwRule *fw_rule) {
    BSTR rule_name = nullptr;
    auto ret = fw_rule->get_Name(&rule_name);
    if (ret != 0) return {};
    ON_OUT_OF_SCOPE(SysFreeString(rule_name));

    if (rule_name == nullptr) return {};

    return rule_name;
}

std::optional<std::wstring> GetRuleAppName(INetFwRule *fw_rule) {
    BSTR app_name = nullptr;
    auto ret = fw_rule->get_ApplicationName(&app_name);
    if (ret != 0) return {};
    ON_OUT_OF_SCOPE(SysFreeString(app_name));

    if (app_name == nullptr) return {};

    return app_name;
}

}  // namespace

bool CreateInboundRule(std::wstring_view rule_name,
                       std::wstring_view raw_app_name, int port) {
    auto app_name = wtools::ToCanonical(raw_app_name);

    Policy policy;

    auto *rules = policy.getRules();
    if (rules == nullptr) return false;

    auto bit_mask = CorrectFirewallBitMask();

    auto *rule = CreateRule();

    // Populate the Firewall Rule object
    rule->put_Name(wtools::Bstr(rule_name));
    rule->put_Description(wtools::Bstr(kRuleDescription));
    rule->put_ApplicationName(wtools::Bstr(app_name));
    rule->put_Protocol(NET_FW_IP_PROTOCOL_TCP);
    rule->put_LocalPorts(
        wtools::Bstr(port == -1 ? L"*" : std::to_wstring(port)));
    rule->put_Direction(NET_FW_RULE_DIR_IN);
    rule->put_Grouping(wtools::Bstr(kRuleGroup));
    rule->put_Profiles(bit_mask);
    rule->put_Action(NET_FW_ACTION_ALLOW);
    rule->put_Enabled(VARIANT_TRUE);

    // Add the Firewall Rule
    auto hr = rules->Add(rule);
    if (FAILED(hr)) {
        XLOG::l("Firewall Rule Add failed: [{:#X}]", hr);
        return false;
    }

    return true;
}

bool RemoveRule(std::wstring_view rule_name) {
    Policy policy;

    auto *rules = policy.getRules();
    if (rules == nullptr) {
        return false;
    }

    auto hr = rules->Remove(wtools::Bstr(rule_name));
    if (FAILED(hr)) {
        XLOG::l("Firewall Rule REMOVE failed: [{:#X}]", hr);
        return false;
    }

    return true;
}

namespace {
std::wstring GenerateRandomRuleName() {
    static bool run_once = false;
    if (!run_once) {
        run_once = true;
        srand(static_cast<unsigned int>(time(nullptr)));  // NOLINT
    }
    auto random_int = rand();

    std::wstring new_name{L"to_delete_"};
    new_name += std::to_wstring(random_int);

    return new_name;
}
}  // namespace

bool RemoveRule(std::wstring_view name, std::wstring_view raw_app_name) {
    if (raw_app_name.empty()) return RemoveRule(name);

    auto app_name = wtools::ToCanonical(raw_app_name);
    std::wstring new_name;

    // find a rule with name and app_name
    auto *rule = ScanAllRules(
        [name, app_name, &new_name](INetFwRule *fw_rule) -> INetFwRule * {
            if (fw_rule == nullptr) return nullptr;  // continue enumeration

            auto rule_name = GetRuleName(fw_rule);
            if (!rule_name || name != *rule_name) {
                return nullptr;
            }

            auto candidate_name = GetRuleAppName(fw_rule);
            if (!candidate_name || !tools::IsEqual(app_name, *candidate_name)) {
                return nullptr;
            }

            // we have found a rule to delete
            // unfortunately MS API has no possibility to delete this rule
            // so we rename this rule to the random name and we will delete
            // rule by this random name
            {
                new_name = GenerateRandomRuleName();
                fw_rule->put_Name(wtools::Bstr(new_name));
                XLOG::t("Rule '{}' renamed to '{}' for deletion",
                        wtools::ToUtf8(name), wtools::ToUtf8(new_name));
                return fw_rule;  // found
            }
        });

    // in any case we have to clean
    if (rule != nullptr) {
        rule->Release();
    }
    if (!new_name.empty()) {
        XLOG::t("Removing Rule '{}' for exe '{}'", wtools::ToUtf8(name),
                wtools::ToUtf8(app_name));
        return RemoveRule(new_name);
    }

    return false;
}

INetFwRule *FindRule(std::wstring_view name, std::wstring_view raw_app_name) {
    auto app_name = wtools::ToCanonical(raw_app_name);

    return ScanAllRules([name, app_name](INetFwRule *fw_rule) -> INetFwRule * {
        if (fw_rule == nullptr) return nullptr;

        auto rule_name = GetRuleName(fw_rule);
        if (!rule_name || name != *rule_name) {
            return nullptr;
        }

        if (app_name.empty()) {
            return fw_rule;
        }

        auto candidate_name = GetRuleAppName(fw_rule);
        if (candidate_name && tools::IsEqual(app_name, *candidate_name)) {
            return fw_rule;  // stop enumeration
        }

        return nullptr;
    });
}

int CountRules(std::wstring_view name, std::wstring_view raw_app_name) {
    auto app_name = wtools::ToCanonical(raw_app_name);

    int count = 0;
    ScanAllRules([name, app_name, &count](INetFwRule *fw_rule) -> INetFwRule * {
        if (fw_rule == nullptr) return nullptr;

        auto rule_name = GetRuleName(fw_rule);

        if (!rule_name || name != rule_name) {
            return nullptr;
        }

        if (app_name.empty()) {
            count++;
            return nullptr;
        }

        auto candidate_name = GetRuleAppName(fw_rule);
        if (candidate_name && tools::IsEqual(app_name, *candidate_name)) {
            count++;
        }

        return nullptr;
    });

    return count;
}

INetFwRule *FindRule(std::wstring_view name) {
    return ScanAllRules([name](INetFwRule *fw_rule) -> INetFwRule * {
        if (fw_rule == nullptr) return nullptr;  // continue enumeration

        BSTR rule_name = nullptr;
        auto ret = fw_rule->get_Name(&rule_name);
        if (ret != 0) return nullptr;

        ON_OUT_OF_SCOPE(SysFreeString(rule_name));
        return wcscmp(name.data(), rule_name) == 0 ? fw_rule : nullptr;
    });
}

}  // namespace cma::fw
