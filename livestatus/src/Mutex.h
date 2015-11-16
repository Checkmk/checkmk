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

#ifndef Mutex_h
#define Mutex_h

#include "config.h" // IWYU pragma: keep
#include <errno.h>
#include <pthread.h>
#include <string.h>
#include <stdexcept>
#include <string>

// A more or less drop-in replacement for C++11's <mutex> (partial)

namespace mk {

class mutex {
public:
    typedef pthread_mutex_t *native_handle_type;
    mutex() { pthread_mutex_init(native_handle(), 0); }
    ~mutex() { check(pthread_mutex_destroy(native_handle())); }
    void lock() { check(pthread_mutex_lock(native_handle())); }
    bool try_lock()
    {
        int status = pthread_mutex_trylock(native_handle());
        if (status != EBUSY) check(status);
        return status == 0;
    }
    void unlock() { check(pthread_mutex_unlock(native_handle())); }
    native_handle_type native_handle() { return &_mutex; }
private:
    mutex(const mutex &);             // = delete
    mutex &operator=(const mutex &);  // = delete

    static void check(int status)
    {
        if (status != 0) {
            throw std::runtime_error(std::string(strerror(status)));
        }
    }

    pthread_mutex_t _mutex;
};

struct adopt_lock_t { };
const adopt_lock_t adopt_lock = { };  // constexpr

template <typename Mutex>
class lock_guard {
public:
    typedef Mutex mutex_type;
    explicit lock_guard(mutex_type &m) : _mutex(m) { _mutex.lock(); }
    lock_guard(mutex_type &m, adopt_lock_t) : _mutex(m) {}
    ~lock_guard() { _mutex.unlock(); }
private:
    lock_guard(const lock_guard &);             // = delete
    lock_guard &operator=(const lock_guard &);  // = delete

    mutex_type &_mutex;
};

} // namespace mk

#endif // Mutex_h
