// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2017             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

// C++ cross platform RAII support
#pragma once
#if !defined(___RAII_H)
#define ___RAII_H
// **********************************************************
// ON_OUT_OF_SCOPE: Usage example
// NOTE 1: This is a SUPPLEMENT for full-featured RAAI.
// NOTE 2: Do not overuse
// 1.
// FILE * fp = fopen("tmp.txt", "w");
// ON_OUT_OF_SCOPE( { puts("close file now"); if (fp) fclose(fp); } );
// 2.
// auto tmp_data  = new char[10000];
// ON_OUT_OF_SCOPE( delete tmp_data; );
// **********************************************************
#if !defined ON_OUT_OF_SCOPE
namespace cma {
template <typename T>
struct InternalScopeGuard {
    T deleter_;
    InternalScopeGuard(T deleter) : deleter_(deleter) {}
    ~InternalScopeGuard() { deleter_(); }
};
}  // namespace cma
#define UNI_NAME(name, line) name##line

#define ON_OUT_OF_SCOPE_2(lambda_body, line)                           \
    auto UNI_NAME(deleter_lambda_, line) = [&]() { lambda_body; };     \
    cma::InternalScopeGuard<decltype(UNI_NAME(deleter_lambda_, line))> \
        UNI_NAME(scope_guard_, line)(UNI_NAME(deleter_lambda_, line));

#define ON_OUT_OF_SCOPE(lambda_body) ON_OUT_OF_SCOPE_2(lambda_body, __LINE__)
#endif

#if !defined CMK_AUTO_LOCK
#include <mutex>
// CMK_AUTO_LOCK Usage example:
// {
//    CMK_AUTO_LOCK(your_lock_for_count);
//    count_++;
// }
#define CMK_AUTO_LOCK(Mutex) \
    std::lock_guard<decltype(Mutex)> Mutex##CmkAutoLock(Mutex);
#endif

#endif  // ___RAAI_H
