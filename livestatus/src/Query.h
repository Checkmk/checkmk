// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2009             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
// 
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
// 
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#ifndef Query_h
#define Query_h

#include "config.h"

#include <stdio.h>
#include <string>
#include <map>
using namespace std;

#include "AndingFilter.h"
#include "global_counters.h"

class Table;
class Column;
class OutputBuffer;
class InputBuffer;

#define OUTPUT_FORMAT_CSV  0
#define OUTPUT_FORMAT_JSON 1

#define RESPONSE_HEADER_OFF     0
#define RESPONSE_HEADER_FIXED16 1
#define RESPONSE_HEADER_HTTP    2 // not yet implemented

#define ANDOR_OR  0
#define ANDOR_AND 1

class Query
{ 
   OutputBuffer *_output;
   Table        *_table;
   AndingFilter  _filter;
   AndingFilter  _stats;
   string        _field_separator;
   string        _dataset_separator;
   string        _list_separator;
   string        _host_service_separator;
   int           _output_format;
   bool          _show_column_headers;
   bool          _need_ds_separator;
   int           _limit;
   unsigned      _current_line;

   typedef vector<Column *> _columns_t;
   _columns_t _columns;
   _columns_t _dummy_columns; // dynamically allocated. Must delete them.
   uint32_t *_stats_counts;
   Column *_stats_group_column;
   typedef map<string, uint32_t *> _stats_groups_t;
   _stats_groups_t _stats_groups; 

public:
   Query(InputBuffer *, OutputBuffer *out, Table *); 
   ~Query();
   bool processDataset(void *);
   void start();
   void finish();
   void setDefaultColumns(const char *);
   void addColumn(Column *column);
   void setShowColumnHeaders(bool x) { _show_column_headers = x; };
   bool hasNoColumns();
   void outputDatasetBegin();
   void outputDatasetEnd();
   void outputFieldSeparator();
   void outputInteger(int32_t);
   void outputUnsignedLong(unsigned long);
   void outputCounter(counter_t);
   void outputDouble(double);
   void outputString(const char *);
   void outputHostService(const char *, const char *);
   void outputBeginList();
   void outputListSeparator();
   void outputEndList();
   void *findIndexFilter(const char *columnname);

private:
   bool doStats();
   uint32_t *getStatsGroup(string name);
   void parseFilterLine(char *line, bool stats);
   void parseStatsGroupLine(char *line);
   void parseAndOrLine(char *line, int andor, bool stats);
   void parseColumnsLine(char *line);
   void parseColumnHeadersLine(char *line);
   void parseLimitLine(char *line);
   void parseSeparatorsLine(char *line);
   void parseOutputFormatLine(char *line);
   void parseKeepAliveLine(char *line);
   void parseResponseHeaderLine(char *line);
   int lookupOperator(const char *opname);
   Column *createDummyColumn(const char *name);
};


#endif // Query_h
