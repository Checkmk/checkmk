// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef Logfile_h
#define Logfile_h

// NOTE: We need the 2nd "keep" pragma for deleting Logfile. Is this an IWYU
// bug?
#include "config.h"  // IWYU pragma: keep

#include <cstdint>
#include <cstdio>
#include <ctime>
#include <filesystem>
#include <map>
#include <memory>
#include <string>

#include "LogEntry.h"  // IWYU pragma: keep
class LogCache;
class Logger;

// key is time_t . lineno
using logfile_entries_t = std::map<uint64_t, std::unique_ptr<LogEntry>>;

class Logfile {
public:
    Logfile(Logger *logger, LogCache *log_cache, std::filesystem::path path,
            bool watch);
    [[nodiscard]] std::filesystem::path path() const { return _path; }

    // for tricky protocol between LogCache::logLineHasBeenAdded and this class
    [[nodiscard]] time_t since() const { return _since; }
    [[nodiscard]] unsigned classesRead() const { return _logclasses_read; }
    [[nodiscard]] size_t size() const { return _entries.size(); }
    long freeMessages(unsigned logclasses);

    // for TableStateHistory and TableLog
    const logfile_entries_t *getEntriesFor(size_t max_lines_per_logfile,
                                           unsigned logclasses);

    // for TableLog::answerQuery
    static uint64_t makeKey(time_t t, size_t lineno);

private:
    Logger *const _logger;
    LogCache *const _log_cache;
    const std::filesystem::path _path;
    const time_t _since;  // time of first entry
    const bool _watch;    // true only for current logfile
    fpos_t _read_pos;     // read until this position
    size_t _lineno;       // read until this line
    logfile_entries_t _entries;
    unsigned _logclasses_read;  // only these types have been read

    void load(size_t max_lines_per_logfile, unsigned logclasses);
    void loadRange(size_t max_lines_per_logfile, FILE *file,
                   unsigned missing_types, unsigned logclasses);
    bool processLogLine(size_t lineno, std::string line, unsigned logclasses);
};

#endif  // Logfile_h
