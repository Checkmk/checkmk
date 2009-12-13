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

TableLog::TableLog()
{
    LogEntry *ref = 0;
    addColumn(new OffsetIntColumn("time", 
		"Time of the log event (UNIX timestamp)", (char *)&(ref->_time) - (char *)ref, -1));

    addColumn(new OffsetStringColumn("message", 
		"The message (test)", (char *)&(ref->_msg) - (char *)ref, -1));
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
    time_t since = time(0);
    time_t until = 0;
    query->findTimerangeFilter("time", &since, &until);

    _logfiles_t::iterator it = findLogfileStartingBefore(since);
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
	while (0 == readdir_r(dir, ent, &result))
	{
	   if (ent->d_name[0] != '.') {
	       snprintf(abspath, sizeof(abspath), "%s/%s", log_archive_path, ent->d_name);
	       scanLogfile(abspath, false);
	   }
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

