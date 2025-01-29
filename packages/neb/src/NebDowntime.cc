// Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "neb/NebDowntime.h"

#include "neb/Downtime.h"

int32_t NebDowntime::id() const { return downtime_._id; }

std::string NebDowntime::author() const { return downtime_._author; }

std::string NebDowntime::comment() const { return downtime_._comment; }

bool NebDowntime::origin_is_rule() const { return false; }

std::chrono::system_clock::time_point NebDowntime::entry_time() const {
    return downtime_._entry_time;
}

std::chrono::system_clock::time_point NebDowntime::start_time() const {
    return downtime_._start_time;
}

std::chrono::system_clock::time_point NebDowntime::end_time() const {
    return downtime_._end_time;
}

bool NebDowntime::isService() const { return downtime_._service != nullptr; }

bool NebDowntime::fixed() const { return downtime_._fixed; }

std::chrono::nanoseconds NebDowntime::duration() const {
    return downtime_._duration;
}

RecurringKind NebDowntime::recurring() const { return RecurringKind::none; }

bool NebDowntime::pending() const { return !downtime_._is_active; }

int32_t NebDowntime::triggered_by() const { return downtime_._triggered_by; };
