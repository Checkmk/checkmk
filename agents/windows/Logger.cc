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

#include <windows.h>
#include <cstdarg>
#include <cstdio>
#include <string>

#include "Logger.h"

Logger::Logger()
    : _verbose_mode(false)
    , _found_crash(false)
    , _crashlogMutex(CreateMutex(NULL, FALSE, NULL))
    , _crash_log("")
    , _connection_log("")
    , _success_log("")
    , _connectionlog_file(INVALID_HANDLE_VALUE)
    , _crashlog_start({0}) {}

void Logger::verbose(const char *format, ...) const {
    if (!_verbose_mode) return;

    va_list ap;
    va_start(ap, format);
    printf("DEBUG: ");
    vprintf(format, ap);
    va_end(ap);
    printf("\n");
    fflush(stdout);
}

// .-----------------------------------------------------------------------.
// |       ____               _       ____       _                         |
// |      / ___|_ __ __ _ ___| |__   |  _ \  ___| |__  _   _  __ _         |
// |     | |   | '__/ _` / __| '_ \  | | | |/ _ \ '_ \| | | |/ _` |        |
// |     | |___| | | (_| \__ \ | | | | |_| |  __/ |_) | |_| | (_| |        |
// |      \____|_|  \__,_|___/_| |_| |____/ \___|_.__/ \__,_|\__, |        |
// |                                                         |___/         |
// '-----------------------------------------------------------------------'

void Logger::openCrashLog(const std::string &log_directory) {
    struct stat buf;

    lockCrashLog();

    _crash_log.reserve(log_directory.size() + 11);
    _crash_log = log_directory + "\\crash.log";
    _connection_log.reserve(log_directory.size() + 16);
    _connection_log = log_directory + "\\connection.log";
    _success_log.reserve(log_directory.size() + 13);
    _success_log = log_directory + "\\success.log";

    // rename left over log if exists (means crash found)
    if (0 == stat(_connection_log.c_str(), &buf)) {
        // rotate to up to 9 crash log files
        char rotate_path_from[256];
        char rotate_path_to[256];
        for (int i = 9; i >= 1; i--) {
            snprintf(rotate_path_to, sizeof(rotate_path_to), "%s\\crash-%d.log",
                     log_directory.c_str(), i);
            if (i > 1)
                snprintf(rotate_path_from, sizeof(rotate_path_from),
                         "%s\\crash-%d.log", log_directory.c_str(), i - 1);
            else
                snprintf(rotate_path_from, sizeof(rotate_path_from),
                         "%s\\crash.log", log_directory.c_str());
            unlink(rotate_path_to);
            rename(rotate_path_from, rotate_path_to);
        }
        rename(_connection_log.c_str(), _crash_log.c_str());
        _found_crash = true;
    }

    // Threads are not allowed to access the crashLog
    _connectionlog_file = CreateFile(TEXT(_connection_log.c_str()),
                                      GENERIC_WRITE,    // open for writing
                                      FILE_SHARE_READ,  // do not share
                                      NULL,             // no security
                                      CREATE_ALWAYS,    // existing file only
                                      FILE_ATTRIBUTE_NORMAL,  // normal file
                                      NULL);
    gettimeofday(&_crashlog_start, 0);
    time_t now = time(0);
    struct tm *t = localtime(&now);
    char timestamp[64];
    strftime(timestamp, sizeof(timestamp), "%b %d %H:%M:%S", t);
    crashLog("Opened crash log at %s.", timestamp);
    unlockCrashLog();
}

void Logger::closeCrashLog() const {
    if (_connectionlog_file) {
        lockCrashLog();
        crashLog("Closing crash log (no crash this time)");

        CloseHandle(_connectionlog_file);
        DeleteFile(_success_log.c_str());
        MoveFile(_connection_log.c_str(), _success_log.c_str());
        unlockCrashLog();
    }
}

void Logger::printCrashLog(std::ostream &out) {
    out << "[[[Check_MK Agent]]]\n";
    if (_found_crash) {
        lockCrashLog();
        out << "C Check_MK Agent crashed\n";
        FILE *f = fopen(_crash_log.c_str(), "r");
        char line[1024];
        while (0 != fgets(line, sizeof(line), f)) {
            out << "W " << line;
        }
        unlockCrashLog();
        fclose(f);
        _found_crash = false;
    }
}

void Logger::crashLog(const char *format, ...) const {
    lockCrashLog();
    struct timeval tv;

    char buffer[1024];
    if (_connectionlog_file != INVALID_HANDLE_VALUE) {
        gettimeofday(&tv, 0);
        long int ellapsed_usec = tv.tv_usec - _crashlog_start.tv_usec;
        long int ellapsed_sec = tv.tv_sec - _crashlog_start.tv_sec;
        if (ellapsed_usec < 0) {
            ellapsed_usec += 1000000;
            ellapsed_sec--;
        }

        DWORD dwBytesWritten = 0;
        snprintf(buffer, sizeof(buffer), "%ld.%06ld ", ellapsed_sec,
                 ellapsed_usec);
        DWORD dwBytesToWrite = (DWORD)strlen(buffer);
        WriteFile(_connectionlog_file, buffer, dwBytesToWrite, &dwBytesWritten,
                  NULL);

        va_list ap;
        va_start(ap, format);
        vsnprintf(buffer, sizeof(buffer), format, ap);
        va_end(ap);

        dwBytesToWrite = (DWORD)strlen(buffer);
        WriteFile(_connectionlog_file, buffer, dwBytesToWrite, &dwBytesWritten,
                  NULL);

        WriteFile(_connectionlog_file, "\r\n", 2, &dwBytesWritten, NULL);
        FlushFileBuffers(_connectionlog_file);
    }
    unlockCrashLog();
}

void Logger::lockCrashLog() const {
    ::WaitForSingleObject(_crashlogMutex, INFINITE);
}

void Logger::unlockCrashLog() const {
    ::ReleaseMutex(_crashlogMutex);
}

std::array<std::string, 3> Logger::getLogFilenames() const {
    return { _crash_log, _connection_log, _success_log };
}
