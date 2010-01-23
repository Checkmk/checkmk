#include "CountAggregator.h"
#include "Query.h"
#include "Filter.h"

void CountAggregator::consume(void *data)
{
    // _filter is 0 --> no filter, accept all data
    if (!_filter || _filter->accepts(data))
	_count++;
}

void CountAggregator::output(Query *q)
{
    q->outputInteger(_count);
}
