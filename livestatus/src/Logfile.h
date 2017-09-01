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
#include "LogEntry.h"  // IWYU pragma: keep
class LogCache;
class Logger;
class MonitoringCore;
class Query;

#ifdef CMC
#include <vector>
class World;
#endif

// key is time_t . lineno
using logfile_entries_t = std::map<uint64_t, std::unique_ptr<LogEntry>>;

class Logfile {
private:
    MonitoringCore *_mc;
    fs::path _path;
    time_t _since;     // time of first entry
    bool _watch;       // true only for current logfile
    fpos_t _read_pos;  // read until this position
    uint32_t _lineno;  // read until this line

    logfile_entries_t _entries;
#ifdef CMC
    World *_world;  // CMC: world our references point into
#endif

public:
    Logfile(MonitoringCore *mc, fs::path path, bool watch);

    std::string path() { return _path; }
#ifdef CMC
    // Note: The buffer is 2 bytes larger then the file, containing a zero
    // character at both ends.
    std::unique_ptr<std::vector<char>> readIntoBuffer();
#endif
    void load(LogCache *logcache, time_t since, time_t until,
              unsigned logclasses);
    void flush();
    time_t since() { return _since; }
    unsigned classesRead() { return _logclasses_read; }
    long numEntries() { return _entries.size(); }
    logfile_entries_t *getEntriesFromQuery(const Query *query,
                                           LogCache *logcache, time_t since,
                                           time_t until, unsigned);
    bool answerQuery(Query *query, LogCache *logcache, time_t since,
                     time_t until, unsigned);
    bool answerQueryReverse(Query *query, LogCache *logcache, time_t since,
                            time_t until, unsigned);

    long freeMessages(unsigned logclasses);
    void updateReferences();

    unsigned _logclasses_read;  // only these types have been read

private:
    void loadRange(FILE *file, unsigned missing_types, LogCache *, time_t since,
                   time_t until, unsigned logclasses);
    bool processLogLine(uint32_t lineno, std::string line, unsigned logclasses);
    uint64_t makeKey(time_t, unsigned);
    Logger *logger() const;
};

#endif  // Logfile_h
