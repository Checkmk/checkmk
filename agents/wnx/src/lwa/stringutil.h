// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef stringutil_h
#define stringutil_h

#include <stdint.h>

#include <codecvt>
#include <iostream>
//#include <locale>
#include <array>
#include <cctype>
#include <regex>
#include <sstream>
#include <string>
#include <vector>

using std::regex;
using std::regex_match;
using std::smatch;
using std::sregex_token_iterator;

class Logger;
class WinApiInterface;
struct sockaddr_storage;

inline void ltrim(std::string &s) {
    s.erase(s.begin(), std::find_if(s.cbegin(), s.cend(), [](unsigned char ch) {
                return !std::isspace(ch);
            }));
}

inline void rtrim(std::string &s) {
    s.erase(std::find_if(s.crbegin(), s.crend(),
                         [](unsigned char ch) { return !std::isspace(ch); })
                .base(),
            s.end());
}

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

int parse_boolean(const char *value);

std::string ConvertToUTF8(const std::wstring &Src) noexcept;

inline std::string to_utf8(const std::wstring &input) {
    if (input.empty()) return {};

    try {
        return std::wstring_convert<std::codecvt_utf8<wchar_t>>().to_bytes(
            input);
    } catch (const std::exception &) {
        return ConvertToUTF8(input);
    }
}

inline std::wstring to_utf16(const std::string &input) {
    return std::wstring_convert<
               std::codecvt_utf8<wchar_t, 0x10ffff, std::little_endian>>()
        .from_bytes(input);
}

struct Utf8 {
    explicit Utf8(const std::wstring &value) : _value(value) {}
    const std::wstring _value;
};

inline std::ostream &operator<<(std::ostream &os, const Utf8 &u) {
    return os << to_utf8(u._value);
}

// case insensitive equality check
bool ci_equal(const std::string &lhs, const std::string &rhs);

// case insensitive compare function (e. g. for std::sort)
bool ci_compare(const std::string &lhs, const std::string &rhs);

// clang-format off
// Start-of-line char: '^' or L'^'
template <class CharT> inline CharT sol();
template <> char sol<char>();
template <> wchar_t sol<wchar_t>();

// End-of-line char: '$' or L'$'
template <class CharT> inline CharT eol();
template <> char eol<char>();
template <> wchar_t eol<wchar_t>();

// Any single char: '.' or L'.'
template <class CharT> inline CharT anyS();
template <> char anyS<char>();
template <> wchar_t anyS<wchar_t>();

// Any single char in glob patterns: '?' or L'?'
template <class CharT> inline CharT anySGlob();
template <> char anySGlob<char>();
template <> wchar_t anySGlob<wchar_t>();

// Any number of chars: '*' or L'*'
template <class CharT> inline CharT anyN();
template <> char anyN<char>();
template <> wchar_t anyN<wchar_t>();

// Escape char: '\\' or L'\\'
template <class CharT> inline CharT esc();
template <> char esc<char>();
template <> wchar_t esc<wchar_t>();

// Is given character one of the regex special characters: 
template <class CharT> inline bool needsEscape(CharT c);
template <> bool needsEscape<char>(char c);
template <> bool needsEscape<wchar_t>(wchar_t c);

namespace rconst = std::regex_constants;
template <class CharT> using StringT = std::basic_string<CharT>;
template <class CharT> using RegexT = std::basic_regex<CharT>;
// clang-format on

template <class CharT>
using MatchT = std::match_results<typename StringT<CharT>::const_iterator>;

template <class CharT>
inline void escape(StringT<CharT> &rPatt) {
    // Escape special characters (apart from '*' and '?')
    for (size_t pos = 0; pos != rPatt.size(); ++pos) {
        if (needsEscape(rPatt[pos])) {
            rPatt.insert(pos++, 1, esc<CharT>());
        }
    }
}

template <class CharT>
inline void globCharReplace(StringT<CharT> &rPatt) {
    // Regex needs '.' instead of glob '?'
    std::replace(rPatt.begin(), rPatt.end(), anySGlob<CharT>(), anyS<CharT>());

    // Regex needs '.*' instead of glob '*'
    for (auto pos = rPatt.find(anyN<CharT>()); pos != StringT<CharT>::npos;
         pos = rPatt.find(anyN<CharT>(), pos)) {
        rPatt.insert(pos, 1, anyS<CharT>());
        pos += 2;
    }
}

template <class CharT>
inline RegexT<CharT> globToRegex(const StringT<CharT> &glob) {
    const auto escCnt = std::count_if(glob.cbegin(), glob.cend(), [](CharT c) {
        return c == anyN<CharT>() || needsEscape<CharT>(c);
    });
    StringT<CharT> rPatt;
    rPatt.reserve(glob.size() + escCnt + 2);
    std::copy(glob.cbegin(), glob.cend(), std::back_inserter(rPatt));
    escape<CharT>(rPatt);
    rPatt.insert(0, 1, sol<CharT>());
    rPatt.push_back(eol<CharT>());
    globCharReplace<CharT>(rPatt);

    return RegexT<CharT>{rPatt, rconst::ECMAScript | rconst::icase};
}

// Do a simple pattern matching with the jokers * and ?.
// This is case insensitive (windows-like).
template <class CharT>
inline bool globmatch(const StringT<CharT> &glob,
                      const StringT<CharT> &target) {
    const auto reg = globToRegex(glob);
    MatchT<CharT> match;
    return std::regex_match(target, match, reg);
}

#if defined(_MSC_BUILD)
template <class T>
inline bool globmatch(const T *glob, const T *target) {
    const auto reg = globToRegex(std::basic_string<T>(glob));
    MatchT<T> match;
    return std::regex_match(std::basic_string<T>(target), match, reg);
}
#endif

std::string replaceAll(const std::string &str, const std::string &from,
                       const std::string &to);

void stringToIPv6(const char *value, uint16_t *address);
void stringToIPv4(const char *value, uint32_t &address);
void netmaskFromPrefixIPv6(int bits, uint16_t *netmask);
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

/**
 * Convert a valid IP address to a textual representation, omitting
 * possible port indication bound to socket address. Both IPv4 and IPv6
 * addresses are supported. For IPv4-mapped IPv6 addresses the corresponding
 * IPv4 address is returned.
 *
 * @param[in] addr    The IP address to be converted
 * @param[in] logger  Pointer to a logger instance
 * @param[in] winapi  Reference to WinAPI instance
 * @return            The string representation of the IP address
 */
std::string IPAddrToString(const sockaddr_storage &addr);

/**
 * Extract the actual IP address out of a string representation possibly
 * containing also the port. Supports both IPv4 and IPv6 addresses. For
 * IPv4-mapped IPv6 addresses the corresponding IPv4 address is extracted.
 *
 * @param[in] inputAddr    The textual representation of an IP address, possibly
 *                         containing also the port number
 * @return                 The extracted IP address as a string
 */
std::string extractIPAddress(const std::string &inputAddr);

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
