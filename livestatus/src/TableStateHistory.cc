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
#include "tables.h"
#include "TableLog.h"
#include "TableServices.h"
#include "TableHosts.h"
#include "TableCommands.h"
#include "TableContacts.h"
#include "auth.h"
#include "LogCache.h"
#include "OutputBuffer.h"
#include "vector"

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
                "Duration percentage of query timeframe", (char *)(&ref->_duration_part) - (char *)ref, -1));
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


    // FIXME: experimental fields
    addColumn(new OffsetTimeColumn("duration_ok",
                 "OK duration of state ( until - from ) (UNIX timestamp)", (char *)&(ref->_duration_state_OK) - (char *)ref, -1));
    addColumn(new OffsetDoubleColumn("duration_perc_ok",
                "OK duration percentage of query timeframe", (char *)(&ref->_duration_part_OK) - (char *)ref, -1));

    addColumn(new OffsetTimeColumn("duration_warning",
                 "WARNING duration of state ( until - from ) (UNIX timestamp)", (char *)&(ref->_duration_state_WARNING) - (char *)ref, -1));
    addColumn(new OffsetDoubleColumn("duration_perc_warning",
                "WARNING duration percentage of query timeframe", (char *)(&ref->_duration_part_WARNING) - (char *)ref, -1));

    addColumn(new OffsetTimeColumn("duration_critical",
                 "CRITICAL duration of state ( until - from ) (UNIX timestamp)", (char *)&(ref->_duration_state_CRITICAL) - (char *)ref, -1));
    addColumn(new OffsetDoubleColumn("duration_perc_critical",
                "CRITICAL duration percentage of query timeframe", (char *)(&ref->_duration_part_CRITICAL) - (char *)ref, -1));

    addColumn(new OffsetTimeColumn("duration_unknown",
                 "UNKNOWN duration of state ( until - from ) (UNIX timestamp)", (char *)&(ref->_duration_state_UNKNOWN) - (char *)ref, -1));
    addColumn(new OffsetDoubleColumn("duration_perc_unknown",
                "UNKNOWN duration percentage of query timeframe", (char *)(&ref->_duration_part_UNKNOWN) - (char *)ref, -1));

    addColumn(new OffsetTimeColumn("duration_nonexistant",
                 "NONEXISTANT duration of state ( until - from ) (UNIX timestamp)", (char *)&(ref->_duration_state_ABSENT) - (char *)ref, -1));
    addColumn(new OffsetDoubleColumn("duration_perc_NONEXISTANT",
                "NONEXISTANT duration percentage of query timeframe", (char *)(&ref->_duration_part_ABSENT) - (char *)ref, -1));


    sla_info = new SLA_Info();

    // join host, service and log tables
    g_table_hosts->addColumns(this, "current_host_", (char *)&(ref->_host)    - (char *)ref);
    g_table_services->addColumns(this, "current_service_", (char *)&(ref->_service) - (char *)ref, false /* no hosts table */);
    g_table_log->addColumns(this, "current_log_", (char *)&(ref->_prev_log_ptr) - (char *)ref, false, false); /* no hosts/services table */
}

TableStateHistory::~TableStateHistory()
{
}

LogEntry *TableStateHistory::getPreviousLogentry(){
	if (_it_entries == _entries->begin()) {
		// open previous logfile
		if (_it_logs == LogCache::handle->_logfiles.begin()) {
			return NULL;
		}else{
			_it_logs--;
	        debug_statehist("Parse log %s", _it_logs->second->path());
			_entries = _it_logs->second->getEntriesFromQuery(_query, LogCache::handle, _since, _until, _classmask);
			_it_entries = _entries->end();
		}
	}
	return (--_it_entries)->second;
}

LogEntry *TableStateHistory::getNextLogentry(){
	_it_entries++;
	if (_it_entries == _entries->end()) {
		_it_entries--; // prevent errors on subsequent getNextLogentry()
		// open next logfile
		_it_logs++;
		if (_it_logs == LogCache::handle->_logfiles.end()) {
			return NULL;
		}else{
			debug_statehist("Parse log %s", _it_logs->second->path());
			_entries = _it_logs->second->getEntriesFromQuery(_query, LogCache::handle, _since, _until, _classmask);
			_it_entries = _entries->begin();
		}
	}
	return _it_entries->second;
}

void TableStateHistory::answerQuery(Query *query)
{
    LogCache::Locker locker(0); // Lock Logcache and disable logfile cleanup
    LogCache::handle->logCachePreChecks();

    _query = query;
    _since = 0;
    _until = time(0) + 1;

    // Optimize time interval for the query. In log querys
    // there should always be a time range in form of one
    // or two filter expressions over time. We use that
    // to limit the number of logfiles we need to scan and
    // to find the optimal entry point into the logfile
    _query->findIntLimits("time", &_since, &_until);
    if (_since == 0) {
        query->setError(RESPONSE_CODE_INVALID_REQUEST, "Start of timeframe required. e.g. Filter: time > 1234567890");
        return;
    }
    _query_timeframe = _until - _since - 1;

    // The second optimization is for log message types.
    // We want to load only those log type that are queried.
    _classmask = LOGCLASS_ALL;
    query->optimizeBitmask("class", &_classmask);
    if (_classmask == 0) {
        debug_statehist("Classmask == 0");
        return;
    }

    // Switch to last logfile (we have at least one)
    _it_logs = LogCache::handle->_logfiles.end();
    --_it_logs;

    // Now find the log where 'since' starts.
    while (_it_logs != LogCache::handle->_logfiles.begin() && _it_logs->first > _since)
        --_it_logs; // go back in history

    // Check if 'until' is within these logfiles
    if (_it_logs->first > _until)  { // all logfiles are too new, invalid timeframe
        query->setError(RESPONSE_CODE_INVALID_REQUEST, "Invalid timeframe, logfiles too new");
        return;
    }

    // Set initial logentry
    // Further logfile traversal is handled via getPreviousLogentry() / getNextLogentry()
    _entries = _it_logs->second->getEntriesFromQuery(query, LogCache::handle, _since, _until, _classmask);
    _it_entries = _entries->end();

    // Find the logentry LOG VERSION: 2.0 just before the 'since' timestamp
    // Due to log_initial_states = 1 all host/service initial states are logged here
    LogEntry* entry;
    bool version_found = false;
    while ((entry = getPreviousLogentry()) != NULL) {
    	if (entry->_time > _since)
    		continue;
    	if (entry->_type == LOG_VERSION) {
    		debug_statehist("\nLOG_VERSION found in %s %d", _it_logs->second->path(), entry->_time);
    		version_found = true;
    		break;
    	}
    }
    if (!version_found)
    	query->setError(RESPONSE_CODE_INVALID_REQUEST, "Unable to find any LOG VERSION entries before query timeframe - data might be incomplete");

    // Notification periods information, name: active(1)/inactive(0)
    map<string,int> notification_periods;

    HostServiceKey key;
    bool only_update = true;
    while ((entry = getNextLogentry()) != NULL) {
        if (entry->_time >= _until) {
        	getPreviousLogentry(); //
        	debug_statehist("End of query timeframe reached");
        	break;
        }
        if (only_update && entry->_time >= _since) {
        	only_update = false;
        }

        switch (entry->_type) {
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
    		key.second = entry->_svc_desc != NULL ? entry->_svc_desc : "";

    		if (sla_info->find(key) == sla_info->end()) {
        		HostServiceState state;
        		bzero(&state, sizeof(HostServiceState));
        		state._from = _since;
        		state._state = entry->_state;
        		state._attempt = entry->_attempt;
        		state._host = entry->_host;
        		state._host_name = entry->_host_name;
        		state._service = entry->_service;
        		state._service_description = entry->_svc_desc;
        		state._log_ptr = entry;

        		// Get notification period of host/service
        		// If this host/service is no longer availabe in nagios -> 24x7
        		if ( state._service != NULL )
        			state._notification_period = state._service->notification_period;
        		else if (state._host != NULL )
        			state._notification_period = entry->_host->notification_period;
        		else
        			state._notification_period = "24x7";

        		// Determine initial in_notification_period status
        		map<string,int>::const_iterator tmp_period = notification_periods.find(state._notification_period);
        		if (tmp_period != notification_periods.end()) {
        			state._in_notification_period = tmp_period->second;
        		}

        		// log nonexistant state if this host/service just appeared within the query timeframe
        		if( ! only_update && entry->_time != _since ) {
        			state._debug_info = "NONEXISTANT ";
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
        	notification_periods[entry->_command_name] = atoi(entry->_state_type);
        	SLA_Info::iterator it_sla = sla_info->begin();
        	while( it_sla != sla_info->end()) {
        		updateHostServiceState(*query, *entry, it_sla->second, only_update);
        		it_sla++;
        	}
        	break;
        }
        case NAGIOS_STARTING:{
        	// each nagios startup sets the _state_unkown to 1 because the host/service may no longer
        	// exists within nagios. If it still exists an INITIAL HOST/SERVICE state entry will follow up shortly
        	// FIXME: what if 'until' falls between nagios startup and the INITIAL states?
        	SLA_Info::iterator it_sla = sla_info->begin();
        	while (it_sla != sla_info->end()) {
        		it_sla->second._no_longer_exists = 1;
        		it_sla++;
        	}
        }
        break;
        }
    }

    debug_statehist("Create final reports");
    // Process logentries up to 5 minutes into the future
    // There might have been a nagios startup right at the end of the query timeframe
    // This invalidates the existance of all hosts/services
    // So we additionally parse the next five minutes and look for any STATE entries
    // to reconfirm the hosts/services existance.
    while ((entry = getNextLogentry()) != NULL) {
    	// Exit if time limit is reached or another nagios startup happened
    	if (entry->_type == NAGIOS_STARTING || entry->_time >= _until + 300)
    		break;

    	if (entry->_type == STATE_HOST || entry->_type == STATE_SERVICE) {
    		key.first  = entry->_host_name;
    		key.second = entry->_svc_desc != NULL ? entry->_svc_desc : "";

    		SLA_Info::iterator it_sla = sla_info->find(key);
    		if (it_sla != sla_info->end() && it_sla->second._no_longer_exists == 1) {
    			it_sla->second._state = entry->_state;
    			it_sla->second._no_longer_exists = 0;
    		}
    	}
    }

    // Create final reports
    SLA_Info::iterator it_sla = sla_info->begin();
    char final_buffer[256];
    sprintf(final_buffer,"Final log entry at %d", _until-1);
    while (it_sla != sla_info->end()) {
        HostServiceState* hst = &it_sla->second;
        hst->_debug_info = "LOG FINAL";
        if (hst->_prev_debug_info == NULL) {
            hst->_prev_debug_info = hst->_debug_info;
        }
        hst->_prev_log_ptr = hst->_log_ptr;
        hst->_time       = _until - 1;
        hst->_until      = hst->_time;
        hst->_duration   = hst->_until - hst->_from;

        // No trace since the last nagios startup -> host/service has vanished
        if (hst->_no_longer_exists == 1)
        	hst->_state = -1;

        process(query, hst, false);
        it_sla++;
    }
    sla_info->clear();
}


void TableStateHistory::updateHostServiceState(Query &query, LogEntry &entry, HostServiceState &hs_state, bool only_update){
    // Update time/until/duration
	hs_state._no_longer_exists = 0;
    hs_state._time     = entry._time;
    hs_state._until    = entry._time;
    hs_state._prev_log_ptr = hs_state._log_ptr;
    hs_state._log_ptr = &entry;
    hs_state._prev_debug_info = hs_state._debug_info;

    switch( entry._type ){
        case ALERT_HOST:
        case ALERT_SERVICE:{
            if (hs_state._state != entry._state) {
                hs_state._debug_info = "ALERT    ";
                process(&query, &hs_state, only_update);
                hs_state._state_alert = entry._state_type;
                hs_state._state = entry._state;
            }
            break;
        }
        case DOWNTIME_ALERT_HOST:
        case DOWNTIME_ALERT_SERVICE:{
            if (hs_state._state_downtime == NULL || strcmp( hs_state._state_downtime, entry._state_type)) {
                hs_state._debug_info = "DOWNTIME ";
                process(&query, &hs_state, only_update);
                hs_state._state_downtime = entry._state_type;
                hs_state._in_downtime = !strncmp(hs_state._state_downtime,"STARTED",7) ? 1 : 0;
            }
            break;
        }
        case FLAPPING_HOST:
        case FLAPPING_SERVICE:{
            if (hs_state._is_flapping == 0 || strcmp( hs_state._state_flapping, entry._state_type)) {
                hs_state._debug_info = "FLAPPING ";
                process(&query, &hs_state, only_update);
                hs_state._state_flapping= entry._state_type;
                hs_state._is_flapping = !strncmp(hs_state._state_flapping,"STARTED",7) ? 1 : 0;
            }
            break;
        }
        case TIMEPERIOD_TRANSITION:{
            // if no _host pointer is available the initial state(1) of _in_notification_period never changes
            if (hs_state._host && !strcmp(entry._command_name, hs_state._notification_period)) {
                int new_status = atoi(entry._state_type);
                if (new_status != hs_state._in_notification_period) {
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
