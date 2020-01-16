// wtools_user_control.h
//
// Windows Specific Tools
//
#pragma once

#ifndef wtools_user_control_h__
#define wtools_user_control_h__

#include <string>  // for wstring

// User Control namespace
namespace wtools::uc {

enum class Status { success, absent, exists, no_domain_service, error };
enum class FindMode { local, automatic };
class LdapControl {
public:
    LdapControl() {}
    Status chooseDomain(std::wstring_view server_name,
                        std::wstring_view domain_name);
    ~LdapControl();

    // User
    Status userAdd(std::wstring_view user_name, std::wstring_view pwd_string);
    Status userDel(std::wstring_view user_name);

    // indirectly tested
    Status changeUserPassword(std::wstring_view user_name,
                              std::wstring_view pwd_string);

    // Local Group
    Status localGroupAdd(std::wstring_view group_name,
                         std::wstring_view group_comment);
    Status localGroupDel(std::wstring_view group_name);

    // Group Member
    Status localGroupAddMembers(std::wstring_view group_name,
                                std::wstring_view user_name);
    Status localGroupDelMembers(std::wstring_view group_name,
                                std::wstring_view user_name);

    // this is trash to access old Windows API
    wchar_t* name() { return primary_dc_name_; }

    const wchar_t* name() const { return primary_dc_name_; }

private:
    wchar_t* primary_dc_name_ = nullptr;
};

}  // namespace wtools::uc

#endif  // wtools_user_control_h__
