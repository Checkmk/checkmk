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

#include "waittriggers.h"
#include <mutex>
#include <ratio>
#include <stdexcept>

namespace {
std::mutex wait_mutex;

std::condition_variable cond_all;
std::condition_variable cond_check;
std::condition_variable cond_state;
std::condition_variable cond_log;
std::condition_variable cond_downtime;
std::condition_variable cond_comment;
std::condition_variable cond_command;
std::condition_variable cond_program;
}  // namespace

std::mutex &trigger_mutex() { return wait_mutex; }

std::condition_variable &trigger_all() { return cond_all; }

std::condition_variable &trigger_check() { return cond_check; }

std::condition_variable &trigger_state() { return cond_state; }

std::condition_variable &trigger_log() { return cond_log; }

std::condition_variable &trigger_downtime() { return cond_downtime; }

std::condition_variable &trigger_comment() { return cond_comment; }

std::condition_variable &trigger_command() { return cond_command; }

std::condition_variable &trigger_program() { return cond_program; }

std::condition_variable &trigger_find(const std::string &name) {
    if (name == "all") {
        return trigger_all();
    }
    if (name == "check") {
        return trigger_check();
    }
    if (name == "state") {
        return trigger_state();
    }
    if (name == "log") {
        return trigger_log();
    }
    if (name == "downtime") {
        return trigger_downtime();
    }
    if (name == "comment") {
        return trigger_comment();
    }
    if (name == "command") {
        return trigger_command();
    }
    if (name == "program") {
        return trigger_program();
    }
    throw std::runtime_error(
        "invalid trigger '" + name +
        "', allowed: all, check, state, log, downtime, comment, command and program");
}

void trigger_notify_all(std::condition_variable &cond) {
    trigger_all().notify_all();
    cond.notify_all();
}

void trigger_wait(std::condition_variable &cond) {
    std::unique_lock<std::mutex> ul(wait_mutex);
    cond.wait(ul);
}

std::cv_status trigger_wait_for(std::condition_variable &cond,
                                std::chrono::milliseconds ms) {
    std::unique_lock<std::mutex> ul(wait_mutex);
    return cond.wait_for(ul, ms);
}
