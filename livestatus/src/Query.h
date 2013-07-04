// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
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
#include "nagios.h"

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
class StatsColumn;
class Aggregator;

#define OUTPUT_FORMAT_CSV    0
#define OUTPUT_FORMAT_JSON   1
#define OUTPUT_FORMAT_PYTHON 2

#define RESPONSE_HEADER_OFF     0
#define RESPONSE_HEADER_FIXED16 1
#define RESPONSE_HEADER_HTTP    2 // not yet implemented

#define ANDOR_OR     0
#define ANDOR_AND    1
#define ANDOR_NEGATE 2


class Query
{
    OutputBuffer *_output;
    Table        *_table;
    AndingFilter  _filter;
    contact      *_auth_user;
    AndingFilter  _wait_condition;
    unsigned      _wait_timeout;
    unsigned      _wait_trigger;
    void         *_wait_object;
    string        _field_separator;
    string        _dataset_separator;
    string        _list_separator;
    string        _host_service_separator;
    bool          _show_column_headers;
    bool          _need_ds_separator;
    int           _output_format;
    int           _limit;
    unsigned      _current_line;
    int           _timezone_offset;

    // normal queries
    typedef vector<Column *> _columns_t;
    _columns_t _columns;
    _columns_t _dummy_columns; // dynamically allocated. Must delete them.

    // stats queries
    typedef vector<StatsColumn *> _stats_columns_t;
    _stats_columns_t _stats_columns; // must also delete
    Aggregator **_stats_aggregators;

    typedef vector<string> _stats_group_spec_t;
    typedef map<_stats_group_spec_t, Aggregator **> _stats_groups_t;
    _stats_groups_t _stats_groups;

public:
    Query(InputBuffer *, OutputBuffer *out, Table *);
    ~Query();
    bool processDataset(void *);
    void start();
    void finish();
    void setDefaultColumns(const char *);
    void addColumn(Column *column);
    void setShowColumnHeaders(bool x) { _show_column_headers = x; }
    void setError(int error_code, const char * msg);
    bool hasNoColumns();
    contact *authUser() { return _auth_user; }
    void outputDatasetBegin();
    void outputDatasetEnd();
    void outputFieldSeparator();
    void outputInteger(int32_t);
    void outputInteger64(int64_t);
    void outputTime(int32_t);
    void outputUnsignedLong(unsigned long);
    void outputCounter(counter_t);
    void outputDouble(double);
    void outputUnicodeEscape(unsigned value);
    void outputString(const char *);
    void outputHostService(const char *, const char *);
    void outputBeginList();
    void outputListSeparator();
    void outputEndList();
    void outputBeginSublist();
    void outputSublistSeparator();
    void outputEndSublist();
    void outputBeginDict();
    void outputDictSeparator();
    void outputDictValueSeparator();
    void outputEndDict();
    void *findIndexFilter(const char *columnname);
    void *findTimerangeFilter(const char *columnname, time_t *, time_t *);
    void findIntLimits(const char *columnname, int *lower, int *upper);
    void optimizeBitmask(const char *columnname, uint32_t *bitmask);
    int timezoneOffset() { return _timezone_offset; }
    AndingFilter *filter() { return &_filter; }

private:
    bool doStats();
    void doWait();
    Aggregator **getStatsGroup(_stats_group_spec_t &groupspec);
    void computeStatsGroupSpec(_stats_group_spec_t &groupspec, void *data);
    Filter *createFilter(Column *column, int operator_id, char *value);
    void parseFilterLine(char *line, bool filter /* and not cond */);
    void parseStatsLine(char *line);
    void parseStatsGroupLine(char *line);
    void parseAndOrLine(char *line, int andor, bool filter /* and not cond */);
    void parseNegateLine(char *line, bool filter /* and not cond */);
    void parseStatsAndOrLine(char *line, int andor);
    void parseStatsNegateLine(char *line);
    void parseColumnsLine(char *line);
    void parseColumnHeadersLine(char *line);
    void parseLimitLine(char *line);
    void parseSeparatorsLine(char *line);
    void parseOutputFormatLine(char *line);
    void parseKeepAliveLine(char *line);
    void parseResponseHeaderLine(char *line);
    void parseAuthUserHeader(char *line);
    void parseWaitTimeoutLine(char *line);
    void parseWaitTriggerLine(char *line);
    void parseWaitObjectLine(char *line);
    void parseLocaltimeLine(char *line);
    int lookupOperator(const char *opname);
    Column *createDummyColumn(const char *name);
};


#endif // Query_h
