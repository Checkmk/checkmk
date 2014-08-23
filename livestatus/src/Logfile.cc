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
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#include <errno.h>
#include <fcntl.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>

#include "Logfile.h"
#include "logger.h"
#include "LogEntry.h"
#include "Query.h"
#include "LogCache.h"

#ifdef CMC
#include "Core.h"
extern Core *g_core;
#endif

extern unsigned long g_max_lines_per_logfile;


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
    flush();
    free(_path);
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

        _lineno = 0;
        loadRange(file, missing_types, logcache, since, until, logclasses);
        fclose(file);
        _logclasses_read |= missing_types;
    }
}

void Logfile::loadRange(FILE *file, unsigned missing_types,
        LogCache *logcache, time_t since, time_t until, unsigned logclasses)
{
    while (fgets(_linebuffer, MAX_LOGLINE, file))
    {
        if (_lineno >= g_max_lines_per_logfile) {
            logger(LG_ERR, "More than %u lines in %s. Ignoring the rest!", g_max_lines_per_logfile, this->_path);
            return;
        }
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
    LogEntry *entry = new LogEntry(lineno, _linebuffer);
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
    updateReferences(); // Make sure existing references to objects point to correct world
    load(logcache, since, until, logclasses); // make sure all messages are present
    return &_entries;
}

bool Logfile::answerQuery(Query *query, LogCache *logcache, time_t since, time_t until, unsigned logclasses)
{
    updateReferences(); // Make sure existing references to objects point to correct world
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
    updateReferences(); // Make sure existing references to objects point to correct world
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


void Logfile::updateReferences()
{
#ifdef CMC
    // If our references in cached log entries do not point to the currently
    // active configuration world, then update all references
    if (_world != g_live_world) {
        unsigned num = 0;
        for (logfile_entries_t::iterator it = _entries.begin(); it != _entries.end(); ++it)
            num += it->second->updateReferences();
        logger(LOG_NOTICE, "Updated %u log cache references of %s to new world.", num, _path);
        _world = g_live_world;
    }
#endif
}

// Read complete file into newly allocated buffer. Returns a pointer
// to a malloced buffer, that the caller must free (or 0, in case of
// an error). The buffer is 2 bytes larger then the file. One byte
// at the beginning and at the end of the buffer are '\0'.
char *Logfile::readIntoBuffer(int *size)
{
    int fd = open(_path, O_RDONLY);
    if (fd < 0) {
        logger(LOG_WARNING, "Cannot open %s for reading: %s", _path, strerror(errno));
        return 0;
    }

    off_t o = lseek(fd, 0, SEEK_END);
    if (o == -1) {
        logger(LOG_WARNING, "Cannot seek to end of %s: %s", _path, strerror(errno));
        close(fd);
        return 0;
    }

    *size = o;
    lseek(fd, 0, SEEK_SET);

    char *buffer = (char *)malloc(*size + 2); // add space for binary 0 at beginning and end
    if (!buffer) {
        logger(LOG_WARNING, "Cannot malloc buffer for reading %s: %s", _path, strerror(errno));
        close(fd);
        return 0;
    }

    int r = read(fd, buffer + 1, *size);
    if (r < 0) {
        logger(LOG_WARNING, "Cannot read %d bytes from %s: %s", *size, _path, strerror(errno));
        free(buffer);
        close(fd);
        return 0;
    }
    else if (r != *size) {
        logger(LOG_WARNING, "Read only %d out of %d bytes from %s", r, *size, _path);
        free(buffer);
        close(fd);
        return 0;
    }
    buffer[0]       = 0;
    buffer[*size+1] = 0; // zero-terminate

    close(fd);
    return buffer;
}
