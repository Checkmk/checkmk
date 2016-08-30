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
// tails. You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

// Needed for localtime_r
#define _XOPEN_SOURCE 500

#include <pthread.h>
#include <cstdio>
#include <syslog.h>
#include <cerrno>
#include <cstring>
#include <ctime>
#include <string>
#include "Logger.h"  // IWYU pragma: keep
#include "nagios.h"

using std::string;

pthread_t g_mainthread_id;
static FILE *fl_logfile = nullptr;

void open_logfile(const string &path) {
    // needed to determine main thread later
    g_mainthread_id = pthread_self();

    fl_logfile = fopen(path.c_str(), "a");
    if (fl_logfile == nullptr) {
        logger(LOG_WARNING,
               "Cannot open logfile " + path + ": " + strerror(errno));
    }
}

void close_logfile() {
    if (fl_logfile != nullptr) {
        fclose(fl_logfile);
        fl_logfile = nullptr;
    }
}

void logger(int /*priority*/, const string &message) {
    // Only the main process may use the Nagios log methods
    if (fl_logfile == nullptr || g_mainthread_id == pthread_self()) {
        // TODO(sp) The Nagios headers are (once again) not const-correct...
        write_to_all_logs(
            const_cast<char *>(("livestatus: " + message).c_str()),
            NSLOG_INFO_MESSAGE);
    } else if (fl_logfile != nullptr) {
        char timestring[64];
        time_t now_t = time(nullptr);
        struct tm now;
        localtime_r(&now_t, &now);
        strftime(timestring, 64, "%F %T ", &now);
        fputs((timestring + message + "\n").c_str(), fl_logfile);
        fflush(fl_logfile);
    }
}
