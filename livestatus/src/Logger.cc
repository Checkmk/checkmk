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

#include "Logger.h"
#include <cerrno>
#include <cstdio>
#include <cstring>
#include <string>

using std::string;

namespace {
FILE *fl_logfile = nullptr;
}  // namespace

void open_logfile(const string &path) {
    fl_logfile = fopen(path.c_str(), "a");
    if (fl_logfile == nullptr) {
        logger(LogLevel::warning,
               "Cannot open logfile " + path + ": " + strerror(errno));
    }
}

void close_logfile() {
    if (fl_logfile != nullptr) {
        fclose(fl_logfile);
        fl_logfile = nullptr;
    }
}

#ifdef CMC

#include <sys/time.h>
#include <ctime>
#include <mutex>

using std::lock_guard;
using std::mutex;

namespace {
std::mutex fl_logfile_mutex;
LogLevel fl_log_level = LogLevel::notice;
bool fl_log_microtime = false;
}  // namespace

// Called during a logfile rotation, triggered by an external command.
// This should only do somehting in case the logfile is really open.
void reopen_logfile(const string &path) {
    if (fl_logfile != nullptr) {
        close_logfile();
        open_logfile(path);
        logger(LogLevel::notice, "Reopened logfile.");
    }
}

void set_log_config(LogLevel log_level, bool log_microtime) {
    fl_log_level = log_level;
    fl_log_microtime = log_microtime;
}

bool should_log(LogLevel log_level) { return log_level <= fl_log_level; }

FILE *get_logfile() { return fl_logfile != nullptr ? fl_logfile : stdout; }

void logger(LogLevel log_level, const string &message) {
    if (!should_log(log_level)) {
        return;  // msg not important enough
    }

    FILE *logfile = get_logfile();

    // Make sure that loglines are not garbled up, Livestatus threads also
    // log...
    lock_guard<mutex> lg(fl_logfile_mutex);
    struct timeval tv;
    gettimeofday(&tv, nullptr);
    time_t t = tv.tv_sec;
    struct tm lt;
    localtime_r(&t, &lt);
    char datestring[32];
    strftime(datestring, sizeof(datestring), "%Y-%m-%d %H:%M:%S ", &lt);
    fputs(datestring, logfile);
    if (fl_log_microtime) {
        fprintf(logfile, "%03ld.%03ld ", tv.tv_usec / 1000, tv.tv_usec % 1000);
    }
    fprintf(logfile, "[%d] ", log_level);
    fputs(message.c_str(), logfile);
    fputc('\n', logfile);
    fflush(logfile);
}

#else

#include <ctime>

void logger(LogLevel /*log_level*/, const string &message) {
    extern bool runningInLivestatusMainThread();
    extern void writeToAllLogs(const string &message);
    // Only the main process may use the Nagios log methods
    if (fl_logfile == nullptr || runningInLivestatusMainThread()) {
        writeToAllLogs("livestatus: " + message);
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

#endif
