#ifndef TimeColumnFilter_h
#define TimeColumnFilter_h

#include "IntColumnFilter.h"

class TimeColumnFilter : public IntColumnFilter
{
public:
    virtual int32_t convertRefValue();
};

#endif // TimeColumnFilter_h

