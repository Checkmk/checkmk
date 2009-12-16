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



/* Es fehlt noch:

   - Wenn Nagios eine neue Logdatei ins Archiv reinrotiert,
     dann muss ich diese neu in den Index aufnehmen. Gleichzeitig
     muss ich die bestehende nagios.log aus dem Archiv entfernen.

   - Die aktuelle Logdatei (watch) muss bei jedem Zugriff auf
     die Größe geprüft werden. Wenn sie größer geworden ist,
     dann muss ich den Rest neu einlesen. Ich könnte außerdem
     die Inode-Nummer beobachten. Wenn sich diese geändert hat,
     gehe ich von einer Rotation aus und mach das, was oben
     beschrieben ist.

   - Eine Optimierung der Bereichsanfrage

   - Ein Lock auf TableLog, da hier ändernde Operationen
     stattfinden.

   - Etliche Meldungstypen: Programm-Meldungen (Neustart),
     Eventhandler-Meldungen, und was gibt es noch?
     Die Verknuefpungen der External-Commands stellen wir
     noch zurueck.


*/

int num_cached_log_messages = 0;

TableLog::TableLog()
{
    LogEntry *ref = 0;
    addColumn(new OffsetIntColumn("time", 
		"Time of the log event (UNIX timestamp)", (char *)&(ref->_time) - (char *)ref, -1));
    addColumn(new OffsetIntColumn("class", 
		"The class of the message as integer (0:info, 1:state, 2:program, 3:notification, 4:passive, 5:command)", (char *)&(ref->_logtype) - (char *)ref, -1));

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
    for (_logfiles_t::iterator it = _logfiles.begin();
	    it != _logfiles.end();
	    ++it)
    {
	delete it->second;
    }
}


void TableLog::answerQuery(Query *query)
{
    time_t since = 0;
    time_t until = time(0);
    // query->findTimerangeFilter("time", &since, &until);
    _logfiles_t::iterator it = _logfiles.lower_bound(since);
    while (it != _logfiles.end()) {
	Logfile *log = it->second;
	if (!log->answerQuery(query, since, until, LOGTYPE_ALL))
	    break; // end of time range in this logfile
	++it;
    }
}


extern char *log_file;
extern char *log_archive_path;

void TableLog::updateLogfileIndex()
{
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

