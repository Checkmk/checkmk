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

#ifndef waittriggers_h
#define waittriggers_h

#include "config.h"  // IWYU pragma: keep

#ifdef __cplusplus
extern "C" {
#endif

struct timespec;

// This is basically a C++ class for triggers done the "C way" via an opaque
// struct, explicit passing of 'this' and using a prefix for names.

struct trigger;

struct trigger *trigger_all();
struct trigger *trigger_check();
struct trigger *trigger_state();
struct trigger *trigger_log();
struct trigger *trigger_downtime();
struct trigger *trigger_comment();
struct trigger *trigger_command();
struct trigger *trigger_program();

struct trigger *trigger_find(const char *name);
const char *trigger_all_names();

void trigger_notify_all(struct trigger *which);

void trigger_wait(struct trigger *which);
int trigger_wait_until(struct trigger *which, const struct timespec *abstime);

#ifdef __cplusplus
}
#endif

#endif  // waittriggers_h
