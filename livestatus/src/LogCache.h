// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef LogCache_h
#define LogCache_h

#include "config.h"  // IWYU pragma: keep

#include <chrono>
#include <cstddef>
#include <filesystem>
#include <functional>
#include <map>
#include <memory>
#include <mutex>
#include <optional>
#include <utility>
#include <vector>

class LogEntry;
class Logfile;
class Logger;
class MonitoringCore;

// We keep this on top level to make forward declarations possible.
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

class LogFilter {
public:
    size_t max_lines_per_logfile;
    unsigned classmask;
    std::chrono::system_clock::time_point since;
    std::chrono::system_clock::time_point until;
};

// NOTE: This class is currently broken due to race conditions: Although it uses
// a lock internally to guard against concurrent modifications happening by its
// own functions, there is no locking at all regarding the writing of log
// messages to the monitoring history and no locking to protect against
// concurrent monitoring history rotations. All of this *has* to move into this
// class, otherwise strange things can happen. Rarely, but nevertheless...
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

    // Used for a confusing fragile protocol betwwen LogCache and Logfile to
    // keep the number of cached log entries under control. Used by
    // Logfile::loadRange()
    void logLineHasBeenAdded(Logfile *logfile, unsigned logclasses);

    // Return log file paths chronologically backwards up to a given horizon
    // plus the first skipped log file path (if any). Used by
    // StateHistoryThread::run().
    std::pair<std::vector<std::filesystem::path>,
              std::optional<std::filesystem::path>>
    pathsSince(std::chrono::system_clock::time_point since);

    // Call the given function with a locked and updated LogCache, keeping the
    // lock and the update function local. Used by
    // TableStateHistory::answerQuery()
    template <class F>
    inline auto apply(F f) {
        std::lock_guard<std::mutex> lg(_lock);
        update();
        return f(LogFiles{_logfiles});
    }

    // Call the given callback for each log entry matching the filter in a
    // chronologically backwards fashion, until the callback returns false. Used
    // by TableLog::answerQuery().
    void for_each(
        const LogFilter &log_filter,
        const std::function<bool(const LogEntry &)> &process_log_entry);

    // Returns the overall number of log entries currently in the cache. Used by
    // Store::numCachedLogMessages().
    size_t numCachedLogMessages();

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
