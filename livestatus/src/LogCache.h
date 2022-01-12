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

// We keep this on top level to make forawrd declarations possible.
class LogFiles {
public:
    using container = std::map<std::chrono::system_clock::time_point,
                               std::unique_ptr<Logfile>>;
    using const_iterator = container::const_iterator;

    explicit LogFiles(const container &log_files) : log_files_{log_files} {}
    [[nodiscard]] auto begin() const { return log_files_.begin(); }
    [[nodiscard]] auto end() const { return log_files_.end(); }

private:
    const container &log_files_;
};

class LogFilesReverse {
public:
    using container = std::map<std::chrono::system_clock::time_point,
                               std::unique_ptr<Logfile>>;
    using const_iterator = container::const_iterator;

    explicit LogFilesReverse(const container &log_files)
        : log_files_{log_files} {}
    [[nodiscard]] auto begin() const { return log_files_.rbegin(); }
    [[nodiscard]] auto end() const { return log_files_.rend(); }

private:
    const container &log_files_;
};

// TODO(sp) Split this class into 2 parts: One is really only a cache for the
// logfiles to monitor, the other part is about the lines in them.
class LogCache {
public:
    // TODO(sp) The constructor is not allowed to call any method of the
    // MonitoringCore it gets, because there is a knot between the Store and the
    // NagiosCore classes, so the MonitoringCore is not yet fully constructed.
    // :-P

    // Used by Store::Store(), which owns the single instance of it in
    // Store::_log_cached. It passes this instance to TableLog::TableLog() and
    // TableStateHistory::TableStateHistory(). StateHistoryThread::run()
    // constructs its own instance.
    explicit LogCache(MonitoringCore *mc);

    // Call the given function with a locked and updated LogCache, keeping the
    // lock and the update function local.
    template <class F>
    inline auto apply(F f) {
        std::lock_guard<std::mutex> lg(_lock);
        update();
        return f(LogFiles{_logfiles});
    }

    // Call the given function with a locked and updated LogCache, keeping the
    // lock and the update function local. Reverse version.
    template <class F>
    inline auto applyReverse(F f) {
        std::lock_guard<std::mutex> lg(_lock);
        update();
        return f(LogFilesReverse{_logfiles});
    }

    // Used by Logfile::loadRange()
    void logLineHasBeenAdded(Logfile *logfile, unsigned logclasses);

private:
    MonitoringCore *const _mc;
    std::mutex _lock;
    size_t _num_cached_log_messages;
    size_t _num_at_last_check;
    std::map<std::chrono::system_clock::time_point, std::unique_ptr<Logfile>>
        _logfiles;
    std::chrono::system_clock::time_point _last_index_update;

    void update();
    void addToIndex(std::unique_ptr<Logfile> logfile);
    [[nodiscard]] Logger *logger() const;
};

#endif  // LogCache_h
