// Windows Tools
#include "stdafx.h"

#include "wtools_user_control.h"

// WINDOWS STUFF
#if defined(_WIN32)
#define WIN32_LEAN_AND_MEAN

#include <lmaccess.h>
#include <lmapibuf.h>
#include <lmerr.h>

#pragma comment(lib, "netapi32.lib")
#endif

#include "logger.h"
#include "winerror.h"  // for ERROR_NO_SUCH_ALIAS, ERROR_ALIAS_EXISTS, ERROR_MEMBER_IN_ALIAS

namespace wtools {

namespace uc {

Status LdapControl::userAdd(std::wstring_view user_name,
                            std::wstring_view pwd_string) {
    USER_INFO_1 user_info;
    // Set up the USER_INFO_1 structure.
    user_info.usri1_name = const_cast<wchar_t*>(user_name.data());
    user_info.usri1_password = const_cast<wchar_t*>(pwd_string.data());
    user_info.usri1_priv = USER_PRIV_USER;

    wchar_t user_home_dir[] = L"";
    user_info.usri1_home_dir = user_home_dir;

    wchar_t user_comment[] = L"Temporary Check MK User";
    user_info.usri1_comment = user_comment;

    user_info.usri1_flags = UF_SCRIPT;

    wchar_t user_script_path[] = L"";
    user_info.usri1_script_path = user_script_path;
    unsigned long parm_err = 0;
    auto err = ::NetUserAdd(primary_dc_name_,            // PDC name
                            1,                           // level
                            (unsigned char*)&user_info,  // input buffer
                            &parm_err);                  // parameter in error

    switch (err) {
        case 0:
            XLOG::l.i("User successfully created.");
            setAsSpecialUser(user_name);
            return Status::success;
        case NERR_UserExists:
            XLOG::l.i("User already exists.");
            return Status::exists;
        default:
            XLOG::l("Error adding user: [{}]", err);
            return Status::error;
    }
}

// this function tested indirectly in runas (difficult top test)
Status LdapControl::changeUserPassword(std::wstring_view user_name,
                                       std::wstring_view pwd_string) {
    USER_INFO_1003 pwd_data;
    pwd_data.usri1003_password = const_cast<wchar_t*>(pwd_string.data());

    auto ret = ::NetUserSetInfo(primary_dc_name_, user_name.data(), 1003,
                                reinterpret_cast<BYTE*>(&pwd_data), nullptr);

    if (ret == NERR_Success) return Status::success;

    XLOG::l("Error setting user: [{}]", ret);
    return Status::error;
}

bool LdapControl::setAsSpecialUser(std::wstring_view user_name) {
    return SetRegistryValue(getSpecialUserRegistryPath(), user_name, 0u);
}

bool LdapControl::clearAsSpecialUser(std::wstring_view user_name) {
    return SetRegistryValue(getSpecialUserRegistryPath(), user_name, 1u);
}

Status LdapControl::userDel(std::wstring_view user_name) {
    auto err =
        ::NetUserDel(primary_dc_name_,                         // PDC name
                     const_cast<wchar_t*>(user_name.data()));  // user name

    switch (err) {
        case 0:
            clearAsSpecialUser(user_name);
            XLOG::l.i("User successfully removed.");
            return Status::success;
        case NERR_UserNotFound:
            XLOG::l.i("User already removed.");
            return Status::absent;
        default:
            XLOG::l("Error removing user: [{}]", err);
            return Status::error;
    }
}

static bool CheckGroupIsForbidden(std::wstring_view group_name) {
    using namespace std::literals::string_literals;
    static const std::wstring PredefinedeGroupsForbiddentoDelete[] = {
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

    return std::any_of(
        std::begin(PredefinedeGroupsForbiddentoDelete),
        std::end(PredefinedeGroupsForbiddentoDelete),
        // predicate:
        [group_name](std::wstring_view name) { return group_name == name; });
}

Status LdapControl::localGroupAdd(std::wstring_view group_name,
                                  std::wstring_view group_comment) {
    auto forbidden = CheckGroupIsForbidden(group_name);
    if (forbidden) {
        XLOG::d("Groups is '{}' predefined group", ConvertToUTF8(group_name));
        return Status::error;
    }

    LOCALGROUP_INFO_1 lg_info;
    lg_info.lgrpi1_name = const_cast<wchar_t*>(group_name.data());
    lg_info.lgrpi1_comment = const_cast<wchar_t*>(group_comment.data());

    unsigned long parm_err = 0;
    auto err = ::NetLocalGroupAdd(primary_dc_name_,          // PDC name
                                  1,                         // level
                                  (unsigned char*)&lg_info,  // input buffer
                                  &parm_err);  // parameter in error

    switch (err) {
        case 0:
            XLOG::l.i("Local group successfully created.");
            return Status::success;
        case ERROR_ALIAS_EXISTS:
        case NERR_GroupExists:
            XLOG::l.i("Local group already exists.");
            return Status::exists;
        default:
            XLOG::l("Error adding local group: [{}]", err);
            return Status::error;
    }
}

Status LdapControl::localGroupDel(std::wstring_view group_name) {
    auto forbidden = CheckGroupIsForbidden(group_name);
    if (forbidden) {
        XLOG::d("Groups is '{}' predefined group", ConvertToUTF8(group_name));
        return Status::error;
    }

    auto g_name = const_cast<wchar_t*>(group_name.data());

    auto err = ::NetLocalGroupDel(primary_dc_name_,  // PDC name
                                  g_name);

    switch (err) {
        case 0:
            XLOG::l.i("Local group successfully removed");
            return Status::success;
        case NERR_GroupNotFound:
            XLOG::l.i("Local group already removed");
            return Status::absent;
        default:
            XLOG::l("Error removing local group: [{}]", err);
            return Status::error;
    }
}

Status LdapControl::localGroupAddMembers(std::wstring_view group_name,
                                         std::wstring_view user_name) {
    LOCALGROUP_MEMBERS_INFO_3 lg_members;
    lg_members.lgrmi3_domainandname = const_cast<wchar_t*>(user_name.data());

    auto err = ::NetLocalGroupAddMembers(
        primary_dc_name_,                               // PDC name
        const_cast<wchar_t*>(group_name.data()),        // group name
        3,                                              // name
        reinterpret_cast<unsigned char*>(&lg_members),  // buffer
        1);                                             // count

    switch (err) {
        case 0:
            XLOG::l.i("User successfully added to local group.");
            return Status::success;

        case ERROR_MEMBER_IN_ALIAS:
            XLOG::l.i("User already in local group.");
            return Status::exists;

        default:
            XLOG::l("Error adding user to local group: [{}]", err);
            return Status::error;
    }
}

Status LdapControl::localGroupDelMembers(std::wstring_view group_name,
                                         std::wstring_view user_name) {
    LOCALGROUP_MEMBERS_INFO_3 lg_members;
    lg_members.lgrmi3_domainandname = const_cast<wchar_t*>(user_name.data());

    auto err = NetLocalGroupDelMembers(
        primary_dc_name_,                               // PDC name
        const_cast<wchar_t*>(group_name.data()),        // group name
        3,                                              // name
        reinterpret_cast<unsigned char*>(&lg_members),  // buffer
        1);                                             // count

    switch (err) {
        case 0:
            XLOG::l.i("User successfully removed from local group.");
            return Status::success;
        case ERROR_MEMBER_NOT_IN_ALIAS:
            XLOG::l.i("User already removed from local group.");
            return Status::absent;
        default:
            XLOG::l("Error removing user from local group: [{}]", err);
            return Status::error;
    }
}

Status LdapControl::chooseDomain(std::wstring_view server_name,
                                 std::wstring_view domain_name) {
    if (primary_dc_name_) {
        ::NetApiBufferFree(static_cast<void*>(primary_dc_name_));
        primary_dc_name_ = nullptr;
    }
    // First get the name of the primary domain controller.
    // Be sure to free the returned buffer.
    auto err = ::NetGetDCName(
        server_name.data(),  // local computer
        domain_name.data(),  // domain name
        reinterpret_cast<unsigned char**>(&primary_dc_name_));  // returned PDC

    if (err == 0) return Status::success;
    if (err == NERR_ServiceNotInstalled || err == NERR_DCNotFound) {
        XLOG::l("Error getting DC name: [{}]", err);
        return Status::no_domain_service;
    }

    XLOG::l("Error getting DC name: [{}]", err);
    return Status::error;
}

LdapControl::~LdapControl() {
    if (primary_dc_name_)
        ::NetApiBufferFree(static_cast<void*>(primary_dc_name_));
}

}  // namespace uc

}  // namespace wtools
