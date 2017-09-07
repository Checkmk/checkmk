// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2015             mk@mathias-kettner.de |
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

#ifndef stringutil_h
#define stringutil_h

#include <stdint.h>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

class WinApiAdaptor;

char *lstrip(char *s);
const char *lstrip(const char *s);
char *rstrip(char *s);
char *strip(char *s);

std::vector<const char *> split_line(char *pos, int (*split_pred)(int));
char *next_word(char **line);

unsigned long long string_to_llu(const char *s);

void lowercase(char *s);

int parse_boolean(const char *value);

struct Utf8 {
    explicit Utf8(const std::wstring &value) : _value(value) {}
    const std::wstring _value;
};

std::ostream &operator<<(std::ostream &os, const Utf8 &u);

std::string to_utf8(const char *input);
std::string to_utf8(const wchar_t *input, const WinApiAdaptor &winapi);

std::wstring to_utf16(const char *input, const WinApiAdaptor &winapi);

// case insensitive compare
bool ci_equal(const std::string &lhs, const std::string &rhs);

// Do a simple pattern matching with the jokers * and ?.
// This is case insensitive (windows-like).
bool globmatch(const char *pattern, const char *astring);
bool globmatch(const wchar_t *pattern, const wchar_t *astring);

std::string replaceAll(const std::string &str, const std::string &from,
                       const std::string &to);

void stringToIPv6(const char *value, uint16_t *address,
                  const WinApiAdaptor &winapi);
void stringToIPv4(const char *value, uint32_t &address);
void netmaskFromPrefixIPv6(int bits, uint16_t *netmask,
                           const WinApiAdaptor &winapi);
void netmaskFromPrefixIPv4(int bits, uint32_t &netmask);

template <typename InputIt, typename SeparatorT>
std::basic_string<SeparatorT> join(InputIt begin, InputIt end,
                                   const SeparatorT *sep) {
    std::basic_ostringstream<SeparatorT> stream;
    bool first = true;

    for (InputIt iter = begin; iter != end; ++iter) {
        if (!first) {
            stream << sep;
        } else {
            first = false;
        }
        stream << *iter;
    }
    return stream.str();
}

template <typename ValueT, typename SeparatorT>
std::basic_string<SeparatorT> join(const std::vector<ValueT> &input,
                                   const SeparatorT *sep) {
    return join(input.begin(), input.end(), sep);
}

// to_string and to_wstring supplied in C++11 but not before
#if _cplusplus < 201103L

namespace std {
template <typename T>
std::wstring to_wstring(const T &source) {
    std::wostringstream str;
    str << source;
    return str.str();
}

template <typename T>
std::string to_string(const T &source) {
    std::ostringstream str;
    str << source;
    return str.str();
}
}

#endif  // _cplusplus < 201103L

#endif  // stringutil_h
