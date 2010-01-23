#include <math.h>
#include "DoubleAggregator.h"
#include "StatsColumn.h"
#include "DoubleColumn.h"
#include "Query.h"

/* SORRY: This file is copy&pasted from IntAggregator.
   I hate copy & paste. But I also dislike complicating
   stuff by using C++ templates and the like.
   */

void DoubleAggregator::consume(void *data)
{
    _count++;
    double value = _column->getValue(data);
    switch (_operation) {
	case STATS_OP_SUM:
	case STATS_OP_AVG:
	    _aggr += value; break;

	case STATS_OP_MIN:
	    if (_count == 1)
		_aggr = value;
	    else if (value < _aggr)
		_aggr = value;
	    break;
	
	case STATS_OP_MAX:
	    if (_count == 1)
		_aggr = value;
	    else if (value > _aggr)
		_aggr = value;
	    break;

	case STATS_OP_STD:
	    _aggr += value;
	    _sumq += value * value;
	    break;
    }
}

		
void DoubleAggregator::output(Query *q)
{
    switch (_operation) {
    case STATS_OP_SUM:
    case STATS_OP_MIN:
    case STATS_OP_MAX:
	q->outputDouble(_aggr); 
	break;

    case STATS_OP_AVG:
	q->outputDouble(_aggr / _count);
	break;
    
    case STATS_OP_STD:
	if (_count <= 1)
	    q->outputDouble(0.0);
	else
	    q->outputDouble(sqrt((_sumq - (_aggr * _aggr) / _count)/(_count - 1)));
	break;
    }
}

