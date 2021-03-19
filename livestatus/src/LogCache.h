// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

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
    [[nodiscard]] bool empty() const { return _logfiles.empty(); }
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
