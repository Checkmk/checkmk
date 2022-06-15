// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// Assorted routines
#pragma once

#include <fmt/format.h>

#include <cctype>
#include <chrono>
#include <cwctype>
#include <filesystem>
#include <string>
#include <string_view>
#include <thread>
#include <tuple>
#include <type_traits>
#include <vector>

#include "tools/_raii.h"
#include "tools/_tgt.h"
#include "tools/_xlog.h"

// Popular Data Structures Here
// I am not sure...
namespace cma {
using ByteVector = std::vector<unsigned char>;
}  // namespace cma

namespace cma::tools {

inline void sleep(int milliseconds) noexcept {
    std::this_thread::sleep_until(std::chrono::steady_clock::now() +
                                  std::chrono::milliseconds(milliseconds));
}

template <typename T, typename B>
inline void sleep(std::chrono::duration<T, B> dur) noexcept {
    std::this_thread::sleep_until(std::chrono::steady_clock::now() + dur);
}

[[nodiscard]] inline bool IsEqual(std::string_view lhs, std::string_view rhs) {
    return std::equal(
        lhs.cbegin(), lhs.cend(), rhs.cbegin(), rhs.cend(),
        [](char l, char r) { return std::tolower(l) == std::tolower(r); });
}

[[nodiscard]] inline bool IsEqual(std::wstring_view lhs,
                                  std::wstring_view rhs) {
    return std::equal(lhs.cbegin(), lhs.cend(), rhs.cbegin(), rhs.cend(),
                      [](wchar_t l, wchar_t r) {
                          return std::tolower(l) == std::tolower(r);
                      });
}

[[nodiscard]] inline bool IsEqual(const std::wstring &lhs,
                                  const std::wstring &rhs) {
    return std::equal(lhs.cbegin(), lhs.cend(), rhs.cbegin(), rhs.cend(),
                      [](wchar_t l, wchar_t r) {
                          return std::tolower(l) == std::tolower(r);
                      });
}

[[nodiscard]] inline bool IsLess(const std::string &lhs,
                                 const std::string &rhs) {
    auto li = lhs.cbegin();
    auto ri = rhs.cbegin();
    for (; li != lhs.cend() && ri != rhs.cend(); ++ri, ++li) {
        auto right_char = std::tolower(*ri);
        auto left_char = std::tolower(*li);
        if (left_char != right_char) {
            return left_char < right_char;
        }
    }

    // If equal until here, lhs < rhs iff lhs shorter than rhs.
    return lhs.size() < rhs.size();
}

// Stupid Approach but C++ has no good methods to uppercase/lowercase string
// #TODO USE IBM ICU or Boost.Locale
inline void WideUpper(std::wstring &str) {
    if constexpr (tgt::IsWindows()) {
        auto *work_string = str.data();  // C++ 17, mutable string
        CharUpperW(work_string);         // Microsoft specific, but safe
    } else {
        // for windows doesn't work, for Linux probably too
        std::transform(str.begin(), str.end(), str.begin(),
                       [](wchar_t ch) { return std::towupper(ch); });
    }
}

inline void StringLower(std::string &str) {
    if constexpr (tgt::IsWindows()) {
        auto *work_string = str.data();  // C++ 17, mutable string
        CharLowerA(work_string);         // Microsoft specific, but safe
    } else {
        // for windows doesn't work, for Linux probably too
        std::transform(str.begin(), str.end(), str.begin(),
                       [](char ch) { return std::tolower(ch); });
    }
}

inline void StringUpper(std::string &str) {
    if constexpr (tgt::IsWindows()) {
        auto *work_string = str.data();
        CharUpperA(work_string);

    } else {
        // for windows doesn't work, for Linux probably too
        std::transform(str.begin(), str.end(), str.begin(),
                       [](char ch) { return std::toupper(ch); });
    }
}

inline void WideLower(std::wstring &str) {
    if constexpr (tgt::IsWindows()) {
        auto *work_string = str.data();
        CharLowerW(work_string);
    } else {
        // for windows doesn't work, for Linux probably too
        std::transform(str.begin(), str.end(), str.begin(),
                       [](const wchar_t ch) { return std::towlower(ch); });
    }
}

// makes a vector from arbitrary objects
// Usage:
// auto vector_of string
template <typename... Args>
std::vector<std::wstring> ConstructVectorWstring(Args &&...args) {
    std::vector<std::wstring> cfg_files;
    static_assert((std::is_constructible_v<std::wstring, Args &> && ...));
    (cfg_files.emplace_back(args), ...);
    return cfg_files;
}

template <typename... Args>
auto ConstructVector(Args &...str) {
    return std::vector{str...};
};

inline bool IsValidRegularFile(const std::filesystem::path &filepath) {
    std::error_code ec;
    return std::filesystem::exists(filepath, ec) &&
           std::filesystem::is_regular_file(filepath);
}

template <typename T>
inline void AddVector(std::vector<char> &accu, const T &add) noexcept {
    auto add_size = add.size();
    if (add_size == 0) {
        return;
    }
    auto old_size = accu.size();
    try {
        accu.resize(add_size + old_size);
        memcpy(accu.data() + old_size, add.data(), add_size);
    } catch (const std::exception &e) {
        xlog::l(XLOG_FLINE + " Exception %s", e.what());
        return;
    }
}

template <typename T>
auto ParseKeyValue(const std::basic_string<T> value, T splitter) {
    auto end = value.find_first_of(splitter);
    if (end == std::basic_string<T>::npos) {
        return std::make_tuple(std::basic_string<T>(), std::basic_string<T>());
    }
    auto k = value.substr(0, end);
    auto v = value.substr(end + 1);
    return std::make_tuple(k, v);
}

template <typename T>
auto ParseKeyValue(const std::basic_string_view<T> value, T splitter) {
    auto end = value.find_first_of(splitter);
    if (end == std::basic_string<T>::npos) {
        return std::make_tuple(std::basic_string<T>(), std::basic_string<T>());
    }
    auto k = value.substr(0, end);
    auto v = value.substr(end + 1);
    return std::make_tuple(std::basic_string<T>(k), std::basic_string<T>(v));
}

template <typename T>
auto ParseKeyValue(const T *value, T splitter) {
    return ParseKeyValue(std::basic_string<T>(value), splitter);
}

// Calculates byte offset in arbitrary data
template <typename T>
void *GetOffsetInBytes(T *object, size_t offset) {
    return static_cast<void *>(reinterpret_cast<char *>(object) + offset);
}

// returns const void*, never fails
template <typename T>
const void *GetOffsetInBytes(const T *object, size_t offset) {
    return static_cast<const void *>(reinterpret_cast<const char *>(object) +
                                     offset);
}

template <typename T>
std::optional<uint32_t> ConvertToUint32(const T &str) noexcept {
    try {
        return std::stoul(str);
    } catch (const std::exception &) {
        return {};
    }
}

template <typename T>
std::optional<uint64_t> ConvertToUint64(const T &str) noexcept {
    try {
        return std::stoull(str);
    } catch (const std::exception &) {
        return {};
    }
}

template <typename T>
uint64_t ConvertToUint64(const T &str, uint64_t dflt) noexcept {
    try {
        return std::stoull(str);
    } catch (const std::exception &) {
        return dflt;
    }
}

#if defined(WINDOWS_OS)

namespace win {
template <typename T>
inline bool SetEnv(const std::basic_string<T> &name,
                   const std::basic_string<T> &value) noexcept {
    auto cmd = name;
    if constexpr (sizeof(T) == 1) {
        cmd += "=" + value;
        return _putenv(cmd.c_str()) == 0;
    } else {
        cmd += L"=" + value;
        return _wputenv(cmd.c_str()) == 0;
    }
}

// safe temporary setting environment variable
// sets variable on ctor
// remove variable on dtor
// NOT THREAD SAFE and cannot be Thread Safe by nature of the _setenv
// Usage {WithEnv we("PATH", ".");.........;}
template <typename T>
class WithEnv {
public:
    // ctor
    WithEnv(const std::basic_string<T> &name, const std::basic_string<T> &value)
        : name_(name) {
        if (!name_.empty()) {
            SetEnv(name, value);
        }
    }

    ~WithEnv() {
        if (!name_.empty()) {
            SetEnv(name_, {});
        }
    }

    // no copy - environment variable are persistent globals
    WithEnv(const WithEnv &rhs) = delete;
    WithEnv &operator=(const WithEnv &rhs) = delete;

    // move is allowed
    WithEnv(WithEnv &&rhs) noexcept {
        name_ = rhs.name_;
        rhs.name_.clear();
    }
    WithEnv &operator=(WithEnv &&rhs) noexcept {
        if (!name_.empty()) {
            SetEnv(name_, {});
        }
        name_ = rhs.name_;
        rhs.name_.clear();
    }

    auto name() noexcept { return name_; }

private:
    std::basic_string<T> name_;
};

template <typename T>
std::basic_string<T> GetEnv(const T *name) noexcept {
    T env_var_value[MAX_PATH] = {0};

    if constexpr (sizeof(T) == 1) {
        ::GetEnvironmentVariableA(name, env_var_value, MAX_PATH);
    } else {
        ::GetEnvironmentVariableW(name, env_var_value, MAX_PATH);
    }
    return std::basic_string<T>(env_var_value);
}

template <typename T>
std::basic_string<T> GetEnv(const std::basic_string<T> &name) noexcept {
    return GetEnv(name.c_str());
}

template <typename T>
std::basic_string<T> GetEnv(const std::basic_string_view<T> &name) noexcept {
    return GetEnv(name.data());
}

}  // namespace win
#endif

inline void LeftTrim(std::string &str) {
    str.erase(str.begin(), std::find_if(str.cbegin(), str.cend(), [](int Ch) {
                  return std::isspace(Ch) == 0;
              }));
}

inline void RightTrim(std::string &str) {
    str.erase(std::find_if(str.crbegin(), str.crend(),
                           [](int Ch) { return std::isspace(Ch) == 0; })
                  .base(),
              str.end());
}

inline void AllTrim(std::string &str) {
    LeftTrim(str);
    RightTrim(str);
}

inline std::vector<std::string_view> ToView(
    const std::vector<std::string> &table) {
    std::vector<std::string_view> s_view;

    for (const auto &str : table) {
        s_view.emplace_back(str);
    }

    return s_view;
}

/// max_count == 0 means inifinite parsing
inline std::vector<std::string> SplitString(const std::string &str,
                                            std::string_view delimiter,
                                            size_t max_count) noexcept {
    // sanity
    if (str.empty()) {
        return {};
    }
    if (delimiter.empty()) {
        return {str};
    }

    size_t start = 0U;
    std::vector<std::string> result;

    auto end = str.find(delimiter);
    while (end != std::string::npos) {
        result.push_back(str.substr(start, end - start));

        start = end + delimiter.length();
        end = str.find(delimiter, start);

        // check for a skipping rest
        if (result.size() == max_count) {
            end = std::string::npos;
            break;
        }
    }

    auto last_string = str.substr(start, end);
    if (!last_string.empty()) {
        result.push_back(last_string);
    }

    return result;
}

inline std::vector<std::string> SplitString(
    const std::string &str, std::string_view delimiter) noexcept {
    return SplitString(str, delimiter, 0);
}

// "a.b.", "." => {"a", "b"}
// "a.b", "." => {"a", "b"}
// ".b", "." => { "b"}
// max_count == 0 means inifinite parsing
inline std::vector<std::wstring> SplitString(const std::wstring &str,
                                             std::wstring_view delimiter,
                                             size_t max_count) noexcept {
    // sanity
    if (str.empty()) {
        return {};
    }
    if (delimiter.empty()) {
        return {str};
    }

    size_t start = 0U;
    std::vector<std::wstring> result;

    auto end = str.find(delimiter);
    while (end != std::string::npos) {
        result.push_back(str.substr(start, end - start));

        start = end + delimiter.length();
        end = str.find(delimiter, start);

        // check for a skipping rest
        if (result.size() == max_count) {
            end = std::string::npos;
            break;
        }
    }

    auto last_string = str.substr(start, end);
    if (!last_string.empty()) {
        result.push_back(last_string);
    }

    return result;
}

inline std::vector<std::wstring> SplitString(
    const std::wstring &str, std::wstring_view delimiter) noexcept {
    return SplitString(str, delimiter, 0);
}

// special case when we are parsing to the end
// indirectly tested in the test-cma_tools
inline std::vector<std::wstring> SplitStringExact(const std::wstring &str,
                                                  std::wstring_view delimiter,
                                                  size_t max_count) noexcept {
    // sanity
    if (str.empty()) {
        return {};
    }
    if (delimiter.empty()) {
        return {str};
    }

    size_t start = 0U;
    std::vector<std::wstring> result;

    auto end = str.find(delimiter);
    while (end != std::string::npos) {
        result.push_back(str.substr(start, end - start));

        start = end + delimiter.length();
        end = str.find(delimiter, start);

        // check for a skipping rest
        if (result.size() == max_count - 1) {
            break;
        }
    }

    auto last_string = str.substr(start, end);
    result.push_back(last_string);

    return result;
}

// joiner :)
// ["a", "b", "c" ] + Separator:"," => "a,b,c"
// C++ is not happy with templating of this function
// we have to make call like JoinVector<wchar_t>
// so we have to implementations
inline std::wstring JoinVector(const std::vector<std::wstring> &values,
                               std::wstring_view separator) {
    if (values.empty()) {
        return {};
    }

    size_t sz = 0;
    for_each(values.begin(), values.end(),
             [&sz](const std::wstring &entry) { sz += entry.size() + 1; });

    std::wstring values_string;
    values_string.reserve(sz);

    values_string = *values.begin();
    for_each(values.begin() + 1, values.end(),
             [&values_string, separator](std::wstring_view entry) {
                 values_string += separator;
                 values_string += entry;
             });
    return values_string;
}

// version for string
inline std::string JoinVector(const std::vector<std::string> &values,
                              std::string_view separator) {
    if (values.empty()) {
        return {};
    }

    size_t sz = 0;
    for_each(values.begin(), values.end(),
             [&sz](const std::string &entry) { sz += entry.size() + 1; });

    std::string values_string;
    values_string.reserve(sz);

    values_string = *values.begin();
    for_each(values.begin() + 1, values.end(),
             [&values_string, separator](std::string_view entry) {
                 values_string += separator;
                 values_string += entry;
             });
    return values_string;
}

template <typename T>
void ConcatVector(std::vector<T> &target, const std::vector<T> &source) {
    std::copy(source.begin(), source.end(), std::back_inserter(target));
}

inline std::string TimeToString(
    std::chrono::system_clock::time_point time_point) {
    auto in_time_t = std::chrono::system_clock::to_time_t(time_point);
    std::stringstream sss;
    auto *loc_time = std::localtime(&in_time_t);
    auto p_time = std::put_time(loc_time, "%Y-%m-%d %T");
    sss << p_time << std::ends;
    return sss.str();
}

inline auto SecondsSinceEpoch() {
    auto time_since = std::chrono::system_clock::now().time_since_epoch();
    const auto now =
        std::chrono::duration_cast<std::chrono::seconds>(time_since);
    return now.count();
}

inline std::string RemoveQuotes(const std::string &in) {
    std::string val{in};
    if (val.size() < 2) {
        return val;
    }

    if (val.back() == '\'' || val.back() == '\"') {
        val.pop_back();
    }
    if (val[0] == '\'' || val[0] == '\"') {
        val = val.substr(1, val.size() - 1);
    }
    return val;
}

inline std::wstring RemoveQuotes(const std::wstring &in) {
    std::wstring val{in};
    if (val.size() < 2) {
        return val;
    }

    if (val.back() == L'\'' || val.back() == L'\"') {
        val.pop_back();
    }
    if (val[0] == L'\'' || val[0] == L'\"') {
        val = val.substr(1, val.size() - 1);
    }
    return val;
}

}  // namespace cma::tools

namespace fmt {

// formatter extender for variable count of parameters
template <typename... Args>
auto formatv(const std::string format_string, const Args &...args) {
    std::string buffer;
    try {
        auto x = std::make_tuple(format_string, args...);
        auto print_message = [&buffer](const auto &...args) {
            buffer = fmt::format(args...);
        };
        std::apply(print_message, x);
    } catch (const std::exception &) {
        xlog::l("Invalid string/parameters to format '%s'",
                format_string.c_str());
    }
    return buffer;
}

}  // namespace fmt
