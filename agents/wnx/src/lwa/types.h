// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef types_h
#define types_h

#include <limits.h>
#include <stdint.h>

#include <filesystem>
#include <functional>
#include <iostream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

#include "common/wtools.h"
#include "logger.h"

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
T from_string(const std::string &input);

template <>
bool from_string<bool>(const std::string &value);
template <>
int from_string<int>(const std::string &value);

template <>
std::string from_string<std::string>(const std::string &value);

template <>
std::filesystem::path from_string<std::filesystem::path>(
    const std::string &value);

// Needed for only_from
struct ipspec {
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
};

template <>
ipspec from_string<ipspec>(const std::string &value);

std::ostream &operator<<(std::ostream &os, const ipspec &ips);

ipspec toIPv6(const ipspec &ips);

using only_from_t = std::vector<ipspec>;

inline uint64_t to_u64(DWORD low, DWORD high) {
    return static_cast<uint64_t>(low) + (static_cast<uint64_t>(high) << 32);
}

struct winperf_counter {
    winperf_counter(int id_, const std::string &name_,
                    const std::string &base_id_)
        : id(id_), name(name_), base_id(base_id_) {}
    int id;
    std::string name;
    std::string base_id;
};

inline std::ostream &operator<<(std::ostream &out, const winperf_counter &wpc) {
    return out << "(id = " << wpc.id << ", name = " << wpc.name << ")";
}

template <typename T>
std::string ToYamlString(const T &Var, bool AsSequence) {
    std::stringstream o;
    o << Var;

    if (AsSequence) return std::string("- ") + o.str();
    return o.str();
}

template <>
std::string ToYamlString(const winperf_counter &wpc, bool);

inline std::string ToYamlKeyedString(const std::string &Key,
                                     const std::string &Pattern,
                                     const std::string &Value) {
    std::string out = "pattern: ";

    out += "'" + Pattern + "'\n";
    out += Key + ": " + Value;

    return out;
}

template <>
winperf_counter from_string<winperf_counter>(const std::string &value);

// Single element of a globline:
// C:/tmp/Testfile*.log
struct glob_token {
    std::string pattern;
    bool nocontext{false};
    bool from_start{false};
    bool rotated{false};
    bool found_match{false};
};

// Stores the condition pattern together with its state
// Pattern definition within the config file:
//      C = *critpatternglobdescription*
struct condition_pattern {
    condition_pattern(const char state_, const std::string glob_pattern_)
        : state(state_), glob_pattern(glob_pattern_) {}
    char state;
    std::string glob_pattern;
};

using condition_patterns_t = std::vector<condition_pattern>;

using glob_tokens_t = std::vector<glob_token>;

// Container for all globlines read from the config
// The following is considered a globline
// textfile = C:\Logfile1.txt C:\tmp\Logfile*.txt
struct globline_container {
    glob_tokens_t tokens;
    condition_patterns_t patterns;
};

using GlobListT = std::vector<globline_container>;

template <>
globline_container from_string<globline_container>(const std::string &value);

inline std::ostream &operator<<(std::ostream &os, const globline_container &g) {
    os << "\n[tokens]\n";
    for (const auto &token : g.tokens) {
        os << "<pattern: " << token.pattern << ", nocontext: " << std::boolalpha
           << token.nocontext << ", from_start: " << token.from_start
           << ", rotated: " << token.rotated
           << ", found_match: " << token.found_match << ">\n";
    }
    os << "[patterns]\n";
    for (const auto &pattern : g.patterns) {
        os << "<state: " << pattern.state
           << ", glob_pattern: " << pattern.glob_pattern << ">\n";
    }
    return os;
}

// How single scripts are executed
enum class script_execution_mode {
    SYNC,  // inline
    ASYNC  // delayed
};

inline std::ostream &operator<<(std::ostream &os,
                                const script_execution_mode mode) {
    return os << static_cast<unsigned>(mode);
}

// How delayed scripts are executed
enum class script_async_execution { PARALLEL, SEQUENTIAL };

inline std::ostream &operator<<(std::ostream &os,
                                const script_async_execution async) {
    return os << static_cast<unsigned>(async);
}

template <>
inline script_execution_mode from_string<script_execution_mode>(
    const std::string &value) {
    if (value == "async")
        return script_execution_mode::ASYNC;
    else if (value == "sync")
        return script_execution_mode::SYNC;
    throw std::runtime_error("invalid execution mode");
}

template <>
inline script_async_execution from_string<script_async_execution>(
    const std::string &value) {
    if (value == "parallel")
        return script_async_execution::PARALLEL;
    else if (value == "sequential")
        return script_async_execution::SEQUENTIAL;
    throw std::runtime_error("invalid async mode");
}

// Command definitions for MRPE
struct mrpe_entry {
    mrpe_entry(const std::string run_as_user_, const std::string command_line_,
               const std::string &plugin_name_,
               const std::string &service_description_)
        : run_as_user(run_as_user_)
        , command_line(command_line_)
        , plugin_name(plugin_name_)
        , service_description(service_description_) {}
    std::string run_as_user;
    std::string command_line;
    std::string plugin_name;
    std::string service_description;
};

inline std::ostream &operator<<(std::ostream &os, const mrpe_entry &entry) {
    os << "(" << entry.plugin_name << ") " << entry.service_description;
    return os;
}

using mrpe_entries_t = std::vector<mrpe_entry>;

template <>
mrpe_entry from_string<mrpe_entry>(const std::string &value);
template <>
std::string ToYamlString(const mrpe_entry &wpc, bool);

#if 0
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

    static void closeHandle(HandleT value) { ::CloseHandle(value); }
};

struct NullHandleTraits {
    using HandleT = HANDLE;
    static HandleT invalidValue() { return nullptr; }

    static void closeHandle(HandleT value) { ::CloseHandle(value); }
};

struct HModuleTraits {
    using HandleT = HMODULE;
    static HandleT invalidValue() { return nullptr; }

    static void closeHandle(HandleT value) { ::FreeLibrary(value); }
};

template <int exitCode>
struct JobHandleTraits {
    using HandleT = HANDLE;
    static HandleT invalidValue() { return nullptr; }

    static void closeHandle(HandleT value) {
        ::TerminateJobObject(value, exitCode);
        ::CloseHandle(value);
    }
};

using HModuleHandle = WrappedHandle<HModuleTraits>;
template <int exitCode>
using JobHandle = WrappedHandle<JobHandleTraits<exitCode>>;

struct HKeyHandleTraits {
    using HandleT = HKEY;
    static HandleT invalidValue() { return nullptr; }

    static void closeHandle(HandleT value) { ::RegCloseKey(value); }
};

using HKeyHandle = WrappedHandle<HKeyHandleTraits>;

struct ServiceHandleTraits {
    using HandleT = SC_HANDLE;
    static HandleT invalidValue() { return nullptr; }

    static void closeHandle(HandleT value) { ::CloseServiceHandle(value); }
};

using ServiceHandle = WrappedHandle<ServiceHandleTraits>;

struct SearchHandleTraits {
    using HandleT = HANDLE;
    static HandleT invalidValue() { return INVALID_HANDLE_VALUE; }

    static void closeHandle(HandleT value) { ::FindClose(value); }
};

using SearchHandle = WrappedHandle<SearchHandleTraits>;

template <typename PointerT>
struct LocalMemoryHandleTraits {
    using HandleT = PointerT;
    static HandleT invalidValue() { return nullptr; }

    static void closeHandle(HandleT value) { ::LocalFree(value); }
};

template <typename PointerT>
using LocalMemoryHandle = WrappedHandle<LocalMemoryHandleTraits<PointerT>>;
#endif

#endif  // types_h
