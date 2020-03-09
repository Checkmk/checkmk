// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef global_counters_h
#define global_counters_h

#include "config.h"  // IWYU pragma: keep

// Remember to update num_counters when you change the enum below. C++ really
// lacks a feature to iterate over enums easily...
enum class Counter {
    neb_callbacks,
    requests,
    connections,
    service_checks,
    host_checks,
    forks,
    log_messages,
    commands,
    livechecks,
    overflows
};

void counterIncrement(Counter which);
const double *counterAddress(Counter which);
const double *counterRateAddress(Counter which);
void do_statistics();

#endif  // global_counters_h
