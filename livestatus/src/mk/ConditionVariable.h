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

#ifndef mk_ConditionVariable_h
#define mk_ConditionVariable_h

#include "config.h" // IWYU pragma: keep
#include <pthread.h>
#include <time.h>
#include "Mutex.h"

// A more or less drop-in replacement for C++11's <condition_variable> (partial)

namespace mk {

enum /* class */ cv_status { no_timeout, timeout };

class condition_variable {
public:
    typedef pthread_cond_t *native_handle_type;

    condition_variable() { check_status(pthread_cond_init(&_cond, 0)); }
    ~condition_variable() { check_status(pthread_cond_destroy(&_cond)); }
    void notify_one() { check_status(pthread_cond_signal(&_cond)); }
    void notify_all() { check_status(pthread_cond_broadcast(&_cond)); }
    void wait(unique_lock<mutex> &ul)
    {
        if (!ul) throw_system_error(EPERM);
        check_status(pthread_cond_wait(&_cond, ul.mutex()->native_handle()));
    }

    template <typename Predicate>
    void wait(unique_lock<mutex> &ul, Predicate p)
    {
        while (!p()) wait(ul);
    }

    // template<typename Rep, typename Period>
    // cv_status wait_for(unique_lock<mutex>& ul,
    //                    const chrono::duration<Rep, Period>& rtime);

    // template<typename Rep, typename Period, typename Predicate>
    // bool wait_for(unique_lock<mutex>& ul,
    //               const chrono::duration<Rep, Period>& rtime,
    //               Predicate p);

    // template<typename Clock, typename Duration>
    // cv_status wait_until(unique_lock<mutex>& lock,
    //                      const chrono::time_point<Clock, Duration>& atime);

    // template<typename Clock, typename Duration, typename Predicate>
    // bool wait_until(unique_lock<mutex>& ul,
    //                 const chrono::time_point<Clock, Duration>& atime,
    //                 Predicate p);

    // Note: This is *not* in the standard, the chrono stuff above is!
    cv_status wait_until(unique_lock<mutex> &ul, const struct timespec *atime)
    {
        int status =
            pthread_cond_timedwait(&_cond, ul.mutex()->native_handle(), atime);
        if (status != ETIMEDOUT) check_status(status);
        return (status == ETIMEDOUT) ? timeout : no_timeout;
    }

    native_handle_type native_handle() { return &_cond; }
private:
    condition_variable(const condition_variable &);            // = delete
    condition_variable &operator=(const condition_variable &); // = delete

    pthread_cond_t _cond;
};

// void notify_all_at_thread_exit(condition_variable& cond,
//                                unique_lock<mutex> ul);


} // namespace mk

#endif // mk_ConditionVariable_h
