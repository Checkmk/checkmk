// test-wtools.cpp
// windows mostly

#include "pch.h"

#include <Ntsecapi.h>

#include "common/wtools_user_control.h"
#include "logger.h"

namespace wtools::uc {  // to become friendly for cma::cfg classes

//
//
static const int counter = 0;

// List of all domains!!!
// This is #REFERENCE
NTSTATUS PrintDomainName() {
    LSA_HANDLE policy;

    static LSA_OBJECT_ATTRIBUTES oa = {sizeof(oa)};

    auto status = LsaOpenPolicy(0, &oa, POLICY_VIEW_LOCAL_INFORMATION, &policy);

    if (!LSA_SUCCESS(status)) return status;
    ON_OUT_OF_SCOPE(LsaClose(policy));

    // I do not know why we use union
    union {
        PPOLICY_DNS_DOMAIN_INFO ppddi;
        PPOLICY_ACCOUNT_DOMAIN_INFO ppadi;
    };

    status = LsaQueryInformationPolicy(policy, PolicyDnsDomainInformation,
                                       (void **)&ppddi);

    if (!LSA_SUCCESS(status)) return status;

    if (ppddi->Sid) {
        XLOG::l("DnsDomainName: '{}'",
                wtools::ToUtf8(ppddi->DnsDomainName.Buffer));
    } else {
        XLOG::l("'{}': not domain controller !!",
                wtools::ToUtf8(ppddi->Name.Buffer));
        status = -1;
    }

    LsaFreeMemory(ppddi);
    if (0 <= status) return status;

    if (LSA_SUCCESS(
            status = LsaQueryInformationPolicy(
                policy, PolicyAccountDomainInformation, (void **)&ppadi))) {
        XLOG::l("DomainName: '{}'", wtools::ToUtf8(ppadi->DomainName.Buffer));
        LsaFreeMemory(ppadi);
    }

    return status;
}

TEST(WtoolsUserControl, Base) {
    LdapControl lc;
    ASSERT_TRUE(lc.name() == nullptr);
    ASSERT_EQ(
        lc.getSpecialUserRegistryPath(),
        LR"(SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon\SpecialAccounts\UserList)");
}

TEST(WtoolsUserControl, DISABLED_Base) {
    LdapControl lc;
    auto ret = lc.chooseDomain(L"SERG-DELL", L"SERG-DELL");
    if (ret == Status::no_domain_service) {
        XLOG::SendStringToStdio("No Domain Controller - no testing\n",
                                XLOG::Colors::yellow);

        return;
    }
    ASSERT_TRUE(ret == Status::success);
}

TEST(WtoolsUserControl, AddDeleteUser) {
    LdapControl lc;
    std::wstring_view u = L"x_test_user";
    lc.userDel(u);
    ON_OUT_OF_SCOPE(lc.userDel(u));
    EXPECT_EQ(Status::absent, lc.userDel(u));
    EXPECT_EQ(Status::success, lc.userAdd(u, L"Xufdrgebd 1"));
    EXPECT_EQ(Status::exists, lc.userAdd(u, L"Xufdrgebd 1"));
    EXPECT_EQ(Status::success, lc.userDel(u));
    EXPECT_EQ(Status::absent, lc.userDel(u));
}

TEST(WtoolsUserControl, AddDeleteUserToUsers) {
    LdapControl lc;
    auto g = wtools::SidToName(L"S-1-5-32-545", SidTypeGroup);
    std::wstring_view u = L"x_user_name";
    ASSERT_EQ(Status::success, lc.userAdd(u, L"Aaaasxwxwwxwecfwecwe 1"));
    EXPECT_EQ(Status::success, lc.localGroupAddMembers(g, u));
    EXPECT_EQ(Status::success, lc.localGroupDelMembers(g, u));
    EXPECT_EQ(Status::absent, lc.localGroupDelMembers(g, u));

    EXPECT_EQ(Status::success, lc.localGroupAddMembers(g, u));
    EXPECT_EQ(Status::error, lc.localGroupDel(g));
    ASSERT_EQ(Status::success, lc.userDel(u));
    EXPECT_EQ(Status::error, lc.localGroupDel(g));
}

TEST(WtoolsUserControl, AddDeleteCheckGroup) {
    LdapControl lc;
    std::wstring_view g = L"x_test_group";
    std::wstring_view c = L"Check MK Testing Group";
    lc.localGroupDel(g);
    ON_OUT_OF_SCOPE(lc.localGroupDel(g));
    EXPECT_EQ(Status::absent, lc.localGroupDel(g));
    EXPECT_EQ(Status::success, lc.localGroupAdd(g, c));
    EXPECT_EQ(Status::exists, lc.localGroupAdd(g, c));
    EXPECT_EQ(Status::success, lc.localGroupDel(g));
    EXPECT_EQ(Status::absent, lc.localGroupDel(g));
}

TEST(WtoolsUserControl, AddDeleteCheckForbiddenGroupIntegration) {
    using namespace std::literals::string_literals;
    LdapControl lc;
    if (wtools::SidToName(L"S-1-5-32-545", SidTypeGroup) != L"Users") {
        GTEST_SKIP() << "This test is only suitable for English Windows";
        return;
    }
    static const std::wstring groups[] = {
        L"Access Control Assistance Operators"s,
        L"Administrators"s,
        L"Backup Operators"s,
        L"Cryptographic Operators"s,
        L"Device Owners"s,
        L"Distributed COM Users"s,
        L"Event Log Readers"s,
        L"Guests"s,
        L"Hyper-V Administrators"s,
        L"IIS_IUSRS"s,
        L"Network Configuration Operators"s,
        L"Performance Log Users"s,
        L"Performance Monitor Users"s,
        L"Power Users"s,
        L"Remote Desktop Users"s,
        L"Remote Management Users"s,
        L"Replicator"s,
        L"System Managed Accounts Group"s,
        L"Users"s};

    for (auto &g : groups) {
        //
        EXPECT_EQ(Status::error, lc.localGroupDel(g)) << "Missing group: " << g;
    }
}

TEST(WtoolsUserControl, AddDeleteMembers) {
    LdapControl lc;
    std::wstring_view g = L"x_test_group";
    std::wstring_view u = L"x_user_name";
    std::wstring_view c = L"Check MK Testing Group";
    lc.localGroupDel(g);
    ON_OUT_OF_SCOPE(lc.userDel(u); lc.localGroupDel(g));

    EXPECT_EQ(Status::absent, lc.localGroupDel(g));
    EXPECT_EQ(Status::error, lc.localGroupAddMembers(g, u));

    ASSERT_EQ(Status::success, lc.localGroupAdd(g, c));
    EXPECT_EQ(Status::error, lc.localGroupAddMembers(g, u));
    ASSERT_EQ(Status::success, lc.userAdd(u, L"Aaaaasxwxwwxwecfwecwe 1"));
    EXPECT_EQ(Status::success, lc.localGroupAddMembers(g, u));

    EXPECT_EQ(Status::success, lc.localGroupDelMembers(g, u));
    EXPECT_EQ(Status::absent, lc.localGroupDelMembers(g, u));

    EXPECT_EQ(Status::success, lc.localGroupAddMembers(g, u));
    EXPECT_EQ(Status::success, lc.localGroupDel(g));
    ASSERT_EQ(Status::success, lc.userDel(u));
    EXPECT_EQ(Status::absent, lc.localGroupDel(g));
}

TEST(WtoolsUserControl, SpecialUsers) {
    auto path = LdapControl::getSpecialUserRegistryPath();
    ASSERT_EQ(
        path,
        LR"(SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon\SpecialAccounts\UserList)");

    constexpr std::wstring_view name = L"cmk_unit_test_user";
    constexpr uint32_t weird_value = 103'456'789u;
    ASSERT_TRUE(LdapControl::setAsSpecialUser(name));
    ON_OUT_OF_SCOPE(wtools::DeleteRegistryValue(path, name));
    auto value = wtools::GetRegistryValue(path, name, weird_value);
    EXPECT_EQ(value, 0);
    EXPECT_TRUE(LdapControl::clearAsSpecialUser(name));
    value = wtools::GetRegistryValue(path, name, weird_value);
    EXPECT_EQ(value, 1);
}

}  // namespace wtools::uc
