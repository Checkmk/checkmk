// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef HostServiceState_h
#define HostServiceState_h

#include <chrono>
#include <cstddef>
#include <string>
#include <vector>
class IHost;
class IService;
class HostServiceState;

// NOTE regarding object lifetimes: The HostServiceState objects are owned by
// TableStateHistory::answerQueryInternal()'s state_info local variable of type
// state_info_t. This variable outlives any HostServiceState objects, so using a
// raw pointer here is safe.
using HostServices = std::vector<HostServiceState *>;

using HostServiceKey = void const *;

class HostServiceState {
public:
    bool _is_host{};
    std::chrono::system_clock::time_point _time;
    size_t _lineno{};
    std::chrono::system_clock::time_point _from;
    std::chrono::system_clock::time_point _until;

    std::chrono::system_clock::duration _duration{};
    double _duration_part{};

    std::chrono::system_clock::duration _duration_unmonitored{};
    double _duration_part_unmonitored{};

    std::chrono::system_clock::duration _duration_ok{};
    double _duration_part_ok{};

    std::chrono::system_clock::duration _duration_warning{};
    double _duration_part_warning{};

    std::chrono::system_clock::duration _duration_critical{};
    double _duration_part_critical{};

    std::chrono::system_clock::duration _duration_unknown{};
    double _duration_part_unknown{};

    // State information
    bool _host_down{};              // used if service
    int _state{};                   // -1/0/1/2/3
    int _in_notification_period{};  // TODO(sp): int TimePeriodTransition::to()
    int _in_service_period{};       // TODO(sp): int TimePeriodTransition::to()
    int _downtime_depth{};
    int _host_downtime_depth{};
    bool _is_flapping{};

    // Service information
    HostServices _services;

    // Absent state handling
    bool _may_no_longer_exist{};
    bool _has_vanished{};
    std::chrono::system_clock::time_point _last_known_time;

    std::string _debug_info;
    std::string _log_output;
    std::string _long_log_output;

    // maybe "": -> no period known, we assume "always"
    std::string _notification_period;
    // maybe "": -> no period known, we assume "always"
    std::string _service_period;
    const IHost *_host{};
    const IService *_service{};
    std::string _host_name;            // Fallback if host no longer exists
    std::string _service_description;  // Fallback if service no longer exists

    // Set all _duration* fields based on _from, _until and query_timeframe
    void computePerStateDurations(
        std::chrono::system_clock::duration query_timeframe);
};

#endif  // HostServiceState_h
