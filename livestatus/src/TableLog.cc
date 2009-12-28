// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2009             mk@mathias-kettner.de |
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
#include "nagios.h"
#include "logger.h"
#include "TableLog.h"
#include "LogEntry.h"
#include "OffsetIntColumn.h"
#include "OffsetStringColumn.h"
#include "Query.h"
#include "Logfile.h"
#include "tables.h"
#include "TableServices.h"
#include "TableHosts.h"
#include "TableCommands.h"
#include "TableContacts.h"

#define CHECK_MEM_CYCLE 1000 /* Check memory every N'th new message */

// watch nagios' logfile rotation
extern time_t last_log_rotation;

/* Es fehlt noch:

   - Etliche Meldungstypen: Programm-Meldungen (Neustart),
     Eventhandler-Meldungen, und was gibt es noch?
     Die Verknuefpungen der External-Commands stellen wir
     noch zurueck.

   - Dokumentation dazu: Ueber die Klassen, die Verknuepfungen,
     die Speicherverwaltung, die Rotation, usw.

*/

int num_cached_log_messages = 0;

TableLog::TableLog(unsigned long max_cached_messages)
    : _max_cached_messages(max_cached_messages)
    , _num_cached_messages(0)
    , _num_at_last_check(0)
{
    pthread_mutex_init(&_lock, 0);

    LogEntry *ref = 0;
    addColumn(new OffsetIntColumn("time", 
		"Time of the log event (UNIX timestamp)", (char *)&(ref->_time) - (char *)ref, -1));
    addColumn(new OffsetIntColumn("class", 
		"The class of the message as integer (0:info, 1:state, 2:program, 3:notification, 4:passive, 5:command)", (char *)&(ref->_logclass) - (char *)ref, -1));

    addColumn(new OffsetStringColumn("message", 
		"The message (test)", (char *)&(ref->_text) - (char *)ref, -1));
    addColumn(new OffsetStringColumn("comment", 
		"A comment field used in various message types", (char *)&(ref->_comment) - (char *)ref, -1));
    addColumn(new OffsetStringColumn("plugin_output", 
		"The output of the check, if any is associated with the message", (char *)&(ref->_check_output) - (char *)ref, -1));
    addColumn(new OffsetIntColumn("state", 
		"The state of the host or service in question", (char *)&(ref->_state) - (char *)ref, -1));
    addColumn(new OffsetIntColumn("state_type", 
		"The type of the state (0: soft, 1: hard)", (char *)&(ref->_state_type) - (char *)ref, -1));
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
    if (classmask == 0)
	return;

    _logfiles_t::iterator it;
    if (since == 0)
	it = _logfiles.begin();
    else { // find oldest relevant logfile
	it = _logfiles.end();
	while (it != _logfiles.begin() &&
		(it == _logfiles.end() || it->first >= since))
	    --it;
    }
    while (it != _logfiles.end()) {
	Logfile *log = it->second;
	logger(LG_INFO, "HIRN: Jetzt kommt Logfile %s", log->path());
	if (!log->answerQuery(query, this, since, until, classmask))
	    break; // end of time range in this logfile
	++it;
    }
    dumpLogfiles();
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
    if (since)
	_logfiles.insert(make_pair(since, logfile));
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
	logger(LG_INFO, "LOG %s ab %d, %u messages, Klassen: 0x%04x", log->path(), log->since(), log->numEntries(), log->classesRead());
    }
}
    
void TableLog::handleNewMessage(Logfile *logfile, time_t since, time_t until, unsigned logclasses)
{
    if (++_num_cached_messages <= _max_cached_messages)
	return; // everything ok
    if (_num_cached_messages < _num_at_last_check + CHECK_MEM_CYCLE)
	return; // Do not check too often
    logger(LG_INFO, "HIRN: %d von %d erreicht", _num_cached_messages + 1, _max_cached_messages);

    logger(LG_INFO, "HIRN: Maximum number of cached log messages reached. Freeing memory");

    // [1] Begin by deleting old logfiles
    _logfiles_t::iterator it;
    for (it = _logfiles.begin(); it != _logfiles.end(); ++it)
    {
        Logfile *log = it->second;
	if (log == logfile) {
	    logger(LG_INFO, "HIRN: Loesche nicht %s", log->path());
	    break;
	}
	if (log->numEntries() > 0) {
	    logger(LG_INFO, "HIRN: Spuele %s weg", log->path());
	    _num_cached_messages -= log->numEntries();
	    log->flush();
	    if (_num_cached_messages <= _max_cached_messages)
		logger(LG_INFO, "HIRN: OK. Jetzt passts wieder (%d von %d)", _num_cached_messages, _max_cached_messages);
		_num_at_last_check = _num_cached_messages;
		return;
	}
    }

    // [2] Delete message classes irrelevent to current query
    for (; it != _logfiles.end(); ++it)
    {
        Logfile *log = it->second;
	if (log->numEntries() > 0) {
	    long freed = log->freeMessages(~logclasses);
	    _num_cached_messages -= freed;
	    logger(LG_INFO, "HIRN: %ld Meldungen aus %s weg", freed, log->path());
	    if (_num_cached_messages <= _max_cached_messages)
		logger(LG_INFO, "HIRN: OK. Jetzt passts wieder (%d von %d)", _num_cached_messages, _max_cached_messages);
		_num_at_last_check = _num_cached_messages;
		return;
	}
    }

    // [3] Flush newest logfiles
    it = _logfiles.end();
    while (true)
    {
	--it;
	Logfile *log = it->second;
	if (log == logfile)
	    break;

	if (log->numEntries() > 0) {
	    _num_cached_messages -= log->numEntries();
	    logger(LG_INFO, "HIRN: Logfile %s von hinten weggeschmissen (bin gerade bei %s)", log->path(), logfile->path());
	    log->flush();
	    if (_num_cached_messages <= _max_cached_messages) {
		_num_at_last_check = _num_cached_messages;
		logger(LG_INFO, "HIRN: OK. Jetzt passts wieder (%d von %d)", _num_cached_messages, _max_cached_messages);
		return;
	    }
	}
    }

    _num_at_last_check = _num_cached_messages;
    logger(LG_INFO, "HIRN: Cannot free enough memory");
}

