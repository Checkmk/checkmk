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

// Performance-Counters:
// http://msdn.microsoft.com/en-us/library/aa373178(VS.85).aspx

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


#include <stdio.h>
#include <stdint.h>
#include <winsock2.h>
#include <ws2ipdef.h>
#include <windows.h>
#include <winbase.h>
#include <winreg.h>    // performance counters from registry
#include <tlhelp32.h>  // list of processes
#include <shellapi.h>
#include <stdarg.h>
#include <time.h>
#include <locale.h>
#include <unistd.h>
#include <sys/types.h>
#include <dirent.h>
#include <sys/types.h>
#include <stdarg.h>
#include <ctype.h>     // isspace()
#include <sys/stat.h>  // stat()
#include <sys/time.h>  // gettimeofday()
#include <map>
#include <vector>
#include <string>
#include <algorithm>
#include "stringutil.h"
#include "Environment.h"
#include "Configuration.h"
#include "ListenSocket.h"
#include "types.h"
#include "wmiHelper.h"
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

#define SERVICE_NAME "Check_MK_Agent"
#define KiloByte 1024

// Limits for static global arrays
#define MAX_EVENTLOGS                 128

// Default buffer size for reading performance counters
#define DEFAULT_BUFFER_SIZE         40960L

// Maximum heap buffer for a single local/plugin script
// This buffer contains the check output
#define HEAP_BUFFER_DEFAULT         16384L
#define HEAP_BUFFER_MAX           2097152L

// Maximum timeout for a single local/plugin script
#define DEFAULT_PLUGIN_TIMEOUT         60
#define DEFAULT_LOCAL_TIMEOUT          60

// Check compilation environment 32/64 bit
#if _WIN32 || _WIN64
#if _WIN64
#define ENVIRONMENT64
#else
#define ENVIRONMENT32
#endif
#endif


#ifdef _LP64
#define PRIdword  "d"
#define PRIudword "u"
#else
#define PRIdword  "ld"
#define PRIudword "lu"
#endif


using namespace std;


typedef map<string, script_container*> script_containers_t;
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
char *ipv4_to_text(uint32_t ip);
void output_data(SOCKET &out, const Environment &env);
double file_time(const FILETIME *filetime);
void open_crash_log(const std::string &log_directory);
void close_crash_log();
void lowercase(char* value);
void collect_script_data(script_execution_mode mode);
void find_scripts(const Environment &env);
void RunImmediate(const char *mode, int argc, char **argv);

void output(SOCKET &out, const char *format, ...) __attribute__ ((format (gnu_printf, 2, 3)));
void crash_log(const char *format, ...) __attribute__ ((format (gnu_printf, 1, 2)));
void verbose(const char *format, ...) __attribute__ ((format (gnu_printf, 1, 2)));

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


bool verbose_mode               = false;
bool do_tcp                     = false;
bool with_stderr                = false;
bool force_tcp_output           = false; // if true, send socket data immediately
bool do_file                    = false;
static FILE* fileout;

OSVERSIONINFO osv;

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
volatile bool g_should_terminate  = false;
volatile bool g_data_collection_retriggered = false;
HANDLE        g_collection_thread;

// Job object for all worker threads
// Gets terminated on shutdown
HANDLE        g_workers_job_object;

// Mutex for crash.log
HANDLE crashlogMutex = CreateMutex(NULL, FALSE, NULL);

// Variables for section <<<logwatch>>>
bool logwatch_suppress_info        = true;

// dynamic buffer for event log entries. Grows with the
// time as needed. Never shrinked.
char *eventlog_buffer    = 0;
int eventlog_buffer_size = 0;

Configuration *g_config;

char g_crash_log[256];
char g_connection_log[256];
char g_success_log[256];

mrpe_entries_t g_included_mrpe_entries;

eventlog_hints_t g_eventlog_hints;
eventlog_state_t g_eventlog_state;

// Pointer to open crash log file, if crash_debug = on
HANDLE g_connectionlog_file;
struct timeval g_crashlog_start;
bool   g_found_crash = false;

wmi::Helper *g_wmi_helper = NULL;




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

#ifdef DEBUG
void debug(char *text)
{
    FILE *debugout = fopen("C:\\check_mk_agent.log", "a");
    if (debugout) {
        fprintf(debugout, "%s\n", text);
        fflush(debugout);
        fclose(debugout);
    }
}
#else
#define debug(C)
#endif


void verbose(const char *format, ...)
{
    if (!verbose_mode)
        return;

    va_list ap;
    va_start(ap, format);
    printf("DEBUG: ");
    vprintf(format, ap);
    va_end(ap);
    printf("\n");
    fflush(stdout);
}


// determine system root by reading the environment variable
// %SystemRoot%. This variable is used in the registry entries
// that describe eventlog messages.
const char *system_root()
{
    static char root[128];
    if (0 < GetWindowsDirectory(root, sizeof(root)))
        return root;
    else
        return "C:\\WINDOWS";
}

double current_time()
{
    SYSTEMTIME systime;
    FILETIME filetime;
    GetSystemTime(&systime);
    SystemTimeToFileTime(&systime, &filetime);
    return file_time(&filetime);
}

#define WINDOWS_TICK 10000000
#define SEC_TO_UNIX_EPOCH 11644473600LL
double file_time(const FILETIME *filetime)
{
    _ULARGE_INTEGER uli;
    uli.LowPart = filetime->dwLowDateTime;
    uli.HighPart = filetime->dwHighDateTime;
    return double(uli.QuadPart / (double)WINDOWS_TICK - SEC_TO_UNIX_EPOCH);
}

void char_replace(char what, char into, char *in)
{
    while (*in) {
        if (*in == what)
            *in = into;
        in++;
    }
}

// Debug function for script containers
void debug_script_container( script_container* container )
{
    crash_log("command:     %s", container->path);
    crash_log("cache age:   %d", container->max_age);
    crash_log("timeout:     %d", container->timeout);
    crash_log("time:        %d", (int)container->buffer_time);
    crash_log("status:      %d", container->status);
    crash_log("buffer:      \n<<<<\n%s\n>>>>", container->buffer);
    crash_log("buffer_work: \n<<<<\n%s\n>>>>", container->buffer_work);
}


template <typename FuncT> FuncT dynamic_func(LPCWSTR dllName, LPCSTR funcName) {
    HMODULE mod = LoadLibraryW(dllName);
    if (mod != NULL) {
        FARPROC proc = GetProcAddress(mod, funcName);
        if (proc != NULL) {
            return (FuncT)proc;
        }
    }
    return NULL;
}

#define DYNAMIC_FUNC(func, dllName) func ## _type func ## _dyn = dynamic_func<func ## _type>(dllName, #func)
// GetProcessHandleCount_type GetProcessHandleCount_dyn = dynamic_func<GetProcessHandleCount_type>(L"kernel32.dll", "GetProcessHandleCount");

//  .----------------------------------------------------------------------.
//  |  ______              _                 _   _               ______    |
//  | / / / /___ _   _ ___| |_ ___ _ __ ___ | |_(_)_ __ ___   ___\ \ \ \   |
//  |/ / / // __| | | / __| __/ _ \ '_ ` _ \| __| | '_ ` _ \ / _ \\ \ \ \  |
//  |\ \ \ \\__ \ |_| \__ \ ||  __/ | | | | | |_| | | | | | |  __// / / /  |
//  | \_\_\_\___/\__, |___/\__\___|_| |_| |_|\__|_|_| |_| |_|\___/_/_/_/   |
//  |            |___/                                                     |
//  '----------------------------------------------------------------------'

void section_systemtime(SOCKET &out)
{
    crash_log("<<<systemtime>>>");
    output(out, "<<<systemtime>>>\n");
    output(out, "%.0f\n", current_time());
}

//  .----------------------------------------------------------------------.
//  |          ______              _   _                 ______            |
//  |         / / / /  _   _ _ __ | |_(_)_ __ ___   ___  \ \ \ \           |
//  |        / / / /  | | | | '_ \| __| | '_ ` _ \ / _ \  \ \ \ \          |
//  |        \ \ \ \  | |_| | |_) | |_| | | | | | |  __/  / / / /          |
//  |         \_\_\_\  \__,_| .__/ \__|_|_| |_| |_|\___| /_/_/_/           |
//  |                       |_|                                            |
//  '----------------------------------------------------------------------'

void section_uptime(SOCKET &out)
{
    crash_log("<<<uptime>>>");
    output(out, "<<<uptime>>>\n");
    static LARGE_INTEGER Frequency, Ticks;
    QueryPerformanceFrequency(&Frequency);
    QueryPerformanceCounter(&Ticks);
    Ticks.QuadPart = Ticks.QuadPart - Frequency.QuadPart;
    unsigned int uptime = (double)Ticks.QuadPart / Frequency.QuadPart;
    output(out, "%u\n", uptime);
}



//  .----------------------------------------------------------------------.
//  |                      ______      _  __  ______                       |
//  |                     / / / /   __| |/ _| \ \ \ \                      |
//  |                    / / / /   / _` | |_   \ \ \ \                     |
//  |                    \ \ \ \  | (_| |  _|  / / / /                     |
//  |                     \_\_\_\  \__,_|_|   /_/_/_/                      |
//  |                                                                      |
//  '----------------------------------------------------------------------'

void df_output_filesystem(SOCKET &out, char *volid)
{
    TCHAR fsname[128];
    TCHAR volume[512];
    DWORD dwSysFlags = 0;
    if (!GetVolumeInformation(volid, volume, sizeof(volume), 0, 0, &dwSysFlags, fsname, sizeof(fsname)))
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

        if (volume[0]) // have a volume name
            char_replace(' ', '_', volume);
        else
            strncpy(volume, volid, sizeof(volume));

        output(out, "%s %s ", volume, fsname);
        output(out, "%" PRIu64 " ", total.QuadPart / KiloByte);
        output(out, "%" PRIu64 " ", (total.QuadPart - free_avail.QuadPart) / KiloByte);
        output(out, "%" PRIu64 " ", free_avail.QuadPart / KiloByte);
        output(out, "%3.0f%% ", perc_used);
        output(out, "%s\n", volid);
    }
}

void df_output_mountpoints(SOCKET &out, char *volid)
{
    char mountpoint[512];
    HANDLE hPt = FindFirstVolumeMountPoint(volid, mountpoint, sizeof(mountpoint));
    if (hPt != INVALID_HANDLE_VALUE) {
        while (true) {
            TCHAR combined_path[1024];
            snprintf(combined_path, sizeof(combined_path), "%s%s", volid, mountpoint);
            df_output_filesystem(out, combined_path);
            if (!FindNextVolumeMountPoint(hPt, mountpoint, sizeof(mountpoint)))
                break;
        }
        FindVolumeMountPointClose(hPt);
    }
}

void section_df(SOCKET &out)
{
    crash_log("<<<df>>>");
    output(out, "<<<df>>>\n");
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
const char *service_start_type(SC_HANDLE scm, LPCWSTR service_name)
{
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
                lpsc = (LPQUERY_SERVICE_CONFIG) LocalAlloc(LMEM_FIXED, cbBufSize);
                if (QueryServiceConfig(schService, lpsc, cbBufSize, &dwBytesNeeded)) {
                    switch (lpsc->dwStartType) {
                        case SERVICE_AUTO_START:    start_type = "auto"; break;
                        case SERVICE_BOOT_START:    start_type = "boot"; break;
                        case SERVICE_DEMAND_START:  start_type = "demand"; break;
                        case SERVICE_DISABLED:      start_type = "disabled"; break;
                        case SERVICE_SYSTEM_START:  start_type = "system"; break;
                        default:                    start_type = "other";
                    }
                }
                LocalFree(lpsc);
            }
        }
        CloseServiceHandle(schService);
    }
    return start_type;
}


void section_services(SOCKET &out)
{
    crash_log("<<<services>>>");
    output(out, "<<<services>>>\n");
    SC_HANDLE scm = OpenSCManager(0, 0, SC_MANAGER_CONNECT | SC_MANAGER_ENUMERATE_SERVICE);
    if (scm != INVALID_HANDLE_VALUE) {
        DWORD bytes_needed = 0;
        DWORD num_services = 0;
        // first determine number of bytes needed
        EnumServicesStatusExW(scm, SC_ENUM_PROCESS_INFO, SERVICE_WIN32, SERVICE_STATE_ALL,
                NULL, 0, &bytes_needed, &num_services, 0, 0);
        if (GetLastError() == ERROR_MORE_DATA && bytes_needed > 0) {
            BYTE *buffer = (BYTE *)malloc(bytes_needed);
            if (buffer) {
                if (EnumServicesStatusExW(scm, SC_ENUM_PROCESS_INFO, SERVICE_WIN32, SERVICE_STATE_ALL,
                            buffer, bytes_needed,
                            &bytes_needed, &num_services, 0, 0))
                {
                    ENUM_SERVICE_STATUS_PROCESSW *service = (ENUM_SERVICE_STATUS_PROCESSW*)buffer;
                    for (unsigned i=0; i<num_services; i++) {
                        DWORD state = service->ServiceStatusProcess.dwCurrentState;
                        const char *state_name = "unknown";
                        switch (state) {
                            case SERVICE_CONTINUE_PENDING: state_name = "continuing"; break;
                            case SERVICE_PAUSE_PENDING:    state_name = "pausing"; break;
                            case SERVICE_PAUSED:           state_name = "paused"; break;
                            case SERVICE_RUNNING:          state_name = "running"; break;
                            case SERVICE_START_PENDING:    state_name = "starting"; break;
                            case SERVICE_STOP_PENDING:     state_name = "stopping"; break;
                            case SERVICE_STOPPED:          state_name = "stopped"; break;
                        }

                        const char *start_type = service_start_type(scm, service->lpServiceName);

                        // The service name usually does not contain spaces. But
                        // in some cases it does. We replace them with _ in order
                        // the keep it in one space-separated column. Since we own
                        // the buffer, we can simply change the name inplace.
                        for (LPWSTR w=service->lpServiceName; *w; ++w) {
                            if (*w == L' ')
                                *w = L'_';
                        }

                        output(out, "%ls %s/%s %s\n",
                                service->lpServiceName, state_name, start_type,
                                to_utf8(service->lpDisplayName).c_str());
                        service ++;
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

// Hilfsfunktionen zum Navigieren in den Performance-Counter Binaerdaten
PERF_OBJECT_TYPE *FirstObject(PERF_DATA_BLOCK *dataBlock) {
    return (PERF_OBJECT_TYPE *) ((BYTE *)dataBlock + dataBlock->HeaderLength);
}
PERF_OBJECT_TYPE *NextObject(PERF_OBJECT_TYPE *act) {
    return (PERF_OBJECT_TYPE *) ((BYTE *)act + act->TotalByteLength);
}
PERF_COUNTER_DEFINITION *FirstCounter(PERF_OBJECT_TYPE *perfObject) {
    return (PERF_COUNTER_DEFINITION *) ((BYTE *) perfObject + perfObject->HeaderLength);
}
PERF_COUNTER_DEFINITION *NextCounter(PERF_COUNTER_DEFINITION *perfCounter) {
    return (PERF_COUNTER_DEFINITION *) ((BYTE *) perfCounter + perfCounter->ByteLength);
}
PERF_COUNTER_BLOCK *GetCounterBlock(PERF_INSTANCE_DEFINITION *pInstance) {
    return (PERF_COUNTER_BLOCK *) ((BYTE *)pInstance + pInstance->ByteLength);
}
PERF_INSTANCE_DEFINITION *FirstInstance (PERF_OBJECT_TYPE *pObject) {
    return (PERF_INSTANCE_DEFINITION *)  ((BYTE *) pObject + pObject->DefinitionLength);
}
PERF_INSTANCE_DEFINITION *NextInstance (PERF_INSTANCE_DEFINITION *pInstance) {
    return (PERF_INSTANCE_DEFINITION *) ((BYTE *)pInstance + pInstance->ByteLength + GetCounterBlock(pInstance)->ByteLength);
}

void outputCounter(SOCKET &out, BYTE *datablock, int counter,
        PERF_OBJECT_TYPE *objectPtr, PERF_COUNTER_DEFINITION *counterPtr);
void outputCounterValue(SOCKET &out, PERF_COUNTER_DEFINITION *counterPtr, PERF_COUNTER_BLOCK *counterBlockPtr);


void dump_performance_counters(SOCKET &out, unsigned counter_base_number, const char *countername)
{
    crash_log("<<<winperf_%s>>>", countername);
    static LARGE_INTEGER Frequency;
    QueryPerformanceFrequency (&Frequency);

    // registry entry is ascii representation of counter index
    char counter_index_name[8];
    snprintf(counter_index_name, sizeof(counter_index_name), "%u", counter_base_number);

    // allocate block to store counter data block
    DWORD size = DEFAULT_BUFFER_SIZE;
    BYTE *data = new BYTE[DEFAULT_BUFFER_SIZE];
    DWORD type;
    DWORD ret;

    // Holt zu einem bestimmten Counter den kompletten Binärblock aus der
    // Registry. Da man vorher nicht weiß, wie groß der Puffer sein muss,
    // kann man nur mit irgendeiner Größe anfangen und dann diesen immer
    // wieder größer machen, wenn er noch zu klein ist. >:-P
    while ((ret = RegQueryValueEx(HKEY_PERFORMANCE_DATA, counter_index_name,
                    0, &type, data, &size)) != ERROR_SUCCESS)
    {
        if (ret == ERROR_MORE_DATA) // WIN32 API sucks...
        {
            // Der Puffer war zu klein. Toll. Also den Puffer größer machen
            // und das ganze nochmal probieren.
            size += DEFAULT_BUFFER_SIZE;
            verbose("Buffer for RegQueryValueEx too small. Resizing...");
            delete [] data;
            data = new BYTE [size];
        }
        else {
            // Es ist ein anderer Fehler aufgetreten. Abbrechen.
            delete [] data;
            return;
        }
    }
    crash_log(" - read performance data, buffer size %" PRIudword, size);

    PERF_DATA_BLOCK *dataBlockPtr = (PERF_DATA_BLOCK *)data;

    // Determine first object in list of objects
    PERF_OBJECT_TYPE *objectPtr = FirstObject(dataBlockPtr);

    // awkward way to ensure we really really only create the section header if there
    // are performance counters
    bool first_counter = true;

    // Now walk through the list of objects. The bad news is:
    // even if we expect only one object, windows might send
    // us more than one object. We need to scan a list of objects
    // in order to find the one we have asked for. >:-P
    for (unsigned int a=0 ; a < dataBlockPtr->NumObjectTypes ; a++)
    {
        // Have we found the object we seek?
        if (objectPtr->ObjectNameTitleIndex == counter_base_number)
        {
            // Yes. Great. Now: each object consist of a lot of counters.
            // We walk through the list of counters in this object:

            // get pointer to first counter
            PERF_COUNTER_DEFINITION *counterPtr = FirstCounter(objectPtr);

            // Now we make a first quick walk through all counters, only in order
            // to find the beginning of the data block (which comes after the
            // counter definitions)
            PERF_COUNTER_DEFINITION *last_counter = FirstCounter(objectPtr);
            for (unsigned int b=0 ; b < objectPtr->NumCounters ; b++)
                last_counter = NextCounter(last_counter);
            BYTE *datablock = (BYTE *)last_counter;

            // In case of multi-instance objects, output a list of all instance names
            int num_instances = objectPtr->NumInstances;
            if (num_instances >= 0)
            {
                if (first_counter) {
                    output(out, "<<<winperf_%s>>>\n", countername);
                    output(out, "%.2f %u %" PRId64 "\n", current_time(), counter_base_number, Frequency.QuadPart);
                    first_counter = false;
                }

                output(out, "%d instances:", num_instances);
                char name[512];
                PERF_INSTANCE_DEFINITION *instancePtr = FirstInstance(objectPtr);
                for(int b=0 ; b<objectPtr->NumInstances ; b++)
                {
                    WCHAR *name_start = (WCHAR *)((char *)(instancePtr) + instancePtr->NameOffset);
                    memcpy(name, name_start, instancePtr->NameLength);
                    WideCharToMultiByte(CP_UTF8, 0, name_start, instancePtr->NameLength, name, sizeof(name), NULL, NULL);
                    // replace spaces with '_'
                    for (char *s = name; *s; s++)
                        if (*s == ' ') *s = '_';

                    output(out, " %s", name);
                    instancePtr = NextInstance(instancePtr);
                }
                output(out, "\n");
            }

            if (first_counter && (objectPtr->NumCounters > 0)) {
                output(out, "<<<winperf_%s>>>\n", countername);
                output(out, "%.2f %u %" PRId64 "\n", current_time(), counter_base_number, Frequency.QuadPart);
                first_counter = false;
            }

            // Now walk through the counter list a second time and output all counters
            for (unsigned int b=0 ; b < objectPtr->NumCounters ; b++)
            {
                outputCounter(out, datablock, counter_base_number, objectPtr, counterPtr);
                counterPtr = NextCounter(counterPtr);
            }
        }
        // naechstes Objekt in der Liste
        objectPtr = NextObject(objectPtr);
    }
    delete [] data;
}


void outputCounter(SOCKET &out, BYTE *datablock, int counter_base_number,
        PERF_OBJECT_TYPE *objectPtr, PERF_COUNTER_DEFINITION *counterPtr)
{

    // determine the type of the counter (for verbose output)
    const char *countertypename = 0;
    switch (counterPtr->CounterType) {
        case PERF_COUNTER_COUNTER:                countertypename = "counter"; break;
        case PERF_COUNTER_TIMER:                  countertypename = "timer"; break;
        case PERF_COUNTER_QUEUELEN_TYPE:          countertypename = "queuelen_type"; break;
        case PERF_COUNTER_BULK_COUNT:             countertypename = "bulk_count"; break;
        case PERF_COUNTER_TEXT:                   countertypename = "text"; break;
        case PERF_COUNTER_RAWCOUNT:               countertypename = "rawcount"; break;
        case PERF_COUNTER_LARGE_RAWCOUNT:         countertypename = "large_rawcount"; break;
        case PERF_COUNTER_RAWCOUNT_HEX:           countertypename = "rawcount_hex"; break;
        case PERF_COUNTER_LARGE_RAWCOUNT_HEX:     countertypename = "large_rawcount_HEX"; break;
        case PERF_SAMPLE_FRACTION:                countertypename = "sample_fraction"; break;
        case PERF_SAMPLE_COUNTER:                 countertypename = "sample_counter"; break;
        case PERF_COUNTER_NODATA:                 countertypename = "nodata"; break;
        case PERF_COUNTER_TIMER_INV:              countertypename = "timer_inv"; break;
        case PERF_SAMPLE_BASE:                    countertypename = "sample_base"; break;
        case PERF_AVERAGE_TIMER:                  countertypename = "average_timer"; break;
        case PERF_AVERAGE_BASE:                   countertypename = "average_base"; break;
        case PERF_AVERAGE_BULK:                   countertypename = "average_bulk"; break;
        case PERF_100NSEC_TIMER:                  countertypename = "100nsec_timer"; break;
        case PERF_100NSEC_TIMER_INV:              countertypename = "100nsec_timer_inv"; break;
        case PERF_COUNTER_MULTI_TIMER:            countertypename = "multi_timer"; break;
        case PERF_COUNTER_MULTI_TIMER_INV:        countertypename = "multi_timer_inV"; break;
        case PERF_COUNTER_MULTI_BASE:             countertypename = "multi_base"; break;
        case PERF_100NSEC_MULTI_TIMER:            countertypename = "100nsec_multi_timer"; break;
        case PERF_100NSEC_MULTI_TIMER_INV:        countertypename = "100nsec_multi_timer_inV"; break;
        case PERF_RAW_FRACTION:                   countertypename = "raw_fraction"; break;
        case PERF_RAW_BASE:                       countertypename = "raw_base"; break;
        case PERF_ELAPSED_TIME:                   countertypename = "elapsed_time"; break;
    }

    // Output index of counter object and counter, and timestamp
    output(out, "%d", static_cast<int>(counterPtr->CounterNameTitleIndex) - counter_base_number);

    // If this is a multi-instance-counter, loop over the instances
    int num_instances = objectPtr->NumInstances;
    if (num_instances >= 0)
    {
        // get pointer to first instance
        PERF_INSTANCE_DEFINITION *instancePtr = FirstInstance(objectPtr);

        for (int b=0 ; b<objectPtr->NumInstances ; b++)
        {
            // PERF_COUNTER_BLOCK dieser Instanz ermitteln.
            PERF_COUNTER_BLOCK *counterBlockPtr = GetCounterBlock(instancePtr);
            outputCounterValue(out, counterPtr, counterBlockPtr);
            instancePtr = NextInstance(instancePtr);
        }

    }
    else { // instanceless counter
        PERF_COUNTER_BLOCK *counterBlockPtr = (PERF_COUNTER_BLOCK *) datablock;
        outputCounterValue(out, counterPtr, counterBlockPtr);
    }
    if (countertypename)
        output(out, " %s\n", countertypename);
    else
        output(out, " type(%lx)\n", counterPtr->CounterType);
}


void outputCounterValue(SOCKET &out, PERF_COUNTER_DEFINITION *counterPtr, PERF_COUNTER_BLOCK *counterBlockPtr)
{
    unsigned offset = counterPtr->CounterOffset;
    int size = counterPtr->CounterSize;
    BYTE *pData = ((BYTE *)counterBlockPtr) + offset;

    if (counterPtr->CounterType & PERF_SIZE_DWORD)
        output(out, " %lu", *(DWORD*)pData);

    else if (counterPtr->CounterType & PERF_SIZE_LARGE)
        output(out, " %" PRIu64, *(UNALIGNED ULONGLONG*)pData);

    // handle other data generically. This is wrong in some situation.
    // Once upon a time in future we might implement a conversion as
    // described in http://msdn.microsoft.com/en-us/library/aa373178%28v=vs.85%29.aspx
    else if (size == 4) {
        DWORD value = *((DWORD *)pData);
        output(out, " %lu", value);
    }
    else if (size == 8) {
        DWORD *data_at = (DWORD *)pData;
        DWORDLONG value = (DWORDLONG)*data_at + ((DWORDLONG)*(data_at + 1) << 32);
        output(out, " %" PRIu64, value);
    }
    else
        output(out, " unknown");
}

void section_winperf(SOCKET &out)
{
    dump_performance_counters(out, 234, "phydisk");
    dump_performance_counters(out, 238, "processor");
    dump_performance_counters(out, 510, "if");

    // also output additionally configured counters
    for (winperf_counters_t::const_iterator it_wp = g_config->winperfCounters().begin();
            it_wp != g_config->winperfCounters().end(); ++it_wp) {
        dump_performance_counters(out, (*it_wp)->id, (*it_wp)->name);
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

void grow_eventlog_buffer(int newsize)
{
    delete [] eventlog_buffer;
    eventlog_buffer = new char[newsize];
    eventlog_buffer_size = newsize;
}


bool output_eventlog_entry(SOCKET &out, char *dllpath, EVENTLOGRECORD *event, char type_char,
        const char *logname, const char *source_name, WCHAR **strings)
{
    char msgbuffer[8192];
    char dll_realpath[128];
    HINSTANCE dll;

    // if no dllpath is NULL, we output the message without text conversion and
    // always succeed. If a dll pathpath is given, we only succeed if the conversion
    // is successfull.

    if (dllpath) {
        // to make it even more difficult, dllpath may contain %SystemRoot%, which
        // must be replaced with the environment variable %SystemRoot% (most probably -
        // but not entirely for sure - C:\WINDOWS
        if (strncasecmp(dllpath, "%SystemRoot%", 12) == 0)
            snprintf(dll_realpath, sizeof(dll_realpath), "%s%s", system_root(), dllpath + 12);
        else if (strncasecmp(dllpath, "%windir%", 8) == 0)
            snprintf(dll_realpath, sizeof(dll_realpath), "%s%s", system_root(), dllpath + 8);
        else
            snprintf(dll_realpath, sizeof(dll_realpath), "%s", dllpath);

        // I found this path in the official API documentation. I hope
        // it's correct for all windows versions
        dll =  LoadLibrary(dll_realpath);
        if (!dll) {
            crash_log("     --> failed to load %s", dll_realpath);
            return false;
        }
    }
    else
        dll = NULL;

    WCHAR wmsgbuffer[8192];
    DWORD dwFlags = FORMAT_MESSAGE_ARGUMENT_ARRAY | FORMAT_MESSAGE_FROM_SYSTEM;
    if (dll)
        dwFlags |= FORMAT_MESSAGE_FROM_HMODULE;

    crash_log("Event ID: %lu.%lu",
            event->EventID / 65536, // "Qualifiers": no idea what *that* is
            event->EventID % 65536); // the actual event id
    crash_log("Formatting Message");
    DWORD len = FormatMessageW(
        dwFlags,
        dll,
        event->EventID,
        0, // accept any language
        wmsgbuffer,
        // msgbuffer,
        8192,
        (char **)strings
    );
    crash_log("Formatting Message - DONE");

    if (dll)
        FreeLibrary(dll);

    if (len) {
        // convert message to UTF-8
        len = WideCharToMultiByte(CP_UTF8, 0, wmsgbuffer, -1, msgbuffer, sizeof(msgbuffer), NULL, NULL);
    }

    if (len == 0) // message could not be converted
    {
        // if conversion was not successfull while trying to load a DLL, we return a
        // failure. Our parent function will then retry later without a DLL path.
        if (dllpath)
            return false;

        // if message cannot be converted, then at least output the text strings.
        // We render all messages one after the other into msgbuffer, separated
        // by spaces.
        memset(msgbuffer, 0, sizeof(msgbuffer)); // avoids problems with 0-termination
        char *w = msgbuffer;
        int sizeleft = sizeof(msgbuffer) - 1; // leave one byte for termination
        int n = 0;
        while (strings[n]) // string array is zero terminated
        {
            WCHAR *s = strings[n];
            DWORD len = WideCharToMultiByte(CP_UTF8, 0, s, -1, w, sizeleft, NULL, NULL);
            if (!len)
                break;
            sizeleft -= len;
            w += len;
            if (sizeleft <= 0)
                break;
            n++;
            if (strings[n])
                *w++ = ' ';
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

    output(out, "%c %s %lu.%lu %s %s\n", type_char, timestamp,
            event->EventID / 65536, // "Qualifiers": no idea what *that* is
            event->EventID % 65536, // the actual event id
            source_name, msgbuffer);
    return true;
}


void process_eventlog_entries(SOCKET &out, const char *logname, char *buffer,
        DWORD bytesread, DWORD *record_number, bool do_not_output,
        int *worst_state, int level, int hide_context)
{
    WCHAR *strings[64];
    char regpath[128];
    BYTE dllpath[128];
    char source_name[128];

    EVENTLOGRECORD *event = (EVENTLOGRECORD *)buffer;
    while (bytesread > 0)
    {
        crash_log("     - record %lu: process_eventlog_entries bytesread %lu, event->Length %lu", *record_number, bytesread, event->Length);
        *record_number = event->RecordNumber;

        char type_char;
        int this_state;
        switch (event->EventType) {
            case EVENTLOG_ERROR_TYPE:
                type_char = 'C';
                this_state = 2;
                break;
            case EVENTLOG_WARNING_TYPE:
                type_char = 'W';
                this_state = 1;
                break;
            case EVENTLOG_INFORMATION_TYPE:
            case EVENTLOG_AUDIT_SUCCESS:
            case EVENTLOG_SUCCESS:
                type_char = level == 0 ? 'O' : '.';
                this_state = 0;
                break;
            case EVENTLOG_AUDIT_FAILURE:
                type_char = 'C';
                this_state = 2;
                break;
            default:
                type_char = 'u';
                this_state = 1;
                break;
        }
        if (*worst_state < this_state)
            *worst_state = this_state;

        // If we are not just scanning for the current end and the worst state,

        // we output the event message
        if (!do_not_output && (!hide_context || type_char != '.'))
        {
            // The source name is the name of the application that produced the event
            // It is UTF-16 encoded
            WCHAR *lpSourceName = (WCHAR *) ((LPBYTE) event + sizeof(EVENTLOGRECORD));
            WideCharToMultiByte(CP_UTF8, 0, lpSourceName, -1, source_name, sizeof(source_name), NULL, NULL);

            char *w = source_name;
            while (*w) {
                if (*w == ' ') *w = '_';
                w++;
            }

            // prepare array of zero terminated strings to be inserted
            // into message template.
            DWORD num_strings = event->NumStrings;
            WCHAR *s = (WCHAR *)(((char *)event) + event->StringOffset);
            unsigned ns;
            for (ns = 0; ns < 63; ns++) {
                if (ns < num_strings) {
                    strings[ns] = s;
                    s += wcslen(s) + 1;
                }
                else
                    // Sometimes the eventlog record does not provide
                    // enough strings for the message template. Causes crash...
                    // -> Fill the rest with empty strings
                    strings[ns] = (WCHAR *)"";
            }
            strings[63] = 0; // end marker in array

            // Windows eventlog entries refer to texts stored in a DLL >:-P
            // We need to load this DLL. First we need to look up which
            // DLL to load in the registry. Hard to image how one could
            // have contrieved this more complicated...
            snprintf(regpath, sizeof(regpath),
                    "SYSTEM\\CurrentControlSet\\Services\\Eventlog\\%s\\%S",
                    logname, lpSourceName);

            HKEY key;
            DWORD ret = RegOpenKeyEx(HKEY_LOCAL_MACHINE, regpath, 0, KEY_READ, &key);

            bool success = false;
            if (ret == ERROR_SUCCESS) // could open registry key
            {
                DWORD size = sizeof(dllpath) - 1; // leave space for 0 termination
                memset(dllpath, 0, sizeof(dllpath));
                if (ERROR_SUCCESS == RegQueryValueEx(key, "EventMessageFile", NULL, NULL, dllpath, &size))
                {
                    crash_log("     - record %lu: DLLs to load: %s", *record_number, dllpath);
                    // Answer may contain more than one DLL. They are separated
                    // by semicola. Not knowing which one is the correct one, I have to try
                    // all...
                    char *token = strtok((char *)dllpath, ";");
                    while (token) {
                        if (output_eventlog_entry(out, token, event, type_char, logname, source_name, strings)) {
                            success = true;
                            break;
                        }
                        token = strtok(NULL, ";");
                    }
                }
                RegCloseKey(key);
            }
            else {
                crash_log("     - record %lu: no DLLs listed in registry", *record_number);
            }

            // No text conversion succeeded. Output without text anyway
            if (!success) {
                crash_log("     - record %lu: translation failed", *record_number);
                output_eventlog_entry(out, NULL, event, type_char, logname, source_name, strings);
            }

        } // type_char != '.'

        bytesread -= event->Length;
        crash_log("     - record %lu: event_processed, bytesread %lu, event->Length %lu", *record_number, bytesread, event->Length);
        event = (EVENTLOGRECORD *) ((LPBYTE) event + event->Length);
    }
}


void output_eventlog(SOCKET &out, const char *logname,
        DWORD *record_number, int level, int hide_context)
{
    crash_log(" - event log \"%s\":", logname);

    if (eventlog_buffer_size == 0) {
        const int initial_size = 65536;
        eventlog_buffer = new char[initial_size];
        eventlog_buffer_size = initial_size;
    }

    HANDLE hEventlog = OpenEventLog(NULL, logname);
    DWORD bytesread = 0;
    DWORD bytesneeded = 0;
    if (hEventlog) {
        crash_log("   . successfully opened event log");

        output(out, "[[[%s]]]\n", logname);
        int worst_state = 0;
        DWORD old_record_number = *record_number;

        // we scan all new entries twice. At the first run we check if
        // at least one warning/error message is present. Only if this
        // is the case we make a second run where we output *all* messages,
        // even the informational ones.
        for (int cycle = 0; cycle < 2; cycle++)
        {
            *record_number = old_record_number;
            verbose("Starting from entry number %lu", old_record_number);
            while (true) {
                DWORD flags;
                if (*record_number == 0) {
                    if (cycle == 1) {
                        verbose("Need to reopen Logfile in order to find start again.");
                        CloseEventLog(hEventlog);
                        hEventlog = OpenEventLog(NULL, logname);
                        if (!hEventlog) {
                            verbose("Failed to reopen event log. Bailing out.");
                            return;
                        }
                        crash_log("   . reopened log");
                    }
                    flags = EVENTLOG_SEQUENTIAL_READ | EVENTLOG_FORWARDS_READ;
                }
                else {
                    verbose("Previous record number was %lu. Doing seek read.", *record_number);
                    flags = EVENTLOG_SEEK_READ | EVENTLOG_FORWARDS_READ;
                }

                if (ReadEventLogW(hEventlog,
                            flags,
                            *record_number + 1,
                            eventlog_buffer,
                            eventlog_buffer_size,
                            &bytesread,
                            &bytesneeded))
                {
                    crash_log("   . got entries starting at %lu (%lu bytes)", *record_number + 1, bytesread);


                    process_eventlog_entries(out, logname, eventlog_buffer,
                            bytesread, record_number, cycle == 0, &worst_state, level, hide_context);
                }
                else {
                    DWORD error = GetLastError();
                    if (error == ERROR_INSUFFICIENT_BUFFER) {
                        grow_eventlog_buffer(bytesneeded);
                        crash_log("   . needed to grow buffer to %lu bytes", bytesneeded);
                    }
                    // found current end of log
                    else if (error == ERROR_HANDLE_EOF) {
                        verbose("End of logfile reached at entry %lu. Worst state is %d",
                                *record_number, worst_state);
                        break;
                    }
                    // invalid parameter can also mean end of log
                    else if (error == ERROR_INVALID_PARAMETER) {
                        verbose("Invalid parameter at entry %lu (could mean end of logfile). Worst state is %d",
                                *record_number, worst_state);
                        break;
                    }
                    else {
                        output(out, "ERROR: Cannot read eventlog '%s': error %lu\n", logname, error);
                        break;
                    }
                }
            }
            if (worst_state < level && logwatch_suppress_info) {
                break; // nothing important found. Skip second run
            }
        }
        CloseEventLog(hEventlog);
    }
    else {
        output(out, "[[[%s:missing]]]\n", logname);
    }
}

// Keeps memory of an event log we have found. It
// might already be known and will not be stored twice.
void register_eventlog(char *logname)
{
    // check if we already know this one...
    for (eventlog_state_t::iterator iter  = g_eventlog_state.begin();
                                    iter != g_eventlog_state.end(); ++iter) {
        if (iter->name.compare(logname) == 0) {
            iter->newly_discovered = true;
            return;
        }
    }

    // yet unknown. register it.
    g_eventlog_state.push_back(eventlog_file_state(logname));
}

void unregister_all_eventlogs()
{
    g_eventlog_state.clear();
}

/* Look into the registry in order to find out, which
   event logs are available. */
bool find_eventlogs(SOCKET &out)
{
    for (eventlog_state_t::iterator iter  = g_eventlog_state.begin();
                                    iter != g_eventlog_state.end(); ++iter) {
        iter->newly_discovered = false;
    }

    char regpath[128];
    snprintf(regpath, sizeof(regpath),
            "SYSTEM\\CurrentControlSet\\Services\\Eventlog");
    HKEY key;
    DWORD ret = RegOpenKeyEx(HKEY_LOCAL_MACHINE, regpath, 0, KEY_ENUMERATE_SUB_KEYS, &key);

    bool success = true;
    if (ret == ERROR_SUCCESS)
    {
        DWORD i = 0;
        char buffer[128];
        DWORD len;
        while (true)
        {
            len = sizeof(buffer);
            DWORD r = RegEnumKeyEx(key, i, buffer, &len, NULL, NULL, NULL, NULL);
            if (r == ERROR_SUCCESS)
                register_eventlog(buffer);
            else if (r != ERROR_MORE_DATA)
            {
                if (r != ERROR_NO_MORE_ITEMS) {
                    output(out, "ERROR: Cannot enumerate over event logs: error code %lu\n", r);
                    success = false;
                }
                break;
            }
            i ++;
        }
        RegCloseKey(key);
    }
    else {
        success = false;
        output(out, "ERROR: Cannot open registry key %s for enumeration: error code %lu\n",
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


bool ExtractProcessOwner(HANDLE hProcess_i, string& csOwner_o)
{
    // Get process token
    WinHandle hProcessToken;
    if (!OpenProcessToken(hProcess_i, TOKEN_READ, hProcessToken.ptr()) || !hProcessToken)
        return false;

    // First get size needed, TokenUser indicates we want user information from given token
    DWORD dwProcessTokenInfoAllocSize = 0;
    GetTokenInformation(hProcessToken, TokenUser, NULL, 0, &dwProcessTokenInfoAllocSize);

    // Call should have failed due to zero-length buffer.
    if(GetLastError() == ERROR_INSUFFICIENT_BUFFER)
    {
        // Allocate buffer for user information in the token.
        PTOKEN_USER pUserToken = reinterpret_cast<PTOKEN_USER>(new BYTE[dwProcessTokenInfoAllocSize]);
        if (pUserToken != NULL)
        {
            // Now get user information in the allocated buffer
            if (GetTokenInformation(hProcessToken, TokenUser, pUserToken, dwProcessTokenInfoAllocSize, &dwProcessTokenInfoAllocSize))
            {
                // Some vars that we may need
                SID_NAME_USE  snuSIDNameUse;
                WCHAR         szUser[MAX_PATH]   = { 0 };
                DWORD         dwUserNameLength   = MAX_PATH;
                WCHAR         szDomain[MAX_PATH] = { 0 };
                DWORD         dwDomainNameLength = MAX_PATH;

                // Retrieve user name and domain name based on user's SID.
                if ( LookupAccountSidW( NULL, pUserToken->User.Sid, szUser, &dwUserNameLength,
                            szDomain, &dwDomainNameLength, &snuSIDNameUse))
                {
                    char info[1024];
                    csOwner_o = "\\\\";
                    WideCharToMultiByte(CP_UTF8, 0, (WCHAR*) &szDomain, -1, info, sizeof(info), NULL, NULL);
                    csOwner_o += info;

                    csOwner_o += "\\";
                    WideCharToMultiByte(CP_UTF8, 0, (WCHAR*) &szUser, -1, info, sizeof(info), NULL, NULL);
                    csOwner_o += info;

                    delete [] pUserToken;
                    return true;
                }
            }
            delete [] pUserToken;
        }
    }
    return false;
}

process_entry_t get_process_perfdata()
{
    unsigned int counter_base_number = 230; // process base number

    map< ULONGLONG, process_entry > process_info;
    // registry entry is ascii representation of counter index
    char counter_index_name[8];
    snprintf(counter_index_name, sizeof(counter_index_name), "%u", counter_base_number);

    // allocate block to store counter data block
    DWORD size = DEFAULT_BUFFER_SIZE;
    BYTE *data = new BYTE[DEFAULT_BUFFER_SIZE];
    DWORD type;
    DWORD ret;

    // Holt zu einem bestimmten Counter den kompletten Binärblock aus der
    // Registry. Da man vorher nicht weiß, wie groß der Puffer sein muss,
    // kann man nur mit irgendeiner Größe anfangen und dann diesen immer
    // wieder größer machen, wenn er noch zu klein ist. >:-P
    while ((ret = RegQueryValueEx(HKEY_PERFORMANCE_DATA, counter_index_name,
                    0, &type, data, &size)) != ERROR_SUCCESS)
    {
        if (ret == ERROR_MORE_DATA) // WIN32 API sucks...
        {
            // Der Puffer war zu klein. Toll. Also den Puffer größer machen
            // und das ganze nochmal probieren.
            size += DEFAULT_BUFFER_SIZE;
            delete [] data;
            data = new BYTE [size];
        }
        else {
            // Es ist ein anderer Fehler aufgetreten. Abbrechen.
            delete [] data;
            return process_info;
        }
    }

    PERF_DATA_BLOCK *dataBlockPtr = (PERF_DATA_BLOCK *)data;

    // Determine first object in list of objects
    PERF_OBJECT_TYPE *objectPtr = FirstObject(dataBlockPtr);

    // Now walk through the list of objects. The bad news is:
    // even if we expect only one object, windows might send
    // us more than one object. We need to scan a list of objects
    // in order to find the one we have asked for. >:-P
    for (unsigned int a=0 ; a < dataBlockPtr->NumObjectTypes ; a++)
    {
        // Have we found the object we seek?
        if (objectPtr->ObjectNameTitleIndex == counter_base_number)
        {
            char name[512];
            PERF_INSTANCE_DEFINITION *instancePtr = FirstInstance(objectPtr);
            for(int b=0 ; b<objectPtr->NumInstances ; b++)
            {
                // get pointer to first counter
                PERF_COUNTER_DEFINITION *counterPtr = FirstCounter(objectPtr);

                WCHAR *name_start = (WCHAR *)((char *)(instancePtr) + instancePtr->NameOffset);
                memcpy(name, name_start, instancePtr->NameLength);
                WideCharToMultiByte(CP_UTF8, 0, name_start, instancePtr->NameLength, name, sizeof(name), NULL, NULL);
                // replace spaces with '_'
                for (char *s = name; *s; s++)
                    if (*s == ' ') *s = '_';

                // get PERF_COUNTER_BLOCK of this instance
                PERF_COUNTER_BLOCK *counterBlockPtr = GetCounterBlock(instancePtr);

                process_entry entry;
                memset(&entry, 0, sizeof(entry));
                for (unsigned int bc=0 ; bc < objectPtr->NumCounters ; bc++) {
                    unsigned offset = counterPtr->CounterOffset;
                    BYTE *pData = ((BYTE *)counterBlockPtr) + offset;
                    switch(offset){
                        case 40:
                             entry.virtual_size     = (ULONGLONG)(*(DWORD*)pData);
                             break;
                        case 56:
                             entry.working_set_size = (ULONGLONG)(*(DWORD*)pData);
                             break;
                        case 64:
                             entry.pagefile_usage   = (ULONGLONG)(*(DWORD*)pData);
                             break;
                        case 104:
                             entry.process_id       = (ULONGLONG)(*(DWORD*)pData);
                             break;
                        default:
                             break;
                    }
                    counterPtr = NextCounter(counterPtr);
                }
                process_info[entry.process_id] = entry;
                instancePtr = NextInstance(instancePtr);
            }

        }
        // next object in list
        objectPtr = NextObject(objectPtr);
    }
    delete [] data;
    return process_info;
}


void section_ps_wmi(SOCKET &out)
{
    crash_log("<<<ps>>>");

    wmi::Result result;
    try {
        result = g_wmi_helper->query(L"SELECT * FROM Win32_Process");
        bool more = result.valid();
       if (!more) {
            return;
        }
        output(out, "<<<ps:sep(9)>>>\n");

        while (more) {
            int processId = result.get<int>(L"ProcessId");

            HANDLE process = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, FALSE, processId);
            string user = "SYSTEM";
            ExtractProcessOwner(process, user);
            std::wstring process_name;

            if (g_config->psFullCommandLine() && result.contains(L"ExecutablePath")) {
                process_name = result.get<std::wstring>(L"ExecutablePath");
            } else {
                process_name = result.get<std::wstring>(L"Caption");
            }

            if (g_config->psFullCommandLine() && result.contains(L"CommandLine")) {
                int argc;
                LPWSTR *argv = CommandLineToArgvW(result.get<std::wstring>(L"CommandLine").c_str(), &argc);
                for (int i = 1; i < argc; ++i) {
                    process_name += std::wstring(L" ") + argv[i];
                }
                LocalFree(argv);
            }

            output(out, "(%s,%" PRIu64 ",%" PRIu64 ",%d,%d,%d,%ls,%ls,%u,%d)\t%ls\n",
                    user.c_str(),
                    string_to_llu(result.get<string>(L"VirtualSize").c_str()) / 1024,
                    string_to_llu(result.get<string>(L"WorkingSetSize").c_str()) / 1024,
                    0,
                    processId,
                    result.get<int>(L"PagefileUsage") / 1024,
                    result.get<wstring>(L"UserModeTime").c_str(),
                    result.get<wstring>(L"KernelModeTime").c_str(),
                    result.get<int>(L"HandleCount"),
                    result.get<int>(L"ThreadCount"),
                    process_name.c_str());
            more = result.next();
        }
    } catch (const wmi::ComException &e) {
        // the most likely cause is that the wmi query fails, i.e. because the service is
        // currently offline.
        crash_log("Exception: %s", e.what());
    } catch (const wmi::ComTypeException &e) {
        crash_log("Exception: %s", e.what());
        std::wstring types;
        std::vector<std::wstring> names;
        for (std::vector<std::wstring>::const_iterator iter = names.begin(); iter != names.end(); ++iter) {
            types += *iter + L"=" + std::to_wstring(result.typeId(iter->c_str())) + L", ";
        }
        crash_log("Data types are different than expected, please report this and include "
                  "the following: %ls", types.c_str());
        abort();
    }
}


void section_ps(SOCKET &out)
{
    crash_log("<<<ps>>>");
    output(out, "<<<ps:sep(9)>>>\n");
    PROCESSENTRY32 pe32;

    process_entry_t process_perfdata = get_process_perfdata();

    WinHandle hProcessSnap(CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0));
    if (hProcessSnap != INVALID_HANDLE_VALUE)
    {
        pe32.dwSize = sizeof(PROCESSENTRY32);

        if (Process32First(hProcessSnap, &pe32))
        {
            do
            {
                string user = "unknown";
                DWORD dwAccess = PROCESS_QUERY_INFORMATION | PROCESS_VM_READ;
                WinHandle hProcess(OpenProcess(dwAccess, FALSE, pe32.th32ProcessID));

                if (NULL == hProcess)
                    continue;

                // Process times
                FILETIME createTime, exitTime, kernelTime, userTime;
                ULARGE_INTEGER kernelmodetime, usermodetime;
                if (GetProcessTimes( hProcess, &createTime, &exitTime, &kernelTime, &userTime ) != -1)
                {
                       kernelmodetime.LowPart  = kernelTime.dwLowDateTime;
                       kernelmodetime.HighPart = kernelTime.dwHighDateTime;
                       usermodetime.LowPart    = userTime.dwLowDateTime;
                       usermodetime.HighPart   = userTime.dwHighDateTime;
                }

                DWORD processHandleCount = 0;

                // GetProcessHandleCount is only available winxp upwards
                typedef BOOL WINAPI (*GetProcessHandleCount_type)(HANDLE, PDWORD);
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
                process_entry_t::iterator it_perf = process_perfdata.find(pe32.th32ProcessID);
                if (it_perf != process_perfdata.end()) {
                    working_set_size = it_perf->second.working_set_size;
                    virtual_size     = it_perf->second.virtual_size;
                    pagefile_usage   = it_perf->second.pagefile_usage;
                }

                //// Note: CPU utilization is determined out of usermodetime and kernelmodetime
                output(out, "(%s,%" PRIu64 ",%" PRIu64 ",%d,%lu,%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%lu,%lu)\t%s\n",
                        user.c_str(),
                        virtual_size / 1024,
                        working_set_size / 1024,
                        0, pe32.th32ProcessID,
                        pagefile_usage / 1024,
                        usermodetime.QuadPart,
                        kernelmodetime.QuadPart,
                        processHandleCount, pe32.cntThreads, pe32.szExeFile);
            } while (Process32Next(hProcessSnap, &pe32));
        }
        process_perfdata.clear();

        // The process snapshot doesn't show the system idle process (used to determine the number of cpu cores)
        // We simply fake this entry..
        SYSTEM_INFO sysinfo;
        GetSystemInfo(&sysinfo);
        output(out, "(SYSTEM,0,0,0,0,0,0,0,0,%lu)\tSystem Idle Process\n", sysinfo.dwNumberOfProcessors);
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


void parse_eventlog_state_line(char *line)
{
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
    elh->name      = strdup(path);
    elh->record_no = record_no;
    g_eventlog_hints.push_back(elh);
}


void load_eventlog_offsets(const std::string &statefile)
{
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


void save_logwatch_offsets(const std::string &logwatch_statefile)
{
    FILE *file = fopen(logwatch_statefile.c_str(), "w");
    if (!file) {
        crash_log("Cannot open %s for writing: %s (%d).\n", logwatch_statefile.c_str(), strerror(errno), errno);
        // not stopping the agent from crashing. This way the user at least
        // notices something went wrong.
        // FIXME: unless there aren't any textfiles configured to be monitored
    }
    for (logwatch_textfiles_t::const_iterator it_tf = g_config->logwatchTextfiles().begin();
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

void save_eventlog_offsets(const std::string &eventlog_statefile)
{
    FILE *file = fopen(eventlog_statefile.c_str(), "w");
    for (eventlog_state_t::iterator state_iter  = g_eventlog_state.begin();
                                    state_iter != g_eventlog_state.end(); ++state_iter) {
        int level = 1;
        for (eventlog_config_t::iterator conf_iter = g_config->eventlogConfig().begin();
                conf_iter != g_config->eventlogConfig().end();
                ++conf_iter) {
            if ((conf_iter->name == "*") || ci_equal(conf_iter->name, state_iter->name)) {
                level = conf_iter->level;
                break;
            }
        }
        if (level != -1)
            fprintf(file, "%s|%lu\n", state_iter->name.c_str(), state_iter->num_known_records);
    }
    fclose(file);
}

void update_script_statistics()
{
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
void cleanup_logwatch_textfiles()
{
    for (logwatch_textfiles_t::iterator it_tf = g_config->logwatchTextfiles().begin();
         it_tf != g_config->logwatchTextfiles().end();) {
        if ((*it_tf)->missing) {
            // remove this file from the list
            free((*it_tf)->path);
            it_tf = g_config->logwatchTextfiles().erase(it_tf);
        }
        else
            it_tf++;
    }
}

// Called on program exit
void cleanup_logwatch()
{
    // cleanup textfiles
    for (logwatch_textfiles_t::iterator it_tf = g_config->logwatchTextfiles().begin();
         it_tf != g_config->logwatchTextfiles().end(); it_tf++)
        (*it_tf)->missing = true;
    cleanup_logwatch_textfiles();

    // cleanup globlines and textpatterns
    for (logwatch_globlines_t::iterator it_globline = g_config->logwatchGloblines().begin();
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
// Can be called in dry-run mode (write_output = false). This tries to detect CRIT or WARN patterns
// If write_output is set to true any data found is written to the out socket
#define UNICODE_BUFFER_SIZE 8192
int fill_unicode_bytebuffer(FILE *file, char* buffer, int offset) {
    int bytes_to_read = UNICODE_BUFFER_SIZE - offset;
    int read_bytes = fread(buffer + offset, 1, bytes_to_read, file);
    return read_bytes + offset;
}

int find_crnl_end(char* buffer) {
    int index = 0;
    while (true) {
        if (index >= UNICODE_BUFFER_SIZE)
            return -1;
        if (buffer[index] == 0x0d && index < UNICODE_BUFFER_SIZE - 2 && buffer[index + 2] == 0x0a)
            return index + 4;
        index += 2;
    }
    return -1;
}

struct process_textfile_response{
    bool found_match;
    int  unprocessed_bytes;
};

process_textfile_response process_textfile_unicode(FILE *file, logwatch_textfile* textfile, SOCKET &out, bool write_output)
{
    verbose("Checking UNICODE file %s\n", textfile->path);
    process_textfile_response response;
    char output_buffer[UNICODE_BUFFER_SIZE];
    char unicode_block[UNICODE_BUFFER_SIZE];

    condition_pattern *pattern = 0;
    int  buffer_level          = 0;     // Current bytes in buffer
    bool cut_line              = false; // Line does not fit in buffer
    int  crnl_end_offset;              // Byte index of CRLF in unicode block
    int  old_buffer_level      = 0;

    memset(unicode_block, 0, UNICODE_BUFFER_SIZE);

    while (true) {
        // Only fill buffer if there is no CRNL present
        if (find_crnl_end(unicode_block) == -1) {
            old_buffer_level = buffer_level;
            buffer_level = fill_unicode_bytebuffer(file, unicode_block, buffer_level);

            if (old_buffer_level == buffer_level)
                break; // Nothing new, file finished
        }

        crnl_end_offset = find_crnl_end(unicode_block);
        if (crnl_end_offset == -1)
        {
            if (buffer_level == UNICODE_BUFFER_SIZE )
                // This line is too long, only report up to the buffers size
                cut_line = true;
            else
                // Missing CRNL... this line is not finished yet
                continue;
        }

        // Convert unicode to utf-8
        memset(output_buffer, 0, UNICODE_BUFFER_SIZE);
        WideCharToMultiByte(CP_UTF8, 0, (wchar_t*)unicode_block,
                            cut_line ? (UNICODE_BUFFER_SIZE - 2) / 2 : (crnl_end_offset - 4) / 2,
                            output_buffer, sizeof(output_buffer), NULL, NULL);

        // Check line
        char state = '.';
        for (condition_patterns_t::iterator it_patt = textfile->patterns->begin();
             it_patt != textfile->patterns->end(); it_patt++) {
            pattern = *it_patt;
            if (globmatch(pattern->glob_pattern, output_buffer)){
                if (!write_output && (pattern->state == 'C' || pattern->state == 'W' || pattern->state == 'O'))
                {
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
            output(out, "%c %s\n", state, output_buffer);
        }

        if (cut_line) {
            cut_line = false;
            buffer_level = 2;
            while (crnl_end_offset == -1) {
                memcpy(unicode_block, unicode_block + UNICODE_BUFFER_SIZE - 2, 2);
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
           memmove(unicode_block, unicode_block + crnl_end_offset, buffer_level);
           memset(unicode_block + buffer_level, 0, UNICODE_BUFFER_SIZE - buffer_level);
        }
    }

    response.found_match = false;
    response.unprocessed_bytes = buffer_level;
    return response;
}

process_textfile_response process_textfile(FILE *file, logwatch_textfile* textfile, SOCKET &out, bool write_output)
{
    char line[4096];
    condition_pattern *pattern = 0;
    process_textfile_response response;
    verbose("Checking file %s\n", textfile->path);

    while (!feof(file)) {
        if (!fgets(line, sizeof(line), file))
            break;

        if (line[strlen(line)-1] == '\n')
            line[strlen(line)-1] = 0;

        char state = '.';
        for (condition_patterns_t::iterator it_patt = textfile->patterns->begin();
             it_patt != textfile->patterns->end(); it_patt++) {
            pattern = *it_patt;
            if (globmatch(pattern->glob_pattern, line)){
                if (!write_output && (pattern->state == 'C' || pattern->state == 'W' || pattern->state == 'O'))
                {
                    response.found_match = true;
                    response.unprocessed_bytes = 0;
                    return response;
                }
                state = pattern->state;
                break;
            }
        }

        if (write_output && strlen(line) > 0 && !(textfile->nocontext && (state == 'I' || state == '.')))
            output(out, "%c %s\n", state, line);
    }

    response.found_match = false;
    response.unprocessed_bytes = 0;
    return response;
}


// The output of this section is compatible with
// the logwatch agent for Linux and UNIX
void section_logfiles(SOCKET &out, const Environment &env)
{
    crash_log("<<<logwatch>>>");
    output(out, "<<<logwatch>>>\n");

    g_config->revalidateLogwatchTextfiles();

    logwatch_textfile *textfile;

    // Missing glob patterns
    for (logwatch_globlines_t::iterator it_globline = g_config->logwatchGloblines().begin();
         it_globline != g_config->logwatchGloblines().end(); ++it_globline) {
        globline_container *cont = *it_globline;
        for (glob_tokens_t::iterator it_token = cont->tokens.begin();
             it_token != cont->tokens.end(); it_token++) {
            if (!((*it_token)->found_match))
                output(out, "[[[%s:missing]]]\n", (*it_token)->pattern);
        }
    }
    for (logwatch_textfiles_t::iterator it_tf = g_config->logwatchTextfiles().begin();
         it_tf != g_config->logwatchTextfiles().end(); ++it_tf) {
        textfile = *it_tf;
        if (textfile->missing){
            output(out, "[[[%s:missing]]]\n", textfile->path);
            continue;
        }

        // Determine Encoding
        if (textfile->encoding == UNDEF || textfile->offset == 0) {
            FILE *file = fopen(textfile->path, "rb");
            if (!file) {
                output(out, "[[[%s:cannotopen]]]\n", textfile->path);
                continue;
            }

            char bytes[2];
            int read_bytes = fread(bytes, 1, sizeof(bytes), file);
            if (read_bytes == sizeof(bytes) && (unsigned char)bytes[0] == 0xFF && (unsigned char)bytes[1] == 0xFE)
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
            output(out, "[[[%s:cannotopen]]]\n", textfile->path);
            continue;
        }

        output(out, "[[[%s]]]\n", textfile->path);

        if (textfile->offset == textfile->file_size) { // no new data
            fclose(file);
            continue;
        }

        fseek(file, (textfile->encoding == UNICODE && textfile->offset == 0) ? 2 : textfile->offset, SEEK_SET);
        process_textfile_response response;
        if (textfile->encoding == UNICODE)
            response = process_textfile_unicode(file, textfile, out, false);
        else
            response = process_textfile(file, textfile, out, false);

        if (response.found_match) {
            fseek(file, (textfile->encoding == UNICODE && textfile->offset == 0) ? 2 : textfile->offset, SEEK_SET);
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


// The output of this section is compatible with
// the logwatch agent for Linux and UNIX
void section_eventlog(SOCKET &out, const Environment &env)
{
    crash_log("<<<logwatch>>>");

    // This agent remembers the record numbers
    // of the event logs up to which messages have
    // been processed. When started, the eventlog
    // is skipped to the end. Historic messages are
    // not been processed.
    static bool first_run = true;
    output(out, "<<<logwatch>>>\n");

    if (find_eventlogs(out))
    {
        // Special handling on startup (first_run)
        // The last processed record number of each eventlog is stored in the file eventstate.txt
        // If there is no entry for the given eventlog we start at the end
        if (first_run && !g_config->logwatchSendInitialEntries()) {
            for (eventlog_state_t::iterator it_st  = g_eventlog_state.begin();
                                            it_st != g_eventlog_state.end(); ++it_st) {
                bool found_hint = false;
                for (eventlog_hints_t::iterator it_el  = g_eventlog_hints.begin();
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
                    if (hEventlog) {
                        DWORD no_records;
                        DWORD oldest_record;
                        GetNumberOfEventLogRecords(hEventlog, &no_records);
                        GetOldestEventLogRecord(hEventlog, &oldest_record);
                        if (no_records > 0)
                            it_st->num_known_records = oldest_record + no_records - 1;
                    }
                }
            }
        }

        for (eventlog_state_t::iterator it_st  = g_eventlog_state.begin();
                                        it_st != g_eventlog_state.end(); ++it_st) {
            if (!it_st->newly_discovered) // not here any more!
                output(out, "[[[%s:missing]]]\n", it_st->name.c_str());
            else {
                // Get the configuration of that log file (which messages to send)
                int level = 1;
                int hide_context = 0;
                for (eventlog_config_t::iterator conf_iter  = g_config->eventlogConfig().begin();
                                                 conf_iter != g_config->eventlogConfig().end(); ++conf_iter) {
                    if ((conf_iter->name == "*") || ci_equal(conf_iter->name, it_st->name)) {
                        level = conf_iter->level;
                        hide_context = conf_iter->hide_context;
                        break;
                    }
                }
                if (level != -1) {
                    output_eventlog(out, it_st->name.c_str(), &it_st->num_known_records, level, hide_context);
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

void section_mem(SOCKET &out)
{
    crash_log("<<<mem>>>");
    output(out, "<<<mem>>>\n");

    MEMORYSTATUSEX statex;
    statex.dwLength = sizeof (statex);
    GlobalMemoryStatusEx (&statex);

    output(out, "MemTotal:     %" PRIu64 " kB\n", statex.ullTotalPhys     / 1024);
    output(out, "MemFree:      %" PRIu64 " kB\n", statex.ullAvailPhys     / 1024);
    output(out, "SwapTotal:    %" PRIu64 " kB\n", (statex.ullTotalPageFile - statex.ullTotalPhys) / 1024);
    output(out, "SwapFree:     %" PRIu64 " kB\n", (statex.ullAvailPageFile - statex.ullAvailPhys) / 1024);
    output(out, "PageTotal:    %" PRIu64 " kB\n", statex.ullTotalPageFile / 1024);
    output(out, "PageFree:     %" PRIu64 " kB\n", statex.ullAvailPageFile / 1024);
    output(out, "VirtualTotal: %" PRIu64 " kB\n", statex.ullTotalVirtual / 1024);
    output(out, "VirtualFree:  %" PRIu64 " kB\n", statex.ullAvailVirtual / 1024);
}

// .-----------------------------------------------------------------------.
// |              ______ __ _ _      _        __     ______                |
// |             / / / // _(_) | ___(_)_ __  / _| ___\ \ \ \               |
// |            / / / /| |_| | |/ _ \ | '_ \| |_ / _ \\ \ \ \              |
// |            \ \ \ \|  _| | |  __/ | | | |  _| (_) / / / /              |
// |             \_\_\_\_| |_|_|\___|_|_| |_|_|  \___/_/_/_/               |
// |                                                                       |
// '-----------------------------------------------------------------------'

void output_fileinfos(SOCKET &out, const char *path);
bool output_fileinfo(SOCKET &out, const char *basename, WIN32_FIND_DATA *data);

void section_fileinfo(SOCKET &out)
{
    crash_log("<<<fileinfo>>>");
    output(out, "<<<fileinfo:sep(124)>>>\n");
    output(out, "%.0f\n", current_time());
    for (fileinfo_paths_t::iterator it_path = g_config->fileinfoPaths().begin();
            it_path != g_config->fileinfoPaths().end(); it_path++) {
        output_fileinfos(out, *it_path);
    }
}

void output_fileinfos(SOCKET &out, const char *path)
{
    WIN32_FIND_DATA data;
    HANDLE h = FindFirstFileEx(path, FindExInfoStandard, &data, FindExSearchNameMatch, NULL, 0);
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
        if (end)
            *end = '\\'; // repair string
        FindClose(h);

        if (!found_file)
            output(out, "%s|missing|%f\n", path, current_time());
    }
    else {
        DWORD e = GetLastError();
        output(out, "%s|missing|%lu\n", path, e);
    }
}


bool output_fileinfo(SOCKET &out, const char *basename, WIN32_FIND_DATA *data)
{
    unsigned long long size = (unsigned long long)data->nFileSizeLow
        + (((unsigned long long)data->nFileSizeHigh) << 32);

    if (0 == (data->dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)) {
        output(out, "%s\\%s|%" PRIu64 "|%.0f\n", basename,
                data->cFileName, size, file_time(&data->ftLastWriteTime));
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

int get_script_timeout(char *name, script_type type)
{
    timeout_configs_t &configs = g_config->timeoutConfigs(type);
    for (timeout_configs_t::iterator it = configs.begin(); it != configs.end(); ++it)
        if (globmatch((*it)->pattern, name))
            return (*it)->timeout;
    return type == PLUGIN ? DEFAULT_PLUGIN_TIMEOUT : DEFAULT_LOCAL_TIMEOUT;
}

int get_script_cache_age(char *name, script_type type)
{
    cache_configs_t &configs = g_config->cacheConfigs(type);
    for (cache_configs_t::iterator it = configs.begin(); it != configs.end(); ++it)
        if (globmatch((*it)->pattern, name))
            return (*it)->max_age;
    return 0;
}

int get_script_max_retries(char *name, script_type type)
{
    retry_count_configs_t &configs = g_config->retryConfigs(type);
    for (retry_count_configs_t::iterator it = configs.begin(); it != configs.end(); ++it)
        if (globmatch((*it)->pattern, name))
            return (*it)->retries;
    return 0;
}

script_execution_mode get_script_execution_mode(char *name, script_type type)
{
    execution_mode_configs_t &configs = g_config->executionModeConfigs(type);
    for (execution_mode_configs_t::iterator it = configs.begin(); it != configs.end(); ++it)
        if (globmatch((*it)->pattern, name))
            return (*it)->mode;
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

char *add_interpreter(char *path, char *newpath)
{
    if (!strcmp(path + strlen(path) - 4, ".vbs")) {
        // If this is a vbscript don't rely on the default handler for this
        // file extensions. This might be notepad or some other editor by
        // default on a lot of systems. So better add cscript as interpreter.
        snprintf(newpath, 256, "cscript.exe //Nologo \"%s\"", path);
        return newpath;
    }
    else if (!strcmp(path + strlen(path) - 4, ".ps1")) {
        // Same for the powershell scripts. Add the powershell interpreter.
        // To make this work properly two things are needed:
        //   1.) The powershell interpreter needs to be in PATH
        //   2.) The execution policy needs to allow the script execution
        //       -> Get-ExecutionPolicy / Set-ExecutionPolicy
        //
        // actually, microsoft always installs the powershell interpreter to the same
        // directory (independent of the version) so even if it's not in the path,
        // we have a good chance with this fallback.
        char dummy;
        ::SearchPathA(NULL, "powershell.exe", NULL, 1, &dummy, NULL);
        const char *interpreter = ::GetLastError() != ERROR_FILE_NOT_FOUND
            ? "powershell.exe"
            : "C:\\Windows\\System32\\WindowsPowershell\\v1.0\\powershell.exe";
        snprintf(newpath, 256, "%s -NoLogo -ExecutionPolicy RemoteSigned \"& \'%s\'\"", interpreter, path);
        return newpath;
    }
    else if (!strcmp(path + strlen(path) - 3, ".pl")) {
        // Perl scripts get perl.exe as interpreter
        snprintf(newpath, 256, "perl.exe \"%s\"", path);
        return newpath;
    }
    else if (!strcmp(path + strlen(path) - 3, ".py")) {
        // Python scripts get python interpreter
        snprintf(newpath, 256, "python.exe \"%s\"", path);
        return newpath;
    }
    else {
        snprintf(newpath, 256, "\"%s\"", path);
        return newpath;
    }
}

bool banned_exec_name(char *name)
{
    if (strlen(name) < 5)
        return false;

    const char *extension = strrchr(name, '.');
    if (extension == NULL) {
        // ban files without extension
        return true;
    }

    if (g_config->executeSuffixes().size()) {
        ++extension;
        for (execute_suffixes_t::const_iterator it_ex = g_config->executeSuffixes().begin();
                it_ex != g_config->executeSuffixes().end(); ++it_ex)
            if (!strcasecmp(extension, it_ex->c_str()))
                return false;
        return true;
    }
    else {
        return  ( !strcasecmp(extension, ".dir")
                || !strcasecmp(extension, ".txt"));
    }
}

bool IsWinNT()  // check if we're running NT
{
    OSVERSIONINFO osv;
    osv.dwOSVersionInfoSize = sizeof(osv);
    GetVersionEx(&osv);
    return (osv.dwPlatformId == VER_PLATFORM_WIN32_NT);
}


int launch_program(script_container* cont)
{
    int exit_code  = 0;
    int out_offset = 0;

    STARTUPINFO si;
    SECURITY_ATTRIBUTES sa;
    SECURITY_DESCRIPTOR sd;   // security information for pipes

    PROCESS_INFORMATION pi;
    WinHandle script_stdout, read_stdout;  // pipe handles
    WinHandle script_stderr,read_stderr;

    // initialize security descriptor (Windows NT)
    if (IsWinNT())
    {
        InitializeSecurityDescriptor(&sd,SECURITY_DESCRIPTOR_REVISION);
        SetSecurityDescriptorDacl(&sd, true, NULL, false);
        sa.lpSecurityDescriptor = &sd;
    }
    else
        sa.lpSecurityDescriptor = NULL;

    sa.nLength = sizeof(SECURITY_ATTRIBUTES);
    sa.bInheritHandle = true;                       // allow inheritable handles

    if (!CreatePipe(read_stdout.ptr(),script_stdout.ptr(),&sa,0)) // create stdout pipe
        return 1;

    if (!CreatePipe(read_stderr.ptr(),script_stderr.ptr(),&sa,0)) // create stderr pipe
        return 1;

    //set startupinfo for the spawned process
    GetStartupInfo(&si);
    si.dwFlags = STARTF_USESTDHANDLES|STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;
    si.hStdOutput = script_stdout;

    if (with_stderr)
        si.hStdError = script_stdout;
    else
        si.hStdError = script_stderr;

    // spawn the child process
    if (!CreateProcess(NULL,cont->path,NULL,NULL,TRUE,CREATE_NEW_CONSOLE,
                NULL,NULL,&si,&pi)) {
        crash_log("failed to spawn process %s: %s", cont->path, get_win_error_as_string().c_str());
        return 1;
    }

    // Create a job object for this process
    // Whenever the process ends all of its childs will terminate, too
    cont->job_object = CreateJobObject(NULL, NULL);
    AssignProcessToJobObject(cont->job_object, pi.hProcess);
    AssignProcessToJobObject(g_workers_job_object, pi.hProcess);

    unsigned long bread;   // bytes read
    unsigned long avail;   // bytes available

    static const size_t BUFFER_SIZE = 16635;
    char buf[BUFFER_SIZE];           // i/o buffer
    memset(buf, 0, BUFFER_SIZE);
    time_t process_start = time(0);
    bool buffer_full = false;

    cont->buffer_work = (char*) HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, HEAP_BUFFER_DEFAULT);
    unsigned long current_heap_size = HeapSize(GetProcessHeap(), 0, cont->buffer_work);

    for(;;)
    {
        if (cont->should_terminate || time(0) - process_start > cont->timeout){
            exit_code = 2;
            break;
        }

        GetExitCodeProcess(pi.hProcess, &cont->exit_code);      // while the process is running
        while (!buffer_full) {
            if (!with_stderr) {
                PeekNamedPipe(read_stderr, buf, BUFFER_SIZE, &bread, &avail, NULL);
                if (avail > 0)
                    // Just read from the pipe, we do not use this data
                    ReadFile(read_stderr, buf, BUFFER_SIZE - 1, &bread, NULL);
            }

            PeekNamedPipe(read_stdout, buf, BUFFER_SIZE, &bread, &avail, NULL);

            if (avail == 0)
                break;

            while (out_offset + bread > current_heap_size) {
                // Increase heap buffer
                if (current_heap_size * 2 <= HEAP_BUFFER_MAX) {
                    cont->buffer_work = (char *) HeapReAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY,
                                                             cont->buffer_work, current_heap_size * 2);
                    current_heap_size = HeapSize(GetProcessHeap(), 0, cont->buffer_work);
                }
                else {
                    buffer_full = true;
                    break;
                }
            }
            if (buffer_full)
                break;

            if (bread > 0) {
                ReadFile(read_stdout, cont->buffer_work + out_offset,
                         std::min<size_t>(BUFFER_SIZE - 1, current_heap_size - out_offset), &bread, NULL);
                out_offset += bread;
            }
        }
        if (buffer_full) {
            crash_log("plugin produced more than 2MB output -> dropped");
            // Buffer full -> delete incomplete data
            exit_code = 1;
            break;
        }

        if (cont->exit_code != STILL_ACTIVE)
            break;

        Sleep(10);
    }
    TerminateJobObject(cont->job_object, exit_code);

    // cleanup the mess
    CloseHandle(cont->job_object);
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);

    return exit_code;
}

DWORD WINAPI ScriptWorkerThread(LPVOID lpParam)
{
    script_container* cont = (script_container*) lpParam;

    // Execute script
    int result = launch_program(cont);

    // Set finished status
    switch (result) {
        case 0:
            cont->status       = SCRIPT_FINISHED;
            cont->last_problem = SCRIPT_NONE;
            cont->retry_count  = cont->max_retries;
            cont->buffer_time  = time(0);
            break;
        case 1:
            cont->status       = SCRIPT_ERROR;
            cont->last_problem = SCRIPT_ERROR;
            cont->retry_count--;
            break;
        case 2:
            cont->status       = SCRIPT_TIMEOUT;
            cont->last_problem = SCRIPT_TIMEOUT;
            cont->retry_count--;
            break;
        default:
            cont->status       = SCRIPT_ERROR;
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

bool script_exists(script_container *cont)
{
    DWORD dwAttr = GetFileAttributes(cont->script_path);
    return !(dwAttr == INVALID_FILE_ATTRIBUTES);
}

void run_script_container(script_container *cont)
{
    if ( (cont->type == PLUGIN && !(g_config->sectionEnabled(SECTION_PLUGINS))) ||
         (cont->type == LOCAL  && !(g_config->sectionEnabled(SECTION_LOCAL))) )
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
        cont->worker_thread  = CreateThread(
                NULL,                 // default security attributes
                0,                    // use default stack size
                ScriptWorkerThread,   // thread function name
                cont,                 // argument to thread function
                0,                    // use default creation flags
                NULL);                // returns the thread identifier

        if (cont->execution_mode == SYNC ||
            (cont->execution_mode == ASYNC && g_config->defaultScriptAsyncExecution() == SEQUENTIAL))
            WaitForSingleObject(cont->worker_thread, INFINITE);

        crash_log("finished with status %d (exit code %" PRIudword ")", cont->status, cont->exit_code);
    }
}

void output_external_programs(SOCKET &out, script_type type)
{
    // Collect and output data
    script_containers_t::iterator it_cont = script_containers.begin();
    script_container* cont = NULL;
    while (it_cont != script_containers.end())
    {
        cont = it_cont->second;
        if (!script_exists(cont)) {
            crash_log("script %s missing", cont->script_path);
            it_cont++;
            continue;
        }

        if (cont->type == type)
        {
            if (cont->status == SCRIPT_FINISHED)
            {
                // Free buffer
                if (cont->buffer != NULL) {
                    HeapFree(GetProcessHeap(), 0, cont->buffer);
                    cont->buffer = NULL;
                }

                // Replace BOM for UTF-16 LE and UTF-8 with newlines
                if ( (strlen(cont->buffer_work)) >= 2 &&
                   ((unsigned char)cont->buffer_work[0] == 0xFF && (unsigned char)cont->buffer_work[1] == 0xFE) )
                {
                    cont->buffer_work[0] = '\n';
                    cont->buffer_work[1] = '\n';
                }
                else if ( strlen(cont->buffer_work) >= 3 &&
                   (unsigned char)cont->buffer_work[0] == 0xEF &&
                   (unsigned char)cont->buffer_work[1] == 0xBB &&
                   (unsigned char)cont->buffer_work[2] == 0xBF )
                {
                    cont->buffer_work[0] = '\n';
                    cont->buffer_work[1] = '\n';
                    cont->buffer_work[2] = '\n';
                }

                if (cont->max_age == 0) {
                    cont->buffer      = cont->buffer_work;
                }
                else {
                    // Determine chache_info text
                    char cache_info[32];
                    snprintf(cache_info, sizeof(cache_info), ":cached(%d,%d)", (int)cont->buffer_time, cont->max_age);
                    int cache_len = strlen(cache_info) + 1;

                    // We need to parse each line and replace any <<<section>>> with <<<section:cached(123455678,3600)>>>
                    // Allocate new buffer, process/modify each line of the original buffer and write it into the new buffer
                    // We increase this new buffer by a good amount, because there might be several hundred
                    // sections (e.g. veeam_backup status piggyback) within this plugin output.
                    // TODO: Maybe add a dry run mode. Count the number of section lines and reserve a fitting extra heap
                    int buffer_heap_size = HeapSize(GetProcessHeap(), 0, cont->buffer_work);
                    char *cache_buffer = (char*) HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, buffer_heap_size + 262144);
                    int cache_buffer_offset = 0;

                    char *line = strtok(cont->buffer_work, "\n");
                    int write_bytes = 0;
                    while (line)
                    {
                        int length = strlen(line);
                        int cr_offset = line[length-1] == '\r' ? 1 : 0;
                        if (length >=8 && strncmp(line, "<<<<", 4) && (!strncmp(line, "<<<", 3) &&
                            !strncmp(line+length-cr_offset-3, ">>>", 3)))
                        {
                            // The return value of snprintf seems broken (off by 3?). Great...
                            write_bytes = length - cr_offset - 3 + 1; // length - \r - <<< + \0
                            snprintf(cache_buffer + cache_buffer_offset, write_bytes, "%s", line);
                            cache_buffer_offset += write_bytes - 1;

                            snprintf(cache_buffer + cache_buffer_offset, cache_len, "%s", cache_info);
                            cache_buffer_offset += cache_len - 1;

                            write_bytes = 3 + cr_offset + 1 + 1; // >>> + \r + \n + \0
                            snprintf(cache_buffer + cache_buffer_offset, write_bytes, "%s\n", line + length - cr_offset - 3);
                            cache_buffer_offset += write_bytes - 1;
                        }
                        else
                        {
                            write_bytes = length + 1 + 1; // length + \n + \0
                            snprintf(cache_buffer + cache_buffer_offset, write_bytes, "%s\n", line);
                            cache_buffer_offset += write_bytes - 1;
                        }
                        line = strtok(NULL, "\n");
                    }
                    HeapFree(GetProcessHeap(), 0, cont->buffer_work);
                    cont->buffer = cache_buffer;
                }

                cont->buffer_work = NULL;
                cont->status      = SCRIPT_IDLE;
            }
            else if (cont->retry_count < 0 && cont->buffer != NULL)
            {
                // Remove outdated cache entries
                HeapFree(GetProcessHeap(), 0, cont->buffer);
                cont->buffer = NULL;
            }
            if (cont->buffer)
                output(out, "%s", cont->buffer);
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

void update_mrpe_includes()
{
    for (unsigned int i = 0 ; i < g_included_mrpe_entries.size(); i++)
        delete g_included_mrpe_entries[i];
    g_included_mrpe_entries.clear();

    FILE *file;
    char  line[512];
    int   lineno = 0;
    for (mrpe_include_t::iterator it_include = g_config->mrpeIncludes().begin();
         it_include != g_config->mrpeIncludes().end(); it_include++)
    {
        char* path = (*it_include)->path;
        file = fopen(path, "r");
        if (!file) {
            crash_log("Include file not found %s", path);
            continue;
        }

        lineno = 0;
        while (!feof(file)) {
            lineno++;
            if (!fgets(line, sizeof(line), file)){
                printf("intern clse\n");
                fclose(file);
                continue;
            }

            char *l = strip(line);
            if (l[0] == 0 || l[0] == '#' || l[0] == ';')
                continue; // skip empty lines and comments

            // split up line at = sign
            char *s = l;
            while (*s && *s != '=')
                s++;
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
                    crash_log("Invalid line %d in %s. Invalid command specification", lineno, path);
                    continue;
                }

                mrpe_entry* tmp_entry = new mrpe_entry();
                memset(tmp_entry, 0, sizeof(mrpe_entry));

                strncpy(tmp_entry->command_line, command_line,
                        sizeof(tmp_entry->command_line));
                strncpy(tmp_entry->service_description, service_description,
                        sizeof(tmp_entry->service_description));

                // compute plugin name, drop directory part
                char *plugin_name = next_word(&value);
                char *p = strrchr(plugin_name, '/');
                if (!p)
                    p = strrchr(plugin_name, '\\');
                if (p)
                    plugin_name = p + 1;
                strncpy(tmp_entry->plugin_name, plugin_name, sizeof(tmp_entry->plugin_name));
                strncpy(tmp_entry->run_as_user, (*it_include)->user, sizeof(tmp_entry->run_as_user));
                g_included_mrpe_entries.push_back(tmp_entry);
            }
        }
        fclose(file);
    }
}

void section_mrpe(SOCKET &out)
{
    crash_log("<<<mrpe>>>");
    output(out, "<<<mrpe>>>\n");

    update_mrpe_includes();

    mrpe_entries_t all_mrpe_entries;
    all_mrpe_entries.insert(all_mrpe_entries.end(),
                            g_config->mrpeEntries().begin(), g_config->mrpeEntries().end());
    all_mrpe_entries.insert(all_mrpe_entries.end(),
                            g_included_mrpe_entries.begin(), g_included_mrpe_entries.end());

    for (mrpe_entries_t::iterator it_mrpe = all_mrpe_entries.begin();
            it_mrpe != all_mrpe_entries.end(); it_mrpe++)
    {
        mrpe_entry *entry = *it_mrpe;
        output(out, "(%s) %s ", entry->plugin_name, entry->service_description);
        crash_log("%s (%s) %s ", entry->run_as_user, entry->plugin_name, entry->service_description);

        char command[1024];
        char run_as_prefix[512];
        memset(run_as_prefix, 0, sizeof(run_as_prefix));
        if (strlen(entry->run_as_user) > 0)
            snprintf(run_as_prefix, sizeof(run_as_prefix), "runas /User:%s ", entry->run_as_user);
        snprintf(command, sizeof(command), "%s%s", run_as_prefix, entry->command_line);
        FILE *f = _popen(entry->command_line, "r");
        if (!f) {
            output(out, "3 Unable to execute - plugin may be missing.\n");
            continue;
        }

        crash_log("Script started -> collecting data");
        if (f) {
            char buffer[8192];
            int bytes = fread(buffer, 1, sizeof(buffer) - 1, f);
            buffer[bytes] = 0;
            rstrip(buffer);
            char *plugin_output = lstrip(buffer);
            // Replace \n with Ascii 1 and \r with spaces
            for (char *x = plugin_output; *x; x++) {
                if (*x == '\n')
                    *x = (char)1;
                else if (*x == '\r')
                    *x = ' ';
            }
            int status = _pclose(f);
            int nagios_code = status;
            output(out, "%d %s\n", nagios_code, plugin_output);
        }
        crash_log("Script finished");
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

void section_local(SOCKET &out)
{
    crash_log("<<<local>>>");
    output(out, "<<<local>>>\n");
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

void section_plugins(SOCKET &out)
{
    // Prevent errors from plugins with missing section
    output(out, "<<<>>>\n");
    output_external_programs(out, PLUGIN);
    // Prevent errors from plugins with missing final newline
    output(out, "\n<<<>>>\n");
}


// .-----------------------------------------------------------------------.
// |                      ____                    _                        |
// |                     / ___| _ __   ___   ___ | |                       |
// |                     \___ \| '_ \ / _ \ / _ \| |                       |
// |                      ___) | |_) | (_) | (_) | |                       |
// |                     |____/| .__/ \___/ \___/|_|                       |
// |                           |_|                                         |
// '-----------------------------------------------------------------------'
void section_spool(SOCKET &out, const Environment &env)
{
    crash_log("<<<spool>>>");
    // Look for files in the spool directory and append these files to
    // the agent output. The name of the files may begin with a number
    // of digits. If this is the case then it is interpreted as a time
    // in seconds: the maximum allowed age of the file. Outdated files
    // are simply being ignored.
    DIR  *dir = opendir(env.spoolDirectory().c_str());
    if (dir) {
        WIN32_FIND_DATA filedata;
        char path[512];
        char buffer[4096];
        time_t now = time(0);

        struct dirent *de;
        while (0 != (de = readdir(dir))) {
            char *name = de->d_name;
            if (name[0] == '.')
                continue;

            snprintf(path, sizeof(path), "%s\\%s", env.spoolDirectory().c_str(), name);
            int max_age = -1;
            if (isdigit(*name))
                max_age = atoi(name);

            if (max_age >= 0) {
                HANDLE h = FindFirstFileEx(path, FindExInfoStandard, &filedata, FindExSearchNameMatch, NULL, 0);
                if (h != INVALID_HANDLE_VALUE) {
                    double mtime = file_time(&(filedata.ftLastWriteTime));
                    FindClose(h);
                    int age = now - mtime;
                    if (age > max_age) {
                        crash_log("    %s: skipping outdated file: age is %d sec, max age is %d sec.",
                            name, age, max_age);
                        continue;
                    }
                }
                else {
                    crash_log("    %s: cannot determine file age", name);
                    continue;
                }
            }
            crash_log("    %s", name);

            // Output file in blocks of 4kb
            FILE *file = fopen(path, "r");
            if (file) {
                int bytes_read;
                while (0 < (bytes_read = fread(buffer, 1, sizeof(buffer)-1, file))) {
                    buffer[bytes_read] = 0;
                    output(out, "%s", buffer);
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

void section_check_mk(SOCKET &out, const Environment &env)
{
    crash_log("<<<check_mk>>>");
    output(out, "<<<check_mk>>>\n");

    output(out, "Version: %s\n", check_mk_version);
    output(out, "BuildDate: %s\n", __DATE__);
#ifdef ENVIRONMENT32
    output(out, "Architecture: 32bit\n");
#else
    output(out, "Architecture: 64bit\n");
#endif
    output(out, "AgentOS: windows\n");
    output(out, "Hostname: %s\n",         env.hostname().c_str());
    output(out, "WorkingDirectory: %s\n", env.currentDirectory().c_str());
    output(out, "ConfigFile: %s\n",       g_config->configFileName(false).c_str());
    output(out, "LocalConfigFile: %s\n",  g_config->configFileName(true).c_str());
    output(out, "AgentDirectory: %s\n",   env.agentDirectory().c_str());
    output(out, "PluginsDirectory: %s\n", env.pluginsDirectory().c_str());
    output(out, "StateDirectory: %s\n",   env.stateDirectory().c_str());
    output(out, "ConfigDirectory: %s\n",  env.configDirectory().c_str());
    output(out, "TempDirectory: %s\n",    env.tempDirectory().c_str());
    output(out, "LogDirectory: %s\n",     env.logDirectory().c_str());
    output(out, "SpoolDirectory: %s\n",   env.spoolDirectory().c_str());
    output(out, "LocalDirectory: %s\n",   env.localDirectory().c_str());
    output(out, "ScriptStatistics: Plugin C:%d E:%d T:%d "
            "Local C:%d E:%d T:%d\n",
            g_script_stat.pl_count, g_script_stat.pl_errors, g_script_stat.pl_timeouts,
            g_script_stat.lo_count, g_script_stat.lo_errors, g_script_stat.lo_timeouts);
    if (g_config->crashDebug()) {
        output(out, "ConnectionLog: %s\n", g_connection_log);
        output(out, "CrashLog: %s\n",      g_crash_log);
        output(out, "SuccessLog: %s\n",    g_success_log);
    }

    output(out, "OnlyFrom:");
    if (g_config->onlyFrom().size() == 0)
        output(out, " 0.0.0.0/0\n");
    else {
        for ( only_from_t::const_iterator it_from = g_config->onlyFrom().begin();
                it_from != g_config->onlyFrom().end(); ++it_from ) {
            ipspec *is = *it_from;
            if (is->ipv6) {
                output(out, " %x:%x:%x:%x:%x:%x:%x:%x/%d",
                        is->ip.v6.address[0], is->ip.v6.address[1],
                        is->ip.v6.address[2], is->ip.v6.address[3],
                        is->ip.v6.address[4], is->ip.v6.address[5],
                        is->ip.v6.address[6], is->ip.v6.address[7],
                        is->bits);
            } else {
                output(out, " %d.%d.%d.%d/%d",
                        is->ip.v4.address & 0xff,
                        is->ip.v4.address >> 8 & 0xff,
                        is->ip.v4.address >> 16 & 0xff,
                        is->ip.v4.address >> 24 & 0xff,
                        is->bits);
            }
        }
        output(out, "\n");
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

TCHAR*                gszServiceName = (TCHAR *)TEXT(SERVICE_NAME);
SERVICE_STATUS        serviceStatus;
SERVICE_STATUS_HANDLE serviceStatusHandle = 0;


void WINAPI ServiceControlHandler( DWORD controlCode )
{
    switch ( controlCode )
    {
        case SERVICE_CONTROL_INTERROGATE:
            break;

        case SERVICE_CONTROL_SHUTDOWN:
        case SERVICE_CONTROL_STOP:
            g_should_terminate = true;
            serviceStatus.dwCurrentState = SERVICE_STOP_PENDING;
            SetServiceStatus( serviceStatusHandle, &serviceStatus );
            return;

        case SERVICE_CONTROL_PAUSE:
            break;

        case SERVICE_CONTROL_CONTINUE:
            break;

        default:
            if ( controlCode >= 128 && controlCode <= 255 )
                // user defined control code
                break;
            else
                // unrecognised control code
                break;
    }

    SetServiceStatus( serviceStatusHandle, &serviceStatus );
}


void WINAPI ServiceMain(DWORD, TCHAR* [] )
{
    // initialise service status
    serviceStatus.dwServiceType             = SERVICE_WIN32_OWN_PROCESS;
    serviceStatus.dwCurrentState            = SERVICE_STOPPED;
    serviceStatus.dwControlsAccepted        = 0;
    serviceStatus.dwWin32ExitCode           = NO_ERROR;
    serviceStatus.dwServiceSpecificExitCode = NO_ERROR;
    serviceStatus.dwCheckPoint              = 0;
    serviceStatus.dwWaitHint                = 0;

    serviceStatusHandle = RegisterServiceCtrlHandler( gszServiceName,
            ServiceControlHandler );

    if ( serviceStatusHandle )
    {
        // service is starting
        serviceStatus.dwCurrentState = SERVICE_START_PENDING;
        SetServiceStatus( serviceStatusHandle, &serviceStatus );

        // Service running
        serviceStatus.dwControlsAccepted |= (SERVICE_ACCEPT_STOP |
                SERVICE_ACCEPT_SHUTDOWN);
        serviceStatus.dwCurrentState = SERVICE_RUNNING;
        SetServiceStatus( serviceStatusHandle, &serviceStatus );

        RunImmediate("service", 0, NULL);

        // service is now stopped
        serviceStatus.dwControlsAccepted &= ~(SERVICE_ACCEPT_STOP |
                SERVICE_ACCEPT_SHUTDOWN);
        serviceStatus.dwCurrentState = SERVICE_STOPPED;
        SetServiceStatus( serviceStatusHandle, &serviceStatus );
    }
}

void RunService()
{
    SERVICE_TABLE_ENTRY serviceTable[] =
    {
        { gszServiceName, ServiceMain },
        { 0, 0 }
    };

    StartServiceCtrlDispatcher( serviceTable );
}

void InstallService()
{
    SC_HANDLE serviceControlManager = OpenSCManager( 0, 0,
            SC_MANAGER_CREATE_SERVICE );

    if ( serviceControlManager )
    {
        char path[ _MAX_PATH + 1 ];
        if ( GetModuleFileName( 0, path, sizeof(path)/sizeof(path[0]) ) > 0 )
        {
            char quoted_path[1024];
            snprintf(quoted_path, sizeof(quoted_path), "\"%s\"", path);
            SC_HANDLE service = CreateService( serviceControlManager,
                    gszServiceName, gszServiceName,
                    SERVICE_ALL_ACCESS, SERVICE_WIN32_OWN_PROCESS,
                    SERVICE_AUTO_START, SERVICE_ERROR_IGNORE, quoted_path,
                    0, 0, 0, 0, 0 );
            if ( service )
            {
                CloseServiceHandle( service );
                printf(SERVICE_NAME " Installed Successfully\n");
            }
            else
            {
                if(GetLastError() == ERROR_SERVICE_EXISTS)
                    printf(SERVICE_NAME " Already Exists.\n");
                else
                    printf(SERVICE_NAME " Was not Installed Successfully. Error Code %d\n", (int)GetLastError());
            }
        }

        CloseServiceHandle( serviceControlManager );
    }
}

void UninstallService()
{
    SC_HANDLE serviceControlManager = OpenSCManager( 0, 0,
            SC_MANAGER_CONNECT );

    if ( serviceControlManager )
    {
        SC_HANDLE service = OpenService( serviceControlManager,
                gszServiceName, SERVICE_QUERY_STATUS | DELETE );
        if ( service )
        {
            SERVICE_STATUS serviceStatus;
            if ( QueryServiceStatus( service, &serviceStatus ) )
            {
                if ( serviceStatus.dwCurrentState == SERVICE_STOPPED )
                {
                    if(DeleteService( service ))
                        printf(SERVICE_NAME " Removed Successfully\n");
                    else
                    {
                        DWORD dwError;
                        dwError = GetLastError();
                        if(dwError == ERROR_ACCESS_DENIED)
                            printf("Access Denied While trying to Remove " SERVICE_NAME " \n");
                        else if(dwError == ERROR_INVALID_HANDLE)
                            printf("Handle invalid while trying to Remove " SERVICE_NAME " \n");
                        else if(dwError == ERROR_SERVICE_MARKED_FOR_DELETE)
                            printf(SERVICE_NAME " already marked for deletion\n");
                    }
                }
                else
                {
                    printf(SERVICE_NAME " is still Running.\n");
                }
            }
            CloseServiceHandle( service );
        }
        CloseServiceHandle( serviceControlManager );
    }
}
void do_install()
{
    InstallService();
}

void do_remove()
{
    UninstallService();
}


// .-----------------------------------------------------------------------.
// |       ____               _       ____       _                         |
// |      / ___|_ __ __ _ ___| |__   |  _ \  ___| |__  _   _  __ _         |
// |     | |   | '__/ _` / __| '_ \  | | | |/ _ \ '_ \| | | |/ _` |        |
// |     | |___| | | (_| \__ \ | | | | |_| |  __/ |_) | |_| | (_| |        |
// |      \____|_|  \__,_|___/_| |_| |____/ \___|_.__/ \__,_|\__, |        |
// |                                                         |___/         |
// '-----------------------------------------------------------------------'

void open_crash_log(const std::string &log_directory)
{
    struct stat buf;

    if (g_config->crashDebug()) {
        WaitForSingleObject(crashlogMutex, INFINITE);
        snprintf(g_crash_log, sizeof(g_crash_log), "%s\\crash.log", log_directory.c_str());
        snprintf(g_connection_log, sizeof(g_connection_log), "%s\\connection.log", log_directory.c_str());
        snprintf(g_success_log, sizeof(g_success_log), "%s\\success.log", log_directory.c_str());

        // rename left over log if exists (means crash found)
        if (0 == stat(g_connection_log, &buf)) {
            // rotate to up to 9 crash log files
            char rotate_path_from[256];
            char rotate_path_to[256];
            for (int i=9; i>=1; i--) {
                snprintf(rotate_path_to, sizeof(rotate_path_to),
                        "%s\\crash-%d.log", log_directory.c_str(), i);
                if (i>1)
                    snprintf(rotate_path_from, sizeof(rotate_path_from),
                            "%s\\crash-%d.log", log_directory.c_str(), i-1);
                else
                    snprintf(rotate_path_from, sizeof(rotate_path_from),
                            "%s\\crash.log", log_directory.c_str());
                unlink(rotate_path_to);
                rename(rotate_path_from, rotate_path_to);
            }
            rename(g_connection_log, g_crash_log);
            g_found_crash = true;
        }

        // Threads are not allowed to access the crash_log
        g_connectionlog_file = CreateFile(TEXT(g_connection_log),
            GENERIC_WRITE,            // open for writing
            FILE_SHARE_READ,          // do not share
            NULL,                     // no security
            CREATE_ALWAYS,            // existing file only
            FILE_ATTRIBUTE_NORMAL,    // normal file
            NULL);
        gettimeofday(&g_crashlog_start, 0);
        time_t now = time(0);
        struct tm *t = localtime(&now);
        char timestamp[64];
        strftime(timestamp, sizeof(timestamp), "%b %d %H:%M:%S", t);
        crash_log("Opened crash log at %s.", timestamp);
        ReleaseMutex(crashlogMutex);
    }
}

void close_crash_log()
{
    if (g_config->crashDebug()) {
        WaitForSingleObject(crashlogMutex, INFINITE);
        crash_log("Closing crash log (no crash this time)");

        CloseHandle(g_connectionlog_file);
        DeleteFile(g_success_log);
        MoveFile(g_connection_log, g_success_log);
        ReleaseMutex(crashlogMutex);
    }
}

void crash_log(const char *format, ...)
{
    WaitForSingleObject(crashlogMutex, INFINITE);
    struct timeval tv;

//  DEBUG ONLY!
//    char buffer[256];
//    va_list args;
//    va_start (args, format);
//    vsprintf (buffer,format, args);
//    printf(buffer);
//    printf("\n");
//    va_end (args);

    char buffer[1024];
    if (g_connectionlog_file != INVALID_HANDLE_VALUE) {
        gettimeofday(&tv, 0);
        long int ellapsed_usec = tv.tv_usec - g_crashlog_start.tv_usec;
        long int ellapsed_sec  = tv.tv_sec - g_crashlog_start.tv_sec;
        if (ellapsed_usec < 0) {
            ellapsed_usec += 1000000;
            ellapsed_sec --;
        }

        DWORD dwBytesWritten = 0;
        snprintf(buffer, sizeof(buffer), "%ld.%06ld ", ellapsed_sec, ellapsed_usec);
        DWORD dwBytesToWrite = (DWORD)strlen(buffer);
        WriteFile(g_connectionlog_file, buffer, dwBytesToWrite, &dwBytesWritten, NULL);

        va_list ap;
        va_start(ap, format);
        vsnprintf(buffer, sizeof(buffer), format, ap);
        va_end(ap);

        dwBytesToWrite = (DWORD)strlen(buffer);
        WriteFile(g_connectionlog_file, buffer, dwBytesToWrite, &dwBytesWritten, NULL);

        WriteFile(g_connectionlog_file, "\r\n", 2, &dwBytesWritten, NULL);
        FlushFileBuffers(g_connectionlog_file);
    }
    ReleaseMutex(crashlogMutex);
}

void output_crash_log(SOCKET &out)
{
    output(out, "<<<logwatch>>>\n");
    output(out, "[[[Check_MK Agent]]]\n");
    if (g_found_crash) {
        WaitForSingleObject(crashlogMutex, INFINITE);
        output(out, "C Check_MK Agent crashed\n");
        FILE *f = fopen(g_crash_log, "r");
        char line[1024];
        while (0 != fgets(line, sizeof(line), f)) {
            output(out, "W %s", line);
        }
        ReleaseMutex(crashlogMutex);
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

void wsa_startup()
{
    WSADATA wsa;
    if (0 != WSAStartup(MAKEWORD(2, 0), &wsa)) {
        fprintf(stderr, "Cannot initialize winsock.\n");
        exit(1);
    }
}

void stop_threads()
{
    // Signal any threads to shut down
    // We don't rely on any check threat running/suspended calls
    // just check the script_container status
    int sizedt = script_containers.size();
    HANDLE hThreadArray[sizedt];
    int active_thread_count = 0;

    script_containers_t::iterator it_cont = script_containers.begin();
    while (it_cont != script_containers.end()) {
        if (it_cont->second->status == SCRIPT_COLLECT) {
            hThreadArray[active_thread_count++] = it_cont->second->worker_thread;
            it_cont->second->should_terminate = 1;
        }
        it_cont++;
    }
    WaitForMultipleObjects(active_thread_count, hThreadArray, TRUE, 5000);
    TerminateJobObject(g_workers_job_object, 0);
}

void output(SOCKET &out, const char *format, ...)
{
    static char outbuffer[HEAP_BUFFER_MAX]; // won't get any bigger...
    static int  len = 0;
    va_list ap;
    va_start(ap, format);
    int written_len = vsnprintf(outbuffer + len, sizeof(outbuffer) - len, format, ap);
    va_end(ap);
    len += written_len;

    // We do not send out the data immediately
    // This would lead to many small tcp packages
    bool write_to_socket = false;
    if (force_tcp_output || len > 1300)
        write_to_socket = true;

    if (do_tcp) {
        while (write_to_socket && !g_should_terminate) {
            ssize_t result = send(out, outbuffer, len, 0);
            if (result == SOCKET_ERROR) {
                debug("send() failed");
                int error = WSAGetLastError();
                if (error == WSAEINTR) {
                    debug("INTR. Nochmal...");
                    continue;
                }
                else if (error == WSAEINPROGRESS) {
                    debug("INPROGRESS. Nochmal...");
                    continue;
                }
                else if (error == WSAEWOULDBLOCK) {
                    debug("WOULDBLOCK. Komisch. Breche ab...");
                    break;
                }
                else {
                    debug("Anderer Fehler. Gebe auf\n");
                    break;
                }
            }
            else if (result == 0)
                debug("send() returned 0");
            else if (result != len) {
                debug("send() sent too few bytes");
                len -= result;
            }
            else
                len = 0;

            break;
        }
    }
    else {
        if (do_file)
            fwrite(outbuffer, len, 1, fileout);
        else
            fwrite(outbuffer, len, 1, stdout);
        len = 0;
    }
}



//   .----------------------------------------------------------------------.
//   |                        __  __       _                                |
//   |                       |  \/  | __ _(_)_ __                           |
//   |                       | |\/| |/ _` | | '_ \                          |
//   |                       | |  | | (_| | | | | |                         |
//   |                       |_|  |_|\__,_|_|_| |_|                         |
//   |                                                                      |
//   '----------------------------------------------------------------------'

void usage()
{
    fprintf(stderr, "Usage: \n"
            "check_mk_agent version         -- show version %s and exit\n"
            "check_mk_agent install         -- install as Windows NT service Check_Mk_Agent\n"
            "check_mk_agent remove          -- remove Windows NT service\n"
            "check_mk_agent adhoc           -- open TCP port %d and answer request until killed\n"
            "check_mk_agent test            -- test output of plugin, do not open TCP port\n"
            "check_mk_agent file FILENAME   -- write output of plugin into file, do not open TCP port\n"
            "check_mk_agent debug           -- similar to test, but with lots of debug output\n"
            "check_mk_agent showconfig      -- shows the effective configuration used (currently incomplete)\n",
            check_mk_version, g_config->port());
    exit(1);
}


void do_debug(const Environment &env)
{
    verbose_mode = true;
    do_tcp = false;
    SOCKET dummy;
    output_data(dummy, env);
}


void do_test(bool output_stderr, const Environment &env)
{
    do_tcp  = false;
    with_stderr = output_stderr;
    SOCKET dummy;
    open_crash_log(env.logDirectory());
    crash_log("Started in test mode.");
    output_data(dummy, env);
    close_crash_log();
}


bool ctrl_handler(DWORD fdwCtrlType)
{
    switch (fdwCtrlType)
    {
        /* handle the CTRL-C signal */
        case CTRL_C_EVENT:
            stop_threads();
            g_should_terminate = true;
            return TRUE;
        default:
            return FALSE;
    }
}

DWORD WINAPI DataCollectionThread( LPVOID lpParam )
{
    do
    {
        g_data_collection_retriggered = false;
        for (script_containers_t::iterator it_cont = script_containers.begin();
                it_cont != script_containers.end(); it_cont++)
            if (it_cont->second->execution_mode == ASYNC)
                run_script_container(it_cont->second);
    } while (g_data_collection_retriggered);
    return 0;
}

void determine_available_scripts(const char *dirname, script_type type, char* run_as_user)
{
    DIR  *dir     = opendir(dirname);
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
                if(dwAttr != INVALID_FILE_ATTRIBUTES && (dwAttr & FILE_ATTRIBUTE_DIRECTORY)) {
                    continue;
                }

                char *command = add_interpreter(path, newpath);
                if (run_as_user != NULL && strlen(run_as_user) > 1)
                    snprintf(command_with_user, sizeof(command_with_user), "runas /User:%s %s", run_as_user, command);
                else
                    snprintf(command_with_user, sizeof(command_with_user), "%s", command);

                // Look if there is already an script_container available for this program
                script_container* cont = NULL;
                script_containers_t::iterator it_cont = script_containers.find(string(command_with_user));
                if (it_cont == script_containers.end()) {
                    // create new entry for this program
                    cont = new script_container();
                    cont->path             = strdup(command_with_user);
                    cont->script_path      = strdup(path);
                    cont->buffer_time      = 0;
                    cont->buffer           = NULL;
                    cont->buffer_work      = NULL;
                    cont->type             = type;
                    cont->should_terminate = 0;
                    cont->run_as_user      = run_as_user;
                    cont->execution_mode   = get_script_execution_mode(name, type);
                    cont->timeout          = get_script_timeout(name, type);
                    cont->max_retries      = get_script_max_retries(name, type);
                    cont->max_age          = get_script_cache_age(name, type);
                    cont->status           = SCRIPT_IDLE;
                    cont->last_problem     = SCRIPT_NONE;
                    script_containers[cont->path] = cont;
                }
            }
        }
        closedir(dir);
    }
}

void collect_script_data(script_execution_mode mode)
{
    if (mode == SYNC) {
        crash_log("Collecting sync local/plugin data");
        for (script_containers_t::iterator it_cont = script_containers.begin();
             it_cont != script_containers.end(); it_cont++)
            if (it_cont->second->execution_mode == SYNC)
                run_script_container(it_cont->second);
    }
    else if (mode == ASYNC) {
        // If the thread is still running, just tell him to do another cycle
        DWORD dwExitCode = 0;
        if (GetExitCodeThread(g_collection_thread, &dwExitCode))
        {
            if (dwExitCode == STILL_ACTIVE) {
                g_data_collection_retriggered = true;
                return;
            }
        }

        if (g_collection_thread != INVALID_HANDLE_VALUE)
            CloseHandle(g_collection_thread);
        crash_log("Start async thread for collecting local/plugin data");
        g_collection_thread = CreateThread(NULL, // default security attributes
                0,                    // use default stack size
                DataCollectionThread, // thread function name
                NULL,                 // argument to thread function
                0,                    // use default creation flags
                NULL);                // returns the thread identifier
    }
}

void do_adhoc(const Environment &env)
{
    do_tcp = true;

    g_should_terminate = false;

    ListenSocket sock(g_config->port(), g_config->onlyFrom(), g_config->supportIPV6());

    printf("Listening for TCP connections (%s) on port %d\n",
            sock.supportsIPV6() ? sock.supportsIPV4() ? "IPv4 and IPv6"
                                : "IPv6 only"
                                : "IPv4 only",
            g_config->port());
    printf("Close window or press Ctrl-C to exit\n");
    fflush(stdout);

    // Job object for worker jobs. All worker are within this object
    // and receive a terminate when the agent ends
    g_workers_job_object = CreateJobObject(NULL, "workers_job");

    // Run all ASYNC scripts on startup, so that their data is available on
    // the first query of a client. Obviously, this slows down the agent startup...
    // This procedure is mandatory, since we want to prevent missing agent sections
    find_scripts(env);
    collect_script_data(ASYNC);
    DWORD dwExitCode = 0;
    while (true)
    {
        if (GetExitCodeThread(g_collection_thread, &dwExitCode))
        {
            if (dwExitCode != STILL_ACTIVE)
                break;
            Sleep(200);
        }
        else
            break;
    }

    // Das Dreckswindows kann nicht vernuenftig gleichzeitig auf
    // ein Socket und auf ein Event warten. Weil ich nicht extra
    // deswegen mit Threads arbeiten will, verwende ich einfach
    // select() mit einem Timeout und polle should_terminate.
    while (!g_should_terminate) {
        SOCKET connection = sock.acceptConnection();
        if ((void*)connection != NULL) {
            open_crash_log(env.logDirectory());
            std::string ip_hr = sock.readableIP(connection);
            crash_log("Accepted client connection from %s.", ip_hr.c_str());

            SetEnvironmentVariable("REMOTE_HOST", ip_hr.c_str());
            output_data(connection, env);
            close_crash_log();
            closesocket(connection);
        }
    }

    stop_threads();
    WSACleanup();
}

void find_scripts(const Environment &env)
{
    // Check if there are new scripts available
    // Scripts in default paths
    determine_available_scripts(env.pluginsDirectory().c_str(), PLUGIN, NULL);
    determine_available_scripts(env.localDirectory().c_str(),   LOCAL,  NULL);
    // Scripts included with user permissions
    for (script_include_t::iterator it_include = g_config->scriptIncludes().begin();
         it_include != g_config->scriptIncludes().end(); ++it_include)
        determine_available_scripts((*it_include)->path, (*it_include)->type, (*it_include)->user);
}

void output_data(SOCKET &out, const Environment &env)
{
    // make sure, output of numbers is not localized
    setlocale(LC_ALL, "C");

    if (g_config->crashDebug())
        output_crash_log(out);

    update_script_statistics();

    find_scripts(env);

    if (g_config->sectionEnabled(SECTION_CHECK_MK))
        section_check_mk(out, env);
    if (g_config->sectionEnabled(SECTION_UPTIME))
        section_uptime(out);
    if (g_config->sectionEnabled(SECTION_DF))
        section_df(out);
    if (g_config->sectionEnabled(SECTION_PS)) {
        if (g_config->psUseWMI()) {
            section_ps_wmi(out);
        } else {
            section_ps(out);
        }
    }
    if (g_config->sectionEnabled(SECTION_MEM))
        section_mem(out);
    if (g_config->sectionEnabled(SECTION_FILEINFO))
        section_fileinfo(out);
    if (g_config->sectionEnabled(SECTION_SERVICES))
        section_services(out);
    if (g_config->sectionEnabled(SECTION_WINPERF))
        section_winperf(out);
    if (g_config->sectionEnabled(SECTION_LOGWATCH))
        section_eventlog(out, env);
    if (g_config->sectionEnabled(SECTION_LOGFILES))
        section_logfiles(out, env);

    // Start data collection of SYNC scripts
    collect_script_data(SYNC);

    if (g_config->sectionEnabled(SECTION_PLUGINS))
        section_plugins(out);
    if (g_config->sectionEnabled(SECTION_LOCAL))
        section_local(out);
    if (g_config->sectionEnabled(SECTION_SPOOL))
        section_spool(out, env);
    if (g_config->sectionEnabled(SECTION_MRPE))
        section_mrpe(out);
    if (g_config->sectionEnabled(SECTION_SYSTEMTIME))
        section_systemtime(out);

    // Send remaining data in out buffer
    if (do_tcp) {
        force_tcp_output = true;
        output(out, "%s", "");
        force_tcp_output = false;
    }

    // Start data collection of ASYNC scripts
    collect_script_data(ASYNC);
}


void cleanup()
{
    delete g_wmi_helper;

    if (eventlog_buffer_size > 0)
        delete [] eventlog_buffer;

    unregister_all_eventlogs(); // frees a few bytes

    if (g_config != NULL) {
        for (fileinfo_paths_t::iterator it_path = g_config->fileinfoPaths().begin();
                it_path != g_config->fileinfoPaths().end(); it_path++) {
            free(*it_path);
        }
        g_config->fileinfoPaths().clear();

        cleanup_logwatch();
    }
}

void show_version()
{
    printf("Check_MK_Agent version %s\n", check_mk_version);
}


const char *state_long_name(char state_id) {
    switch (state_id) {
        case 'O': return "ok";
        case 'W': return "warning";
        case 'C': return "crit";
        case 'I': return "ignore";
        default: return "invalid";
    }
}

const char *level_name(int level_id) {
    switch (level_id) {
        case -1: return "off";
        case  0: return "all";
        case  1: return "warn";
        case  2: return "crit";
        default: return "invalid";
    }
}

void show_config()
{
    printf("[global]\n");
    printf("port = %d\n", g_config->port());
    printf("crash_debug = %s\n", g_config->crashDebug() ? "yes" : "no");
    if (!g_config->executeSuffixes().empty()) {
        printf("execute = ");
        for (execute_suffixes_t::iterator iter = g_config->executeSuffixes().begin();
                iter != g_config->executeSuffixes().end(); ++iter) {
            printf("%s", iter->c_str());
        }
        printf("\n");
    }

    printf("\n[logwatch]\n");
    printf("send_all = %s\n", g_config->logwatchSendInitialEntries() ? "yes" : "no");
    for (eventlog_config_t::iterator iter = g_config->eventlogConfig().begin();
            iter != g_config->eventlogConfig().end(); ++iter) {
        printf("logfile %s = %s%s\n",
                    iter->name.c_str(),
                    iter->hide_context ? "nocontext " : "",
                    level_name(iter->level));
    }


    printf("\n[local]\n");
    for (timeout_configs_t::iterator iter = g_config->timeoutConfigs(LOCAL).begin();
            iter != g_config->timeoutConfigs(LOCAL).end(); ++iter) {
        printf("timeout %s = %d\n", (*iter)->pattern, (*iter)->timeout);
    }
    for (cache_configs_t::iterator iter = g_config->cacheConfigs(LOCAL).begin();
            iter != g_config->cacheConfigs(LOCAL).end(); ++iter) {
        printf("cache_age %s = %d\n", (*iter)->pattern, (*iter)->max_age);
    }
    for (retry_count_configs_t::iterator iter = g_config->retryConfigs(LOCAL).begin();
            iter != g_config->retryConfigs(LOCAL).end(); ++iter) {
        printf("retry_count %s = %d\n", (*iter)->pattern, (*iter)->retries);
    }
    for (execution_mode_configs_t::iterator iter = g_config->executionModeConfigs(LOCAL).begin();
            iter != g_config->executionModeConfigs(LOCAL).end(); ++iter) {
        printf("execution %s = %s\n", (*iter)->pattern, (*iter)->mode == SYNC ? "SYNC" : "ASYNC");
    }
    for (script_include_t::iterator iter = g_config->scriptIncludes().begin();
            iter != g_config->scriptIncludes().end(); ++iter) {
        if ((*iter)->type == LOCAL) {
            printf("include %s = %s\n", (*iter)->user, (*iter)->path);
        }
    }

    printf("\n[plugin]\n");
    for (timeout_configs_t::iterator iter = g_config->timeoutConfigs(PLUGIN).begin();
            iter != g_config->timeoutConfigs(PLUGIN).end(); ++iter) {
        printf("timeout %s = %d\n", (*iter)->pattern, (*iter)->timeout);
    }
    for (cache_configs_t::iterator iter = g_config->cacheConfigs(PLUGIN).begin();
            iter != g_config->cacheConfigs(PLUGIN).end(); ++iter) {
        printf("cache_age %s = %d\n", (*iter)->pattern, (*iter)->max_age);
    }
    for (retry_count_configs_t::iterator iter = g_config->retryConfigs(PLUGIN).begin();
            iter != g_config->retryConfigs(PLUGIN).end(); ++iter) {
        printf("retry_count %s = %d\n", (*iter)->pattern, (*iter)->retries);
    }
    for (execution_mode_configs_t::iterator iter = g_config->executionModeConfigs(PLUGIN).begin();
            iter != g_config->executionModeConfigs(PLUGIN).end(); ++iter) {
        printf("execution %s = %s\n", (*iter)->pattern, (*iter)->mode == SYNC ? "SYNC" : "ASYNC");
    }
    for (script_include_t::iterator iter = g_config->scriptIncludes().begin();
            iter != g_config->scriptIncludes().end(); ++iter) {
        if ((*iter)->type == LOCAL) {
            printf("include %s = %s\n", (*iter)->user, (*iter)->path);
        }
    }

    printf("\n[logfiles]\n");
    for (logwatch_globlines_t::iterator iter = g_config->logwatchGloblines().begin();
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
            printf("%s", (*it_token)->pattern != NULL ? (*it_token)->pattern : "null");
        }
        printf("\n");
        for (condition_patterns_t::iterator it_pattern = (*iter)->patterns.begin();
                it_pattern != (*iter)->patterns.end(); ++it_pattern) {
            printf("%s = %s\n", state_long_name((*it_pattern)->state), (*it_pattern)->glob_pattern);
        }
        printf("\n");
    }

    printf("\n[winperf]\n");
    for (winperf_counters_t::iterator iter = g_config->winperfCounters().begin();
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
        printf("check = %s %s\n", (*iter)->service_description, (*iter)->command_line);
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
    snprintf(uninstall_file_path, 512, "%s\\uninstall_plugins.bat", env.agentDirectory().c_str());
    FILE *uninstall_file = fopen(uninstall_file_path, "w");
    fprintf(uninstall_file, "REM * If you want to uninstall the plugins which were installed during the\n"
                            "REM * last 'check_mk_agent.exe unpack' command, just execute this script\n\n");


    bool had_error = false;
    while (true) {
        int   read_bytes;
        BYTE  filepath_length;
        int   content_length;
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
        BYTE *dirname  = NULL;
        for (int i = filepath_length - 1; i >= 0; i--)
        {
            if (filepath[i] == '/') {
                if (filename == NULL) {
                    filename = filepath + i + 1;
                    dirname  = filepath;
                    filepath[i] = 0;
                }
                else {
                    filepath[i] = '\\';
                }
            }
        }
        if (dirname == NULL)
            filename = filepath;

        if (dirname != NULL) {
            char new_dir[1024];
            snprintf(new_dir, sizeof(new_dir), "%s\\%s", env.agentDirectory().c_str(), dirname);
            CreateDirectory(new_dir, NULL);
            fprintf(uninstall_file, "del \"%s\\%s\\%s\"\n", env.agentDirectory().c_str(), dirname, filename);
        }
        else
            fprintf(uninstall_file, "del \"%s\\%s\"\n", env.agentDirectory().c_str(), filename);

        // TODO: remove custom dirs on uninstall

        // Write plugin
        char plugin_path[512];
        if (dirname != NULL)
            snprintf(plugin_path, sizeof(plugin_path), "%s\\%s\\%s", env.agentDirectory().c_str(), dirname, filename);
        else
            snprintf(plugin_path, sizeof(plugin_path), "%s\\%s", env.agentDirectory().c_str(), filename);

        FILE *plugin_file = fopen(plugin_path, "wb");
        fwrite(content, 1, content_length, plugin_file);
        fclose(plugin_file);

        free(filepath);
        free(content);
    }

    fprintf(uninstall_file, "del \"%s\\uninstall_plugins.bat\"\n", env.agentDirectory().c_str());
    fclose(uninstall_file);
    fclose(file);

    if (had_error) {
        printf("There was an error on unpacking the Check_MK-Agent package: File integrity is broken\n."
               "The file might have been installed partially!");
        exit(1);
    }

}


void load_state(const Environment &env) {
    load_eventlog_offsets(env.eventlogStatefile());
}


void RunImmediate(const char *mode, int argc, char **argv)
{
    // base directory structure on current working directory or registered dir (from registry)?
    bool use_cwd = !strcmp(mode, "adhoc") || !strcmp(mode, "test");
    Environment env(use_cwd);

    g_config = new Configuration(env);

    if (g_config->useWMI()) {
        try {
            g_wmi_helper = new wmi::Helper();
        } catch (const std::runtime_error &ex) {
            fprintf(stderr, "Failed to initialize wmi: %s", ex.what());
            exit(1);
        }
    }

    load_state(env);

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
    }
    else if (!strcmp(mode, "adhoc") || !strcmp(mode, "service"))
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


int main(int argc, char **argv)
{
    wsa_startup();

    // Determine windows version
    osv.dwOSVersionInfoSize = sizeof(osv);
    GetVersionEx(&osv);

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

