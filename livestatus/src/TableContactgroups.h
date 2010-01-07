#ifndef TableContactgroups_h
#define TableContactgroups_h

#include <set>
#include "config.h"
#include "Table.h"
#include "objects.h"

class TableContactgroups : public Table
{
public:
    TableContactgroups();
    const char *name() { return "contactgroups"; };
    void answerQuery(Query *query);
    void addColumns(Table *table, string prefix, int indirect_offset);
};

#endif // TableContactgroups_h

