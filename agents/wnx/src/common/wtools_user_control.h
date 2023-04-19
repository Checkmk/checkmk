// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// wtools_user_control.h
//
// Windows Specific Tools
//
#pragma once

#ifndef WTOOLS_USER_CONTROL_H
#define WTOOLS_USER_CONTROL_H

#include <string>  // for wstring

// User Control namespace
namespace wtools::uc {

enum class Status { success, absent, exists, no_domain_service, error };
enum class FindMode { local, automatic };
class LdapControl {
public:
    LdapControl() = default;
    LdapControl(const LdapControl &) = delete;
    LdapControl &operator=(const LdapControl &) = delete;
    LdapControl(LdapControl &&) = delete;
    LdapControl &operator=(LdapControl &&) = delete;

    Status chooseDomain(std::wstring_view server_name,
                        std::wstring_view domain_name);
    ~LdapControl();

    // User
    [[nodiscard]] Status userAdd(std::wstring_view user_name,
                                 std::wstring_view pwd_string) const noexcept;
    [[maybe_unused]] Status userDel(
        std::wstring_view user_name) const noexcept;  // NOLINT

    // indirectly tested
    [[nodiscard]] Status changeUserPassword(std::wstring_view user_name,
                                            std::wstring_view pwd_string) const;

    // Local Group
    [[nodiscard]] Status localGroupAdd(std::wstring_view group_name,
                                       std::wstring_view group_comment) const;
    [[maybe_unused]] Status localGroupDel(
        std::wstring_view group_name) const;  // NOLINT

    // Group Member
    [[nodiscard]] Status localGroupAddMembers(
        std::wstring_view group_name, std::wstring_view user_name) const;
    [[nodiscard]] Status localGroupDelMembers(
        std::wstring_view group_name, std::wstring_view user_name) const;

    // this is trash to access old Windows API
    wchar_t *name() { return primary_dc_name_; }

    [[nodiscard]] const wchar_t *name() const { return primary_dc_name_; }

    static bool setAsSpecialUser(std::wstring_view user_name);
    static bool clearAsSpecialUser(std::wstring_view user_name);
    static constexpr std::wstring_view getSpecialUserRegistryPath() noexcept {
        constexpr std::wstring_view path =
            LR"(SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon\SpecialAccounts\UserList)";
        return path;
    }

private:
    wchar_t *primary_dc_name_ = nullptr;
};

}  // namespace wtools::uc

#endif  // WTOOLS_USER_CONTROL_H
