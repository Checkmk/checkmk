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
#include "TableStateHistory.h"
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
#include "LogCache.h"


#define CHECK_MEM_CYCLE 1000 /* Check memory every N'th new message */

// watch nagios' logfile rotation
extern int g_debug_level;


// Debugging logging is hard if debug messages are logged themselves...
void debug_statehist(const char *loginfo, ...)
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


TableStateHistory::TableStateHistory()
{
	debug_statehist("INIT STATE HIST");
    HostServiceState *ref = 0;
    addColumn(new OffsetTimeColumn("time",
                "Time of the log event (UNIX timestamp)", (char *)&(ref->time) - (char *)ref, -1));
    addColumn(new OffsetTimeColumn("from",
                "Time of HostServiceState Start (UNIX timestamp)", (char *)&(ref->from) - (char *)ref, -1));
    addColumn(new OffsetTimeColumn("until",
                "Time at HostServiceState End (UNIX timestamp)", (char *)&(ref->until) - (char *)ref, -1));
    addColumn(new OffsetTimeColumn("duration",
                 "HostServiceState duration (UNIX timestamp)", (char *)&(ref->duration) - (char *)ref, -1));
    addColumn(new OffsetIntColumn("attempt",
                "The number of the check attempt", (char *)&(ref->attempt) - (char *)ref, -1));
    addColumn(new OffsetIntColumn("hard_state",
                 "Hard State", (char *)&(ref->state) - (char *)ref, -1));
    addColumn(new OffsetIntColumn("in_downtime",
                 "In downtime", (char *)&(ref->in_downtime) - (char *)ref, -1));
    addColumn(new OffsetIntColumn("state",
    		"The state of the host or service in question", (char *)&(ref->state) - (char *)ref, -1));


    sla_info = new SLA_Info();

    // join host and service tables
//    g_table_hosts->addColumns(this, "current_host_",    (char *)&(ref->host)    - (char *)ref);
//    g_table_services->addColumns(this, "current_service_", (char *)&(ref->_service) - (char *)ref, false /* no hosts table */);
//    g_table_contacts->addColumns(this, "current_contact_", (char *)&(ref->_contact) - (char *)ref);
//    g_table_commands->addColumns(this, "current_command_", (char *)&(ref->_command) - (char *)ref);
}


TableStateHistory::~TableStateHistory()
{
}


void TableStateHistory::answerQuery(Query *query)
{
	debug_statehist("ANSWER STATE HIST QUERY ");
    // since logfiles are loaded on demand, we need
    // to lock out concurrent threads.
	LogCache::handle->lockLogCache();
	LogCache::handle->logCachePreChecks();

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
    	debug_statehist("Classmask == 0");
    	LogCache::handle->unlockLogCache();
    	return;
    }

    _logfiles_t::iterator it;
    it = LogCache::handle->_logfiles.end(); // it now points beyond last log file
    --it; // switch to last logfile (we have at least one)

    // Now find newest log where 'until' is contained. The problem
    // here: For each logfile we only know the time of the *first* entry,
    // not that of the last.
    while (it != LogCache::handle->_logfiles.begin() && it->first > until) // while logfiles are too new...
    	--it; // go back in history

    if (it->first > until)  { // all logfiles are too new
        debug_statehist("Alle logs zu neu");
    	LogCache::handle->unlockLogCache();
        return;
    }

    // Get entries from Logfile handle
    Logfile *log = it->second;
    entries_t* entries = log->getEntriesFromQuery(query, LogCache::handle, since, until, classmask);
    entries_t::iterator it_entries = entries->begin();

    // Logfile Start: Anfangsstati ermitteln und in Map eintragen
    LogEntry *entry;


    // TODO: cycle through all logfiles

    // PHASE: pre-since
    // Collect and Update HostServiceState
    while (it_entries != entries->end())
    {
       entry = it_entries->second;
       if (entry->_time >= since){
    	   break;
       }
       // Host entry
       if (entry->_host_name != NULL){
           HostServiceKey key;
    	   key.first = entry->_host_name;
           if (entry->_svc_desc != NULL){
        	   key.second = entry->_svc_desc;
           }
           // Create HostServiceState if none exists
           if ( sla_info->find(key) == sla_info->end() ){
        	   HostServiceState state;
        	   state.from = since;
        	   state.state = entry->_state;
        	   state.attempt = entry->_attempt;
        	   sla_info->insert(std::make_pair(key, state));
           }
           // TODO: doppeltes find entfernenl, wieder auf only_update umschalten
    	   updateHostServiceState(*query, *entry, sla_info->find(key)->second, true);
       }

       // TODO:
       // Timeperiod Transition
       // Update all host entries
       ++it_entries;
    }

    LogCache::handle->unlockLogCache();
    sla_info->clear();
}

void TableStateHistory::updateHostServiceState(Query &query, LogEntry &entry, HostServiceState &hs_state, bool only_update){
	// Update duration

	hs_state.until    = entry._time;
	hs_state.duration = hs_state.until - hs_state.from;
	ProcessDataSet dataset(&query, &hs_state, only_update);

	if( entry._logclass == LOGCLASS_ALERT ){
		// TODO: strncmp entfernen, das wird im Logentry.cc bereits ermittelt. Hier wird dann nur noch die enum/etc. ausgewertet
		debug_statehist("process entry %s",entry._text);

		// Check DOWNTIME changes
		if( !strncmp(entry._text, "HOST DOWNTIME ALERT: ", 19) || !strncmp(entry._text, "SERVICE DOWNTIME ALERT: ", 22)){
			debug_statehist("DER DOWNTIME ALARM. hs_state time %d from %d until %d duration %d",entry._time,  hs_state.from, hs_state.until, hs_state.duration);

			if( strcmp( hs_state.state_type, entry._state_type ) != 0 ){
				debug_statehist("DOWNTIME STATE CHANGE: %s %s <%s> <%s>", entry._host_name, entry._svc_desc, hs_state.state_type, entry._state_type);
				dataset.tryProcess();
				hs_state.state_type = strdup(entry._state_type);
			}
		}

		// Check State changes
		if( !strncmp(entry._text, "SERVICE ALERT", 13) ){
			debug_statehist("DER SERVICE ALARM. hs_state time %d from %d until %d duration %d",entry._time,  hs_state.from, hs_state.until, hs_state.duration);

			if( hs_state.state != entry._state ){
				debug_statehist("STATE CHANGE:  %s %s <%d> <%d>", entry._host_name, entry._svc_desc, hs_state.state, entry._state);
				debug_statehist("processed %d", dataset.tryProcess());
				hs_state.state_type = strdup(entry._state_type);
			}
		}
	}
}

bool TableStateHistory::isAuthorized(contact *ctc, void *data)
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

Column *TableStateHistory::column(const char *colname)
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
