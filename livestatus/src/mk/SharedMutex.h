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

#ifndef mk_SharedMutex_h
#define mk_SharedMutex_h

#include "config.h" // IWYU pragma: keep
#include <pthread.h>
#include "Mutex.h"

// A more or less drop-in replacement for C++14's <shared_mutex> (partial)

namespace mk {

// Note: This is not in the standard, but close enough to shared_mutex for our purposes.
class rw_mutex {
public:
    typedef pthread_rwlock_t *native_handle_type;
    rw_mutex() { check_status(pthread_rwlock_init(&_mutex, 0)); }
    ~rw_mutex() { check_status(pthread_rwlock_destroy(&_mutex)); }
    void lock() { check_status(pthread_rwlock_wrlock(&_mutex)); }
    bool try_lock()
    {
        int status = pthread_rwlock_trywrlock(&_mutex);
        if (status != EBUSY) check_status(status);
        return status == 0;
    }
    void unlock() { check_status(pthread_rwlock_unlock(&_mutex)); }
    void lock_shared() { check_status(pthread_rwlock_rdlock(&_mutex)); }
    bool try_lock_shared()
    {
        int status = pthread_rwlock_tryrdlock(&_mutex);
        if (status != EBUSY) check_status(status);
        return status == 0;
    }
    void unlock_shared() { check_status(pthread_rwlock_unlock(&_mutex)); }
    native_handle_type native_handle() { return &_mutex; }
private:
    rw_mutex(const rw_mutex &);            // = delete
    rw_mutex &operator=(const rw_mutex &); // = delete

    pthread_rwlock_t _mutex;
};


template <typename Mutex>
class shared_lock {
public:
    typedef Mutex mutex_type;

    shared_lock() : _mutex(0), _owns_lock(false) {}
    explicit shared_lock(mutex_type &m)
        : _mutex(addressOf(m)), _owns_lock(false)
    {
        lock();
        _owns_lock = true;
    }

    shared_lock(mutex_type &m, defer_lock_t)
        : _mutex(addressOf(m)), _owns_lock(false)
    {
    }

    shared_lock(mutex_type &m, try_to_lock_t)
        : _mutex(addressOf(m)), _owns_lock(_mutex->try_lock_shared())
    {
    }

    shared_lock(mutex_type &m, adopt_lock_t)
        : _mutex(addressOf(m)), _owns_lock(true)
    {
    }

    // template<typename Clock, typename Duration>
    // shared_lock(mutex_type& m,
    //             const chrono::time_point<Clock, Duration>& atime);

    // template<typename Rep, typename Period>
    // shared_lock(mutex_type& m,
    //             const chrono::duration<Rep, Period>& rtime);

    ~shared_lock()
    {
        if (_owns_lock) unlock();
    }

    // shared_lock(shared_lock&& other)
    // shared_lock& operator=(shared_lock&& other)

    void lock()
    {
        if (!_mutex) throw_system_error(EPERM);
        if (_owns_lock) throw_system_error(EDEADLK);
        _mutex->lock_shared();
        _owns_lock = true;
    }

    bool try_lock()
    {
        if (!_mutex) throw_system_error(EPERM);
        if (_owns_lock) throw_system_error(EDEADLK);
        _owns_lock = _mutex->try_lock_shared();
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
            _mutex->unlock_shared();
            _owns_lock = false;
        }
    }

    void swap(shared_lock &other)
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
    shared_lock(const shared_lock &);            // = delete;
    shared_lock &operator=(const shared_lock &); // = delete;

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
void swap(shared_lock<Mutex> &x, shared_lock<Mutex> &y)
{
    x.swap(y);
}

} // namespace mk

#endif // mk_SharedMutex_h
