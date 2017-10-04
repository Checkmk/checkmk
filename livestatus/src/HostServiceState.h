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
// tails. You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#ifndef HostServiceState_h
#define HostServiceState_h

#include "config.h"  // IWYU pragma: keep
#include <cstdint>
#include <ctime>
#include <string>
#include <vector>
class HostServiceState;

// for host/service, ugly...
#ifdef CMC
#include "cmc.h"
#else
#include "nagios.h"
#endif

typedef std::vector<HostServiceState *> HostServices;

typedef void *HostServiceKey;

class HostServiceState {
public:
    bool _is_host;
    time_t _time;
    int32_t _lineno;
    time_t _from;
    time_t _until;

    time_t _duration;
    double _duration_part;

    time_t _duration_state_UNMONITORED;
    double _duration_part_UNMONITORED;

    time_t _duration_state_OK;
    double _duration_part_OK;

    time_t _duration_state_WARNING;
    double _duration_part_WARNING;

    time_t _duration_state_CRITICAL;
    double _duration_part_CRITICAL;

    time_t _duration_state_UNKNOWN;
    double _duration_part_UNKNOWN;

    // State information
    int _host_down;  // used if service
    int _state;      // -1/0/1/2/3
    int _in_notification_period;
    int _in_service_period;
    int _in_downtime;
    int _in_host_downtime;
    int _is_flapping;

    // Service information
    HostServices _services;

    // Absent state handling
    bool _may_no_longer_exist;
    bool _has_vanished;
    time_t _last_known_time;

    std::string _debug_info;
    std::string _log_output;

    // maybe "": -> no period known, we assume "always"
    std::string _notification_period;
    // maybe "": -> no period known, we assume "always"
    std::string _service_period;
    host *_host;
    service *_service;
    std::string _host_name;            // Fallback if host no longer exists
    std::string _service_description;  // Fallback if service no longer exists

    HostServiceState();
#ifdef CMC
    void computePerStateDurations();
#endif
};

#endif  // HostServiceState_h
