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
    Status chooseDomain(std::wstring_view domain, std::wstring_view name);
    ~LdapControl();

    // User
    Status UserAdd(std::wstring_view user_name, std::wstring_view pwd_string);
    Status UserDel(std::wstring_view user_name);

    // Local Group
    Status LocalGroupAdd(std::wstring_view group_name,
                         std::wstring_view group_comment);
    Status LocalGroupDel(std::wstring_view group_name);

    // Group Member
    Status LocalGroupAddMembers(std::wstring_view group_name,
                                std::wstring_view user_name);
    Status LocalGroupDelMembers(std::wstring_view group_name,
                                std::wstring_view user_name);

    // this is trash to access old Windows API
    wchar_t* name() { return primary_dc_name_; }

    const wchar_t* name() const { return primary_dc_name_; }

private:
    wchar_t* primary_dc_name_ = nullptr;
};

}  // namespace wtools::uc

#endif  // wtools_user_control_h__
