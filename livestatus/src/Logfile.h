// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
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
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#ifndef Logfile_h
#define Logfile_h

#include <sys/types.h>
#include <stdio.h>
#include <stdint.h>
#include <map>

using namespace std;

#define MAX_LOGLINE 65536

class LogEntry;
class Query;
class LogCache;

typedef map<uint64_t, LogEntry *> logfile_entries_t; // key is time_t . lineno

class Logfile
{
public:
    Logfile(const char *path, bool watch);
    ~Logfile();

    char *path() { return _path; }
    void load(LogCache *LogCache, time_t since, time_t until, unsigned logclasses);
    void flush();
    time_t since() { return _since; }
    unsigned classesRead() { return _logclasses_read; }
    long numEntries() { return _entries.size(); }
    logfile_entries_t* getEntriesFromQuery(Query *query, LogCache *lc, time_t since, time_t until, unsigned);
    bool answerQuery(Query *query, LogCache *lc, time_t since, time_t until, unsigned);
    bool answerQueryReverse(Query *query, LogCache *lc, time_t since, time_t until, unsigned);

    long freeMessages(unsigned logclasses);

    unsigned   _logclasses_read; // only these types have been read
private:
    char      *_path;
    time_t     _since;         // time of first entry
    bool       _watch;         // true only for current logfile
    ino_t      _inode;         // needed to detect switching
    fpos_t     _read_pos;      // read until this position
    uint32_t   _lineno;        // read until this line

    logfile_entries_t  _entries;
    char       _linebuffer[MAX_LOGLINE];


private:
    void loadRange(FILE *file, unsigned missing_types, LogCache *,
                   time_t since, time_t until, unsigned logclasses);
    bool processLogLine(uint32_t, unsigned);
    uint64_t makeKey(time_t, unsigned);
};


#endif // Logfile_h

