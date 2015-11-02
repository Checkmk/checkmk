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

#include <vector>
#include <string>
#include <sstream>
// umm, this is a C header, not actually part of C++ until C++11. This may be a problem in older
// MSVCs
#include <stdint.h>

#ifdef _WIN32
#include <windows.h>
#endif



char *lstrip(char *s);
void rstrip(char *s);
char *strip(char *s);

std::vector<const char*> split_line(char *pos, int (*split_pred)(int));
char *next_word(char **line);

char *llu_to_string(unsigned long long value);
unsigned long long string_to_llu(const char *s);

char *ipv4_to_text(uint32_t ip);

void lowercase(char *s);

int parse_boolean(char *value);

std::string to_utf8(const wchar_t *input);

// case insensitive compare
bool ci_equal(const std::string &lhs, const std::string &rhs);

// Do a simple pattern matching with the jokers * and ?.
// This is case insensitive (windows-like).
bool globmatch(const char *pattern, const char *astring);

#ifdef _WIN32
std::string get_win_error_as_string(DWORD error_id = ::GetLastError());
#endif

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

#endif // _cplusplus < 201103L


#endif // stringutil_h
