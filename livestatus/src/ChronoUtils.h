// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef ChronoUtils_h
#define ChronoUtils_h

#include "config.h"  // IWYU pragma: keep

#include <chrono>
#include <cstdlib>
#include <iomanip>
#include <ratio>
#include <string>
#include <utility>

namespace mk {
#if __cplusplus > 201703L
using days = std::chrono::days;
using weeks = std::chrono::weeks;
#else
using days = std::chrono::duration<int64_t, std::ratio<86400>>;
using weeks = std::chrono::duration<int64_t, std::ratio<604800>>;
#endif

// Using std::chrono::duration.count() in an unrestricted way is a maintenance
// nightmare: If you e.g. change the type of a member from seconds to
// microseconds, the compiler will very probably still be happy, but all count()
// use sites are wrong now! A much better alternative is to explicitly say in
// which duration units you actually want the ticks.
template <class ToDuration, class Rep, class Period>
constexpr typename ToDuration::rep ticks(
    const std::chrono::duration<Rep, Period> &d) {
    return std::chrono::duration_cast<ToDuration>(d).count();
}

}  // namespace mk

inline double elapsed_ms_since(std::chrono::steady_clock::time_point then) {
    return mk::ticks<std::chrono::duration<double, std::milli>>(
        std::chrono::steady_clock::now() - then);
}

inline tm to_tm(std::chrono::system_clock::time_point tp) {
    auto t = std::chrono::system_clock::to_time_t(tp);
    struct tm ret;
// NOTE: A brilliant example of how to make a simple API function a total
// chaos follows...
#if defined(__STDC_LIB_EXT1__)
    // C11 function, only guaranteed to be available when a
    //    #define __STDC_WANT_LIB_EXT1_ 1
    // is done before including <time.h>. Signature:
    //    struct tm *localtime_s(const time_t *restrict timer,
    //                           struct tm *restrict result)
    localtime_s(&t, &ret);
#elif defined(__WIN32)
    // Win32 variant, it keeps us entertained with swapped parameters and a
    // different return value, yay! Signature:
    //    errno_t localtime_s(struct tm* _tm, const time_t *time)
    localtime_s(&ret, &t);
#else
    // POSIX.1-2008 variant, available under MinGW64 only under obscure
    // circumstances, so better avoid it there. Signature:
    //    struct tm *localtime_r(const time_t *restrict timer,
    //                           struct tm *restrict result);
    localtime_r(&t, &ret);
#endif
    return ret;
}

inline std::chrono::system_clock::time_point from_tm(tm tp) {
    return std::chrono::system_clock::from_time_t(mktime(&tp));
}

template <typename Rep, typename Period>
inline timeval to_timeval(std::chrono::duration<Rep, Period> dur) {
    using namespace std::chrono_literals;
    timeval tv;
    // NOTE: The static_casts below are needed to avoid warning on e.g. some
    // 32bit platforms, because the underlying types might be larger than the
    // timeval fields. We can't use the correct POSIX types time_t and
    // suseconds_t because of the broken MinGW cross compiler, so we revert to
    // decltype.
    tv.tv_sec =
        static_cast<decltype(tv.tv_sec)>(mk::ticks<std::chrono::seconds>(dur));
    tv.tv_usec = static_cast<decltype(tv.tv_usec)>(
        mk::ticks<std::chrono::microseconds>(dur % 1s));
    return tv;
}

inline std::chrono::system_clock::time_point from_timeval(const timeval &tv) {
    return std::chrono::system_clock::time_point(
        std::chrono::seconds(tv.tv_sec) +
        std::chrono::microseconds(tv.tv_usec));
}

inline std::chrono::system_clock::time_point parse_time_t(
    const std::string &str) {
    return std::chrono::system_clock::from_time_t(atoi(str.c_str()));
}

template <typename Dur>
typename Dur::rep time_point_part(std::chrono::system_clock::time_point &tp) {
    return mk::ticks<Dur>(tp.time_since_epoch() % Dur(1000));
}

struct FormattedTimePoint {
    explicit FormattedTimePoint(
        std::chrono::system_clock::time_point time_point)
        : tp(time_point) {}

    std::chrono::system_clock::time_point tp;

    friend std::ostream &operator<<(std::ostream &os,
                                    const FormattedTimePoint &f) {
        tm local = to_tm(f.tp);
        return os << std::put_time(&local, "%Y-%m-%d %H:%M:%S");
    }
};

#endif  // ChronoUtils_h
