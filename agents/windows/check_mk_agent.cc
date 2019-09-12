// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2018             mk@mathias-kettner.de |
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

#include <winsock2.h>
#include <ctype.h>  // isspace()
#include <dirent.h>
#include <inttypes.h>
#include <locale.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <sys/time.h>
#include <sys/types.h>
#include <time.h>
#include <unistd.h>
#include <winbase.h>
#include <windows.h>
#include <winreg.h>  // performance counters from registry
#include <ws2ipdef.h>
#include <algorithm>
#include <fstream>
#include <functional>
#include <map>
#include <memory>
#include <optional>
#include <string>
#include <unordered_map>
#include <vector>
#include "ChronoUtils.h"
#include "Configurable.h"
#include "Configuration.h"
#include "CrashHandler.h"
#include "Environment.h"
#include "EventLog.h"
#include "ExternalCmd.h"
#include "ListenSocket.h"
#include "OHMMonitor.h"
#include "OutputProxy.h"
#include "PerfCounter.h"
#include "RotatingFileHandler.h"
#include "SectionManager.h"
#include "Thread.h"
#include "WinApi.h"
#include "WritableFile.h"
#include "dynamic_func.h"
#include "monitor.h"
#include "stringutil.h"
#include "types.h"
#include "wmiHelper.h"

using std::lock_guard;
using std::make_unique;
using std::map;
using std::mutex;
using std::ostream;
using std::setfill;
using std::setw;
using std::string;
using std::unordered_map;
using std::vector;
using std::chrono::milliseconds;

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

static const char RT_PROTOCOL_VERSION_ENCRYPTED[2] = {'0', '0'};
static const char RT_PROTOCOL_VERSION_UNENCRYPTED[2] = {'9', '9'};

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

// Forward declarations of functions
void listen_tcp_loop(const Environment &env);
void output_data(OutputProxy &out, const Environment &env, bool realtime,
                 bool section_flush,
                 const std::optional<std::string> &remoteIP);
void RunImmediate(const char *mode, int argc, char **argv);

//  .----------------------------------------------------------------------.
//  |                   _        _                          _              |
//  |                  | | _ __ | |_  ___  _ __ _ __   __ _| |___          |
//  |                  | || '_ \| __|/ _ \| '__| '_ \ / _` | / __|         |
//  |                  | || | | | |_|  __/| |  | | | | (_| | \__ \         |
//  |                  |_||_| |_\___|\___||_|  |_| |_|\__,_|_|___/         |
//  |                                                                      |
//  +----------------------------------------------------------------------+
//  | Internal linkage                                                     |
//  '----------------------------------------------------------------------'
namespace {

class UnpackError : public std::runtime_error {
public:
    UnpackError(const std::string &what) : std::runtime_error(what) {}
};

class MillisecondsFormatter : public Formatter {
    void format(ostream &os, const LogRecord &record) override {
        auto tp = record.getTimePoint();
        os << FormattedTimePoint(record.getTimePoint())            //
           << setfill('0') << "."                                  //
           << setw(3) << time_point_part<milliseconds>(tp) << " "  //
           << "[" << record.getLevel() << "] "                     //
           << record.getMessage();
    }
};

// Ugly but there is no (?) way to pass these as parameters to the Windows
// service stuff. At least, let us *not* make this yet another global variable
// and access them from other compilation units...
const WinApi s_winapi;
bool supportIPv6() {
    INT iNuminfo = 0;
    DWORD bufferSize = 0;
    std::vector<BYTE> protocolInfo;
    INT iErrno = NO_ERROR;
    LPWSAPROTOCOL_INFOW lpProtocolInfo = nullptr;

    // WSCEnumProtocols is broken (nice!). You *must* call it 1st time with null
    // buffer & bufferSize 0. Otherwise it will corrupt your heap in case the
    // necessary buffer size exceeds your allocated buffer. Do never ever trust
    // Microsoft WinAPI documentation!
    while ((iNuminfo = s_winapi.WSCEnumProtocols(nullptr, lpProtocolInfo,
                                                 &bufferSize, &iErrno)) ==
           SOCKET_ERROR) {
        if (iErrno == WSAENOBUFS) {
            protocolInfo.resize(bufferSize, 0);
            lpProtocolInfo =
                reinterpret_cast<LPWSAPROTOCOL_INFOW>(protocolInfo.data());
        } else {
            std::cerr << "WSCEnumProtocols failed with error: " << iErrno
                      << std::endl;
            WSACleanup();
            exit(1);
        }
    }

    for (INT i = 0; i < iNuminfo; ++i) {
        if (lpProtocolInfo[i].iAddressFamily == AF_INET6) return true;
    }

    return false;
}

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
    OnlyFromConfigurable only_from;

    GlobalConfig(const Environment &env)
        : parser(env)
        , port(parser, "global", "port", 6556, s_winapi)
        , realtime_port(parser, "global", "realtime_port", 6559, s_winapi)
        , realtime_timeout(parser, "global", "realtime_timeout", 90, s_winapi)
        , crash_debug(parser, "global", "crash_debug", false, s_winapi)
        , section_flush(parser, "global", "section_flush", true, s_winapi)
        , encrypted(parser, "global", "encrypted", false, s_winapi)
        , encrypted_rt(parser, "global", "encrypted_rt", true, s_winapi)
        , support_ipv6(parser, "global", "ipv6", supportIPv6(), s_winapi)
        , passphrase(parser, "global", "passphrase", "", s_winapi)
        , only_from(parser, "global", "only_from", s_winapi) {}
} * s_config;

SectionManager *s_sections;

}  // namespace

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

// Thread relevant variables
volatile bool g_should_terminate = false;

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

template <typename T>
bool in_set(const T &val, const std::set<T> &test_set) {
    return test_set.find(val) != test_set.end();
}

void foreach_enabled_section(bool realtime,
                             const std::function<void(Section *)> &func) {
    for (auto &section : s_sections->sections()) {
        if ((realtime &&
             s_sections->realtimeSectionEnabled(section->configName())) ||
            (!realtime && s_sections->sectionEnabled(section->configName()))) {
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

char *gszServiceName = (char *)SERVICE_NAME;
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
            s_winapi.SetServiceStatus(serviceStatusHandle, &serviceStatus);
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

    s_winapi.SetServiceStatus(serviceStatusHandle, &serviceStatus);
}

void WINAPI ServiceMain(DWORD, char *[]) {
    // initialise service status
    serviceStatus.dwServiceType = SERVICE_WIN32_OWN_PROCESS;
    serviceStatus.dwCurrentState = SERVICE_STOPPED;
    serviceStatus.dwControlsAccepted = 0;
    serviceStatus.dwWin32ExitCode = NO_ERROR;
    serviceStatus.dwServiceSpecificExitCode = NO_ERROR;
    serviceStatus.dwCheckPoint = 0;
    serviceStatus.dwWaitHint = 0;

    serviceStatusHandle = s_winapi.RegisterServiceCtrlHandler(
        gszServiceName, ServiceControlHandler);

    if (serviceStatusHandle) {
        // service is starting
        serviceStatus.dwCurrentState = SERVICE_START_PENDING;
        s_winapi.SetServiceStatus(serviceStatusHandle, &serviceStatus);

        // Service running
        serviceStatus.dwControlsAccepted |=
            (SERVICE_ACCEPT_STOP | SERVICE_ACCEPT_SHUTDOWN);
        serviceStatus.dwCurrentState = SERVICE_RUNNING;
        s_winapi.SetServiceStatus(serviceStatusHandle, &serviceStatus);

        monitor::EnableHealthMonitor = true;  // service may be restarted
        RunImmediate("service", 0, NULL);

        // service is now stopped
        serviceStatus.dwControlsAccepted &=
            ~(SERVICE_ACCEPT_STOP | SERVICE_ACCEPT_SHUTDOWN);
        serviceStatus.dwCurrentState = SERVICE_STOPPED;
        s_winapi.SetServiceStatus(serviceStatusHandle, &serviceStatus);
    }
}

void RunService() {
    SERVICE_TABLE_ENTRY serviceTable[] = {{gszServiceName, ServiceMain},
                                          {0, 0}};

    s_winapi.StartServiceCtrlDispatcher(serviceTable);
}

void InstallService() {
    SC_HANDLE serviceControlManager =
        s_winapi.OpenSCManager(0, 0, SC_MANAGER_CREATE_SERVICE);

    if (serviceControlManager) {
        char path[_MAX_PATH + 1] = {0};
        if (s_winapi.GetModuleFileName(0, path,
                                       sizeof(path) / sizeof(path[0])) > 0) {
            const auto quoted_path = std::string{"\""} + path + "\"";
            ServiceHandle service{
                s_winapi.CreateService(serviceControlManager, gszServiceName,
                                       gszServiceName, SERVICE_ALL_ACCESS,
                                       SERVICE_WIN32_OWN_PROCESS,
                                       SERVICE_AUTO_START, SERVICE_ERROR_IGNORE,
                                       quoted_path.c_str()),
                s_winapi};
            if (service) {
                std::cout << SERVICE_NAME << " Installed Successfully"
                          << std::endl;
            } else {
                const DWORD lastError = s_winapi.GetLastError();
                if (lastError == ERROR_SERVICE_EXISTS) {
                    std::cout << SERVICE_NAME << " Already Exists."
                              << std::endl;
                } else {
                    std::cout << SERVICE_NAME
                              << " Was not Installed Successfully. Error Code "
                              << lastError << std::endl;
                }
            }
        }
    }
}

void UninstallService() {
    ServiceHandle serviceControlManager{
        s_winapi.OpenSCManager(0, 0, SC_MANAGER_CONNECT), s_winapi};

    if (serviceControlManager) {
        ServiceHandle service{
            s_winapi.OpenService(serviceControlManager.get(), gszServiceName,
                                 SERVICE_QUERY_STATUS | DELETE),
            s_winapi};
        if (service) {
            SERVICE_STATUS serviceStatus;
            if (s_winapi.QueryServiceStatus(service.get(), &serviceStatus)) {
                while (in_set(serviceStatus.dwCurrentState,
                              {SERVICE_RUNNING, SERVICE_STOP_PENDING})) {
                    if (serviceStatus.dwCurrentState == SERVICE_STOP_PENDING) {
                        // wait for the wait-hint but no less than 1 second and
                        // no more than 10
                        DWORD waitTime = serviceStatus.dwWaitHint / 10;
                        waitTime =
                            std::max(1000UL, std::min(waitTime, 10000UL));
                        s_winapi.Sleep(waitTime);
                        if (!s_winapi.QueryServiceStatus(service.get(),
                                                         &serviceStatus)) {
                            break;
                        }
                    } else {
                        if (s_winapi.ControlService(service.get(),
                                                    SERVICE_CONTROL_STOP,
                                                    &serviceStatus) == 0) {
                            break;
                        }
                    }
                }

                if (serviceStatus.dwCurrentState == SERVICE_STOPPED) {
                    if (s_winapi.DeleteService(service.get()))
                        std::cout << SERVICE_NAME << " Removed Successfully"
                                  << std::endl;
                    else {
                        const DWORD dwError = s_winapi.GetLastError();
                        if (dwError == ERROR_ACCESS_DENIED)
                            std::cout << "Access Denied While trying to "
                                         "Remove "
                                      << SERVICE_NAME << std::endl;
                        else if (dwError == ERROR_INVALID_HANDLE)
                            std::cout << "Handle invalid while trying to "
                                         "Remove "
                                      << SERVICE_NAME << std::endl;
                        else if (dwError == ERROR_SERVICE_MARKED_FOR_DELETE)
                            std::cout << SERVICE_NAME
                                      << " already marked for deletion"
                                      << std::endl;
                    }
                } else {
                    std::cout << SERVICE_NAME << " is still Running."
                              << std::endl;
                }
            }
        }
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
    if (0 != s_winapi.WSAStartup(MAKEWORD(2, 0), &wsa)) {
        std::cerr << "Cannot initialize winsock." << std::endl;
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

    s_winapi.WaitForMultipleObjects(thread_handles.size(), &thread_handles[0],
                                    TRUE, 5000);
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
    std::cerr
        << "Usage: \n"
        << "check_mk_agent version         -- show version " << CHECK_MK_VERSION
        << " and exit\n"
        << "check_mk_agent install         -- install as Windows NT service "
        << "Check_Mk_Agent\n"
        << "check_mk_agent remove          -- remove Windows NT service\n"
        << "check_mk_agent adhoc           -- open TCP port " << *s_config->port
        << " and answer "
        << "request until killed\n"
        << "check_mk_agent test            -- test output of plugin, do not "
        << "open TCP port\n"
        << "check_mk_agent file FILENAME   -- write output of plugin into "
        << "file, do not open TCP port\n"
        << "check_mk_agent debug           -- similar to test, but with lots "
        << "of debug output\n"
        << "check_mk_agent showconfig      -- shows the effective "
        << "configuration used (currently incomplete)" << std::endl;
    exit(1);
}

void outputFileBase(const Environment &env, FILE *file) {
    FileOutputProxy dummy(file);
    output_data(dummy, env, false, *s_config->section_flush, std::nullopt);
}

void do_debug(const Environment &env) {
    Logger *logger = Logger::getLogger("winagent");
    const auto saveLevel = logger->getLevel();
    logger->setLevel(LogLevel::notice);

    outputFileBase(env, stdout);

    logger->setLevel(saveLevel);
}

void do_test(const Environment &env) {
    Notice(Logger::getLogger("winagent")) << "Started in test mode.";
    outputFileBase(env, stdout);
}

void do_file(const Environment &env, const char *filename) {
    std::unique_ptr<FILE, decltype(&fclose)> file(fopen(filename, "w"), fclose);

    if (!file) {
        std::cerr << "Cannot open " << filename << " for writing." << std::endl;
        exit(1);
    }

    outputFileBase(env, file.get());
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

DWORD WINAPI realtime_check_func(void *data_in) {
    ThreadData *data = (ThreadData *)data_in;
    Logger *logger = Logger::getLogger("winagent");

    try {
        sockaddr_storage current_address;
        std::string current_ip;
        SocketHandle current_socket(s_winapi);

        std::unique_ptr<BufferedSocketProxy> out;
        if (*s_config->encrypted_rt) {
            out.reset(new EncryptingBufferedSocketProxy(
                INVALID_SOCKET, *s_config->passphrase, logger, s_winapi));
        } else {
            out.reset(
                new BufferedSocketProxy(INVALID_SOCKET, logger, s_winapi));
        }

        timeval before;
        gettimeofday(&before, 0);
        while (!data->terminate) {
            timeval now;
            gettimeofday(&now, 0);
            long duration = (now.tv_sec - before.tv_sec) * 1000 +
                            (now.tv_usec - before.tv_usec) / 1000;
            if (duration < 1000) {
                s_winapi.Sleep(1000 - duration);
            }
            gettimeofday(&before, 0);

            lock_guard<mutex>(data->mutex);
            // adhere to the configured timeout
            if ((time(NULL) < data->push_until) && !data->terminate) {
                // if a new request was made, reestablish the connection
                if (data->new_request) {
                    data->new_request = false;
                    // (re-)establish connection if necessary
                    current_socket.reset();
                    out->setSocket(INVALID_SOCKET);

                    current_address = data->last_address;
                    if (current_address.ss_family != 0) {
                        int sockaddr_size = 0;
                        if (current_address.ss_family == AF_INET) {
                            sockaddr_in *addrv4 =
                                (sockaddr_in *)&current_address;
                            addrv4->sin_port =
                                s_winapi.htons(*s_config->realtime_port);
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
                                temp.sin_port =
                                    s_winapi.htons(*s_config->realtime_port);
                                temp.sin_family = AF_INET;
                                memcpy(&temp.sin_addr.S_un.S_addr,
                                       addrv6->sin6_addr.u.Byte + 12, 4);

                                current_address.ss_family = AF_INET;
                                sockaddr_size = sizeof(sockaddr_in);
                                memcpy(&current_address, &temp, sockaddr_size);
                            } else {
                                addrv6->sin6_port =
                                    s_winapi.htons(*s_config->realtime_port);
                                sockaddr_size = sizeof(sockaddr_in6);
                            }
                        }
                        current_ip =
                            IPAddrToString(current_address, logger, s_winapi);
                        Debug(logger) << "current_ip = " << current_ip;
                        current_socket.reset(
                            s_winapi.socket(current_address.ss_family,
                                            SOCK_DGRAM, IPPROTO_UDP));
                        if (!current_socket) {
                            Emergency(logger) << "failed to establish socket: "
                                              << s_winapi.WSAGetLastError();
                            return 1;
                        }
                        if (s_winapi.connect(current_socket.get(),
                                             (const sockaddr *)&current_address,
                                             sockaddr_size) == SOCKET_ERROR) {
                            Emergency(logger) << "failed to connect: "
                                              << s_winapi.WSAGetLastError();
                            current_socket.reset();
                        }
                        out->setSocket(current_socket.get());
                    }
                }

                // send data
                if (current_socket) {
                    // send data
                    s_winapi.SetEnvironmentVariable("REMOTE_HOST",
                                                    current_ip.c_str());
                    s_winapi.SetEnvironmentVariable("REMOTE",
                                                    current_ip.c_str());
                    char timestamp[11];
                    snprintf(timestamp, 11, "%" PRIdtime, time(NULL));

                    // The realtime mode uses the following "protocol"
                    // - encrypted output is indicated by "00"
                    // - unencrypted output is indicated by "99"
                    // After the encryption indicator, a 10 bytes timestamp is
                    // written, followed by the actual un/encrypted content
                    if (*s_config->encrypted) {
                        out->writeBinary(RT_PROTOCOL_VERSION_ENCRYPTED, 2);
                    } else {
                        out->writeBinary(RT_PROTOCOL_VERSION_UNENCRYPTED, 2);
                    }
                    out->writeBinary(timestamp, 10);
                    output_data(*out, data->env, true, false,
                                std::optional(current_ip));
                }
            }
        }

        return 0;
    } catch (const std::exception &e) {
        Alert(logger) << "failed to run realtime check: " << e.what();
        return 1;
    }
}

//#define WITH_MEMORY_OVERFLOW
#if defined(WITH_MEMORY_OVERFLOW)
std::vector<char *> vec;
#endif
void do_adhoc(const Environment &env) {
    g_should_terminate = false;
    Logger *logger = Logger::getLogger("winagent");
    ListenSocket sock(*s_config->port, *s_config->only_from,
                      *s_config->support_ipv6, logger, s_winapi);

    std::cout << "Listening for TCP connections (";

    if (sock.supportsIPV6()) {
        if (sock.supportsIPV4())
            std::cout << "IPv4 and IPv6";
        else
            std::cout << "IPv6 only";
    } else {
        std::cout << "IPv4 only";
    }
    std::cout << ") on port " << *s_config->port << std::endl;

    std::cout << "realtime monitoring ";
    if (s_sections->useRealtimeMonitoring())
        std::cout << "active\n";
    else
        std::cout << "inactive\n";

    std::cout << "Close window or press Ctrl-C to exit" << std::endl;

    // Run all ASYNC scripts on startup, so that their data is available on
    // the first query of a client. Obviously, this slows down the agent
    // startup...
    // This procedure is mandatory, since we want to prevent missing agent
    // sections
    foreach_enabled_section(false,
                            [](Section *section) { section->startIfAsync(); });
    foreach_enabled_section(
        false, [](Section *section) { section->waitForCompletion(); });

    ThreadData thread_data{env, logger};
    Thread realtime_checker(realtime_check_func, thread_data, s_winapi);

    if (s_sections->useRealtimeMonitoring()) {
        thread_data.terminate = false;
        realtime_checker.start();
    }

    std::unique_ptr<BufferedSocketProxy> out;

    if (*s_config->encrypted) {
        out.reset(new EncryptingBufferedSocketProxy(
            INVALID_SOCKET, *s_config->passphrase, logger, s_winapi));
    } else {
        out.reset(new BufferedSocketProxy(INVALID_SOCKET, logger, s_winapi));
    }

    while (!g_should_terminate) {
        SocketHandle connection = std::move(sock.acceptConnection());
        if (connection) {
            out->setSocket(connection.get());

            // The adhoc mode uses the following "protocol"
            // - encrypted output is indicated by "00"
            // - unencrypted output MUST start with "<<<"
            //   These are usually generated by one the agent sections
            if (*s_config->encrypted) {
                out->writeBinary(RT_PROTOCOL_VERSION_ENCRYPTED, 2);
            }

            const sockaddr_storage addr = sock.address(connection.get());
            std::string ip_hr = IPAddrToString(addr, logger, s_winapi);
            Debug(logger) << "Accepted client connection from " << ip_hr << ".";
            {  // limit lifetime of mutex lock
                lock_guard<mutex>(thread_data.mutex);
                thread_data.new_request = true;
                thread_data.last_address = sock.address(connection.get());
                thread_data.push_until =
                    time(NULL) + *s_config->realtime_timeout;
            }

            s_winapi.SetEnvironmentVariable("REMOTE_HOST", ip_hr.c_str());
            s_winapi.SetEnvironmentVariable("REMOTE", ip_hr.c_str());
            try {
                output_data(*out, env, false, *s_config->section_flush,
                            std::optional(ip_hr));
            } catch (const std::exception &e) {
                Alert(Logger::getLogger("winagent"))
                    << "unhandled exception: " << e.what();
            }
        }

        if (monitor::EnableHealthMonitor) {
#if defined(WITH_MEMORY_OVERFLOW)
            // code to overflow memory
            char *b = new char[10'000'000];
            memset(b, 0, 10'000'000);
            vec.push_back(b);
            Error(logger) << "memory vector is " << vec.size();
#endif
            if (!monitor::IsAgentHealthy()) {
                Error(logger)
                    << "MEMORY IS OVER for process " << ::GetCurrentProcessId();
                RestartService();
            }
        }
    }

    if (realtime_checker.wasStarted()) {
        thread_data.terminate = true;
    }

    stop_threads();

    if (realtime_checker.wasStarted()) {
        int res = realtime_checker.join();
        Debug(logger) << "Realtime check thread ended with error code " << res
                      << ".";
    }

    s_winapi.WSACleanup();
}

void output_data(OutputProxy &out, const Environment &env, bool realtime,
                 bool section_flush,
                 const std::optional<std::string> &remoteIP) {
    // make sure, output of numbers is not localized
    setlocale(LC_ALL, "C");

    // allow async sections to prepare their data
    foreach_enabled_section(realtime,
                            [](Section *section) { section->startIfAsync(); });

    // output sections
    foreach_enabled_section(
        realtime, [&out, &env, section_flush, &remoteIP](Section *section) {
            std::stringstream str;
            section->produceOutput(str, remoteIP);
            out.output("%s", str.str().c_str());
            if (section_flush) out.flush(false);
        });

    // Send remaining data in out buffer
    out.flush(true);
}

void show_version() {
    std::cout << "Check_MK_Agent version " << CHECK_MK_VERSION << std::endl;
}

void show_config() { s_config->parser.outputConfigurables(std::cout); }

namespace {

const char *integrityErrorMsg =
    "There was an error on unpacking the Check_MK-Agent package: File "
    "integrity is broken.\n"
    "The file might have been installed partially!";

const char *uninstallInfo =
    "REM * If you want to uninstall the plugins which were installed "
    "during the\n"
    "REM * last 'check_mk_agent.exe unpack' command, just execute this "
    "script\n\n";

std::string managePluginPath(const std::string &filePath,
                             const Environment &env) {
    // Extract basename and dirname from path
    auto pos = filePath.find_last_of("/");
    const std::string basename =
        pos == std::string::npos ? filePath : filePath.substr(pos + 1);
    const std::string dirname =
        pos == std::string::npos ? "" : filePath.substr(0, pos);
    std::string pluginPath{env.agentDirectory() + "\\"};

    if (!dirname.empty()) {
        pluginPath += dirname;
        s_winapi.CreateDirectory(pluginPath.c_str(), nullptr);
        pluginPath += "\\";
    }

    pluginPath += basename;

    return pluginPath;
}

template <typename LengthT>
std::vector<BYTE> readData(std::ifstream &ifs, bool zeroTerminate,
                           const std::function<void(LengthT)> &check =
                               [](LengthT) {}) {
    LengthT length = 0;
    ifs.read(reinterpret_cast<char *>(&length), sizeof(length));
    if (!ifs.good()) {
        return {};
    }
    check(length);
    size_t count = length;
    if (zeroTerminate) {
        count += 1;
    }
    std::vector<BYTE> dataBuffer(count, 0);
    ifs.read(reinterpret_cast<char *>(dataBuffer.data()), length);

    if (!ifs.good()) {
        throw UnpackError(integrityErrorMsg);
    }

    if (zeroTerminate) {
        dataBuffer[length] = '\0';
    }

    return dataBuffer;
}

void extractPlugin(const Environment &env, std::ifstream &ifs,
                   WritableFile &uninstallFile) {
    // Read Filename
    const auto filepath = readData<BYTE>(ifs, true);

    if (!ifs.good()) {
        if (ifs.eof()) {
            return;
        } else {
            throw UnpackError(integrityErrorMsg);
        }
    }
    const std::string filePath(reinterpret_cast<char const *>(filepath.data()));
    const auto checkPluginSize = [&filePath](const int length) {
        // Maximum plugin size is 20 MB
        if (length > 20 * 1024 * 1024) {
            throw UnpackError("Size of plugin '" + filePath +
                              "' exceeds 20 MB");
        }
    };
    const auto content = readData<int>(ifs, false, checkPluginSize);
    if (!ifs.good()) {
        throw UnpackError(integrityErrorMsg);
    }
    const auto pluginPath = managePluginPath(filePath, env);
    uninstallFile << "del \"" << pluginPath << "\"\n";

    // TODO: remove custom dirs on uninstall

    // Write plugin
    WritableFile pluginFile(pluginPath, 0, CREATE_NEW, s_winapi);
    pluginFile << content;
}

}  // namespace

void do_unpack_plugins(const char *plugin_filename, const Environment &env) {
    Logger *logger = Logger::getLogger("winagent");
    try {
        std::ifstream ifs(plugin_filename,
                          std::ifstream::in | std::ifstream::binary);
        if (!ifs) {
            throw UnpackError(
                std::string{"Unable to open Check_MK-Agent package "} +
                plugin_filename);
        }

        WritableFile uninstallFile(
            env.agentDirectory() + "\\uninstall_plugins.bat", 0, CREATE_NEW,
            s_winapi);
        uninstallFile << uninstallInfo;

        while (!ifs.eof()) {
            extractPlugin(env, ifs, uninstallFile);
        }

        uninstallFile << "del \"" << env.agentDirectory()
                      << "\\uninstall_plugins.bat\"\n";
    } catch (const std::runtime_error &e) {
        Error(logger) << e.what();
        std::cerr << e.what() << std::endl;
        exit(1);
    }

    try {
        Debug(logger) << "areAllFilesWritable: " << std::boolalpha
                      << areAllFilesWritable(
                             env.agentDirectory(), s_winapi,
                             getDefaultWhitelist(env, s_winapi));
    } catch (const FileError &e) {
        Error(logger) << e.what();
    }
}

void addIPv6Addresses() {
    if (*s_config->support_ipv6) {
        auto &only_from = *s_config->only_from;
        const size_t origSize = only_from.size();
        only_from.reserve(only_from.size() * 2);
        // also add a v4->v6 converted filter
        for (size_t i = 0; i < origSize; ++i) {
            if (!only_from[i].ipv6) {
                only_from.push_back(toIPv6(only_from[i], s_winapi));
            }
        }
        s_config->only_from->shrink_to_fit();
    }
}

void RunImmediate(const char *mode, int argc, char **argv) {
    // base directory structure on current working directory or registered dir
    // (from registry)?
    bool use_cwd = !strcmp(mode, "adhoc") || !strcmp(mode, "test");
    Logger *logger = Logger::getLogger("winagent");
    Environment env(use_cwd, strcmp(mode, "test") == 0, logger, s_winapi);

    const std::string logFilename = env.logDirectory() + "\\agent.log";

    if (strcmp(mode, "debug")) {  // if not debugging, use log file
        // TODO: Make logfile rotation parameters configurable
        logger->setHandler(std::make_unique<RotatingFileHandler>(
            logFilename, std::make_unique<FileRotationApi>(),
            8388608 /* 8 MB */, 5));
    }

    if (Handler *handler = logger->getHandler()) {
        handler->setFormatter(make_unique<MillisecondsFormatter>());
    }

    s_config = new GlobalConfig(env);
    s_sections = new SectionManager(s_config->parser, s_config->only_from,
                                    logger, s_winapi);

    // careful: destroying the section manager destroys the wmi helpers created
    // for
    // wmi sections, which in turn releases COM objects. This needs to happen
    // before
    // cleanup of globals, otherwise a global CoUninitialize() may have been
    // called
    // and then those releases will fail
    OnScopeExit selectionsFree([]() {
        delete s_sections;
        s_sections = nullptr;
    });

    s_config->parser.readSettings();

    if (!*s_config->crash_debug) {  // default level already LogLevel::debug
        logger->setLevel(LogLevel::warning);
    }

    addIPv6Addresses();
    s_sections->loadDynamicSections();
    s_sections->emitConfigLoaded();

    if (!strcmp(mode, "test"))
        do_test(env);
    else if (!strcmp(mode, "file")) {
        if (argc < 1) {
            std::cerr << "Please specify the name of an output file."
                      << std::endl;
            exit(1);
        }
        do_file(env, argv[0]);
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

inline LONG WINAPI exception_handler(LPEXCEPTION_POINTERS ptrs) {
    return CrashHandler(Logger::getLogger("winagent"), s_winapi)
        .handleCrash(ptrs);
}

int main(int argc, char **argv) {
    wsa_startup();

    s_winapi.SetUnhandledExceptionFilter(exception_handler);

    s_winapi.SetConsoleCtrlHandler((PHANDLER_ROUTINE)ctrl_handler, TRUE);

    if ((argc > 2) && (strcmp(argv[1], "file") && strcmp(argv[1], "unpack"))) {
        // need to parse config so we can display defaults in usage
        bool use_cwd = true;
        Environment env(use_cwd, false, Logger::getLogger("winagent"),
                        s_winapi);
        s_config = new GlobalConfig(env);
        usage();
    }

    if (argc <= 1)
        RunService();
    else {
        RunImmediate(argv[1], argc - 2, argv + 2);
    }
}
