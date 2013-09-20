// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
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

#include <stdio.h>
#include <stdint.h>
#include <winsock2.h>
#include <windows.h>
#include <winbase.h>
#include <winreg.h>    // performance counters from registry
#include <tlhelp32.h>  // list of processes
#include <stdarg.h>
#include <time.h>
#include <locale.h>
#include <unistd.h>
#include <sys/types.h>
#include <dirent.h>
#include <sys/types.h>
#include <ctype.h>     // isspace()
#include <sys/stat.h>  // stat()
#include <sys/time.h>  // gettimeofday()
#include <map>
#include <vector>
#include <string>

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

#define CHECK_MK_VERSION "1.2.3i1"
#define CHECK_MK_AGENT_PORT 6556
#define SERVICE_NAME "Check_MK_Agent"
#define KiloByte 1024

#define SECTION_CHECK_MK     0x00000001
#define SECTION_UPTIME       0x00000002
#define SECTION_DF           0x00000004
#define SECTION_PS           0x00000008
#define SECTION_MEM          0x00000010
#define SECTION_SERVICES     0x00000020
#define SECTION_WINPERF      0x00000040
#define SECTION_LOGWATCH     0x00000080
#define SECTION_SYSTEMTIME   0x00000100
#define SECTION_PLUGINS      0x00000200
#define SECTION_LOCAL        0x00000400
#define SECTION_MRPE         0x00000800
#define SECTION_FILEINFO     0x00001000
#define SECTION_LOGFILES     0x00002000

// Limits for static global arrays
#define MAX_EVENTLOGS                 128

// Default buffer size for reading performance counters
#define DEFAULT_BUFFER_SIZE         40960L

// Maximum heap buffer for a single local/plugin script
// This buffer contains the check output
#define HEAP_BUFFER_DEFAULT         16384L
#define HEAP_BUFFER_MAX            524288L

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

using namespace std;

// Needed for only_from
struct ipspec {
    uint32_t address;
    uint32_t netmask;
    int      bits;
};

// Configuration for section [winperf]
struct winperf_counter {
    int   id;
    char *name;
};

// Configuration entries from [logwatch] for individual logfiles
struct eventlog_config_entry {
    char name[256];
    int level;
    int hide_context;
};

// Definitions for scripts
enum caching_method {
    CACHE_ASYNC,
    CACHE_SYNC,
    CACHE_OFF,
};

// States for plugin and local scripts
enum script_status {
    SCRIPT_IDLE,
    SCRIPT_FINISHED,
    SCRIPT_COLLECT,
    SCRIPT_ERROR,
    SCRIPT_TIMEOUT,
    SCRIPT_NONE,
};

enum script_type {
    TYPE_PLUGIN,
    TYPE_LOCAL
};

struct script_container {
    char         *path;
    int           max_age;
    int           timeout;
    int           max_retries;
    int           retry_count;
    time_t        buffer_time;
    char         *buffer;
    char         *buffer_work;
    script_type   type;
    script_status status;
    script_status last_problem;
    volatile bool should_terminate;
    HANDLE        worker_thread;
    HANDLE        job_object;
};

struct retry_config{
    char         *pattern;
    int           retries;
};
typedef vector<retry_config*> retry_config_t;
retry_config_t retry_configs_local, retry_configs_plugin;

struct timeout_config {
    char         *pattern;
    int           timeout;
};
typedef vector<timeout_config*> timeout_config_t;
timeout_config_t timeout_configs_local, timeout_configs_plugin;

struct cache_config {
    char         *pattern;
    int           max_age;
};
typedef vector<cache_config*> cache_config_t;
cache_config_t cache_configs_local, cache_configs_plugin;

typedef map<string, script_container*> script_containers_t;
script_containers_t script_containers;

// Command definitions for MRPE
struct mrpe_entry {
    char command_line[256];
    char plugin_name[64];
    char service_description[256];
};

// Forward declarations of functions
void listen_tcp_loop();
void output(SOCKET &out, const char *format, ...);
char *ipv4_to_text(uint32_t ip);
void output_data(SOCKET &out);
double file_time(const FILETIME *filetime);
void open_crash_log();
void close_crash_log();
void crash_log(const char *format, ...);

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

caching_method g_caching_method = CACHE_OFF;
bool verbose_mode               = false;
bool g_crash_debug              = false;
bool do_tcp                     = false;
bool force_tcp_output           = false; // if true, send socket data immediately

char g_hostname[256];
int  g_port                     = CHECK_MK_AGENT_PORT;


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

// Sections enabled (configurable in check_mk.ini)
unsigned long enabled_sections = 0xffffffff;

// Variables for section <<<logwatch>>>
bool logwatch_send_initial_entries = false;
bool logwatch_suppress_info        = true;

// dynamic buffer for event log entries. Grows with the
// time as needed. Never shrinked.
char *eventlog_buffer    = 0;
int eventlog_buffer_size = 0;

// Our memory of what event logs we know and up to
// which record entry we have seen its messages so
// far. We do not want to make use of C++ features
// here so sorry for the mess...
unsigned num_eventlogs = 0;
DWORD    known_record_numbers[MAX_EVENTLOGS];
char    *eventlog_names[MAX_EVENTLOGS];
bool     newly_found[MAX_EVENTLOGS];

// Directories
char g_agent_directory[256];
char g_current_directory[256];
char g_plugins_dir[256];
char g_local_dir[256];
char g_config_file[256];
char g_crash_log[256];
char g_connection_log[256];
char g_success_log[256];
char g_logwatch_statefile[256];

// Configuration of eventlog monitoring (see config parser)
int num_eventlog_configs = 0;
eventlog_config_entry eventlog_config[MAX_EVENTLOGS];

// Configuration of only_from
typedef vector<ipspec*> only_from_t;
only_from_t g_only_from;

// Configuration of winperf counters
typedef vector<winperf_counter*> winperf_counters_t;
winperf_counters_t g_winperf_counters;

// Configuration of winperf counters
typedef vector<mrpe_entry*> mrpe_entries_t;
mrpe_entries_t g_mrpe_entries;

// Configuration of execution suffixed
typedef vector<char *> execute_suffixes_t;
execute_suffixes_t g_execute_suffixes;

// Configuration of file patterns for fileinfo
typedef vector<char*> fileinfo_paths_t;
fileinfo_paths_t g_fileinfo_paths;

// Pointer to open crash log file, if crash_debug = on
FILE  *g_connectionlog_file = 0;
struct timeval g_crashlog_start;
bool   g_found_crash = false;


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
    printf("\n");
    fflush(stdout);
}


char *llu_to_string(unsigned long long value)
{
    static char buffer[64];

    if (value == 0) {
        strcpy(buffer, "0");
        return buffer;
    }

    buffer[63] = 0;

    char *write = buffer + 63;
    while (value > 0) {
        if (write <= buffer) {
            strcpy(buffer, "(invalid)");
            return buffer;
        }
        char digit = (value % 10) + '0';
        *--write = digit;
        value = value / 10;
    }
    return write;
}

unsigned long long string_to_llu(char *s)
{
    unsigned long long value = 0;
    unsigned long long mult = 1;
    char *e = s + strlen(s);
    while (e > s) {
        --e;
        value += mult * (*e - '0');
        mult *= 10;
    }
    return value;
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

char *lstrip(char *s)
{
    while (isspace(*s))
        s++;
    return s;
}


void rstrip(char *s)
{
    char *end = s + strlen(s); // point one beyond last character
    while (end > s && isspace(*(end - 1))) {
        end--;
    }
    *end = 0;
}

char *strip(char *s)
{
    rstrip(s);
    return lstrip(s);
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
    static LARGE_INTEGER Frequency,Ticks;
    QueryPerformanceFrequency (&Frequency);
    QueryPerformanceCounter (&Ticks);
    Ticks.QuadPart = Ticks.QuadPart - Frequency.QuadPart;
    unsigned int uptime = (double)Ticks.QuadPart / Frequency.QuadPart;
    output(out, "%s\n", llu_to_string(uptime));
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
        output(out, "%s ", llu_to_string(total.QuadPart / KiloByte));
        output(out, "%s ", llu_to_string((total.QuadPart - free_avail.QuadPart) / KiloByte));
        output(out, "%s ", llu_to_string(free_avail.QuadPart / KiloByte));
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
//  |                      ______             ______                       |
//  |                     / / / /  _ __  ___  \ \ \ \                      |
//  |                    / / / /  | '_ \/ __|  \ \ \ \                     |
//  |                    \ \ \ \  | |_) \__ \  / / / /                     |
//  |                     \_\_\_\ | .__/|___/ /_/_/_/                      |
//  |                             |_|                                      |
//  '----------------------------------------------------------------------'

void section_ps(SOCKET &out)
{
    crash_log("<<<ps>>>");
    output(out, "<<<ps:sep(0)>>>\n");
    HANDLE hProcessSnap;
    PROCESSENTRY32 pe32;

    hProcessSnap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (hProcessSnap != INVALID_HANDLE_VALUE)
    {
        pe32.dwSize = sizeof(PROCESSENTRY32);
        if (Process32First(hProcessSnap, &pe32)) {
            do {
                output(out, "%s\n", pe32.szExeFile);
            } while (Process32Next(hProcessSnap, &pe32));
        }
        CloseHandle(hProcessSnap);
    }
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
const char *service_start_type(SC_HANDLE scm, LPCTSTR service_name)
{
    // Query the start type of the service
    const char *start_type = "invalid1";
    SC_HANDLE schService;
    LPQUERY_SERVICE_CONFIG lpsc;
    schService = OpenService(scm, service_name, SERVICE_QUERY_CONFIG);
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
        EnumServicesStatusEx(scm, SC_ENUM_PROCESS_INFO, SERVICE_WIN32, SERVICE_STATE_ALL,
                NULL, 0, &bytes_needed, &num_services, 0, 0);
        if (GetLastError() == ERROR_MORE_DATA && bytes_needed > 0) {
            BYTE *buffer = (BYTE *)malloc(bytes_needed);
            if (buffer) {
                if (EnumServicesStatusEx(scm, SC_ENUM_PROCESS_INFO, SERVICE_WIN32, SERVICE_STATE_ALL,
                            buffer, bytes_needed,
                            &bytes_needed, &num_services, 0, 0))
                {
                    ENUM_SERVICE_STATUS_PROCESS *service = (ENUM_SERVICE_STATUS_PROCESS *)buffer;
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
                        for (char *w=(char *)(service->lpServiceName); *w; w++) {
                            if (*w == ' ')
                                *w = '_';
                        }

                        output(out, "%s %s/%s %s\n",
                                service->lpServiceName, state_name, start_type,
                                service->lpDisplayName);
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
    output(out, "<<<winperf_%s>>>\n", countername);
    output(out, "%.2f %u\n", current_time(), counter_base_number);

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
        } else {
            // Es ist ein anderer Fehler aufgetreten. Abbrechen.
            delete [] data;
            return;
        }
    }
    crash_log(" - read performance data, buffer size %d", size);

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
    output(out, "%d", counterPtr->CounterNameTitleIndex - counter_base_number);

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

    if (counterPtr->CounterType | PERF_SIZE_DWORD)
        output(out, " %llu", (ULONGLONG)(*(DWORD*)pData));

    else if (counterPtr->CounterType | PERF_SIZE_LARGE)
        output(out, " %llu", *(UNALIGNED ULONGLONG*)pData);

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
        output(out, " %s", llu_to_string(value));
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
    for (winperf_counters_t::iterator it_wp = g_winperf_counters.begin();
            it_wp != g_winperf_counters.end(); it_wp++)
        dump_performance_counters(out, (*it_wp)->id, (*it_wp)->name);
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
    char msgbuffer[2048];
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

    WCHAR wmsgbuffer[2048];
    DWORD dwFlags = FORMAT_MESSAGE_ARGUMENT_ARRAY | FORMAT_MESSAGE_FROM_SYSTEM;
    if (dll)
        dwFlags |= FORMAT_MESSAGE_FROM_HMODULE;

    DWORD len = FormatMessageW(
            // DWORD len = FormatMessage(
        dwFlags,
        dll,
        event->EventID,
        0, // accept any language
        wmsgbuffer,
        // msgbuffer,
        2048,
        (char **)strings);

            if (dll)
            FreeLibrary(dll);

            if (len)
            {
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
        DWORD bytesread, DWORD *record_number, bool just_find_end,
        int *worst_state, int level, int hide_context)
{
    WCHAR *strings[64];
    char regpath[128];
    BYTE dllpath[128];
    char source_name[128];

    EVENTLOGRECORD *event = (EVENTLOGRECORD *)buffer;
    while (bytesread > 0)
    {
        crash_log("     - record %d: process_eventlog_entries bytesread %d, event->Length %d", *record_number, bytesread, event->Length); 
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
        if (!just_find_end && (!hide_context || type_char != '.'))
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
            for (ns = 0; ns < num_strings; ns++) {
                if (ns >= 63) break;
                strings[ns] = s;
                s += wcslen(s) + 1;
            }
            strings[ns] = 0; // end marker in array

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
                    crash_log("     - record %d: DLLs to load: %s", *record_number, dllpath);
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
                crash_log("     - record %d: no DLLs listed in registry", *record_number);
            }

            // No text conversion succeeded. Output without text anyway
            if (!success) {
                crash_log("     - record %d: translation failed", *record_number);
                output_eventlog_entry(out, NULL, event, type_char, logname, source_name, strings);
            }

        } // type_char != '.'

        bytesread -= event->Length;
        crash_log("     - record %d: event_processed, bytesread %d, event->Length %d", *record_number, bytesread, event->Length);
        event = (EVENTLOGRECORD *) ((LPBYTE) event + event->Length);
    }
}


void output_eventlog(SOCKET &out, const char *logname,
        DWORD *record_number, bool just_find_end, int level, int hide_context)
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
        for (int t=0; t<2; t++)
        {
            *record_number = old_record_number;
            verbose("Starting from entry number %u", old_record_number);
            while (true) {
                DWORD flags;
                if (*record_number == 0) {
                    if (t == 1) {
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
                    verbose("Previous record number was %d. Doing seek read.", *record_number);
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
                    crash_log("   . got entries starting at %d (%d bytes)", *record_number + 1, bytesread);
                    process_eventlog_entries(out, logname, eventlog_buffer,
                            bytesread, record_number, just_find_end || t==0, &worst_state, level, hide_context);
                }
                else {
                    DWORD error = GetLastError();
                    if (error == ERROR_INSUFFICIENT_BUFFER) {
                        grow_eventlog_buffer(bytesneeded);
                        crash_log("   . needed to grow buffer to %d bytes", bytesneeded);
                    }
                    // found current end of log
                    else if (error == ERROR_HANDLE_EOF) {
                        verbose("End of logfile reached at entry %u. Worst state is %d",
                                *record_number, worst_state);
                        break;
                    }
                    // invalid parameter can also mean end of log
                    else if (error == ERROR_INVALID_PARAMETER) {
                        verbose("Invalid parameter at entry %u (could mean end of logfile). Worst state is %d",
                                *record_number, worst_state);
                        break;
                    }
                    else {
                        output(out, "ERROR: Cannot read eventlog '%s': error %u\n", logname, error);
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
    if (num_eventlogs >= MAX_EVENTLOGS)
        return; // veeery unlikely

    // check if we already know this one...
    for (unsigned i=0; i < num_eventlogs; i++) {
        if (!strcmp(logname, eventlog_names[i])) {
            newly_found[i] = true; // remember its still here
            return;
        }
    }

    // yet unknown. register it.
    known_record_numbers[num_eventlogs] = 0;
    eventlog_names[num_eventlogs] = strdup(logname);
    newly_found[num_eventlogs] = true;
    num_eventlogs ++;
}

void unregister_all_eventlogs()
{
    for (unsigned i=0; i < num_eventlogs; i++)
        free(eventlog_names[i]);
    num_eventlogs = 0;
}

/* Look into the registry in order to find out, which
   event logs are available. */
bool find_eventlogs(SOCKET &out)
{
    for (unsigned i=0; i<num_eventlogs; i++)
        newly_found[i] = 0;

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
                    output(out, "ERROR: Cannot enumerate over event logs: error code %d\n", r);
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
        output(out, "ERROR: Cannot open registry key %s for enumeration: error code %d\n",
                regpath, GetLastError());
    }
    return success;
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

// Stores the condition pattern together with its state
// Pattern definition within the config file:
//      C = *critpatternglobdescription*
struct condition_pattern {
    char  state;
    char *glob_pattern;
};
typedef vector<condition_pattern*> condition_patterns_t;

// Single element of a globline:
// C:/tmp/Testfile*.log
struct glob_token {
    char *pattern;
    bool  found_match;
};
typedef vector<glob_token*> glob_tokens_t;

// Container for all globlines read from the config
// The following is considered a globline
// textfile = C:\Logfile1.txt C:\tmp\Logfile*.txt
struct globline_container {
    glob_tokens_t        *tokens;
    condition_patterns_t *patterns;
};

// A textfile instance containing information about various file
// parameters and the pointer to the matching pattern_container
struct logwatch_textfile {
    char                 *path;
    unsigned long long    file_id;   // used to detect if a file has been replaced
    unsigned long long    file_size; // size of the file
    unsigned long long    offset;    // current fseek offset in the file
    bool                  missing;   // file no longer exists
    condition_patterns_t *patterns;  // glob patterns applying for this file
};

typedef vector<globline_container*> logwatch_globlines_t;
logwatch_globlines_t g_logwatch_globlines;

typedef vector<logwatch_textfile*>  logwatch_textfiles_t;
logwatch_textfiles_t g_logwatch_textfiles;
logwatch_textfiles_t g_logwatch_hints; // result of loaded state

globline_container *g_current_globline_container = NULL;

void save_logwatch_offsets()
{
    FILE *file = fopen(g_logwatch_statefile, "w");
    for (logwatch_textfiles_t::iterator it_tf = g_logwatch_textfiles.begin();
         it_tf != g_logwatch_textfiles.end(); it_tf++) {
        logwatch_textfile *tf = *it_tf;
        if (!tf->missing) {
            // llu_to_string is not reentrant, so do this in three steps
            fprintf(file, "%s|%s", tf->path, llu_to_string(tf->file_id));
            fprintf(file, "|%s", llu_to_string(tf->file_size));
            fprintf(file, "|%s\r\n", llu_to_string(tf->offset));
        }
    }
    fclose(file);
}

void parse_logwatch_state_line(char *line) 
{
    /* Example: line = "M://log1.log|98374598374|0|16"; */
    rstrip(line);
    char *p = line;
    while (*p && *p != '|') p++;
    *p = 0;
    char *path = line;
    p++;
    char *token = strtok(p, "|");
    unsigned long long file_id = string_to_llu(token);
    token = strtok(NULL, "|");
    unsigned long long file_size = string_to_llu(token);
    token = strtok(NULL, "|");
    unsigned long long offset = string_to_llu(token);

    logwatch_textfile *tf = new logwatch_textfile();
    tf->path = strdup(path);
    tf->file_id = file_id;
    tf->file_size = file_size;
    tf->offset = offset;
    tf->missing = false;
    tf->patterns = 0;
    g_logwatch_hints.push_back(tf);
}

void load_logwatch_offsets()
{
    static bool offsets_loaded = false;
    if (!offsets_loaded) {
        FILE *file = fopen(g_logwatch_statefile, "r");
        if (file) {
            char line[256];
            while (NULL != fgets(line, sizeof(line), file)) {
                parse_logwatch_state_line(line);
            }
            fclose(file);
        }
        offsets_loaded = true;
    }
}

void update_script_statistics()
{
    script_containers_t::iterator it = script_containers.begin();
    script_container *cont = NULL;

    memset(&g_script_stat, 0, sizeof(g_script_stat));
    while (it != script_containers.end()) {
        cont = it->second;
        if (cont->type == TYPE_PLUGIN)
            g_script_stat.pl_count++;
        else
            g_script_stat.lo_count++;

        switch (cont->last_problem) {
            case SCRIPT_TIMEOUT:
                if (cont->type == TYPE_PLUGIN)
                    g_script_stat.pl_timeouts++;
                else
                    g_script_stat.lo_timeouts++;
                break;
            case SCRIPT_ERROR:
                if (cont->type == TYPE_PLUGIN)
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

// Add a new state pattern to the current pattern container
void add_condition_pattern(char state, char *value)
{
    if (g_current_globline_container == NULL) {
        fprintf(stderr, "You need to set a textfile, before specifying a condition pattern\n");
        return;
    }

    condition_pattern *new_pattern = new condition_pattern();
    new_pattern->state = state;
    new_pattern->glob_pattern = strdup(value);
    g_current_globline_container->patterns->push_back(new_pattern);
}


logwatch_textfile* get_logwatch_textfile(const char *filename)
{
    for (logwatch_textfiles_t::iterator it_tf = g_logwatch_textfiles.begin();
         it_tf != g_logwatch_textfiles.end(); it_tf++) {
        if (strcmp(filename, (*it_tf)->path) == 0)
            return *it_tf;
    }
    return 0;
}

// Add a new textfile and to the global textfile list
// and determine some initial values
bool add_new_logwatch_textfile(const char *full_filename, condition_patterns_t *patterns)
{
    logwatch_textfile *new_textfile = new logwatch_textfile();

    HANDLE hFile = CreateFile(full_filename,// file to open
            GENERIC_READ,          // open for reading
            FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE,
            NULL,                  // default security
            OPEN_EXISTING,         // existing file only
            FILE_ATTRIBUTE_NORMAL, // normal file
            NULL);                 // no attr. template

    BY_HANDLE_FILE_INFORMATION fileinfo;
    GetFileInformationByHandle(hFile, &fileinfo);
    CloseHandle(hFile);

    new_textfile->path         = strdup(full_filename);
    new_textfile->missing      = false;
    new_textfile->patterns     = patterns;

    // Hier aus den gespeicherten Hints was holen....
    bool found_hint = false;
    for (logwatch_textfiles_t::iterator it_lh = g_logwatch_hints.begin();
         it_lh != g_logwatch_hints.end(); it_lh++) {
        logwatch_textfile *hint = *it_lh;
        if (!strcmp(hint->path, full_filename)) {
            new_textfile->file_size = hint->file_size;
            new_textfile->file_id = hint->file_id;
            new_textfile->offset = hint->offset;
            found_hint = true;
            break;
        }
    }

    if (!found_hint) {
        new_textfile->file_size    = (unsigned long long)fileinfo.nFileSizeLow +
            (((unsigned long long)fileinfo.nFileSizeHigh) << 32);
        new_textfile->file_id      = (unsigned long long)fileinfo.nFileIndexLow +
            (((unsigned long long)fileinfo.nFileIndexHigh) << 32);
        new_textfile->offset       = new_textfile->file_size;
    }

    g_logwatch_textfiles.push_back(new_textfile);
    return true;
}


// Check if the given full_filename already exists. If so, do some basic file integrity checks
// Otherwise create a new textfile instance
void update_or_create_logwatch_textfile(const char *full_filename, condition_patterns_t *patterns)
{
    logwatch_textfile *textfile;
    if ((textfile = get_logwatch_textfile(full_filename)) != NULL)
    {
        HANDLE hFile = CreateFile(textfile->path,// file to open
                GENERIC_READ,          // open for reading
                FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE,
                NULL,                  // default security
                OPEN_EXISTING,         // existing file only
                FILE_ATTRIBUTE_NORMAL, // normal file
                NULL);                 // no attr. template

        BY_HANDLE_FILE_INFORMATION fileinfo;
        // Do some basic checks to ensure its still the same file
        // try to fill the structure with info regarding the file
        if (hFile != INVALID_HANDLE_VALUE)
        {
            if (GetFileInformationByHandle(hFile, &fileinfo))
            {
                unsigned long long file_id = (unsigned long long)fileinfo.nFileIndexLow +
                    (((unsigned long long)fileinfo.nFileIndexHigh) << 32);
                textfile->file_size        = (unsigned long long)fileinfo.nFileSizeLow +
                    (((unsigned long long)fileinfo.nFileSizeHigh) << 32);

                if (file_id != textfile->file_id) {                // file has been changed
                    verbose("File %s: id has changed from %s", 
                            full_filename, llu_to_string(textfile->file_id));
                    verbose(" to %s\n", llu_to_string(file_id));
                    textfile->offset = 0;
                    textfile->file_id = file_id;
                } else if (textfile->file_size < textfile->offset) { // file has been truncated
                    verbose("File %s: file has been truncated\n", full_filename);
                    textfile->offset = 0;
                }

                textfile->missing = false; 
            }
            CloseHandle(hFile);
        } else {
            verbose("Cant open file with CreateFile %s\n", full_filename);
        }
    }
    else
        add_new_logwatch_textfile(full_filename, patterns); // Add new file
}

// Process a single expression (token) of a globline and try to find matching files
void process_glob_expression(glob_token *glob_token, condition_patterns_t *patterns) 
{
    WIN32_FIND_DATA data;
    char full_filename[512];
    glob_token->found_match = false;
    HANDLE h = FindFirstFileEx(glob_token->pattern, FindExInfoStandard, &data, FindExSearchNameMatch, NULL, 0);
    if (h != INVALID_HANDLE_VALUE) {
        glob_token->found_match = true;
        const char *basename = "";
        char *end = strrchr(glob_token->pattern, '\\');
        if (end) {
            *end = 0;
            basename = glob_token->pattern;
        }
        snprintf(full_filename,sizeof(full_filename), "%s\\%s", basename, data.cFileName);
        update_or_create_logwatch_textfile(full_filename, patterns);

        while (FindNextFile(h, &data)){
            snprintf(full_filename,sizeof(full_filename), "%s\\%s", basename, data.cFileName);
            update_or_create_logwatch_textfile(full_filename, patterns);
        }

        if (end)
            *end = '\\'; // repair string
        FindClose(h);
    }
}

// Add a new globline from the config file:
// C:/Testfile D:/var/log/data.log D:/tmp/art*.log
// This globline is split into tokens which are processed by process_glob_expression
void add_globline(char *value)
{
    // Each globline receives its own pattern container
    // In case new files matching the glob pattern are we
    // we already have all state,regex patterns available
    globline_container *new_globline = new globline_container();
    new_globline->patterns           = new condition_patterns_t();
    new_globline->tokens             = new glob_tokens_t();

    g_logwatch_globlines.push_back(new_globline);
    g_current_globline_container = new_globline;

    // Split globline into tokens
    if (value != 0) {
        char *copy = strdup(value);
        char *token = strtok(copy, "|");
        while (token) {
            token = lstrip(token);
            glob_token *new_token = new glob_token();
            new_token->pattern = strdup(token);
            new_globline->tokens->push_back(new_token);
            process_glob_expression(new_token, new_globline->patterns);
            token = strtok(NULL, "|");
        }
        free(copy);
    }
}


// Revalidate the existance of logfiles and check if the files attribute (id / size) indicate a change
void revalidate_logwatch_textfiles()
{
    // First of all invalidate all textfiles
    for (logwatch_textfiles_t::iterator it_tf = g_logwatch_textfiles.begin();
            it_tf != g_logwatch_textfiles.end(); it_tf++) {
        (*it_tf)->missing = true;
    }

    for (logwatch_globlines_t::iterator it_line = g_logwatch_globlines.begin();
         it_line != g_logwatch_globlines.end(); it_line++) {
        for (glob_tokens_t::iterator it_token = (*it_line)->tokens->begin();
             it_token != (*it_line)->tokens->end(); it_token++) {
            process_glob_expression(*it_token, (*it_line)->patterns);
        }
    }
}


bool globmatch(const char *pattern, char *astring);


// Remove missing files from list
void cleanup_logwatch_textfiles()
{ 
    for (logwatch_textfiles_t::iterator it_tf = g_logwatch_textfiles.begin();
         it_tf != g_logwatch_textfiles.end();) {
        if ((*it_tf)->missing) {
            // remove this file from the list
            free((*it_tf)->path);
            it_tf = g_logwatch_textfiles.erase(it_tf);
        } else
            it_tf++;
    }
}

// Called on program exit
void cleanup_logwatch() 
{
    // cleanup textfiles
    for (logwatch_textfiles_t::iterator it_tf = g_logwatch_textfiles.begin();
         it_tf != g_logwatch_textfiles.end(); it_tf++)
        (*it_tf)->missing = true;
    cleanup_logwatch_textfiles();

    // cleanup globlines and textpatterns
    for (logwatch_globlines_t::iterator it_globline = g_logwatch_globlines.begin();
         it_globline != g_logwatch_globlines.end(); it_globline++) {
        globline_container *cont = *it_globline;

        for (glob_tokens_t::iterator it_token = cont->tokens->begin();
             it_token != cont->tokens->end(); it_token++) {
            free((*it_token)->pattern);
            delete (*it_token);
        }
        cont->tokens->clear();
        delete cont->tokens;

        for (condition_patterns_t::iterator it_patt = cont->patterns->begin();
             it_patt != cont->patterns->end(); it_patt++) {
            free((*it_patt)->glob_pattern);
            delete (*it_patt);
        }
        cont->patterns->clear();
        delete cont->patterns;
        delete cont;
    }
}


// Process content of the given textfile
// Can be called in dry-run mode (write_output = false). This tries to detect CRIT or WARN patterns
// If write_output is set to true any data found is written to the out socket
bool process_textfile(FILE *file, logwatch_textfile* textfile, SOCKET &out, bool write_output) 
{
    char line[4096];
    condition_pattern *pattern = 0;
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
                    return true;
                state = pattern->state;
                break;
            }
        }

        if (write_output && strlen(line) > 0)
            output(out, "%c %s\n", state, line);
    }

    return false;
}


// The output of this section is compatible with
// the logwatch agent for Linux and UNIX
void section_logfiles(SOCKET &out)
{
    crash_log("<<<logwatch>>>");
    output(out, "<<<logwatch>>>\n");
    revalidate_logwatch_textfiles();

    logwatch_textfile *textfile;

    // Missing glob patterns
    for (logwatch_globlines_t::iterator it_globline = g_logwatch_globlines.begin();
         it_globline != g_logwatch_globlines.end(); it_globline++) {
        globline_container *cont = *it_globline;
        for (glob_tokens_t::iterator it_token = cont->tokens->begin();
             it_token != cont->tokens->end(); it_token++) {
            if (!((*it_token)->found_match))
                output(out, "[[[%s:missing]]]\n", (*it_token)->pattern);
        }
    }
    for (logwatch_textfiles_t::iterator it_tf = g_logwatch_textfiles.begin();
         it_tf != g_logwatch_textfiles.end(); it_tf++) {
        textfile = *it_tf;
        if (textfile->missing){
            output(out, "[[[%s:missing]]]\n", textfile->path);
            continue;
        }

        FILE *file = fopen(textfile->path, "r");
        if (!file) {
            output(out, "[[[%s:cannotopen]]]\n", textfile->path);
            continue;
        }

        output(out, "[[[%s]]]\n", textfile->path);

        if (textfile->offset == textfile->file_size) {// no new data
            fclose(file);
            continue;
        }

        fseek(file, textfile->offset, SEEK_SET);

        // try to find WARN / CRIT match
        bool found_match = process_textfile(file, textfile, out, false);

        if (found_match) {
            fseek(file, textfile->offset, SEEK_SET);
            process_textfile(file, textfile, out, true);
        }

        fclose(file);
        textfile->offset = textfile->file_size;
    }

    cleanup_logwatch_textfiles();
    save_logwatch_offsets();
}


// The output of this section is compatible with
// the logwatch agent for Linux and UNIX
void section_eventlog(SOCKET &out)
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
        for (unsigned i=0; i < num_eventlogs; i++) {
            if (!newly_found[i]) // not here any more!
                output(out, "[[[%s:missing]]]\n", eventlog_names[i]);
            else {
                // Get the configuration of that log file (which messages to send)
                int level = 1;
                int hide_context = 0;
                for (int j=0; j<num_eventlog_configs; j++) {
                    const char *cname = eventlog_config[j].name;
                    if (!strcmp(cname, "*") ||
                            !strcasecmp(cname, eventlog_names[i]))
                    {
                        level = eventlog_config[j].level;
                        hide_context = eventlog_config[j].hide_context;
                        break;
                    }
                }
                if (level != -1) {
                    output_eventlog(out, eventlog_names[i], &known_record_numbers[i],
                            first_run && !logwatch_send_initial_entries, level, hide_context);
                }
            }
        }
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

    output(out, "MemTotal:     %11d kB\n", statex.ullTotalPhys     / 1024);
    output(out, "MemFree:      %11d kB\n", statex.ullAvailPhys     / 1024);
    output(out, "SwapTotal:    %11d kB\n", (statex.ullTotalPageFile - statex.ullTotalPhys) / 1024);
    output(out, "SwapFree:     %11d kB\n", (statex.ullAvailPageFile - statex.ullAvailPhys) / 1024);
    output(out, "PageTotal:    %11d kB\n", statex.ullTotalPageFile / 1024);
    output(out, "PageFree:     %11d kB\n", statex.ullAvailPageFile / 1024);
    output(out, "VirtualTotal: %11d kB\n", statex.ullTotalVirtual / 1024);
    output(out, "VirtualFree:  %11d kB\n", statex.ullAvailVirtual / 1024);
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
void output_fileinfo(SOCKET &out, const char *basename, WIN32_FIND_DATA *data);

void section_fileinfo(SOCKET &out)
{
    crash_log("<<<fileinfo>>>");
    output(out, "<<<fileinfo:sep(124)>>>\n");
    output(out, "%.0f\n", current_time());
    for (fileinfo_paths_t::iterator it_path = g_fileinfo_paths.begin();
            it_path != g_fileinfo_paths.end(); it_path++) {
        output_fileinfos(out, *it_path);
    }
}

void output_fileinfos(SOCKET &out, const char *path)
{
    WIN32_FIND_DATA data;
    HANDLE h = FindFirstFileEx(path, FindExInfoStandard, &data, FindExSearchNameMatch, NULL, 0);
    if (h != INVALID_HANDLE_VALUE) {
        // compute basename of path: search backwards for '\'
        const char *basename = "";
        char *end = strrchr(path, '\\');
        if (end) {
            *end = 0;
            basename = path;
        }
        output_fileinfo(out, basename, &data);
        while (FindNextFile(h, &data))
            output_fileinfo(out, basename, &data);
        if (end)
            *end = '\\'; // repair string
        FindClose(h);
    }
    else {
        DWORD e = GetLastError();
        output(out, "%s|missing|%d\n", path, e);
    }
}


void output_fileinfo(SOCKET &out, const char *basename, WIN32_FIND_DATA *data)
{
    unsigned long long size = (unsigned long long)data->nFileSizeLow
        + (((unsigned long long)data->nFileSizeHigh) << 32);

    if (0 == (data->dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)) {
        output(out, "%s\\%s|%llu|%.0f\n", basename,
                data->cFileName, size, file_time(&data->ftLastWriteTime));
    }
}


bool handle_fileinfo_config_variable(char *var, char *value)
{
    if (!strcmp(var, "path")) {
        g_fileinfo_paths.push_back(strdup(value));
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

bool handle_script_config_variable(char *var, char *value, script_type type)
{
    if (!strncmp(var, "timeout ", 8)) {
        char* script_pattern  = lstrip(var + 8);
        timeout_config* entry = new timeout_config();
        entry->pattern        = strdup(script_pattern);
        entry->timeout        = atoi(value);
        if (type == TYPE_PLUGIN)
            timeout_configs_plugin.push_back(entry);
        else
            timeout_configs_local.push_back(entry);
    }
    else if (!strncmp(var, "cache_age ", 10)) {
        char* plugin_pattern = lstrip(var + 10);
        cache_config* entry  = new cache_config();
        entry->pattern       = strdup(plugin_pattern);
        entry->max_age       = atoi(value);
        if (type == TYPE_PLUGIN)
            cache_configs_plugin.push_back(entry);
        else
            cache_configs_local.push_back(entry);
    } else if (!strncmp(var, "retry_count ", 12)) {
        char* plugin_pattern = lstrip(var + 12);
        retry_config* entry  = new retry_config();
        entry->pattern       = strdup(plugin_pattern);
        entry->retries       = atoi(value);
        if (type == TYPE_PLUGIN)
            retry_configs_plugin.push_back(entry);
        else
            retry_configs_local.push_back(entry);
    }
    return true;
}

bool handle_plugin_config_variable(char *var, char *value)
{
    return handle_script_config_variable(var, value, TYPE_PLUGIN);
}

bool handle_local_config_variable(char *var, char *value)
{
    return handle_script_config_variable(var, value, TYPE_LOCAL);
}

int get_script_timeout(char *name, script_type type)
{
    timeout_config_t* configs = type == TYPE_PLUGIN ? &timeout_configs_plugin : &timeout_configs_local;
    for (timeout_config_t::iterator it = configs->begin();
            it != configs->end(); it++)
        if (globmatch((*it)->pattern, name))
            return (*it)->timeout;
    return type == TYPE_PLUGIN ? DEFAULT_PLUGIN_TIMEOUT : DEFAULT_LOCAL_TIMEOUT;
}

int get_script_cache_age(char *name, script_type type)
{
    cache_config_t* configs = type == TYPE_PLUGIN ? &cache_configs_plugin : &cache_configs_local;
    for (cache_config_t::iterator it = configs->begin();
            it != configs->end(); it++)
        if (globmatch((*it)->pattern, name))
            return (*it)->max_age;
    return 0;
}

int get_script_max_retries(char *name, script_type type)
{
    retry_config_t* configs = type == TYPE_PLUGIN ? &retry_configs_plugin : &retry_configs_local;
    for (retry_config_t::iterator it = configs->begin();
            it != configs->end(); it++)
        if (globmatch((*it)->pattern, name))
            return (*it)->retries;
    return 0;
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
        snprintf(newpath, 256, "powershell.exe -NoLogo -ExecutionPolicy RemoteSigned \"& \'%s\'\"", path);
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

    char *extension = name + strlen(name) - 4;
    if (g_execute_suffixes.size()) {
        if (extension[0] != '.')
            return true;
        extension ++;
        for (execute_suffixes_t::iterator it_ex = g_execute_suffixes.begin();
                it_ex!= g_execute_suffixes.end(); it_ex++)
            if (!strcasecmp(extension, *it_ex))
                return false;
        return true;
    }
    else{
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
    char buf[16635];           // i/o buffer

    STARTUPINFO si;
    SECURITY_ATTRIBUTES sa;
    SECURITY_DESCRIPTOR sd;   // security information for pipes
    PROCESS_INFORMATION pi;
    HANDLE newstdout,read_stdout;  // pipe handles

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

    if (!CreatePipe(&read_stdout,&newstdout,&sa,0)) // create stdout pipe
    {
        return 1;
    }

    //set startupinfo for the spawned process
    GetStartupInfo(&si);
    si.dwFlags = STARTF_USESTDHANDLES|STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;
    si.hStdOutput = newstdout;
    si.hStdError = newstdout;

    // spawn the child process
    if (!CreateProcess(NULL,cont->path,NULL,NULL,TRUE,CREATE_NEW_CONSOLE,
                NULL,NULL,&si,&pi))
    {
        CloseHandle(newstdout);
        CloseHandle(read_stdout);
        return 1;
    }

    // Create a job object for this process
    // Whenever the process ends all of its childs will terminate, too
    cont->job_object = CreateJobObject(NULL, NULL);
    AssignProcessToJobObject(cont->job_object, pi.hProcess);
    AssignProcessToJobObject(g_workers_job_object, pi.hProcess);

    unsigned long exit=0;  // process exit code
    unsigned long bread;   // bytes read
    unsigned long avail;   // bytes available

    memset(buf, 0, sizeof(buf));
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
        GetExitCodeProcess(pi.hProcess, &exit);      // while the process is running
        while (!buffer_full) {
            PeekNamedPipe(read_stdout, buf, sizeof(buf), &bread, &avail, NULL);
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
                memset(buf, 0, sizeof(buf));
                ReadFile(read_stdout, buf, sizeof(buf) - 1, &bread, NULL);
                out_offset += snprintf(cont->buffer_work + out_offset, current_heap_size - out_offset, buf);
            }
        }
        if (buffer_full) {
            // Buffer full -> delete incomplete data
            exit_code = 1;
            break;
        }

        if (exit != STILL_ACTIVE)
            break;

        Sleep(10);
    }

    TerminateJobObject(cont->job_object, exit_code);

    // cleanup the mess
    CloseHandle(cont->job_object);
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
    CloseHandle(newstdout);
    CloseHandle(read_stdout);
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

// Run all programs in given dir. If dry_run is set, only create the script_container and return
void run_external_programs(char *dirname, script_type type, bool dry_run = false)
{
    DIR *dir = opendir(dirname);
    time_t now = time(0);
    if (dir) {
        struct dirent *de;
        while (0 != (de = readdir(dir))) {
            char *name = de->d_name;

            if (name[0] != '.' && !banned_exec_name(name)) {
                char path[512];
                snprintf(path, sizeof(path), "%s\\%s", dirname, name);
                char newpath[512];
                // If the path in question is a directory -> return
                DWORD dwAttr = GetFileAttributes(path);
                if(dwAttr != 0xffffffff && (dwAttr & FILE_ATTRIBUTE_DIRECTORY)) {
                    continue;
                }

                char *command = add_interpreter(path, newpath);
                // Look if there is already an script_container available for this program
                script_container* cont = NULL;
                script_containers_t::iterator it_cont = script_containers.find(string(command));
                if (it_cont == script_containers.end()) {
                    // create new entry for this program
                    cont = new script_container();
                    cont->path             = strdup(command);
                    cont->buffer_time      = 0;
                    cont->buffer           = NULL;
                    cont->buffer_work      = NULL;
                    cont->type             = type;
                    cont->should_terminate = 0;
                    cont->timeout          = get_script_timeout(name, type);
                    cont->max_retries      = get_script_max_retries(name, type);
                    cont->max_age          = get_script_cache_age(name, type);
                    cont->status           = SCRIPT_IDLE;
                    cont->last_problem     = SCRIPT_NONE;
                    script_containers[cont->path] = cont;
                    if (dry_run)
                        continue;
                } else
                    cont = it_cont->second;

                if (now - cont->buffer_time >= cont->max_age) {
                    // Check if the thread within this cont is still collecting data
                    // or a thread has finished but its data wasnt processed yet
                    if (cont->status == SCRIPT_COLLECT || cont->status == SCRIPT_FINISHED) {
                        crash_log("Thread skip start: %s ; reason: %s", cont->path,
                                cont->status == SCRIPT_COLLECT ? "thread already running" : "new data available");
                        continue;
                    }
                    cont->buffer_time = time(0);
                    cont->status = SCRIPT_COLLECT;
                    crash_log("Thread start: %s", cont->path);
                    cont->worker_thread  = CreateThread(
                            NULL,                 // default security attributes
                            0,                    // use default stack size
                            ScriptWorkerThread,   // thread function name
                            cont,                 // argument to thread function
                            0,                    // use default creation flags
                            NULL);                // returns the thread identifier
                    if (g_caching_method == CACHE_OFF || g_caching_method == CACHE_SYNC) {
                        crash_log("Thread wait (%s): %s",
                                 (g_caching_method == CACHE_OFF ? "CACHE OFF" : "CACHE SYNC"), cont->path);
                        WaitForSingleObject(cont->worker_thread, INFINITE);
                        crash_log("Thread finished: %s", cont->path);
                    }
                } else
                    crash_log("Thread skip - using cache: %s", cont->path);

            }
        }
        closedir(dir);
    }
}

void output_external_programs(SOCKET &out, script_type type)
{
    // Collect and output data
    script_containers_t::iterator it_cont = script_containers.begin();
    script_container* cont = NULL;
    while (it_cont != script_containers.end()) {
        cont = it_cont->second;
        if (cont->type == type) {
            if (cont->status == SCRIPT_FINISHED) {
                // Free buffer
                if (cont->buffer != NULL) {
                    HeapFree(GetProcessHeap(), 0, cont->buffer);
                    cont->buffer = NULL;
                }
                cont->buffer      = cont->buffer_work;
                cont->buffer_work = NULL;
                cont->status      = SCRIPT_IDLE;
            } else if (cont->retry_count < 0 && cont->buffer != NULL) {
                // Remove outdated cache entries
                HeapFree(GetProcessHeap(), 0, cont->buffer);
                cont->buffer = NULL;
            }
            if (cont->buffer)
                output(out, cont->buffer);
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

void section_mrpe(SOCKET &out)
{
    crash_log("<<<mrpe>>>");
    output(out, "<<<mrpe>>>\n");

    for (mrpe_entries_t::iterator it_mrpe = g_mrpe_entries.begin();
            it_mrpe != g_mrpe_entries.end(); it_mrpe++)
    {
        mrpe_entry *entry = *it_mrpe;
        output(out, "(%s) %s ", entry->plugin_name, entry->service_description);

        FILE *f = _popen(entry->command_line, "r");
        if (!f) {
            output(out, "3 Unable to execute - plugin may be missing.\n");
            continue;
        }

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

void section_local_collect()
{
    run_external_programs(g_local_dir, TYPE_LOCAL);
}

void section_local(SOCKET &out)
{
    crash_log("<<<local>>>");
    output(out, "<<<local>>>\n");
    output_external_programs(out, TYPE_LOCAL);
}

//  .----------------------------------------------------------------------.
//  |                   ____  _             _                              |
//  |                  |  _ \| |_   _  __ _(_)_ __  ___                    |
//  |                  | |_) | | | | |/ _` | | '_ \/ __|                   |
//  |                  |  __/| | |_| | (_| | | | | \__ \                   |
//  |                  |_|   |_|\__,_|\__, |_|_| |_|___/                   |
//  |                                 |___/                                |
//  '----------------------------------------------------------------------'

void section_plugins_collect()
{
    run_external_programs(g_plugins_dir, TYPE_PLUGIN);
}

void section_plugins(SOCKET &out)
{
    output_external_programs(out, TYPE_PLUGIN);
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

void section_check_mk(SOCKET &out)
{
    crash_log("<<<check_mk>>>");
    output(out, "<<<check_mk>>>\n");
    output(out, "Version: %s\n", CHECK_MK_VERSION);
#ifdef ENVIRONMENT32
    output(out, "Architecture: 32bit\n");
#else
    output(out, "Architecture: 64bit\n");
#endif
    output(out, "AgentOS: windows\n");
    output(out, "Hostname: %s\n",         g_hostname);
    output(out, "WorkingDirectory: %s\n", g_current_directory);
    output(out, "ConfigFile: %s\n",       g_config_file);
    output(out, "AgentDirectory: %s\n",   g_agent_directory);
    output(out, "PluginsDirectory: %s\n", g_plugins_dir);
    output(out, "LocalDirectory: %s\n",   g_local_dir);
    output(out, "ScriptStatistics: Plugin C:%d E:%d T:%d "
            "Local C:%d E:%d T:%d\n",
            g_script_stat.pl_count, g_script_stat.pl_errors, g_script_stat.pl_timeouts,
            g_script_stat.lo_count, g_script_stat.lo_errors, g_script_stat.lo_timeouts);
    if (g_crash_debug) {
        output(out, "ConnectionLog: %s\n", g_connection_log);
        output(out, "CrashLog: %s\n",      g_crash_log);
        output(out, "SuccessLog: %s\n",    g_success_log);
    }

    output(out, "OnlyFrom:");
    if (g_only_from.size() == 0)
        output(out, " 0.0.0.0/0\n");
    else {
        for ( only_from_t::iterator it_from = g_only_from.begin();
                it_from != g_only_from.end(); it_from++ ) {
            ipspec *is = *it_from;
            output(out, " %d.%d.%d.%d/%d",
                    is->address & 0xff,
                    is->address >> 8 & 0xff,
                    is->address >> 16 & 0xff,
                    is->address >> 24 & 0xff,
                    is->bits);
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
    serviceStatus.dwServiceType      	    = SERVICE_WIN32_OWN_PROCESS;
    serviceStatus.dwCurrentState     	    = SERVICE_STOPPED;
    serviceStatus.dwControlsAccepted 	    = 0;
    serviceStatus.dwWin32ExitCode    	    = NO_ERROR;
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

        do_tcp = true;
        listen_tcp_loop();

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
            SC_HANDLE service = CreateService( serviceControlManager,
                    gszServiceName, gszServiceName,
                    SERVICE_ALL_ACCESS, SERVICE_WIN32_OWN_PROCESS,
                    SERVICE_AUTO_START, SERVICE_ERROR_IGNORE, path,
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

void open_crash_log()
{
    struct stat buf;

    if (g_crash_debug) {
        WaitForSingleObject(crashlogMutex, INFINITE);
        snprintf(g_crash_log, sizeof(g_crash_log), "%s\\crash.log", g_agent_directory);
        snprintf(g_connection_log, sizeof(g_connection_log), "%s\\connection.log", g_agent_directory);
        snprintf(g_success_log, sizeof(g_success_log), "%s\\success.log", g_agent_directory);

        // rename left over log if exists (means crash found)
        if (0 == stat(g_connection_log, &buf)) {
            // rotate to up to 9 crash log files
            char rotate_path_from[256];
            char rotate_path_to[256];
            for (int i=9; i>=1; i--) {
                snprintf(rotate_path_to, sizeof(rotate_path_to),
                        "%s\\crash-%d.log", g_agent_directory, i);
                if (i>1)
                    snprintf(rotate_path_from, sizeof(rotate_path_from),
                            "%s\\crash-%d.log", g_agent_directory, i-1);
                else
                    snprintf(rotate_path_from, sizeof(rotate_path_from),
                            "%s\\crash.log", g_agent_directory);
                unlink(rotate_path_to);
                rename(rotate_path_from, rotate_path_to);
            }
            rename(g_connection_log, g_crash_log);
            g_found_crash = true;
        }

        g_connectionlog_file = fopen(g_connection_log, "w");
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
    if (g_crash_debug) {
        WaitForSingleObject(crashlogMutex, INFINITE);
        crash_log("Closing crash log (no crash this time)");
        fclose(g_connectionlog_file);
        unlink(g_success_log);
        rename(g_connection_log, g_success_log);
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

    if (g_connectionlog_file) {
        gettimeofday(&tv, 0);
        long int ellapsed_usec = tv.tv_usec - g_crashlog_start.tv_usec;
        long int ellapsed_sec  = tv.tv_sec - g_crashlog_start.tv_sec;
        if (ellapsed_usec < 0) {
            ellapsed_usec += 1000000;
            ellapsed_sec --;
        }

        va_list ap;
        va_start(ap, format);
        fprintf(g_connectionlog_file, "%ld.%06ld ", ellapsed_sec, ellapsed_usec);
        vfprintf(g_connectionlog_file, format, ap);
        fputs("\n", g_connectionlog_file);
        fflush(g_connectionlog_file);
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
            output(out, "W ");
            output(out, line);
        }
        ReleaseMutex(crashlogMutex);
        fclose(f);
        g_found_crash = false;
    }
}



//  .----------------------------------------------------------------------.
//  |    ____             __ _                       _   _                 |
//  |   / ___|___  _ __  / _(_) __ _ _   _ _ __ __ _| |_(_) ___  _ __      |
//  |  | |   / _ \| '_ \| |_| |/ _` | | | | '__/ _` | __| |/ _ \| '_ \     |
//  |  | |__| (_) | | | |  _| | (_| | |_| | | | (_| | |_| | (_) | | | |    |
//  |   \____\___/|_| |_|_| |_|\__, |\__,_|_|  \__,_|\__|_|\___/|_| |_|    |
//  |                          |___/                                       |
//  '----------------------------------------------------------------------'

int parse_boolean(char *value)
{
    if (!strcmp(value, "yes"))
        return 1;
    else if (!strcmp(value, "no"))
        return 0;
    else
        fprintf(stderr, "Invalid boolean value. Only yes and no are allowed.\r\n");
    return -1;
}

void lowercase(char *s)
{
    while (*s) {
        *s = tolower(*s);
        s++;
    }
}
// Do a simple pattern matching with the jokers * and ?.
// This is case insensitive (windows-like).
bool globmatch(const char *pattern, char *astring)
{
    const char *p = pattern;
    char *s = astring;
    while (*s) {
        if (!*p)
            return false; // pattern too short

        // normal character-wise match
        if (tolower(*p) == tolower(*s) || *p == '?') {
            p++;
            s++;
        }

        // non-matching charactetr
        else if (*p != '*')
            return false;

        else { // check *
            // If there is more than one asterisk in the pattern,
            // we need to try out several variants. We do this
            // by backtracking (smart, eh?)
            int maxlength = strlen(s);
            // replace * by a sequence of ?, at most the rest length of s
            char *subpattern = (char *)malloc(strlen(p) + maxlength + 1);
            bool match = false;
            for (int i=0; i<=maxlength; i++) {
                for (int x=0; x<i; x++)
                    subpattern[x] = '?';
                strcpy(subpattern + i, p + 1); // omit leading '*'
                if (globmatch(subpattern, s)) {
                    match = true;
                    break;
                }
            }
            free(subpattern);
            return match;
        }
    }

    // string has ended, pattern not. Pattern must only
    // contain * now if it wants to match
    while (*p == '*') p++;
    return *p == 0;
}



void add_only_from(char *value)
{
    unsigned a, b, c, d;
    int bits = 32;

    if (strchr(value, '/')) {
        if (5 != sscanf(value, "%u.%u.%u.%u/%u", &a, &b, &c, &d, &bits)) {
            fprintf(stderr, "Invalid value %s for only_hosts\n", value);
            exit(1);
        }
    }
    else {
        if (4 != sscanf(value, "%u.%u.%u.%u", &a, &b, &c, &d)) {
            fprintf(stderr, "Invalid value %s for only_hosts\n", value);
            exit(1);
        }
    }

    uint32_t ip = a + b * 0x100 + c * 0x10000 + d * 0x1000000;
    uint32_t mask_swapped = 0;
    for (int bit = 0; bit < bits; bit ++)
        mask_swapped |= 0x80000000 >> bit;
    uint32_t mask;
    unsigned char *s = (unsigned char *)&mask_swapped;
    unsigned char *t = (unsigned char *)&mask;
    t[3] = s[0];
    t[2] = s[1];
    t[1] = s[2];
    t[0] = s[3];


    if ((ip & mask) != ip) {
        fprintf(stderr, "Invalid only_hosts entry: host part not 0: %s/%u",
                ipv4_to_text(ip), bits);
        exit(1);
    }

    ipspec *tmp_ipspec = new ipspec();
    tmp_ipspec->address = ip;
    tmp_ipspec->netmask = mask;
    tmp_ipspec->bits    = bits;
    g_only_from.push_back(tmp_ipspec);
}

char *next_word(char **line)
{
    if (*line == 0) // allow subsequent calls without checking
        return 0;

    char *end = *line + strlen(*line);
    char *value = *line;
    while (value < end) {
        value = lstrip(value);
        char *s = value;
        while (*s && !isspace(*s))
            s++;
        *s = 0;
        *line = s + 1;
        rstrip(value);
        if (strlen(value) > 0)
            return value;
        else
            return 0;
    }
    return 0;
}


void parse_only_from(char *value)
{
    char *word;
    while (0 != (word = next_word(&value)))
        add_only_from(word);
}

void parse_execute(char *value)
{
    // clean array if this options has been parsed already
    for (execute_suffixes_t::iterator it_ex = g_execute_suffixes.begin();
            it_ex!= g_execute_suffixes.end(); it_ex++)
        free(*it_ex);
    g_execute_suffixes.clear();

    char *suffix;
    while (0 != (suffix = next_word(&value)))
        g_execute_suffixes.push_back(strdup(suffix));
}


bool parse_crash_debug(char *value)
{
    int s = parse_boolean(value);
    if (s == -1)
        return false;
    g_crash_debug = s;
    return true;
}


bool handle_global_config_variable(char *var, char *value)
{
    if (!strcmp(var, "only_from")) {
        parse_only_from(value);
        return true;
    }
    else if (!strcmp(var, "port")) {
        g_port = atoi(value);
        return true;
    }
    else if (!strcmp(var, "execute")) {
        parse_execute(value);
        return true;
    }
    else if (!strcmp(var, "caching_method")) {
        if (!strcmp(value, "async"))
            g_caching_method = CACHE_ASYNC;
        else if (!strcmp(value, "sync"))
            g_caching_method = CACHE_SYNC;
        else if (!strcmp(value, "off"))
            g_caching_method = CACHE_OFF;
        return true;
    }
    else if (!strcmp(var, "crash_debug")) {
        return parse_crash_debug(value);
    }
    else if (!strcmp(var, "sections")) {
        enabled_sections = 0;
        char *word;
        while ((word = next_word(&value))) {
            if (!strcmp(word, "check_mk"))
                enabled_sections |= SECTION_CHECK_MK;
            else if (!strcmp(word, "uptime"))
                enabled_sections |= SECTION_UPTIME;
            else if (!strcmp(word, "df"))
                enabled_sections |= SECTION_DF;
            else if (!strcmp(word, "ps"))
                enabled_sections |= SECTION_PS;
            else if (!strcmp(word, "mem"))
                enabled_sections |= SECTION_MEM;
            else if (!strcmp(word, "services"))
                enabled_sections |= SECTION_SERVICES;
            else if (!strcmp(word, "winperf"))
                enabled_sections |= SECTION_WINPERF;
            else if (!strcmp(word, "logwatch"))
                enabled_sections |= SECTION_LOGWATCH;
            else if (!strcmp(word, "logfiles"))
                enabled_sections |= SECTION_LOGFILES;
            else if (!strcmp(word, "systemtime"))
                enabled_sections |= SECTION_SYSTEMTIME;
            else if (!strcmp(word, "plugins"))
                enabled_sections |= SECTION_PLUGINS;
            else if (!strcmp(word, "local"))
                enabled_sections |= SECTION_LOCAL;
            else if (!strcmp(word, "mrpe"))
                enabled_sections |= SECTION_MRPE;
            else if (!strcmp(word, "fileinfo"))
                enabled_sections |= SECTION_FILEINFO;
            else {
                fprintf(stderr, "Invalid section '%s'.\r\n", word);
                return false;
            }
        }
        return true;
    }

    return false;
}

bool handle_winperf_config_variable(char *var, char *value)
{
    if (!strcmp(var, "counters")) {
        char *word;
        while (0 != (word = next_word(&value))) {
            char *colon = strchr(word, ':');
            if (!colon) {
                fprintf(stderr, "Invalid counter '%s' in section [winperf]: need number and colon, e.g. 238:processor.\n", word);
                exit(1);
            }
            *colon = 0;
            winperf_counter *tmp_counter = new winperf_counter();
            tmp_counter->name = strdup(colon + 1);
            tmp_counter->id = atoi(word);
            g_winperf_counters.push_back(tmp_counter);
        }
        return true;
    }
    return false;
}

bool handle_logfiles_config_variable(char *var, char *value)
{
    load_logwatch_offsets();
    if (!strcmp(var, "textfile")) {
        if (value != 0)
            add_globline(value);
        return true;
    }else if (!strcmp(var, "warn")) {
        if (value != 0)
            add_condition_pattern('W', value);
        return true;
    }else if (!strcmp(var, "crit")) {
        if (value != 0)
            add_condition_pattern('C', value);
        return true;
    }else if (!strcmp(var, "ignore")) {
        if (value != 0)
            add_condition_pattern('I', value);
        return true;
    }else if (!strcmp(var, "ok")) {
        if (value != 0)
            add_condition_pattern('O', value);
        return true;
    }
    return false;
}

bool handle_logwatch_config_variable(char *var, char *value)
{
    if (!strncmp(var, "logfile ", 8)) {
        int level;
        char *logfilename = lstrip(var + 8);
        lowercase(logfilename);

        // value might have the option nocontext
        int hide_context = 0;
        char *s = value;
        while (*s && *s != ' ')
            s++;
        if (*s == ' ') {
            if (!strcmp(s+1, "nocontext"))
                hide_context = 1;
        }
        *s = 0;

        if (!strcmp(value, "off"))
            level = -1;
        else if (!strcmp(value, "all"))
            level = 0;
        else if (!strcmp(value, "warn"))
            level = 1;
        else if (!strcmp(value, "crit"))
            level = 2;
        else {
            fprintf(stderr, "Invalid log level '%s'.\r\n"
                    "Allowed are off, all, warn and crit.\r\n", value);
            return false;
        }

        if (num_eventlog_configs < MAX_EVENTLOGS) {
            eventlog_config[num_eventlog_configs].level = level;
            eventlog_config[num_eventlog_configs].hide_context = hide_context;
            strncpy(eventlog_config[num_eventlog_configs].name, logfilename, 256);
            num_eventlog_configs++;
        }

        return true;
    }
    else if (!strcmp(var, "sendall")) {
        int s = parse_boolean(value);
        if (s == -1)
            return false;
        logwatch_send_initial_entries = s;
        return true;
    }
    return false;
}

bool check_host_restriction(char *patterns)
{
    char *word;
    while ((word = next_word(&patterns))) {
        if (globmatch(word, g_hostname)) {
            return true;
        }
    }
    return false;
}


bool handle_mrpe_config_variable(char *var, char *value)
{
    if (!strcmp(var, "check")) {
        // First word: service description
        // Rest: command line
        fprintf(stderr, "VALUE: [%s]\r\n", value);
        char *service_description = next_word(&value);
        char *command_line = value;
        if (!command_line || !command_line[0]) {
            fprintf(stderr, "Invalid command specification for mrpe:\r\n"
                    "Format: SERVICEDESC COMMANDLINE\r\n");
            return false;
        }
        fprintf(stderr, "CMD: [%s]\r\n", command_line);

        mrpe_entry* tmp_entry = new mrpe_entry();

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
        strncpy(tmp_entry->plugin_name, plugin_name,
                sizeof(tmp_entry->plugin_name));
        g_mrpe_entries.push_back(tmp_entry);
        return true;
    }
    return false;
}


/* Example configuration file:

   [global]
# Process this logfile only on the following hosts
only_on = zhamzr12

# Restrict access to certain IP addresses
only_from = 127.0.0.1 192.168.56.0/24

# Enable crash debugging
crash_debug = on


[winperf]
# Select counters to extract. The following counters
# are needed by checks shipped with check_mk.
counters = 10332:msx_queues

[logwatch]
# Select which messages are to be sent in which
# event log
logfile system      = off
logfile application = info
logfile *           = off

[mrpe]
check = DISK_C: mrpe/check_disk -w C:
check = MEM mrpe/check_mem -w 10 -c 20
 */

void read_config_file()
{
    snprintf(g_config_file, sizeof(g_config_file), "%s\\check_mk.ini", g_agent_directory);
    FILE *file = fopen(g_config_file, "r");
    if (!file) {
        g_config_file[0] = 0;
        return;
    }

    char line[512];
    int lineno = 0;
    bool (*variable_handler)(char *var, char *value) = 0;
    bool is_active = true; // false in sections with host restrictions

    while (!feof(file)) {
        if (!fgets(line, sizeof(line), file)){
            fclose(file);
            return;
        }
        lineno ++;
        char *l = strip(line);
        if (l[0] == 0 || l[0] == '#' || l[0] == ';')
            continue; // skip empty lines and comments
        int len = strlen(l);
        if (l[0] == '[' && l[len-1] == ']') {
            // found section header
            l[len-1] = 0;
            char *section = l + 1;
            if (!strcmp(section, "global"))
                variable_handler = handle_global_config_variable;
            else if (!strcmp(section, "winperf"))
                variable_handler = handle_winperf_config_variable;
            else if (!strcmp(section, "logwatch"))
                variable_handler = handle_logwatch_config_variable;
            else if (!strcmp(section, "logfiles"))
                variable_handler = handle_logfiles_config_variable;
            else if (!strcmp(section, "mrpe"))
                variable_handler = handle_mrpe_config_variable;
            else if (!strcmp(section, "fileinfo"))
                variable_handler = handle_fileinfo_config_variable;
            else if (!strcmp(section, "plugins"))
                variable_handler = handle_plugin_config_variable;
            else if (!strcmp(section, "local"))
                variable_handler = handle_local_config_variable;
            else {
                fprintf(stderr, "Invalid section [%s] in %s in line %d.\r\n",
                        section, g_config_file, lineno);
                exit(1);
            }
            // forget host-restrictions if new section begins
            is_active = true;
        }
        else if (!variable_handler) {
            fprintf(stderr, "Line %d is outside of any section.\r\n", lineno);
            exit(1);
        }
        else {
            // split up line at = sign
            char *s = l;
            while (*s && *s != '=')
                s++;
            if (*s != '=') {
                fprintf(stderr, "Invalid line %d in %s.\r\n",
                        lineno, g_config_file);
                exit(1);
            }
            *s = 0;
            char *value = s + 1;
            char *variable = l;
            rstrip(variable);
            lowercase(variable);
            value = strip(value);

            // handle host restriction
            if (!strcmp(variable, "host"))
                is_active = check_host_restriction(value);

            // skip all other variables for non-relevant hosts
            else if (!is_active)
                continue;

            // Useful for debugging host restrictions
            else if (!strcmp(variable, "print"))
                fprintf(stderr, "%s\r\n", value);


            else if (!variable_handler(variable, value)) {
                fprintf(stderr, "Invalid entry in %s line %d.\r\n", g_config_file, lineno);
                exit(1);
            }
        }
    }
    fclose(file);
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
    if (0 != (gethostname(g_hostname, sizeof(g_hostname)))) {
        strcpy(g_hostname, "");
    }

}

char *ipv4_to_text(uint32_t ip)
{
    static char text[32];
    snprintf(text, 32, "%u.%u.%u.%u",
            ip & 255,
            ip >> 8 & 255,
            ip >> 16 & 255,
            ip >> 24);
    return text;
}

bool check_only_from(uint32_t ip)
{
    if (g_only_from.size() == 0)
        return true; // no restriction set

    for (only_from_t::iterator it_from = g_only_from.begin();
            it_from != g_only_from.end(); it_from++) {
        uint32_t signibits = ip & (*it_from)->netmask;
        if (signibits == (*it_from)->address)
            return true;
    }
    return false;
}


SOCKET RemoveSocketInheritance(SOCKET oldsocket)
{
    HANDLE newhandle;
    DuplicateHandle(GetCurrentProcess(), (HANDLE)oldsocket,
            GetCurrentProcess(), &newhandle, 0, FALSE,
            DUPLICATE_CLOSE_SOURCE | DUPLICATE_SAME_ACCESS);
    return (SOCKET)newhandle;
}

void stop_threads()
{
    // Signal any threads to shut down
    // We don't rely on any check threat running/suspended calls
    // just check the script_container status
    HANDLE hThreadArray[script_containers.size()];
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

void listen_tcp_loop()
{
    // We need to create a socket which listen for incoming connections
    // but we do not want that it is inherited to child processes (local/plugins)
    // Therefore we open the socket - this one is inherited by default
    // Now we duplicate this handle and explicitly say that inheritance is forbidden
    // and use the duplicate from now on
    SOCKET tmp_s = socket(AF_INET, SOCK_STREAM, 0);
    SOCKET s = RemoveSocketInheritance(tmp_s);

    SOCKADDR_IN addr;
    memset(&addr, 0, sizeof(SOCKADDR_IN));
    addr.sin_family = AF_INET;
    addr.sin_port = htons(g_port);
    addr.sin_addr.s_addr = ADDR_ANY;

    int optval = 1;
    setsockopt(s, SOL_SOCKET, SO_REUSEADDR, (const char*)&optval, sizeof(optval));

    if (SOCKET_ERROR == bind(s, (SOCKADDR *)&addr, sizeof(SOCKADDR_IN))) {
        fprintf(stderr, "Cannot bind socket to port %d\n", g_port);
        exit(1);
    }

    if (SOCKET_ERROR == listen(s, 5)) {
        fprintf(stderr, "Cannot listen to socket\n");
        exit(1);
    }

    // Job object for worker jobs. All worker are within this object
    // and receive a terminate when the agent ends
    g_workers_job_object = CreateJobObject(NULL, "workers_job");

    SOCKET connection;
    // Loop for ever.
    debug("Starting main loop.");
    while (!g_should_terminate)
    {
        // Das Dreckswindows kann nicht vernuenftig gleichzeitig auf
        // ein Socket und auf ein Event warten. Weil ich nicht extra
        // deswegen mit Threads arbeiten will, verwende ich einfach
        // select() mit einem Timeout und polle should_terminate.

        fd_set fds;
        FD_ZERO(&fds);
        FD_SET(s, &fds);
        struct timeval timeout;
        timeout.tv_sec = 0;
        timeout.tv_usec = 500000;

        SOCKADDR_IN remote_addr;
        int addr_len = sizeof(SOCKADDR_IN);

        if (1 == select(1, &fds, NULL, NULL, &timeout))
        {
            connection = accept(s, (SOCKADDR *)&remote_addr, &addr_len);
            connection = RemoveSocketInheritance(connection);
            if (connection != INVALID_SOCKET) {
                uint32_t ip = 0;
                if (remote_addr.sin_family == AF_INET)
                    ip = remote_addr.sin_addr.s_addr;
                if (check_only_from(ip)) {
                    open_crash_log();
                    crash_log("Accepted client connection from %u.%u.%u.%u.",
                            ip & 0xff, (ip >> 8) & 0xff, (ip >> 16) & 0xff, (ip >> 24) & 0xff);
                    output_data(connection);
                    close_crash_log();
                }
                closesocket(connection);
            }
        }
        else if (!g_should_terminate) {
            Sleep(1); // should never happen
        }
    }

    stop_threads();

    closesocket(s);
    WSACleanup();

}


void output(SOCKET &out, const char *format, ...)
{
    static char outbuffer[HEAP_BUFFER_MAX]; // won't get any bigger...
    static int  len = 0;
    va_list ap;
    va_start(ap, format);
    int written_len = vsnprintf(outbuffer + len, sizeof(outbuffer) - len, format, ap);
    len += written_len;

    // We do not send out the data immediately
    // This would lead to many small tcp packages
    bool write_to_socket = false;
    if (force_tcp_output || len > 1300)
        write_to_socket = true;

    if (do_tcp) {
        while (write_to_socket && !g_should_terminate) {
            int result = send(out, outbuffer, len, 0);
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
            "check_mk_agent version -- show version " CHECK_MK_VERSION " and exit\n"
            "check_mk_agent install -- install as Windows NT service Check_Mk_Agent\n"
            "check_mk_agent remove  -- remove Windows NT service\n"
            "check_mk_agent adhoc   -- open TCP port %d and answer request until killed\n"
            "check_mk_agent test    -- test output of plugin, do not open TCP port\n"
            "check_mk_agent debug   -- similar to test, but with lots of debug output\n", g_port);
    exit(1);
}


void do_debug()
{
    verbose_mode = true;
    do_tcp = false;
    // logwatch_send_initial_entries = true;
    // logwatch_suppress_info = false;
    SOCKET dummy;
    output_data(dummy);
}

void do_test()
{
    do_tcp = false;
    SOCKET dummy;
    output_data(dummy);
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
        if (enabled_sections & SECTION_PLUGINS) {
            section_plugins_collect();
        }
        if (enabled_sections & SECTION_LOCAL) {
            section_local_collect();
        }
    } while (g_data_collection_retriggered);
    return 0;
}

void start_external_data_collection()
{

    // If the thread is still running, just tell him to do another cycle
    // This can only apply to CACHE_SYNC and CACHE_ASYNC, since in
    // CACHE_OFF mode we always wait till the thread has finished
    DWORD dwExitCode = 0;
    if(GetExitCodeThread(g_collection_thread, &dwExitCode))
    {
        if (dwExitCode == STILL_ACTIVE) {
            g_data_collection_retriggered = true;
            return;
        }
    }

    crash_log("Start thread for collecting local/plugin data");
    g_collection_thread = CreateThread(NULL, // default security attributes
            0,                    // use default stack size
            DataCollectionThread, // thread function name
            NULL,                 // argument to thread function
            0,                    // use default creation flags
            NULL);                // returns the thread identifier

    // If CACHE_OFF is set are waiting till the thread has finished
    if (g_caching_method == CACHE_OFF)
        WaitForSingleObject(g_collection_thread, INFINITE);
}

void do_adhoc()
{

    // If caching is activated do an initial data collection run on startup
    // Otherwise we might miss some important data on the first inventory
    if (g_caching_method != CACHE_OFF)
        start_external_data_collection();

    do_tcp = true;
    printf("Listening for TCP connections on port %d\n", g_port);
    printf("Close window or press Ctrl-C to exit\n");
    fflush(stdout);

    g_should_terminate = false;

    listen_tcp_loop(); // runs for ever or until Ctrl-C
}

void output_data(SOCKET &out)
{
    // make sure, output of numbers is not localized
    setlocale(LC_ALL, "C");

    if (g_crash_debug)
        output_crash_log(out);

    update_script_statistics();

    if (enabled_sections & SECTION_CHECK_MK)
        section_check_mk(out);
    if (enabled_sections & SECTION_UPTIME)
        section_uptime(out);
    if (enabled_sections & SECTION_DF)
        section_df(out);
    if (enabled_sections & SECTION_PS)
        section_ps(out);
    if (enabled_sections & SECTION_MEM)
        section_mem(out);
    if (enabled_sections & SECTION_FILEINFO)
        section_fileinfo(out);
    if (enabled_sections & SECTION_SERVICES)
        section_services(out);
    if (enabled_sections & SECTION_WINPERF)
        section_winperf(out);
    if (enabled_sections & SECTION_LOGWATCH)
        section_eventlog(out);
    if (enabled_sections & SECTION_LOGFILES)
        section_logfiles(out);

    // Collect local / plugins data for later usage
    // These sections are handled in seperate threads and processes
    if (g_caching_method == CACHE_OFF)
        start_external_data_collection();

    if (enabled_sections & SECTION_PLUGINS)
        section_plugins(out);
    if (enabled_sections & SECTION_LOCAL)
        section_local(out);
    if (enabled_sections & SECTION_MRPE)
        section_mrpe(out);
    if (enabled_sections & SECTION_SYSTEMTIME)
        section_systemtime(out);

    // Send remaining data in out buffer
    if (do_tcp) {
        force_tcp_output = true;
        output(out, "");
        force_tcp_output = false;
    }

    if (g_caching_method != CACHE_OFF)
        start_external_data_collection();
}


void cleanup()
{
    if (eventlog_buffer_size > 0)
        delete [] eventlog_buffer;

    unregister_all_eventlogs(); // frees a few bytes

    for (execute_suffixes_t::iterator it_ex = g_execute_suffixes.begin(); 
            it_ex != g_execute_suffixes.end(); it_ex++)
        free(*it_ex);
    g_execute_suffixes.clear();

    for (fileinfo_paths_t::iterator it_path = g_fileinfo_paths.begin();
            it_path != g_fileinfo_paths.end(); it_path++) {
        free(*it_path);
    }
    g_fileinfo_paths.clear();

    cleanup_logwatch();
}

void show_version()
{
    printf("Check_MK_Agent version %s\n", CHECK_MK_VERSION);
}

void get_agent_dir(char *buffer, int size)
{
    buffer[0] = 0;

    HKEY key;
    DWORD ret = RegOpenKeyEx(HKEY_LOCAL_MACHINE,
            "SYSTEM\\CurrentControlSet\\Services\\check_mk_agent", 0, KEY_READ, &key);
    if (ret == ERROR_SUCCESS)
    {
        DWORD dsize = size;
        if (ERROR_SUCCESS == RegQueryValueEx(key, "ImagePath", NULL, NULL, (BYTE *)buffer, &dsize))
        {
            char *end = buffer + strlen(buffer);
            // search backwards for backslash
            while (end > buffer && *end != '\\')
                end--;
            *end = 0; // replace \ with string end => get directory of executable

            // Handle case where name is quoted with double quotes.
            // This is reported to happen on some 64 Bit systems when spaces
            // are in the directory name.
            if (*buffer == '"') {
                memmove(buffer, buffer + 1, strlen(buffer));
            }
        }
        RegCloseKey(key);
    }
    else {
        // If the agent is not installed as service, simply
        // assume the current directory to be the agent
        // directory (for test and adhoc mode)
        strncpy(buffer, g_current_directory, size);
        if (buffer[strlen(buffer)-1] == '\\') // Remove trailing backslash
            buffer[strlen(buffer)-1] = 0;
    }

}

void determine_directories() 
{
    // Determine directories once and forever
    getcwd(g_current_directory, sizeof(g_current_directory));
    get_agent_dir(g_agent_directory, sizeof(g_agent_directory));
    snprintf(g_plugins_dir, sizeof(g_plugins_dir), "%s\\plugins", g_agent_directory);
    snprintf(g_local_dir, sizeof(g_local_dir), "%s\\local", g_agent_directory);
    snprintf(g_logwatch_statefile, sizeof(g_logwatch_statefile), "%s\\logstate.txt", g_agent_directory);
}

int main(int argc, char **argv)
{
    wsa_startup();
    determine_directories();
    read_config_file();

    SetConsoleCtrlHandler((PHANDLER_ROUTINE)ctrl_handler, TRUE);

    if (argc > 2)
        usage();
    else if (argc <= 1)
        RunService();
    else if (!strcmp(argv[1], "test"))
        do_test();
    else if (!strcmp(argv[1], "adhoc"))
        do_adhoc();
    else if (!strcmp(argv[1], "install"))
        do_install();
    else if (!strcmp(argv[1], "remove"))
        do_remove();
    else if (!strcmp(argv[1], "debug"))
        do_debug();
    else if (!strcmp(argv[1], "version"))
        show_version();
    else
        usage();

    cleanup();
}

