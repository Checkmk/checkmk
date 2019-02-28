// Assorted routines
#pragma once

#include <string.h>
#include <cctype>

#include <chrono>
#include <cwctype>
#include <filesystem>
#include <optional>
#include <string>
#include <tuple>
#include <type_traits>
#include <vector>

#include "tools/_raii.h"
#include "tools/_tgt.h"
#include "tools/_xlog.h"

#include "fmt/format.h"

namespace cma::tools {

// gtest [+]
inline bool IsEqual(const std::string& Left, const std::string& Right) {
    return std::equal(Left.cbegin(), Left.cend(), Right.cbegin(), Right.cend(),
                      [](char LeftChar, char RightChar) {
                          return std::tolower(LeftChar) ==
                                 std::tolower(RightChar);
                      });
}

// returns true if left is Less than right
inline bool IsLess(const std::string& Left, const std::string& Right) {
    auto li = Left.cbegin();
    auto ri = Right.cbegin();
    for (; li != Left.cend() && ri != Right.cend(); ++ri, ++li) {
        auto right_char = std::tolower(*ri);
        auto left_char = std::tolower(*li);
        if (left_char != right_char) return left_char < right_char;
    }

    // If equal until here, lhs < rhs iff lhs shorter than rhs.
    return Left.size() < Right.size();
}

// Stupid Approach but C++ has no good methods to uppercase/lowercase string
// #TODO USE IBM ICU or Boost.Locale
inline void WideUpper(std::wstring& WideStr) {
    if constexpr (tgt::IsWindows()) {
        auto work_string = WideStr.data();
        CharUpperW(work_string);

    } else {
        // for windows doesn't work, for Linux probably too
        std::transform(WideStr.begin(), WideStr.end(), WideStr.begin(),
                       [](const wchar_t Ch) { return std::towupper(Ch); });
    }
}

// Stupid Approach but C++ has no good methods to uppercase/lowercase string
// #TODO USE IBM ICU or Boost.Locale
inline void WideLower(std::wstring& WideStr) {
    if constexpr (tgt::IsWindows()) {
        auto work_string = WideStr.data();
        CharLowerW(work_string);
    } else {
        // for windows doesn't work, for Linux probably too
        std::transform(WideStr.begin(), WideStr.end(), WideStr.begin(),
                       [](const wchar_t Ch) { return std::towlower(Ch); });
    }
}

// makes a vector from arbitrary objects
// Usage:
// auto vector_of string
template <typename... Args>
std::vector<std::wstring> ConstructVectorWstring(Args&&... args) {
    using namespace std;
    vector<wstring> cfg_files;
    static_assert((std::is_constructible_v<std::wstring, Args&> && ...));
    (cfg_files.emplace_back(args), ...);
    return cfg_files;
}

template <typename... Args>
auto ConstructVector(Args&... Str) {
    return std::vector{Str...};
};

inline bool IsRegularFileValid(std::filesystem::path& Path) {
    namespace fs = std::filesystem;
    std::error_code ec;
    if (!fs::exists(Path, ec)) {
        return false;
    }

    if (!fs::is_regular_file(Path)) {
        return false;
    }

    return true;
}

inline void AddDirSymbol(std::string& Dir) {
    std::filesystem::path p = Dir;
    p /= "";
    Dir = p.u8string();
}

inline void AddDirSymbol(std::wstring& Dir) {
    std::filesystem::path p = Dir;
    p /= "";
    Dir = p.wstring();
}

// useful tools to combine to buffers
// #TODO test!
template <typename T>
inline void AddVector(std::vector<char>& Accu, const T& Add) noexcept {
    auto add_size = Add.size();
    if (!add_size) return;
    auto old_size = Accu.size();
    try {
        Accu.resize(add_size + old_size);
        memcpy(Accu.data() + old_size, Add.data(), add_size);
    } catch (const std::exception& e) {
        xlog::l(XLOG_FLINE + " Out of memory %s", e.what());
        return;
    }
}

// #TODO test!
template <typename T>
inline void AddString(std::basic_string<T>& Accu,
                      const std::vector<T>& Add) noexcept {
    static_assert(sizeof(T) == 1, "only chars are supposed");
    auto add_size = Add.size();
    if (!add_size) return;
    auto old_size = Accu.size();
    try {
        Accu.resize(add_size + old_size);
        memcpy(Accu.data() + old_size, Add.data(), add_size);
    } catch (const std::exception& e) {
        xlog::l(XLOG_FLINE + " Out of *memory* %s", e.what());
        return;
    }
}

template <typename T>
auto ParseKeyValue(const std::basic_string<T> Arg, T Splitter) {
    auto end = Arg.find_first_of(Splitter);
    if (end == std::basic_string<T>::npos) {
        return std::make_tuple(std::basic_string<T>(), std::basic_string<T>());
    }
    auto key = Arg.substr(0, end);
    auto value = Arg.substr(end + 1);
    return std::make_tuple(key, value);
}

template <typename T>
auto ParseKeyValue(const T* Arg, T Splitter) {
    return ParseKeyValue(std::basic_string<T>(Arg), Splitter);
}

inline const std::string ConvertToString(const std::string& In) { return In; }

inline const std::string ConvertToString(const std::wstring& In) {
    std::string out(In.begin(), In.end());
    return out;
}

// calculates byte offset in arbitrary data
// returns void*
template <typename T>
void* GetOffsetInBytes(T* Object, size_t Offset) {
    return static_cast<void*>(reinterpret_cast<char*>(Object) + Offset);
}

// returns const void*. #TODO make it with templates C++
template <typename T>
const void* GetOffsetInBytes(const T* Object, size_t Offset) {
    return static_cast<const void*>(reinterpret_cast<const char*>(Object) +
                                    Offset);
}

template <typename T>
std::optional<uint32_t> ConvertToUint32(const T& Str) noexcept {
    try {
        return std::stoul(Str);
    } catch (const std::exception&) {
        return {};
    }
}

template <typename T>
std::optional<uint64_t> ConvertToUint64(const T& Str) noexcept {
    try {
        return std::stoull(Str);
    } catch (const std::exception&) {
        return {};
    }
}

// #TODO to be tested - do not use it
template <typename T, typename U>
U ConvertToUint(const T& Str, U Default) noexcept {
    static_assert(std::is_arithmetic<U> && std::is_unsigned<U>,
                  "U is not good type");
    try {
        if constexpr (sizeof(U) <= 4) return std::stoul(Str);
        return std::stoull(Str);
    } catch (const std::exception&) {
        return Default;
    }
}

template <typename T>
uint64_t ConvertToUint64(const T& Str, uint64_t Default) noexcept {
    try {
        return std::stoull(Str);
    } catch (const std::exception&) {
        return Default;
    }
}

#if defined(WINDOWS_OS)

namespace win {
// gtest [+]
// returns data from the root machine registry
inline uint32_t GetRegistryValue(const std::wstring Key,
                                 const std::wstring Value,
                                 uint32_t Default) noexcept {
    HKEY hkey = 0;
    auto result = ::RegOpenKeyW(HKEY_LOCAL_MACHINE, Key.c_str(), &hkey);
    if (ERROR_SUCCESS == result && hkey) {
        ON_OUT_OF_SCOPE(RegCloseKey(hkey));
        DWORD type = REG_DWORD;
        uint32_t buffer;
        DWORD count = sizeof(buffer);
        auto ret = RegQueryValueExW(hkey, Value.c_str(), 0, &type,
                                    reinterpret_cast<LPBYTE>(&buffer), &count);
        if (ret == ERROR_SUCCESS && count && type == REG_DWORD) {
            return buffer;
        }

        // failure here
        xlog::d(XLOG_FLINE + "Absent %ls%ls query return code %d", Key.c_str(),
                Value.c_str(), ret);
        return Default;
    }

    return Default;
}

inline std::wstring GetRegistryValue(const std::wstring Key,
                                     const std::wstring Value,
                                     const std::wstring Default) noexcept {
    HKEY hkey = 0;
    auto result = ::RegOpenKeyW(HKEY_LOCAL_MACHINE, Key.c_str(), &hkey);
    if (ERROR_SUCCESS == result && hkey) {
        ON_OUT_OF_SCOPE(RegCloseKey(hkey));
        DWORD type = REG_SZ;
        wchar_t buffer[512];
        DWORD count = sizeof(buffer);
        auto ret = RegQueryValueExW(hkey, Value.c_str(), 0, &type,
                                    reinterpret_cast<LPBYTE>(buffer), &count);

        // check for errors
        auto type_ok = type == REG_SZ || type == REG_EXPAND_SZ;
        if (count == 0 || !type_ok) {
            // failure here
            xlog::l(XLOG_FLINE + "Absent %ls %ls query return code %d",
                    Key.c_str(), Value.c_str(), ret);
            return Default;
        }

        if (ret == ERROR_SUCCESS) {
            return buffer;
        }

        if (ret == ERROR_MORE_DATA) {
            // realloc required
            DWORD type = REG_SZ;
            auto buffer_big = new wchar_t[count / sizeof(wchar_t) + 2];
            ON_OUT_OF_SCOPE(delete[] buffer_big);
            DWORD count = sizeof(count);
            ret =
                RegQueryValueExW(hkey, Value.c_str(), 0, &type,
                                 reinterpret_cast<LPBYTE>(buffer_big), &count);

            // check for errors
            type_ok = type == REG_SZ || type == REG_EXPAND_SZ;
            if (count == 0 || !type_ok) {
                // failure here
                xlog::l(XLOG_FLINE + "Absent %ls %ls query return code %d",
                        Key.c_str(), Value.c_str(), ret);
                return Default;
            }

            if (ret == ERROR_SUCCESS) {
                return buffer_big;
            }
            // failure here
            xlog::l(XLOG_FLINE + "Absent %ls%ls query return code %d",
                    Key.c_str(), Value.c_str(), ret);
        }
    }
    // failure here
    xlog::l(XLOG_FLINE + "Cannot open Key %ls query return code %d",
            Key.c_str(), result);
    return Default;
}

template <typename T>
inline bool SetEnv(const T* EnvVarName, const T* EnvVarValue) {}

template <typename T>
inline bool SetEnv(const std::basic_string<T>& EnvVarName,
                   const std::basic_string<T>& EnvVarValue) {
    auto cmd = EnvVarName;
    if constexpr (sizeof(T) == 1) {
        cmd += "=" + EnvVarValue;
        return _putenv(cmd.c_str()) == 0;
    } else {
        cmd += L"=" + EnvVarValue;
        return _wputenv(cmd.c_str()) == 0;
    }
}

template <typename T>
std::basic_string<T> GetEnv(const T* Name) {
    T remote_machine_string[MAX_PATH];
    remote_machine_string[0] = 0;

    // we need constexpr here to eliminate compilation error
    if constexpr (sizeof(T) == 1) {
        GetEnvironmentVariableA(Name, remote_machine_string, MAX_PATH);
    } else {
        GetEnvironmentVariableW(Name, remote_machine_string, MAX_PATH);
    }
    return std::basic_string<T>(remote_machine_string);
}

template <typename T>
std::basic_string<T> GetEnv(const std::basic_string<T>& Name) {
    return GetEnv(Name.c_str());
}

// #TODO check do we really need this.
inline ULONGLONG __stdcall PreVistaGetTickCount64() {
    LARGE_INTEGER freq;
    LARGE_INTEGER counter;
    if (TRUE != QueryPerformanceFrequency(&freq)) {
        assert(0 == 1);
        return 0;
    }
    assert(0 != freq.QuadPart);
    if (TRUE != QueryPerformanceCounter(&counter)) {
        assert(0 == 1);
        return 0;
    }
    return static_cast<ULONGLONG>(counter.QuadPart / (freq.QuadPart / 1000));
}

}  // namespace win
#endif

inline void LeftTrim(std::string& Str) {
    Str.erase(Str.begin(), std::find_if(Str.cbegin(), Str.cend(), [](int Ch) {
                  return !std::isspace(Ch);
              }));
}

inline void RightTrim(std::string& Str) {
    Str.erase(std::find_if(Str.crbegin(), Str.crend(),
                           [](int Ch) { return !std::isspace(Ch); })
                  .base(),
              Str.end());
}

inline void AllTrim(std::string& Str) {
    LeftTrim(Str);
    RightTrim(Str);
}

// string splitter
// gtest [+]
inline std::vector<std::string> SplitString(const std::string& In,
                                            const std::string Delim,
                                            int MaxCount = 0) noexcept {
    // sanity
    if (In.empty()) return {};
    if (Delim.empty()) return {In};

    size_t start = 0U;
    std::vector<std::string> result;

    auto end = In.find(Delim);
    while (end != std::string::npos) {
        result.push_back(In.substr(start, end - start));

        start = end + Delim.length();
        end = In.find(Delim, start);

        // check for a skipping rest
        if (result.size() == MaxCount) {
            end = std::string::npos;
            break;
        }
    }

    auto last_string = In.substr(start, end);
    if (!last_string.empty()) result.push_back(last_string);

    return result;
}

// "a.b.", "." => {"a", "b"}
// "a.b", "." => {"a", "b"}
// ".b", "." => { "b"}
inline std::vector<std::wstring> SplitString(const std::wstring& In,
                                             const std::wstring Delim,
                                             int MaxCount = 0) noexcept {
    // sanity
    if (In.empty()) return {};
    if (Delim.empty()) return {In};

    size_t start = 0U;
    std::vector<std::wstring> result;

    auto end = In.find(Delim);
    while (end != std::string::npos) {
        result.push_back(In.substr(start, end - start));

        start = end + Delim.length();
        end = In.find(Delim, start);

        // check for a skipping rest
        if (result.size() == MaxCount) {
            end = std::string::npos;
            break;
        }
    }

    auto last_string = In.substr(start, end);
    if (!last_string.empty()) result.push_back(last_string);

    return result;
}

// not used now!
inline std::vector<std::wstring> SplitStringExact(const std::wstring& In,
                                                  const std::wstring Delim,
                                                  int MaxCount = 0) noexcept {
    // sanity
    if (In.empty()) return {};
    if (Delim.empty()) return {In};

    size_t start = 0U;
    std::vector<std::wstring> result;

    auto end = In.find(Delim);
    while (end != std::string::npos) {
        result.push_back(In.substr(start, end - start));

        start = end + Delim.length();
        end = In.find(Delim, start);

        // check for a skipping rest
        if (result.size() == MaxCount) {
            end = std::string::npos;
            break;
        }
    }

    auto last_string = In.substr(start, end);
    result.push_back(last_string);

    return result;
}

// joiner :)
// ["a", "b", "c" ] + Separator:"," => "a,b,c"
// C++ is not happy with templating of this function
// we have to make call like JoinVector<wchar_t>
// so we have to implementations
inline std::wstring JoinVector(const std::vector<std::wstring> Values,
                               const std::wstring& Separator) {
    std::wstring values_string;
    size_t sz = 0;
    if (Values.size() == 0) {
        return {};
    }

    for_each(Values.begin(), Values.end(),
             [&sz](std::wstring Entry) { sz += Entry.size() + 1; });
    values_string.reserve(sz);

    values_string = *Values.begin();
    for_each(Values.begin() + 1, Values.end(),
             [&values_string, Separator](std::wstring Entry) {
                 values_string += Separator + Entry;
             });
    return values_string;
}

// version for string
inline std::string JoinVector(const std::vector<std::string> Values,
                              const std::string& Separator) {
    std::string values_string;
    size_t sz = 0;
    if (Values.size() == 0) {
        return {};
    }

    for_each(Values.begin(), Values.end(),
             [&sz](std::string Entry) { sz += Entry.size() + 1; });
    values_string.reserve(sz);

    values_string = *Values.begin();
    for_each(Values.begin() + 1, Values.end(),
             [&values_string, Separator](std::string Entry) {
                 values_string += Separator + Entry;
             });
    return values_string;
}

template <typename T>
bool Find(const std::vector<T>& Vector, const T& Value) {
    if (Vector.empty()) return false;

    auto found = std::find(Vector.begin(), Vector.end(), Value);
    return found != Vector.end();
}

inline std::string TimeToString(
    std::chrono::system_clock::time_point TimePoint) {
    auto in_time_t = std::chrono::system_clock::to_time_t(TimePoint);
    std::stringstream sss;
    auto loc_time = std::localtime(&in_time_t);
    auto p_time = std::put_time(loc_time, "%Y-%m-%d %T");
    sss << p_time << std::ends;
    return sss.str();
}

inline auto SecondsSinceEpoch() {
    auto time_since = std::chrono::system_clock::now().time_since_epoch();
    const std::chrono::duration<long long> now =
        std::chrono::duration_cast<std::chrono::seconds>(time_since);
    return now.count();
}

}  // namespace cma::tools

namespace fmt {

// formatter extender for variable count of parameters
template <typename... Args>
auto formatv(const std::string Format, const Args&... args) {
    std::string buffer;
    try {
        auto x = std::make_tuple(Format, args...);
        auto print_message = [&buffer](const auto&... args) {
            // return formatted value
            buffer = fmt::format(args...);
        };
        std::apply(print_message, x);
    } catch (const std::exception&) {
        // XLOG::l.crit("Invalid string to format \"{}\"", std::get<0>(x));
        XLOG::l.crit("Invalid string/parameters to format '{}'", Format);
    }
    return buffer;
}

}  // namespace fmt
