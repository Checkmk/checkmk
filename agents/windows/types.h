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

#ifndef types_h
#define types_h

#include <limits.h>
#include <stdint.h>
#include <experimental/filesystem>
#include <functional>
#include <iostream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>
#include "WinApiInterface.h"

#if (__SIZEOF_POINTER__ == 8 || defined(_WIN64))
#define PRIdword "d"
#define PRIudword "lu"
#define PRIdtime "lld"
#else
#define PRIdword "ld"
#define PRIudword "lu"
#define PRIdtime "ld"
#endif

#ifndef INVALID_HANDLE_VALUE
#define INVALID_HANDLE_VALUE ((HANDLE)(LONG_PTR)-1)
#endif  // INVALID_HANDLE_VALUE

namespace fs = std::experimental::filesystem;

class script_statistics_t {
public:
    script_statistics_t() { reset(); }
    script_statistics_t(script_statistics_t &) = delete;
    script_statistics_t &operator=(script_statistics_t &) = delete;

    void reset() {
        _statistics["plugin_count"] = 0;
        _statistics["plugin_errors"] = 0;
        _statistics["plugin_timeouts"] = 0;
        _statistics["local_count"] = 0;
        _statistics["local_errors"] = 0;
        _statistics["local_timeouts"] = 0;
    }

    unsigned &operator[](const std::string &key) { return _statistics[key]; }

private:
    std::unordered_map<std::string, unsigned> _statistics;
};

class StringConversionError : public std::invalid_argument {
public:
    explicit StringConversionError(const std::string &what)
        : std::invalid_argument(what) {}
};

template <typename T>
T from_string(const WinApiInterface &winapi, const std::string &input);

template <>
bool from_string<bool>(const WinApiInterface &, const std::string &value);
template <>
int from_string<int>(const WinApiInterface &, const std::string &value);

template <>
std::string from_string<std::string>(const WinApiInterface &,
                                     const std::string &value);

template <>
fs::path from_string<fs::path>(const WinApiInterface &,
                               const std::string &value);

// Needed for only_from
struct ipspec {
    explicit ipspec(const WinApiInterface &winapi_)
        : winapi(std::ref(winapi_)) {}
    union {
        struct {
            uint32_t address;
            uint32_t netmask;
        } v4;
        struct {
            uint16_t address[8];
            uint16_t netmask[8];
        } v6;
    } ip;
    int bits;
    bool ipv6;
    std::reference_wrapper<const WinApiInterface> winapi;
};

template <>
ipspec from_string<ipspec>(const WinApiInterface &winapi,
                           const std::string &value);

std::ostream &operator<<(std::ostream &os, const ipspec &ips);

ipspec toIPv6(const ipspec &ips, const WinApiInterface &winapi);

using only_from_t = std::vector<ipspec>;

class StateParseError : public std::invalid_argument {
public:
    explicit StateParseError(const std::string &what)
        : std::invalid_argument(what) {}
};

class OnScopeExit {
public:
    OnScopeExit(const std::function<void()> &cleaner) : _cleaner(cleaner) {}
    ~OnScopeExit() { _cleaner(); }

private:
    std::function<void()> _cleaner;
};

inline uint64_t to_u64(DWORD low, DWORD high) {
    return static_cast<uint64_t>(low) + (static_cast<uint64_t>(high) << 32);
}

template <typename HandleTraits, typename Api = WinApiInterface>
class WrappedHandle {
    using handle_t = typename HandleTraits::HandleT;

public:
    explicit WrappedHandle(const Api &api) noexcept
        : WrappedHandle(HandleTraits::invalidValue(), api) {}

    WrappedHandle(handle_t handle, const Api &api) noexcept
        : _handle(handle), _api(std::ref(api)) {}

    virtual ~WrappedHandle() { reset(); }

    WrappedHandle(const WrappedHandle &) = delete;
    WrappedHandle &operator=(const WrappedHandle &) = delete;

    WrappedHandle(WrappedHandle &&other)
        : _handle(other._handle), _api(std::move(other._api)) {
        other._handle = HandleTraits::invalidValue();
    }

    WrappedHandle &operator=(WrappedHandle &&rhs) noexcept {
        reset(rhs.release());
        _api = std::move(rhs._api);
        return *this;
    }

    handle_t release() noexcept {
        handle_t h = _handle;
        _handle = HandleTraits::invalidValue();
        return h;
    }

    void reset(handle_t handle = HandleTraits::invalidValue()) noexcept {
        using std::swap;
        swap(_handle, handle);
        if (handle != HandleTraits::invalidValue()) {
            HandleTraits::closeHandle(handle, _api.get());
        }
    }

    void swap(WrappedHandle &other) {
        using std::swap;
        swap(_handle, other._handle);
        swap(_api, other._api);
    }

    operator bool() const { return _handle != HandleTraits::invalidValue(); }

    handle_t get() const { return _handle; }

protected:
    handle_t _handle;
    std::reference_wrapper<const Api> _api;
};

template <typename HandleTraits, typename Api>
inline void swap(WrappedHandle<HandleTraits, Api> &x,
                 WrappedHandle<HandleTraits, Api> &y) noexcept {
    x.swap(y);
}

template <typename HandleTraits, typename Api>
inline bool operator==(const WrappedHandle<HandleTraits, Api> &x,
                       const WrappedHandle<HandleTraits, Api> &y) noexcept {
    return x.get() == y.get();
}

template <typename HandleTraits, typename Api>
inline bool operator!=(const WrappedHandle<HandleTraits, Api> &x,
                       const WrappedHandle<HandleTraits, Api> &y) noexcept {
    return !(x.get() == y.get());
}

template <typename HandleTraits, typename Api>
inline bool operator<(const WrappedHandle<HandleTraits, Api> &x,
                      const WrappedHandle<HandleTraits, Api> &y) noexcept {
    return x.get() < y.get();
}

template <typename HandleTraits, typename Api>
inline bool operator<=(const WrappedHandle<HandleTraits, Api> &x,
                       const WrappedHandle<HandleTraits, Api> &y) noexcept {
    return !(y.get() < x.get());
}

template <typename HandleTraits, typename Api>
inline bool operator>(const WrappedHandle<HandleTraits, Api> &x,
                      const WrappedHandle<HandleTraits, Api> &y) noexcept {
    return y.get() < x.get();
}

template <typename HandleTraits, typename Api>
inline bool operator>=(const WrappedHandle<HandleTraits, Api> &x,
                       const WrappedHandle<HandleTraits, Api> &y) noexcept {
    return !(x.get() < y.get());
}

template <typename HandleTraits, typename Api>
inline std::ostream &operator<<(std::ostream &os,
                                const WrappedHandle<HandleTraits, Api> &h) {
    return os << std::hex << h.get();
}

struct InvalidHandleTraits {
    using HandleT = HANDLE;
    static HandleT invalidValue() { return INVALID_HANDLE_VALUE; }

    static void closeHandle(HandleT value, const WinApiInterface &winapi) {
        winapi.CloseHandle(value);
    }
};

struct NullHandleTraits {
    using HandleT = HANDLE;
    static HandleT invalidValue() { return nullptr; }

    static void closeHandle(HandleT value, const WinApiInterface &winapi) {
        winapi.CloseHandle(value);
    }
};

struct HModuleTraits {
    using HandleT = HMODULE;
    static HandleT invalidValue() { return nullptr; }

    static void closeHandle(HandleT value, const WinApiInterface &winapi) {
        winapi.FreeLibrary(value);
    }
};

template <int exitCode>
struct JobHandleTraits {
    using HandleT = HANDLE;
    static HandleT invalidValue() { return nullptr; }

    static void closeHandle(HandleT value, const WinApiInterface &winapi) {
        winapi.TerminateJobObject(value, exitCode);
        winapi.CloseHandle(value);
    }
};

using HModuleHandle = WrappedHandle<HModuleTraits>;
template <int exitCode>
using JobHandle = WrappedHandle<JobHandleTraits<exitCode>>;

struct HKeyHandleTraits {
    using HandleT = HKEY;
    static HandleT invalidValue() { return nullptr; }

    static void closeHandle(HandleT value, const WinApiInterface &winapi) {
        winapi.RegCloseKey(value);
    }
};

using HKeyHandle = WrappedHandle<HKeyHandleTraits>;

struct ServiceHandleTraits {
    using HandleT = SC_HANDLE;
    static HandleT invalidValue() { return nullptr; }

    static void closeHandle(HandleT value, const WinApiInterface &winapi) {
        winapi.CloseServiceHandle(value);
    }
};

using ServiceHandle = WrappedHandle<ServiceHandleTraits>;

struct SearchHandleTraits {
    using HandleT = HANDLE;
    static HandleT invalidValue() { return INVALID_HANDLE_VALUE; }

    static void closeHandle(HandleT value, const WinApiInterface &winapi) {
        winapi.FindClose(value);
    }
};

using SearchHandle = WrappedHandle<SearchHandleTraits>;

template <typename PointerT>
struct LocalMemoryHandleTraits {
    using HandleT = PointerT;
    static HandleT invalidValue() { return nullptr; }

    static void closeHandle(HandleT value, const WinApiInterface &winapi) {
        winapi.LocalFree(value);
    }
};

template <typename PointerT>
using LocalMemoryHandle = WrappedHandle<LocalMemoryHandleTraits<PointerT>>;

#endif  // types_h
