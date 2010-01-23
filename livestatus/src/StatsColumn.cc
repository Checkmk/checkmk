#include "StatsColumn.h"
#include "Column.h"
#include "Filter.h"
#include "CountAggregator.h"
#include "IntAggregator.h"
#include "DoubleAggregator.h"

StatsColumn::~StatsColumn()
{
    if (_filter)
	delete _filter;
}

Aggregator *StatsColumn::createAggregator()
{
    if (_operation == STATS_OP_COUNT) 
	return new CountAggregator(_filter);
    else if (_column->type() == COLTYPE_INT)
	return new IntAggregator((IntColumn *)_column, _operation);
    else if (_column->type() == COLTYPE_DOUBLE)
	return new DoubleAggregator((DoubleColumn *)_column, _operation);
    else  // this is a bug
	return new CountAggregator(_filter);
}
