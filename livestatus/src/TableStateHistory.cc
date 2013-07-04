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
#include <stdarg.h>

#include "nagios.h"
#include "logger.h"
#include "OffsetIntColumn.h"
#include "OffsetTimeColumn.h"
#include "OffsetStringColumn.h"
#include "OffsetDoubleColumn.h"
#include "Query.h"
#include "tables.h"
#include "auth.h"
#include "Store.h"
#include "LogEntry.h"
#include "TableStateHistory.h"

#ifdef CMC
#include "Host.h"
#include "Service.h"
#include "Timeperiod.h"
#endif


typedef pair<string, string> HostServiceKey;

struct HostServiceState {
    bool    _is_host;
    time_t  _time;
    int     _lineno;
    time_t  _from;
    time_t  _until;

    time_t  _duration;
    double  _duration_part;

    // Do not change order within this block!
    // These durations will be bzero'd
    time_t  _duration_state_UNMONITORED;
    double  _duration_part_UNMONITORED;
    time_t  _duration_state_OK;
    double  _duration_part_OK;
    time_t  _duration_state_WARNING;
    double  _duration_part_WARNING;
    time_t  _duration_state_CRITICAL;
    double  _duration_part_CRITICAL;
    time_t  _duration_state_UNKNOWN;
    double  _duration_part_UNKNOWN;

    // State information
    int     _host_down;      // used if service
    int     _state;             // -1/0/1/2/3
    int     _in_notification_period;
    int     _in_downtime;
    int     _in_host_downtime;
    int     _is_flapping;


    // Absent state handling
    bool    _may_no_longer_exist;
    bool    _has_vanished;
    time_t  _last_known_time;


    const char  *_debug_info;
    // Pointer to dynamically allocated strings (strdup) that live here.
    // These pointers are 0, if there is no output (e.g. downtime)
    char        *_log_output;
    char        *_notification_period;  // may be "": -> no period known, we assume "always"
    host        *_host;
    service     *_service;
    const char  *_host_name;            // Fallback if host no longer exists
    const char  *_service_description;  // Fallback if service no longer exists

    HostServiceState() { bzero(this, sizeof(HostServiceState)); }
    ~HostServiceState();
    void debug_me(const char *loginfo, ...);
};


#define CHECK_MEM_CYCLE 1000 /* Check memory every N'th new message */

extern Store *g_store;

#define CLASSMASK_STATEHIST 70


// Debugging logging is hard if debug messages are logged themselves...
void debug_statehist(const char *loginfo, ...)
{
    FILE *x = fopen("/tmp/livestatus_state.log", "a+");
    va_list ap;
    va_start(ap, loginfo);
    vfprintf(x, loginfo, ap);
    fputc('\n', x);
    va_end(ap);
    fclose(x);
}


// Debug output of HostServiceState struct
void log_hst(HostServiceState *state)
{
    debug_statehist("\n++++++++++++++\nSTATE INFO");
    if (state->_host_name)
        debug_statehist("host name %s", state->_host_name);
    if (state->_service_description)
        debug_statehist("svc description %s", state->_service_description);

    debug_statehist("time  %d", state->_time);
    debug_statehist("state %d", state->_state);
    if (state->_log_output)
        debug_statehist("check_output %s", state->_log_output);
    if (state->_debug_info)
        debug_statehist("debug_info %s", state->_debug_info);
    if (state->_notification_period)
        debug_statehist("notification period %s", state->_notification_period);
    debug_statehist("from  %d", state->_from);
    debug_statehist("until %d", state->_until);
    debug_statehist("duration %d", state->_duration);
}

HostServiceState::~HostServiceState()
{
    if (_log_output != 0)
        free(_log_output);
};

TableStateHistory::TableStateHistory()
{
    HostServiceState *ref = 0;
    addColumn(new OffsetTimeColumn("time",
            "Time of the log event (seconds since 1/1/1970)", (char *)&(ref->_time) - (char *)ref, -1));
    addColumn(new OffsetIntColumn("lineno",
            "The number of the line in the log file", (char *)&(ref->_lineno) - (char *)ref, -1));
    addColumn(new OffsetTimeColumn("from",
            "Start time of state (seconds since 1/1/1970)", (char *)&(ref->_from) - (char *)ref, -1));
    addColumn(new OffsetTimeColumn("until",
            "End time of state (seconds since 1/1/1970)", (char *)&(ref->_until) - (char *)ref, -1));
    addColumn(new OffsetIntColumn("duration",
            "Duration of state (until - from)", (char *)&(ref->_duration) - (char *)ref, -1));
    addColumn(new OffsetDoubleColumn("duration_part",
            "Duration part in regard to the query timeframe", (char *)(&ref->_duration_part) - (char *)ref, -1));
    addColumn(new OffsetIntColumn("state",
            "The state of the host or service in question - OK(0) / WARNING(1) / CRITICAL(2) / UNKNOWN(3) / UNMONITORED(-1)", (char *)&(ref->_state) - (char *)ref, -1));
    addColumn(new OffsetIntColumn("host_down",
            "Shows if the host of this service is down", (char *)&(ref->_host_down) - (char *)ref, -1));
    addColumn(new OffsetIntColumn("in_downtime",
            "Shows if the host or service is in downtime", (char *)&(ref->_in_downtime) - (char *)ref, -1));
    addColumn(new OffsetIntColumn("in_host_downtime",
            "Shows if the host of this service is in downtime", (char *)&(ref->_in_host_downtime) - (char *)ref, -1));
    addColumn(new OffsetIntColumn("is_flapping",
            "Shows if the host or service is flapping", (char *)&(ref->_is_flapping) - (char *)ref, -1));
    addColumn(new OffsetIntColumn("in_notification_period",
            "Shows if the host or service is within its notification period", (char *)&(ref->_in_notification_period) - (char *)ref, -1));
    addColumn(new OffsetStringColumn("notification_period",
            "The notification period of the host or service in question", (char *)&(ref->_notification_period) - (char *)ref, -1));
    addColumn(new OffsetStringColumn("debug_info",
            "Debug information", (char *)&(ref->_debug_info) - (char *)ref, -1));
    addColumn(new OffsetStringColumn("host_name",
            "Host name", (char *)&(ref->_host_name) - (char *)ref, -1));
    addColumn(new OffsetStringColumn("service_description",
            "Description of the service", (char *)&(ref->_service_description) - (char *)ref, -1));
    addColumn(new OffsetStringColumn("log_output",
            "Logfile output relevant for this state", (char *)&(ref->_log_output) - (char *)ref, -1));
    addColumn(new OffsetIntColumn("duration_ok",
            "OK duration of state ( until - from )", (char *)&(ref->_duration_state_OK) - (char *)ref, -1));
    addColumn(new OffsetDoubleColumn("duration_part_ok",
            "OK duration part in regard to the query timeframe", (char *)(&ref->_duration_part_OK) - (char *)ref, -1));

    addColumn(new OffsetIntColumn("duration_warning",
            "WARNING duration of state (until - from)", (char *)&(ref->_duration_state_WARNING) - (char *)ref, -1));
    addColumn(new OffsetDoubleColumn("duration_part_warning",
            "WARNING duration part in regard to the query timeframe", (char *)(&ref->_duration_part_WARNING) - (char *)ref, -1));

    addColumn(new OffsetIntColumn("duration_critical",
            "CRITICAL duration of state (until - from)", (char *)&(ref->_duration_state_CRITICAL) - (char *)ref, -1));
    addColumn(new OffsetDoubleColumn("duration_part_critical",
            "CRITICAL duration part in regard to the query timeframe", (char *)(&ref->_duration_part_CRITICAL) - (char *)ref, -1));

    addColumn(new OffsetIntColumn("duration_unknown",
            "UNKNOWN duration of state (until - from)", (char *)&(ref->_duration_state_UNKNOWN) - (char *)ref, -1));
    addColumn(new OffsetDoubleColumn("duration_part_unknown",
            "UNKNOWN duration part in regard to the query timeframe", (char *)(&ref->_duration_part_UNKNOWN) - (char *)ref, -1));

    addColumn(new OffsetIntColumn("duration_unmonitored",
            "UNMONITORED duration of state (until - from)", (char *)&(ref->_duration_state_UNMONITORED) - (char *)ref, -1));
    addColumn(new OffsetDoubleColumn("duration_part_unmonitored",
            "UNMONITORED duration part in regard to the query timeframe", (char *)(&ref->_duration_part_UNMONITORED) - (char *)ref, -1));


    // join host and service tables
    g_table_hosts->addColumns(this, "current_host_", (char *)&(ref->_host)    - (char *)ref);
    g_table_services->addColumns(this, "current_service_", (char *)&(ref->_service) - (char *)ref, false /* no hosts table */);
}

LogEntry *TableStateHistory::getPreviousLogentry()
{
    if (_it_entries == _entries->begin()) {
        // open previous logfile
        if (_it_logs == g_store->logCache()->logfiles()->begin())
            return 0;
        else {
            _it_logs--;
            _entries = _it_logs->second->getEntriesFromQuery(_query, g_store->logCache(), _since, _until, CLASSMASK_STATEHIST);
            _it_entries = _entries->end();
        }
    }
    return (--_it_entries)->second;
}

LogEntry *TableStateHistory::getNextLogentry()
{
    if (++_it_entries == _entries->end()) {
        if (++_it_logs == g_store->logCache()->logfiles()->end()) {
            // No further logfiles available
            // prevent errors on subsequent getNextLogentry()
            --_it_entries;
            --_it_logs;
            return 0;
        }
        else {
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

    // Keep track of the historic state of services/hosts here
    typedef map<HostServiceKey, HostServiceState*> state_info_t;
    state_info_t state_info;

    // Store hosts/services that we have filtered out here
    typedef set<HostServiceKey> object_blacklist_t;
    object_blacklist_t object_blacklist;

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

    _query_timeframe = _until - _since - 1;
    if (_query_timeframe == 0) {
        query->setError(RESPONSE_CODE_INVALID_REQUEST, "Query timeframe is 0 seconds");
        g_store->logCache()->unlockLogCache();
        return;
    }

    // Switch to last logfile (we have at least one)
    _it_logs = g_store->logCache()->logfiles()->end();
    --_it_logs;

    // Now find the log where 'since' starts.
    while (_it_logs != g_store->logCache()->logfiles()->begin() && _it_logs->first >= _since) {
        --_it_logs; // go back in history
    }

    // Check if 'until' is within these logfiles
    if (_it_logs->first > _until) {
        // All logfiles are too new, invalid timeframe
        // -> No data available. Return empty result.
        g_store->logCache()->unlockLogCache();
        return;
    }

    // Set initial logentry
    // Further logfile traversal is handled via getPreviousLogentry() / getNextLogentry()
    _entries = _it_logs->second->getEntriesFromQuery(query, g_store->logCache(), _since, _until, CLASSMASK_STATEHIST);
    _it_entries = _entries->begin();

    // Start at the logentry LOG VERSION: 2.0 which is logged in the first lines of each logfile
    // If no entry is found there will be an UNMONITORED entry till the host or service appears
    LogEntry* entry = _it_entries->second;
    bool version_found = false;
    while (entry != 0) {
        if (entry->_time >= _since){
            break;
        }
        if (entry->_type == LOG_VERSION) {
            version_found = true;
            break;
        }
        entry = getNextLogentry();
    }

//    if (!version_found) {
//        query->setError(RESPONSE_CODE_INVALID_REQUEST, "Unable to find any LOG VERSION entries before query "
//                "timeframe. Logfiles seem corrupted.");
//        g_store->logCache()->unlockLogCache();
//        return;
//    }

    HostServiceKey key;
    bool only_update = true;
    bool in_nagios_initial_states = false;
    while (0 != (entry = getNextLogentry()))
    {
        if (entry->_time >= _until) {
            getPreviousLogentry();
            break;
        }
        if (only_update && entry->_time >= _since) {
            // Reached start of query timeframe. From now on let's produce real output
            only_update = false;
        }

        if (in_nagios_initial_states && !(entry->_type == STATE_SERVICE_INITIAL || entry->_type == STATE_HOST_INITIAL)) {
            // Set still unknown hosts / services to unmonitored
            state_info_t::iterator it_hst = state_info.begin();
            while (it_hst != state_info.end())
            {
                HostServiceState* hst = it_hst->second;
                if (hst->_may_no_longer_exist) {
                	hst->_has_vanished = true;
                }
                it_hst++;
            }

            in_nagios_initial_states = false;
        }

        switch (entry->_type) {
        case DOWNTIME_ALERT_SERVICE:
        case DOWNTIME_ALERT_HOST:
        case STATE_SERVICE:
        case STATE_SERVICE_INITIAL:
        case STATE_HOST:
        case STATE_HOST_INITIAL:
        case ALERT_SERVICE:
        case ALERT_HOST:
        case FLAPPING_HOST:
        case FLAPPING_SERVICE:
        {
            key.first  = entry->_host_name;
            key.second = entry->_svc_desc != 0 ? entry->_svc_desc : "";

            if (object_blacklist.find(key) != object_blacklist.end())
            {
                // Host/Service is not needed for this query and has already
                // been filtered out.
                continue;
            }

            // Find state object for this host/service
            HostServiceState *state;
            state_info_t::iterator it_hst = state_info.find(key);
            if (it_hst == state_info.end()) 
            {
                // No state found. Now check if this host/services is filtered out
                if (objectFilteredOut(entry->_host_name, entry->_svc_desc)) {
                    object_blacklist.insert(key);
                    continue;
                }

                state = new HostServiceState();
                state_info.insert(std::make_pair(key, state));

                state->_is_host = entry->_svc_desc == 0;
                state->_from    = _since;
                state->_host    = entry->_host;
                state->_service = entry->_service;

                state->_host_name           = key.first.c_str();
                state->_service_description = key.second.c_str();

                // Get notification period of host/service
                // If this host/service is no longer availabe in nagios -> set to ""
                if (state->_service != 0)
                    #ifdef CMC
                    state->_notification_period = (char *)state->_service->notificationPeriod()->name();
                    #else
                    state->_notification_period = state->_service->notification_period;
                    #endif
                else if (state->_host != 0)
                    #ifdef CMC
                    state->_notification_period = (char *)state->_host->notificationPeriod()->name();
                    #else
                    state->_notification_period = state->_host->notification_period;
                    #endif
                else
                    state->_notification_period = (char *)"";

                // Determine initial in_notification_period status
                _notification_periods_t::const_iterator tmp_period = _notification_periods.find(state->_notification_period);
                if (tmp_period != _notification_periods.end())
                    state->_in_notification_period = tmp_period->second;
                else
                    state->_in_notification_period = 1;

                // If this key is a service try to find its host and apply its _in_host_downtime and _host_down parameters
                if (!state->_is_host) {
                    state_info_t::iterator my_host = state_info.find(HostServiceKey(key.first,""));
                    if (my_host != state_info.end()) {
                        state->_in_host_downtime = my_host->second->_in_host_downtime;
                        state->_host_down        = my_host->second->_host_down;
                    }
                }

                // Log UNMONITORED state if this host or service just appeared within the query timeframe
                if (!only_update) {
                    state->_debug_info = "UNMONITORED ";
                    state->_state      = -1;
                }
            }
            else
                state = it_hst->second;

            updateHostServiceState(query, entry, state, only_update);

            // Host downtime or state changes also affect its services
            if (entry->_type == ALERT_HOST || entry->_type == STATE_HOST || entry->_type == DOWNTIME_ALERT_HOST){
                state_info_t::iterator it_hst = state_info.begin();
                while (it_hst != state_info.end()) {
                    if (!it_hst->second->_is_host && !strcmp(state->_host_name, it_hst->second->_host_name)){
                        updateHostServiceState(query, entry, it_hst->second, only_update);
                    }
                    it_hst++;
                }
            }
            break;
        }
        case TIMEPERIOD_TRANSITION:
        {
            _notification_periods[entry->_command_name] = atoi(entry->_state_type);
            state_info_t::iterator it_hst = state_info.begin();
            while (it_hst != state_info.end()) {
                updateHostServiceState(query, entry, it_hst->second, only_update);
                it_hst++;
            }
            break;
        }
        case LOG_INITIAL_STATES:
        {
            // This feature is only available if log_initial_states is set to 1
            // If log_initial_states is set, each nagios startup logs the initial states of all known
            // hosts and services. Therefore we can detect if a host is no longer available after
            // a nagios startup. If it still exists an INITIAL HOST/SERVICE state entry will follow up shortly.
            state_info_t::iterator it_hst = state_info.begin();
            while (it_hst != state_info.end()) {
            	if (!it_hst->second->_has_vanished) {
            		it_hst->second->_last_known_time = entry->_time;
            		it_hst->second->_may_no_longer_exist = true;
            	}
                it_hst++;
            }
            in_nagios_initial_states = true;
            break;
        }
        }
    }

    // Create final reports
    state_info_t::iterator it_hst = state_info.begin();
    while (it_hst != state_info.end())
    {
        HostServiceState* hst = it_hst->second;

        // No trace since the last two nagios startup -> host/service has vanished
        if (hst->_may_no_longer_exist) {
        	// Log last known state up to nagios restart
            hst->_time  = hst->_last_known_time;
            hst->_until = hst->_last_known_time;
            process(query, hst);

            // Set absent state
            hst->_state = -1;
            hst->_until = hst->_time;
            hst->_debug_info = "UNMONITORED";
            if (hst->_log_output)
                free(hst->_log_output);
            hst->_log_output = 0;
        }

        hst->_time  = _until - 1;
        hst->_until = hst->_time;

        process(query, hst);
        it_hst++;
    }
    g_store->logCache()->unlockLogCache();
}

bool TableStateHistory::objectFilteredOut(const char *host_name, const char *service_description)
{
    return false;
}

void TableStateHistory::updateHostServiceState(Query *query, const LogEntry *entry, HostServiceState *hs_state, const bool only_update){
    // Revive host / service if it was unmonitored
    if (entry->_type != TIMEPERIOD_TRANSITION && hs_state->_has_vanished)
    {
    	hs_state->_time  = hs_state->_last_known_time;
    	hs_state->_until = hs_state->_last_known_time;
    	process(query, hs_state);

    	hs_state->_may_no_longer_exist = false;
    	hs_state->_has_vanished = false;
    	// Set absent state
    	hs_state->_state = -1;
    	hs_state->_debug_info = "UNMONITORED";
    	hs_state->_in_downtime = 0;
    	hs_state->_in_notification_period = 0;
    	hs_state->_is_flapping = 0;
    	if (hs_state->_log_output)
    		free(hs_state->_log_output);
    	hs_state->_log_output = 0;

        // Apply latest notification period information and set the host_state to unmonitored
        _notification_periods_t::const_iterator it_status = _notification_periods.find(hs_state->_notification_period);
        if (it_status != _notification_periods.end()) {
            hs_state->_in_notification_period = it_status->second;
        }
        else // No notification period information available -> within notification period
            hs_state->_in_notification_period = 1;
    }

    // Update basic information
    hs_state->_time   = entry->_time;
    hs_state->_lineno = entry->_lineno;
    hs_state->_until  = entry->_time;

    // A timeperiod entry never brings an absent host or service into existence..
    if (entry->_type != TIMEPERIOD_TRANSITION)
        hs_state->_may_no_longer_exist = false;

    switch (entry->_type)
    {
    case STATE_HOST:
    case STATE_HOST_INITIAL:
    case ALERT_HOST:
    {
        if (hs_state->_is_host) {
            if (hs_state->_state != entry->_state) {
                if (!only_update)
                    process(query, hs_state);
                hs_state->_state      = entry->_state;
                hs_state->_host_down  = entry->_state > 0;
                hs_state->_debug_info = "HOST STATE";
            }
        }
        else if (hs_state->_host_down != entry->_state > 0)
        {
            if (!only_update)
                process(query, hs_state);
            hs_state->_host_down  = entry->_state > 0;
            hs_state->_debug_info = "SVC HOST STATE";

        }
        break;
    }
    case STATE_SERVICE:
    case STATE_SERVICE_INITIAL:
    case ALERT_SERVICE:
    {
        if (hs_state->_state != entry->_state) {
            if (!only_update)
                process(query, hs_state);
            hs_state->_debug_info = "SVC ALERT";
            hs_state->_state = entry->_state;
        }
        break;
    }
    case DOWNTIME_ALERT_HOST:
    {
        int downtime_active = !strncmp(entry->_state_type,"STARTED",7) ? 1 : 0;

        if (hs_state->_in_host_downtime != downtime_active) {
            if (!only_update)
                process(query, hs_state);
            hs_state->_debug_info       = hs_state->_is_host ? "HOST DOWNTIME" : "SVC HOST DOWNTIME";
            hs_state->_in_host_downtime = downtime_active;
            if (hs_state->_is_host)
                hs_state->_in_downtime  = downtime_active;
        }
        break;
    }
    case DOWNTIME_ALERT_SERVICE:
    {
        int downtime_active = !strncmp(entry->_state_type,"STARTED",7) ? 1 : 0;
        if (hs_state->_in_downtime != downtime_active) {
            if (!only_update)
                process(query, hs_state);
            hs_state->_debug_info = "DOWNTIME SERVICE";
            hs_state->_in_downtime = downtime_active;
        }
        break;

    }
    case FLAPPING_HOST:
    case FLAPPING_SERVICE:
    {
        int flapping_active = !strncmp(entry->_state_type,"STARTED",7) ? 1 : 0;
        if (hs_state->_is_flapping != flapping_active) {
            if (!only_update)
                process(query, hs_state);
            hs_state->_debug_info = "FLAPPING ";
            hs_state->_is_flapping = flapping_active;
        }
        break;
    }
    case TIMEPERIOD_TRANSITION:
    {
        // if no _host pointer is available the initial status of _in_notification_period (1) never changes
        if (hs_state->_host && !strcmp(entry->_command_name, hs_state->_notification_period)) {
            int new_status = atoi(entry->_state_type);
            if (new_status != hs_state->_in_notification_period) {
                if (!only_update)
                    process(query, hs_state);
                hs_state->_debug_info = "TIMEPERIOD ";
                hs_state->_in_notification_period = new_status;
            }
        }
        break;
    }
    }

    if (entry->_type != TIMEPERIOD_TRANSITION) {
        if (hs_state->_log_output)
            free(hs_state->_log_output);

        if ( (entry->_type == STATE_HOST_INITIAL || entry->_type == STATE_SERVICE_INITIAL) &&
             (entry->_check_output != 0 && !strcmp(entry->_check_output, "(null)")) )
            hs_state->_log_output = 0;

        else
            hs_state->_log_output = entry->_check_output ? strdup(entry->_check_output) : 0;
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
        hs_state->_duration_state_OK          = hs_state->_duration;
        hs_state->_duration_part_OK           = hs_state->_duration_part;
        break;
    case STATE_WARNING:
        hs_state->_duration_state_WARNING     = hs_state->_duration;
        hs_state->_duration_part_WARNING      = hs_state->_duration_part;
        break;
    case STATE_CRITICAL:
        hs_state->_duration_state_CRITICAL    = hs_state->_duration;
        hs_state->_duration_part_CRITICAL     = hs_state->_duration_part;
        break;
    case STATE_UNKNOWN:
        hs_state->_duration_state_UNKNOWN     = hs_state->_duration;
        hs_state->_duration_part_UNKNOWN      = hs_state->_duration_part;
        break;
    default:
        break;
    }

    // if (hs_state->_duration > 0)
    query->processDataset(hs_state);
    hs_state->_from = hs_state->_until;
};

bool TableStateHistory::isAuthorized(contact *ctc, void *data)
{
    HostServiceState *entry = (HostServiceState *)data;
    service *svc = entry->_service;
    host *hst = entry->_host;

    if (hst || svc)
        return is_authorized_for(ctc, hst, svc);
    else
        return false;
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
