#include "OffsetTimeColumn.h"
#include "TimeColumnFilter.h"

void OffsetTimeColumn::output(void *data, Query *query)
{
    query->outputTime(getValue(data));
}
    
Filter *IntColumn::createFilter(int operator_id, char *value)
{
    // The TimeColumnFilter applies the timezone offset
    // from the Localtime: header
    return new TimeColumnFilter(this, operator_id, value);
}


