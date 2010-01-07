#include "nagios.h"
#include "Query.h"
#include "OffsetStringColumn.h"
#include "TableTimeperiods.h"

extern timeperiod *timeperiod_list;

TableTimeperiods::TableTimeperiods()
{
    addColumns(this, "", -1);
}


void TableTimeperiods::addColumns(Table *table, string prefix, int indirect_offset)
{
    timeperiod tp;
    char *ref = (char *)&tp;
    table->addColumn(new OffsetStringColumn(prefix + "name", 
		"The name of the timeperiod", (char *)(&tp.name) - ref, indirect_offset));
    table->addColumn(new OffsetStringColumn(prefix + "alias", 
		"The alias of the timeperiod", (char *)(&tp.alias) - ref, indirect_offset));
    // TODO: add days and exceptions
}


void TableTimeperiods::answerQuery(Query *query)
{
    timeperiod *tp = timeperiod_list;
    while (tp) {
	if (!query->processDataset(tp)) break;
	tp = tp->next;
    }
}
