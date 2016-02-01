// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2015             mk@mathias-kettner.de |
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

#include "logging.h"
#include <sys/stat.h>
#include <sys/time.h>
#include <windows.h>
#include <cstdarg>
#include <cstdio>
#include <string>

extern bool verbose_mode;
extern char g_crash_log[256];
extern char g_connection_log[256];
extern char g_success_log[256];
extern bool g_found_crash;
extern HANDLE g_crashlogMutex;

// Pointer to open crash log file, if crash_debug = on
HANDLE g_connectionlog_file = INVALID_HANDLE_VALUE;
struct timeval g_crashlog_start;

void verbose(const char *format, ...) {
    if (!verbose_mode) return;

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

void open_crash_log(const std::string &log_directory) {
    struct stat buf;

    WaitForSingleObject(g_crashlogMutex, INFINITE);

    snprintf(g_crash_log, sizeof(g_crash_log), "%s\\crash.log",
             log_directory.c_str());
    snprintf(g_connection_log, sizeof(g_connection_log), "%s\\connection.log",
             log_directory.c_str());
    snprintf(g_success_log, sizeof(g_success_log), "%s\\success.log",
             log_directory.c_str());

    // rename left over log if exists (means crash found)
    if (0 == stat(g_connection_log, &buf)) {
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
        rename(g_connection_log, g_crash_log);
        g_found_crash = true;
    }

    // Threads are not allowed to access the crash_log
    g_connectionlog_file = CreateFile(TEXT(g_connection_log),
                                      GENERIC_WRITE,    // open for writing
                                      FILE_SHARE_READ,  // do not share
                                      NULL,             // no security
                                      CREATE_ALWAYS,    // existing file only
                                      FILE_ATTRIBUTE_NORMAL,  // normal file
                                      NULL);
    gettimeofday(&g_crashlog_start, 0);
    time_t now = time(0);
    struct tm *t = localtime(&now);
    char timestamp[64];
    strftime(timestamp, sizeof(timestamp), "%b %d %H:%M:%S", t);
    crash_log("Opened crash log at %s.", timestamp);
    ReleaseMutex(g_crashlogMutex);
}

void close_crash_log() {
    if (g_connectionlog_file) {
        WaitForSingleObject(g_crashlogMutex, INFINITE);
        crash_log("Closing crash log (no crash this time)");

        CloseHandle(g_connectionlog_file);
        DeleteFile(g_success_log);
        MoveFile(g_connection_log, g_success_log);
        ReleaseMutex(g_crashlogMutex);
    }
}

void crash_log(const char *format, ...) {
    WaitForSingleObject(g_crashlogMutex, INFINITE);
    struct timeval tv;

    char buffer[1024];
    if (g_connectionlog_file != INVALID_HANDLE_VALUE) {
        gettimeofday(&tv, 0);
        long int ellapsed_usec = tv.tv_usec - g_crashlog_start.tv_usec;
        long int ellapsed_sec = tv.tv_sec - g_crashlog_start.tv_sec;
        if (ellapsed_usec < 0) {
            ellapsed_usec += 1000000;
            ellapsed_sec--;
        }

        DWORD dwBytesWritten = 0;
        snprintf(buffer, sizeof(buffer), "%ld.%06ld ", ellapsed_sec,
                 ellapsed_usec);
        DWORD dwBytesToWrite = (DWORD)strlen(buffer);
        WriteFile(g_connectionlog_file, buffer, dwBytesToWrite, &dwBytesWritten,
                  NULL);

        va_list ap;
        va_start(ap, format);
        vsnprintf(buffer, sizeof(buffer), format, ap);
        va_end(ap);

        dwBytesToWrite = (DWORD)strlen(buffer);
        WriteFile(g_connectionlog_file, buffer, dwBytesToWrite, &dwBytesWritten,
                  NULL);

        WriteFile(g_connectionlog_file, "\r\n", 2, &dwBytesWritten, NULL);
        FlushFileBuffers(g_connectionlog_file);
    }
    ReleaseMutex(g_crashlogMutex);
}
