// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
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

#ifndef mk_String_h
#define mk_String_h

#include "config.h" // IWYU pragma: keep
#include <stdio.h>
#include <limits>
#include <string>

// Some missing functions from  C++11's <string>

namespace mk {

template <typename T>
std::string to_string_helper(const char *format, T value)
{
    char buf[std::numeric_limits<T>::max_exponent10 == 0
                 ? sizeof(T) * 4 + 1 // 4 = ceil(log2(10))
                 : std::numeric_limits<T>::max_exponent10 + 20];
    const int len = snprintf(buf, sizeof(buf), format, value);
    return std::string(buf, buf + len);
}

inline std::string to_string(int x)
{
    return to_string_helper("%d", x);
}

inline std::string to_string(unsigned x)
{
    return to_string_helper("%u", x);
}

inline std::string to_string(long x)
{
    return to_string_helper("%ld", x);
}

inline std::string to_string(unsigned long x)
{
    return to_string_helper("%lu", x);
}

inline std::string to_string(long long x)
{
    return to_string_helper("%lld", x);
}

inline std::string to_string(unsigned long long x)
{
    return to_string_helper("%llu", x);
}

inline std::string to_string(float x)
{
    return to_string_helper("%f", x);
}

inline std::string to_string(double x)
{
    return to_string_helper("%f", x);
}

inline std::string to_string(long double x)
{
    return to_string_helper("%Lf", x);
}

} // namespace mk

#endif // mk_String_h
