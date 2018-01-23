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
#include <codecvt>
#include <iostream>
#include <locale>
#include <regex>
#include <sstream>
#include <string>
#include <vector>

using std::regex;
using std::regex_match;
using std::smatch;
using std::sregex_token_iterator;

class WinApiAdaptor;

char *lstrip(char *s);
const char *lstrip(const char *s);
char *rstrip(char *s);
char *strip(char *s);

inline void ltrim(std::string &s) {
    s.erase(s.begin(), std::find_if(s.cbegin(), s.cend(),
                                    [](int ch) { return !std::isspace(ch); }));
}

inline void rtrim(std::string &s) {
    s.erase(std::find_if(s.crbegin(), s.crend(),
                         [](int ch) { return !std::isspace(ch); })
                .base(),
            s.end());
}

std::vector<const char *> split_line(char *pos, int (*split_pred)(int));
char *next_word(char **line);

template <typename CharT>
inline std::vector<std::basic_string<CharT>> tokenizeBase(
    const std::basic_string<CharT> &input, const std::basic_regex<CharT> &re,
    int submatch) {
    return {std::regex_token_iterator<
                typename std::basic_string<CharT>::const_iterator>{
                input.cbegin(), input.cend(), re, submatch},
            std::regex_token_iterator<
                typename std::basic_string<CharT>::const_iterator>{}};
}

/**
 * Split a string into tokens at given delimiter.
 *
 * @param[in] input        The string to be split
 * @param[in] delimiter    The delimiter to split at
 * @return                 A vector of tokens
 */
template <typename CharT>
inline std::vector<std::basic_string<CharT>> tokenize(
    const std::basic_string<CharT> &input,
    const std::basic_string<CharT> &delimiter) {
    return tokenizeBase(input, std::basic_regex<CharT>{delimiter}, -1);
}

/**
 * Split a string into tokens at given delimiter.
 *
 * @param[in] input        The string to be split
 * @param[in] delimiter    The delimiter to split at
 * @return                 A vector of tokens
 */
template <typename CharT>
inline std::vector<std::basic_string<CharT>> tokenize(
    const std::basic_string<CharT> &input, const CharT *delimiter) {
    return tokenizeBase(input, std::basic_regex<CharT>{delimiter}, -1);
}

template <typename CharT>
inline std::basic_regex<CharT> possiblyQuotedRegex();
template <>
std::regex possiblyQuotedRegex<char>();
template <>
std::wregex possiblyQuotedRegex<wchar_t>();

/**
 * Split a string into tokens at space or tab. Substrings enclosed in single or
 * double quotes are not split and the enclosing quotes are retained in the
 * returned tokens.
 *
 * Example: ()
 * input:              This\t'is \t an' "example sentence."
 * returned tokens:    This, 'is \t an', "example sentence."
 *
 * @param[in] input        The string to be split
 * @return                 A vector of tokens
 */
template <typename CharT>
inline std::vector<std::basic_string<CharT>> tokenizePossiblyQuoted(
    const std::basic_string<CharT> &input) {
    return tokenizeBase(input, possiblyQuotedRegex<CharT>(), 1);
}

unsigned long long string_to_llu(const char *s);

void lowercase(char *s);

int parse_boolean(const char *value);

inline std::string to_utf8(const std::wstring &input) {
    return std::wstring_convert<std::codecvt_utf8<wchar_t>>().to_bytes(input);
}

std::wstring to_utf16(const char *input, const WinApiAdaptor &winapi);

struct Utf8 {
    explicit Utf8(const std::wstring &value) : _value(value) {}
    const std::wstring _value;
};

inline std::ostream &operator<<(std::ostream &os, const Utf8 &u) {
    return os << to_utf8(u._value);
}

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
                                   const SeparatorT *sep,
                                   std::ios::fmtflags flags = std::ios::dec) {
    std::basic_ostringstream<SeparatorT> stream;
    stream.setf(flags, std::ios::basefield);

    for (InputIt iter = begin; iter != end; ++iter) {
        if (iter != begin) {
            stream << sep;
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

/**
 * Check if a path is relative or absolute. Works with both Windows and Unix
 * style paths with backslash and forward slash separators, respectively. The
 * presence of Windows drive letter does not affect the result for absolute or
 * relative paths. Absolute UNC paths starting with either '\\' or '//' are
 * recognized as absolute paths.

 * param[in] path    The path to be checked
 * return            True if the path is relative, False if it is absolute
 */
inline bool isPathRelative(const std::string &path) {
    const std::array<regex, 2> regexes{
        // Windows absolute path (with/without drive letter or UNC):
        regex{"^\"?(([A-Za-z]:)?\\\\[^<>:\"/\\\\|?*]|\\\\\\\\[^<>:\"/\\\\|?*])",
              regex::extended},
        // Unix-style absolute path (with/without drive letter or UNC):
        regex{"^\"?(([A-Za-z]:)?/[^<>:\"/\\\\|?*]|//[^<>:\"/\\\\|?*])",
              regex::extended}};
    smatch match;
    return std::all_of(regexes.cbegin(), regexes.cend(),
                       [&path, &match](const regex &re) {
                           return !regex_search(path, match, re);
                       });
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
}  // namespace std

#endif  // _cplusplus < 201103L

#endif  // stringutil_h
