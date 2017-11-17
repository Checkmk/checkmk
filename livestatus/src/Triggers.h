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

#ifndef Triggers_h
#define Triggers_h

#include "config.h"  // IWYU pragma: keep
#include <chrono>
#include <condition_variable>
#include <mutex>
#include <string>

class Triggers {
public:
    enum class Kind {
        all,
        check,
        state,
        log,
        downtime,
        comment,
        command,
        program
    };

    Kind find(const std::string &name);

    void notify_all(Kind trigger);

    template <class Rep, class Period, class Predicate>
    void wait_for(Kind trigger,
                  const std::chrono::duration<Rep, Period> &rel_time,
                  Predicate pred) {
        std::unique_lock<std::mutex> ul(_mutex);
        auto &cond = condition_variable_for(trigger);
        if (rel_time == rel_time.zero()) {
            cond.wait(ul, pred);
        } else {
            cond.wait_for(ul, rel_time, pred);
        }
    }

private:
    std::mutex _mutex;
    std::condition_variable _cond_all;
    std::condition_variable _cond_check;
    std::condition_variable _cond_state;
    std::condition_variable _cond_log;
    std::condition_variable _cond_downtime;
    std::condition_variable _cond_comment;
    std::condition_variable _cond_command;
    std::condition_variable _cond_program;

    std::condition_variable &condition_variable_for(Kind trigger);
};

#endif  // Triggers_h
