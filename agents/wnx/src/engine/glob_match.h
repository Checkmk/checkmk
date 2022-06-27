// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// provides basic api to start and stop service

#pragma once

#include <regex>
#include <string>

namespace cma::tools::gm {
// ------------------------------------------------------
// Matchers:
// ------------------------------------------------------

// ?
template <typename T>
T MakeQuestionMark();
template <>
inline char MakeQuestionMark<char>() {
    return '?';
}

template <>
inline wchar_t MakeQuestionMark<wchar_t>() {
    return L'?';
}

// ^
template <typename T>
T MakeCap();
template <>
inline char MakeCap<char>() {
    return '^';
}

template <>
inline wchar_t MakeCap<wchar_t>() {
    return L'^';
}

// .
template <typename T>
T MakeDot();
template <>
inline char MakeDot<char>() {
    return '.';
}

template <>
inline wchar_t MakeDot<wchar_t>() {
    return L'.';
}

// $
template <typename T>
T MakeDollar();
template <>
inline char MakeDollar<char>() {
    return '$';
}

template <>
inline wchar_t MakeDollar<wchar_t>() {
    return L'$';
}

// *
template <typename T>
T MakeStar();
template <>
inline char MakeStar<char>() {
    return '*';
}

template <>
inline wchar_t MakeStar<wchar_t>() {
    return L'*';
}

template <typename T>
inline T MakeBackSlash() {}

template <>
inline char MakeBackSlash<char>() {
    return '\\';
}
template <>
inline wchar_t MakeBackSlash<wchar_t>() {
    return L'\\';
}

inline bool NeedsEscape(char c) {
    const std::string s{"$()+.[]^{|}\\"};
    return s.find(c) != std::string::npos;
}

inline bool NeedsEscape(wchar_t c) {
    const std::wstring s{L"$()+.[]^{|}\\"};
    return s.find(c) != std::wstring::npos;
}

template <typename T>
void InsertEscapes(std::basic_string<T> &pattern) {
    // Escape special characters (apart from '*' and '?')
    for (size_t pos = 0; pos != pattern.size(); ++pos) {
        auto insert_escape = NeedsEscape(pattern[pos]);
        if (insert_escape) {
            pattern.insert(pos++, 1, MakeBackSlash<T>());
        }
    }
}

template <typename T>
void GlobCharReplace(std::basic_string<T> &pattern) {
    // Regex needs '.' instead of glob '?'
    std::replace(pattern.begin(), pattern.end(),
                 MakeQuestionMark<T>(),  // "?"
                 MakeDot<T>());          // "."

    // Regex needs '.*' instead of glob '*'
    for (auto pos = pattern.find(MakeStar<T>());
         pos != std::basic_string<T>::npos;
         pos = pattern.find(MakeStar<T>(), pos)) {
        pattern.insert(pos, 1, MakeDot<T>());
        pos += 2;
    }
}

template <typename T>
std::basic_regex<T> GlobToRegex(const std::basic_string<T> &pattern) {
    std::basic_string<T> result{pattern};
    result.reserve(result.size() * 2 + 2);  // worst case

    InsertEscapes<T>(result);
    result.insert(0, 1, MakeCap<T>());
    result.push_back(MakeDollar<T>());
    GlobCharReplace<T>(result);

    return std::basic_regex<T>{
        result, std::regex_constants::ECMAScript | std::regex_constants::icase};
}
}  // namespace cma::tools::gm

namespace cma::tools {
template <class T>
inline bool GlobMatch(const T *pattern, const T *target) {
    const auto reg = gm::GlobToRegex(std::basic_string<T>(pattern));
    std::match_results<std::basic_string<T>::const_iterator> match;
    return std::regex_match(std::basic_string<T>(target), match, reg);
}

inline bool GlobMatch(const std::string &pattern, const std::string &target) {
    const auto reg = gm::GlobToRegex(pattern);
    std::match_results<std::string::const_iterator> match;
    return std::regex_match(target, match, reg);
}

inline bool GlobMatch(const std::wstring &pattern, const std::wstring &target) {
    const auto reg = gm::GlobToRegex(pattern);
    std::match_results<std::wstring::const_iterator> match;
    return std::regex_match(target, match, reg);
}

}  // namespace cma::tools
