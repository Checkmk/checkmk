#ifndef TableTimeperiods_h
#define TableTimeperiods_h

#include "Table.h"

class TableTimeperiods : public Table
{
public:
  TableTimeperiods();
  const char *name() { return "timeperiods"; };
  void answerQuery(Query *query);
  void addColumns(Table *table, string prefix, int indirect_offset);
};

#endif // TableTimeperiods_h

