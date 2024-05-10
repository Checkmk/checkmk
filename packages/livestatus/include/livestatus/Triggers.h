// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef Triggers_h
#define Triggers_h

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

    static Kind find(const std::string &name);

    void notify_all(Kind trigger);

    template <typename Rep, typename Period, typename Predicate>
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
