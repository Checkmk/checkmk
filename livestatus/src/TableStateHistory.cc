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
#include "OffsetDoubleColumn.h"
#include "Query.h"
#include "Logfile.h"
#include "tables.h"
#include "TableServices.h"
#include "TableHosts.h"
#include "TableCommands.h"
#include "TableContacts.h"
#include "auth.h"
#include "LogCache.h"
#include "OutputBuffer.h"

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
    HostServiceState *ref = 0;
    addColumn(new OffsetTimeColumn("time",
                "Time of the log event (UNIX timestamp)", (char *)&(ref->_time) - (char *)ref, -1));
    addColumn(new OffsetTimeColumn("from",
                "Start time of state (UNIX timestamp)", (char *)&(ref->_from) - (char *)ref, -1));
    addColumn(new OffsetTimeColumn("until",
                "End time of state (UNIX timestamp)", (char *)&(ref->_until) - (char *)ref, -1));
    addColumn(new OffsetTimeColumn("duration",
                 "Duration of state ( until - from ) (UNIX timestamp)", (char *)&(ref->_duration) - (char *)ref, -1));
    addColumn(new OffsetDoubleColumn("duration_perc",
                "Duration percentage of query timeframe", (char *)(&ref->_duration_perc) - (char *)ref, -1));
    addColumn(new OffsetIntColumn("attempt",
                "The number of the check attempt", (char *)&(ref->_attempt) - (char *)ref, -1));
    addColumn(new OffsetIntColumn("state",
    		"The state of the host or service in question", (char *)&(ref->_state) - (char *)ref, -1));
    addColumn(new OffsetStringColumn("state_type",
    		"The type of the state (varies on different log classes)", (char *)&(ref->_state_alert) - (char *)ref, -1));
    addColumn(new OffsetIntColumn("in_downtime",
    		"Shows if the host/service is in downtime", (char *)&(ref->_in_downtime) - (char *)ref, -1));
    addColumn(new OffsetIntColumn("is_flapping",
    		"Shows if the host/service is flapping", (char *)&(ref->_is_flapping) - (char *)ref, -1));
    addColumn(new OffsetIntColumn("in_notification_period",
        		"Shows if the host/service is within its notification period", (char *)&(ref->_in_notification_period) - (char *)ref, -1));
    addColumn(new OffsetStringColumn("notification_period",
        		"Shows if the host/service notification period", (char *)&(ref->_notification_period) - (char *)ref, -1));
    addColumn(new OffsetStringColumn("debug_info",
                 "The type of the state (varies on different log classes)", (char *)&(ref->_prev_debug_info) - (char *)ref, -1));
    addColumn(new OffsetStringColumn("host_name",
                 "Host name", (char *)&(ref->_host_name) - (char *)ref, -1));
    addColumn(new OffsetStringColumn("service_description",
                 "Service description", (char *)&(ref->_service_description) - (char *)ref, -1));

    // FIXME: test
    addColumn(new OffsetStringColumn("log_text",
    			  "Complete Text of Logentry", (char *)&(ref->_prev_log_text) - (char *)ref, -1));

    sla_info = new SLA_Info();

    // join host and service tables
    //g_table_hosts->addColumns(this, "current_host_",    (char *)&(ref->_host)    - (char *)ref);
    //g_table_services->addColumns(this, "current_service_", (char *)&(ref->_service) - (char *)ref, false /* no hosts table */);

}

TableStateHistory::~TableStateHistory()
{
}

void TableStateHistory::answerQuery(Query *query)
{
	// since logfiles are loaded on demand, we need
    // to lock out concurrent threads.
	LogCache::Locker locker(0); // Lock Logcache and disable logfile cleanup
	LogCache::handle->logCachePreChecks();

    int since = 0;
    int until = time(0) + 1;
    // Optimize time interval for the query. In log querys
    // there should always be a time range in form of one
    // or two filter expressions over time. We use that
    // to limit the number of logfiles we need to scan and
    // to find the optimal entry point into the logfile

    query->findIntLimits("time", &since, &until);
    if (since == 0) {
    	query->setError(RESPONSE_CODE_INVALID_REQUEST, "Starttime filter required");
    	return;
    }
    _query_timeframe = until - 1 - since;

    // The second optimization is for log message types.
    // We want to load only those log type that are queried.
    uint32_t classmask = LOGCLASS_ALL;
    query->optimizeBitmask("class", &classmask);
    if (classmask == 0) {
    	debug_statehist("Classmask == 0");
    	return;
    }

    _logfiles_t::iterator it_logs;
    it_logs = LogCache::handle->_logfiles.end(); // it now points beyond last log file
    --it_logs; // switch to last logfile (we have at least one)

    // Now find log where 'since' is contained.
    while (it_logs != LogCache::handle->_logfiles.begin() && it_logs->first > since)
    	--it_logs; // go back in history

    if (it_logs->first > until)  { // all logfiles are too new, invalid timeframe
    	query->setError(RESPONSE_CODE_INVALID_REQUEST, "Invalid timeframe, logfiles too new");
    	return;
    }

    LogEntry *entry;
    entries_t* entries;
    entries_t::iterator it_entries;
    Logfile *log;
    // Find the logentry LOG VERSION: 2.0 just before the since timestamp
    // This indicates a fresh nagios startup containing all host/service initial states logged
	while (it_logs != LogCache::handle->_logfiles.begin()) {
		log = it_logs->second;
		bool version_found = false;
		entries = log->getEntriesFromQuery(query, LogCache::handle, since, until, classmask);
		it_entries = entries->end();
		while (it_entries != entries->begin())
		{
			--it_entries;
			if( it_entries->second->_time > since )
				break;
			if( it_entries->second->_logclass == LOGCLASS_LOG_VERSION){
				version_found = true;
				break;
			}
		}
		if (version_found)
			break;
		--it_logs;
	}

	HostServiceKey key;
	bool only_update = true;
	while (it_logs != LogCache::handle->_logfiles.end() ){
		log = it_logs->second;
		debug_statehist("Parse log %s", log->path());

		entries = log->getEntriesFromQuery(query, LogCache::handle, since, until, classmask);
		it_entries = entries->begin();

		while (it_entries != entries->end())
		{
			entry = it_entries->second;
			if(entry->_time >= until)
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
			case FLAPPING_HOST:
			case FLAPPING_SERVICE:
			{
				key.first = entry->_host_name;
				if (entry->_svc_desc != NULL)
					key.second = entry->_svc_desc;
				else
					key.second = "";
				if (sla_info->find(key) == sla_info->end()) {
					HostServiceState state;
					bzero(&state, sizeof(HostServiceState));
					state._from = since;
					state._state = entry->_state;
					state._attempt = entry->_attempt;
					state._host = entry->_host;
					state._host_name = entry->_host_name; // Used if state._host is unavailable
					state._service = entry->_service;
					state._service_description = entry->_svc_desc;

					if ( state._service != NULL ){
						state._notification_period = state._service->notification_period;
					}else if (state._host != NULL ){
						state._notification_period = entry->_host->notification_period;
					}else
						state._notification_period = "24x7";

					// intitial states - will be overridden soon
					state._in_notification_period = 1;
					state._log_ptr = entry; // unused
					state._log_text = entry->_complete;

					// log nonexistant state if this host/service
					// just appeared within the query timeframe
					if( ! only_update && entry->_time != since ){
						state._debug_info = "UNKNOWN ";
						state._state = -1;
						state._time  = entry->_time;
						state._until = entry->_time;
						process(query, &state, false);
						state._state = entry->_state;
					}
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
    char final_buffer[1024];
    sprintf(final_buffer,"Final log entry at %d", until-1);

    while( it_sla != sla_info->end() ){
    	HostServiceState* hst = &it_sla->second;
    	hst->_debug_info = "LOG FINAL";
    	hst->_prev_log_text = hst->_log_text;
    	hst->_time       = until - 1;
    	hst->_until      = hst->_time;
    	hst->_duration   = hst->_until - hst->_from;
		process(query, hst, false);
    	it_sla++;
    }

    sla_info->clear();
}


void TableStateHistory::updateHostServiceState(Query &query, LogEntry &entry, HostServiceState &hs_state, bool only_update){
	// Update time/until/duration
	hs_state._time     = entry._time;
	hs_state._until    = entry._time;
	hs_state._prev_log_text = hs_state._log_text;
	hs_state._log_text = entry._complete;
	hs_state._prev_debug_info = hs_state._debug_info;

	switch( entry._type ){
		case ALERT_HOST:
		case ALERT_SERVICE:{
			if( hs_state._state != entry._state ){
				hs_state._debug_info = "ALERT    ";
				process(&query, &hs_state, only_update);
				hs_state._state_alert = entry._state_type;
				hs_state._state = entry._state;
			}
			break;
		}
		case DOWNTIME_ALERT_HOST:
		case DOWNTIME_ALERT_SERVICE:{
			if( hs_state._state_downtime == NULL || strcmp( hs_state._state_downtime, entry._state_type ) ){
				hs_state._debug_info = "DOWNTIME ";
				process(&query, &hs_state, only_update);
				hs_state._state_downtime = entry._state_type;
				hs_state._in_downtime = !strncmp(hs_state._state_downtime,"STARTED",7) ? 1 : 0;
			}
			break;
		}
		case FLAPPING_HOST:
		case FLAPPING_SERVICE:{
			if( hs_state._is_flapping == 0 || strcmp( hs_state._state_flapping, entry._state_type ) ){
				hs_state._debug_info = "FLAPPING ";
				process(&query, &hs_state, only_update);
				hs_state._state_flapping= entry._state_type;
				hs_state._is_flapping = !strncmp(hs_state._state_flapping,"STARTED",7) ? 1 : 0;
			}
			break;
		}
		case TIMEPERIOD_TRANSITION:{
			// if no _host pointer is available the initial state(1) of _in_notification_period never changes
			if( hs_state._host && !strcmp(entry._command_name, hs_state._notification_period) ){
				int new_status = atoi(entry._state_type);
				if( new_status != hs_state._in_notification_period ){
					hs_state._debug_info = "TIMEPERI ";
					process(&query, &hs_state, only_update);
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
