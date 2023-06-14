// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/Triggers.h"

#include <stdexcept>

// static
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
