#ifndef IntAggregator_h
#define IntAggregator_h

#include "Aggregator.h"
class IntColumn;

class IntAggregator : public Aggregator
{
    IntColumn *_column;
    int64_t _aggr;
    double _sumq;
public:
    IntAggregator(IntColumn *c, int o) : 
	Aggregator(o), _column(c), _aggr(0), _sumq(0) {};
    void consume(void *data);
    void output(Query *);
};

#endif // IntAggregator_h

