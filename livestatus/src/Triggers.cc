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

#include "Triggers.h"
#include <stdexcept>

Triggers::Kind Triggers::find(const std::string &name) {
    if (name == "all") {
        return Kind::all;
    }
    if (name == "check") {
        return Kind::check;
    }
    if (name == "state") {
        return Kind::state;
    }
    if (name == "log") {
        return Kind::log;
    }
    if (name == "downtime") {
        return Kind::downtime;
    }
    if (name == "comment") {
        return Kind::comment;
    }
    if (name == "command") {
        return Kind::command;
    }
    if (name == "program") {
        return Kind::program;
    }
    throw std::runtime_error(
        "invalid trigger '" + name +
        "', allowed: all, check, state, log, downtime, comment, command and program");
}

void Triggers::notify_all(Kind trigger) {
    condition_variable_for(Kind::all).notify_all();
    condition_variable_for(trigger).notify_all();
}

std::condition_variable &Triggers::condition_variable_for(Kind trigger) {
    switch (trigger) {
        case Kind::all:
            return _cond_all;
        case Kind::check:
            return _cond_check;
        case Kind::state:
            return _cond_state;
        case Kind::log:
            return _cond_log;
        case Kind::downtime:
            return _cond_downtime;
        case Kind::comment:
            return _cond_comment;
        case Kind::command:
            return _cond_command;
        case Kind::program:
            return _cond_program;
    }
    return _cond_all;  // unreachable
}
