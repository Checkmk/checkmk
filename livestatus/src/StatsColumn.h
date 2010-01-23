#ifndef StatsColumn_h
#define StatsColumn_h

#define STATS_OP_COUNT 0
#define STATS_OP_SUM   1
#define STATS_OP_MIN   2
#define STATS_OP_MAX   3
#define STATS_OP_AVG   4
#define STATS_OP_STD   5

class Aggregator;
class Column;
class Filter;

class StatsColumn
{
    Column *_column;
    Filter *_filter;
    int _operation;

public:
    StatsColumn(Column *c, Filter *f, int o) : 
	_column(c), _filter(f), _operation(o) {};
    ~StatsColumn();
    int operation() { return _operation; };
    Filter *stealFilter() { Filter *f = _filter; _filter=0; return f; };
    Aggregator *createAggregator();
};

#endif // StatsColumn_h

