// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

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

using HostServices = std::vector<HostServiceState *>;

using HostServiceKey = void *;

class HostServiceState {
public:
    bool _is_host;
    time_t _time;
    int32_t _lineno;
    time_t _from;
    time_t _until;

    time_t _duration;
    double _duration_part;

    time_t _duration_unmonitored;
    double _duration_part_unmonitored;

    time_t _duration_ok;
    double _duration_part_ok;

    time_t _duration_warning;
    double _duration_part_warning;

    time_t _duration_critical;
    double _duration_part_critical;

    time_t _duration_unknown;
    double _duration_part_unknown;

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
    std::string _long_log_output;

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
