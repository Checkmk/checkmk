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
#include <functional>
#include <stdexcept>
#include <string>
#include <vector>
#undef CreateMutex
#include "WinApiAdaptor.h"
#undef _WIN32_WINNT
#define _WIN32_WINNT 0x0600

#if (__SIZEOF_POINTER__ == 8)
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

typedef short SHORT;

static const unsigned int SECTION_CHECK_MK = 0x00000001;
static const unsigned int SECTION_UPTIME = 0x00000002;
static const unsigned int SECTION_DF = 0x00000004;
static const unsigned int SECTION_PS = 0x00000008;
static const unsigned int SECTION_MEM = 0x00000010;
static const unsigned int SECTION_SERVICES = 0x00000020;
static const unsigned int SECTION_OHM = 0x00000040;
static const unsigned int SECTION_LOGWATCH = 0x00000080;
static const unsigned int SECTION_SYSTEMTIME = 0x00000100;
static const unsigned int SECTION_PLUGINS = 0x00000200;
static const unsigned int SECTION_LOCAL = 0x00000400;
static const unsigned int SECTION_SPOOL = 0x00000800;
static const unsigned int SECTION_MRPE = 0x00001000;
static const unsigned int SECTION_FILEINFO = 0x00002000;
static const unsigned int SECTION_LOGFILES = 0x00004000;
static const unsigned int SECTION_CRASHLOG = 0x00008000;
static const unsigned int SECTION_CPU = 0x00010000;
static const unsigned int SECTION_EXCHANGE = 0x00020000;
static const unsigned int SECTION_WEBSERVICES = 0x00040000;
static const unsigned int SECTION_DOTNET = 0x00080000;
static const unsigned int SECTION_WINPERF_IF = 0x00100000;
static const unsigned int SECTION_WINPERF_CPU = 0x00200000;
static const unsigned int SECTION_WINPERF_PHYDISK = 0x00400000;
static const unsigned int SECTION_WINPERF_CONFIG = 0x00800000;
static const unsigned int SECTION_SKYPE = 0x01000000;

static const unsigned int SECTION_WINPERF =
    SECTION_WINPERF_IF | SECTION_WINPERF_CPU | SECTION_WINPERF_PHYDISK |
    SECTION_WINPERF_CONFIG;

template <typename T>
T from_string(const WinApiAdaptor &winapi, const std::string &input);

template <>
bool from_string<bool>(const WinApiAdaptor &winapi, const std::string &value);
template <>
int from_string<int>(const WinApiAdaptor &winapi, const std::string &value);

template <>
std::string from_string<std::string>(const WinApiAdaptor &winapi,
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
ipspec *from_string<ipspec *>(const WinApiAdaptor &winapi,
                              const std::string &value);

// Configuration for section [winperf]
struct winperf_counter {
    int id;
    std::string name;
};

template <>
winperf_counter *from_string<winperf_counter *>(const WinApiAdaptor &winapi,
                                                const std::string &value);

// Configuration entries from [logwatch] for individual logfiles
struct eventlog_config_entry {
    eventlog_config_entry(int level, int hide_context, const char *name,
                          bool vista_api)
        : name(name)
        , level(level)
        , hide_context(hide_context)
        , vista_api(vista_api) {}

    std::string name;
    int level;
    int hide_context;
    bool vista_api;
};

template <>
eventlog_config_entry from_string<eventlog_config_entry>(
    const WinApiAdaptor &winapi, const std::string &value);

std::ostream &operator<<(std::ostream &out, const eventlog_config_entry &val);

// How single scripts are executed
enum script_execution_mode {
    SYNC,  // inline
    ASYNC  // delayed
};

template <>
script_execution_mode from_string<script_execution_mode>(
    const WinApiAdaptor &winapi, const std::string &value);

// How delayed scripts are executed
enum script_async_execution { PARALLEL, SEQUENTIAL };

template <>
script_async_execution from_string<script_async_execution>(
    const WinApiAdaptor &winapi, const std::string &value);

struct retry_config {
    char *pattern;
    int retries;
};

enum file_encoding {
    UNDEF,
    DEFAULT,
    UNICODE,
};

// Stores the condition pattern together with its state
// Pattern definition within the config file:
//      C = *critpatternglobdescription*
struct condition_pattern {
    char state;
    char *glob_pattern;
};
typedef std::vector<condition_pattern *> condition_patterns_t;

// A textfile instance containing information about various file
// parameters and the pointer to the matching pattern_container
struct logwatch_textfile {
    std::string name;  // name used for section headers. this is the
                       // filename for regular logs and the pattern
                       // for rotated logs
    std::vector<std::string> paths;
    unsigned long long file_id;    // used to detect if a file has been replaced
    unsigned long long file_size;  // size of the file
    unsigned long long offset{0};  // current fseek offset in the file
    bool missing{false};           // file no longer exists
    bool nocontext;                // do not report ignored lines
    bool rotated;                  // assume the logfile is a rotating log
    file_encoding encoding;
    condition_patterns_t *patterns;  // glob patterns applying for this file
};

// Single element of a globline:
// C:/tmp/Testfile*.log
struct glob_token {
    char *pattern;
    bool nocontext{false};
    bool from_start{false};
    bool rotated{false};
    bool found_match;
};
typedef std::vector<glob_token *> glob_tokens_t;

// Container for all globlines read from the config
// The following is considered a globline
// textfile = C:\Logfile1.txt C:\tmp\Logfile*.txt
struct globline_container {
    glob_tokens_t tokens;
    condition_patterns_t patterns;
};

// Command definitions for MRPE
struct mrpe_entry {
    char run_as_user[256];
    char command_line[256];
    char plugin_name[64];
    char service_description[256];
};

template <>
mrpe_entry *from_string<mrpe_entry *>(const WinApiAdaptor &winapi,
                                      const std::string &value);

// Our memory of what event logs we know and up to
// which record entry we have seen its messages so
// far.
struct eventlog_file_state {
    eventlog_file_state(const char *name)
        : name(name), newly_discovered(true) {}
    std::string name;
    uint64_t record_no;
    bool newly_discovered;
};

struct eventlog_hint_t {
    char *name;
    uint64_t record_no;
};

struct timeout_config {
    char *pattern;
    int timeout;
};

struct cache_config {
    char *pattern;
    int max_age;
};

struct execution_mode_config {
    char *pattern;
    script_execution_mode mode;
};

typedef std::vector<ipspec *> only_from_t;
typedef std::vector<globline_container *> logwatch_globlines_t;
typedef std::vector<eventlog_config_entry> eventlog_config_t;
typedef std::vector<mrpe_entry *> mrpe_entries_t;
typedef std::vector<eventlog_file_state> eventlog_state_t;
typedef std::vector<eventlog_hint_t *> eventlog_hints_t;
typedef std::vector<char *> fileinfo_paths_t;
typedef std::vector<retry_config *> retry_count_configs_t;
typedef std::vector<timeout_config *> timeout_configs_t;
typedef std::vector<cache_config *> cache_configs_t;
typedef std::vector<execution_mode_config *> execution_mode_configs_t;

// poor mans binder for a member function. Unnecessary if we ever use a C++11
// compiler
template <typename ObjectT, typename ReturnT>
class KVBind {
public:
    typedef ReturnT (ObjectT::*Function)(char *, char *);

    KVBind(ObjectT *obj = NULL) : _obj(obj), _func(NULL) {}

    void setFunc(Function func) { this->_func = func; }

    bool isUnset() const { return (_obj == NULL) || (_func == NULL); }

    ReturnT operator()(char *key, char *value) {
        return (_obj->*_func)(key, value);
    }

private:
    ObjectT *_obj;
    Function _func;
};

class Mutex {
    HANDLE _mutex;
    const WinApiAdaptor &_winapi;

public:
    explicit Mutex(const WinApiAdaptor &winapi) : _winapi(winapi) {
        _mutex = _winapi.CreateMutex(NULL, FALSE, NULL);
    }
    ~Mutex() { _winapi.CloseHandle(_mutex); }

    void lock() { _winapi.WaitForSingleObject(_mutex, INFINITE); }

    void unlock() { _winapi.ReleaseMutex(_mutex); }
};

class MutexLock {
    Mutex &_mutex;

public:
    MutexLock(Mutex &mutex) : _mutex(mutex) { _mutex.lock(); }

    ~MutexLock() { _mutex.unlock(); }
};

// wrapper for windows handles that automatically closes the
// handle on leaving scope
// FIXME: duplicate of ManagedHandle?
class WinHandle {
public:
    explicit WinHandle(const WinApiAdaptor &winapi,
                       HANDLE hdl = INVALID_HANDLE_VALUE)
        : _handle(hdl), _winapi(winapi) {}

    WinHandle(const WinHandle &reference) = delete;

    ~WinHandle() {
        if (_handle != INVALID_HANDLE_VALUE) {
            _winapi.CloseHandle(_handle);
        }
    }

    WinHandle &operator=(const WinHandle &reference) = delete;

    WinHandle &operator=(HANDLE hdl) {
        if (_handle != INVALID_HANDLE_VALUE) {
            _winapi.CloseHandle(_handle);
        }
        _handle = hdl;
        return *this;
    }

    operator HANDLE() const { return _handle; }

    HANDLE *ptr() { return &_handle; }

private:
    HANDLE _handle;
    const WinApiAdaptor &_winapi;
};

class OnScopeExit {
    std::function<void()> _cleaner;

public:
    OnScopeExit(const std::function<void()> &cleaner) : _cleaner(cleaner) {}
    ~OnScopeExit() { _cleaner(); }
};

inline uint64_t to_u64(DWORD low, DWORD high) {
    return static_cast<uint64_t>(low) + (static_cast<uint64_t>(high) << 32);
}

class ManagedHandle {
public:
    ManagedHandle(HANDLE handle, const WinApiAdaptor &winapi)
        : _handle(handle), _winapi(winapi) {}

    ~ManagedHandle() {
        if (_handle != nullptr) {
            _winapi.CloseHandle(_handle);
            _handle = nullptr;
        }
    }

    ManagedHandle(const ManagedHandle &) = delete;  // Delete copy constructor

    ManagedHandle &operator=(const ManagedHandle &) =
        delete;  // Delete assignment operator

    ManagedHandle(ManagedHandle &&from)
        : _handle(from._handle), _winapi(from._winapi) {  // Move constructor
        from._handle = nullptr;
    }

    ManagedHandle &operator=(ManagedHandle &&from) =
        delete;  // Move assignment operator

    //    ManagedHandle &operator=(ManagedHandle &&from) {              //
    //    Move assignment operator
    //        close();
    //        _handle = from._handle;
    //        from._handle = nullptr;
    //        return *this;
    //    }

    HANDLE get_handle() { return _handle; };

private:
    HANDLE _handle;
    const WinApiAdaptor &_winapi;
};

#endif  // types_h
