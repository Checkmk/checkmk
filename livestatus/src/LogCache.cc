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

#include <time.h>
#include <sys/types.h>
#include <dirent.h>
#include <unistd.h>
#include <stddef.h>
#include <stdarg.h>
#include <stdlib.h>

#include "nagios.h"
#include "logger.h"
#include "tables.h"
#include "auth.h"
#include "Logfile.h"
#include "LogEntry.h"
#include "LogCache.h"

#define CHECK_MEM_CYCLE 1000 /* Check memory every N'th new message */

// watch nagios' logfile rotation
extern time_t last_log_rotation;
extern int g_debug_level;
extern char *log_archive_path;
extern char *log_file;


int num_cached_log_messages = 0;

// Debugging logging is hard if debug messages are logged themselves...
void debug(const char *loginfo, ...)
{
    if (g_debug_level < 2)
        return;

    FILE *x = fopen("/tmp/livestatus.log", "a+");
    va_list ap;
    va_start(ap, loginfo);
    vfprintf(x, loginfo, ap);
    fputc('\n', x);
    va_end(ap);
    fclose(x);
}

LogCache::LogCache(unsigned long max_cached_messages)
    : _max_cached_messages(max_cached_messages)
    , _num_at_last_check(0)
    , _my_world(0)
{
    pthread_mutex_init(&_lock, 0);
    updateLogfileIndex();
}

void LogCache::setMaxCachedMessages(unsigned long m)
{
    if (m != _max_cached_messages) {
        logger(LOG_NOTICE, "Logfile cache: Changing max messages to %ld", m);
        _max_cached_messages = m;
    }
}


LogCache::~LogCache()
{
    forgetLogfiles();
    pthread_mutex_destroy(&_lock);
}

void LogCache::lockLogCache()
{
    pthread_mutex_lock(&_lock);
}

void LogCache::unlockLogCache()
{
    pthread_mutex_unlock(&_lock);
}

bool LogCache::logCachePreChecks()
{
#ifdef CMC
    if (g_live_world != _my_world) {
        forgetLogfiles();
        updateLogfileIndex();
    }
#endif
    // Do we have any logfiles (should always be the case,
    // but we don't want to crash...
    if (_logfiles.size() == 0) {
        logger(LOG_INFO, "Warning: no logfile found, not even %s", log_file);
        return false;
    }
    // Has Nagios rotated logfiles? => Update
    // our file index. And delete all memorized
    // log messages.
    if (last_log_rotation > _last_index_update) {
        logger(LG_INFO, "Nagios has rotated logfiles. Rebuilding logfile index");
        forgetLogfiles();
        updateLogfileIndex();
    }
    return true;
}

void LogCache::forgetLogfiles()
{
    for (_logfiles_t::iterator it = _logfiles.begin();
            it != _logfiles.end();
            ++it)
    {
        delete it->second;
    }
    _logfiles.clear();
    num_cached_log_messages = 0;
#ifdef CMC
    _my_world = g_live_world;
#endif
}

void LogCache::updateLogfileIndex()
{
    _last_index_update = time(0);
    // We need to find all relevant logfiles. This includes
    // directory.
    // the current nagios.log and all files in the archive
    scanLogfile(log_file, true);

    DIR *dir = opendir(log_archive_path);

    if (dir) {
        char abspath[4096];
        struct dirent *ent, *result;
        int len = offsetof(struct dirent, d_name)
            + pathconf(log_archive_path, _PC_NAME_MAX) + 1;
        ent = (struct dirent *)malloc(len);

        while (0 == readdir_r(dir, ent, &result) && result != 0)
        {
            if (ent->d_name[0] != '.') {
                snprintf(abspath, sizeof(abspath), "%s/%s", log_archive_path, ent->d_name);
                scanLogfile(abspath, false);
            }
            // ent = result;
        }
        free(ent);
        closedir(dir);
    }
    else
        logger(LG_INFO, "Cannot open log archive '%s'", log_archive_path);
}

void LogCache::scanLogfile(char *path, bool watch)
{
    Logfile *logfile = new Logfile(path, watch);
    time_t since = logfile->since();
    if (since) {
        // make sure that no entry with that 'since' is existing yet.
        // under normal circumstances this never happens. But the
        // user might have copied files around.
        if (_logfiles.find(since) == _logfiles.end())
            _logfiles.insert(make_pair(since, logfile));
        else {
            logger(LG_WARN, "Ignoring duplicate logfile %s", path);
            delete logfile;
        }
    }
    else
        delete logfile;
}

void LogCache::dumpLogfiles()
{
    for (_logfiles_t::iterator it = _logfiles.begin();
            it != _logfiles.end();
            ++it)
    {
        Logfile *log = it->second;
        debug("LOG %s from %d, %u messages, classes: 0x%04x", log->path(), log->since(), log->numEntries(), log->classesRead());
    }
}

/* This method is called each time a log message is loaded
   into memory. If the number of messages loaded in memory
   is to large, memory will be freed by flushing logfiles
   and message not needed by the current query.

   The parameters to this method reflect the current query,
   not the messages that just has been loaded.
 */
void LogCache::handleNewMessage(Logfile *logfile, time_t since __attribute__ ((__unused__)), time_t until __attribute__ ((__unused__)), unsigned logclasses)
{
    if ( ++num_cached_log_messages <= _max_cached_messages  )
        return; // current message count still allowed, everything ok

    /* Memory checking an freeing consumes CPU ressources. We save
       ressources, by avoiding to make the memory check each time
       a new message is loaded when being in a sitation where no
       memory can be freed. We do this by suppressing the check when
       the number of messages loaded into memory has not grown
       by at least CHECK_MEM_CYCLE messages */
    if (num_cached_log_messages < _num_at_last_check + CHECK_MEM_CYCLE)
        return; // Do not check this time

    // [1] Begin by deleting old logfiles
    // Begin deleting with the oldest logfile available
    _logfiles_t::iterator it;
    for (it = _logfiles.begin(); it != _logfiles.end(); ++it)
    {
        Logfile *log = it->second;
        if (log == logfile) {
            // Do not touch the logfile the Query is currently accessing
            break;
        }
        if (log->numEntries() > 0) {
            num_cached_log_messages -= log->numEntries();
            log->flush(); // drop all messages of that file
            if (num_cached_log_messages <= _max_cached_messages) {
                // remember the number of log messages in cache when
                // the last memory-release was done. No further
                // release-check shall be done until that number changes.
                _num_at_last_check = num_cached_log_messages;
                return;
            }
        }
    }
    // The end of this loop must be reached by 'break'. At least one logfile
    // must be the current logfile. So now 'it' points to the current logfile.
    // We save that pointer for later.
    _logfiles_t::iterator queryit = it;

    // [2] Delete message classes irrelevent to current query
    // Starting from the current logfile (wo broke out of the
    // previous loop just when 'it' pointed to that)
    for (; it != _logfiles.end(); ++it)
    {
        Logfile *log = it->second;
        if (log->numEntries() > 0 && (log->classesRead() & ~logclasses) != 0) {
            if (g_debug_level > 2)
                debug("Freeing classes 0x%02x of file %s", ~logclasses, log->path());
            long freed = log->freeMessages(~logclasses); // flush only messages not needed for current query
            num_cached_log_messages -= freed;
            if (num_cached_log_messages <= _max_cached_messages) {
                _num_at_last_check = num_cached_log_messages;
                return;
            }
        }
    }

    // [3] Flush newest logfiles
    // If there are still too many messages loaded, continue
    // flushing logfiles from the oldest to the newest starting
    // at the file just after (i.e. newer than) the current logfile
    for (it = ++queryit; it != _logfiles.end(); ++it)
    {
        Logfile *log = it->second;
        if (log->numEntries() > 0) {
            debug("Flush newer log, msgs %d", log->numEntries());
            num_cached_log_messages -= log->numEntries();
            log->flush();
            if (num_cached_log_messages <= _max_cached_messages) {
                _num_at_last_check = num_cached_log_messages;
                return;
            }
        }
    }
    _num_at_last_check = num_cached_log_messages;
    // If we reach this point, no more logfiles can be unloaded,
    // despite the fact that there are still too many messages
    // loaded.

    if (g_debug_level > 2)
        debug("Cannot unload more messages. Still %d loaded (max is %d)",
                num_cached_log_messages, _max_cached_messages);
}

