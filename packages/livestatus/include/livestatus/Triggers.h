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
                  Predicate pred) const {
        std::unique_lock<std::mutex> ul(_mutex);
        auto &cond = condition_variable_for(trigger);
        if (rel_time == rel_time.zero()) {
            cond.wait(ul, pred);
        } else {
            cond.wait_for(ul, rel_time, pred);
        }
    }

private:
    // TODO(sp): All of this "mutable" Kung Fu is here to make wait_for() const,
    // which in turn is a prerequisite to make the ICore used by Query const: It
    // calls wait_for() if there is a WaitCondition in the Livestatus query.
    // Although this is semantically OK, perhaps there is a nicer way to achieve
    // this without all those "mutable"s.
    mutable std::mutex _mutex;
    mutable std::condition_variable _cond_all;
    mutable std::condition_variable _cond_check;
    mutable std::condition_variable _cond_state;
    mutable std::condition_variable _cond_log;
    mutable std::condition_variable _cond_downtime;
    mutable std::condition_variable _cond_comment;
    mutable std::condition_variable _cond_command;
    mutable std::condition_variable _cond_program;

    std::condition_variable &condition_variable_for(Kind trigger) const;
};

#endif  // Triggers_h
