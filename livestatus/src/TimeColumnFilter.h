#ifndef TimeColumnFilter_h
#define TimeColumnFilter_h

#include "IntColumnFilter.h"

class TimeColumnFilter : public IntColumnFilter
{
public:
    TimeColumnFilter(IntColumn *column, int opid, char *value) : 
	IntColumnFilter(column, opid, value) {};
    virtual int32_t convertRefValue();
};

#endif // TimeColumnFilter_h

