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
#include "Store.h"


#define CHECK_MEM_CYCLE 1000 /* Check memory every N'th new message */

// watch nagios' logfile rotation
extern Store *g_store;

TableLog::TableLog()
{
    addColumns(this, "", -1);
}

void TableLog::addColumns(Table *table, string prefix, int indirect_offset, bool add_host, bool add_services)
{
    LogEntry *ref = 0;
    table->addColumn(new OffsetTimeColumn(prefix + "time",
            "Time of the log event (UNIX timestamp)", (char *)&(ref->_time) - (char *)ref, indirect_offset));
    table->addColumn(new OffsetIntColumn(prefix + "lineno",
            "The number of the line in the log file", (char *)&(ref->_lineno) - (char *)ref, indirect_offset));
    table->addColumn(new OffsetIntColumn(prefix + "class",
            "The class of the message as integer (0:info, 1:state, 2:program, 3:notification, 4:passive, 5:command)", (char *)&(ref->_logclass) - (char *)ref, indirect_offset));
    table->addColumn(new OffsetStringColumn(prefix + "message",
            "The complete message line including the timestamp", (char *)&(ref->_complete) - (char *)ref, indirect_offset));
    table->addColumn(new OffsetStringColumn(prefix + "type",
            "The type of the message (text before the colon), the message itself for info messages", (char *)&(ref->_text) - (char *)ref, indirect_offset));
    table->addColumn(new OffsetStringColumn(prefix + "options",
            "The part of the message after the ':'", (char *)&(ref->_options) - (char *)ref, indirect_offset));
    table->addColumn(new OffsetStringColumn(prefix + "comment",
            "A comment field used in various message types", (char *)&(ref->_comment) - (char *)ref, indirect_offset));
    table->addColumn(new OffsetStringColumn(prefix + "plugin_output",
            "The output of the check, if any is associated with the message", (char *)&(ref->_check_output) - (char *)ref, indirect_offset));
    table->addColumn(new OffsetIntColumn(prefix + "state",
            "The state of the host or service in question", (char *)&(ref->_state) - (char *)ref, indirect_offset));
    table->addColumn(new OffsetStringColumn(prefix + "state_type",
            "The type of the state (varies on different log classes)", (char *)&(ref->_state_type) - (char *)ref, indirect_offset));
    table->addColumn(new OffsetIntColumn(prefix + "attempt",
            "The number of the check attempt", (char *)&(ref->_attempt) - (char *)ref, indirect_offset));
    table->addColumn(new OffsetStringColumn(prefix + "service_description",
            "The description of the service log entry is about (might be empty)",
            (char *)&(ref->_svc_desc) - (char *)ref, indirect_offset));
    table->addColumn(new OffsetStringColumn(prefix + "host_name",
            "The name of the host the log entry is about (might be empty)",
            (char *)&(ref->_host_name) - (char *)ref, indirect_offset));
    table->addColumn(new OffsetStringColumn(prefix + "contact_name",
            "The name of the contact the log entry is about (might be empty)",
            (char *)&(ref->_contact_name) - (char *)ref, indirect_offset));
    table->addColumn(new OffsetStringColumn(prefix + "command_name",
            "The name of the command of the log entry (e.g. for notifications)",
            (char *)&(ref->_command_name) - (char *)ref, indirect_offset));


    // join host and service tables
    if (add_host)
        g_table_hosts->addColumns(table, "current_host_",    (char *)&(ref->_host)    - (char *)ref);
    if (add_services)
        g_table_services->addColumns(table, "current_service_", (char *)&(ref->_service) - (char *)ref, false /* no hosts table */);
    g_table_contacts->addColumns(table, "current_contact_", (char *)&(ref->_contact) - (char *)ref);
    g_table_commands->addColumns(table, "current_command_", (char *)&(ref->_command) - (char *)ref);
}

TableLog::~TableLog()
{
}


void TableLog::answerQuery(Query *query)
{
    g_store->logCache()->lockLogCache();
    g_store->logCache()->logCachePreChecks();

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
        g_store->logCache()->unlockLogCache();
        return;
    }

    /* This code start with the oldest log entries. I'm going
       to change this and start with the newest. That way,
       the Limit: header produces more reasonable results. */

    /* NEW CODE - NEWEST FIRST */
    _logfiles_t::iterator it;
    it = g_store->logCache()->logfiles()->end(); // it now points beyond last log file
    --it; // switch to last logfile (we have at least one)

    // Now find newest log where 'until' is contained. The problem
    // here: For each logfile we only know the time of the *first* entry,
    // not that of the last.
    while (it != g_store->logCache()->logfiles()->begin() && it->first > until) // while logfiles are too new...
        --it; // go back in history
    if (it->first > until) { // all logfiles are too new
        g_store->logCache()->unlockLogCache();
        return;
    }

    while (true) {
        Logfile *log = it->second;
        if (!log->answerQueryReverse(query, g_store->logCache(), since, until, classmask))
            break; // end of time range found
        if (it == g_store->logCache()->logfiles()->begin())
            break; // this was the oldest one
        --it;
    }
    g_store->logCache()->unlockLogCache();
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
