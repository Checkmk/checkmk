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

    FILE *x = fopen("/tmp/livestatus_state.log", "a+");
    va_list ap;
    va_start(ap, loginfo);
    vfprintf(x, loginfo, ap);
    fputc('\n', x);
    va_end(ap);
    fclose(x);
}


TableStateHistory::TableStateHistory()
{
	logger(LG_CRIT, "INIT STATE HIST");

    HostServiceState *ref = 0;
    addColumn(new OffsetTimeColumn("time",
                "Time of the log event (UNIX timestamp)", (char *)&(ref->_time) - (char *)ref, -1));
    addColumn(new OffsetTimeColumn("from",
                "Time of HostServiceState Start (UNIX timestamp)", (char *)&(ref->_from) - (char *)ref, -1));
    addColumn(new OffsetTimeColumn("until",
                "Time at HostServiceState End (UNIX timestamp)", (char *)&(ref->_until) - (char *)ref, -1));
    addColumn(new OffsetTimeColumn("duration",
                 "HostServiceState duration (UNIX timestamp)", (char *)&(ref->_duration) - (char *)ref, -1));
    addColumn(new OffsetIntColumn("attempt",
                "The number of the check attempt", (char *)&(ref->_attempt) - (char *)ref, -1));
    addColumn(new OffsetIntColumn("hard_state",
                 "Hard State", (char *)&(ref->_state) - (char *)ref, -1));
    addColumn(new OffsetIntColumn("state",
    		"The state of the host or service in question", (char *)&(ref->_state) - (char *)ref, -1));
    addColumn(new OffsetIntColumn("in_downtime",
        		"Shows if the host/service is in downtime", (char *)&(ref->_in_downtime) - (char *)ref, -1));
    addColumn(new OffsetStringColumn("notification_period",
        		"Shows if the host/service notification period", (char *)&(ref->_notification_period) - (char *)ref, -1));
    addColumn(new OffsetIntColumn("in_notification_period",
        		"Shows if the host/service is within its notification period", (char *)&(ref->_in_notification_period) - (char *)ref, -1));
    addColumn(new OffsetStringColumn("state_type",
                 "The type of the state (varies on different log classes)", (char *)&(ref->_state_type) - (char *)ref, -1));
    addColumn(new OffsetStringColumn("debug_info",
                 "The type of the state (varies on different log classes)", (char *)&(ref->_debug_info) - (char *)ref, -1));
    addColumn(new OffsetStringColumn("host_name",
                 "Host name", (char *)&(ref->_host_name) - (char *)ref, -1));
    addColumn(new OffsetStringColumn("svc_description",
                 "Service description", (char *)&(ref->_svc_desc) - (char *)ref, -1));



    sla_info = new SLA_Info();

    // join host and service tables
    g_table_hosts->addColumns(this, "current_host_",    (char *)&(ref->_host)    - (char *)ref);
    g_table_services->addColumns(this, "current_service_", (char *)&(ref->_service) - (char *)ref, false /* no hosts table */);
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

    _logfiles_t::iterator it_logs;
    it_logs = LogCache::handle->_logfiles.end(); // it now points beyond last log file
    --it_logs; // switch to last logfile (we have at least one)

    // Now find newest log where 'until' is contained. The problem
    // here: For each logfile we only know the time of the *first* entry,
    // not that of the last.
    while (it_logs != LogCache::handle->_logfiles.begin() && it_logs->first > since) // while logfiles are too new...
    	--it_logs; // go back in history

    if (it_logs->first > until)  { // all logfiles are too new
        debug_statehist("Alle logs zu neu");
    	LogCache::handle->unlockLogCache();
    	return;
    }

    LogEntry *entry;
	HostServiceKey key;
	bool only_update = true;



	while( it_logs != LogCache::handle->_logfiles.end() ){
		Logfile *log = it_logs->second;
		debug_statehist("Parse log %s", log->path());

		entries_t* entries = log->getEntriesFromQuery(query, LogCache::handle, since, until, classmask);
		entries_t::iterator it_entries = entries->begin();

		while (it_entries != entries->end())
		{
			entry = it_entries->second;
			if(entry->_time > until)
				break;
			if(only_update && entry->_time >= since){
				only_update = false;
			}

			switch( entry->_type){
			case DOWNTIME_ALERT_SERVICE:
			case DOWNTIME_ALERT_HOST:
			case STATE_SERVICE:
			case STATE_HOST:
			case ALERT_SERVICE:
			case ALERT_HOST:
			{
				key.first = entry->_host_name;
				if ( entry->_svc_desc != NULL )
					key.second = entry->_svc_desc;
				else
					key.second = "";
				if ( sla_info->find(key) == sla_info->end() ){
					HostServiceState state;
					bzero(&state, sizeof(HostServiceState));
					state._from = since;
					state._state = entry->_state;
					state._attempt = entry->_attempt;
					state._host = entry->_host;
					state._host_name = entry->_host_name; // Used if state._host is unavailable
					state._service = entry->_service;
					state._svc_desc = entry->_svc_desc;

					if( state._service != NULL ){
						state._notification_period = state._service->notification_period;
					}else if (state._host != NULL ){
						state._notification_period = entry->_host->notification_period;
					}else
						state._notification_period = "24x7"; // TODO: pruefen

					// TODO: weg damit
					state._downtime_state = "";
					state._in_notification_period = 1;

					state._log_ptr = entry;

					debug_statehist("NEW KEY %s %s", state._host_name, state._svc_desc);
					sla_info->insert(std::make_pair(key, state));
				}
				updateHostServiceState(*query, *entry, sla_info->find(key)->second, only_update);
				break;
			}
			case TIMEPERIOD_TRANSITION:{
				SLA_Info::iterator it_sla = sla_info->begin();
				while( it_sla != sla_info->end() ){
					updateHostServiceState(*query, *entry, it_sla->second, only_update);
					it_sla++;
				}
				break;
			}
			}
			++it_entries;
		}
    	++it_logs;
    }

    // Create final reports
    SLA_Info::iterator it_sla = sla_info->begin();
    while( it_sla != sla_info->end() ){
    	HostServiceState* hst = &it_sla->second;
    	hst->_debug_info = "LOG FINAL LINE    ";
    	hst->_time       = until - 1;
    	hst->_until      = hst->_time;
    	hst->_duration   = hst->_until - hst->_from;
    	ProcessDataSet dataset(query, &it_sla->second, false);
    	dataset.process();
    	it_sla++;
    }

    LogCache::handle->unlockLogCache();
    sla_info->clear();
}

void print_hsstate(HostServiceState &hs_state){
	if( hs_state._service != NULL && hs_state._service->description != NULL )
		debug_statehist("HS STATE: \nhost %s\nservice %s", hs_state._host->name, hs_state._service->description);
	else
		debug_statehist("HS STATE: \nhost %s\n", hs_state._host->name);
	debug_statehist("from  %d\nuntil %d\nduration %d", hs_state._from, hs_state._until, hs_state._duration);
	debug_statehist("timeperiod %s", hs_state._notification_period);
	if( hs_state._state_type != NULL )
		debug_statehist("state_type %s\n\n", hs_state._state_type);
}

void TableStateHistory::updateHostServiceState(Query &query, LogEntry &entry, HostServiceState &hs_state, bool only_update){
	// Update time/until/duration
	hs_state._time     = entry._time;
	hs_state._until    = entry._time;
	hs_state._duration = hs_state._until - hs_state._from;
	ProcessDataSet dataset(&query, &hs_state, only_update);

	switch( entry._type ){
		case ALERT_HOST:
		case ALERT_SERVICE:{
			debug_statehist("entry time %d\n%s", entry._time, entry._complete);
			print_hsstate(hs_state);
			if( hs_state._state != entry._state ){
				hs_state._debug_info = "ALERT    TRIGGERED";
				dataset.process();
				hs_state._state_type = entry._state_type;
				hs_state._state = entry._state;
			}
			break;
		}
		case DOWNTIME_ALERT_SERVICE:
		case DOWNTIME_ALERT_HOST:{
			if( strcmp( hs_state._downtime_state, entry._state_type ) ){
				hs_state._debug_info = "DOWNTIME TRIGGERED";
				dataset.process();
				hs_state._downtime_state = entry._state_type;
				hs_state._in_downtime = strncmp(hs_state._downtime_state,"STARTED",7) ? 1 : 0;
			}
			break;
		}
		case TIMEPERIOD_TRANSITION:{
			if( !strcmp(entry._command_name, hs_state._notification_period) ){
				int new_status = atoi(entry._state_type);
				if( new_status != hs_state._in_notification_period ){
					hs_state._debug_info = "TIMEPERIOD TRIGGER";
					dataset.process();
					hs_state._in_notification_period = new_status;
				}
			}
			break;
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
