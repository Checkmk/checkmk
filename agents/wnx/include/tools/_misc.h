// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// Assorted routines
#pragma once

#include <cctype>
#include <chrono>
#include <cwctype>
#include <filesystem>
#include <ranges>
#include <string>
#include <string_view>
#include <thread>
#include <tuple>
#include <type_traits>
#include <vector>

#include "tools/_tgt.h"
#include "tools/_xlog.h"

namespace cma::type {
template <class T>
concept StringViewLike = std::convertible_to<T, std::string_view>;
template <class T>
concept WideStringViewLike = std::convertible_to<T, std::wstring_view>;
template <typename C>
concept AnyStringView = StringViewLike<C> || WideStringViewLike<C>;

}  // namespace cma::type

// Popular Data Structures Here
// I am not sure...
namespace cma {
using ByteVector = std::vector<unsigned char>;
}  // namespace cma

namespace cma::tools {

inline void sleep(uint32_t milliseconds) noexcept {
    std::this_thread::sleep_until(std::chrono::steady_clock::now() +
                                  std::chrono::milliseconds(milliseconds));
}

template <typename T, typename B>
void sleep(std::chrono::duration<T, B> dur) noexcept {
    std::this_thread::sleep_until(std::chrono::steady_clock::now() + dur);
}

inline auto CompareIgnoreCase(char lhs, char rhs) noexcept {
    // TODO(sk): naive implementation
    return std::tolower(lhs) <=> std::tolower(rhs);
}

inline auto CompareIgnoreCase(wchar_t lhs, wchar_t rhs) noexcept {
    // TODO(sk): naive implementation
    return std::towlower(lhs) <=> std::towlower(rhs);
}

/// Checks basically whether we have vector(ContiguousContainer)
/// C++ concepts library doesn't support now ContiguosContainer
template <typename C>
concept VectorLike = requires(C c) {
    c[0];
    c.data();
    c.size();
};
template <VectorLike Data>
std::string_view ToView(const Data &input) {
    return {reinterpret_cast<const char *>(input.data()),
            sizeof(input[0]) * input.size()};
}

inline std::optional<std::wstring_view> ToWideView(std::string_view s) {
    if ((s.size() % 2) != 0) {
        return {};
    }
    return std::wstring_view{reinterpret_cast<const wchar_t *>(s.data()),
                             s.size() / 2};
}

template <class T>
    requires type::StringViewLike<T>
[[nodiscard]] auto AsView(const T &p) noexcept {
    return std::string_view{p};
}

template <class T>
    requires type::WideStringViewLike<T>
[[nodiscard]] auto AsView(const T &p) noexcept {
    return std::wstring_view{p};
}

template <class T, class V>
    requires type::AnyStringView<T> && type::AnyStringView<V>
[[nodiscard]] bool IsEqual(const T &lhs, const V &rhs) {
    return std::ranges::equal(AsView(lhs), AsView(rhs), [](auto l, auto r) {
        return CompareIgnoreCase(l, r) == std::strong_ordering::equal;
    });
}

template <class T, class V>
    requires type::AnyStringView<T> && type::AnyStringView<V>
auto ThreeWayCompare(const T &lhs, const V &rhs) {
    return std::lexicographical_compare_three_way(
        lhs.begin(), lhs.end(), std::ranges::begin(rhs), std::ranges::end(rhs),
        [](auto l, auto r) { return CompareIgnoreCase(l, r); });
}

[[nodiscard]] inline bool IsLess(std::string_view lhs,
                                 std::string_view rhs) noexcept {
    return ThreeWayCompare(lhs, rhs) == std::strong_ordering::less;
}

// Stupid Approach but C++ has no good methods to uppercase/lowercase string
// #TODO USE IBM ICU or Boost.Locale
inline void WideUpper(std::wstring &str) {
    if constexpr (tgt::IsWindows()) {
        auto *work_string = str.data();  // C++ 17, mutable string
        CharUpperW(work_string);         // Microsoft specific, but safe
    } else {
        // for windows doesn't work, for Linux probably too
        std::ranges::transform(str, str.begin(),
                               [](wchar_t ch) { return std::towupper(ch); });
    }
}

inline void StringLower(std::string &str) {
    if constexpr (tgt::IsWindows()) {
        auto *work_string = str.data();  // C++ 17, mutable string
        CharLowerA(work_string);         // Microsoft specific, but safe
    } else {
        // for windows doesn't work, for Linux probably too
        std::ranges::transform(str, str.begin(),
                               [](char ch) { return std::tolower(ch); });
    }
}

inline void StringUpper(std::string &str) {
    if constexpr (tgt::IsWindows()) {
        auto *work_string = str.data();
        CharUpperA(work_string);

    } else {
        // for windows doesn't work, for Linux probably too
        std::ranges::transform(str, str.begin(),
                               [](char ch) { return std::toupper(ch); });
    }
}

inline void WideLower(std::wstring &str) {
    if constexpr (tgt::IsWindows()) {
        auto *work_string = str.data();
        CharLowerW(work_string);
    } else {
        // for windows doesn't work, for Linux probably too
        std::ranges::transform(str, str.begin(), [](const wchar_t ch) {
            return std::towlower(ch);
        });
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
}

inline bool IsValidRegularFile(const std::filesystem::path &filepath) noexcept {
    std::error_code ec;
    return std::filesystem::exists(filepath, ec) &&
           std::filesystem::is_regular_file(filepath, ec);
}

template <typename T>
void AddVector(std::vector<char> &accu, const T &add) noexcept {
    const auto add_size = add.size();
    if (add_size == 0) {
        return;
    }
    auto old_size = accu.size();
    try {
        accu.resize(add_size + old_size);
        memcpy(accu.data() + old_size, add.data(), add_size);
    } catch (const std::exception &e) {
        xlog::l(XLOG_FLINE + " Exception %s", e.what());
    }
}

template <typename T>
auto ParseKeyValue(const std::basic_string<T> &value, T splitter) {
    const auto end = value.find_first_of(splitter);
    if (end == std::basic_string<T>::npos) {
        return std::make_tuple(std::basic_string<T>(), std::basic_string<T>());
    }
    auto k = value.substr(0, end);
    auto v = value.substr(end + 1);
    return std::make_tuple(k, v);
}

template <typename T>
auto ParseKeyValue(std::basic_string_view<T> value, T splitter) {
    const auto end = value.find_first_of(splitter);
    if (end == std::basic_string<T>::npos) {
        return std::make_tuple(std::basic_string<T>(), std::basic_string<T>());
    }
    const auto k = value.substr(0, end);
    const auto v = value.substr(end + 1);
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
    return reinterpret_cast<const char *>(object) + offset;
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
bool SetEnv(const std::basic_string<T> &name,
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
        return *this;
    }

    auto name() noexcept { return name_; }

private:
    std::basic_string<T> name_;
};

template <typename T>
std::basic_string<T> GetEnv(const T *name) noexcept {
    std::basic_string<T> env_var_value;
    if constexpr (sizeof(T) == 1) {
        DWORD size = GetEnvironmentVariableA(name, nullptr, 0);
        env_var_value.resize(size);
        GetEnvironmentVariableA(name, env_var_value.data(), size);
    } else {
        DWORD size = GetEnvironmentVariableW(name, nullptr, 0);
        env_var_value.resize(size);
        GetEnvironmentVariableW(name, env_var_value.data(), size);
    }
    while (!env_var_value.empty() && env_var_value.back() == 0) {
        env_var_value.pop_back();
    }
    return env_var_value;
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
    str.erase(str.begin(), std::ranges::find_if(str, [](int ch) {
                  return std::isspace(ch) == 0;
              }));
}

inline void RightTrim(std::string &str) noexcept {
    // attention: reverse search here
    str.erase(std::ranges::find_if(str.rbegin(), str.rend(),
                                   [](int ch) { return std::isspace(ch) == 0; })
                  .base(),
              str.end());
}

inline void AllTrim(std::string &str) {
    LeftTrim(str);
    RightTrim(str);
}

template <typename C>
concept TheChar = std::is_same_v<C, char> || std::is_same_v<C, wchar_t>;

/// "a.b.", "." => {"a", "b"}
/// "a.b", "." => {"a", "b"}
/// ".b", "." => { "b"}
/// max_count == 0 means inifinite parsing
template <TheChar T>
std::vector<std::basic_string<T>> SplitString(
    const std::basic_string<T> &str, std::basic_string_view<T> delimiter,
    size_t max_count) noexcept {
    // sanity
    if (str.empty()) {
        return {};
    }
    if (delimiter.empty()) {
        return {str};
    }

    size_t start = 0U;
    std::vector<std::basic_string<T>> result;

    auto end = str.find(delimiter);
    while (end != std::basic_string<T>::npos) {
        result.push_back(str.substr(start, end - start));

        start = end + delimiter.length();
        end = str.find(delimiter, start);

        // check for a skipping rest
        if (result.size() == max_count) {
            end = std::basic_string<T>::npos;
            break;
        }
    }

    auto last_string = str.substr(start, end);
    if (!last_string.empty()) {
        result.push_back(last_string);
    }

    return result;
}

template <TheChar T>
std::vector<std::basic_string<T>> SplitString(const std::basic_string<T> &str,
                                              const T *delimiter,
                                              size_t max_count) noexcept {
    return SplitString(str, std::basic_string_view<T>(delimiter), max_count);
}

template <TheChar T>
std::vector<std::basic_string<T>> SplitString(
    const std::basic_string<T> &str, const std::basic_string<T> &delimiter,
    size_t max_count) noexcept {
    return SplitString(str, std::basic_string_view<T>(delimiter), max_count);
}

template <TheChar T>
std::vector<std::basic_string<T>> SplitString(
    const std::basic_string<T> &str,
    std::basic_string_view<T> delimiter) noexcept {
    return SplitString(str, delimiter, 0);
}

template <TheChar T>
std::vector<std::basic_string<T>> SplitString(const std::basic_string<T> &str,
                                              const T *delimiter) noexcept {
    return SplitString(str, delimiter, 0);
}

template <TheChar T>
std::vector<std::basic_string<T>> SplitString(
    const std::basic_string<T> &str,
    const std::basic_string<T> &delimiter) noexcept {
    return SplitString(str, std::basic_string_view<T>(delimiter), 0);
}

/// special case when we are parsing to the end
/// indirectly tested in the test-cma_tools
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
    result.push_back(str.substr(start, end));

    return result;
}

/// Join strings a-la Python join()
/// ["a", "b", "c" ] + Separator:"," => "a,b,c"
template <TheChar T>
std::basic_string<T> JoinVector(const std::vector<std::basic_string<T>> &values,
                                std::basic_string_view<T> separator) {
    if (values.empty()) {
        return {};
    }

    size_t sz = separator.size() * values.size();
    std::ranges::for_each(values,
                          [&](const auto &entry) { sz += entry.size(); });

    std::basic_string<T> result;
    result.reserve(sz);

    std::ranges::for_each(
        values, [&result, separator](std::basic_string_view<T> entry) {
            result += entry;
            result += separator;
        });
    result.resize(sz - separator.length());
    return result;
}

template <TheChar T>
std::basic_string<T> JoinVector(const std::vector<std::basic_string<T>> &values,
                                const T *separator) {
    return JoinVector(values, std::basic_string_view<T>(separator));
}

template <typename T>
void ConcatVector(std::vector<T> &target, const std::vector<T> &source) {
    std::ranges::copy(source, std::back_inserter(target));
}

inline auto SecondsSinceEpoch() {
    const auto time_since = std::chrono::system_clock::now().time_since_epoch();
    const auto now =
        std::chrono::duration_cast<std::chrono::seconds>(time_since);
    return now.count();
}

inline std::pair<uint32_t, uint32_t> IsQuoted(std::string_view in) {
    return {in.front() == '\'' || in.front() == '\"' ? 1 : 0,
            in.back() == '\'' || in.back() == '\"' ? 1 : 0};
}

inline std::pair<uint32_t, uint32_t> IsQuoted(std::wstring_view in) {
    return {in.front() == L'\'' || in.front() == L'\"' ? 1 : 0,
            in.back() == L'\'' || in.back() == L'\"' ? 1 : 0};
}

template <TheChar T>
std::basic_string<T> RemoveQuotes(std::basic_string_view<T> in) {
    if (in.size() < 2) {
        return std::basic_string<T>{in};
    }

    const auto [start, end] = IsQuoted(in);

    return std::basic_string<T>{
        end + start != 0 ? in.substr(start, in.size() - (start + end)) : in};
}

template <TheChar T>
std::basic_string<T> RemoveQuotes(const std::basic_string<T> &in) {
    return RemoveQuotes(std::basic_string_view<T>{in});
}

}  // namespace cma::tools
