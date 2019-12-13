// wtools_runas.h
//
// Windows Runas Tools
//
#pragma once

#ifndef wtools_runas_h__
#define wtools_runas_h__
#include <windef.h>

#include <string>

namespace wtools::runas {
// windows like API
std::tuple<DWORD, HANDLE, HANDLE> RunAsJob(
    std::wstring_view user_name,   // serg
    std::wstring_view password,    // my_pass
    std::wstring_view command,     // "c.bat"
    BOOL inherit_handles = FALSE,  // not optimal, but default
    HANDLE stdio_handle = 0,       // when we want to catch output
    HANDLE stderr_handle = 0,      // same
    DWORD creation_flags = 0,      // never checked this
    DWORD start_flags = 0) noexcept;

}  // namespace wtools::runas
#endif  // wtools_runas_h__
