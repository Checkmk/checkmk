#include <time.h>

#include "TimeperiodsCache.h"
#include "nagios.h"
#include "logger.h"

extern timeperiod *timeperiod_list;

TimeperiodsCache::TimeperiodsCache()
{
    pthread_mutex_init(&_cache_lock, 0);
    _cache_time = 0;
}


TimeperiodsCache::~TimeperiodsCache()
{
    pthread_mutex_destroy(&_cache_lock);
}


void TimeperiodsCache::update(time_t now)
{
    pthread_mutex_lock(&_cache_lock);

    // update cache only once a minute. The timeperiod
    // definitions have 1 minute as granularity, so a 
    // 1sec resultion is not needed.
    int minutes = now / 60;
    if (minutes == _cache_time) {
        pthread_mutex_unlock(&_cache_lock);
        return;
    }

    _cache_time = minutes;
    _cache.clear();

    // Loop over all timeperiods and compute if we are
    // currently in
    timeperiod *tp = timeperiod_list;
    while (tp) {
        bool is_in = 0 == check_time_against_period(now, tp);
	_cache.insert(std::make_pair(tp, is_in));
	tp = tp->next;
    }
    pthread_mutex_unlock(&_cache_lock);
}


bool TimeperiodsCache::inTimeperiod(timeperiod *tp)
{
    bool is_in;
    pthread_mutex_lock(&_cache_lock);
    _cache_t::iterator it = _cache.find(tp);
    if (it != _cache.end())
	is_in = it->second;
    else {
        logger(LG_INFO, "No timeperiod information available for %s.", tp->name);
        time_t now = time(0);
	is_in = 0 == check_time_against_period(now, tp);
    }
    pthread_mutex_unlock(&_cache_lock);
    return is_in;
}

