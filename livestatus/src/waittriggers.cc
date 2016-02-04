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

#include "waittriggers.h"
#include <string.h>
#include "mk/ConditionVariable.h"
#include "mk/Mutex.h"

using mk::condition_variable;
using mk::mutex;
using mk::unique_lock;

namespace {

struct trigger *to_trigger(condition_variable *c) {
    return reinterpret_cast<struct trigger *>(c);
}

condition_variable *from_trigger(struct trigger *c) {
    return reinterpret_cast<condition_variable *>(c);
}

mutex g_wait_mutex;

condition_variable cond_all;
condition_variable cond_check;
condition_variable cond_state;
condition_variable cond_log;
condition_variable cond_downtime;
condition_variable cond_comment;
condition_variable cond_command;
condition_variable cond_program;
}  // namespace

struct trigger *trigger_all() {
    return to_trigger(&cond_all);
}

struct trigger *trigger_check() {
    return to_trigger(&cond_check);
}

struct trigger *trigger_state() {
    return to_trigger(&cond_state);
}

struct trigger *trigger_log() {
    return to_trigger(&cond_log);
}

struct trigger *trigger_downtime() {
    return to_trigger(&cond_downtime);
}

struct trigger *trigger_comment() {
    return to_trigger(&cond_comment);
}

struct trigger *trigger_command() {
    return to_trigger(&cond_command);
}

struct trigger *trigger_program() {
    return to_trigger(&cond_program);
}

struct trigger *trigger_find(const char *name) {
    if (strcmp(name, "all") == 0) {
        return trigger_all();
    }
    if (strcmp(name, "check") == 0) {
        return trigger_check();
    }
    if (strcmp(name, "state") == 0) {
        return trigger_state();
    }
    if (strcmp(name, "log") == 0) {
        return trigger_log();
    }
    if (strcmp(name, "downtime") == 0) {
        return trigger_downtime();
    }
    if (strcmp(name, "comment") == 0) {
        return trigger_comment();
    }
    if (strcmp(name, "command") == 0) {
        return trigger_command();
    }
    if (strcmp(name, "program") == 0) {
        return trigger_program();
    }
    return nullptr;
}

const char *trigger_all_names() {
    return "all, check, state, log, downtime, comment, command and program";
}

void trigger_notify_all(struct trigger *which) {
    from_trigger(trigger_all())->notify_all();
    from_trigger(which)->notify_all();
}

void trigger_wait(struct trigger *which) {
    unique_lock<mutex> ul(g_wait_mutex);
    from_trigger(which)->wait(ul);
}

int trigger_wait_until(struct trigger *which, const struct timespec *abstime) {
    unique_lock<mutex> ul(g_wait_mutex);
    return static_cast<int>(from_trigger(which)->wait_until(ul, abstime) ==
                            mk::no_timeout);
}
