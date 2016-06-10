// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
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
// tails. You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#ifndef Query_h
#define Query_h

#include "config.h"  // IWYU pragma: keep
#include <stdint.h>
#include <time.h>
#include <list>
#include <map>
#include <string>
#include <unordered_set>
#include <vector>
#include "AndingFilter.h"
#include "OutputBuffer.h"
#include "global_counters.h"
#include "nagios.h"  // IWYU pragma: keep
#include "opids.h"
class Aggregator;
class Column;
class Filter;
class StatsColumn;
class Table;

enum class OutputFormat { csv, json, python };

class Query {
    OutputBuffer *_output;
    Table *_table;
    AndingFilter _filter;
    contact *_auth_user;
    AndingFilter _wait_condition;
    unsigned _wait_timeout;
    struct trigger *_wait_trigger;
    void *_wait_object;
    std::string _field_separator;
    std::string _dataset_separator;
    std::string _list_separator;
    std::string _host_service_separator;
    bool _show_column_headers;
    bool _need_ds_separator;
    OutputFormat _output_format;
    int _limit;
    int _time_limit;
    time_t _time_limit_timeout;
    unsigned _current_line;
    int _timezone_offset;

    // normal queries
    typedef std::vector<Column *> _columns_t;
    _columns_t _columns;
    _columns_t _dummy_columns;  // dynamically allocated. Must delete them.

    // stats queries
    typedef std::vector<StatsColumn *> _stats_columns_t;
    _stats_columns_t _stats_columns;  // must also delete
    Aggregator **_stats_aggregators;

    typedef std::vector<std::string> _stats_group_spec_t;
    typedef std::map<_stats_group_spec_t, Aggregator **> _stats_groups_t;
    _stats_groups_t _stats_groups;

    std::unordered_set<Column *> _all_columns;

public:
    Query(const std::list<std::string> &lines, OutputBuffer *output, Table *);
    ~Query();
    void process();
    bool processDataset(void *);
    bool timelimitReached();
    void addColumn(Column *column);

    OutputFormat getOutputFormat() const;
    void setOutputFormat(OutputFormat format);

    void add(const std::string &str);
    void add(const std::vector<char> &blob);
    size_t size();
    void setResponseHeader(OutputBuffer::ResponseHeader r);
    void setDoKeepalive(bool d);
    void setError(OutputBuffer::ResponseCode code, const std::string &message);

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
    void outputNull();
    void outputAsciiEscape(char value);
    void outputUnicodeEscape(unsigned value);
    void outputString(const char *, int len = -1);
    void outputBlob(const std::vector<char> *blob);
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
    void *findIndexFilter(const std::string &column_name);
    void *findTimerangeFilter(const char *columnname, time_t *, time_t *);
    void findIntLimits(const std::string &column_name, int *lower, int *upper);
    void optimizeBitmask(const std::string &column_name, uint32_t *bitmask);
    int timezoneOffset() { return _timezone_offset; }
    AndingFilter *filter() { return &_filter; }
    std::unordered_set<Column *> *allColumns() { return &_all_columns; }

private:
    bool doStats();
    void doWait();
    Aggregator **getStatsGroup(_stats_group_spec_t &groupspec);
    void computeStatsGroupSpec(_stats_group_spec_t &groupspec, void *data);
    Filter *createFilter(Column *column, RelationalOperator relOp,
                         const std::string &value);
    void parseFilterLine(char *line, AndingFilter &filter);
    void parseStatsLine(char *line);
    void parseStatsGroupLine(char *line);
    void parseAndOrLine(char *line, LogicalOperator andor, AndingFilter &filter,
                        std::string header);
    void parseNegateLine(char *line, AndingFilter &filter, std::string header);
    void parseStatsAndOrLine(char *line, LogicalOperator andor);
    void parseStatsNegateLine(char *line);
    void parseColumnsLine(char *line);
    void parseColumnHeadersLine(char *line);
    void parseLimitLine(char *line);
    void parseTimelimitLine(char *line);
    void parseSeparatorsLine(char *line);
    void parseOutputFormatLine(char *line);
    void parseKeepAliveLine(char *line);
    void parseResponseHeaderLine(char *line);
    void parseAuthUserHeader(char *line);
    void parseWaitTimeoutLine(char *line);
    void parseWaitTriggerLine(char *line);
    void parseWaitObjectLine(char *line);
    void parseLocaltimeLine(char *line);
    void start();
    void finish();
    Column *createDummyColumn(const char *name);
};

#endif  // Query_h
