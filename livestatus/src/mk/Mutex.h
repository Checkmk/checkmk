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

#ifndef mk_Mutex_h
#define mk_Mutex_h

#include "config.h" // IWYU pragma: keep
#include <errno.h>
#include <pthread.h>
#include <string.h>
#include <algorithm>
#include <stdexcept>
#include <string>

// A more or less drop-in replacement for C++11's <mutex> (partial)

namespace mk {

// Alas, system_error is a C++11 feature, so we throw its superclass.
inline void throw_system_error(int err)
{
    throw std::runtime_error(std::string(strerror(err)));
}


inline void check_status(int status)
{
    if (status != 0) throw_system_error(status);
}


class mutex {
public:
    typedef pthread_mutex_t *native_handle_type;
    mutex() { check_status(pthread_mutex_init(&_mutex, 0)); }
    ~mutex() { check_status(pthread_mutex_destroy(&_mutex)); }
    void lock() { check_status(pthread_mutex_lock(&_mutex)); }
    bool try_lock()
    {
        int status = pthread_mutex_trylock(&_mutex);
        if (status != EBUSY) check_status(status);
        return status == 0;
    }
    void unlock() { check_status(pthread_mutex_unlock(&_mutex)); }
    native_handle_type native_handle() { return &_mutex; }
private:
    mutex(const mutex &);            // = delete
    mutex &operator=(const mutex &); // = delete

    pthread_mutex_t _mutex;
};


class recursive_mutex {
public:
    typedef pthread_mutex_t *native_handle_type;
    recursive_mutex()
    {
        pthread_mutexattr_t attr;
        check_status(pthread_mutexattr_init(&attr));
        check_status(pthread_mutexattr_settype(&attr, PTHREAD_MUTEX_RECURSIVE));
        check_status(pthread_mutex_init(&_mutex, &attr));
        check_status(pthread_mutexattr_destroy(&attr));
    }
    ~recursive_mutex() { check_status(pthread_mutex_destroy(&_mutex)); }
    void lock() { check_status(pthread_mutex_lock(&_mutex)); }
    bool try_lock()
    {
        int status = pthread_mutex_trylock(&_mutex);
        if (status != EBUSY) check_status(status);
        return status == 0;
    }
    void unlock() { check_status(pthread_mutex_unlock(&_mutex)); }
    native_handle_type native_handle() { return &_mutex; }
private:
    recursive_mutex(const recursive_mutex &);            // = delete;
    recursive_mutex &operator=(const recursive_mutex &); // = delete;

    pthread_mutex_t _mutex;
};


struct defer_lock_t {
};
const defer_lock_t defer_lock = {}; // constexpr

struct try_to_lock_t {
};
const try_to_lock_t try_to_lock = {}; // constexpr

struct adopt_lock_t {
};
const adopt_lock_t adopt_lock = {}; // constexpr


template <typename Mutex>
class lock_guard {
public:
    typedef Mutex mutex_type;
    explicit lock_guard(mutex_type &m) : _mutex(m) { _mutex.lock(); }
    lock_guard(mutex_type &m, adopt_lock_t) : _mutex(m) {}
    ~lock_guard() { _mutex.unlock(); }
private:
    lock_guard(const lock_guard &);            // = delete
    lock_guard &operator=(const lock_guard &); // = delete

    mutex_type &_mutex;
};


template <typename Mutex>
class unique_lock {
public:
    typedef Mutex mutex_type;

    unique_lock() : _mutex(0), _owns_lock(false) {}
    explicit unique_lock(mutex_type &m)
        : _mutex(addressOf(m)), _owns_lock(false)
    {
        lock();
        _owns_lock = true;
    }

    unique_lock(mutex_type &m, defer_lock_t)
        : _mutex(addressOf(m)), _owns_lock(false)
    {
    }

    unique_lock(mutex_type &m, try_to_lock_t)
        : _mutex(addressOf(m)), _owns_lock(_mutex->try_lock())
    {
    }

    unique_lock(mutex_type &m, adopt_lock_t)
        : _mutex(addressOf(m)), _owns_lock(true)
    {
    }

    // template<typename Clock, typename Duration>
    // unique_lock(mutex_type& m,
    //             const chrono::time_point<Clock, Duration>& atime);

    // template<typename Rep, typename Period>
    // unique_lock(mutex_type& m,
    //             const chrono::duration<Rep, Period>& rtime);

    ~unique_lock()
    {
        if (_owns_lock) unlock();
    }

    // unique_lock(unique_lock&& other)
    // unique_lock& operator=(unique_lock&& other)

    void lock()
    {
        if (!_mutex) throw_system_error(EPERM);
        if (_owns_lock) throw_system_error(EDEADLK);
        _mutex->lock();
        _owns_lock = true;
    }

    bool try_lock()
    {
        if (!_mutex) throw_system_error(EPERM);
        if (_owns_lock) throw_system_error(EDEADLK);
        _owns_lock = _mutex->try_lock();
        return _owns_lock;
    }

    // template<typename Clock, typename Duration>
    // bool try_lock_until(const chrono::time_point<Clock, Duration>& atime)

    // template<typename Rep, typename Period>
    // bool try_lock_for(const chrono::duration<Rep, Period>& rtime)

    void unlock()
    {
        if (!_owns_lock) throw_system_error(EPERM);
        if (_mutex) {
            _mutex->unlock();
            _owns_lock = false;
        }
    }

    void swap(unique_lock &other)
    {
        std::swap(_mutex, other._mutex);
        std::swap(_owns_lock, other._owns_lock);
    }

    mutex_type *release()
    {
        mutex_type *ret = _mutex;
        _mutex = 0;
        _owns_lock = false;
        return ret;
    }

    bool owns_lock() const { return _owns_lock; }
    operator bool() const { return owns_lock(); } // explicit
    mutex_type *mutex() const { return _mutex; }
private:
    unique_lock(const unique_lock &);            // = delete;
    unique_lock &operator=(const unique_lock &); // = delete;

    mutex_type *_mutex;
    bool _owns_lock;

    // basically std::addressof from C++11's <memory>
    template <typename T>
    inline T *addressOf(T &x)
    {
        return reinterpret_cast<T *>(
            &const_cast<char &>(reinterpret_cast<const volatile char &>(x)));
    }
};


template <typename Mutex>
void swap(unique_lock<Mutex> &x, unique_lock<Mutex> &y)
{
    x.swap(y);
}

} // namespace mk

#endif // mk_Mutex_h
