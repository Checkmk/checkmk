// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "stdafx.h"

#include "wnx/firewall.h"

#include <comutil.h>
#include <netfw.h>

#include "common/wtools.h"
#include "tools/_misc.h"
#include "wnx/logger.h"

#pragma comment(lib, "ole32.lib")
#pragma comment(lib, "oleaut32.lib")
namespace cma::fw {

constexpr std::wstring_view NET_FW_IP_PROTOCOL_TCP_NAME = L"TCP";
constexpr std::wstring_view NET_FW_IP_PROTOCOL_UDP_NAME = L"UDP";
constexpr std::wstring_view NET_FW_RULE_DIR_IN_NAME = L"In";
constexpr std::wstring_view NET_FW_RULE_DIR_OUT_NAME = L"Out";
constexpr std::wstring_view NET_FW_RULE_ACTION_BLOCK_NAME = L"Block";
constexpr std::wstring_view NET_FW_RULE_ACTION_ALLOW_NAME = L"Allow";
constexpr std::wstring_view NET_FW_RULE_ENABLE_IN_NAME = L"TRUE";
constexpr std::wstring_view NET_FW_RULE_DISABLE_IN_NAME = L"FALSE";

INetFwRule *CreateRule() {  // Create a new Firewall Rule object.
    INetFwRule *rule = nullptr;
    auto hr = CoCreateInstance(__uuidof(NetFwRule), nullptr,
                               CLSCTX_INPROC_SERVER, __uuidof(INetFwRule),
                               reinterpret_cast<void **>(&rule));
    if (FAILED(hr)) {
        XLOG::l("CoCreateInstance for Firewall Rule failed: [{:#X}]", hr);
        return nullptr;
    }

    return rule;
}

Policy::Policy() {
    auto hr = CoCreateInstance(__uuidof(NetFwPolicy2), nullptr,
                               CLSCTX_INPROC_SERVER, __uuidof(INetFwPolicy2),
                               reinterpret_cast<void **>(&policy_));

    if (FAILED(hr)) {
        XLOG::l("CoCreateInstance for INetFwPolicy2 failed: [{:#X}]", hr);
        policy_ = nullptr;
        rules_ = nullptr;
        return;
    }

    policy_->get_Rules(&rules_);
    if (FAILED(hr)) {
        XLOG::l("get_Rules failed: [{:#X}]", hr);
    }
}

Policy::~Policy() {
    if (rules_ != nullptr) {
        rules_->Release();
    }
    if (policy_ != nullptr) {
        policy_->Release();
    }
}

long Policy::getCurrentProfileTypes() const {
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

IEnumVARIANT *Policy::getEnum() const {
    if (rules_ == nullptr) {
        return nullptr;
    }

    IUnknown *enumerator = nullptr;
    rules_->get__NewEnum(&enumerator);

    if (enumerator == nullptr) {
        return nullptr;
    }
    ON_OUT_OF_SCOPE(enumerator->Release());

    IEnumVARIANT *variant = nullptr;
    const auto hr = enumerator->QueryInterface(
        __uuidof(IEnumVARIANT), reinterpret_cast<void **>(&variant));

    return SUCCEEDED(hr) ? variant : nullptr;
}

long Policy::getRulesCount() const {
    if (rules_ == nullptr) {
        return 0;
    }

    long rule_count = 0;
    auto hr = rules_->get_Count(&rule_count);
    if (FAILED(hr)) {
        XLOG::l.i("get_Count failed: [{:#X}]\n", hr);
        return 0;
    }

    return rule_count;
}

INetFwRule *ScanAllRules(
    const std::function<INetFwRule *(INetFwRule *)> &processor) {
    const Policy policy;
    if (policy.getRules() == nullptr) {
        return nullptr;
    }

    long rule_count = policy.getRulesCount();
    if (rule_count == 0) {
        return nullptr;
    }

    XLOG::t.i("Firewall Rules count is [{}]", rule_count);

    const auto policies = policy.getEnum();
    if (policies == nullptr) {
        return nullptr;
    }
    ON_OUT_OF_SCOPE(policies->Release());

    ULONG fetched = 0;
    VARIANT var{};
    ::VariantClear(&var);

    while (true) {
        auto hr = policies->Next(1, &var, &fetched);
        ON_OUT_OF_SCOPE(::VariantClear(&var););

        if (S_FALSE == hr || !SUCCEEDED(hr)) {
            break;
        }

        hr = ::VariantChangeType(&var, &var, 0, VT_DISPATCH);
        if (!SUCCEEDED(hr)) {
            break;
        }

        INetFwRule *rule = nullptr;

        const auto dispatch = V_DISPATCH(&var);
        hr = dispatch->QueryInterface(__uuidof(INetFwRule),
                                      reinterpret_cast<void **>(&rule));
        if (!SUCCEEDED(hr) || rule == nullptr) {
            continue;
        }

        // processing itself
        const auto rule_candidate = processor(rule);

        // post processing
        if (rule != rule_candidate) {
            rule->Release();
        }

        if (rule_candidate) {
            return rule_candidate;
        }
    }

    return nullptr;
}

namespace {
std::string ToUtf8(const BSTR &bstr) {
    if (bstr == nullptr) {
        return {"nullptr"};
    }
    return wtools::ToUtf8(bstr);
}

void DumpBaseInfo(INetFwRule *fw_rule) {
    BSTR bstr_val{nullptr};
    if (SUCCEEDED(fw_rule->get_Name(&bstr_val))) {
        XLOG::l.i("Name:             '{}'", ToUtf8(bstr_val));
        ::SysFreeString(bstr_val);
    }

    if (SUCCEEDED(fw_rule->get_Description(&bstr_val))) {
        XLOG::l.i("Description:      '{}'", ToUtf8(bstr_val));
        ::SysFreeString(bstr_val);
    }

    if (SUCCEEDED(fw_rule->get_ApplicationName(&bstr_val))) {
        XLOG::l.i("Application Name: '{}'", ToUtf8(bstr_val));
        ::SysFreeString(bstr_val);
    }

    if (SUCCEEDED(fw_rule->get_ServiceName(&bstr_val))) {
        XLOG::l.i("Service Name:     '{}'", ToUtf8(bstr_val));
        ::SysFreeString(bstr_val);
    }
}

void DumpDirection(INetFwRule *fw_rule) {
    NET_FW_RULE_DIRECTION fw_direction;

    if (!SUCCEEDED(fw_rule->get_Direction(&fw_direction))) {
        return;
    }
    switch (fw_direction) {
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

void DumpAction(INetFwRule *fw_rule) {
    NET_FW_ACTION fw_action;
    if (!SUCCEEDED(fw_rule->get_Action(&fw_action))) {
        return;
    }

    switch (fw_action) {
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

void DumpProtocol(INetFwRule *fw_rule) {
    long protocol = 0;
    if (!SUCCEEDED(fw_rule->get_Protocol(&protocol))) {
        return;
    }

    switch (protocol) {
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
}
void DumpPorts(INetFwRule *fw_rule) {
    BSTR bstr_val{nullptr};
    if (SUCCEEDED(fw_rule->get_LocalPorts(&bstr_val))) {
        XLOG::l.i("Local Ports:      '{}'", ToUtf8(bstr_val));
        ::SysFreeString(bstr_val);
    }
    if (SUCCEEDED(fw_rule->get_RemotePorts(&bstr_val))) {
        XLOG::l.i("Remote Ports:      '{}'", ToUtf8(bstr_val));
        ::SysFreeString(bstr_val);
    }
}

void DumpIcmp(INetFwRule *fw_rule) {
    BSTR bstr_val{nullptr};

    if (SUCCEEDED(fw_rule->get_IcmpTypesAndCodes(&bstr_val))) {
        XLOG::l.i("ICMP TypeCode:      '{}'", ToUtf8(bstr_val));
        ::SysFreeString(bstr_val);
    }
}

void DumpAddresses(INetFwRule *fw_rule) {
    BSTR bstr_val{nullptr};
    if (SUCCEEDED(fw_rule->get_LocalAddresses(&bstr_val))) {
        XLOG::l.i("LocalAddresses:   '{}'", ToUtf8(bstr_val));
        ::SysFreeString(bstr_val);
    }
    if (SUCCEEDED(fw_rule->get_RemoteAddresses(&bstr_val))) {
        XLOG::l.i("RemoteAddresses:  '{}'", ToUtf8(bstr_val));
        ::SysFreeString(bstr_val);
    }
}

void DumpProfileBitmask(INetFwRule *fw_rule) {
    long profile_bitmask = 0;
    struct ProfileMapElement {
        NET_FW_PROFILE_TYPE2 id_;
        LPCWSTR name_;
    };

    constexpr std::array profile_map = {
        ProfileMapElement{NET_FW_PROFILE2_DOMAIN, L"Domain"},
        ProfileMapElement{NET_FW_PROFILE2_PRIVATE, L"Private"},
        ProfileMapElement{NET_FW_PROFILE2_PUBLIC, L"Public"}};

    if (SUCCEEDED(fw_rule->get_Profiles(&profile_bitmask))) {
        // The returned bitmask can have more than 1 bit set if multiple
        // profiles
        //   are active or current at the same time
        for (const auto &[id, name] : profile_map) {
            if (profile_bitmask & id) {
                XLOG::l.i("Profile:  '{}'", wtools::ToUtf8(name));
            }
        }
    }
}
void DumpInterfaces(INetFwRule *fw_rule) {
    variant_t interface_array;
    variant_t interface_string;
    if (SUCCEEDED(fw_rule->get_Interfaces(&interface_array)) &&
        interface_array.vt != VT_EMPTY) {
        SAFEARRAY *safe_arr = interface_array.parray;
        for (long index = safe_arr->rgsabound->lLbound;
             index < static_cast<long>(safe_arr->rgsabound->cElements);
             index++) {
            SafeArrayGetElement(safe_arr, &index, &interface_string);
            XLOG::l.i("Interfaces:       '{}'",
                      wtools::ToUtf8(interface_string.bstrVal));
            interface_string.Clear();
        }
    }

    BSTR bstr_val;
    if (SUCCEEDED(fw_rule->get_InterfaceTypes(&bstr_val))) {
        XLOG::l.i("Interface Types:  '{}'", ToUtf8(bstr_val));
        ::SysFreeString(bstr_val);
    }
}

void DumpEnabled(INetFwRule *fw_rule) {
    VARIANT_BOOL fw_enabled;
    if (SUCCEEDED(fw_rule->get_Enabled(&fw_enabled))) {
        if (fw_enabled) {
            XLOG::l.i("Enabled:          '{}'",
                      wtools::ToUtf8(NET_FW_RULE_ENABLE_IN_NAME));
        } else {
            XLOG::l.i("Enabled:          '{}'",
                      wtools::ToUtf8(NET_FW_RULE_DISABLE_IN_NAME));
        }
    }
}

void DumpOther(INetFwRule *fw_rule) {
    BSTR bstr_val;
    VARIANT_BOOL fw_enabled;
    if (SUCCEEDED(fw_rule->get_Grouping(&bstr_val))) {
        XLOG::l.i("Grouping:         '{}'", ToUtf8(bstr_val));
        ::SysFreeString(bstr_val);
    }

    if (SUCCEEDED(fw_rule->get_EdgeTraversal(&fw_enabled))) {
        if (fw_enabled) {
            XLOG::l.i("Edge Traversal:   '{}'",
                      wtools::ToUtf8(NET_FW_RULE_ENABLE_IN_NAME));
        } else {
            XLOG::l.i("Edge Traversal:   '{}'",
                      wtools::ToUtf8(NET_FW_RULE_DISABLE_IN_NAME));
        }
    }
}

}  // namespace

// Output properties of a Firewall rule
// ABSOLUTE INTERNAL
// FROM MSDN
// MAY HAVE MEMORY LEAKS!!!!
INetFwRule *DumpFirewallRulesInCollection(INetFwRule *fw_rule) {
    XLOG::l.i("---------------------------------------------\n");

    DumpBaseInfo(fw_rule);
    DumpProtocol(fw_rule);
    DumpPorts(fw_rule);
    DumpIcmp(fw_rule);
    DumpIcmp(fw_rule);
    DumpAddresses(fw_rule);
    DumpProfileBitmask(fw_rule);
    DumpDirection(fw_rule);
    DumpAction(fw_rule);
    DumpInterfaces(fw_rule);
    DumpEnabled(fw_rule);
    DumpOther(fw_rule);

    return nullptr;  // continue enumeration
}  // namespace cma::fw

// Instantiate INetFwPolicy2
INetFwPolicy2 *WFCOMInitialize() {
    INetFwPolicy2 *net_fw_policy2 = nullptr;

    auto hr = ::CoCreateInstance(__uuidof(NetFwPolicy2), nullptr,
                                 CLSCTX_INPROC_SERVER, __uuidof(INetFwPolicy2),
                                 reinterpret_cast<void **>(&net_fw_policy2));

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
    if (fw_rule->get_Name(&rule_name) != 0) {
        return {};
    }
    ON_OUT_OF_SCOPE(::SysFreeString(rule_name));

    return rule_name != nullptr ? rule_name : std::optional<std::wstring>{};
}

std::optional<std::wstring> GetRuleAppName(INetFwRule *fw_rule) {
    BSTR app_name = nullptr;
    if (fw_rule->get_ApplicationName(&app_name) != 0) {
        return {};
    }
    ON_OUT_OF_SCOPE(::SysFreeString(app_name));

    return app_name != nullptr ? app_name : std::optional<std::wstring>{};
}

}  // namespace

bool CreateInboundRule(std::wstring_view rule_name,
                       std::wstring_view raw_app_name, int port) {
    const auto app_name = wtools::ToCanonical(raw_app_name);

    const Policy policy;

    auto *rules = policy.getRules();
    if (rules == nullptr) {
        return false;
    }

    const auto bit_mask = CorrectFirewallBitMask();

    auto *rule = CreateRule();

    // Populate the Firewall Rule object
    rule->put_Name(wtools::Bstr(rule_name).bstr());
    rule->put_Description(wtools::Bstr(kRuleDescription).bstr());
    rule->put_ApplicationName(wtools::Bstr(app_name).bstr());
    rule->put_Protocol(NET_FW_IP_PROTOCOL_TCP);
    rule->put_LocalPorts(
        wtools::Bstr(port == -1 ? L"*" : std::to_wstring(port)).bstr());
    rule->put_Direction(NET_FW_RULE_DIR_IN);
    rule->put_Grouping(wtools::Bstr(kRuleGroup).bstr());
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

    auto hr = rules->Remove(wtools::Bstr(rule_name).bstr());
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
    const auto random_int = rand();  // NOLINT

    std::wstring new_name{L"to_delete_"};
    new_name += std::to_wstring(random_int);

    return new_name;
}
}  // namespace

bool RemoveRule(std::wstring_view rule_name, std::wstring_view raw_app_name) {
    if (raw_app_name.empty()) {
        return RemoveRule(rule_name);
    }

    auto app_name = wtools::ToCanonical(raw_app_name);
    std::wstring new_name;

    // find a rule with rule_name and app_name
    auto *rule = ScanAllRules(
        [rule_name, app_name, &new_name](INetFwRule *fw_rule) -> INetFwRule * {
            if (fw_rule == nullptr) {
                return nullptr;  // continue enumeration
            }

            const auto name = GetRuleName(fw_rule);
            if (!name || rule_name != *name) {
                return nullptr;
            }

            const auto candidate_name = GetRuleAppName(fw_rule);
            if (!candidate_name || !tools::IsEqual(app_name, *candidate_name)) {
                return nullptr;
            }

            // we have found a rule to delete
            // unfortunately MS API has no possibility to delete this rule
            // so we rename this rule to the random rule_name and we will delete
            // rule by this random rule_name
            {
                new_name = GenerateRandomRuleName();
                fw_rule->put_Name(wtools::Bstr(new_name).bstr());
                XLOG::t("Rule '{}' renamed to '{}' for deletion",
                        wtools::ToUtf8(rule_name), wtools::ToUtf8(new_name));
                return fw_rule;  // found
            }
        });

    // in any case we have to clean
    if (rule != nullptr) {
        rule->Release();
    }
    if (!new_name.empty()) {
        XLOG::t("Removing Rule '{}' for exe '{}'", wtools::ToUtf8(rule_name),
                wtools::ToUtf8(app_name));
        return RemoveRule(new_name);
    }

    return false;
}

INetFwRule *FindRule(std::wstring_view rule_name,
                     std::wstring_view raw_app_name) {
    auto app_name = wtools::ToCanonical(raw_app_name);

    return ScanAllRules(
        [rule_name, app_name](INetFwRule *fw_rule) -> INetFwRule * {
            if (fw_rule == nullptr) {
                return nullptr;
            }

            const auto name = GetRuleName(fw_rule);
            if (!name || rule_name != *name) {
                return nullptr;
            }

            if (app_name.empty()) {
                return fw_rule;
            }

            const auto candidate_name = GetRuleAppName(fw_rule);
            if (candidate_name && tools::IsEqual(app_name, *candidate_name)) {
                return fw_rule;  // stop enumeration
            }

            return nullptr;
        });
}

int CountRules(std::wstring_view rule_name, std::wstring_view raw_app_name) {
    auto app_name = wtools::ToCanonical(raw_app_name);

    int count = 0;
    ScanAllRules(
        [rule_name, app_name, &count](INetFwRule *fw_rule) -> INetFwRule * {
            if (fw_rule == nullptr) {
                return nullptr;
            }

            const auto name = GetRuleName(fw_rule);

            if (!name || name != rule_name) {
                return nullptr;
            }

            if (app_name.empty()) {
                count++;
                return nullptr;
            }

            const auto candidate_name = GetRuleAppName(fw_rule);
            if (candidate_name && tools::IsEqual(app_name, *candidate_name)) {
                count++;
            }

            return nullptr;
        });

    return count;
}

INetFwRule *FindRule(std::wstring_view rule_name) {
    return ScanAllRules([rule_name](INetFwRule *fw_rule) -> INetFwRule * {
        if (fw_rule == nullptr) {
            return nullptr;
        }

        BSTR name = nullptr;
        if (fw_rule->get_Name(&name) != 0) {
            return nullptr;
        }

        ON_OUT_OF_SCOPE(::SysFreeString(name));
        return wcscmp(rule_name.data(), name) == 0 ? fw_rule : nullptr;
    });
}

}  // namespace cma::fw
