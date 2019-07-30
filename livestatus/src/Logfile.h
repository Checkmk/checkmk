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
    std::filesystem::path path() const { return _path; }

    // for tricky protocol between LogCache::logLineHasBeenAdded and this class
    time_t since() const { return _since; }
    unsigned classesRead() const { return _logclasses_read; }
    size_t size() const { return _entries.size(); }
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
