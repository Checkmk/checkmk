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

#include <fcntl.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>

#include "Logfile.h"
#include "logger.h"
#include "LogEntry.h"
#include "Query.h"
#include "LogCache.h"


Logfile::Logfile(const char *path, bool watch)
  : _path(strdup(path))
  , _since(0)
  , _watch(watch)
  , _inode(0)
  , _lineno(0)
  , _logclasses_read(0)
{
    int fd = open(path, O_RDONLY);
    if (fd < 0) {
        logger(LG_INFO, "Cannot open logfile '%s'", path);
        return;
    }

    char line[12];
    if (12 != read(fd, line, 12)) {
        close(fd);
        return; // ignoring. might be empty
    }

    if (line[0] != '[' || line[11] != ']') {
        logger(LG_INFO, "Ignoring logfile '%s':does not begin with '[123456789] '", path);
        close(fd);
        return;
    }

    line[11] = 0;
    _since = atoi(line+1);
    close(fd);
}


Logfile::~Logfile()
{
    free(_path);
    flush();
}


void Logfile::flush()
{
	for (logfile_entries_t::iterator it = _entries.begin(); it != _entries.end(); ++it)
        delete it->second;

    _entries.clear();
    _logclasses_read = 0;
}


void Logfile::load(LogCache *logcache, time_t since, time_t until, unsigned logclasses)
{
    // HIER KOENNTE ICH FLUSHEN, WENN g_active_world nicht mehr stimmt

    unsigned missing_types = logclasses & ~_logclasses_read;
    FILE *file = 0;
    // The current logfile has the _watch flag set to true.
    // In that case, if the logfile has grown, we need to
    // load the rest of the file, even if no logclasses
    // are missing.
    if (_watch) {
        file = fopen(_path, "r");
        if (!file) {
            logger(LG_INFO, "Cannot open logfile '%s'", _path);
            return;
        }
        // If we read this file for the first time, we initialize
        // the current file position to 0
        if (_lineno == 0)
            fgetpos(file, &_read_pos);

        // file might have grown. Read all classes that we already
        // have read to the end of the file
        if (_logclasses_read) {
            fsetpos(file, &_read_pos); // continue at previous end
            loadRange(file, _logclasses_read, logcache, since, until, logclasses);
            fgetpos(file, &_read_pos);
        }
        if (missing_types) {
        	fseek(file, 0, SEEK_SET);
            _lineno = 0;
            loadRange(file, missing_types, logcache, since, until, logclasses);
            _logclasses_read |= missing_types;
            fgetpos(file, &_read_pos); // remember current end of file
        }
        fclose(file);
    }
    else
    {
        if (missing_types == 0)
            return;

        file = fopen(_path, "r");
        if (!file) {
            logger(LG_INFO, "Cannot open logfile '%s'", _path);
            return;
        }

        loadRange(file, missing_types, logcache, since, until, logclasses);
        fclose(file);
        _logclasses_read |= missing_types;
    }
}

void Logfile::loadRange(FILE *file, unsigned missing_types,
        LogCache *logcache, time_t since, time_t until, unsigned logclasses)
{
    //logger(LOG_NOTICE, "Read logfile: %s", this->_path);
    while (fgets(_linebuffer, MAX_LOGLINE, file))
    {
        _lineno++;
        if (processLogLine(_lineno, missing_types)) {
            logcache->handleNewMessage(this, since, until, logclasses); // memory management
        }
    }
}

long Logfile::freeMessages(unsigned logclasses)
{
    long freed = 0;
    for (logfile_entries_t::iterator it = _entries.begin(); it != _entries.end(); ++it)
    {
        LogEntry *entry = it->second;
        if ((1 << entry->_logclass) & logclasses)
        {
            delete it->second;
            _entries.erase(it);
            freed ++;
        }
    }
    _logclasses_read &= ~logclasses;
    return freed;
}

inline bool Logfile::processLogLine(uint32_t lineno, unsigned logclasses)
{
    LogEntry *entry = new LogEntry(lineno, _linebuffer, logclasses);
    // ignored invalid lines
    if (entry->_logclass == LOGCLASS_INVALID) {
        delete entry;
        return false;
    }
    if ((1 << entry->_logclass) & logclasses) {
        uint64_t key = makeKey(entry->_time, lineno);
        if (_entries.find(key) == _entries.end())
            _entries.insert(make_pair(key, entry));
        else { // this should never happen. The lineno must be unique!
            logger(LG_ERR, "Strange: duplicate logfile line %s", _linebuffer);
            delete entry;
            return false;
        }
        return true;
    }
    else {
        delete entry;
        return false;
    }
}

logfile_entries_t* Logfile::getEntriesFromQuery(Query *query, LogCache *logcache, time_t since, time_t until, unsigned logclasses)
{
	 load(logcache, since, until, logclasses); // make sure all messages are present
	 return &_entries;
}

bool Logfile::answerQuery(Query *query, LogCache *logcache, time_t since, time_t until, unsigned logclasses)
{
    load(logcache, since, until, logclasses); // make sure all messages are present
    uint64_t sincekey = makeKey(since, 0);
    logfile_entries_t::iterator it = _entries.lower_bound(sincekey);
    while (it != _entries.end())
    {
        LogEntry *entry = it->second;
        if (entry->_time >= until)
            return false; // end found
        if (!query->processDataset(entry))
            return false; // limit exceeded
        ++it;
    }
    return true;
}

bool Logfile::answerQueryReverse(Query *query, LogCache *logcache, time_t since, time_t until, unsigned logclasses)
{
    load(logcache, since, until, logclasses); // make sure all messages are present
    uint64_t untilkey = makeKey(until, 999999999);
    logfile_entries_t::iterator it = _entries.upper_bound(untilkey);
    while (it != _entries.begin())
    {
        --it;
        LogEntry *entry = it->second;
        if (entry->_time < since)
            return false; // end found
        if (!query->processDataset(entry))
            return false; // limit exceeded
    }
    return true;
}

uint64_t Logfile::makeKey(time_t t, unsigned lineno)
{
    return (uint64_t)((uint64_t)t << 32) | (uint64_t)lineno;
}

