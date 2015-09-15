// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2015             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// Copyright by Mathias Kettner and Mathias Kettner GmbH.  All rights reserved.
//
// Check_MK is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.
//
// Check_MK is  distributed in the hope that it will be useful, but
// WITHOUT ANY WARRANTY;  without even the implied warranty of
// MERCHANTABILITY  or  FITNESS FOR A PARTICULAR PURPOSE. See the
// GNU General Public License for more details.
//
// You should have  received  a copy of the  GNU  General Public
// License along with Check_MK.  If  not, email to mk@mathias-kettner.de
// or write to the postal address provided at www.mathias-kettner.de

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
class World;

typedef map<uint64_t, LogEntry *> logfile_entries_t; // key is time_t . lineno

class Logfile
{
private:
    char      *_path;
    time_t     _since;         // time of first entry
    bool       _watch;         // true only for current logfile
    ino_t      _inode;         // needed to detect switching
    fpos_t     _read_pos;      // read until this position
    uint32_t   _lineno;        // read until this line

    logfile_entries_t  _entries;
    char       _linebuffer[MAX_LOGLINE];
    World     *_world;         // CMC: world our references point into


public:
    Logfile(const char *path, bool watch);
    ~Logfile();

    char *path() { return _path; }
    char *readIntoBuffer(int *size);
    void load(LogCache *LogCache, time_t since, time_t until, unsigned logclasses);
    void flush();
    time_t since() { return _since; }
    unsigned classesRead() { return _logclasses_read; }
    long numEntries() { return _entries.size(); }
    logfile_entries_t* getEntriesFromQuery(Query *query, LogCache *lc, time_t since, time_t until, unsigned);
    bool answerQuery(Query *query, LogCache *lc, time_t since, time_t until, unsigned);
    bool answerQueryReverse(Query *query, LogCache *lc, time_t since, time_t until, unsigned);

    long freeMessages(unsigned logclasses);
    void updateReferences();

    unsigned   _logclasses_read; // only these types have been read


private:
    void loadRange(FILE *file, unsigned missing_types, LogCache *,
                   time_t since, time_t until, unsigned logclasses);
    bool processLogLine(uint32_t, unsigned);
    uint64_t makeKey(time_t, unsigned);
};


#endif // Logfile_h

