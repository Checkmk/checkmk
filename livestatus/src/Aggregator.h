#ifndef Aggregator_h
#define Aggregator_h

#include "config.h"
#include <stdint.h>
class Query;

class Aggregator
{
protected:
    int      _operation;
    uint32_t _count;
public:
    Aggregator(int o) : _operation(o), _count(0) {};
    virtual void consume(void *data) = 0;
    virtual void output(Query *) = 0;
};


#endif // Aggregator_h

