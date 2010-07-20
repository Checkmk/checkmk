#ifndef _TimeperiodsCache_h
#define _TimeperiodsCache_h

#include <map>
#include "nagios.h"

class TimeperiodsCache 
{
    time_t _cache_time;
    typedef std::map<timeperiod *, bool> _cache_t;
    _cache_t _cache;
    pthread_mutex_t _cache_lock;

public:
    TimeperiodsCache();
    ~TimeperiodsCache();
    void update(time_t now);
    bool inTimeperiod(timeperiod *tp);
};

#endif // _TimeperiodsCache_h
