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

#include "Environment.h"
#include <windows.h>
#include <cassert>
#include <stdexcept>
#include "LoggerAdaptor.h"
#include "stringutil.h"

using namespace std;

// technically this is the limit for path names on windows, practically few
// applications and not
// even all apis support more than 260
static const int MAX_PATH_UNICODE = 32767;

Environment *Environment::s_Instance = nullptr;

Environment::Environment(bool use_cwd, const LoggerAdaptor &logger)
    : _hostname(), _logger(logger) {
    determineDirectories(use_cwd);

    char buffer[256];
    if (gethostname(buffer, sizeof(buffer)) == 0) {
        _hostname = buffer;
    }
    if (s_Instance == nullptr) {
        s_Instance = this;
    }
}

Environment::~Environment() {
    if (s_Instance == this) {
        s_Instance = nullptr;
    }
}

Environment *Environment::instance() { return s_Instance; }

void Environment::getAgentDirectory(char *buffer, int size, bool use_cwd) {
    buffer[0] = 0;

    HKEY key;
    DWORD ret = -1;

    if (!use_cwd) {
        ret =
            RegOpenKeyEx(HKEY_LOCAL_MACHINE,
                         "SYSTEM\\CurrentControlSet\\Services\\check_mk_agent",
                         0, KEY_READ, &key);
    }

    if (ret == ERROR_SUCCESS) {
        DWORD dsize = size;
        if (ERROR_SUCCESS == RegQueryValueEx(key, "ImagePath", NULL, NULL,
                                             (BYTE *)buffer, &dsize)) {
            char *end = buffer + strlen(buffer);
            // search backwards for backslash
            while (end > buffer && *end != '\\') end--;
            *end =
                0;  // replace \ with string end => get directory of executable

            // Handle case where name is quoted with double quotes.
            // This is reported to happen on some 64 Bit systems when spaces
            // are in the directory name.
            if (*buffer == '"') {
                memmove(buffer, buffer + 1, strlen(buffer));
            }
        }
        RegCloseKey(key);
    } else {
        // If the agent is not installed as service, simply
        // assume the current directory to be the agent
        // directory (for test and adhoc mode)
        strncpy(buffer, _current_directory.c_str(), size);
        if (buffer[strlen(buffer) - 1] == '\\')  // Remove trailing backslash
            buffer[strlen(buffer) - 1] = 0;
    }
}

string Environment::assignDirectory(const char *name) {
    string result(_agent_directory + "\\" + name);
    if (!CreateDirectoryA(result.c_str(), NULL)) {
        if (GetLastError() != ERROR_ALREADY_EXISTS) {
            _logger.crashLog("Failed to create directory %s: %s (%lu)", name,
                      get_win_error_as_string().c_str(), GetLastError());
        }
    }
    return result;
}

void Environment::determineDirectories(bool use_cwd) {
    char *buffer = new char[MAX_PATH_UNICODE];
    try {
        ::GetCurrentDirectoryA(MAX_PATH_UNICODE, buffer);
        _current_directory = buffer;
        getAgentDirectory(buffer, MAX_PATH_UNICODE, use_cwd);
        _agent_directory = buffer;

        delete[] buffer;
    } catch (...) {
        delete[] buffer;
        throw;
    }

    _plugins_directory = assignDirectory("plugins");
    _config_directory = assignDirectory("config");
    _local_directory = assignDirectory("local");
    _spool_directory = assignDirectory("spool");
    _state_directory = assignDirectory("state");
    _temp_directory = assignDirectory("temp");
    _log_directory = assignDirectory("log");
    _bin_directory = _agent_directory + "\\bin";  // not created if missing

    _logwatch_statefile = _state_directory + "\\logstate.txt";
    _eventlog_statefile = _state_directory + "\\eventstate.txt";

    // Set these directories as environment variables. Some scripts might use
    // them...
    SetEnvironmentVariable("MK_PLUGINSDIR", _plugins_directory.c_str());
    SetEnvironmentVariable("MK_CONFDIR", _config_directory.c_str());
    SetEnvironmentVariable("MK_LOCALDIR", _local_directory.c_str());
    SetEnvironmentVariable("MK_SPOOLDIR", _spool_directory.c_str());
    SetEnvironmentVariable("MK_STATEDIR", _state_directory.c_str());
    SetEnvironmentVariable("MK_TEMPDIR", _temp_directory.c_str());
    SetEnvironmentVariable("MK_LOGDIR", _log_directory.c_str());
}

bool Environment::isWinNt() {
    OSVERSIONINFO osv;
    osv.dwOSVersionInfoSize = sizeof(OSVERSIONINFO);
    ::GetVersionEx(&osv);

    return (osv.dwPlatformId == VER_PLATFORM_WIN32_NT);
}

uint16_t Environment::winVersion() {
    OSVERSIONINFO osv;
    osv.dwOSVersionInfoSize = sizeof(OSVERSIONINFO);
    ::GetVersionEx(&osv);

    return ((osv.dwMajorVersion & 0xFF) << 8) | (osv.dwMinorVersion & 0xFF);
}
