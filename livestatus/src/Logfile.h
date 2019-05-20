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

#include "config.h"  // IWYU pragma: keep
#include <cstdint>
#include <cstdio>
#include <ctime>
#include <map>
#include <memory>
#include <string>
#include "FileSystem.h"
class LogCache;
class LogEntry;
class Logger;
class MonitoringCore;
class Query;

#ifdef CMC
class World;
#endif

// key is time_t . lineno
using logfile_entries_t = std::map<uint64_t, std::unique_ptr<LogEntry>>;

class Logfile {
public:
    Logfile(MonitoringCore *mc, LogCache *logcache, fs::path path, bool watch);
    [[nodiscard]] fs::path path() const { return _path; }

    // for tricky protocol between LogCache::logLineHasBeenAdded and this class
    void flush();
    [[nodiscard]] time_t since() const { return _since; }
    [[nodiscard]] unsigned classesRead() const { return _logclasses_read; }
    [[nodiscard]] size_t size() const { return _entries.size(); }
    long freeMessages(unsigned logclasses);

    // for TableStateHistory
    const logfile_entries_t *getEntriesFor(unsigned logclasses);

    // for TableLog::answerQuery
    bool answerQueryReverse(Query *query, time_t since, time_t until,
                            unsigned logclasses);

private:
    MonitoringCore *const _mc;
    LogCache *const _logcache;
    const fs::path _path;
    const time_t _since;  // time of first entry
    const bool _watch;    // true only for current logfile
    fpos_t _read_pos;     // read until this position
    size_t _lineno;       // read until this line
    logfile_entries_t _entries;
#ifdef CMC
    World *_world;  // CMC: world our references point into
#endif
    unsigned _logclasses_read;  // only these types have been read

    void load(unsigned logclasses);
    void loadRange(FILE *file, unsigned missing_types, unsigned logclasses);
    bool processLogLine(size_t lineno, std::string line, unsigned logclasses);
    uint64_t makeKey(time_t t, size_t lineno);
    void updateReferences();
    [[nodiscard]] Logger *logger() const;
};

#endif  // Logfile_h
