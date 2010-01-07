#include "nagios.h"
#include "Query.h"
#include "OffsetStringColumn.h"
#include "TableContactgroups.h"
#include "ContactgroupsMemberColumn.h"

extern contactgroup *contactgroup_list;

TableContactgroups::TableContactgroups()
{
    addColumns(this, "", -1);
}


void TableContactgroups::addColumns(Table *table, string prefix, int indirect_offset)
{
    contactgroup cg;
    char *ref = (char *)&cg;
    table->addColumn(new OffsetStringColumn(prefix + "name",
		"The name of the contactgroup", (char *)(&cg.group_name) - ref, indirect_offset));
    table->addColumn(new OffsetStringColumn(prefix + "alias",
		"The alias of the contactgroup", (char *)(&cg.alias) - ref, indirect_offset));
    table->addColumn(new ContactgroupsMemberColumn(prefix + "members",
		"A list of all members of this contactgroup", indirect_offset));
}


void TableContactgroups::answerQuery(Query *query)
{
    contactgroup *cg = contactgroup_list;
    while (cg) {
	if (!query->processDataset(cg)) break;
	cg = cg->next;
    }
}
