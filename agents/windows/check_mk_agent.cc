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
#include <stdint.h>
#include <stdio.h>
#include <sys/time.h>
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
#include "Configurable.h"
#include "Configuration.h"
#include "Environment.h"
#include "EventLog.h"
#include "ExternalCmd.h"
#include "ListenSocket.h"
#include "OHMMonitor.h"
#include "OutputProxy.h"
#include "PerfCounter.h"
#include "SectionManager.h"
#include "Thread.h"
#include "crashhandling.h"
#include "dynamic_func.h"
#include "logging.h"
#include "stringutil.h"
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
//  | Declarations of macros, structs and function prototypes             |
//  '----------------------------------------------------------------------'

const char *check_mk_version = CHECK_MK_VERSION;

static const char RT_PROTOCOL_VERSION[2] = {'0', '0'};

#define SERVICE_NAME "Check_MK_Agent"

// Limits for static global arrays
#define MAX_EVENTLOGS 128

// Maximum heap buffer for a single local/plugin script
// This buffer contains the check output

// Check compilation environment 32/64 bit
#if _WIN32 || _WIN64
#if _WIN64
#define ENVIRONMENT64
#else
#define ENVIRONMENT32
#endif
#endif

using namespace std;

// Forward declarations of functions
void listen_tcp_loop(const Environment &env);
void output_data(OutputProxy &out, const Environment &env, bool realtime,
                 bool section_flush);
void RunImmediate(const char *mode, int argc, char **argv);

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

// Thread relevant variables
volatile bool g_should_terminate = false;

// Job object for all worker threads
// Gets terminated on shutdown
HANDLE g_workers_job_object;

struct GlobalConfig {
    Configuration parser;

    Configurable<int> port;
    Configurable<int> realtime_port;
    Configurable<int> realtime_timeout;
    Configurable<bool> crash_debug;
    Configurable<bool> section_flush;
    Configurable<bool> encrypted;
    Configurable<bool> encrypted_rt;
    Configurable<bool> support_ipv6;
    Configurable<std::string> passphrase;
    SplittingListConfigurable<only_from_t,
                              BlockMode::FileExclusive<only_from_t>>
        only_from;

    GlobalConfig(const Environment &env)
        : parser(env)
        , port(parser, "global", "port", 6556)
        , realtime_port(parser, "global", "realtime_port", 6559)
        , realtime_timeout(parser, "global", "realtime_timeout", 90)
        , crash_debug(parser, "global", "crash_debug", false)
        , section_flush(parser, "global", "section_flush", true)
        , encrypted(parser, "global", "encrypted", false)
        , encrypted_rt(parser, "global", "encrypted_rt", true)
        , support_ipv6(parser, "global", "ipv6", true)
        , passphrase(parser, "global", "passphrase", "")
        , only_from(parser, "global", "only_from") {}
} * g_config;

SectionManager *g_sections;

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

double file_time(const FILETIME *filetime) {
    static const double SEC_TO_UNIX_EPOCH = 11644473600.0;
    static const double WINDOWS_TICK = 10000000.0;

    _ULARGE_INTEGER uli;
    uli.LowPart = filetime->dwLowDateTime;
    uli.HighPart = filetime->dwHighDateTime;

    return (double(uli.QuadPart) / WINDOWS_TICK) - SEC_TO_UNIX_EPOCH;
}

double current_time() {
    SYSTEMTIME systime;
    FILETIME filetime;
    GetSystemTime(&systime);
    SystemTimeToFileTime(&systime, &filetime);
    return file_time(&filetime);
}

template <typename T>
bool in_set(const T &val, const std::set<T> &test_set) {
    return test_set.find(val) != test_set.end();
}

void foreach_enabled_section(bool realtime,
                             const std::function<void(Section *)> &func) {
    for (auto &section : g_sections->sections()) {
        if ((realtime && g_sections->realtimeSectionEnabled(section->name())) ||
            (!realtime && g_sections->sectionEnabled(section->name()))) {
            func(section.get());
        }
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
void stop_threads();

void WINAPI ServiceControlHandler(DWORD controlCode) {
    switch (controlCode) {
        case SERVICE_CONTROL_INTERROGATE:
            break;

        case SERVICE_CONTROL_SHUTDOWN:
        case SERVICE_CONTROL_STOP:
            g_should_terminate = true;
            stop_threads();
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
    std::vector<HANDLE> thread_handles;

    // Signal any threads to shut down
    // We don't rely on any check threat running/suspended calls
    // just check the script_container status
    foreach_enabled_section(false, [&thread_handles](Section *section) {
        std::vector<HANDLE> temp = section->stopAsync();
        thread_handles.insert(thread_handles.end(), temp.begin(), temp.end());
    });

    WaitForMultipleObjects(thread_handles.size(), &thread_handles[0], TRUE,
                           5000);
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
            check_mk_version, *g_config->port);
    exit(1);
}

void do_debug(const Environment &env) {
    verbose_mode = true;

    FileOutputProxy dummy(do_file ? fileout : stdout);

    output_data(dummy, env, false, *g_config->section_flush);
}

void do_test(bool output_stderr, const Environment &env) {
    with_stderr = output_stderr;
    FileOutputProxy dummy(do_file ? fileout : stdout);
    if (*g_config->crash_debug) {
        open_crash_log(env.logDirectory());
    }
    crash_log("Started in test mode.");
    output_data(dummy, env, false, *g_config->section_flush);
    if (*g_config->crash_debug) {
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

        std::unique_ptr<BufferedSocketProxy> out;

        if (*g_config->encrypted_rt) {
            out.reset(new EncryptingBufferedSocketProxy(INVALID_SOCKET,
                                                        *g_config->passphrase));
        } else {
            out.reset(new BufferedSocketProxy(INVALID_SOCKET));
        }

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
                        out->setSocket(INVALID_SOCKET);
                    }
                    current_address = data->last_address;
                    if (current_address.ss_family != 0) {
                        int sockaddr_size = 0;
                        if (current_address.ss_family == AF_INET) {
                            sockaddr_in *addrv4 =
                                (sockaddr_in *)&current_address;
                            addrv4->sin_port = htons(*g_config->realtime_port);
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
                                temp.sin_port = htons(*g_config->realtime_port);
                                temp.sin_family = AF_INET;
                                memcpy(&temp.sin_addr.s_addr,
                                       addrv6->sin6_addr.u.Byte + 12, 4);

                                current_address.ss_family = AF_INET;
                                sockaddr_size = sizeof(sockaddr_in);
                                memcpy(&current_address, &temp, sockaddr_size);
                            } else {
                                // FIXME: for reasons I don't understand, the
                                // v6-address we get from getpeername has all
                                // words flipped. why? is this safe or will it
                                // break on some systems?
                                for (int i = 0; i < 16; i += 2) {
                                    BYTE temp = addrv6->sin6_addr.u.Byte[i];
                                    addrv6->sin6_addr.u.Byte[i] =
                                        addrv6->sin6_addr.u.Byte[i + 1];
                                    addrv6->sin6_addr.u.Byte[i + 1] = temp;
                                }

                                addrv6->sin6_port =
                                    htons(*g_config->realtime_port);
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
                        out->setSocket(current_socket);
                    }
                }

                // send data
                if (current_socket != INVALID_SOCKET) {
                    // send data
                    SetEnvironmentVariable("REMOTE_HOST", current_ip.c_str());
                    SetEnvironmentVariable("REMOTE", current_ip.c_str());
                    char timestamp[11];
                    snprintf(timestamp, 11, "%" PRIdtime, time(NULL));

                    // these writes are unencrypted!
                    if (*g_config->encrypted) {
                        out->writeBinary(RT_PROTOCOL_VERSION, 2);
                    }
                    out->writeBinary(timestamp, 10);
                    output_data(*out, data->env, true, false);
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
    g_should_terminate = false;

    ListenSocket sock(*g_config->port, *g_config->only_from,
                      *g_config->support_ipv6);

    printf("Listening for TCP connections (%s) on port %d\n",
           sock.supportsIPV6()
               ? sock.supportsIPV4() ? "IPv4 and IPv6" : "IPv6 only"
               : "IPv4 only",
           *g_config->port);

    printf("realtime monitoring %s\n",
           g_sections->useRealtimeMonitoring() ? "active" : "inactive");

    printf("Close window or press Ctrl-C to exit\n");
    fflush(stdout);

    // Job object for worker jobs. All worker are within this object
    // and receive a terminate when the agent ends
    g_workers_job_object = CreateJobObject(nullptr, "workers_job");

    // Run all ASYNC scripts on startup, so that their data is available on
    // the first query of a client. Obviously, this slows down the agent
    // startup...
    // This procedure is mandatory, since we want to prevent missing agent
    // sections
    foreach_enabled_section(false,
                            [](Section *section) { section->startIfAsync(); });
    foreach_enabled_section(
        false, [](Section *section) { section->waitForCompletion(); });

    ThreadData thread_data{0, false, env};
    Thread realtime_checker(realtime_check_func, thread_data);

    if (g_sections->useRealtimeMonitoring()) {
        thread_data.terminate = false;
        realtime_checker.start();
    }

    std::unique_ptr<BufferedSocketProxy> out;
    if (*g_config->encrypted) {
        out.reset(new EncryptingBufferedSocketProxy(INVALID_SOCKET,
                                                    *g_config->passphrase));
    } else {
        out.reset(new BufferedSocketProxy(INVALID_SOCKET));
    }
    while (!g_should_terminate) {
        SOCKET connection = sock.acceptConnection();
        if ((void *)connection != NULL) {
            if (*g_config->crash_debug) {
                close_crash_log();
                open_crash_log(env.logDirectory());
            }
            out->setSocket(connection);
            if (*g_config->encrypted) {
                out->writeBinary(RT_PROTOCOL_VERSION, 2);
            }

            std::string ip_hr = sock.readableIP(connection);
            crash_log("Accepted client connection from %s.", ip_hr.c_str());
            {  // limit lifetime of mutex lock
                MutexLock guard(thread_data.mutex);
                thread_data.new_request = true;
                thread_data.last_address = sock.address(connection);
                thread_data.push_until =
                    time(NULL) + *g_config->realtime_timeout;
            }

            SetEnvironmentVariable("REMOTE_HOST", ip_hr.c_str());
            SetEnvironmentVariable("REMOTE", ip_hr.c_str());
            try {
                output_data(*out, env, false, *g_config->section_flush);
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

void output_data(OutputProxy &out, const Environment &env, bool realtime,
                 bool section_flush) {
    // make sure, output of numbers is not localized
    setlocale(LC_ALL, "C");

    // allow async sections to prepare their data
    foreach_enabled_section(realtime,
                            [](Section *section) { section->startIfAsync(); });

    // output sections
    foreach_enabled_section(realtime,
                            [&out, &env, section_flush](Section *section) {
                                std::stringstream str;
                                section->produceOutput(str, env);
                                out.output("%s", str.str().c_str());
                                if (section_flush) out.flush(false);
                            });

    // Send remaining data in out buffer
    out.flush(true);
}

void show_version() { printf("Check_MK_Agent version %s\n", check_mk_version); }

void show_config() { g_config->parser.outputConfigurables(std::cout); }

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

void postProcessOnlyFrom() {
    if (*g_config->support_ipv6) {
        // find all ipv4 specs, later insert a the same spec as a v6 adress.
        std::vector<ipspec *> v4specs;
        for (ipspec *spec : *g_config->only_from) {
            if (!spec->ipv6) {
                v4specs.push_back(spec);
            }
        }

        for (ipspec *spec : v4specs) {
            // also add a v4->v6 coverted filter

            ipspec *result = new ipspec();
            // first 96 bits are fixed: 0:0:0:0:0:ffff
            result->bits = 96 + spec->bits;
            result->ipv6 = true;
            memset(result->ip.v6.address, 0, sizeof(uint16_t) * 5);
            result->ip.v6.address[5] = 0xFFFFu;
            result->ip.v6.address[6] =
                static_cast<uint16_t>(spec->ip.v4.address & 0xFFFFu);
            result->ip.v6.address[7] =
                static_cast<uint16_t>(spec->ip.v4.address >> 16);
            netmaskFromPrefixIPv6(result->bits, result->ip.v6.netmask);
            g_config->only_from.add(result);
        }
    }
}

void RunImmediate(const char *mode, int argc, char **argv) {
    // base directory structure on current working directory or registered dir
    // (from registry)?
    bool use_cwd = !strcmp(mode, "adhoc") || !strcmp(mode, "test");
    Environment env(use_cwd);

    g_config = new GlobalConfig(env);
    g_sections = new SectionManager(g_config->parser, env);

    // careful: destroying the section manager destroys the wmi helpers created
    // for
    // wmi sections, which in turn releases COM objects. This needs to happen
    // before
    // cleanup of globals, otherwise a global CoUninitialize() may have been
    // called
    // and then those releases will fail
    OnScopeExit selectionsFree([]() {
        delete g_sections;
        g_sections = nullptr;
    });

    g_config->parser.readSettings();
    postProcessOnlyFrom();
    g_sections->loadDynamicSections();
    g_sections->emitConfigLoaded(env);

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

    SetUnhandledExceptionFilter(exception_handler);

    SetConsoleCtrlHandler((PHANDLER_ROUTINE)ctrl_handler, TRUE);

    if ((argc > 2) && (strcmp(argv[1], "file") && strcmp(argv[1], "unpack"))) {
        // need to parse config so we can display defaults in usage
        bool use_cwd = true;
        Environment env(use_cwd);
        g_config = new GlobalConfig(env);
        usage();
    }

    if (argc <= 1)
        RunService();
    else {
        RunImmediate(argv[1], argc - 2, argv + 2);
    }
}
