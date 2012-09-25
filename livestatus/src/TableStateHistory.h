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
	int     _state;			 // -1/0/1/2/3
	int     _in_notification_period;
	int     _in_downtime;
	int     _in_host_downtime;
	int     _is_flapping;


	// Absent state handling
	int		_no_longer_exists;
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


class TableStateHistory : public Table
{
    int      _query_timeframe;
    Query   *_query;
    int      _since;
    int      _until;

	// Notification periods information, name: active(1)/inactive(0)
    typedef map<string, int> _notification_periods_t;
    _notification_periods_t  _notification_periods;

    // Helper functions to traverse through logfiles
    _logfiles_t::iterator _it_logs;
    logfile_entries_t*            _entries;
    logfile_entries_t::iterator   _it_entries;
    LogEntry*             _current_entry;

public:
    TableStateHistory();
    const char *name() { return "statehist"; }
    const char *prefixname() { return "statehist_"; }
    bool isAuthorized(contact *ctc, void *data);
    void handleNewMessage(Logfile *logfile, time_t since, time_t until, unsigned logclasses);
    void answerQuery(Query *query);
    Column *column(const char *colname); // override in order to handle current_
    void updateHostServiceState(Query *query, const LogEntry *entry, HostServiceState *state, const bool only_update);

private:
    LogEntry* getPreviousLogentry();
    LogEntry* getNextLogentry();
    void      process(Query *query, HostServiceState *hs_state);
};


#endif // TableStateHistory_h
