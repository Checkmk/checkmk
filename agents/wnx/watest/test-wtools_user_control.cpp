// test-wtools.cpp
// windows mostly

#include "pch.h"

#include "common/wtools_user_control.h"
#include "logger.h"

namespace wtools::uc {  // to become friendly for cma::cfg classes

//
//
static const int counter = 0;

TEST(WtoolsUserControl, Base) {
    LdapControl lc;
    ASSERT_TRUE(lc.name() == nullptr);
    auto ret = lc.chooseDomain(L"WORKGROUP", L"SERG-DELL");
    if (ret == Status::no_domain_service) {
        XLOG::SendStringToStdio("No Domain Controller - no testing",
                                XLOG::Colors::yellow);
        return;
    }
    ASSERT_TRUE(ret == Status::success);
}

TEST(WtoolsUserControl, AddDeleteUser) {
    LdapControl lc;
    std::wstring_view u = L"x_test_user";
    lc.UserDel(u);
    ON_OUT_OF_SCOPE(lc.UserDel(u));
    EXPECT_EQ(Status::absent, lc.UserDel(u));
    EXPECT_EQ(Status::success, lc.UserAdd(u, L"xufdrgebd_1"));
    EXPECT_EQ(Status::exists, lc.UserAdd(u, L"xufdrgebd_1"));
    EXPECT_EQ(Status::success, lc.UserDel(u));
    EXPECT_EQ(Status::absent, lc.UserDel(u));
}

TEST(WtoolsUserControl, AddDeleteUserToUsers) {
    LdapControl lc;
    std::wstring_view g = L"Users";
    std::wstring_view u = L"x_user_name";
    ASSERT_EQ(Status::success, lc.UserAdd(u, L"aaaaasxwxwwxwecfwecwe"));
    EXPECT_EQ(Status::success, lc.LocalGroupAddMembers(g, u));
    EXPECT_EQ(Status::success, lc.LocalGroupDelMembers(g, u));
    EXPECT_EQ(Status::absent, lc.LocalGroupDelMembers(g, u));

    EXPECT_EQ(Status::success, lc.LocalGroupAddMembers(g, u));
    EXPECT_EQ(Status::error, lc.LocalGroupDel(g));
    ASSERT_EQ(Status::success, lc.UserDel(u));
    EXPECT_EQ(Status::error, lc.LocalGroupDel(g));
}

TEST(WtoolsUserControl, AddDeleteCheckGroup) {
    LdapControl lc;
    std::wstring_view g = L"x_test_group";
    std::wstring_view c = L"Check MK Testing Group";
    lc.LocalGroupDel(g);
    ON_OUT_OF_SCOPE(lc.LocalGroupDel(g));
    EXPECT_EQ(Status::absent, lc.LocalGroupDel(g));
    EXPECT_EQ(Status::success, lc.LocalGroupAdd(g, c));
    EXPECT_EQ(Status::exists, lc.LocalGroupAdd(g, c));
    EXPECT_EQ(Status::success, lc.LocalGroupDel(g));
    EXPECT_EQ(Status::absent, lc.LocalGroupDel(g));
}

TEST(WtoolsUserControl, AddDeleteCheckForbiddenGroup) {
    using namespace std::literals::string_literals;
    LdapControl lc;
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
    for (auto& g : groups) {
        //
        EXPECT_EQ(Status::error, lc.LocalGroupDel(g));
    }
}

TEST(WtoolsUserControl, AddDeleteMembers) {
    LdapControl lc;
    std::wstring_view g = L"x_test_group";
    std::wstring_view u = L"x_user_name";
    std::wstring_view c = L"Check MK Testing Group";
    lc.LocalGroupDel(g);
    ON_OUT_OF_SCOPE(lc.UserDel(u); lc.LocalGroupDel(g));

    EXPECT_EQ(Status::absent, lc.LocalGroupDel(g));
    EXPECT_EQ(Status::error, lc.LocalGroupAddMembers(g, u));

    ASSERT_EQ(Status::success, lc.LocalGroupAdd(g, c));
    EXPECT_EQ(Status::error, lc.LocalGroupAddMembers(g, u));
    ASSERT_EQ(Status::success, lc.UserAdd(u, L"aaaaasxwxwwxwecfwecwe"));
    EXPECT_EQ(Status::success, lc.LocalGroupAddMembers(g, u));

    EXPECT_EQ(Status::success, lc.LocalGroupDelMembers(g, u));
    EXPECT_EQ(Status::absent, lc.LocalGroupDelMembers(g, u));

    EXPECT_EQ(Status::success, lc.LocalGroupAddMembers(g, u));
    EXPECT_EQ(Status::success, lc.LocalGroupDel(g));
    ASSERT_EQ(Status::success, lc.UserDel(u));
    EXPECT_EQ(Status::absent, lc.LocalGroupDel(g));
}

}  // namespace wtools::uc
