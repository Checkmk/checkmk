// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#include "Environment.h"
#include <cassert>
#include <cstring>
#include <stdexcept>
#include <vector>
#include "Logger.h"
#include "WinApiInterface.h"
#include "types.h"
#include "win_error.h"

using namespace std;

// technically this is the limit for path names on windows, practically few
// applications and not
// even all apis support more than 260
static const int MAX_PATH_UNICODE = 32767;

Environment *Environment::s_Instance = nullptr;

Environment::Environment(bool use_cwd, bool with_stderr, Logger *logger,
                         const WinApiInterface &winapi)
    : _logger(logger)
    , _winapi(winapi)
    , _hostname(determineHostname())
    , _current_directory(determineCurrentDirectory())
    , _agent_directory(determineAgentDirectory(use_cwd))
    , _plugins_directory(assignDirectory("plugins"))
    , _config_directory(assignDirectory("config"))
    , _local_directory(assignDirectory("local"))
    , _spool_directory(assignDirectory("spool"))
    , _state_directory(assignDirectory("state"))
    , _temp_directory(assignDirectory("temp"))
    , _log_directory(assignDirectory("log"))
    , _bin_directory(_agent_directory + "\\bin")  // not created if missing
    , _logwatch_statefile(_state_directory + "\\logstate.txt")
    , _eventlog_statefile(_state_directory + "\\eventstate.txt")
    , _workers_job_object(_winapi.CreateJobObject(nullptr, "workers_job"),
                          _winapi)
    , _with_stderr(with_stderr) {
    // Set these directories as environment variables. Some scripts might use
    // them...
    _winapi.SetEnvironmentVariable("MK_PLUGINSDIR", _plugins_directory.c_str());
    _winapi.SetEnvironmentVariable("MK_CONFDIR", _config_directory.c_str());
    _winapi.SetEnvironmentVariable("MK_LOCALDIR", _local_directory.c_str());
    _winapi.SetEnvironmentVariable("MK_SPOOLDIR", _spool_directory.c_str());
    _winapi.SetEnvironmentVariable("MK_STATEDIR", _state_directory.c_str());
    _winapi.SetEnvironmentVariable("MK_TEMPDIR", _temp_directory.c_str());
    _winapi.SetEnvironmentVariable("MK_LOGDIR", _log_directory.c_str());

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

string Environment::determineHostname() const {
    const int bufferSize = 256;
    char buffer[bufferSize] = "\0";
    return (_winapi.gethostname(buffer, bufferSize) == 0) ? buffer : "";
}

string Environment::determineCurrentDirectory() const {
    vector<char> buffer(MAX_PATH_UNICODE, '\0');
    const DWORD bytesWritten =
        _winapi.GetCurrentDirectoryA(MAX_PATH_UNICODE, buffer.data());

    if (bytesWritten == 0 || bytesWritten >= MAX_PATH_UNICODE) return "";

    buffer.resize(bytesWritten);
    return {buffer.begin(), buffer.end()};
}

string Environment::determineAgentDirectory(bool use_cwd) const {
    HKEY key = nullptr;
    DWORD ret = -1;

    if (!use_cwd) {
        ret = _winapi.RegOpenKeyEx(
            HKEY_LOCAL_MACHINE,
            "SYSTEM\\CurrentControlSet\\Services\\check_mk_agent", 0, KEY_READ,
            &key);
    }

    HKeyHandle hKey{key, _winapi};

    if (ret == ERROR_SUCCESS) {
        vector<unsigned char> buffer(MAX_PATH_UNICODE, '\0');
        DWORD dsize = MAX_PATH_UNICODE;

        if (ERROR_SUCCESS == _winapi.RegQueryValueEx(hKey.get(), "ImagePath",
                                                     NULL, NULL, buffer.data(),
                                                     &dsize)) {
            buffer.resize(dsize);
            string directory{buffer.begin(), buffer.end()};
            // search backwards for backslash
            size_t found = directory.find_last_of("/\\");
            directory = directory.substr(0, found);

            // Handle case where name is quoted with double quotes.
            // This is reported to happen on some 64 Bit systems when spaces
            // are in the directory name.
            if (directory.front() == '"') {
                directory.erase(directory.begin());
            }

            return directory;
        } else {  // Avoid returning null-filled enormous string upon read
                  // error:
            return "";
        }
    } else {
        // If the agent is not installed as service, simply
        // assume the current directory to be the agent
        // directory (for test and adhoc mode)
        string directory(_current_directory);

        if (directory.back() == '\\')  // Remove trailing backslash
            directory.pop_back();

        return directory;
    }
}

string Environment::assignDirectory(const char *name) const {
    const string result(_agent_directory + "\\" + name);
    if (!_winapi.CreateDirectoryA(result.c_str(), NULL)) {
        const auto lastError = _winapi.GetLastError();
        if (lastError != ERROR_ALREADY_EXISTS) {
            Error(_logger) << "Failed to create directory : " << name << ": "
                           << get_win_error_as_string(_winapi, lastError)
                           << " (" << lastError << ")";
        }
    }
    return result;
}

bool Environment::isWinNt() const {
    OSVERSIONINFO osv;
    osv.dwOSVersionInfoSize = sizeof(OSVERSIONINFO);
    _winapi.GetVersionEx(&osv);

    return (osv.dwPlatformId == VER_PLATFORM_WIN32_NT);
}

uint16_t Environment::winVersion() const {
    OSVERSIONINFO osv;
    osv.dwOSVersionInfoSize = sizeof(OSVERSIONINFO);
    _winapi.GetVersionEx(&osv);

    return ((osv.dwMajorVersion & 0xFF) << 8) | (osv.dwMinorVersion & 0xFF);
}
