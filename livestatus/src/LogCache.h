// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef LogCache_h
#define LogCache_h

#include "config.h"  // IWYU pragma: keep

#include <chrono>
#include <cstddef>
#include <map>
#include <memory>
#include <mutex>
class Logfile;
class Logger;
class MonitoringCore;

// TODO(sp) Split this class into 2 parts: One is really only a cache for the
// logfiles to monitor, the other part is about the lines in them.
class LogCache {
public:
    using key_type = std::chrono::system_clock::time_point;
    using mapped_type = std::unique_ptr<Logfile>;
    using map_type = std::map<key_type, mapped_type>;
    using iterator = map_type::iterator;
    using const_iterator = map_type::const_iterator;

    // TODO(sp) Using this class requires a very tricky and fragile protocol:
    // You have to get the lock and call update() before you use any of the
    // other methods. Furthermore, the constructor is not allowed to call any
    // method of the MonitoringCore it gets, because there is a knot between the
    // Store and the NagiosCore classes, so the MonitoringCore is not yet fully
    // constructed. :-P

    // Used internally and to guard the execution of TableLog::answerQuery() and
    // TableStateHistory::answerQuery(). StateHistoryThread::run() uses this,
    // too.
    std::mutex _lock;

    // Used by Store::Store(), which owns the single instance of it in
    // Store::_log_cached. It passes this instance to TableLog::TableLog() and
    // TableStateHistory::TableStateHistory(). StateHistoryThread::run()
    // constructs its own instance.
    explicit LogCache(MonitoringCore *mc);

    // Used internally and by TableLog::answerQuery() and
    // TableStateHistory::answerQuery(). StateHistoryThread::run() uses this,
    // too. Always guarded by _lock.
    void update();

    // Used by Store::numCachedLogMessages(), uses _lock for itself.
    [[nodiscard]] size_t numCachedLogMessages();

    // Used by Logfile::loadRange()
    void logLineHasBeenAdded(Logfile *logfile, unsigned logclasses);

    // Used by TableLog::answerQuery() and TableStateHistory::answerQuery().
    // StateHistoryThread::run() uses this, too.
    [[nodiscard]] bool empty() const { return _logfiles.empty(); }

    // Used by TableLog::answerQuery(), TableStateHistory::answerQuery(),
    // TableStateHistory::getPreviousLogentry(),
    // TableStateHistory::getNextLogentry(), and StateHistoryThread::run()
    auto begin() { return _logfiles.begin(); }
    auto end() { return _logfiles.end(); }

private:
    MonitoringCore *const _mc;
    size_t _num_cached_log_messages;
    size_t _num_at_last_check;
    LogCache::map_type _logfiles;
    std::chrono::system_clock::time_point _last_index_update;

    void addToIndex(mapped_type logfile);
    [[nodiscard]] Logger *logger() const;
};

#endif  // LogCache_h
