#ifndef CountAggregator_h
#define CountAggregator_h

#include "Aggregator.h"
#include "StatsColumn.h"

class Filter;

class CountAggregator : public Aggregator
{
    Filter *_filter;
public:
    CountAggregator(Filter *f) : Aggregator(STATS_OP_COUNT), _filter(f) {};
    void consume(void *data);
    void output(Query *);
};

#endif // CountAggregator_h

