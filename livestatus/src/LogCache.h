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

#ifndef LogCache_h
#define LogCache_h

#include "config.h"  // IWYU pragma: keep
#include <chrono>
#include <ctime>
#include <map>
#include <memory>
#include <mutex>
class Logfile;
class Logger;
class MonitoringCore;

using logfiles_t = std::map<time_t, std::unique_ptr<Logfile>>;

// TODO(sp) Split this class into 2 parts: One is really only a cache for the
// logfiles to monitor, the other part is about the lines in them.
class LogCache {
public:
    // TODO(sp) Using this class requires a very tricky and fragile protocol:
    // You have to get the lock and call update() before you use any of the
    // other methods. Furthermore, the constructor is not allowed to call any
    // method of the MonitoringCore it gets, because there is a knot between the
    // Store and the NagiosCore classes, so the MonitoringCore is not yet fully
    // constructed. :-P
    std::mutex _lock;
    explicit LogCache(MonitoringCore *mc);
    void update();

    [[nodiscard]] size_t numCachedLogMessages() const;
    void logLineHasBeenAdded(Logfile *logfile, unsigned logclasses);
    auto begin() { return _logfiles.begin(); }
    auto end() { return _logfiles.end(); }

private:
    MonitoringCore *const _mc;
    size_t _num_cached_log_messages;
    size_t _num_at_last_check;
    logfiles_t _logfiles;
    std::chrono::system_clock::time_point _last_index_update;

    void addToIndex(std::unique_ptr<Logfile> logfile);
    [[nodiscard]] Logger *logger() const;
};

#endif  // LogCache_h
