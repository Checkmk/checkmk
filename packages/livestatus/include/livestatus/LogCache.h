// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef LogCache_h
#define LogCache_h

#include <chrono>
#include <cstddef>
#include <filesystem>
#include <map>
#include <memory>
#include <mutex>

#include "livestatus/Logfile.h"
class ICore;
class Logger;

// We keep this on top level to make forward declarations possible.
class LogFiles {
public:
    using container = std::map<std::chrono::system_clock::time_point,
                               std::unique_ptr<Logfile>>;
    using const_iterator = container::const_iterator;

    explicit LogFiles(const container &log_files) : log_files_{&log_files} {}
    [[nodiscard]] auto begin() const { return log_files_->begin(); }
    [[nodiscard]] auto end() const { return log_files_->end(); }

private:
    const container *log_files_;
};

class LogFilter {
public:
    size_t max_lines_per_log_file;
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
    // TODO(sp) The constructor is not allowed to call any method of the ICore
    // it gets, because there is a knot between the Store and the NebCore
    // classes, so the ICore is not yet fully constructed. :-P

    // Used by Store::Store(), which owns the single instance of it in
    // Store::_log_cached. It passes this instance to TableLog::TableLog() and
    // TableStateHistory::TableStateHistory(). StateHistoryThread::run()
    // constructs its own instance.
    explicit LogCache(ICore *core);

    // Used for a confusing fragile protocol between LogCache and Logfile to
    // keep the number of cached log entries under control. Used by
    // Logfile::loadRange()
    void logLineHasBeenAdded(Logfile *log_file, unsigned log_classes);

    // Call the given function with a locked and updated LogCache, keeping the
    // lock and the update function local.
    template <typename F>
    inline auto apply(F f) {
        std::lock_guard<std::mutex> lg{lock_};
        update();
        return f(LogFiles{log_files_}, num_cached_log_messages_);
    }

private:
    ICore *const core_;
    std::mutex lock_;
    size_t num_cached_log_messages_;
    size_t num_at_last_check_;
    std::map<std::chrono::system_clock::time_point, std::unique_ptr<Logfile>>
        log_files_;
    std::chrono::system_clock::time_point last_index_update_;

    void update();
    void addToIndex(const std::filesystem::path &path, bool watch);
    [[nodiscard]] Logger *logger() const;
};

#endif  // LogCache_h
