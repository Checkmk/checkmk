#ifndef DoubleAggregator_h
#define DoubleAggregator_h

#include "Aggregator.h"
class DoubleColumn;

class DoubleAggregator : public Aggregator
{
    DoubleColumn *_column;
    double _aggr;
    double _sumq;
public:
    DoubleAggregator(DoubleColumn *c, int o) : 
	Aggregator(o), _column(c), _aggr(0), _sumq(0) {};
    void consume(void *data);
    void output(Query *);
};

#endif // DoubleAggregator_h

