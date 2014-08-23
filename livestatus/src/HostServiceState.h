// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
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

#ifndef HostServiceState_h
#define HostServiceState_h

#include <time.h>
#include <string.h>
#include <nagios.h>
#include <vector>
using namespace std;

struct HostServiceState;
typedef vector<HostServiceState*> HostServices;

typedef void* HostServiceKey;

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
    int     _in_service_period;
    int     _in_downtime;
    int     _in_host_downtime;
    int     _is_flapping;

    // Service information
    HostServices _services;

    // Absent state handling
    bool    _may_no_longer_exist;
    bool    _has_vanished;
    time_t  _last_known_time;


    const char  *_debug_info;
    // Pointer to dynamically allocated strings (strdup) that live here.
    // These pointers are 0, if there is no output (e.g. downtime)
    char        *_log_output;
    char        *_notification_period;  // may be "": -> no period known, we assume "always"
    char        *_service_period;  // may be "": -> no period known, we assume "always"
    host        *_host;
    service     *_service;
    const char  *_host_name;            // Fallback if host no longer exists
    const char  *_service_description;  // Fallback if service no longer exists

    HostServiceState() { bzero(this, sizeof(HostServiceState)); }
    ~HostServiceState();
    void computePerStateDurations();
    void debug_me(const char *loginfo, ...);
};

#endif // HostServiceState_h
