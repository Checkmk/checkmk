// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef HostServiceState_h
#define HostServiceState_h

#include "config.h"  // IWYU pragma: keep

#include <chrono>
#include <cstddef>
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
    std::chrono::system_clock::time_point _time;
    size_t _lineno;
    std::chrono::system_clock::time_point _from;
    std::chrono::system_clock::time_point _until;

    std::chrono::system_clock::duration _duration;
    double _duration_part;

    std::chrono::system_clock::duration _duration_unmonitored;
    double _duration_part_unmonitored;

    std::chrono::system_clock::duration _duration_ok;
    double _duration_part_ok;

    std::chrono::system_clock::duration _duration_warning;
    double _duration_part_warning;

    std::chrono::system_clock::duration _duration_critical;
    double _duration_part_critical;

    std::chrono::system_clock::duration _duration_unknown;
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
    std::chrono::system_clock::time_point _last_known_time;

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
