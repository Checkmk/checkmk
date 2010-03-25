#include "TimePointerColumn.h"
#include "TimeColumnFilter.h"
#include "Query.h"

void TimePointerColumn::output(void *data, Query *query)
{
    query->outputTime(getValue(data));
}
    
Filter *TimePointerColumn::createFilter(int operator_id, char *value)
{
    // The TimeColumnFilter applies the timezone offset
    // from the Localtime: header
    return new TimeColumnFilter(this, operator_id, value);
}
