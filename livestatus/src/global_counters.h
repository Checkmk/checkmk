// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2015             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// Copyright by Mathias Kettner and Mathias Kettner GmbH.  All rights reserved.
//
// Check_MK is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.
//
// Check_MK is  distributed in the hope that it will be useful, but
// WITHOUT ANY WARRANTY;  without even the implied warranty of
// MERCHANTABILITY  or  FITNESS FOR A PARTICULAR PURPOSE. See the
// GNU General Public License for more details.
//
// You should have  received  a copy of the  GNU  General Public
// License along with Check_MK.  If  not, email to mk@mathias-kettner.de
// or write to the postal address provided at www.mathias-kettner.de

#ifndef global_counters_h
#define global_counters_h

#include "config.h"

#include <stdint.h>

#ifndef EXTERN
# define EXTERN extern
#endif

typedef uint64_t counter_t;

#define COUNTER_NEB_CALLBACKS        0
#define COUNTER_REQUESTS             1
#define COUNTER_CONNECTIONS          2
#define COUNTER_SERVICE_CHECKS       3
#define COUNTER_HOST_CHECKS          4
#define COUNTER_FORKS                5
#define COUNTER_LOG_MESSAGES         6
#define COUNTER_COMMANDS             7
#define COUNTER_LIVECHECKS           8
#define COUNTER_LIVECHECK_OVERFLOWS  9
#define COUNTER_OVERFLOWS           10
#define NUM_COUNTERS                11

EXTERN counter_t g_counters[NUM_COUNTERS];
EXTERN counter_t g_last_counter[NUM_COUNTERS];
EXTERN double g_counter_rate[NUM_COUNTERS];

void do_statistics();

#endif // global_counters_h

