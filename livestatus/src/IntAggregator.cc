#include <math.h>
#include "IntAggregator.h"
#include "StatsColumn.h"
#include "IntColumn.h"
#include "Query.h"

void IntAggregator::consume(void *data)
{
    _count++;
    int32_t value = _column->getValue(data);
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
	    _sumq += (double)value * (double)value;
	    break;
    }
}

		
void IntAggregator::output(Query *q)
{
    switch (_operation) {
    case STATS_OP_SUM:
    case STATS_OP_MIN:
    case STATS_OP_MAX:
	q->outputInteger64(_aggr); 
	break;

    case STATS_OP_AVG:
	q->outputDouble(double(_aggr) / _count);
	break;
    
    case STATS_OP_STD:
	if (_count <= 1)
	    q->outputDouble(0.0);
	else
	    q->outputDouble(sqrt((_sumq - ((double)_aggr * (double)_aggr) / _count)/(_count - 1)));
	break;
    }
}

/* Algorithmus fuer die Standardabweichung, 
   bei der man zuvor den Mittelwert nicht
   wissen muss:

   def std(l):
       sum = 0.0
       sumq = 0.0
       for x in l:
           sum += x
           sumq += x*x
       n = len(l)
       return ((sumq - sum*sum/n)/(n-1)) ** 0.5

*/

