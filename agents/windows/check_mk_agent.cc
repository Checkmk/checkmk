// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
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

// Looking for documentation on Win32-API? Here are some of the
// documents that I used:

// Registry:
// http://msdn.microsoft.com/en-us/library/ms724897.aspx

// Eventlogs:
// http://msdn.microsoft.com/en-us/library/aa363672(VS.85).aspx
// http://msdn.microsoft.com/en-us/library/bb427356(VS.85).aspx

// System Error Codes:
// http://msdn.microsoft.com/en-us/library/ms681381(VS.85).aspx

// This program needs at least windows version 0x0500
// (Window 2000 / Windows XP)
#define WINVER 0x0500
// This define is required to use the function GetProcessHandleCount in
// the ps section. Only available in winxp upwards
#define _WIN32_WINNT 0x0501

#include <winsock2.h>
#include <ctype.h>  // isspace()
#include <dirent.h>
#include <locale.h>
#include <shellapi.h>
#include <stdarg.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <sys/time.h>
#include <sys/types.h>
#include <sys/types.h>
#include <time.h>
#include <tlhelp32.h>  // list of processes
#include <unistd.h>
#include <winbase.h>
#include <windows.h>
#include <winreg.h>  // performance counters from registry
#include <ws2ipdef.h>
#include <algorithm>
#include <map>
#include <string>
#include <vector>
#include "Configuration.h"
#include "Environment.h"
#include "ListenSocket.h"
#include "OHMMonitor.h"
#include "OutputProxy.h"
#include "PerfCounter.h"
#include "Thread.h"
#include "logging.h"
#include "stringutil.h"
#include "types.h"
#include "wmiHelper.h"
#include "EventLog.h"
#include "ExternalCmd.h"
#define __STDC_FORMAT_MACROS
#include <inttypes.h>

//  .----------------------------------------------------------------------.
//  |       ____            _                 _   _                        |
//  |      |  _ \  ___  ___| | __ _ _ __ __ _| |_(_) ___  _ __  ___        |
//  |      | | | |/ _ \/ __| |/ _` | '__/ _` | __| |/ _ \| '_ \/ __|       |
//  |      | |_| |  __/ (__| | (_| | | | (_| | |_| | (_) | | | \__ \       |
//  |      |____/ \___|\___|_|\__,_|_|  \__,_|\__|_|\___/|_| |_|___/       |
//  |                                                                      |
//  +----------------------------------------------------------------------+
//  | Declarations of macrosk, structs and function prototypes             |
//  '----------------------------------------------------------------------'

const char *check_mk_version = CHECK_MK_VERSION;

static const char RT_PROTOCOL_VERSION[2] = {'0', '0'};

#define SERVICE_NAME "Check_MK_Agent"
#define KiloByte 1024

// Limits for static global arrays
#define MAX_EVENTLOGS 128

// Maximum heap buffer for a single local/plugin script
// This buffer contains the check output
#define HEAP_BUFFER_DEFAULT 16384L
#define HEAP_BUFFER_MAX 2097152L

// Maximum timeout for a single local/plugin script
#define DEFAULT_PLUGIN_TIMEOUT 60
#define DEFAULT_LOCAL_TIMEOUT 60

// Check compilation environment 32/64 bit
#if _WIN32 || _WIN64
#if _WIN64
#define ENVIRONMENT64
#else
#define ENVIRONMENT32
#endif
#endif

using namespace std;

typedef map<string, script_container *> script_containers_t;
script_containers_t script_containers;

struct process_entry {
    unsigned long long process_id;
    unsigned long long working_set_size;
    unsigned long long pagefile_usage;
    unsigned long long virtual_size;
};
typedef map<unsigned long long, process_entry> process_entry_t;

// Forward declarations of functions
void listen_tcp_loop(const Environment &env);
void output_data(OutputProxy &out, const Environment &env,
                 unsigned long sectionMask, bool section_flush);
double file_time(const FILETIME *filetime);
void lowercase(char *value);
void collect_script_data(script_execution_mode mode);
void find_scripts(const Environment &env);
void RunImmediate(const char *mode, int argc, char **argv);
void prepare_sections(const Environment &env);

//  .----------------------------------------------------------------------.
//  |                    ____ _       _           _                        |
//  |                   / ___| | ___ | |__   __ _| |___                    |
//  |                  | |  _| |/ _ \| '_ \ / _` | / __|                   |
//  |                  | |_| | | (_) | |_) | (_| | \__ \                   |
//  |                   \____|_|\___/|_.__/ \__,_|_|___/                   |
//  |                                                                      |
//  +----------------------------------------------------------------------+
//  | Global variables                                                     |
//  '----------------------------------------------------------------------'

bool verbose_mode = false;
bool with_stderr = false;
bool do_file = false;
static FILE *fileout;

// Statistical values
struct script_statistics_t {
    int pl_count;
    int pl_errors;
    int pl_timeouts;
    int lo_count;
    int lo_errors;
    int lo_timeouts;
} g_script_stat;

// Thread relevant variables
volatile bool g_should_terminate = false;
volatile bool g_data_collection_retriggered = false;
HANDLE g_collection_thread;

// Job object for all worker threads
// Gets terminated on shutdown
HANDLE g_workers_job_object;

// Mutex for crash.log
HANDLE g_crashlogMutex = CreateMutex(NULL, FALSE, NULL);

// Variables for section <<<logwatch>>>
bool logwatch_suppress_info = true;

Configuration *g_config;

char g_crash_log[256];
char g_connection_log[256];
char g_success_log[256];

mrpe_entries_t g_included_mrpe_entries;

eventlog_hints_t g_eventlog_hints;
eventlog_state_t g_eventlog_state;

bool g_found_crash = false;

std::unique_ptr<OHMMonitor> g_ohmMonitor;

class WMILookup {
public:
    static wmi::Helper &get(const std::wstring &path = L"Root\\Cimv2") {
        WMILookup &inst = instance();
        auto iter = inst._helpers.find(path);
        if (iter == inst._helpers.end()) {
            iter = inst._helpers
                       .insert(std::make_pair(
                           path, std::unique_ptr<wmi::Helper>(
                                     new wmi::Helper(path.c_str()))))
                       .first;
        }
        return *iter->second;
    }

    static void clear() { instance()._helpers.clear(); }

private:
    static WMILookup &instance() {
        static WMILookup instance;
        return instance;
    }
    WMILookup() {}

private:
    std::map<std::wstring, std::unique_ptr<wmi::Helper>> _helpers;
};

//  .----------------------------------------------------------------------.
//  |                  _   _      _                                        |
//  |                 | | | | ___| |_ __   ___ _ __ ___                    |
//  |                 | |_| |/ _ \ | '_ \ / _ \ '__/ __|                   |
//  |                 |  _  |  __/ | |_) |  __/ |  \__ \                   |
//  |                 |_| |_|\___|_| .__/ \___|_|  |___/                   |
//  |                              |_|                                     |
//  +----------------------------------------------------------------------+
//  | Global helper functions                                              |
//  '----------------------------------------------------------------------'


double current_time() {
    SYSTEMTIME systime;
    FILETIME filetime;
    GetSystemTime(&systime);
    SystemTimeToFileTime(&systime, &filetime);
    return file_time(&filetime);
}

double file_time(const FILETIME *filetime) {
    static const double SEC_TO_UNIX_EPOCH = 11644473600.0;
    static const double WINDOWS_TICK = 10000000.0;

    _ULARGE_INTEGER uli;
    uli.LowPart = filetime->dwLowDateTime;
    uli.HighPart = filetime->dwHighDateTime;

    return (double(uli.QuadPart) / WINDOWS_TICK) - SEC_TO_UNIX_EPOCH;
}

void char_replace(char what, char into, char *in) {
    while (*in) {
        if (*in == what) *in = into;
        in++;
    }
}

// Debug function for script containers
void debug_script_container(script_container *container) {
    crash_log("command:     %s", container->path);
    crash_log("cache age:   %d", container->max_age);
    crash_log("timeout:     %d", container->timeout);
    crash_log("time:        %d", (int)container->buffer_time);
    crash_log("status:      %d", container->status);
    crash_log("buffer:      \n<<<<\n%s\n>>>>", container->buffer);
    crash_log("buffer_work: \n<<<<\n%s\n>>>>", container->buffer_work);
}


template <typename T>
bool in_set(const T &val, const std::set<T> &test_set) {
    return test_set.find(val) != test_set.end();
}


template <typename FuncT>
FuncT dynamic_func(LPCWSTR dllName, LPCSTR funcName) {
    HMODULE mod = LoadLibraryW(dllName);
    if (mod != NULL) {
        FARPROC proc = GetProcAddress(mod, funcName);
        if (proc != NULL) {
            return (FuncT)proc;
        }
    }
    return NULL;
}

#define DYNAMIC_FUNC(func, dllName) \
    func##_type func##_dyn = dynamic_func<func##_type>(dllName, #func)
// GetProcessHandleCount_type GetProcessHandleCount_dyn =
// dynamic_func<GetProcessHandleCount_type>(L"kernel32.dll",
// "GetProcessHandleCount");

//  .----------------------------------------------------------------------.
//  |  ______              _                 _   _               ______    |
//  | / / / /___ _   _ ___| |_ ___ _ __ ___ | |_(_)_ __ ___   ___\ \ \ \   |
//  |/ / / // __| | | / __| __/ _ \ '_ ` _ \| __| | '_ ` _ \ / _ \\ \ \ \  |
//  |\ \ \ \\__ \ |_| \__ \ ||  __/ | | | | | |_| | | | | | |  __// / / /  |
//  | \_\_\_\___/\__, |___/\__\___|_| |_| |_|\__|_|_| |_| |_|\___/_/_/_/   |
//  |            |___/                                                     |
//  '----------------------------------------------------------------------'

void section_systemtime(OutputProxy &out) {
    crash_log("<<<systemtime>>>");
    out.output(
        "<<<systemtime>>>\n"
        "%.0f\n",
        current_time());
}

//  .----------------------------------------------------------------------.
//  |          ______              _   _                 ______            |
//  |         / / / /  _   _ _ __ | |_(_)_ __ ___   ___  \ \ \ \           |
//  |        / / / /  | | | | '_ \| __| | '_ ` _ \ / _ \  \ \ \ \          |
//  |        \ \ \ \  | |_| | |_) | |_| | | | | | |  __/  / / / /          |
//  |         \_\_\_\  \__,_| .__/ \__|_|_| |_| |_|\___| /_/_/_/           |
//  |                       |_|                                            |
//  '----------------------------------------------------------------------'

void section_uptime(OutputProxy &out) {
    crash_log("<<<uptime>>>");

    std::string uptime;

    typedef ULONGLONG WINAPI (*GetTickCount64_type)(void);
    DYNAMIC_FUNC(GetTickCount64, L"kernel32.dll");
    if (GetTickCount64_dyn != nullptr) {
        // GetTickCount64 is only available on Vista/2008 and newer
        uptime = std::to_string(GetTickCount64_dyn() / 1000);
    } else {
        int tries = 2;
        while (tries-- > 0) {
            // fallback if GetTickCount64 is not available
            try {
                wmi::Result res = WMILookup::get().query(
                    L"SELECT SystemUpTime FROM "
                    L"Win32_PerfFormattedData_PerfOS_System");
                if (res.valid()) {
                    uptime = res.get<std::string>(L"SystemUpTime");
                }
            } catch (const wmi::ComException &e) {
                crash_log("wmi request for SystemUpTime failed: %s", e.what());
            }
        }
    }

    if (!uptime.empty()) {
        out.output(
            "<<<uptime>>>\n"
            "%s\n",
            uptime.c_str());
    }
}

//  .----------------------------------------------------------------------.
//  |                      ______      _  __  ______                       |
//  |                     / / / /   __| |/ _| \ \ \ \                      |
//  |                    / / / /   / _` | |_   \ \ \ \                     |
//  |                    \ \ \ \  | (_| |  _|  / / / /                     |
//  |                     \_\_\_\  \__,_|_|   /_/_/_/                      |
//  |                                                                      |
//  '----------------------------------------------------------------------'

void df_output_filesystem(OutputProxy &out, char *volid) {
    TCHAR fsname[128];
    TCHAR volume[512];
    DWORD dwSysFlags = 0;
    if (!GetVolumeInformation(volid, volume, sizeof(volume), 0, 0, &dwSysFlags,
                              fsname, sizeof(fsname)))
        fsname[0] = 0;

    ULARGE_INTEGER free_avail, total, free;
    free_avail.QuadPart = 0;
    total.QuadPart = 0;
    free.QuadPart = 0;
    int returnvalue = GetDiskFreeSpaceEx(volid, &free_avail, &total, &free);
    if (returnvalue > 0) {
        double perc_used = 0;
        if (total.QuadPart > 0)
            perc_used = 100 - (100 * free_avail.QuadPart / total.QuadPart);

        if (volume[0])  // have a volume name
            char_replace(' ', '_', volume);
        else
            strncpy(volume, volid, sizeof(volume));

        out.output("%s\t%s\t", volume, fsname);
        out.output("%" PRIu64 "\t", total.QuadPart / KiloByte);
        out.output("%" PRIu64 "\t",
                   (total.QuadPart - free_avail.QuadPart) / KiloByte);
        out.output("%" PRIu64 "\t", free_avail.QuadPart / KiloByte);
        out.output("%3.0f%%\t", perc_used);
        out.output("%s\n", volid);
    }
}

void df_output_mountpoints(OutputProxy &out, char *volid) {
    char mountpoint[512];
    HANDLE hPt =
        FindFirstVolumeMountPoint(volid, mountpoint, sizeof(mountpoint));
    if (hPt != INVALID_HANDLE_VALUE) {
        while (true) {
            TCHAR combined_path[1024];
            snprintf(combined_path, sizeof(combined_path), "%s%s", volid,
                     mountpoint);
            df_output_filesystem(out, combined_path);
            if (!FindNextVolumeMountPoint(hPt, mountpoint, sizeof(mountpoint)))
                break;
        }
        FindVolumeMountPointClose(hPt);
    }
}

void section_df(OutputProxy &out) {
    crash_log("<<<df:sep(9)>>>");
    out.output("<<<df:sep(9)>>>\n");
    TCHAR buffer[4096];
    DWORD len = GetLogicalDriveStrings(sizeof(buffer), buffer);

    TCHAR *end = buffer + len;
    TCHAR *drive = buffer;
    while (drive < end) {
        UINT drvType = GetDriveType(drive);
        if (drvType == DRIVE_FIXED)  // only process local harddisks
        {
            df_output_filesystem(out, drive);
            df_output_mountpoints(out, drive);
        }
        drive += strlen(drive) + 1;
    }

    // Output volumes, that have no drive letter. The following code
    // works, but then we have no information about the drive letters.
    // And if we run both, then volumes are printed twice. So currently
    // we output only fixed drives and mount points below those fixed
    // drives.

    // HANDLE hVolume;
    // char volid[512];
    // hVolume = FindFirstVolume(volid, sizeof(volid));
    // if (hVolume != INVALID_HANDLE_VALUE) {
    //     df_output_filesystem(out, volid);
    //     while (true) {
    //         // df_output_mountpoints(out, volid);
    //         if (!FindNextVolume(hVolume, volid, sizeof(volid)))
    //             break;
    //     }
    //     FindVolumeClose(hVolume);
    // }
}

//  .----------------------------------------------------------------------.
//  |         ______                      _                ______          |
//  |        / / / /  ___  ___ _ ____   _(_) ___ ___  ___  \ \ \ \         |
//  |       / / / /  / __|/ _ \ '__\ \ / / |/ __/ _ \/ __|  \ \ \ \        |
//  |       \ \ \ \  \__ \  __/ |   \ V /| | (_|  __/\__ \  / / / /        |
//  |        \_\_\_\ |___/\___|_|    \_/ |_|\___\___||___/ /_/_/_/         |
//  |                                                                      |
//  '----------------------------------------------------------------------'

// Determine the start type of a service. Unbelievable how much
// code is needed for that...
const char *service_start_type(SC_HANDLE scm, LPCWSTR service_name) {
    // Query the start type of the service
    const char *start_type = "invalid1";
    SC_HANDLE schService;
    LPQUERY_SERVICE_CONFIG lpsc;
    schService = OpenServiceW(scm, service_name, SERVICE_QUERY_CONFIG);
    if (schService) {
        start_type = "invalid2";
        DWORD dwBytesNeeded, cbBufSize;
        if (!QueryServiceConfig(schService, NULL, 0, &dwBytesNeeded)) {
            start_type = "invalid3";
            DWORD dwError = GetLastError();
            if (dwError == ERROR_INSUFFICIENT_BUFFER) {
                start_type = "invalid4";
                cbBufSize = dwBytesNeeded;
                lpsc =
                    (LPQUERY_SERVICE_CONFIG)LocalAlloc(LMEM_FIXED, cbBufSize);
                if (QueryServiceConfig(schService, lpsc, cbBufSize,
                                       &dwBytesNeeded)) {
                    switch (lpsc->dwStartType) {
                        case SERVICE_AUTO_START:
                            start_type = "auto";
                            break;
                        case SERVICE_BOOT_START:
                            start_type = "boot";
                            break;
                        case SERVICE_DEMAND_START:
                            start_type = "demand";
                            break;
                        case SERVICE_DISABLED:
                            start_type = "disabled";
                            break;
                        case SERVICE_SYSTEM_START:
                            start_type = "system";
                            break;
                        default:
                            start_type = "other";
                    }
                }
                LocalFree(lpsc);
            }
        }
        CloseServiceHandle(schService);
    }
    return start_type;
}

void section_services(OutputProxy &out) {
    crash_log("<<<services>>>");
    out.output("<<<services>>>\n");
    SC_HANDLE scm =
        OpenSCManager(0, 0, SC_MANAGER_CONNECT | SC_MANAGER_ENUMERATE_SERVICE);
    if (scm != INVALID_HANDLE_VALUE) {
        DWORD bytes_needed = 0;
        DWORD num_services = 0;
        // first determine number of bytes needed
        EnumServicesStatusExW(scm, SC_ENUM_PROCESS_INFO, SERVICE_WIN32,
                              SERVICE_STATE_ALL, NULL, 0, &bytes_needed,
                              &num_services, 0, 0);
        if (GetLastError() == ERROR_MORE_DATA && bytes_needed > 0) {
            BYTE *buffer = (BYTE *)malloc(bytes_needed);
            if (buffer) {
                if (EnumServicesStatusExW(scm, SC_ENUM_PROCESS_INFO,
                                          SERVICE_WIN32, SERVICE_STATE_ALL,
                                          buffer, bytes_needed, &bytes_needed,
                                          &num_services, 0, 0)) {
                    ENUM_SERVICE_STATUS_PROCESSW *service =
                        (ENUM_SERVICE_STATUS_PROCESSW *)buffer;
                    for (unsigned i = 0; i < num_services; i++) {
                        DWORD state =
                            service->ServiceStatusProcess.dwCurrentState;
                        const char *state_name = "unknown";
                        switch (state) {
                            case SERVICE_CONTINUE_PENDING:
                                state_name = "continuing";
                                break;
                            case SERVICE_PAUSE_PENDING:
                                state_name = "pausing";
                                break;
                            case SERVICE_PAUSED:
                                state_name = "paused";
                                break;
                            case SERVICE_RUNNING:
                                state_name = "running";
                                break;
                            case SERVICE_START_PENDING:
                                state_name = "starting";
                                break;
                            case SERVICE_STOP_PENDING:
                                state_name = "stopping";
                                break;
                            case SERVICE_STOPPED:
                                state_name = "stopped";
                                break;
                        }

                        const char *start_type =
                            service_start_type(scm, service->lpServiceName);

                        // The service name usually does not contain spaces. But
                        // in some cases it does. We replace them with _ in
                        // order
                        // the keep it in one space-separated column. Since we
                        // own
                        // the buffer, we can simply change the name inplace.
                        for (LPWSTR w = service->lpServiceName; *w; ++w) {
                            if (*w == L' ') *w = L'_';
                        }

                        out.output("%ls %s/%s %s\n", service->lpServiceName,
                                   state_name, start_type,
                                   to_utf8(service->lpDisplayName).c_str());
                        service++;
                    }
                }
                free(buffer);
            }
        }
        CloseServiceHandle(scm);
    }
}

//  .----------------------------------------------------------------------.
//  |    ______           _                        __          ______      |
//  |   / / / / __      _(_)_ __  _ __   ___ _ __ / _|         \ \ \ \     |
//  |  / / / /  \ \ /\ / / | '_ \| '_ \ / _ \ '__| |_           \ \ \ \    |
//  |  \ \ \ \   \ V  V /| | | | | |_) |  __/ |  |  _|  _ _ _   / / / /    |
//  |   \_\_\_\   \_/\_/ |_|_| |_| .__/ \___|_|  |_|___(_|_|_) /_/_/_/     |
//  |                            |_|              |_____|                  |
//  '----------------------------------------------------------------------'

void dump_performance_counters(OutputProxy &out, unsigned counter_base_number,
                               const char *countername) {
    crash_log("<<<winperf_%s>>>", countername);

    try {
        PerfCounterObject counterObject(counter_base_number);

        if (!counterObject.isEmpty()) {
            LARGE_INTEGER Frequency;
            QueryPerformanceFrequency(&Frequency);
            out.output("<<<winperf_%s>>>\n", countername);
            out.output("%.2f %u %" PRId64 "\n", current_time(), counter_base_number,
                       Frequency.QuadPart);

            std::vector<PERF_INSTANCE_DEFINITION *> instances =
                counterObject.instances();
            // output instances - if any
            if (instances.size() > 0) {
                out.output("%d instances:", static_cast<int>(instances.size()));
                for (std::wstring name : counterObject.instanceNames()) {
                    std::replace(name.begin(), name.end(), L' ', L'_');
                    out.output(" %s", to_utf8(name.c_str()).c_str());
                }
                out.output("\n");
            }

            // output counters
            for (const PerfCounter &counter : counterObject.counters()) {
                out.output("%d", static_cast<int>(counter.titleIndex()) -
                                     static_cast<int>(counter_base_number));
                for (ULONGLONG value : counter.values(instances)) {
                    out.output(" %" PRIu64, value);
                }
                out.output(" %s\n", counter.typeName().c_str());
            }
        }
    } catch (const std::exception &e) {
        crash_log("Exception: %s", e.what());
    }
}

//  .----------------------------------------------------------------------.
//  |      ______  _                           _       _      ______       |
//  |     / / / / | | ___   __ ___      ____ _| |_ ___| |__   \ \ \ \      |
//  |    / / / /  | |/ _ \ / _` \ \ /\ / / _` | __/ __| '_ \   \ \ \ \     |
//  |    \ \ \ \  | | (_) | (_| |\ V  V / (_| | || (__| | | |  / / / /     |
//  |     \_\_\_\ |_|\___/ \__, | \_/\_/ \__,_|\__\___|_| |_| /_/_/_/      |
//  |                      |___/                                           |
//  '----------------------------------------------------------------------'


// loads a dll while ignoring blacklisted dlls and with support for
// environment variables in the path
HMODULE load_library_ext(const char *dllpath) {
    HMODULE dll = nullptr;

    // this should be sufficient most of the time
    static const size_t INIT_BUFFER_SIZE = 128;

    std::string dllpath_expanded;
    dllpath_expanded.resize(INIT_BUFFER_SIZE, '\0');
    DWORD required = ExpandEnvironmentStrings(dllpath, &dllpath_expanded[0],
                                              dllpath_expanded.size());
    if (required > dllpath_expanded.size()) {
        dllpath_expanded.resize(required + 1);
        required = ExpandEnvironmentStrings(dllpath, &dllpath_expanded[0],
                                            dllpath_expanded.size());
    } else if (required == 0) {
        dllpath_expanded = dllpath;
    }
    if (required != 0) {
        // required includes the zero terminator
        dllpath_expanded.resize(required - 1);
    }

    // load the library as a datafile without loading refernced dlls. This is
    // quicker but most of all it prevents problems if dependent dlls can't be
    // loaded.
    dll =
        LoadLibraryExA(dllpath_expanded.c_str(), nullptr,
                       DONT_RESOLVE_DLL_REFERENCES | LOAD_LIBRARY_AS_DATAFILE);
    return dll;
}

bool output_eventlog_entry(OutputProxy &out, const char *dllpath,
                           EVENTLOGRECORD *event, char type_char,
                           const char *logname, const char *source_name,
                           const WCHAR **strings,
                           std::map<std::string, HMODULE> &handle_cache) {
    char msgbuffer[8192];

    HMODULE dll = nullptr;

    // if dllpath is NULL, we output the message without text conversion and
    // always succeed. If a dll pathpath is given, we only succeed if the
    // conversion
    // is successfull.

    if (dllpath) {
        auto iter = handle_cache.find(dllpath);
        if (iter == handle_cache.end()) {
            dll = load_library_ext(dllpath);
            iter = handle_cache.insert(std::make_pair(std::string(dllpath), dll)).first;
        } else {
            dll = iter->second;
        }
        if (!dll) {
            crash_log("     --> failed to load %s", dllpath);
            return false;
        }
    } else
        dll = NULL;

    WCHAR wmsgbuffer[8192];
    DWORD dwFlags = FORMAT_MESSAGE_ARGUMENT_ARRAY | FORMAT_MESSAGE_FROM_SYSTEM;
    if (dll) dwFlags |= FORMAT_MESSAGE_FROM_HMODULE;

    crash_log("Event ID: %lu.%lu",
              event->EventID / 65536,   // "Qualifiers": no idea what *that* is
              event->EventID % 65536);  // the actual event id
    crash_log("Formatting Message");
    DWORD len = FormatMessageW(dwFlags, dll, event->EventID,
                               0,  // accept any language
                               wmsgbuffer,
                               // msgbuffer,
                               8192, (char **)strings);
    crash_log("Formatting Message - DONE");

    if (len) {
        // convert message to UTF-8
        len = WideCharToMultiByte(CP_UTF8, 0, wmsgbuffer, -1, msgbuffer,
                                  sizeof(msgbuffer), NULL, NULL);
    }

    if (len == 0)  // message could not be converted
    {
        // if conversion was not successfull while trying to load a DLL, we
        // return a
        // failure. Our parent function will then retry later without a DLL
        // path.
        if (dllpath) return false;

        // if message cannot be converted, then at least output the text
        // strings.
        // We render all messages one after the other into msgbuffer, separated
        // by spaces.
        memset(msgbuffer, 0,
               sizeof(msgbuffer));  // avoids problems with 0-termination
        char *w = msgbuffer;
        int sizeleft = sizeof(msgbuffer) - 1;  // leave one byte for termination
        int n = 0;
        while (strings[n])  // string array is zero terminated
        {
            const WCHAR *s = strings[n];
            DWORD len =
                WideCharToMultiByte(CP_UTF8, 0, s, -1, w, sizeleft, NULL, NULL);
            if (!len) break;
            sizeleft -= len;
            w += len;
            if (sizeleft <= 0) break;
            n++;
            if (strings[n]) *w++ = ' ';
        }
    }

    // replace newlines with spaces. check_mk expects one message each line.
    char *w = msgbuffer;
    while (*w) {
        if (*w == '\n' || *w == '\r') *w = ' ';
        w++;
    }

    // convert UNIX timestamp to local time
    time_t time_generated = (time_t)event->TimeGenerated;
    struct tm *t = localtime(&time_generated);
    char timestamp[64];
    strftime(timestamp, sizeof(timestamp), "%b %d %H:%M:%S", t);

    out.output("%c %s %lu.%lu %s %s\n", type_char, timestamp,
               event->EventID / 65536,  // "Qualifiers": no idea what *that* is
               event->EventID % 65536,  // the actual event id
               source_name, msgbuffer);
    return true;
}

std::pair<char, int> determine_event_state(EVENTLOGRECORD *event, int level) {
    switch (event->EventType) {
        case EVENTLOG_ERROR_TYPE:
            return {'C', 2};
        case EVENTLOG_WARNING_TYPE:
            return {'W', 1};
        case EVENTLOG_INFORMATION_TYPE:
        case EVENTLOG_AUDIT_SUCCESS:
        case EVENTLOG_SUCCESS:
            if (level == 0)
                return {'O', 0};
            else
                return {'.', 0};
        case EVENTLOG_AUDIT_FAILURE:
            return {'C', 2};
        default:
            return {'u', 1};
    }
}

void process_eventlog_entry(OutputProxy &out, EventLog &event_log,
                            EVENTLOGRECORD *event, int level, int hide_context,
                            std::map<std::string, HMODULE> &handle_cache) {
    char type_char;
    int this_state;
    std::tie(type_char, this_state) = determine_event_state(event, level);

    if (hide_context && (type_char == '.')) {
        return;
    }

    // source is the application that produced the event
    std::string source_name = to_utf8((WCHAR *)(event + 1));
    std::replace(source_name.begin(), source_name.end(), ' ', '_');

    // prepare array of zero terminated strings to be inserted
    // into message template.
    std::vector<const WCHAR*> strings;
    const WCHAR *string = (WCHAR *)(((char *)event) + event->StringOffset);
    for (int i = 0; i < event->NumStrings; ++i) {
        strings.push_back(string);
        string += wcslen(string) + 1;
    }

    // Sometimes the eventlog record does not provide
    // enough strings for the message template. Causes crash...
    // -> Fill the rest with empty strings
    strings.resize(63, L"");
    // end marker in array
    strings.push_back(nullptr);

    // To save space and to make log messages localizable, each
    // eventlog entry only contains an id and the variable parameters of
    // a message.
    // The actual error string has to be retrieved from a dll, usually
    // the one that caused the error.
    std::vector<std::string> message_files =
        event_log.getMessageFiles(source_name.c_str());

    bool success = false;
    for (const std::string &message_file : message_files) {
        if (output_eventlog_entry(out, message_file.c_str(), event, type_char,
                                  event_log.getName().c_str(),
                                  source_name.c_str(), &strings[0],
                                  handle_cache)) {
            success = true;
        }
    }

    if (!success) {
        if (message_files.size() == 0) {
            crash_log("     - record %lu: no DLLs listed in registry",
                      event->RecordNumber);
        } else {
            crash_log("     - record %lu: translation failed",
                      event->RecordNumber);
        }
        output_eventlog_entry(out, NULL, event, type_char,
                              event_log.getName().c_str(), source_name.c_str(),
                              &strings[0], handle_cache);
    }
    crash_log("     - record %lu: event_processed, "
            "event->Length %lu", event->RecordNumber, event->Length);
}

void output_eventlog(OutputProxy &out, const char *logname,
                     DWORD *record_number, int level, int hide_context) {
    crash_log(" - event log \"%s\":", logname);

    try {
        EventLog log(logname);
        crash_log("   . successfully opened event log");

        out.output("[[[%s]]]\n", logname);
        int worst_state = 0;

        DWORD newest_record = *record_number;

        // record_number is the last event we read, so we want to seek past it
        log.seek(*record_number + 1);

        // first pass - determine if there are records above level
        EVENTLOGRECORD *record = log.read();
        while (record != nullptr) {
            std::pair<char, int> state = determine_event_state(record, level);
            worst_state = std::max(worst_state, state.second);

            // store highest record number we found. This is just in case
            // the second pass doesn't heppen
            newest_record = record->RecordNumber;
            record = log.read();
        }

        crash_log("    . worst state: %d", worst_state);

        // loading and releasing the message dlls for each message was by far
        // the biggest performance cost (~90%) of resolving eventlog messages.
        // -> keep the handles open until all messages are logged so we only
        //    load each dll once
        std::map<std::string, HMODULE> handle_cache;

        // second pass - if there were, print everything
        if ((worst_state >= level) || !logwatch_suppress_info) {
            log.reset();
            log.seek(*record_number + 1);

            EVENTLOGRECORD *record = log.read();
            while (record != nullptr) {
                crash_log("record %d", (int)record->RecordNumber);
                process_eventlog_entry(out, log, record, level, hide_context,
                                       handle_cache);

                // store highest record number we found
                newest_record = record->RecordNumber;
                record = log.read();
            }
        }
        for (auto kv : handle_cache) {
            ::FreeLibrary(kv.second);
        }
        *record_number = newest_record;
    } catch (const std::exception &e) {
        crash_log("failed to read event log: %s\n", e.what());
        out.output("[[[%s:missing]]]\n", logname);
    }
}

// Keeps memory of an event log we have found. It
// might already be known and will not be stored twice.
void register_eventlog(char *logname) {
    // check if we already know this one...
    for (eventlog_state_t::iterator iter = g_eventlog_state.begin();
         iter != g_eventlog_state.end(); ++iter) {
        if (iter->name.compare(logname) == 0) {
            iter->newly_discovered = true;
            return;
        }
    }

    // yet unknown. register it.
    g_eventlog_state.push_back(eventlog_file_state(logname));
}

void unregister_all_eventlogs() { g_eventlog_state.clear(); }

/* Look into the registry in order to find out, which
   event logs are available. */
bool find_eventlogs(OutputProxy &out) {
    for (eventlog_state_t::iterator iter = g_eventlog_state.begin();
         iter != g_eventlog_state.end(); ++iter) {
        iter->newly_discovered = false;
    }

    char regpath[128];
    snprintf(regpath, sizeof(regpath),
             "SYSTEM\\CurrentControlSet\\Services\\Eventlog");
    HKEY key;
    DWORD ret = RegOpenKeyEx(HKEY_LOCAL_MACHINE, regpath, 0,
                             KEY_ENUMERATE_SUB_KEYS, &key);

    bool success = true;
    if (ret == ERROR_SUCCESS) {
        DWORD i = 0;
        char buffer[128];
        DWORD len;
        while (true) {
            len = sizeof(buffer);
            DWORD r =
                RegEnumKeyEx(key, i, buffer, &len, NULL, NULL, NULL, NULL);
            if (r == ERROR_SUCCESS)
                register_eventlog(buffer);
            else if (r != ERROR_MORE_DATA) {
                if (r != ERROR_NO_MORE_ITEMS) {
                    out.output(
                        "ERROR: Cannot enumerate over event logs: error code "
                        "%lu\n",
                        r);
                    success = false;
                }
                break;
            }
            i++;
        }
        RegCloseKey(key);
    } else {
        success = false;
        out.output(
            "ERROR: Cannot open registry key %s for enumeration: error code "
            "%lu\n",
            regpath, GetLastError());
    }
    return success;
}

//  .----------------------------------------------------------------------.
//  |                      ______             ______                       |
//  |                     / / / /  _ __  ___  \ \ \ \                      |
//  |                    / / / /  | '_ \/ __|  \ \ \ \                     |
//  |                    \ \ \ \  | |_) \__ \  / / / /                     |
//  |                     \_\_\_\ | .__/|___/ /_/_/_/                      |
//  |                             |_|                                      |
//  '----------------------------------------------------------------------'

bool ExtractProcessOwner(HANDLE hProcess_i, string &csOwner_o) {
    // Get process token
    WinHandle hProcessToken;
    if (!OpenProcessToken(hProcess_i, TOKEN_READ, hProcessToken.ptr()) ||
        !hProcessToken)
        return false;

    // First get size needed, TokenUser indicates we want user information from
    // given token
    DWORD dwProcessTokenInfoAllocSize = 0;
    GetTokenInformation(hProcessToken, TokenUser, NULL, 0,
                        &dwProcessTokenInfoAllocSize);

    // Call should have failed due to zero-length buffer.
    if (GetLastError() == ERROR_INSUFFICIENT_BUFFER) {
        // Allocate buffer for user information in the token.
        PTOKEN_USER pUserToken = reinterpret_cast<PTOKEN_USER>(
            new BYTE[dwProcessTokenInfoAllocSize]);
        if (pUserToken != NULL) {
            // Now get user information in the allocated buffer
            if (GetTokenInformation(hProcessToken, TokenUser, pUserToken,
                                    dwProcessTokenInfoAllocSize,
                                    &dwProcessTokenInfoAllocSize)) {
                // Some vars that we may need
                SID_NAME_USE snuSIDNameUse;
                WCHAR szUser[MAX_PATH] = {0};
                DWORD dwUserNameLength = MAX_PATH;
                WCHAR szDomain[MAX_PATH] = {0};
                DWORD dwDomainNameLength = MAX_PATH;

                // Retrieve user name and domain name based on user's SID.
                if (LookupAccountSidW(NULL, pUserToken->User.Sid, szUser,
                                      &dwUserNameLength, szDomain,
                                      &dwDomainNameLength, &snuSIDNameUse)) {
                    char info[1024];
                    csOwner_o = "\\\\";
                    WideCharToMultiByte(CP_UTF8, 0, (WCHAR *)&szDomain, -1,
                                        info, sizeof(info), NULL, NULL);
                    csOwner_o += info;

                    csOwner_o += "\\";
                    WideCharToMultiByte(CP_UTF8, 0, (WCHAR *)&szUser, -1, info,
                                        sizeof(info), NULL, NULL);
                    csOwner_o += info;

                    delete[] pUserToken;
                    return true;
                }
            }
            delete[] pUserToken;
        }
    }
    return false;
}

process_entry_t get_process_perfdata() {
    process_entry_t process_info;

    PerfCounterObject counterObject(230);  // process base number

    if (!counterObject.isEmpty()) {
        LARGE_INTEGER Frequency;
        QueryPerformanceFrequency(&Frequency);

        std::vector<PERF_INSTANCE_DEFINITION *> instances =
            counterObject.instances();

        std::vector<process_entry> entries(
            instances.size());  // one instance = one process

        // gather counters
        for (const PerfCounter &counter : counterObject.counters()) {
            std::vector<ULONGLONG> values = counter.values(instances);
            for (std::size_t i = 0; i < values.size(); ++i) {
                switch (counter.offset()) {
                    case 40:
                        entries.at(i).virtual_size = values[i];
                        break;
                    case 56:
                        entries.at(i).working_set_size = values[i];
                        break;
                    case 64:
                        entries.at(i).pagefile_usage = values[i];
                        break;
                    case 104:
                        entries.at(i).process_id = values[i];
                        break;
                }
            }
        }

        for (const process_entry &entry : entries) {
            process_info[entry.process_id] = entry;
        }
    }
    return process_info;
}

void section_ps_wmi(OutputProxy &out) {
    crash_log("<<<ps>>>");

    wmi::Result result;
    try {
        result = WMILookup::get().query(L"SELECT * FROM Win32_Process");
        bool more = result.valid();
        if (!more) {
            return;
        }
        out.output("<<<ps:sep(9)>>>\n");

        while (more) {
            int processId = result.get<int>(L"ProcessId");

            WinHandle process(OpenProcess(
                PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, FALSE, processId));
            string user = "SYSTEM";
            ExtractProcessOwner(process, user);
            std::wstring process_name;

            if (g_config->psFullCommandLine() &&
                result.contains(L"ExecutablePath")) {
                process_name = result.get<std::wstring>(L"ExecutablePath");
            } else {
                process_name = result.get<std::wstring>(L"Caption");
            }

            if (g_config->psFullCommandLine() &&
                result.contains(L"CommandLine")) {
                int argc;
                LPWSTR *argv = CommandLineToArgvW(
                    result.get<std::wstring>(L"CommandLine").c_str(), &argc);
                for (int i = 1; i < argc; ++i) {
                    process_name += std::wstring(L" ") + argv[i];
                }
                LocalFree(argv);
            }

            out.output(
                "(%s,%" PRIu64 ",%" PRIu64 ",%d,%d,%d,%ls,%ls,%u,%d)\t%ls\n",
                user.c_str(),
                string_to_llu(result.get<string>(L"VirtualSize").c_str()) /
                    1024,
                string_to_llu(result.get<string>(L"WorkingSetSize").c_str()) /
                    1024,
                0, processId, result.get<int>(L"PagefileUsage") / 1024,
                result.get<wstring>(L"UserModeTime").c_str(),
                result.get<wstring>(L"KernelModeTime").c_str(),
                result.get<int>(L"HandleCount"),
                result.get<int>(L"ThreadCount"), process_name.c_str());
            more = result.next();
        }
    } catch (const wmi::ComException &e) {
        // the most likely cause is that the wmi query fails, i.e. because the
        // service is
        // currently offline.
        crash_log("Exception: %s", e.what());
    } catch (const wmi::ComTypeException &e) {
        crash_log("Exception: %s", e.what());
        std::wstring types;
        std::vector<std::wstring> names;
        for (std::vector<std::wstring>::const_iterator iter = names.begin();
             iter != names.end(); ++iter) {
            types += *iter + L"=" +
                     std::to_wstring(result.typeId(iter->c_str())) + L", ";
        }
        crash_log(
            "Data types are different than expected, please report this and "
            "include "
            "the following: %ls",
            types.c_str());
        abort();
    }
}

void section_ps(OutputProxy &out) {
    crash_log("<<<ps>>>");
    out.output("<<<ps:sep(9)>>>\n");
    PROCESSENTRY32 pe32;

    process_entry_t process_perfdata;
    try {
        process_perfdata = get_process_perfdata();
    } catch (const std::runtime_error &e) {
        // the most likely cause is that the wmi query fails, i.e. because the
        // service is currently offline.
        crash_log("Exception: Error while querying process perfdata: %s", e.what());
    }

    WinHandle hProcessSnap(CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0));
    if (hProcessSnap != INVALID_HANDLE_VALUE) {
        pe32.dwSize = sizeof(PROCESSENTRY32);

        if (Process32First(hProcessSnap, &pe32)) {
            do {
                string user = "unknown";
                DWORD dwAccess = PROCESS_QUERY_INFORMATION | PROCESS_VM_READ;
                WinHandle hProcess(
                    OpenProcess(dwAccess, FALSE, pe32.th32ProcessID));

                if (NULL == hProcess) continue;

                // Process times
                FILETIME createTime, exitTime, kernelTime, userTime;
                ULARGE_INTEGER kernelmodetime, usermodetime;
                if (GetProcessTimes(hProcess, &createTime, &exitTime,
                                    &kernelTime, &userTime) != -1) {
                    kernelmodetime.LowPart = kernelTime.dwLowDateTime;
                    kernelmodetime.HighPart = kernelTime.dwHighDateTime;
                    usermodetime.LowPart = userTime.dwLowDateTime;
                    usermodetime.HighPart = userTime.dwHighDateTime;
                }

                DWORD processHandleCount = 0;

                // GetProcessHandleCount is only available winxp upwards
                typedef BOOL WINAPI (*GetProcessHandleCount_type)(HANDLE,
                                                                  PDWORD);
                DYNAMIC_FUNC(GetProcessHandleCount, L"kernel32.dll");
                if (GetProcessHandleCount_dyn != NULL) {
                    GetProcessHandleCount_dyn(hProcess, &processHandleCount);
                }

                // Process owner
                ExtractProcessOwner(hProcess, user);

                // Memory levels
                ULONGLONG working_set_size = 0;
                ULONGLONG virtual_size = 0;
                ULONGLONG pagefile_usage = 0;
                process_entry_t::iterator it_perf =
                    process_perfdata.find(pe32.th32ProcessID);
                if (it_perf != process_perfdata.end()) {
                    working_set_size = it_perf->second.working_set_size;
                    virtual_size = it_perf->second.virtual_size;
                    pagefile_usage = it_perf->second.pagefile_usage;
                }

                //// Note: CPU utilization is determined out of usermodetime and
                /// kernelmodetime
                out.output("(%s,%" PRIu64 ",%" PRIu64 ",%d,%lu,%" PRIu64
                           ",%" PRIu64 ",%" PRIu64 ",%lu,%lu)\t%s\n",
                           user.c_str(), virtual_size / 1024,
                           working_set_size / 1024, 0, pe32.th32ProcessID,
                           pagefile_usage / 1024, usermodetime.QuadPart,
                           kernelmodetime.QuadPart, processHandleCount,
                           pe32.cntThreads, pe32.szExeFile);
            } while (Process32Next(hProcessSnap, &pe32));
        }
        process_perfdata.clear();

        // The process snapshot doesn't show the system idle process (used to
        // determine the number of cpu cores)
        // We simply fake this entry..
        SYSTEM_INFO sysinfo;
        GetSystemInfo(&sysinfo);
        out.output("(SYSTEM,0,0,0,0,0,0,0,0,%lu)\tSystem Idle Process\n",
                   sysinfo.dwNumberOfProcessors);
    }
}

// .-----------------------------------------------------------------------.
// |            _                              _       _                   |
// |           | |    ___   __ ___      ____ _| |_ ___| |__                |
// |           | |   / _ \ / _` \ \ /\ / / _` | __/ __| '_ \               |
// |           | |__| (_) | (_| |\ V  V / (_| | || (__| | | |              |
// |           |_____\___/ \__, | \_/\_/ \__,_|\__\___|_| |_|              |
// |                       |___/                                           |
// +-----------------------------------------------------------------------+
// | Functions related to the evaluation of logwatch textfiles             |
// '-----------------------------------------------------------------------'

void parse_eventlog_state_line(char *line) {
    /* Example: line = "System|1234" */
    rstrip(line);
    char *p = line;
    while (*p && *p != '|') p++;
    *p = 0;
    char *path = line;
    p++;

    char *token = strtok(p, "|");

    if (!token) return;
    unsigned long long record_no = string_to_llu(token);

    eventlog_hint_t *elh = new eventlog_hint_t();
    elh->name = strdup(path);
    elh->record_no = record_no;
    g_eventlog_hints.push_back(elh);
}

void load_eventlog_offsets(const std::string &statefile) {
    static bool records_loaded = false;
    if (!records_loaded) {
        FILE *file = fopen(statefile.c_str(), "r");
        if (file) {
            char line[256];
            while (NULL != fgets(line, sizeof(line), file)) {
                parse_eventlog_state_line(line);
            }
            fclose(file);
        }
        records_loaded = true;
    }
}

void save_logwatch_offsets(const std::string &logwatch_statefile) {
    FILE *file = fopen(logwatch_statefile.c_str(), "w");
    if (!file) {
        crash_log("Cannot open %s for writing: %s (%d).\n",
                  logwatch_statefile.c_str(), strerror(errno), errno);
        // not stopping the agent from crashing. This way the user at least
        // notices something went wrong.
        // FIXME: unless there aren't any textfiles configured to be monitored
    }
    for (logwatch_textfiles_t::const_iterator it_tf =
             g_config->logwatchTextfiles().begin();
         it_tf != g_config->logwatchTextfiles().end(); ++it_tf) {
        logwatch_textfile *tf = *it_tf;
        if (!tf->missing) {
            fprintf(file, "%s|%" PRIu64 "|%" PRIu64 "|%" PRIu64 "\r\n",
                    tf->path, tf->file_id, tf->file_size, tf->offset);
        }
    }
    if (file != NULL) {
        fclose(file);
    }
}

void save_eventlog_offsets(const std::string &eventlog_statefile) {
    FILE *file = fopen(eventlog_statefile.c_str(), "w");
    for (eventlog_state_t::iterator state_iter = g_eventlog_state.begin();
         state_iter != g_eventlog_state.end(); ++state_iter) {
        int level = 1;
        for (eventlog_config_t::iterator conf_iter =
                 g_config->eventlogConfig().begin();
             conf_iter != g_config->eventlogConfig().end(); ++conf_iter) {
            if ((conf_iter->name == "*") ||
                ci_equal(conf_iter->name, state_iter->name)) {
                level = conf_iter->level;
                break;
            }
        }
        if (level != -1)
            fprintf(file, "%s|%lu\n", state_iter->name.c_str(),
                    state_iter->num_known_records);
    }
    fclose(file);
}

void update_script_statistics() {
    script_containers_t::iterator it = script_containers.begin();
    script_container *cont = NULL;

    memset(&g_script_stat, 0, sizeof(g_script_stat));
    while (it != script_containers.end()) {
        cont = it->second;
        if (cont->type == PLUGIN)
            g_script_stat.pl_count++;
        else
            g_script_stat.lo_count++;

        switch (cont->last_problem) {
            case SCRIPT_TIMEOUT:
                if (cont->type == PLUGIN)
                    g_script_stat.pl_timeouts++;
                else
                    g_script_stat.lo_timeouts++;
                break;
            case SCRIPT_ERROR:
                if (cont->type == PLUGIN)
                    g_script_stat.pl_errors++;
                else
                    g_script_stat.lo_errors++;
                break;
            default:
                break;
        }
        it++;
    }
}

// Remove missing files from list
void cleanup_logwatch_textfiles() {
    logwatch_textfiles_t &textfiles = g_config->logwatchTextfiles();

    // remove_if puts the missing textfiles to the end of the list, it doesn't
    // actually remove anything
    auto first_missing =
        std::remove_if(textfiles.begin(), textfiles.end(),
                       [](logwatch_textfile *file) { return file->missing; });

    for (logwatch_textfiles_t::iterator iter = first_missing;
         iter != textfiles.end(); ++iter) {
        free((*iter)->path);
        delete *iter;
    }

    textfiles.erase(first_missing, textfiles.end());
}

// Called on program exit
void cleanup_logwatch() {
    // cleanup textfiles
    for (logwatch_textfiles_t::iterator it_tf =
             g_config->logwatchTextfiles().begin();
         it_tf != g_config->logwatchTextfiles().end(); it_tf++)
        (*it_tf)->missing = true;
    cleanup_logwatch_textfiles();

    // cleanup globlines and textpatterns
    for (logwatch_globlines_t::iterator it_globline =
             g_config->logwatchGloblines().begin();
         it_globline != g_config->logwatchGloblines().end(); it_globline++) {
        globline_container *cont = *it_globline;

        for (glob_tokens_t::iterator it_token = cont->tokens.begin();
             it_token != cont->tokens.end(); it_token++) {
            free((*it_token)->pattern);
            delete (*it_token);
        }
        cont->tokens.clear();

        for (condition_patterns_t::iterator it_patt = cont->patterns.begin();
             it_patt != cont->patterns.end(); it_patt++) {
            free((*it_patt)->glob_pattern);
            delete (*it_patt);
        }
        cont->patterns.clear();
        delete cont;
    }
}

// Process content of the given textfile
// Can be called in dry-run mode (write_output = false). This tries to detect
// CRIT or WARN patterns
// If write_output is set to true any data found is written to the out socket
#define UNICODE_BUFFER_SIZE 8192
int fill_unicode_bytebuffer(FILE *file, char *buffer, int offset) {
    int bytes_to_read = UNICODE_BUFFER_SIZE - offset;
    int read_bytes = fread(buffer + offset, 1, bytes_to_read, file);
    return read_bytes + offset;
}

int find_crnl_end(char *buffer) {
    int index = 0;
    while (true) {
        if (index >= UNICODE_BUFFER_SIZE) return -1;
        if (buffer[index] == 0x0d && index < UNICODE_BUFFER_SIZE - 2 &&
            buffer[index + 2] == 0x0a)
            return index + 4;
        index += 2;
    }
    return -1;
}

struct process_textfile_response {
    bool found_match;
    int unprocessed_bytes;
};

process_textfile_response process_textfile_unicode(FILE *file,
                                                   logwatch_textfile *textfile,
                                                   OutputProxy &out,
                                                   bool write_output) {
    verbose("Checking UNICODE file %s\n", textfile->path);
    process_textfile_response response;
    char output_buffer[UNICODE_BUFFER_SIZE];
    char unicode_block[UNICODE_BUFFER_SIZE];

    condition_pattern *pattern = 0;
    int buffer_level = 0;   // Current bytes in buffer
    bool cut_line = false;  // Line does not fit in buffer
    int crnl_end_offset;    // Byte index of CRLF in unicode block
    int old_buffer_level = 0;

    memset(unicode_block, 0, UNICODE_BUFFER_SIZE);

    while (true) {
        // Only fill buffer if there is no CRNL present
        if (find_crnl_end(unicode_block) == -1) {
            old_buffer_level = buffer_level;
            buffer_level =
                fill_unicode_bytebuffer(file, unicode_block, buffer_level);

            if (old_buffer_level == buffer_level)
                break;  // Nothing new, file finished
        }

        crnl_end_offset = find_crnl_end(unicode_block);
        if (crnl_end_offset == -1) {
            if (buffer_level == UNICODE_BUFFER_SIZE)
                // This line is too long, only report up to the buffers size
                cut_line = true;
            else
                // Missing CRNL... this line is not finished yet
                continue;
        }

        // Convert unicode to utf-8
        memset(output_buffer, 0, UNICODE_BUFFER_SIZE);
        WideCharToMultiByte(CP_UTF8, 0, (wchar_t *)unicode_block,
                            cut_line ? (UNICODE_BUFFER_SIZE - 2) / 2
                                     : (crnl_end_offset - 4) / 2,
                            output_buffer, sizeof(output_buffer), NULL, NULL);

        // Check line
        char state = '.';
        for (condition_patterns_t::iterator it_patt =
                 textfile->patterns->begin();
             it_patt != textfile->patterns->end(); it_patt++) {
            pattern = *it_patt;
            if (globmatch(pattern->glob_pattern, output_buffer)) {
                if (!write_output &&
                    (pattern->state == 'C' || pattern->state == 'W' ||
                     pattern->state == 'O')) {
                    response.found_match = true;
                    response.unprocessed_bytes = buffer_level;
                    return response;
                }
                state = pattern->state;
                break;
            }
        }

        // Output line
        if (write_output && strlen(output_buffer) > 0) {
            out.output("%c %s\n", state, output_buffer);
        }

        if (cut_line) {
            cut_line = false;
            buffer_level = 2;
            while (crnl_end_offset == -1) {
                memcpy(unicode_block, unicode_block + UNICODE_BUFFER_SIZE - 2,
                       2);
                memset(unicode_block + 2, 0, UNICODE_BUFFER_SIZE - 2);
                old_buffer_level = buffer_level;
                buffer_level = fill_unicode_bytebuffer(file, unicode_block, 2);
                if (old_buffer_level == buffer_level)
                    // Nothing new, file finished
                    break;
                crnl_end_offset = find_crnl_end(unicode_block);
            }
        }

        if (crnl_end_offset > 0) {
            buffer_level = buffer_level - crnl_end_offset;
            memmove(unicode_block, unicode_block + crnl_end_offset,
                    buffer_level);
            memset(unicode_block + buffer_level, 0,
                   UNICODE_BUFFER_SIZE - buffer_level);
        }
    }

    response.found_match = false;
    response.unprocessed_bytes = buffer_level;
    return response;
}

process_textfile_response process_textfile(FILE *file,
                                           logwatch_textfile *textfile,
                                           OutputProxy &out,
                                           bool write_output) {
    char line[4096];
    condition_pattern *pattern = 0;
    process_textfile_response response;
    verbose("Checking file %s\n", textfile->path);

    while (!feof(file)) {
        if (!fgets(line, sizeof(line), file)) break;

        if (line[strlen(line) - 1] == '\n') line[strlen(line) - 1] = 0;

        char state = '.';
        for (condition_patterns_t::iterator it_patt =
                 textfile->patterns->begin();
             it_patt != textfile->patterns->end(); it_patt++) {
            pattern = *it_patt;
            if (globmatch(pattern->glob_pattern, line)) {
                if (!write_output &&
                    (pattern->state == 'C' || pattern->state == 'W' ||
                     pattern->state == 'O')) {
                    response.found_match = true;
                    response.unprocessed_bytes = 0;
                    return response;
                }
                state = pattern->state;
                break;
            }
        }

        if (write_output && strlen(line) > 0 &&
            !(textfile->nocontext && (state == 'I' || state == '.')))
            out.output("%c %s\n", state, line);
    }

    response.found_match = false;
    response.unprocessed_bytes = 0;
    return response;
}

// The output of this section is compatible with
// the logwatch agent for Linux and UNIX
void section_logfiles(OutputProxy &out, const Environment &env) {
    crash_log("<<<logwatch>>>");
    out.output("<<<logwatch>>>\n");

    g_config->revalidateLogwatchTextfiles();

    logwatch_textfile *textfile;

    // Missing glob patterns
    for (logwatch_globlines_t::iterator it_globline =
             g_config->logwatchGloblines().begin();
         it_globline != g_config->logwatchGloblines().end(); ++it_globline) {
        globline_container *cont = *it_globline;
        for (glob_tokens_t::iterator it_token = cont->tokens.begin();
             it_token != cont->tokens.end(); it_token++) {
            if (!((*it_token)->found_match))
                out.output("[[[%s:missing]]]\n", (*it_token)->pattern);
        }
    }
    for (logwatch_textfiles_t::iterator it_tf =
             g_config->logwatchTextfiles().begin();
         it_tf != g_config->logwatchTextfiles().end(); ++it_tf) {
        textfile = *it_tf;
        if (textfile->missing) {
            out.output("[[[%s:missing]]]\n", textfile->path);
            continue;
        }

        // Determine Encoding
        if (textfile->encoding == UNDEF || textfile->offset == 0) {
            FILE *file = fopen(textfile->path, "rb");
            if (!file) {
                out.output("[[[%s:cannotopen]]]\n", textfile->path);
                continue;
            }

            char bytes[2];
            int read_bytes = fread(bytes, 1, sizeof(bytes), file);
            if (read_bytes == sizeof(bytes) &&
                (unsigned char)bytes[0] == 0xFF &&
                (unsigned char)bytes[1] == 0xFE)
                textfile->encoding = UNICODE;
            else
                textfile->encoding = DEFAULT;
            fclose(file);
        }

        // Start processing file
        FILE *file;
        if (textfile->encoding == UNICODE)
            file = fopen(textfile->path, "rb");
        else
            file = fopen(textfile->path, "r");

        if (!file) {
            out.output("[[[%s:cannotopen]]]\n", textfile->path);
            continue;
        }

        out.output("[[[%s]]]\n", textfile->path);

        if (textfile->offset == textfile->file_size) {  // no new data
            fclose(file);
            continue;
        }

        fseek(file, (textfile->encoding == UNICODE && textfile->offset == 0)
                        ? 2
                        : textfile->offset,
              SEEK_SET);
        process_textfile_response response;
        if (textfile->encoding == UNICODE)
            response = process_textfile_unicode(file, textfile, out, false);
        else
            response = process_textfile(file, textfile, out, false);

        if (response.found_match) {
            fseek(file, (textfile->encoding == UNICODE && textfile->offset == 0)
                            ? 2
                            : textfile->offset,
                  SEEK_SET);
            if (textfile->encoding == UNICODE)
                response = process_textfile_unicode(file, textfile, out, true);
            else
                response = process_textfile(file, textfile, out, true);
        }

        fclose(file);
        textfile->offset = textfile->file_size - response.unprocessed_bytes;
    }

    cleanup_logwatch_textfiles();
    save_logwatch_offsets(env.logwatchStatefile());
}

void dump_wmi_table(OutputProxy &out, wmi::Result &result) {
    if (!result.valid()) {
        return;
    }
    out.output("%ls\n", join(result.names(), L",").c_str());
    bool more = true;
    while (more) {
        std::vector<std::wstring> values = result.names();
        // resolve all table keys to their value on this row.
        std::transform(values.begin(), values.end(), values.begin(),
                       [&result](const std::wstring &name) {
                           return result.get<std::wstring>(name.c_str());
                       });
        out.output("%ls\n", join(values, L",").c_str());

        more = result.next();
    }
}

bool output_wmi_table(OutputProxy &out, const wchar_t *table_name,
                      const char *section_name, bool as_subtable = false) {
    wmi::Result result;
    try {
        result = WMILookup::get().getClass(table_name);
    } catch (const wmi::ComException &e) {
        crash_log("wmi request for %ls failed: %s", table_name, e.what());
        return true;
    }

    if (!result.valid()) {
        crash_log("table %ls %s", table_name,
                  FAILED(result.last_error()) ? "doesn't exist" : "is empty");
        return !FAILED(result.last_error());
    }

    if (as_subtable) {
        out.output("[%s]\n", section_name);
    } else {
        out.output("<<<%s:sep(44)>>>\n", section_name);
    }
    dump_wmi_table(out, result);
    return true;
}

void section_dotnet(OutputProxy &out) {
    crash_log("<<<dotnet_clrmemory>>>");

    if (!output_wmi_table(out, L"Win32_PerfRawData_NETFramework_NETCLRMemory",
                          "dotnet_clrmemory")) {
        crash_log("dotnet wmi table(s) missing or empty -> section disabled");
        g_config->disableSection(SECTION_DOTNET);
    }
}

void section_cpu(OutputProxy &out) {
    crash_log("<<<wmi_cpuload>>>");

    out.output("<<<wmi_cpuload:sep(44)>>>\n");
    if (!output_wmi_table(out, L"Win32_PerfRawData_PerfOS_System",
                          "system_perf", true) ||
        !output_wmi_table(out, L"Win32_ComputerSystem", "computer_system",
                          true)) {
        crash_log(
            "cpuload related wmi tables missing or empty -> section disabled");
        g_config->disableSection(SECTION_CPU);
    }
}

void section_exchange(OutputProxy &out) {
    bool any_section_valid = false;
    for (auto &data_source : {
             std::make_pair(L"MSExchangeActiveSync", "msexch_activesync"),
             std::make_pair(L"MSExchangeAvailabilityService",
                            "msexch_availability"),
             std::make_pair(L"MSExchangeOWA", "msexch_owa"),
             std::make_pair(L"MSExchangeAutodiscover", "msexch_autodiscovery"),
             std::make_pair(L"MSExchangeISClientType", "msexch_isclienttype"),
             std::make_pair(L"MSExchangeISStore", "msexch_isstore"),
             std::make_pair(L"MSExchangeRpcClientAccess",
                            "msexch_rpcclientaccess"),
         }) {
        std::wostringstream table_name;
        table_name << L"Win32_PerfRawData_" << data_source.first << L"_"
                   << data_source.first;
        crash_log("<<<%s>>>", data_source.second);
        any_section_valid |=
            output_wmi_table(out, table_name.str().c_str(), data_source.second);
    }

    if (!any_section_valid) {
        crash_log("exchange wmi tables missing or empty -> section disabled");
        g_config->disableSection(SECTION_EXCHANGE);
    }
}

void section_webservices(OutputProxy &out) {
    crash_log("<<<wmi_webservices>>>");

    if (!output_wmi_table(out, L"Win32_PerfRawData_W3SVC_WebService",
                          "wmi_webservices")) {
        crash_log("webservices wmi table missing or empty -> section disabled");
        g_config->disableSection(SECTION_WEBSERVICES);
    }
}

void section_ohm(OutputProxy &out) {
    crash_log("<<<openhardwaremonitor>>>");

    wmi::Result result;
    try {
        result = WMILookup::get(L"Root\\OpenHardwareMonitor")
                     .query(
                         L"SELECT Index, Name, Parent, SensorType, Value FROM "
                         L"Sensor");
    } catch (const wmi::ComException &e) {
        crash_log("failed to query ohm wmi-section: %s", e.what());
    }

    if (result.valid()) {
        out.output("<<<openhardwaremonitor:sep(44)>>>\n");
        dump_wmi_table(out, result);
    } else {
        if (!g_ohmMonitor->checkAvailabe()) {
            crash_log("ohm not installed or not runnable -> section disabled");
            g_config->disableSection(SECTION_OHM);
        } else {
            crash_log("ohm wmi table empty");
        }
        // if ohm was started here, we still don't query the data again this
        // cycle
        // because it's impossible to predict how long the ohm client takes to
        // start
        // up but it won't be instantanious
    }
}

// The output of this section is compatible with
// the logwatch agent for Linux and UNIX
void section_eventlog(OutputProxy &out, const Environment &env) {
    crash_log("<<<logwatch>>>");

    // This agent remembers the record numbers
    // of the event logs up to which messages have
    // been processed. When started, the eventlog
    // is skipped to the end. Historic messages are
    // not been processed.
    static bool first_run = true;
    out.output("<<<logwatch>>>\n");

    if (find_eventlogs(out)) {
        // Special handling on startup (first_run)
        // The last processed record number of each eventlog is stored in the
        // file eventstate.txt
        // If there is no entry for the given eventlog we start at the end
        if (first_run && !g_config->logwatchSendInitialEntries()) {
            for (eventlog_state_t::iterator it_st = g_eventlog_state.begin();
                 it_st != g_eventlog_state.end(); ++it_st) {
                bool found_hint = false;
                for (eventlog_hints_t::iterator it_el =
                         g_eventlog_hints.begin();
                     it_el != g_eventlog_hints.end(); it_el++) {
                    eventlog_hint_t *hint = *it_el;
                    if (it_st->name.compare(hint->name) == 0) {
                        it_st->num_known_records = hint->record_no;
                        found_hint = true;
                        break;
                    }
                }
                if (!found_hint) {
                    HANDLE hEventlog = OpenEventLog(NULL, it_st->name.c_str());
                    OnScopeExit exitHandler([hEventlog] () {
                            CloseEventLog(hEventlog);
                            });
                    if (hEventlog) {
                        DWORD no_records;
                        DWORD oldest_record;
                        GetNumberOfEventLogRecords(hEventlog, &no_records);
                        GetOldestEventLogRecord(hEventlog, &oldest_record);
                        if (no_records > 0)
                            it_st->num_known_records =
                                oldest_record + no_records - 1;
                    }
                }
            }
        }

        for (eventlog_state_t::iterator it_st = g_eventlog_state.begin();
             it_st != g_eventlog_state.end(); ++it_st) {
            if (!it_st->newly_discovered)  // not here any more!
                out.output("[[[%s:missing]]]\n", it_st->name.c_str());
            else {
                // Get the configuration of that log file (which messages to
                // send)
                int level = 1;
                int hide_context = 0;
                for (eventlog_config_t::iterator conf_iter =
                         g_config->eventlogConfig().begin();
                     conf_iter != g_config->eventlogConfig().end();
                     ++conf_iter) {
                    if ((conf_iter->name == "*") ||
                        ci_equal(conf_iter->name, it_st->name)) {
                        level = conf_iter->level;
                        hide_context = conf_iter->hide_context;
                        break;
                    }
                }
                if (level != -1) {
                    output_eventlog(out, it_st->name.c_str(),
                                    &it_st->num_known_records, level,
                                    hide_context);
                }
            }
        }
        save_eventlog_offsets(env.eventlogStatefile());
    }
    first_run = false;
}

//  .----------------------------------------------------------------------.
//  |              ______                            ______                |
//  |             / / / /  _ __ ___   ___ _ __ ___   \ \ \ \               |
//  |            / / / /  | '_ ` _ \ / _ \ '_ ` _ \   \ \ \ \              |
//  |            \ \ \ \  | | | | | |  __/ | | | | |  / / / /              |
//  |             \_\_\_\ |_| |_| |_|\___|_| |_| |_| /_/_/_/               |
//  |                                                                      |
//  '----------------------------------------------------------------------'

// The output imitates that of the Linux agent. That makes
// a special check for check_mk unneccessary:
// <<<mem>>>.
// MemTotal:       514104 kB
// MemFree:         19068 kB
// SwapTotal:     1048568 kB
// SwapFree:      1043732 kB

void section_mem(OutputProxy &out) {
    crash_log("<<<mem>>>");
    out.output("<<<mem>>>\n");

    MEMORYSTATUSEX statex;
    statex.dwLength = sizeof(statex);
    GlobalMemoryStatusEx(&statex);

    out.output("MemTotal:     %" PRIu64 " kB\n", statex.ullTotalPhys / 1024);
    out.output("MemFree:      %" PRIu64 " kB\n", statex.ullAvailPhys / 1024);
    out.output("SwapTotal:    %" PRIu64 " kB\n",
               (statex.ullTotalPageFile - statex.ullTotalPhys) / 1024);
    out.output("SwapFree:     %" PRIu64 " kB\n",
               (statex.ullAvailPageFile - statex.ullAvailPhys) / 1024);
    out.output("PageTotal:    %" PRIu64 " kB\n",
               statex.ullTotalPageFile / 1024);
    out.output("PageFree:     %" PRIu64 " kB\n",
               statex.ullAvailPageFile / 1024);
    out.output("VirtualTotal: %" PRIu64 " kB\n", statex.ullTotalVirtual / 1024);
    out.output("VirtualFree:  %" PRIu64 " kB\n", statex.ullAvailVirtual / 1024);
}

// .-----------------------------------------------------------------------.
// |              ______ __ _ _      _        __     ______                |
// |             / / / // _(_) | ___(_)_ __  / _| ___\ \ \ \               |
// |            / / / /| |_| | |/ _ \ | '_ \| |_ / _ \\ \ \ \              |
// |            \ \ \ \|  _| | |  __/ | | | |  _| (_) / / / /              |
// |             \_\_\_\_| |_|_|\___|_|_| |_|_|  \___/_/_/_/               |
// |                                                                       |
// '-----------------------------------------------------------------------'

void output_fileinfos(OutputProxy &out, const char *path);
bool output_fileinfo(OutputProxy &out, const char *basename,
                     WIN32_FIND_DATA *data);

void section_fileinfo(OutputProxy &out) {
    crash_log("<<<fileinfo>>>");
    out.output("<<<fileinfo:sep(124)>>>\n");
    out.output("%.0f\n", current_time());
    for (fileinfo_paths_t::iterator it_path = g_config->fileinfoPaths().begin();
         it_path != g_config->fileinfoPaths().end(); it_path++) {
        output_fileinfos(out, *it_path);
    }
}

void output_fileinfos(OutputProxy &out, const char *path) {
    WIN32_FIND_DATA data;
    HANDLE h = FindFirstFileEx(path, FindExInfoStandard, &data,
                               FindExSearchNameMatch, NULL, 0);
    bool found_file = false;

    if (h != INVALID_HANDLE_VALUE) {
        // compute basename of path: search backwards for '\'
        const char *basename = "";
        char *end = strrchr(path, '\\');
        if (end) {
            *end = 0;
            basename = path;
        }
        found_file = output_fileinfo(out, basename, &data);
        while (FindNextFile(h, &data))
            found_file = output_fileinfo(out, basename, &data) || found_file;
        if (end) *end = '\\';  // repair string
        FindClose(h);

        if (!found_file) out.output("%s|missing|%f\n", path, current_time());
    } else {
        DWORD e = GetLastError();
        out.output("%s|missing|%lu\n", path, e);
    }
}

bool output_fileinfo(OutputProxy &out, const char *basename,
                     WIN32_FIND_DATA *data) {
    unsigned long long size = (unsigned long long)data->nFileSizeLow +
                              (((unsigned long long)data->nFileSizeHigh) << 32);

    if (0 == (data->dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)) {
        out.output("%s\\%s|%" PRIu64 "|%.0f\n", basename, data->cFileName, size,
                   file_time(&data->ftLastWriteTime));
        return true;
    }
    return false;
}

// .-Scripts---------------------------------------------------------------.
// |                   ____            _       _                           |
// |                  / ___|  ___ _ __(_)_ __ | |_ ___                     |
// |                  \___ \ / __| '__| | '_ \| __/ __|                    |
// |                   ___) | (__| |  | | |_) | |_\__ \                    |
// |                  |____/ \___|_|  |_| .__/ \__|___/                    |
// |                                    |_|                                |
// +-----------------------------------------------------------------------+
// | Config functions for local and plugins scripts                        |
// '-----------------------------------------------------------------------'

int get_script_timeout(char *name, script_type type) {
    timeout_configs_t &configs = g_config->timeoutConfigs(type);
    for (timeout_configs_t::iterator it = configs.begin(); it != configs.end();
         ++it)
        if (globmatch((*it)->pattern, name)) return (*it)->timeout;
    return type == PLUGIN ? DEFAULT_PLUGIN_TIMEOUT : DEFAULT_LOCAL_TIMEOUT;
}

int get_script_cache_age(char *name, script_type type) {
    cache_configs_t &configs = g_config->cacheConfigs(type);
    for (cache_configs_t::iterator it = configs.begin(); it != configs.end();
         ++it)
        if (globmatch((*it)->pattern, name)) return (*it)->max_age;
    return 0;
}

int get_script_max_retries(char *name, script_type type) {
    retry_count_configs_t &configs = g_config->retryConfigs(type);
    for (retry_count_configs_t::iterator it = configs.begin();
         it != configs.end(); ++it)
        if (globmatch((*it)->pattern, name)) return (*it)->retries;
    return 0;
}

script_execution_mode get_script_execution_mode(char *name, script_type type) {
    execution_mode_configs_t &configs = g_config->executionModeConfigs(type);
    for (execution_mode_configs_t::iterator it = configs.begin();
         it != configs.end(); ++it)
        if (globmatch((*it)->pattern, name)) return (*it)->mode;
    return g_config->defaultScriptExecutionMode();
}

//   .----------------------------------------------------------------------.
//   |     ____                    _                                        |
//   |    |  _ \ _   _ _ __  _ __ (_)_ __   __ _   _ __  _ __ __ _ ___      |
//   |    | |_) | | | | '_ \| '_ \| | '_ \ / _` | | '_ \| '__/ _` / __|     |
//   |    |  _ <| |_| | | | | | | | | | | | (_| | | |_) | | | (_| \__ \     |
//   |    |_| \_\\__,_|_| |_|_| |_|_|_| |_|\__, | | .__/|_|  \__, |___/     |
//   |                                     |___/  |_|        |___/          |
//   +----------------------------------------------------------------------+
//   | Functions for dealing with running external programs.                |
//   '----------------------------------------------------------------------'

char *add_interpreter(char *path, char *newpath) {
    if (!strcmp(path + strlen(path) - 4, ".vbs")) {
        // If this is a vbscript don't rely on the default handler for this
        // file extensions. This might be notepad or some other editor by
        // default on a lot of systems. So better add cscript as interpreter.
        snprintf(newpath, 256, "cscript.exe //Nologo \"%s\"", path);
        return newpath;
    } else if (!strcmp(path + strlen(path) - 4, ".ps1")) {
        // Same for the powershell scripts. Add the powershell interpreter.
        // To make this work properly two things are needed:
        //   1.) The powershell interpreter needs to be in PATH
        //   2.) The execution policy needs to allow the script execution
        //       -> Get-ExecutionPolicy / Set-ExecutionPolicy
        //
        // actually, microsoft always installs the powershell interpreter to the
        // same directory (independent of the version) so even if it's not in
        // the path, we have a good chance with this fallback.
        const char *fallback =
            "C:\\Windows\\System32\\WindowsPowershell\\v1.0\\powershell.exe";

        char dummy;
        ::SearchPathA(NULL, "powershell.exe", NULL, 1, &dummy, NULL);
        const char *interpreter = ::GetLastError() != ERROR_FILE_NOT_FOUND
                                      ? "powershell.exe"
                                      : fallback;
        snprintf(newpath, 256,
                 "%s -NoLogo -ExecutionPolicy RemoteSigned \"& \'%s\'\"",
                 interpreter, path);
        return newpath;
    } else if (!strcmp(path + strlen(path) - 3, ".pl")) {
        // Perl scripts get perl.exe as interpreter
        snprintf(newpath, 256, "perl.exe \"%s\"", path);
        return newpath;
    } else if (!strcmp(path + strlen(path) - 3, ".py")) {
        // Python scripts get python interpreter
        snprintf(newpath, 256, "python.exe \"%s\"", path);
        return newpath;
    } else {
        snprintf(newpath, 256, "\"%s\"", path);
        return newpath;
    }
}

bool banned_exec_name(char *name) {
    if (strlen(name) < 5) return false;

    const char *extension = strrchr(name, '.');
    if (extension == NULL) {
        // ban files without extension
        return true;
    }

    if (g_config->executeSuffixes().size()) {
        ++extension;
        for (execute_suffixes_t::const_iterator it_ex =
                 g_config->executeSuffixes().begin();
             it_ex != g_config->executeSuffixes().end(); ++it_ex)
            if (!strcasecmp(extension, it_ex->c_str())) return false;
        return true;
    } else {
        return (!strcasecmp(extension, ".dir") ||
                !strcasecmp(extension, ".txt"));
    }
}


int launch_program(script_container *cont) {
    enum {
        SUCCESS = 0,
        CANCELED,
        BUFFER_FULL,
        WORKING
    } result = WORKING;
    try {
        ExternalCmd command(cont->path);

        static const size_t BUFFER_SIZE = 16635;
        char buf[BUFFER_SIZE];  // i/o buffer
        memset(buf, 0, BUFFER_SIZE);
        time_t process_start = time(0);

        cont->buffer_work = (char *)HeapAlloc(
            GetProcessHeap(), HEAP_ZERO_MEMORY, HEAP_BUFFER_DEFAULT);
        unsigned long current_heap_size =
            HeapSize(GetProcessHeap(), 0, cont->buffer_work);

        int out_offset = 0;
        // outer loop -> wait until the process is finished, reading its output
        while (result == WORKING) {
            if (cont->should_terminate ||
                time(0) - process_start > cont->timeout) {
                result = CANCELED;
                continue;
            }

            cont->exit_code = command.exitCode();

            // inner loop without delay -> read all data available in
            // the pipe
            while (result == WORKING) {
                // drop stderr
                command.readStderr(buf, BUFFER_SIZE, false);

                DWORD available = command.stdoutAvailable();
                if (available == 0) {
                    break;
                }

                while (out_offset + available > current_heap_size) {
                    // Increase heap buffer
                    if (current_heap_size * 2 <= HEAP_BUFFER_MAX) {
                        cont->buffer_work = (char *)HeapReAlloc(
                            GetProcessHeap(), HEAP_ZERO_MEMORY,
                            cont->buffer_work, current_heap_size * 2);
                        current_heap_size =
                            HeapSize(GetProcessHeap(), 0, cont->buffer_work);
                    } else {
                        result = BUFFER_FULL;
                        break;
                    }
                }
                if (result != BUFFER_FULL) {
                    size_t max_read = std::min<size_t>(
                        BUFFER_SIZE - 1, current_heap_size - out_offset);


                    DWORD bread = command.readStdout(cont->buffer_work + out_offset,
                                                     max_read, true);
                    if (bread == 0) {
                        result = BUFFER_FULL;
                    }
                    out_offset += bread;
                }
            }

            if (result == BUFFER_FULL) {
                crash_log("plugin produced more than 2MB output -> dropped");
            }

            if (cont->exit_code != STILL_ACTIVE) {
                result = SUCCESS;
            }

            if (result == WORKING) {
                Sleep(10); // 10 milliseconds
            }
        }

        // if the output has a utf-16 bom, we need to convert it now, as the
        // remaining code doesn't handle wide characters
        unsigned char *buf_u =
            reinterpret_cast<unsigned char *>(cont->buffer_work);
        if ((buf_u[0] == 0xFF) && (buf_u[1] == 0xFE)) {
            wchar_t *buffer_u16 =
                reinterpret_cast<wchar_t *>(cont->buffer_work);
            std::string buffer_u8 = to_utf8(buffer_u16);
            HeapFree(GetProcessHeap(), 0, buffer_u16);
            cont->buffer_work =
                (char *)HeapAlloc(GetProcessHeap(), 0, buffer_u8.size() + 1);
            memcpy(cont->buffer_work, buffer_u8.c_str(), buffer_u8.size() + 1);
        }

        command.closeScriptHandles();
    } catch (const std::exception &e) {
        crash_log("%s", e.what());
        result = CANCELED;
    }
    return result;
}

DWORD WINAPI ScriptWorkerThread(LPVOID lpParam) {
    script_container *cont = (script_container *)lpParam;

    // Execute script
    int result = launch_program(cont);

    // Set finished status
    switch (result) {
        case 0:
            cont->status = SCRIPT_FINISHED;
            cont->last_problem = SCRIPT_NONE;
            cont->retry_count = cont->max_retries;
            cont->buffer_time = time(0);
            break;
        case 1:
            cont->status = SCRIPT_ERROR;
            cont->last_problem = SCRIPT_ERROR;
            cont->retry_count--;
            break;
        case 2:
            cont->status = SCRIPT_TIMEOUT;
            cont->last_problem = SCRIPT_TIMEOUT;
            cont->retry_count--;
            break;
        default:
            cont->status = SCRIPT_ERROR;
            cont->last_problem = SCRIPT_ERROR;
            cont->retry_count--;
    }

    // Cleanup work buffer in case the script ran into a timeout / error
    if (cont->status == SCRIPT_TIMEOUT || cont->status == SCRIPT_ERROR) {
        HeapFree(GetProcessHeap(), 0, cont->buffer_work);
        cont->buffer_work = NULL;
    }
    return 0;
}

bool script_exists(script_container *cont) {
    DWORD dwAttr = GetFileAttributes(cont->script_path);
    return !(dwAttr == INVALID_FILE_ATTRIBUTES);
}

void run_script_container(script_container *cont) {
    if ((cont->type == PLUGIN &&
         ((g_config->enabledSections() & SECTION_PLUGINS) == 0)) ||
        (cont->type == LOCAL &&
         ((g_config->enabledSections() & SECTION_LOCAL) == 0)))
        return;

    // Return if this script is no longer present
    // However, the script container is preserved
    if (!script_exists(cont)) {
        crash_log("script %s no longer exists", cont->script_path);
        return;
    }

    time_t now = time(0);
    if (now - cont->buffer_time >= cont->max_age) {
        // Check if the thread within this cont is still collecting data
        // or a thread has finished but its data wasnt processed yet
        if (cont->status == SCRIPT_COLLECT || cont->status == SCRIPT_FINISHED) {
            return;
        }
        cont->status = SCRIPT_COLLECT;

        if (cont->worker_thread != INVALID_HANDLE_VALUE)
            CloseHandle(cont->worker_thread);

        crash_log("invoke script %s", cont->script_path);
        cont->worker_thread =
            CreateThread(NULL,                // default security attributes
                         0,                   // use default stack size
                         ScriptWorkerThread,  // thread function name
                         cont,                // argument to thread function
                         0,                   // use default creation flags
                         NULL);               // returns the thread identifier

        if (cont->execution_mode == SYNC ||
            (cont->execution_mode == ASYNC &&
             g_config->defaultScriptAsyncExecution() == SEQUENTIAL))
            WaitForSingleObject(cont->worker_thread, INFINITE);

        crash_log("finished with status %d (exit code %" PRIudword ")",
                  cont->status, cont->exit_code);
    }
}

void output_external_programs(OutputProxy &out, script_type type) {
    // Collect and output data
    script_containers_t::iterator it_cont = script_containers.begin();
    script_container *cont = NULL;
    while (it_cont != script_containers.end()) {
        cont = it_cont->second;
        if (!script_exists(cont)) {
            crash_log("script %s missing", cont->script_path);
            it_cont++;
            continue;
        }

        if (cont->type == type) {
            if (cont->status == SCRIPT_FINISHED) {
                // Free buffer
                if (cont->buffer != NULL) {
                    HeapFree(GetProcessHeap(), 0, cont->buffer);
                    cont->buffer = NULL;
                }

                // Replace BOM with newlines.
                // At this point the buffer must not contain a wide character
                // encoding as the code can't handle it!
                if (strlen(cont->buffer_work) >= 3 &&
                    (unsigned char)cont->buffer_work[0] == 0xEF &&
                    (unsigned char)cont->buffer_work[1] == 0xBB &&
                    (unsigned char)cont->buffer_work[2] == 0xBF) {
                    cont->buffer_work[0] = '\n';
                    cont->buffer_work[1] = '\n';
                    cont->buffer_work[2] = '\n';
                }

                if (cont->max_age == 0) {
                    cont->buffer = cont->buffer_work;
                } else {
                    // Determine chache_info text
                    char cache_info[32];
                    snprintf(cache_info, sizeof(cache_info), ":cached(%d,%d)",
                             (int)cont->buffer_time, cont->max_age);
                    int cache_len = strlen(cache_info) + 1;

                    // We need to parse each line and replace any <<<section>>>
                    // with <<<section:cached(123455678,3600)>>>
                    // Allocate new buffer, process/modify each line of the
                    // original buffer and write it into the new buffer
                    // We increase this new buffer by a good amount, because
                    // there might be several hundred
                    // sections (e.g. veeam_backup status piggyback) within this
                    // plugin output.
                    // TODO: Maybe add a dry run mode. Count the number of
                    // section lines and reserve a fitting extra heap
                    int buffer_heap_size =
                        HeapSize(GetProcessHeap(), 0, cont->buffer_work);
                    char *cache_buffer =
                        (char *)HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY,
                                          buffer_heap_size + 262144);
                    int cache_buffer_offset = 0;

                    char *line = strtok(cont->buffer_work, "\n");
                    int write_bytes = 0;
                    while (line) {
                        int length = strlen(line);
                        int cr_offset = line[length - 1] == '\r' ? 1 : 0;
                        if (length >= 8 && strncmp(line, "<<<<", 4) &&
                            (!strncmp(line, "<<<", 3) &&
                             !strncmp(line + length - cr_offset - 3, ">>>",
                                      3))) {
                            // The return value of snprintf seems broken (off by
                            // 3?). Great...
                            write_bytes = length - cr_offset - 3 +
                                          1;  // length - \r - <<< + \0
                            snprintf(cache_buffer + cache_buffer_offset,
                                     write_bytes, "%s", line);
                            cache_buffer_offset += write_bytes - 1;

                            snprintf(cache_buffer + cache_buffer_offset,
                                     cache_len, "%s", cache_info);
                            cache_buffer_offset += cache_len - 1;

                            write_bytes =
                                3 + cr_offset + 1 + 1;  // >>> + \r + \n + \0
                            snprintf(cache_buffer + cache_buffer_offset,
                                     write_bytes, "%s\n",
                                     line + length - cr_offset - 3);
                            cache_buffer_offset += write_bytes - 1;
                        } else {
                            write_bytes = length + 1 + 1;  // length + \n + \0
                            snprintf(cache_buffer + cache_buffer_offset,
                                     write_bytes, "%s\n", line);
                            cache_buffer_offset += write_bytes - 1;
                        }
                        line = strtok(NULL, "\n");
                    }
                    HeapFree(GetProcessHeap(), 0, cont->buffer_work);
                    cont->buffer = cache_buffer;
                }

                cont->buffer_work = NULL;
                cont->status = SCRIPT_IDLE;
            } else if (cont->retry_count < 0 && cont->buffer != NULL) {
                // Remove outdated cache entries
                HeapFree(GetProcessHeap(), 0, cont->buffer);
                cont->buffer = NULL;
            }
            if (cont->buffer) out.output("%s", cont->buffer);
        }
        it_cont++;
    }
}

//  .----------------------------------------------------------------------.
//  |              ______                             ______               |
//  |             / / / /  _ __ ___  _ __ _ __   ___  \ \ \ \              |
//  |            / / / /  | '_ ` _ \| '__| '_ \ / _ \  \ \ \ \             |
//  |            \ \ \ \  | | | | | | |  | |_) |  __/  / / / /             |
//  |             \_\_\_\ |_| |_| |_|_|  | .__/ \___| /_/_/_/              |
//  |                                    |_|                               |
//  '----------------------------------------------------------------------'

void update_mrpe_includes() {
    for (unsigned int i = 0; i < g_included_mrpe_entries.size(); i++)
        delete g_included_mrpe_entries[i];
    g_included_mrpe_entries.clear();

    FILE *file;
    char line[512];
    int lineno = 0;
    for (mrpe_include_t::iterator it_include = g_config->mrpeIncludes().begin();
         it_include != g_config->mrpeIncludes().end(); it_include++) {
        char *path = (*it_include)->path;
        file = fopen(path, "r");
        if (!file) {
            crash_log("Include file not found %s", path);
            continue;
        }

        lineno = 0;
        while (!feof(file)) {
            lineno++;
            if (!fgets(line, sizeof(line), file)) {
                printf("intern clse\n");
                fclose(file);
                continue;
            }

            char *l = strip(line);
            if (l[0] == 0 || l[0] == '#' || l[0] == ';')
                continue;  // skip empty lines and comments

            // split up line at = sign
            char *s = l;
            while (*s && *s != '=') s++;
            if (*s != '=') {
                crash_log("Invalid line %d in %s.", lineno, path);
                continue;
            }
            *s = 0;
            char *value = s + 1;
            char *var = l;
            rstrip(var);
            lowercase(var);
            value = strip(value);

            if (!strcmp(var, "check")) {
                // First word: service description
                // Rest: command line
                char *service_description = next_word(&value);
                char *command_line = value;
                if (!command_line || !command_line[0]) {
                    crash_log(
                        "Invalid line %d in %s. Invalid command specification",
                        lineno, path);
                    continue;
                }

                mrpe_entry *tmp_entry = new mrpe_entry();
                memset(tmp_entry, 0, sizeof(mrpe_entry));

                strncpy(tmp_entry->command_line, command_line,
                        sizeof(tmp_entry->command_line));
                strncpy(tmp_entry->service_description, service_description,
                        sizeof(tmp_entry->service_description));

                // compute plugin name, drop directory part
                char *plugin_name = next_word(&value);
                char *p = strrchr(plugin_name, '/');
                if (!p) p = strrchr(plugin_name, '\\');
                if (p) plugin_name = p + 1;
                strncpy(tmp_entry->plugin_name, plugin_name,
                        sizeof(tmp_entry->plugin_name));
                strncpy(tmp_entry->run_as_user, (*it_include)->user,
                        sizeof(tmp_entry->run_as_user));
                g_included_mrpe_entries.push_back(tmp_entry);
            }
        }
        fclose(file);
    }
}

void section_mrpe(OutputProxy &out) {
    crash_log("<<<mrpe>>>");
    out.output("<<<mrpe>>>\n");

    update_mrpe_includes();

    mrpe_entries_t all_mrpe_entries;
    all_mrpe_entries.insert(all_mrpe_entries.end(),
                            g_config->mrpeEntries().begin(),
                            g_config->mrpeEntries().end());
    all_mrpe_entries.insert(all_mrpe_entries.end(),
                            g_included_mrpe_entries.begin(),
                            g_included_mrpe_entries.end());

    for (mrpe_entries_t::iterator it_mrpe = all_mrpe_entries.begin();
         it_mrpe != all_mrpe_entries.end(); it_mrpe++) {
        mrpe_entry *entry = *it_mrpe;
        out.output("(%s) %s ", entry->plugin_name, entry->service_description);
        crash_log("%s (%s) %s ", entry->run_as_user, entry->plugin_name,
                  entry->service_description);

        char modified_command[1024];
        char run_as_prefix[512];
        memset(run_as_prefix, 0, sizeof(run_as_prefix));
        if (strlen(entry->run_as_user) > 0)
            snprintf(run_as_prefix, sizeof(run_as_prefix), "runas /User:%s ",
                     entry->run_as_user);
        snprintf(modified_command, sizeof(modified_command), "%s%s", run_as_prefix,
                 entry->command_line);

        try {
            ExternalCmd command(modified_command);
            crash_log("Script started -> collecting data");
            std::string buffer;
            buffer.resize(8192);
            char *buf_start = &buffer[0];
            char *pos = &buffer[0];

            while (command.exitCode() == STILL_ACTIVE) {
                DWORD read = command.readStdout(
                    pos, buffer.size() - (pos - buf_start), false);

                pos += read;
                Sleep(10);
            }
            command.readStdout(pos, buffer.size() - (pos - buf_start), false);


            char *output_end = rstrip(&buffer[0]);
            char *plugin_output = lstrip(&buffer[0]);
            // replace newlines
            std::transform (plugin_output, output_end, plugin_output, [] (char ch) {
                    if (ch == '\n') return '\1';
                    if (ch == '\r') return ' ';
                    else return ch;
                    });
            int nagios_code = command.exitCode();
            out.output("%d %s\n", nagios_code, plugin_output);
            crash_log("Script finished");
            command.closeScriptHandles();
        } catch (const std::exception &e) {
            crash_log("mrpe failed: %s", e.what());
            out.output("3 Unable to execute - plugin may be missing.\n");
            continue;
        }
    }
}

//  .----------------------------------------------------------------------.
//  |                 ______  _                 _  ______                  |
//  |                / / / / | | ___   ___ __ _| | \ \ \ \                 |
//  |               / / / /  | |/ _ \ / __/ _` | |  \ \ \ \                |
//  |               \ \ \ \  | | (_) | (_| (_| | |  / / / /                |
//  |                \_\_\_\ |_|\___/ \___\__,_|_| /_/_/_/                 |
//  |                                                                      |
//  '----------------------------------------------------------------------'

void section_local(OutputProxy &out) {
    crash_log("<<<local>>>");
    out.output("<<<local>>>\n");
    output_external_programs(out, LOCAL);
}

//  .----------------------------------------------------------------------.
//  |                   ____  _             _                              |
//  |                  |  _ \| |_   _  __ _(_)_ __  ___                    |
//  |                  | |_) | | | | |/ _` | | '_ \/ __|                   |
//  |                  |  __/| | |_| | (_| | | | | \__ \                   |
//  |                  |_|   |_|\__,_|\__, |_|_| |_|___/                   |
//  |                                 |___/                                |
//  '----------------------------------------------------------------------'

void section_plugins(OutputProxy &out) {
    // Prevent errors from plugins with missing section
    out.output("<<<>>>\n");
    output_external_programs(out, PLUGIN);
    // Prevent errors from plugins with missing final newline
    out.output("\n<<<>>>\n");
}

// .-----------------------------------------------------------------------.
// |                      ____                    _                        |
// |                     / ___| _ __   ___   ___ | |                       |
// |                     \___ \| '_ \ / _ \ / _ \| |                       |
// |                      ___) | |_) | (_) | (_) | |                       |
// |                     |____/| .__/ \___/ \___/|_|                       |
// |                           |_|                                         |
// '-----------------------------------------------------------------------'
void section_spool(OutputProxy &out, const Environment &env) {
    crash_log("<<<spool>>>");
    // Look for files in the spool directory and append these files to
    // the agent output. The name of the files may begin with a number
    // of digits. If this is the case then it is interpreted as a time
    // in seconds: the maximum allowed age of the file. Outdated files
    // are simply being ignored.
    DIR *dir = opendir(env.spoolDirectory().c_str());
    if (dir) {
        WIN32_FIND_DATA filedata;
        char path[512];
        char buffer[4096];
        time_t now = time(0);

        struct dirent *de;
        while (0 != (de = readdir(dir))) {
            char *name = de->d_name;
            if (name[0] == '.') continue;

            snprintf(path, sizeof(path), "%s\\%s", env.spoolDirectory().c_str(),
                     name);
            int max_age = -1;
            if (isdigit(*name)) max_age = atoi(name);

            if (max_age >= 0) {
                HANDLE h = FindFirstFileEx(path, FindExInfoStandard, &filedata,
                                           FindExSearchNameMatch, NULL, 0);
                if (h != INVALID_HANDLE_VALUE) {
                    double mtime = file_time(&(filedata.ftLastWriteTime));
                    FindClose(h);
                    int age = now - mtime;
                    if (age > max_age) {
                        crash_log(
                            "    %s: skipping outdated file: age is %d sec, "
                            "max age is %d sec.",
                            name, age, max_age);
                        continue;
                    }
                } else {
                    crash_log("    %s: cannot determine file age", name);
                    continue;
                }
            }
            crash_log("    %s", name);

            // Output file in blocks of 4kb
            FILE *file = fopen(path, "r");
            if (file) {
                int bytes_read;
                while (0 < (bytes_read =
                                fread(buffer, 1, sizeof(buffer) - 1, file))) {
                    buffer[bytes_read] = 0;
                    out.output("%s", buffer);
                }
                fclose(file);
            }
        }
        closedir(dir);
    }
}

//  .----------------------------------------------------------------------.
//  |     ______   ____ _               _        __  __ _  __ ______       |
//  |    / / / /  / ___| |__   ___  ___| | __   |  \/  | |/ / \ \ \ \      |
//  |   / / / /  | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /   \ \ \ \     |
//  |   \ \ \ \  | |___| | | |  __/ (__|   <    | |  | | . \   / / / /     |
//  |    \_\_\_\  \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\ /_/_/_/      |
//  |                                      |_____|                         |
//  +----------------------------------------------------------------------+
//  | The section <<<check_mk>>>                                           |
//  '----------------------------------------------------------------------'

void section_check_mk(OutputProxy &out, const Environment &env) {
    crash_log("<<<check_mk>>>");
    out.output("<<<check_mk>>>\n");

    out.output("Version: %s\n", check_mk_version);
    out.output("BuildDate: %s\n", __DATE__);
#ifdef ENVIRONMENT32
    out.output("Architecture: 32bit\n");
#else
    out.output("Architecture: 64bit\n");
#endif
    out.output("AgentOS: windows\n");
    out.output("Hostname: %s\n", env.hostname().c_str());
    out.output("WorkingDirectory: %s\n", env.currentDirectory().c_str());
    out.output("ConfigFile: %s\n", g_config->configFileName(false).c_str());
    out.output("LocalConfigFile: %s\n", g_config->configFileName(true).c_str());
    out.output("AgentDirectory: %s\n", env.agentDirectory().c_str());
    out.output("PluginsDirectory: %s\n", env.pluginsDirectory().c_str());
    out.output("StateDirectory: %s\n", env.stateDirectory().c_str());
    out.output("ConfigDirectory: %s\n", env.configDirectory().c_str());
    out.output("TempDirectory: %s\n", env.tempDirectory().c_str());
    out.output("LogDirectory: %s\n", env.logDirectory().c_str());
    out.output("SpoolDirectory: %s\n", env.spoolDirectory().c_str());
    out.output("LocalDirectory: %s\n", env.localDirectory().c_str());
    out.output(
        "ScriptStatistics: Plugin C:%d E:%d T:%d "
        "Local C:%d E:%d T:%d\n",
        g_script_stat.pl_count, g_script_stat.pl_errors,
        g_script_stat.pl_timeouts, g_script_stat.lo_count,
        g_script_stat.lo_errors, g_script_stat.lo_timeouts);
    if (g_config->crashDebug()) {
        out.output("ConnectionLog: %s\n", g_connection_log);
        out.output("CrashLog: %s\n", g_crash_log);
        out.output("SuccessLog: %s\n", g_success_log);
    }

    out.output("OnlyFrom:");
    if (g_config->onlyFrom().size() == 0)
        out.output(" 0.0.0.0/0\n");
    else {
        for (only_from_t::const_iterator it_from = g_config->onlyFrom().begin();
             it_from != g_config->onlyFrom().end(); ++it_from) {
            ipspec *is = *it_from;
            if (is->ipv6) {
                out.output(" %x:%x:%x:%x:%x:%x:%x:%x/%d", is->ip.v6.address[0],
                           is->ip.v6.address[1], is->ip.v6.address[2],
                           is->ip.v6.address[3], is->ip.v6.address[4],
                           is->ip.v6.address[5], is->ip.v6.address[6],
                           is->ip.v6.address[7], is->bits);
            } else {
                out.output(" %d.%d.%d.%d/%d", is->ip.v4.address & 0xff,
                           is->ip.v4.address >> 8 & 0xff,
                           is->ip.v4.address >> 16 & 0xff,
                           is->ip.v4.address >> 24 & 0xff, is->bits);
            }
        }
        out.output("\n");
    }
}

//  .----------------------------------------------------------------------.
//  |                  ____                  _                             |
//  |                 / ___|  ___ _ ____   _(_) ___ ___                    |
//  |                 \___ \ / _ \ '__\ \ / / |/ __/ _ \                   |
//  |                  ___) |  __/ |   \ V /| | (_|  __/                   |
//  |                 |____/ \___|_|    \_/ |_|\___\___|                   |
//  |                                                                      |
//  +----------------------------------------------------------------------+
//  | Stuff dealing with the Windows service management.                   |
//  '----------------------------------------------------------------------'

TCHAR *gszServiceName = (TCHAR *)TEXT(SERVICE_NAME);
SERVICE_STATUS serviceStatus;
SERVICE_STATUS_HANDLE serviceStatusHandle = 0;

void WINAPI ServiceControlHandler(DWORD controlCode) {
    switch (controlCode) {
        case SERVICE_CONTROL_INTERROGATE:
            break;

        case SERVICE_CONTROL_SHUTDOWN:
        case SERVICE_CONTROL_STOP:
            g_should_terminate = true;
            serviceStatus.dwCurrentState = SERVICE_STOP_PENDING;
            SetServiceStatus(serviceStatusHandle, &serviceStatus);
            return;

        case SERVICE_CONTROL_PAUSE:
            break;

        case SERVICE_CONTROL_CONTINUE:
            break;

        default:
            if (controlCode >= 128 && controlCode <= 255)
                // user defined control code
                break;
            else
                // unrecognised control code
                break;
    }

    SetServiceStatus(serviceStatusHandle, &serviceStatus);
}

void WINAPI ServiceMain(DWORD, TCHAR *[]) {
    // initialise service status
    serviceStatus.dwServiceType = SERVICE_WIN32_OWN_PROCESS;
    serviceStatus.dwCurrentState = SERVICE_STOPPED;
    serviceStatus.dwControlsAccepted = 0;
    serviceStatus.dwWin32ExitCode = NO_ERROR;
    serviceStatus.dwServiceSpecificExitCode = NO_ERROR;
    serviceStatus.dwCheckPoint = 0;
    serviceStatus.dwWaitHint = 0;

    serviceStatusHandle =
        RegisterServiceCtrlHandler(gszServiceName, ServiceControlHandler);

    if (serviceStatusHandle) {
        // service is starting
        serviceStatus.dwCurrentState = SERVICE_START_PENDING;
        SetServiceStatus(serviceStatusHandle, &serviceStatus);

        // Service running
        serviceStatus.dwControlsAccepted |=
            (SERVICE_ACCEPT_STOP | SERVICE_ACCEPT_SHUTDOWN);
        serviceStatus.dwCurrentState = SERVICE_RUNNING;
        SetServiceStatus(serviceStatusHandle, &serviceStatus);

        RunImmediate("service", 0, NULL);

        // service is now stopped
        serviceStatus.dwControlsAccepted &=
            ~(SERVICE_ACCEPT_STOP | SERVICE_ACCEPT_SHUTDOWN);
        serviceStatus.dwCurrentState = SERVICE_STOPPED;
        SetServiceStatus(serviceStatusHandle, &serviceStatus);
    }
}

void RunService() {
    SERVICE_TABLE_ENTRY serviceTable[] = {{gszServiceName, ServiceMain},
                                          {0, 0}};

    StartServiceCtrlDispatcher(serviceTable);
}

void InstallService() {
    SC_HANDLE serviceControlManager =
        OpenSCManager(0, 0, SC_MANAGER_CREATE_SERVICE);

    if (serviceControlManager) {
        char path[_MAX_PATH + 1];
        if (GetModuleFileName(0, path, sizeof(path) / sizeof(path[0])) > 0) {
            char quoted_path[1024];
            snprintf(quoted_path, sizeof(quoted_path), "\"%s\"", path);
            SC_HANDLE service =
                CreateService(serviceControlManager, gszServiceName,
                              gszServiceName, SERVICE_ALL_ACCESS,
                              SERVICE_WIN32_OWN_PROCESS, SERVICE_AUTO_START,
                              SERVICE_ERROR_IGNORE, quoted_path, 0, 0, 0, 0, 0);
            if (service) {
                CloseServiceHandle(service);
                printf(SERVICE_NAME " Installed Successfully\n");
            } else {
                if (GetLastError() == ERROR_SERVICE_EXISTS)
                    printf(SERVICE_NAME " Already Exists.\n");
                else
                    printf(SERVICE_NAME
                           " Was not Installed Successfully. Error Code %d\n",
                           (int)GetLastError());
            }
        }

        CloseServiceHandle(serviceControlManager);
    }
}

void UninstallService() {
    SC_HANDLE serviceControlManager = OpenSCManager(0, 0, SC_MANAGER_CONNECT);

    if (serviceControlManager) {
        SC_HANDLE service = OpenService(serviceControlManager, gszServiceName,
                                        SERVICE_QUERY_STATUS | DELETE);
        if (service) {
            SERVICE_STATUS serviceStatus;
            if (QueryServiceStatus(service, &serviceStatus)) {
                while (in_set(serviceStatus.dwCurrentState,
                              {SERVICE_RUNNING, SERVICE_STOP_PENDING})) {
                    if (serviceStatus.dwCurrentState == SERVICE_STOP_PENDING) {
                        // wait for the wait-hint but no less than 1 second and
                        // no more than 10
                        DWORD waitTime = serviceStatus.dwWaitHint / 10;
                        waitTime =
                            std::max(1000UL, std::min(waitTime, 10000UL));
                        Sleep(waitTime);
                        if (!QueryServiceStatus(service, &serviceStatus)) {
                            break;
                        }
                    } else {
                        if (ControlService(service, SERVICE_CONTROL_STOP,
                                           &serviceStatus) == 0) {
                            break;
                        }
                    }
                }

                if (serviceStatus.dwCurrentState == SERVICE_STOPPED) {
                    if (DeleteService(service))
                        printf(SERVICE_NAME " Removed Successfully\n");
                    else {
                        DWORD dwError;
                        dwError = GetLastError();
                        if (dwError == ERROR_ACCESS_DENIED)
                            printf(
                                "Access Denied While trying to "
                                "Remove " SERVICE_NAME " \n");
                        else if (dwError == ERROR_INVALID_HANDLE)
                            printf(
                                "Handle invalid while trying to "
                                "Remove " SERVICE_NAME " \n");
                        else if (dwError == ERROR_SERVICE_MARKED_FOR_DELETE)
                            printf(SERVICE_NAME
                                   " already marked for deletion\n");
                    }
                } else {
                    printf(SERVICE_NAME " is still Running.\n");
                }
            }
            CloseServiceHandle(service);
        }
        CloseServiceHandle(serviceControlManager);
    }
}
void do_install() { InstallService(); }

void do_remove() { UninstallService(); }

void output_crash_log(OutputProxy &out) {
    out.output("<<<logwatch>>>\n");
    out.output("[[[Check_MK Agent]]]\n");
    if (g_found_crash) {
        WaitForSingleObject(g_crashlogMutex, INFINITE);
        out.output("C Check_MK Agent crashed\n");
        FILE *f = fopen(g_crash_log, "r");
        char line[1024];
        while (0 != fgets(line, sizeof(line), f)) {
            out.output("W %s", line);
        }
        ReleaseMutex(g_crashlogMutex);
        fclose(f);
        g_found_crash = false;
    }
}

//  .----------------------------------------------------------------------.
//  |          _____ ____ ____    ____             _        _              |
//  |         |_   _/ ___|  _ \  / ___|  ___   ___| | _____| |_            |
//  |           | || |   | |_) | \___ \ / _ \ / __| |/ / _ \ __|           |
//  |           | || |___|  __/   ___) | (_) | (__|   <  __/ |_            |
//  |           |_| \____|_|     |____/ \___/ \___|_|\_\___|\__|           |
//  |                                                                      |
//  +----------------------------------------------------------------------+
//  | Stuff dealing with the handling of the TCP socket                    |
//  '----------------------------------------------------------------------'

void wsa_startup() {
    WSADATA wsa;
    if (0 != WSAStartup(MAKEWORD(2, 0), &wsa)) {
        fprintf(stderr, "Cannot initialize winsock.\n");
        exit(1);
    }
}

void stop_threads() {
    // Signal any threads to shut down
    // We don't rely on any check threat running/suspended calls
    // just check the script_container status
    int sizedt = script_containers.size();
    HANDLE hThreadArray[sizedt];
    int active_thread_count = 0;

    script_containers_t::iterator it_cont = script_containers.begin();
    while (it_cont != script_containers.end()) {
        if (it_cont->second->status == SCRIPT_COLLECT) {
            hThreadArray[active_thread_count++] =
                it_cont->second->worker_thread;
            it_cont->second->should_terminate = 1;
        }
        it_cont++;
    }

    WaitForMultipleObjects(active_thread_count, hThreadArray, TRUE, 5000);
    TerminateJobObject(g_workers_job_object, 0);
    ::CloseHandle(g_workers_job_object);
}

//   .----------------------------------------------------------------------.
//   |                        __  __       _                                |
//   |                       |  \/  | __ _(_)_ __                           |
//   |                       | |\/| |/ _` | | '_ \                          |
//   |                       | |  | | (_| | | | | |                         |
//   |                       |_|  |_|\__,_|_|_| |_|                         |
//   |                                                                      |
//   '----------------------------------------------------------------------'

void usage() {
    fprintf(stderr,
            "Usage: \n"
            "check_mk_agent version         -- show version %s and exit\n"
            "check_mk_agent install         -- install as Windows NT service "
            "Check_Mk_Agent\n"
            "check_mk_agent remove          -- remove Windows NT service\n"
            "check_mk_agent adhoc           -- open TCP port %d and answer "
            "request until killed\n"
            "check_mk_agent test            -- test output of plugin, do not "
            "open TCP port\n"
            "check_mk_agent file FILENAME   -- write output of plugin into "
            "file, do not open TCP port\n"
            "check_mk_agent debug           -- similar to test, but with lots "
            "of debug output\n"
            "check_mk_agent showconfig      -- shows the effective "
            "configuration used (currently incomplete)\n",
            check_mk_version, g_config->port());
    exit(1);
}

void do_debug(const Environment &env) {
    verbose_mode = true;

    FileOutputProxy dummy(do_file ? fileout : stdout);

    update_script_statistics();
    output_data(dummy, env, g_config->enabledSections(),
                g_config->sectionFlush());
}

void do_test(bool output_stderr, const Environment &env) {
    with_stderr = output_stderr;
    FileOutputProxy dummy(do_file ? fileout : stdout);
    if (g_config->crashDebug()) {
        open_crash_log(env.logDirectory());
    }
    crash_log("Started in test mode.");
    update_script_statistics();
    output_data(dummy, env, g_config->enabledSections(),
                g_config->sectionFlush());
    if (g_config->crashDebug()) {
        close_crash_log();
    }
}

bool ctrl_handler(DWORD fdwCtrlType) {
    switch (fdwCtrlType) {
        /* handle the CTRL-C signal */
        case CTRL_C_EVENT:
            stop_threads();
            g_should_terminate = true;
            return TRUE;
        default:
            return FALSE;
    }
}

DWORD WINAPI DataCollectionThread(LPVOID lpParam) {
    do {
        g_data_collection_retriggered = false;
        for (script_containers_t::iterator it_cont = script_containers.begin();
             it_cont != script_containers.end(); ++it_cont) {
            if (it_cont->second->execution_mode == ASYNC) {
                run_script_container(it_cont->second);
            }
        }
    } while (g_data_collection_retriggered);
    return 0;
}

void determine_available_scripts(const char *dirname, script_type type,
                                 char *run_as_user) {
    DIR *dir = opendir(dirname);
    if (dir) {
        struct dirent *de;
        while (0 != (de = readdir(dir))) {
            char *name = de->d_name;

            if (name[0] != '.' && !banned_exec_name(name)) {
                char path[512];
                snprintf(path, sizeof(path), "%s\\%s", dirname, name);
                char newpath[512];
                char command_with_user[1024];
                // If the path in question is a directory -> continue
                DWORD dwAttr = GetFileAttributes(path);
                if (dwAttr != INVALID_FILE_ATTRIBUTES &&
                    (dwAttr & FILE_ATTRIBUTE_DIRECTORY)) {
                    continue;
                }

                char *command = add_interpreter(path, newpath);
                if (run_as_user != NULL && strlen(run_as_user) > 1)
                    snprintf(command_with_user, sizeof(command_with_user),
                             "runas /User:%s %s", run_as_user, command);
                else
                    snprintf(command_with_user, sizeof(command_with_user), "%s",
                             command);

                // Look if there is already an script_container available for
                // this program
                script_container *cont = NULL;
                script_containers_t::iterator it_cont =
                    script_containers.find(string(command_with_user));
                if (it_cont == script_containers.end()) {
                    // create new entry for this program
                    cont = new script_container();
                    cont->path = strdup(command_with_user);
                    cont->script_path = strdup(path);
                    cont->buffer_time = 0;
                    cont->buffer = NULL;
                    cont->buffer_work = NULL;
                    cont->type = type;
                    cont->should_terminate = 0;
                    cont->run_as_user = run_as_user;
                    cont->execution_mode =
                        get_script_execution_mode(name, type);
                    cont->timeout = get_script_timeout(name, type);
                    cont->max_retries = get_script_max_retries(name, type);
                    cont->max_age = get_script_cache_age(name, type);
                    cont->status = SCRIPT_IDLE;
                    cont->last_problem = SCRIPT_NONE;
                    script_containers[cont->path] = cont;
                }
            }
        }
        closedir(dir);
    }
}

void collect_script_data(script_execution_mode mode) {
    if (mode == SYNC) {
        crash_log("Collecting sync local/plugin data");
        for (script_containers_t::iterator it_cont = script_containers.begin();
             it_cont != script_containers.end(); it_cont++)
            if (it_cont->second->execution_mode == SYNC)
                run_script_container(it_cont->second);
    } else if (mode == ASYNC) {
        // If the thread is still running, just tell him to do another cycle
        DWORD dwExitCode = 0;
        if (GetExitCodeThread(g_collection_thread, &dwExitCode)) {
            if (dwExitCode == STILL_ACTIVE) {
                g_data_collection_retriggered = true;
                return;
            }
        }

        if (g_collection_thread != INVALID_HANDLE_VALUE)
            CloseHandle(g_collection_thread);
        crash_log("Start async thread for collecting local/plugin data");
        g_collection_thread =
            CreateThread(NULL,                  // default security attributes
                         0,                     // use default stack size
                         DataCollectionThread,  // thread function name
                         NULL,                  // argument to thread function
                         0,                     // use default creation flags
                         NULL);                 // returns the thread identifier
    }
}

struct ThreadData {
    time_t push_until;
    bool terminate;
    Environment env;
    bool new_request;
    sockaddr_storage last_address;
    Mutex mutex;
};

DWORD WINAPI realtime_check_func(void *data_in) {
    ThreadData *data = (ThreadData *)data_in;

    try {
        sockaddr_storage current_address;
        std::string current_ip;
        SOCKET current_socket = INVALID_SOCKET;

        EncryptingBufferedSocketProxy out(
            INVALID_SOCKET, g_config->passphrase(),
            BufferedSocketProxy::DEFAULT_BUFFER_SIZE);
        timeval before;
        gettimeofday(&before, 0);
        while (!data->terminate) {
            timeval now;
            gettimeofday(&now, 0);
            long duration = (now.tv_sec - before.tv_sec) * 1000 +
                            (now.tv_usec - before.tv_usec) / 1000;
            if (duration < 1000) {
                ::Sleep(1000 - duration);
            }
            gettimeofday(&before, 0);

            MutexLock guard(data->mutex);
            // adhere to the configured timeout
            if ((time(NULL) < data->push_until) && !data->terminate) {
                // if a new request was made, reestablish the connection
                if (data->new_request) {
                    data->new_request = false;
                    // (re-)establish connection if necessary
                    if (current_socket != INVALID_SOCKET) {
                        closesocket(current_socket);
                        out.setSocket(INVALID_SOCKET);
                    }
                    current_address = data->last_address;
                    if (current_address.ss_family != 0) {
                        int sockaddr_size = 0;
                        if (current_address.ss_family == AF_INET) {
                            sockaddr_in *addrv4 =
                                (sockaddr_in *)&current_address;
                            addrv4->sin_port = htons(g_config->realtimePort());
                            sockaddr_size = sizeof(sockaddr_in);
                        } else {
                            sockaddr_in6 *addrv6 =
                                (sockaddr_in6 *)&current_address;

                            if ((addrv6->sin6_addr.u.Word[0] == 0) &&
                                (addrv6->sin6_addr.u.Word[1] == 0) &&
                                (addrv6->sin6_addr.u.Word[2] == 0) &&
                                (addrv6->sin6_addr.u.Word[3] == 0) &&
                                (addrv6->sin6_addr.u.Word[4] == 0)) {
                                // this is a ipv4 address mapped to ipv6
                                // revert that mapping, otherwise we may not be
                                // able
                                // to connect.
                                sockaddr_in temp{0};
                                temp.sin_port = htons(g_config->realtimePort());
                                temp.sin_family = AF_INET;
                                memcpy(&temp.sin_addr.s_addr,
                                       addrv6->sin6_addr.u.Byte + 12, 4);

                                current_address.ss_family = AF_INET;
                                sockaddr_size = sizeof(sockaddr_in);
                                memcpy(&current_address, &temp, sockaddr_size);
                            } else {
                                // FIXME: for reasons I don't understand, the
                                // v6-address we get
                                // from getpeername has all words flipped. why?
                                // is this safe or
                                // will it break on some systems?
                                for (int i = 0; i < 16; i += 2) {
                                    BYTE temp = addrv6->sin6_addr.u.Byte[i];
                                    addrv6->sin6_addr.u.Byte[i] =
                                        addrv6->sin6_addr.u.Byte[i + 1];
                                    addrv6->sin6_addr.u.Byte[i + 1] = temp;
                                }

                                addrv6->sin6_port =
                                    htons(g_config->realtimePort());
                                sockaddr_size = sizeof(sockaddr_in6);
                            }
                        }
                        current_ip = ListenSocket::readableIP(&current_address);

                        current_socket = socket(current_address.ss_family,
                                                SOCK_DGRAM, IPPROTO_UDP);
                        if (current_socket == INVALID_SOCKET) {
                            crash_log("failed to establish socket: %d",
                                      (int)::WSAGetLastError());
                            return 1;
                        }

                        if (connect(current_socket,
                                    (const sockaddr *)&current_address,
                                    sockaddr_size) == SOCKET_ERROR) {
                            crash_log("failed to connect: %d",
                                      (int)::WSAGetLastError());
                            closesocket(current_socket);
                            current_socket = INVALID_SOCKET;
                        }
                        out.setSocket(current_socket);
                    }
                }

                // send data
                if (current_socket != INVALID_SOCKET) {
                    // send data
                    SetEnvironmentVariable("REMOTE_HOST", current_ip.c_str());
                    char timestamp[11];
                    snprintf(timestamp, 11, "%" PRIdtime, time(NULL));

                    // these writes are unencrypted!
                    out.writeBinary(RT_PROTOCOL_VERSION, 2);
                    out.writeBinary(timestamp, 10);
                    output_data(out, data->env, g_config->realtimeSections(),
                                false);
                }
            }
        }
        closesocket(current_socket);

        return 0;
    } catch (const std::exception &e) {
        crash_log("failed to run realtime check: %s", e.what());
        return 1;
    }
}

void do_adhoc(const Environment &env) {
    prepare_sections(env);

    g_should_terminate = false;

    ListenSocket sock(g_config->port(), g_config->onlyFrom(),
                      g_config->supportIPV6());

    printf("Listening for TCP connections (%s) on port %d\n",
           sock.supportsIPV6()
               ? sock.supportsIPV4() ? "IPv4 and IPv6" : "IPv6 only"
               : "IPv4 only",
           g_config->port());
    printf("Close window or press Ctrl-C to exit\n");
    fflush(stdout);

    // Job object for worker jobs. All worker are within this object
    // and receive a terminate when the agent ends
    g_workers_job_object = CreateJobObject(NULL, "workers_job");

    // Run all ASYNC scripts on startup, so that their data is available on
    // the first query of a client. Obviously, this slows down the agent
    // startup...
    // This procedure is mandatory, since we want to prevent missing agent
    // sections
    find_scripts(env);
    collect_script_data(ASYNC);
    DWORD dwExitCode = 0;
    while (true) {
        if (GetExitCodeThread(g_collection_thread, &dwExitCode)) {
            if (dwExitCode != STILL_ACTIVE) break;
            Sleep(200);
        } else
            break;
    }

    ThreadData thread_data{0, false, env};
    Thread realtime_checker(realtime_check_func, thread_data);

    crash_log("realtime monitoring %s",
              g_config->useRealtimeMonitoring() ? "active" : "inactive");

    if (g_config->useRealtimeMonitoring() != 0) {
        thread_data.terminate = false;
        realtime_checker.start();
    }

    // Das Dreckswindows kann nicht vernuenftig gleichzeitig auf
    // ein Socket und auf ein Event warten. Weil ich nicht extra
    // deswegen mit Threads arbeiten will, verwende ich einfach
    // select() mit einem Timeout und polle should_terminate.
    BufferedSocketProxy out(INVALID_SOCKET);
    while (!g_should_terminate) {
        SOCKET connection = sock.acceptConnection();
        BufferedSocketProxy out(connection);
        if ((void *)connection != NULL) {
            if (g_config->crashDebug()) {
                close_crash_log();
                open_crash_log(env.logDirectory());
            }
            out.setSocket(connection);
            std::string ip_hr = sock.readableIP(connection);
            crash_log("Accepted client connection from %s.", ip_hr.c_str());
            {  // limit lifetime of mutex lock
                MutexLock guard(thread_data.mutex);
                thread_data.new_request = true;
                thread_data.last_address = sock.address(connection);
                thread_data.push_until =
                    time(NULL) + g_config->realtimeTimeout();
            }

            SetEnvironmentVariable("REMOTE_HOST", ip_hr.c_str());
            update_script_statistics();
            try {
                output_data(out, env, g_config->enabledSections(),
                            g_config->sectionFlush());
            } catch (const std::exception &e) {
                crash_log("unhandled exception: %s", e.what());
            }
            closesocket(connection);
        }
    }

    if (realtime_checker.wasStarted()) {
        thread_data.terminate = true;
    }

    stop_threads();

    if (realtime_checker.wasStarted()) {
        int res = realtime_checker.join();
        crash_log("realtime check thread ended with errror code %d.", res);
    }

    WSACleanup();
    close_crash_log();
}

void find_scripts(const Environment &env) {
    // Check if there are new scripts available
    // Scripts in default paths
    determine_available_scripts(env.pluginsDirectory().c_str(), PLUGIN, NULL);
    determine_available_scripts(env.localDirectory().c_str(), LOCAL, NULL);
    // Scripts included with user permissions
    for (script_include_t::iterator it_include =
             g_config->scriptIncludes().begin();
         it_include != g_config->scriptIncludes().end(); ++it_include)
        determine_available_scripts((*it_include)->path, (*it_include)->type,
                                    (*it_include)->user);
}

void output_data(OutputProxy &out, const Environment &env,
                 unsigned long section_mask, bool section_flush) {
    prepare_sections(env);

    // make sure, output of numbers is not localized
    setlocale(LC_ALL, "C");

    if ((section_mask & SECTION_CRASHLOG) != 0) {
        if (g_config->crashDebug()) output_crash_log(out);
    }

    find_scripts(env);

    if ((section_mask & SECTION_CHECK_MK) != 0) {
        section_check_mk(out, env);
        if (section_flush) out.flush();
    }
    if ((section_mask & SECTION_UPTIME) != 0) {
        section_uptime(out);
        if (section_flush) out.flush();
    }
    if ((section_mask & SECTION_DF) != 0) {
        section_df(out);
        if (section_flush) out.flush();
    }
    if ((section_mask & SECTION_PS) != 0) {
        if (g_config->psUseWMI()) {
            section_ps_wmi(out);
        } else {
            section_ps(out);
        }
        if (section_flush) out.flush();
    }
    if ((section_mask & SECTION_MEM) != 0) {
        section_mem(out);
        if (section_flush) out.flush();
    }
    if ((section_mask & SECTION_FILEINFO) != 0) {
        section_fileinfo(out);
        if (section_flush) out.flush();
    }
    if ((section_mask & SECTION_SERVICES) != 0) {
        section_services(out);
        if (section_flush) out.flush();
    }
    if ((section_mask & SECTION_WINPERF_IF) != 0) {
        dump_performance_counters(out, 510, "if");
        if (section_flush) out.flush();
    }
    if ((section_mask & SECTION_WINPERF_PHYDISK) != 0) {
        dump_performance_counters(out, 234, "phydisk");
        if (section_flush) out.flush();
    }
    if ((section_mask & SECTION_WINPERF_CPU) != 0) {
        dump_performance_counters(out, 238, "processor");
        if (section_flush) out.flush();
    }
    if ((section_mask & SECTION_WINPERF_CONFIG) != 0) {
        for (winperf_counters_t::const_iterator it_wp =
                 g_config->winperfCounters().begin();
             it_wp != g_config->winperfCounters().end(); ++it_wp) {
            dump_performance_counters(out, (*it_wp)->id, (*it_wp)->name);
            if (section_flush) out.flush();
        }
    }
    if ((section_mask & SECTION_LOGWATCH) != 0) {
        section_eventlog(out, env);
        if (section_flush) out.flush();
    }
    if ((section_mask & SECTION_LOGFILES) != 0) {
        section_logfiles(out, env);
        if (section_flush) out.flush();
    }
    if ((section_mask & SECTION_DOTNET) != 0) {
        section_dotnet(out);
        if (section_flush) out.flush();
    }
    if ((section_mask & SECTION_CPU) != 0) {
        section_cpu(out);
        if (section_flush) out.flush();
    }
    if ((section_mask & SECTION_EXCHANGE) != 0) {
        section_exchange(out);
        if (section_flush) out.flush();
    }
    if ((section_mask & SECTION_WEBSERVICES) != 0) {
        section_webservices(out);
        if (section_flush) out.flush();
    }
    if ((section_mask & SECTION_OHM) != 0) {
        section_ohm(out);
        if (section_flush) out.flush();
    }

    // Start data collection of SYNC scripts
    if (((section_mask & SECTION_PLUGINS) != 0) ||
        ((section_mask & SECTION_LOCAL) != 0)) {
        collect_script_data(SYNC);
    }

    if ((section_mask & SECTION_PLUGINS) != 0) {
        section_plugins(out);
        if (section_flush) out.flush();
    }
    if ((section_mask & SECTION_LOCAL) != 0) {
        section_local(out);
        if (section_flush) out.flush();
    }
    if ((section_mask & SECTION_SPOOL) != 0) {
        section_spool(out, env);
        if (section_flush) out.flush();
    }
    if ((section_mask & SECTION_MRPE) != 0) {
        section_mrpe(out);
        if (section_flush) out.flush();
    }
    if ((section_mask & SECTION_SYSTEMTIME) != 0) {
        section_systemtime(out);
        if (section_flush) out.flush();
    }

    if (!section_flush) {
        // Send remaining data in out buffer
        out.flush();
    }

    // Start data collection of ASYNC scripts
    if (((section_mask & SECTION_PLUGINS) != 0) ||
        ((section_mask & SECTION_LOCAL) != 0)) {
        collect_script_data(ASYNC);
    }
}

void cleanup() {
    WMILookup::clear();

    unregister_all_eventlogs();  // frees a few bytes

    if (g_config != NULL) {
        for (fileinfo_paths_t::iterator it_path =
                 g_config->fileinfoPaths().begin();
             it_path != g_config->fileinfoPaths().end(); it_path++) {
            free(*it_path);
        }
        g_config->fileinfoPaths().clear();

        cleanup_logwatch();
    }
}

void show_version() { printf("Check_MK_Agent version %s\n", check_mk_version); }

const char *state_long_name(char state_id) {
    switch (state_id) {
        case 'O':
            return "ok";
        case 'W':
            return "warning";
        case 'C':
            return "crit";
        case 'I':
            return "ignore";
        default:
            return "invalid";
    }
}

const char *level_name(int level_id) {
    switch (level_id) {
        case -1:
            return "off";
        case 0:
            return "all";
        case 1:
            return "warn";
        case 2:
            return "crit";
        default:
            return "invalid";
    }
}

void show_config() {
    printf("[global]\n");
    printf("port = %d\n", g_config->port());
    printf("crash_debug = %s\n", g_config->crashDebug() ? "yes" : "no");
    if (!g_config->executeSuffixes().empty()) {
        printf("execute = ");
        for (execute_suffixes_t::iterator iter =
                 g_config->executeSuffixes().begin();
             iter != g_config->executeSuffixes().end(); ++iter) {
            printf("%s", iter->c_str());
        }
        printf("\n");
    }

    printf("\n[logwatch]\n");
    printf("send_all = %s\n",
           g_config->logwatchSendInitialEntries() ? "yes" : "no");
    for (eventlog_config_t::iterator iter = g_config->eventlogConfig().begin();
         iter != g_config->eventlogConfig().end(); ++iter) {
        printf("logfile %s = %s%s\n", iter->name.c_str(),
               iter->hide_context ? "nocontext " : "", level_name(iter->level));
    }

    printf("\n[local]\n");
    for (timeout_configs_t::iterator iter =
             g_config->timeoutConfigs(LOCAL).begin();
         iter != g_config->timeoutConfigs(LOCAL).end(); ++iter) {
        printf("timeout %s = %d\n", (*iter)->pattern, (*iter)->timeout);
    }
    for (cache_configs_t::iterator iter = g_config->cacheConfigs(LOCAL).begin();
         iter != g_config->cacheConfigs(LOCAL).end(); ++iter) {
        printf("cache_age %s = %d\n", (*iter)->pattern, (*iter)->max_age);
    }
    for (retry_count_configs_t::iterator iter =
             g_config->retryConfigs(LOCAL).begin();
         iter != g_config->retryConfigs(LOCAL).end(); ++iter) {
        printf("retry_count %s = %d\n", (*iter)->pattern, (*iter)->retries);
    }
    for (execution_mode_configs_t::iterator iter =
             g_config->executionModeConfigs(LOCAL).begin();
         iter != g_config->executionModeConfigs(LOCAL).end(); ++iter) {
        printf("execution %s = %s\n", (*iter)->pattern,
               (*iter)->mode == SYNC ? "SYNC" : "ASYNC");
    }
    for (script_include_t::iterator iter = g_config->scriptIncludes().begin();
         iter != g_config->scriptIncludes().end(); ++iter) {
        if ((*iter)->type == LOCAL) {
            printf("include %s = %s\n", (*iter)->user, (*iter)->path);
        }
    }

    printf("\n[plugin]\n");
    for (timeout_configs_t::iterator iter =
             g_config->timeoutConfigs(PLUGIN).begin();
         iter != g_config->timeoutConfigs(PLUGIN).end(); ++iter) {
        printf("timeout %s = %d\n", (*iter)->pattern, (*iter)->timeout);
    }
    for (cache_configs_t::iterator iter =
             g_config->cacheConfigs(PLUGIN).begin();
         iter != g_config->cacheConfigs(PLUGIN).end(); ++iter) {
        printf("cache_age %s = %d\n", (*iter)->pattern, (*iter)->max_age);
    }
    for (retry_count_configs_t::iterator iter =
             g_config->retryConfigs(PLUGIN).begin();
         iter != g_config->retryConfigs(PLUGIN).end(); ++iter) {
        printf("retry_count %s = %d\n", (*iter)->pattern, (*iter)->retries);
    }
    for (execution_mode_configs_t::iterator iter =
             g_config->executionModeConfigs(PLUGIN).begin();
         iter != g_config->executionModeConfigs(PLUGIN).end(); ++iter) {
        printf("execution %s = %s\n", (*iter)->pattern,
               (*iter)->mode == SYNC ? "SYNC" : "ASYNC");
    }
    for (script_include_t::iterator iter = g_config->scriptIncludes().begin();
         iter != g_config->scriptIncludes().end(); ++iter) {
        if ((*iter)->type == LOCAL) {
            printf("include %s = %s\n", (*iter)->user, (*iter)->path);
        }
    }

    printf("\n[logfiles]\n");
    for (logwatch_globlines_t::iterator iter =
             g_config->logwatchGloblines().begin();
         iter != g_config->logwatchGloblines().end(); ++iter) {
        printf("textfile = ");
        bool first = true;
        for (glob_tokens_t::iterator it_token = (*iter)->tokens.begin();
             it_token != (*iter)->tokens.end(); ++it_token) {
            if (!first) {
                printf(" | ");
            } else {
                first = false;
            }
            printf("%s", (*it_token)->pattern != NULL ? (*it_token)->pattern
                                                      : "null");
        }
        printf("\n");
        for (condition_patterns_t::iterator it_pattern =
                 (*iter)->patterns.begin();
             it_pattern != (*iter)->patterns.end(); ++it_pattern) {
            printf("%s = %s\n", state_long_name((*it_pattern)->state),
                   (*it_pattern)->glob_pattern);
        }
        printf("\n");
    }

    printf("\n[winperf]\n");
    for (winperf_counters_t::iterator iter =
             g_config->winperfCounters().begin();
         iter != g_config->winperfCounters().end(); ++iter) {
        printf("counters = %d:%s\n", (*iter)->id, (*iter)->name);
    }

    printf("\n[fileinfo]\n");
    for (fileinfo_paths_t::iterator iter = g_config->fileinfoPaths().begin();
         iter != g_config->fileinfoPaths().end(); ++iter) {
        printf("path = %s\n", (*iter));
    }

    printf("\n[mrpe]\n");
    for (mrpe_entries_t::iterator iter = g_config->mrpeEntries().begin();
         iter != g_config->mrpeEntries().end(); ++iter) {
        printf("check = %s %s\n", (*iter)->service_description,
               (*iter)->command_line);
    }

    for (mrpe_include_t::iterator iter = g_config->mrpeIncludes().begin();
         iter != g_config->mrpeIncludes().end(); ++iter) {
        printf("include = %s %s\n", (*iter)->user, (*iter)->path);
    }

    printf("\n[ps]\n");
    printf("use_wmi = %s\n", g_config->psUseWMI() ? "yes" : "no");
    printf("full_path = %s\n", g_config->psFullCommandLine() ? "yes" : "no");
}

void do_unpack_plugins(const char *plugin_filename, const Environment &env) {
    FILE *file = fopen(plugin_filename, "rb");
    if (!file) {
        printf("Unable to open Check_MK-Agent package %s\n", plugin_filename);
        exit(1);
    }

    char uninstall_file_path[512];
    snprintf(uninstall_file_path, 512, "%s\\uninstall_plugins.bat",
             env.agentDirectory().c_str());
    FILE *uninstall_file = fopen(uninstall_file_path, "w");
    fprintf(uninstall_file,
            "REM * If you want to uninstall the plugins which were installed "
            "during the\n"
            "REM * last 'check_mk_agent.exe unpack' command, just execute this "
            "script\n\n");

    bool had_error = false;
    while (true) {
        int read_bytes;
        BYTE filepath_length;
        int content_length;
        BYTE *filepath;
        BYTE *content;

        // Read Filename
        read_bytes = fread(&filepath_length, 1, 1, file);
        if (read_bytes != 1) {
            if (feof(file))
                break;
            else {
                had_error = true;
                break;
            }
        }
        filepath = (BYTE *)malloc(filepath_length + 1);
        read_bytes = fread(filepath, 1, filepath_length, file);
        filepath[filepath_length] = 0;

        if (read_bytes != filepath_length) {
            had_error = true;
            break;
        }

        // Read Content
        read_bytes = fread(&content_length, 1, sizeof(content_length), file);
        if (read_bytes != sizeof(content_length)) {
            had_error = true;
            break;
        }

        // Maximum plugin size is 20 MB
        if (content_length > 20 * 1024 * 1024) {
            had_error = true;
            break;
        }
        content = (BYTE *)malloc(content_length);
        read_bytes = fread(content, 1, content_length, file);
        if (read_bytes != content_length) {
            had_error = true;
            break;
        }

        // Extract filename and path to file
        BYTE *filename = NULL;
        BYTE *dirname = NULL;
        for (int i = filepath_length - 1; i >= 0; i--) {
            if (filepath[i] == '/') {
                if (filename == NULL) {
                    filename = filepath + i + 1;
                    dirname = filepath;
                    filepath[i] = 0;
                } else {
                    filepath[i] = '\\';
                }
            }
        }
        if (dirname == NULL) filename = filepath;

        if (dirname != NULL) {
            char new_dir[1024];
            snprintf(new_dir, sizeof(new_dir), "%s\\%s",
                     env.agentDirectory().c_str(), dirname);
            CreateDirectory(new_dir, NULL);
            fprintf(uninstall_file, "del \"%s\\%s\\%s\"\n",
                    env.agentDirectory().c_str(), dirname, filename);
        } else
            fprintf(uninstall_file, "del \"%s\\%s\"\n",
                    env.agentDirectory().c_str(), filename);

        // TODO: remove custom dirs on uninstall

        // Write plugin
        char plugin_path[512];
        if (dirname != NULL)
            snprintf(plugin_path, sizeof(plugin_path), "%s\\%s\\%s",
                     env.agentDirectory().c_str(), dirname, filename);
        else
            snprintf(plugin_path, sizeof(plugin_path), "%s\\%s",
                     env.agentDirectory().c_str(), filename);

        FILE *plugin_file = fopen(plugin_path, "wb");
        fwrite(content, 1, content_length, plugin_file);
        fclose(plugin_file);

        free(filepath);
        free(content);
    }

    fprintf(uninstall_file, "del \"%s\\uninstall_plugins.bat\"\n",
            env.agentDirectory().c_str());
    fclose(uninstall_file);
    fclose(file);

    if (had_error) {
        printf(
            "There was an error on unpacking the Check_MK-Agent package: File "
            "integrity is broken\n."
            "The file might have been installed partially!");
        exit(1);
    }
}

void load_state(const Environment &env) {
    load_eventlog_offsets(env.eventlogStatefile());
}

// do initialization of global state required to generate section output
void prepare_sections(const Environment &env) {
    static bool already_run = false;
    if (!already_run) {
        already_run = true;
        if (g_config->enabledSections() & SECTION_OHM) {
            g_ohmMonitor.reset(new OHMMonitor(env));
            bool available = false;
            try {
                wmi::Result result =
                    WMILookup::get(L"Root\\OpenHardwareMonitor")
                        .query(
                            L"SELECT Index, Name, Parent, SensorType, Value "
                            L"FROM Sensor");
                available = result.valid();
            } catch (const wmi::ComException &) {
                // query failed, probably the ohm wmi namespace doesn't exist
            }

            if (!available && !g_ohmMonitor->checkAvailabe()) {
                crash_log(
                    "ohm not installed or not runnable -> section disabled");
                g_config->disableSection(SECTION_OHM);
            }
        }

        load_state(env);
    }
}

void RunImmediate(const char *mode, int argc, char **argv) {
    // base directory structure on current working directory or registered dir
    // (from registry)?
    bool use_cwd = !strcmp(mode, "adhoc") || !strcmp(mode, "test");
    Environment env(use_cwd);

    g_config = new Configuration(env);

    if (!strcmp(mode, "test"))
        do_test(true, env);
    else if (!strcmp(mode, "file")) {
        if (argc < 1) {
            fprintf(stderr, "Please specify the name of an output file.\n");
            exit(1);
        }
        fileout = fopen(argv[0], "w");
        if (!fileout) {
            fprintf(stderr, "Cannot open %s for writing.\n", argv[2]);
            exit(1);
        }
        do_file = true;
        do_test(false, env);
        fclose(fileout);
    } else if (!strcmp(mode, "adhoc") || !strcmp(mode, "service"))
        do_adhoc(env);
    else if (!strcmp(mode, "install"))
        do_install();
    else if (!strcmp(mode, "remove"))
        do_remove();
    else if (!strcmp(mode, "unpack"))
        do_unpack_plugins(argv[0], env);
    else if (!strcmp(mode, "debug"))
        do_debug(env);
    else if (!strcmp(mode, "version"))
        show_version();
    else if (!strcmp(mode, "showconfig"))
        show_config();
    else
        usage();
}

int main(int argc, char **argv) {
    wsa_startup();

    SetConsoleCtrlHandler((PHANDLER_ROUTINE)ctrl_handler, TRUE);

    if ((argc > 2) && (strcmp(argv[1], "file") && strcmp(argv[1], "unpack")))
        usage();

    if (argc <= 1)
        RunService();
    else {
        RunImmediate(argv[1], argc - 2, argv + 2);
    }
    cleanup();
}
