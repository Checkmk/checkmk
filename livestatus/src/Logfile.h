// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef Logfile_h
#define Logfile_h

// NOTE: We need the 2nd "keep" pragma for deleting Logfile. Is this an IWYU
// bug?
#include "config.h"  // IWYU pragma: keep

#include <chrono>
#include <cstdio>
#include <filesystem>
#include <functional>
#include <map>
#include <memory>
#include <string>
#include <utility>

#include "LogEntry.h"  // IWYU pragma: keep
class LogCache;
class LogFilter;
class Logger;

class Logfile {
public:
    using key_type = std::pair<std::chrono::system_clock::time_point, size_t>;
    using map_type = std::map<key_type, std::unique_ptr<LogEntry>>;
    using const_iterator = map_type::const_iterator;

    // Used by LogCache::update(). All instances are owned by
    // LogCache::_logfiles.
    Logfile(Logger *logger, LogCache *log_cache, std::filesystem::path path,
            bool watch);

    // Used internally and by StateHistoryThread::run().
    [[nodiscard]] std::filesystem::path path() const { return _path; }

    // Used by LogCache::addToIndex() for tricky protocol between
    // LogCache::logLineHasBeenAdded() and this class.
    [[nodiscard]] std::chrono::system_clock::time_point since() const {
        return _since;
    }

    // Used by LogCache::logLineHasBeenAdded().
    [[nodiscard]] unsigned classesRead() const { return _logclasses_read; }
    [[nodiscard]] size_t size() const { return _entries.size(); }
    long freeMessages(unsigned logclasses);

    // Used by TableLog::answerQueryReverse() and
    // TableStateHistory::getEntries().
    const Logfile::map_type *getEntriesFor(size_t max_lines_per_logfile,
                                           unsigned logclasses);

    // Used internally and by TableLog::answerQueryReverse(). Should be nuked.
    static Logfile::key_type makeKey(std::chrono::system_clock::time_point t,
                                     size_t lineno) {
        return {t, lineno};
    }

    static bool processLogEntries(
        const std::function<bool(const LogEntry &)> &process_log_entry,
        const map_type *entries, const LogFilter &log_filter);

private:
    Logger *const _logger;
    LogCache *const _log_cache;
    const std::filesystem::path _path;
    const std::chrono::system_clock::time_point _since;  // time of first entry
    const bool _watch;  // true only for current logfile
    fpos_t _read_pos;   // read until this position
    size_t _lineno;     // read until this line
    Logfile::map_type _entries;
    unsigned _logclasses_read;  // only these types have been read

    void load(size_t max_lines_per_logfile, unsigned logclasses);
    void loadRange(size_t max_lines_per_logfile, FILE *file,
                   unsigned missing_types, unsigned logclasses);
    bool processLogLine(size_t lineno, std::string line, unsigned logclasses);
};

#endif  // Logfile_h
