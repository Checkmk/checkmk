#include "OffsetTimeColumn.h"
#include "TimeColumnFilter.h"
#include "Query.h"

void OffsetTimeColumn::output(void *data, Query *query)
{
    query->outputTime(getValue(data, query));
}
    
Filter *OffsetTimeColumn::createFilter(int operator_id, char *value)
{
    // The TimeColumnFilter applies the timezone offset
    // from the Localtime: header
    return new TimeColumnFilter(this, operator_id, value);
}
