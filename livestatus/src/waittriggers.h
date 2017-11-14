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

#ifndef waittriggers_h
#define waittriggers_h

#include "config.h"  // IWYU pragma: keep
#include <chrono>
#include <condition_variable>

// This is basically a C++ class for triggers done the "C way" via an opaque
// struct, explicit passing of 'this' and using a prefix for names.
struct trigger;

trigger *trigger_all();
trigger *trigger_check();
trigger *trigger_state();
trigger *trigger_log();
trigger *trigger_downtime();
trigger *trigger_comment();
trigger *trigger_command();
trigger *trigger_program();

trigger *trigger_find(const char *name);
const char *trigger_all_names();

void trigger_notify_all(struct trigger *which);

void trigger_wait(struct trigger *which);
std::cv_status trigger_wait_for(struct trigger *which,
                                std::chrono::milliseconds ms);

#endif  // waittriggers_h
