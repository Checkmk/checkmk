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
#include "Store.h"

#define CHECK_MEM_CYCLE 1000 /* Check memory every N'th new message */

extern int g_debug_level;
extern Store *g_store;

//#define CLASSMASK_STATEHIST LOGCLASS_ALERT | LOGCLASS_PROGRAM | LOGCLASS_STATE
#define CLASSMASK_STATEHIST LOGCLASS_ALL


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

HostServiceState::~HostServiceState()
{
	debug_me("im destruktor!11");
	if (_check_output != NULL) {
		debug_me("im destruktor!11 %s",_check_output);
		free(_check_output);
	}
	if (_prev_check_output != NULL) {
		debug_me("im destruktor!11 prev %s",_prev_check_output);
		free(_prev_check_output);
	}
};

void HostServiceState::debug_me(const char *loginfo, ...)
{
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
                 "Duration of state (until - from) (UNIX timestamp)", (char *)&(ref->_duration) - (char *)ref, -1));
    addColumn(new OffsetDoubleColumn("duration_perc",
                "Duration percentage of query timeframe", (char *)(&ref->_duration_part) - (char *)ref, -1));
    addColumn(new OffsetIntColumn("state",
            "The state of the host or service in question", (char *)&(ref->_state) - (char *)ref, -1));
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
    addColumn(new OffsetStringColumn("check_output",
                 "Service description", (char *)&(ref->_prev_check_output) - (char *)ref, -1));

    addColumn(new OffsetTimeColumn("duration_ok",
                 "OK duration of state ( until - from ) (UNIX timestamp)", (char *)&(ref->_duration_state_OK) - (char *)ref, -1));
    addColumn(new OffsetDoubleColumn("duration_part_ok",
                "OK duration percentage of query timeframe", (char *)(&ref->_duration_part_OK) - (char *)ref, -1));

    addColumn(new OffsetTimeColumn("duration_warning",
                 "WARNING duration of state ( until - from ) (UNIX timestamp)", (char *)&(ref->_duration_state_WARNING) - (char *)ref, -1));
    addColumn(new OffsetDoubleColumn("duration_part_warning",
                "WARNING duration percentage of query timeframe", (char *)(&ref->_duration_part_WARNING) - (char *)ref, -1));

    addColumn(new OffsetTimeColumn("duration_critical",
                 "CRITICAL duration of state ( until - from ) (UNIX timestamp)", (char *)&(ref->_duration_state_CRITICAL) - (char *)ref, -1));
    addColumn(new OffsetDoubleColumn("duration_part_critical",
                "CRITICAL duration percentage of query timeframe", (char *)(&ref->_duration_part_CRITICAL) - (char *)ref, -1));

    addColumn(new OffsetTimeColumn("duration_unknown",
                 "UNKNOWN duration of state ( until - from ) (UNIX timestamp)", (char *)&(ref->_duration_state_UNKNOWN) - (char *)ref, -1));
    addColumn(new OffsetDoubleColumn("duration_part_unknown",
                "UNKNOWN duration percentage of query timeframe", (char *)(&ref->_duration_part_UNKNOWN) - (char *)ref, -1));

    addColumn(new OffsetTimeColumn("duration_unmonitored",
                 "UNMONITORED duration of state ( until - from ) (UNIX timestamp)", (char *)&(ref->_duration_state_UNMONITORED) - (char *)ref, -1));
    addColumn(new OffsetDoubleColumn("duration_part_unmonitored",
                "UNMONITORED duration part of query timeframe", (char *)(&ref->_duration_part_UNMONITORED) - (char *)ref, -1));


    // join host and service tables
    g_table_hosts->addColumns(this, "current_host_", (char *)&(ref->_host)    - (char *)ref);
    g_table_services->addColumns(this, "current_service_", (char *)&(ref->_service) - (char *)ref, false /* no hosts table */);
}

LogEntry *TableStateHistory::getPreviousLogentry(){
	if (_it_entries == _entries->begin()) {
		// open previous logfile
		if (_it_logs == g_store->logCache()->_logfiles.begin()) {
			return NULL;
		}else{
			_it_logs--;
	        debug_statehist("getPrev: Parse log %s", _it_logs->second->path());
			_entries = _it_logs->second->getEntriesFromQuery(_query, g_store->logCache(), _since, _until, CLASSMASK_STATEHIST);
			_it_entries = _entries->end();
		}
	}
	return (--_it_entries)->second;
}

LogEntry *TableStateHistory::getNextLogentry(){
	if (++_it_entries == _entries->end()){
		if (++_it_logs == g_store->logCache()->_logfiles.end()){
			debug_statehist("Kein neueres log vorhanden");
			// prevent errors on subsequent getNextLogentry()
			--_it_entries;
			--_it_logs;
			return NULL;
		}else{
			debug_statehist("getNext: Open new log %s", _it_logs->second->path());
			_entries = _it_logs->second->getEntriesFromQuery(_query, g_store->logCache(), _since, _until, CLASSMASK_STATEHIST);
			_it_entries = _entries->begin();
		}
	}
	return _it_entries->second;
}

void TableStateHistory::answerQuery(Query *query)
{

	g_store->logCache()->lockLogCache();
	g_store->logCache()->logCachePreChecks();

	typedef map<HostServiceKey, HostServiceState*> state_info_t;
	state_info_t state_info;

//	 ____  _____ ____  _   _  ____
//	|  _ \| ____| __ )| | | |/ ___|
//	| | | |  _| |  _ \| | | | |  _
//	| |_| | |___| |_) | |_| | |_| |
//	|____/|_____|____/ \___/ \____|
	static int trigger = 0;
    extern int num_cached_log_messages;
    debug_statehist("\n\n\nCached messages: %d", num_cached_log_messages);
    _logfiles_t::iterator _it_debug = g_store->logCache()->_logfiles.begin();
    while( _it_debug != g_store->logCache()->_logfiles.end() ){
    	debug_statehist("######## Available logs %d %d %s", g_store->logCache()->_logfiles.size(), _it_debug->second->numEntries(), _it_debug->second->path());
    	_it_debug++;
    }

    debug_statehist("\n\nDurchlaufe ein paar Daten... ( trigger %d )\n=============================================", trigger);
    _it_logs = g_store->logCache()->_logfiles.begin();
    debug_statehist("Logfile handle %x", _it_logs->second);

	_it_logs->second->getEntriesFromQuery(query, g_store->logCache(), _since, _until, CLASSMASK_STATEHIST); // archive
	_it_logs->second->flush();

//
//    if (trigger == 0)
//    	_it_logs->second->getEntriesFromQuery(query, g_store->logCache(), _since, _until, CLASSMASK_STATEHIST); // archive
//
//    if (trigger == 2)
//    	_it_logs->second->flush();
//
//    if (trigger == 4){
//    	_it_logs->second->getEntriesFromQuery(query, g_store->logCache(), _since, _until, CLASSMASK_STATEHIST); // archive
//    	trigger = -1;
//    }
    trigger++;
    g_store->logCache()->unlockLogCache();
	debug_statehist("Und Ende");
    return;






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
        g_store->logCache()->unlockLogCache();
        return;
    }
    _query_timeframe = _until - _since;

    // Switch to last logfile (we have at least one)
    _it_logs = g_store->logCache()->_logfiles.end();
    --_it_logs;

    // Now find the log where 'since' starts.
    while (_it_logs != g_store->logCache()->_logfiles.begin() && _it_logs->first > _since)
    	--_it_logs; // go back in history
	debug_statehist("Since   %d befindet sich in %s", _since, _it_logs->second->path());


    // Check if 'until' is within these logfiles
    if (_it_logs->first > _until)  { // all logfiles are too new, invalid timeframe
        // No data available. Return empty result.
        g_store->logCache()->unlockLogCache();
        return;
    }

    // Set initial logentry
    // Further logfile traversal is handled via getPreviousLogentry() / getNextLogentry()
    _entries = _it_logs->second->getEntriesFromQuery(query, g_store->logCache(), _since, _until, CLASSMASK_STATEHIST);
    _it_entries = _entries->end();

    // Find the logentry LOG VERSION: 2.0 just before the 'since' timestamp
    // Due to log_initial_states = 1 all host/service initial states are logged here
    LogEntry* entry;
    bool version_found = false;

    while ((entry = getPreviousLogentry()) != NULL) {
    	if (entry->_time > _since)
    		continue;
    	if (entry->_type == LOG_VERSION) {
    		debug_statehist("\n>>>>>>>>>>>>>>>>> \nLOG_VERSION found in %s %d", _it_logs->second->path(), entry->_time);
    		version_found = true;
    		break;
    	}
    }
    if (!version_found){
    	query->setError(RESPONSE_CODE_INVALID_REQUEST, "Unable to find any LOG VERSION entries before query "
    			        "timeframe. Logfiles seem corrupted.");
    	g_store->logCache()->unlockLogCache();
    	return;
    }


    HostServiceKey key;
    bool only_update = true;
    while (0 != (entry = getNextLogentry()))
    {
        if (entry->_time >= _until) {
        	getPreviousLogentry();
        	debug_statehist("End of query timeframe reached");
        	break;
        }
        if (only_update && entry->_time >= _since) {
            // Reached start of query timeframe. From now on let's produce real output
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

    		HostServiceState *state;
    		state_info_t::iterator it_hst = state_info.find(key);
    		if (it_hst == state_info.end()) {
    			state = new HostServiceState();
        		state_info.insert(std::make_pair(key, state));

        		state->_from    = _since;
        		state->_host    = entry->_host;
        		state->_service = entry->_service;

        		state->_host_name           = it_hst->first.first.c_str();
        		state->_service_description = it_hst->first.second.c_str();

        		// Get notification period of host/service
        		// If this host/service is no longer availabe in nagios -> 24x7
        		if ( state->_service != NULL )
        			state->_notification_period = state->_service->notification_period;
        		else if (state->_host != NULL )
        			state->_notification_period = state->_host->notification_period;
        		else
        			state->_notification_period = "";

        		// Determine initial in_notification_period status
        		_notification_periods_t::const_iterator tmp_period = _notification_periods.find(state->_notification_period);
        		if (tmp_period != _notification_periods.end())
        			state->_in_notification_period = tmp_period->second;
        		else
        			state->_in_notification_period = 1;

        		// log nonexistant state if this host/service just appeared within the query timeframe
        		if (!only_update) {
        			state->_debug_info      = "NONEXISTANT ";
        			state->_state = -1;
        		}
        	}
    		else
    			state = it_hst->second;

    		updateHostServiceState(*query, *entry, *state, only_update);
        	break;
        }
        case TIMEPERIOD_TRANSITION:{
        	_notification_periods[entry->_command_name] = atoi(entry->_state_type);
        	state_info_t::iterator it_hst = state_info.begin();
        	while( it_hst != state_info.end()) {
        		updateHostServiceState(*query, *entry, *it_hst->second, only_update);
        		it_hst++;
        	}
        	break;
        }
        case NAGIOS_STARTING:{
        	// Each nagios startup increments the _state_unkown because the host/service may no longer exist
        	// If it still exists an INITIAL HOST/SERVICE state entry will follow up shortly
        	// We remember the _last_known_time in case of multiple nagios startups
        	// inbetween the reappearance -> ABSENT state
        	state_info_t::iterator it_hst = state_info.begin();
        	while (it_hst != state_info.end()) {
        		if (it_hst->second->_no_longer_exists == 0)
        			it_hst->second->_last_known_time = entry->_time;
        		it_hst->second->_no_longer_exists++;
        		it_hst++;
        	}
        }
        break;
        }
    }

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

    		state_info_t::iterator it_hst = state_info.find(key);
    		if (it_hst != state_info.end() && it_hst->second->_no_longer_exists == 1) {
    			it_hst->second->_state = entry->_state;
    			it_hst->second->_no_longer_exists = 0;
    		}
    	}
    }

    // Create final reports
    state_info_t::iterator it_hst = state_info.begin();
    char final_buffer[256];
    sprintf(final_buffer,"Final log entry at %d", _until-1);
    while (it_hst != state_info.end()) {
    	HostServiceState* hst = it_hst->second;
        hst->_debug_info = "LOG FINAL";
        if (hst->_prev_debug_info == NULL) {
            hst->_prev_debug_info = hst->_debug_info;
        }

        // No trace since the last nagios startup -> host/service has vanished
        if (hst->_no_longer_exists == 1){
        	// Log last known state up to nagios restart
        	hst->_time  = hst->_last_known_time;
        	hst->_until = hst->_last_known_time;
        	process(query, hst);

        	// Log absent state
        	hst->_state = -1;
        	hst->_until = hst->_time;
        	hst->_prev_debug_info = "NONEXISTANT ";
        }

        if( hst->_prev_check_output != NULL){
        	hst->_prev_check_output = hst->_check_output;
        }

        hst->_time       = _until - 1;
        hst->_until      = hst->_time;

       	process(query, hst);
        it_hst++;
    }
    g_store->logCache()->unlockLogCache();
}


void TableStateHistory::updateHostServiceState(Query &query, LogEntry &entry, HostServiceState &hs_state, bool only_update){
	// Handle UNMONITORED states
	if ( entry._type != TIMEPERIOD_TRANSITION && hs_state._no_longer_exists > 1 )
	{
		// Create existing entry for last known existance
		hs_state._until = hs_state._last_known_time;
		process(&query, &hs_state);
		// Reanimate this host/service
		// ============================
        // Apply latest notification period information and set the host_state to absent
		// The following source code will handle the creation of an absent entry
		// FIXME: cleanup various parameters. Flapping/Downtime/etc.
		_notification_periods_t::const_iterator it_status = _notification_periods.find(hs_state._notification_period);
        if (it_status != _notification_periods.end()) {
			hs_state._in_notification_period = it_status->second;
		}
        else{ // shouldnt happen
			hs_state._in_notification_period = 1;
		}
		hs_state._state = -1;
	}

	// Update basic information
	hs_state._time         = entry._time;
    hs_state._until        = entry._time;

    // Remember check plugin output (this and previous one)
    if (hs_state._prev_check_output)
    	free(hs_state._prev_check_output);
    hs_state._prev_check_output = hs_state._check_output;
    hs_state._check_output = entry._check_output ? strdup(entry._check_output) : 0;

    hs_state._prev_debug_info = hs_state._debug_info;

    // A timeperiod entry never brings an absent host into existance..
    if (entry._type != TIMEPERIOD_TRANSITION)
		hs_state._no_longer_exists = 0;

    switch (entry._type) {
    	case STATE_HOST:
    	case STATE_SERVICE:
        case ALERT_HOST:
        case ALERT_SERVICE:{
            if (hs_state._state != entry._state) {
            	hs_state._debug_info = "ALERT    ";
                if (!only_update)
                	process(&query, &hs_state);
                hs_state._state = entry._state;
            }
            break;
        }
        case DOWNTIME_ALERT_HOST:
        case DOWNTIME_ALERT_SERVICE:{
        	int downtime_active = !strncmp(entry._state_type,"STARTED",7) ? 1 : 0;
            if (hs_state._in_downtime != downtime_active) {
                hs_state._debug_info = "DOWNTIME ";
                if (!only_update)

                process(&query, &hs_state);
                hs_state._in_downtime = downtime_active;
            }
            break;
        }
        case FLAPPING_HOST:
        case FLAPPING_SERVICE:{
        	int flapping_active = !strncmp(entry._state_type,"STARTED",7) ? 1 : 0;
            if (hs_state._is_flapping != flapping_active) {
                hs_state._debug_info = "FLAPPING ";
                if (!only_update)
                	process(&query, &hs_state);
                hs_state._is_flapping = flapping_active;
            }
            break;
        }
        case TIMEPERIOD_TRANSITION:{
            // if no _host pointer is available the initial state(1) of _in_notification_period never changes
            if (hs_state._host && !strcmp(entry._command_name, hs_state._notification_period)) {
                int new_status = atoi(entry._state_type);
                if (new_status != hs_state._in_notification_period) {
                	hs_state._debug_info = "TIMEPERI ";
                    if (!only_update)
                    	process(&query, &hs_state);
                	hs_state._in_notification_period = new_status;
                }
            }
            break;
        }
    }
}

void TableStateHistory::process(Query *query, HostServiceState *hs_state)
{
	hs_state->_duration = hs_state->_until - hs_state->_from;
	hs_state->_duration_part = (double)hs_state->_duration / (double)_query_timeframe;

	bzero(&hs_state->_duration_state_UNMONITORED, sizeof(time_t) * 5 + sizeof(double) * 5);

	switch (hs_state->_state) {
	case -1:
		hs_state->_duration_state_UNMONITORED = hs_state->_duration;
		hs_state->_duration_part_UNMONITORED  = hs_state->_duration_part;
		break;
	case STATE_OK:
		hs_state->_duration_state_OK       = hs_state->_duration;
		hs_state->_duration_part_OK        = hs_state->_duration_part;
		break;
	case STATE_WARNING:
		hs_state->_duration_state_WARNING  = hs_state->_duration;
		hs_state->_duration_part_WARNING   = hs_state->_duration_part;
		break;
	case STATE_CRITICAL:
		hs_state->_duration_state_CRITICAL = hs_state->_duration;
		hs_state->_duration_part_CRITICAL  = hs_state->_duration_part;
		break;
	case STATE_UNKNOWN:
		hs_state->_duration_state_UNKNOWN  = hs_state->_duration;
		hs_state->_duration_part_UNKNOWN   = hs_state->_duration_part;
		break;
	default:
		break;
	}

	if (hs_state->_duration > 0)
		query->processDataset(hs_state);
	hs_state->_from = hs_state->_until;
};

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
