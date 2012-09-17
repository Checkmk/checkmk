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

#ifndef TableStateHistory_h
#define TableStateHistory_h

#include <map>
#include <time.h>
#include "config.h"
#include "string.h"
#include "logger.h"
#include "nagios.h"
#include "Logfile.h"
#include "LogCache.h"
#include "Query.h"


typedef pair<string, string> HostServiceKey;
class LessThan
{
public:
    bool operator()(const HostServiceKey& lhs, const HostServiceKey& rhs)
    {
        if (lhs.first < rhs.first)
            return true;
        if (lhs.first > rhs.first)
            return false;
        return lhs.second < rhs.second;
    }
};

class HostServiceState{
public:
	time_t  _time;
	time_t  _from;
	time_t  _until;
	time_t  _duration;
	double  _duration_part;
	int     _attempt;
	int     _state;			 // -1/0/1/2/3
	char*   _state_alert;    // STARTED/STOPPED
	char*   _state_flapping; // STARTED/STOPPED
	char*   _state_downtime; // STARTED/STOPPED/CANCELED
	int		_no_longer_exists;   // 0/1
	char*   _notification_period;
	int     _in_notification_period;
	int     _in_downtime;
	int     _is_flapping;

	LogEntry* _log_ptr;
	LogEntry* _prev_log_ptr;
	char*   _debug_info;
	char*   _prev_debug_info;

	time_t  _duration_state_ABSENT;
	double  _duration_part_ABSENT;
	time_t  _duration_state_OK;
	double  _duration_part_OK;
	time_t  _duration_state_WARNING;
	double  _duration_part_WARNING;
	time_t  _duration_state_CRITICAL;
	double  _duration_part_CRITICAL;
	time_t  _duration_state_UNKNOWN;
	double  _duration_part_UNKNOWN;

    host      *_host;
    char*     _host_name; // Fallback if host no longer exists
    service   *_service;
    char*     _service_description;  // Fallback if service no longer exists



	HostServiceState(){};
};

typedef map<HostServiceKey, HostServiceState, LessThan> SLA_Info;

class TableStateHistory : public Table
{

public:
    TableStateHistory();
    ~TableStateHistory();
    const char *name() { return "statehist"; }
    const char *prefixname() { return "statehist"; }
    bool isAuthorized(contact *ctc, void *data);
    void handleNewMessage(Logfile *logfile, time_t since, time_t until, unsigned logclasses);
    void answerQuery(Query *query);
    Column *column(const char *colname); // override in order to handle current_
    void updateHostServiceState(Query &query, LogEntry &entry, HostServiceState &state, bool only_update);

private:
    int  _query_timeframe;
    bool answerQuery(Query *, Logfile *, time_t, time_t);
    Query*   _query;
    int      _since;
    int      _until;
    uint32_t _classmask;

    // Helper functions to traverse through logfiles
    _logfiles_t::iterator _it_logs;
    entries_t*            _entries;
    entries_t::iterator   _it_entries;
    LogEntry*             _current_entry;
    LogEntry* getPreviousLogentry();
    LogEntry* getNextLogentry();

    inline void process(Query *query, HostServiceState *hs_state, bool do_nothing){
    	if( do_nothing )
    		return;
    	hs_state->_duration = hs_state->_until - hs_state->_from;
    	hs_state->_duration_part = (double)hs_state->_duration / (double)_query_timeframe;


    	bzero(&hs_state->_duration_state_ABSENT, sizeof(time_t) * 5 + sizeof(double) * 5);

    	switch (hs_state->_state) {
    	case -1:
    		hs_state->_duration_state_ABSENT = hs_state->_duration;
    		hs_state->_duration_part_ABSENT  = hs_state->_duration_part;
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

    	query->processDataset(hs_state);
    	hs_state->_from = hs_state->_until;
    };
   SLA_Info* sla_info;
};


#endif // TableStateHistory_h
