// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2012             mk@mathias-kettner.de |
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

#include "nagios.h"
#include "logger.h"
#include "TableLog.h"
#include "LogEntry.h"
#include "OffsetIntColumn.h"
#include "OffsetTimeColumn.h"
#include "OffsetStringColumn.h"
#include "Query.h"
#include "Logfile.h"
#include "tables.h"
#include "TableServices.h"
#include "TableHosts.h"
#include "TableCommands.h"
#include "TableContacts.h"
#include "auth.h"

#define CHECK_MEM_CYCLE 1000 /* Check memory every N'th new message */

// watch nagios' logfile rotation
extern time_t last_log_rotation;
extern int g_debug_level;

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


TableLog::TableLog(unsigned long max_cached_messages)
  : _num_cached_messages(0)
  , _max_cached_messages(max_cached_messages)
  , _num_at_last_check(0)
{
    pthread_mutex_init(&_lock, 0);

    LogEntry *ref = 0;
    addColumn(new OffsetTimeColumn("time",
                "Time of the log event (UNIX timestamp)", (char *)&(ref->_time) - (char *)ref, -1));
    addColumn(new OffsetIntColumn("lineno",
                "The number of the line in the log file", (char *)&(ref->_lineno) - (char *)ref, -1));
    addColumn(new OffsetIntColumn("class",
                "The class of the message as integer (0:info, 1:state, 2:program, 3:notification, 4:passive, 5:command)", (char *)&(ref->_logclass) - (char *)ref, -1));

    addColumn(new OffsetStringColumn("message",
                "The complete message line including the timestamp", (char *)&(ref->_complete) - (char *)ref, -1));
    addColumn(new OffsetStringColumn("type",
                "The type of the message (text before the colon), the message itself for info messages", (char *)&(ref->_text) - (char *)ref, -1));
    addColumn(new OffsetStringColumn("options",
                "The part of the message after the ':'", (char *)&(ref->_options) - (char *)ref, -1));
    addColumn(new OffsetStringColumn("comment",
                "A comment field used in various message types", (char *)&(ref->_comment) - (char *)ref, -1));
    addColumn(new OffsetStringColumn("plugin_output",
                "The output of the check, if any is associated with the message", (char *)&(ref->_check_output) - (char *)ref, -1));
    addColumn(new OffsetIntColumn("state",
                "The state of the host or service in question", (char *)&(ref->_state) - (char *)ref, -1));
    addColumn(new OffsetStringColumn("state_type",
                "The type of the state (varies on different log classes)", (char *)&(ref->_state_type) - (char *)ref, -1));
    addColumn(new OffsetIntColumn("attempt",
                "The number of the check attempt", (char *)&(ref->_attempt) - (char *)ref, -1));
    addColumn(new OffsetStringColumn("service_description",
                "The description of the service log entry is about (might be empty)",
                (char *)&(ref->_svc_desc) - (char *)ref, -1));
    addColumn(new OffsetStringColumn("host_name",
                "The name of the host the log entry is about (might be empty)",
                (char *)&(ref->_host_name) - (char *)ref, -1));
    addColumn(new OffsetStringColumn("contact_name",
                "The name of the contact the log entry is about (might be empty)",
                (char *)&(ref->_contact_name) - (char *)ref, -1));
    addColumn(new OffsetStringColumn("command_name",
                "The name of the command of the log entry (e.g. for notifications)",
                (char *)&(ref->_command_name) - (char *)ref, -1));

    // join host and service tables
    g_table_hosts->addColumns(this, "current_host_",    (char *)&(ref->_host)    - (char *)ref);
    g_table_services->addColumns(this, "current_service_", (char *)&(ref->_service) - (char *)ref, false /* no hosts table */);
    g_table_contacts->addColumns(this, "current_contact_", (char *)&(ref->_contact) - (char *)ref);
    g_table_commands->addColumns(this, "current_command_", (char *)&(ref->_command) - (char *)ref);

    updateLogfileIndex();
}


TableLog::~TableLog()
{
    forgetLogfiles();
    pthread_mutex_destroy(&_lock);
}


void TableLog::forgetLogfiles()
{
    for (_logfiles_t::iterator it = _logfiles.begin();
            it != _logfiles.end();
            ++it)
    {
        delete it->second;
    }
    _logfiles.clear();
    _num_cached_messages = 0;
}


void TableLog::answerQuery(Query *query)
{
    // since logfiles are loaded on demand, we need
    // to lock out concurrent threads.
    pthread_mutex_lock(&_lock);

    // Do we have any logfiles (should always be the case,
    // but we don't want to crash...
    if (_logfiles.size() == 0) {
        pthread_mutex_unlock(&_lock);
        logger(LOG_INFO, "Warning: no logfile found, not even nagios.log");
        return;
    }

    // Has Nagios rotated logfiles? => Update
    // our file index. And delete all memorized
    // log messages.
    if (last_log_rotation > _last_index_update) {
        logger(LG_INFO, "Nagios has rotated logfiles. Rebuilding logfile index");
        forgetLogfiles();
        updateLogfileIndex();
    }

    int since = 0;
    int until = time(0) + 1;
    // Optimize time interval for the query. In log querys
    // there should always be a time range in form of one
    // or two filter expressions over time. We use that
    // to limit the number of logfiles we need to scan and
    // to find the optimal entry point into the logfile
    query->findIntLimits("time", &since, &until);

    // The second optimization is for log message types.
    // We want to load only those log type that are queried.
    uint32_t classmask = LOGCLASS_ALL;
    query->optimizeBitmask("class", &classmask);
    if (classmask == 0) {
        pthread_mutex_unlock(&_lock);
        return;
    }


    /* This code start with the oldest log entries. I'm going
       to change this and start with the newest. That way,
       the Limit: header produces more reasonable results. */

    /* NEW CODE - NEWEST FIRST */
    _logfiles_t::iterator it;
    it = _logfiles.end(); // it now points beyond last log file
    --it; // switch to last logfile (we have at least one)

    // Now find newest log where 'until' is contained. The problem
    // here: For each logfile we only know the time of the *first* entry,
    // not that of the last.
    while (it != _logfiles.begin() && it->first > until) // while logfiles are too new...
        --it; // go back in history
    if (it->first > until)  { // all logfiles are too new
        pthread_mutex_unlock(&_lock);
        return;
    }

    while (true) {
        Logfile *log = it->second;
        debug("Query is now at logfile %s, needing classes 0x%x", log->path(), classmask);
        if (!log->answerQueryReverse(query, this, since, until, classmask))
            break; // end of time range found
        if (it == _logfiles.begin())
            break; // this was the oldest one
        --it;
    }

    // dumpLogfiles();
    pthread_mutex_unlock(&_lock);
}


extern char *log_file;
extern char *log_archive_path;

void TableLog::updateLogfileIndex()
{
    _last_index_update = time(0);

    // We need to find all relevant logfiles. This includes
    // the current nagios.log and all files in the archive
    // directory.
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

void TableLog::scanLogfile(char *path, bool watch)
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

void TableLog::dumpLogfiles()
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
void TableLog::handleNewMessage(Logfile *logfile, time_t since __attribute__ ((__unused__)), time_t until __attribute__ ((__unused__)), unsigned logclasses)
{
    if (++_num_cached_messages <= _max_cached_messages)
        return; // current message count still allowed, everything ok

    /* Memory checking an freeing consumes CPU ressources. We save
       ressources, by avoiding to make the memory check each time
       a new message is loaded when being in a sitation where no
       memory can be freed. We do this by suppressing the check when
       the number of messages loaded into memory has not grown
       by at least CHECK_MEM_CYCLE messages */
    if (_num_cached_messages < _num_at_last_check + CHECK_MEM_CYCLE)
        return; // Do not check this time

    // [1] Begin by deleting old logfiles
    // Begin deleting with the oldest logfile available
    _logfiles_t::iterator it;
    for (it = _logfiles.begin(); it != _logfiles.end(); ++it)
    {
        Logfile *log = it->second;
        ///if (g_debug_level > 2)
        //    debug("Logfile %s (%s, %d entries)", log->path(), log == logfile ? "current" : "other", log->numEntries());
        if (log == logfile) {
            // Do not touch the logfile the Query is currently accessing
            // and
            break;
        }
        if (log->numEntries() > 0) {
            _num_cached_messages -= log->numEntries();
            log->flush(); // drop all messages of that file
            if (_num_cached_messages <= _max_cached_messages) {
                // remember the number of log messages in cache when
                // the last memory-release was done. No further
                // release-check shall be done until that number changes.
                _num_at_last_check = _num_cached_messages;
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
            _num_cached_messages -= freed;
            if (_num_cached_messages <= _max_cached_messages) {
                _num_at_last_check = _num_cached_messages;
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
            _num_cached_messages -= log->numEntries();
            log->flush();
            if (_num_cached_messages <= _max_cached_messages) {
                _num_at_last_check = _num_cached_messages;
                return;
            }
        }
    }
    _num_at_last_check = _num_cached_messages;
    // If we reach this point, no more logfiles can be unloaded,
    // despite the fact that there are still too many messages
    // loaded.
    if (g_debug_level > 2)
        debug("Cannot unload more messages. Still %d loaded (max is %d)",
                _num_cached_messages, _max_cached_messages);
}

bool TableLog::isAuthorized(contact *ctc, void *data)
{
    LogEntry *entry = (LogEntry *)data;
    service *svc = entry->_service;
    host *hst = entry->_host;

    if (hst || svc)
        return is_authorized_for(ctc, hst, svc);
    // suppress entries for messages that belong to
    // hosts that do not exist anymore.
    else if (entry->_logclass == LOGCLASS_ALERT
        || entry->_logclass == LOGCLASS_NOTIFICATION
        || entry->_logclass == LOGCLASS_PASSIVECHECK
        || entry->_logclass == LOGCLASS_STATE)
        return false;
    else
        return true;
}

Column *TableLog::column(const char *colname)
{
    // First try to find column in the usual way
    Column *col = Table::column(colname);
    if (col) return col;

    // Now try with prefix "current_", since our joined
    // tables have this prefix in order to make clear that
    // we access current and not historic data and in order
    // to prevent mixing up historic and current fields with
    // the same name.
    string with_current = string("current_") + colname;
    return Table::column(with_current.c_str());
}
