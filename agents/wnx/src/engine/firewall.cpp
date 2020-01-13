// Windows Tools

#include "stdafx.h"

#include "firewall.h"

#include <comutil.h>
#include <netfw.h>

#include <filesystem>

#include "common/wtools.h"
#include "logger.h"
#include "tools/_misc.h"

#if defined(WIN32)
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
    auto hr = CoCreateInstance(__uuidof(NetFwRule), NULL, CLSCTX_INPROC_SERVER,
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
        XLOG::l.i("CoCreateInstance for INetFwPolicy2 failed: [{:#X}]", hr);
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
    if (policy_ == nullptr) return -1;

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

class Bstr {
public:
    Bstr(const Bstr &) = delete;
    Bstr(Bstr &&) = delete;
    Bstr &operator=(const Bstr &) = delete;
    Bstr &operator=(Bstr &&) = delete;

    Bstr(std::wstring_view str) { data_ = ::SysAllocString(str.data()); }
    ~Bstr() { ::SysFreeString(data_); }
    operator BSTR() { return data_; }

public:
    BSTR data_;
};

void Check(BSTR bstr) {
    //
    XLOG::l("x");
}

INetFwRule *ScanAllRules(std::function<INetFwRule *(INetFwRule *)> processor) {
    Policy p;
    auto rules = p.getRules();
    if (rules == nullptr) return nullptr;

    // Obtain the number of Firewall rules
    long rule_count = p.getRulesCount();
    if (rule_count == 0) return 0;

    XLOG::t.i("Firewall Rules count is [{}]", rule_count);

    auto variant = p.getEnum();
    if (variant == nullptr) return nullptr;
    ON_OUT_OF_SCOPE(variant->Release());

    ULONG cFetched = 0;
    VARIANT var;
    ::VariantClear(&var);

    while (1) {
        auto hr = variant->Next(1, &var, &cFetched);
        ON_OUT_OF_SCOPE(::VariantClear(&var););

        if (S_FALSE == hr) break;
        if (!SUCCEEDED(hr)) break;
        hr = ::VariantChangeType(&var, &var, 0, VT_DISPATCH);
        if (!SUCCEEDED(hr)) break;

        INetFwRule *rule = nullptr;

        auto dispatch = (V_DISPATCH(&var));
        hr = dispatch->QueryInterface(__uuidof(INetFwRule),
                                      reinterpret_cast<void **>(&rule));
        if (!SUCCEEDED(hr)) break;
        if (rule == nullptr) continue;

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
        return wtools::ConvertToUTF8(bstr);
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
                          wtools::ConvertToUTF8(NET_FW_IP_PROTOCOL_TCP_NAME));
                break;

            case NET_FW_IP_PROTOCOL_UDP:

                XLOG::l.i("IP Protocol:      '{}'",
                          wtools::ConvertToUTF8(NET_FW_IP_PROTOCOL_UDP_NAME));
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
                          wtools::ConvertToUTF8(NET_FW_RULE_DIR_IN_NAME));
                break;

            case NET_FW_RULE_DIR_OUT:

                XLOG::l.i("Direction:        '{}'",
                          wtools::ConvertToUTF8(NET_FW_RULE_DIR_OUT_NAME));
                break;

            default:

                break;
        }
    }

    if (SUCCEEDED(fw_rule->get_Action(&fwAction))) {
        switch (fwAction) {
            case NET_FW_ACTION_BLOCK:

                XLOG::l.i("Action:           '{}'",
                          wtools::ConvertToUTF8(NET_FW_RULE_ACTION_BLOCK_NAME));
                break;

            case NET_FW_ACTION_ALLOW:

                XLOG::l.i("Action:           '{}'",
                          wtools::ConvertToUTF8(NET_FW_RULE_ACTION_ALLOW_NAME));
                break;

            default:

                break;
        }
    }

    if (SUCCEEDED(fw_rule->get_Interfaces(&InterfaceArray))) {
        if (InterfaceArray.vt != VT_EMPTY) {
            SAFEARRAY *pSa = nullptr;

            pSa = InterfaceArray.parray;

            for (long index = pSa->rgsabound->lLbound;
                 index < (long)pSa->rgsabound->cElements; index++) {
                SafeArrayGetElement(pSa, &index, &InterfaceString);
                XLOG::l.i("Interfaces:       '{}'",
                          wtools::ConvertToUTF8((BSTR)InterfaceString.bstrVal));
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
                      wtools::ConvertToUTF8(NET_FW_RULE_ENABLE_IN_NAME));
        } else {
            XLOG::l.i("Enabled:          '{}'",
                      wtools::ConvertToUTF8(NET_FW_RULE_DISABLE_IN_NAME));
        }
    }

    if (SUCCEEDED(fw_rule->get_Grouping(&bstrVal))) {
        XLOG::l.i("Grouping:         '{}'", to_utf8(bstrVal));
        ::SysFreeString(bstrVal);
    }

    if (SUCCEEDED(fw_rule->get_EdgeTraversal(&bEnabled))) {
        if (bEnabled) {
            XLOG::l.i("Edge Traversal:   '{}'",
                      wtools::ConvertToUTF8(NET_FW_RULE_ENABLE_IN_NAME));
        } else {
            XLOG::l.i("Edge Traversal:   '{}'",
                      wtools::ConvertToUTF8(NET_FW_RULE_DISABLE_IN_NAME));
        }
    }

    return nullptr;  // continue enumeration
}

// Instantiate INetFwPolicy2
INetFwPolicy2 *WFCOMInitialize() {
    INetFwPolicy2 *pNetFwPolicy2 = nullptr;

    auto hr =
        CoCreateInstance(__uuidof(NetFwPolicy2), NULL, CLSCTX_INPROC_SERVER,
                         __uuidof(INetFwPolicy2), (void **)&pNetFwPolicy2);

    if (FAILED(hr)) {
        XLOG::l.i("CoCreateInstance for INetFwPolicy2 failed: [{:#X}]", hr);
        return nullptr;
    }

    return pNetFwPolicy2;
}

// #TODO: do we need it in the cma::tools?
// #IMPORTANT: this function is tested  only indirectly
static std::wstring ToCanonical(std::wstring_view raw_app_name) {
    namespace fs = std::filesystem;
    constexpr int buf_size = 16 * 1024 + 1;
    auto buf = std::make_unique<wchar_t[]>(buf_size);
    std::error_code ec;
    auto resulting_size =
        ::ExpandEnvironmentStringsW(raw_app_name.data(), buf.get(), buf_size);

    auto p =
        fs::weakly_canonical(resulting_size > 0 ? buf.get() : raw_app_name, ec);

    if (ec.value() == 0) return p.wstring();

    XLOG::l.i(
        "Path '{}' cannot be canonical: probably based on the environment variables",
        wtools::ConvertToUTF8(raw_app_name));

    return std::wstring(raw_app_name);
}

bool CreateInboundRule(std::wstring_view rule_name,
                       std::wstring_view raw_app_name, int port) {
    auto app_name = ToCanonical(raw_app_name);
    // Retrieve INetFwPolicy2
    Policy p;
    // Retrieve INetFwRules
    auto rules = p.getRules();
    if (rules == nullptr) return false;

    // Retrieve Current Profiles bitmask
    long bit_mask = p.getCurrentProfileTypes();
    if (bit_mask == -1) return false;

    // When possible we avoid adding firewall rules to the Public profile.
    // If Public is currently active and it is not the only active profile, we
    // remove it from the bitmask
    if ((bit_mask & NET_FW_PROFILE2_PUBLIC) &&
        (bit_mask != NET_FW_PROFILE2_PUBLIC)) {
        bit_mask ^= NET_FW_PROFILE2_PUBLIC;
    }

    auto rule = CreateRule();

    // Populate the Firewall Rule object
    rule->put_Name(Bstr(rule_name));
    rule->put_Description(Bstr(kRuleDescription));
    rule->put_ApplicationName(Bstr(app_name));
    rule->put_Protocol(NET_FW_IP_PROTOCOL_TCP);
    rule->put_LocalPorts(Bstr(port == -1 ? L"*" : std::to_wstring(port)));
    rule->put_Direction(NET_FW_RULE_DIR_IN);
    rule->put_Grouping(Bstr(kRuleGroup));
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

static std::optional<std::wstring> GetRuleName(INetFwRule *fw_rule) {
    BSTR rule_name = nullptr;
    auto ret = fw_rule->get_Name(&rule_name);
    if (ret != 0) return {};
    ON_OUT_OF_SCOPE(SysFreeString(rule_name));

    if (rule_name == nullptr) return {};

    return rule_name;
}

static std::optional<std::wstring> GetRuleAppName(INetFwRule *fw_rule) {
    BSTR app_name = nullptr;
    auto ret = fw_rule->get_ApplicationName(&app_name);
    if (ret != 0) return {};
    ON_OUT_OF_SCOPE(SysFreeString(app_name));

    if (app_name == nullptr) return {};

    return app_name;
}

bool RemoveRule(std::wstring_view rule_name) {
    // Retrieve INetFwPolicy2
    Policy p;
    // Retrieve INetFwRules
    auto rules = p.getRules();
    if (rules == nullptr) return false;

    auto hr = rules->Remove(Bstr(rule_name));
    if (FAILED(hr)) {
        XLOG::l("Firewall Rule REMOVE failed: [{:#X}]", hr);
        return false;
    }

    return true;
}

std::wstring GenerateRandomRuleName() {
    static bool run_once = false;
    if (!run_once) {
        run_once = true;
        srand(static_cast<unsigned int>(time(nullptr)));
    }
    auto random_int = rand();
    std::wstring new_name = L"to_delete_";
    new_name += std::to_wstring(random_int);

    return new_name;
}

bool RemoveRule(std::wstring_view name, std::wstring_view raw_app_name) {
    if (raw_app_name.empty()) return RemoveRule(name);

    auto app_name = raw_app_name.empty() ? L"" : ToCanonical(raw_app_name);
    std::wstring new_name;

    // find a rule with name and app_name
    auto rule = ScanAllRules(
        [name, app_name, &new_name](INetFwRule *fw_rule) -> INetFwRule * {
            if (fw_rule == nullptr) return nullptr;  // continue enumeration

            {
                auto rule_name = GetRuleName(fw_rule);
                if (!rule_name || wcscmp(name.data(), rule_name->c_str()))
                    return nullptr;
            }

            {
                auto candidate_name = GetRuleAppName(fw_rule);
                if (!candidate_name) return nullptr;

                if (!cma::tools::IsEqual(app_name, *candidate_name))
                    return nullptr;

                // we have found a rule to delete
                // unfortunately MS API has no possibility to delete this rule
                // so we rename this rule to the random name and we will delete
                // rule by this random name
                {
                    new_name = GenerateRandomRuleName();
                    fw_rule->put_Name(Bstr(new_name));
                    XLOG::t("Rule '{}' renamed to '{}' for deletion",
                            wtools::ConvertToUTF8(name),
                            wtools::ConvertToUTF8(new_name));
                    return fw_rule;  // found
                }
            }
        });

    // in any case we have to clean
    if (rule) rule->Release();
    if (!new_name.empty()) {
        XLOG::t("Removing Rule '{}' for exe '{}'", wtools::ConvertToUTF8(name),
                wtools::ConvertToUTF8(app_name));
        return RemoveRule(new_name);
    }

    return false;
}

INetFwRule *FindRule(std::wstring_view name, std::wstring_view raw_app_name) {
    auto app_name = raw_app_name.empty() ? L"" : ToCanonical(raw_app_name);

    return ScanAllRules([name, app_name](INetFwRule *fw_rule) -> INetFwRule * {
        if (fw_rule == nullptr) return nullptr;  // continue enumeration

        {
            auto rule_name = GetRuleName(fw_rule);
            if (!rule_name) return nullptr;

            if (wcscmp(name.data(), rule_name->c_str())) return nullptr;
        }

        if (app_name.empty()) return fw_rule;

        {
            auto candidate_name = GetRuleAppName(fw_rule);
            if (!candidate_name) return nullptr;

            if (cma::tools::IsEqual(app_name, *candidate_name))
                return fw_rule;  // stop enumeration

            return nullptr;
        }
    });
}

int CountRules(std::wstring_view name, std::wstring_view raw_app_name) {
    auto app_name = raw_app_name.empty() ? L"" : ToCanonical(raw_app_name);

    int count = 0;
    ScanAllRules([name, app_name, &count](INetFwRule *fw_rule) -> INetFwRule * {
        if (fw_rule == nullptr) return nullptr;

        {
            auto rule_name = GetRuleName(fw_rule);
            if (!rule_name) return nullptr;

            if (wcscmp(name.data(), rule_name->c_str())) return nullptr;
        }

        if (app_name.empty()) count++;

        {
            auto candidate_name = GetRuleAppName(fw_rule);
            if (!candidate_name) return nullptr;

            if (cma::tools::IsEqual(app_name, *candidate_name)) count++;
            return nullptr;
        }
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
#endif
