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

#include <string.h>
#include <strings.h>
#include <stdlib.h>
#include <sys/time.h>
#include <errno.h>

#include "logger.h"
#include "opids.h"
#include "strutil.h"
#include "Table.h"
#include "Query.h"
#include "Filter.h"
#include "Column.h"
#include "EmptyColumn.h"
#include "OutputBuffer.h"
#include "InputBuffer.h"
#include "StatsColumn.h"
#include "Aggregator.h"
#include "OringFilter.h"
#include "NegatingFilter.h"
#include "waittriggers.h"
#include "data_encoding.h"
#include "auth.h"

extern int g_debug_level;
extern unsigned long g_max_response_size;
extern int g_data_encoding;

Query::Query(InputBuffer *input, OutputBuffer *output, Table *table) :
    _output(output),
    _table(table),
    _auth_user(0),
    _wait_timeout(0),
    _wait_trigger(WT_NONE),
    _wait_object(0),
    _field_separator(";"),
    _dataset_separator("\n"),
    _list_separator(","),
    _host_service_separator("|"),
    _show_column_headers(true),
    _need_ds_separator(false),
    _output_format(OUTPUT_FORMAT_CSV),
    _limit(-1),
    _current_line(0),
    _timezone_offset(0)
{
    while (input->moreLines())
    {
        string line = input->nextLine();
        char *buffer = (char *)line.c_str();
        rstrip(buffer);
        if (g_debug_level > 0)
            logger(LG_INFO, "Query: %s", buffer);
        if (!strncmp(buffer, "Filter:", 7))
            parseFilterLine(lstrip(buffer + 7), true);

        else if (!strncmp(buffer, "Or:", 3))
            parseAndOrLine(lstrip(buffer + 3), ANDOR_OR, true);

        else if (!strncmp(buffer, "And:", 4))
            parseAndOrLine(lstrip(buffer + 4), ANDOR_AND, true);

        else if (!strncmp(buffer, "Negate:", 7))
            parseNegateLine(lstrip(buffer + 7), true);

        else if (!strncmp(buffer, "StatsOr:", 8))
            parseStatsAndOrLine(lstrip(buffer + 8), ANDOR_OR);

        else if (!strncmp(buffer, "StatsAnd:", 9))
            parseStatsAndOrLine(lstrip(buffer + 9), ANDOR_AND);

        else if (!strncmp(buffer, "StatsNegate:", 12))
            parseStatsNegateLine(lstrip(buffer + 12));

        else if (!strncmp(buffer, "Stats:", 6))
            parseStatsLine(lstrip(buffer + 6));

        else if (!strncmp(buffer, "StatsGroupBy:", 13))
            parseStatsGroupLine(lstrip(buffer + 13));

        else if (!strncmp(buffer, "Columns:", 8))
            parseColumnsLine(lstrip(buffer + 8));

        else if (!strncmp(buffer, "ColumnHeaders:", 14))
            parseColumnHeadersLine(lstrip(buffer + 14));

        else if (!strncmp(buffer, "Limit:", 6))
            parseLimitLine(lstrip(buffer + 6));

        else if (!strncmp(buffer, "AuthUser:", 9))
            parseAuthUserHeader(lstrip(buffer + 9));

        else if (!strncmp(buffer, "Separators:", 11))
            parseSeparatorsLine(lstrip(buffer + 11));

        else if (!strncmp(buffer, "OutputFormat:", 13))
            parseOutputFormatLine(lstrip(buffer + 13));

        else if (!strncmp(buffer, "ResponseHeader:", 15))
            parseResponseHeaderLine(lstrip(buffer + 15));

        else if (!strncmp(buffer, "KeepAlive:", 10))
            parseKeepAliveLine(lstrip(buffer + 10));

        else if (!strncmp(buffer, "WaitCondition:", 14))
            parseFilterLine(lstrip(buffer + 14), false);

        else if (!strncmp(buffer, "WaitConditionAnd:", 17))
            parseAndOrLine(lstrip(buffer + 17), ANDOR_AND, false);

        else if (!strncmp(buffer, "WaitConditionOr:", 16))
            parseAndOrLine(lstrip(buffer + 16), ANDOR_OR, false);

        else if (!strncmp(buffer, "WaitConditionNegate:", 20))
            parseNegateLine(lstrip(buffer + 20), false);

        else if (!strncmp(buffer, "WaitTrigger:", 12))
            parseWaitTriggerLine(lstrip(buffer + 12));

        else if (!strncmp(buffer, "WaitObject:", 11))
            parseWaitObjectLine(lstrip(buffer + 11));

        else if (!strncmp(buffer, "WaitTimeout:", 12))
            parseWaitTimeoutLine(lstrip(buffer + 12));

        else if (!strncmp(buffer, "Localtime:", 10))
            parseLocaltimeLine(lstrip(buffer + 10));


        else if (!buffer[0])
            break;

        else {
            output->setError(RESPONSE_CODE_INVALID_HEADER, "Undefined request header '%s'", buffer);
            break;
        }
    }
}

Query::~Query()
{
    // delete dummy-columns
    for (_columns_t::iterator it = _dummy_columns.begin();
            it != _dummy_columns.end();
            ++it)
    {
        delete *it;
    }

    // delete stats columns
    for (_stats_columns_t::iterator it = _stats_columns.begin();
            it != _stats_columns.end();
            ++it)
    {
        delete *it;
    }
}

Column *Query::createDummyColumn(const char *name)
{
    Column *col = new EmptyColumn(name, "Dummy column");
    _dummy_columns.push_back(col);
    return col;
}


void Query::addColumn(Column *column)
{
    _columns.push_back(column);
}

void Query::setError(int error_code, const char* msg){
	_output->setError(error_code, msg);
}

bool Query::hasNoColumns()
{
    return _columns.size() == 0 && !doStats();
}

int Query::lookupOperator(const char *opname)
{
    int opid;
    int negate = 1;
    if (opname[0] == '!') {
        negate = -1;
        opname ++;
    }

    if (!strcmp(opname, "="))
        opid = OP_EQUAL;
    else if (!strcmp(opname, "~"))
        opid = OP_REGEX;
    else if (!strcmp(opname, "=~"))
        opid = OP_EQUAL_ICASE;
    else if (!strcmp(opname, "~~"))
        opid = OP_REGEX_ICASE;
    else if (!strcmp(opname, ">"))
        opid = OP_GREATER;
    else if (!strcmp(opname, "<"))
        opid = OP_LESS;
    else if (!strcmp(opname, ">=")) {
        opid = OP_LESS;
        negate = -negate;
    }
    else if (!strcmp(opname, "<=")) {
        opid = OP_GREATER;
        negate = -negate;
    }
    else
        opid = OP_INVALID;
    return negate * opid;
}

Filter *Query::createFilter(Column *column, int operator_id, char *value)
{
    Filter *filter = column->createFilter(operator_id, value);
    if (!filter)
        _output->setError(RESPONSE_CODE_INVALID_HEADER, "cannot create filter on table %s", _table->name());
    else if (filter->hasError()) {
        _output->setError(filter->errorCode(), "error in Filter header: %s", filter->errorMessage().c_str());
        delete filter;
        filter = 0;
    }
    else
        filter->setQuery(this);
    return filter;
}


void Query::parseAndOrLine(char *line, int andor, bool filter)
{
    char *value = next_field(&line);
    int number = atoi(value);
    if (!isdigit(value[0]) || number <= 0) {
        _output->setError(RESPONSE_CODE_INVALID_HEADER, "Invalid value for %s%s: need non-zero integer number",
                filter ? "" : "WaitCondition",
                andor == ANDOR_OR ? "Or" : "And");
        return;
    }
    if (filter)
        _filter.combineFilters(number, andor);
    else
        _wait_condition.combineFilters(number, andor);
}

void Query::parseNegateLine(char *line, bool filter)
{
    if (next_field(&line)) {
        _output->setError(RESPONSE_CODE_INVALID_HEADER,
                filter ? "Negate: does not take any arguments"
                : "WaitConditionNegate: does not take any arguments");
        return;
    }

    Filter *to_negate;
    if (filter) {
        to_negate = _filter.stealLastSubfiler();
        if (!to_negate) {
            _output->setError(RESPONSE_CODE_INVALID_HEADER, "Negate: no Filter: header to negate");
            return;
        }
    }
    else {
        to_negate = _wait_condition.stealLastSubfiler();
        if (!to_negate) {
            _output->setError(RESPONSE_CODE_INVALID_HEADER, "Negate: no Wait:-condition negate");
            return;
        }
    }
    Filter *negated = new NegatingFilter(to_negate);
    if (filter)
        _filter.addSubfilter(negated);
    else
        _wait_condition.addSubfilter(negated);
}


void Query::parseStatsAndOrLine(char *line, int andor)
{
    char *value = next_field(&line);
    int number = atoi(value);
    if (!isdigit(value[0]) || number <= 0) {
        _output->setError(RESPONSE_CODE_INVALID_HEADER, "Invalid value for Stats%s: need non-zero integer number",
                andor == ANDOR_OR ? "Or" : "And");
        return;
    }

    // The last 'number' StatsColumns must be of type STATS_OP_COUNT
    AndingFilter *anding = (andor == ANDOR_OR) ? new OringFilter() : new AndingFilter();
    while (number > 0) {
        if (_stats_columns.size() == 0) {
            _output->setError(RESPONSE_CODE_INVALID_HEADER, "Invalid count for Stats%s: too few Stats: headers available",
                    andor == ANDOR_OR ? "Or" : "And");
            delete anding;
            return;
        }

        StatsColumn *col = _stats_columns.back();
        if (col->operation() != STATS_OP_COUNT) {
            _output->setError(RESPONSE_CODE_INVALID_HEADER, "Can use Stats%s only on Stats: headers of filter type",
                    andor == ANDOR_OR ? "Or" : "And");
            delete anding;
            return;
        }
        anding->addSubfilter(col->stealFilter());
        delete col;
        _stats_columns.pop_back();
        number --;
    }
    _stats_columns.push_back(new StatsColumn(0, anding, STATS_OP_COUNT));
}


void Query::parseStatsNegateLine(char *line)
{
    if (next_field(&line)) {
        _output->setError(RESPONSE_CODE_INVALID_HEADER, "StatsNegate: does not take any arguments");
        return;
    }
    if (_stats_columns.size() == 0) {
        _output->setError(RESPONSE_CODE_INVALID_HEADER, "StatsNegate: no Stats: headers available");
        return;
    }
    StatsColumn *col = _stats_columns.back();
    if (col->operation() != STATS_OP_COUNT) {
        _output->setError(RESPONSE_CODE_INVALID_HEADER, "Can use StatsNegate only on Stats: headers of filter type");
        return;
    }
    NegatingFilter *negated = new NegatingFilter(col->stealFilter());
    delete col;
    _stats_columns.pop_back();
    _stats_columns.push_back(new StatsColumn(0, negated, STATS_OP_COUNT));
}

void Query::parseStatsLine(char *line)
{
    if (!_table)
        return;

    // first token is either aggregation operator or column name
    char *col_or_op = next_field(&line);
    if (!col_or_op) {
        _output->setError(RESPONSE_CODE_INVALID_HEADER, "empty stats line");
        return;
    }

    int operation = STATS_OP_COUNT;
    if (!strcmp(col_or_op, "sum"))
        operation = STATS_OP_SUM;
    else if (!strcmp(col_or_op, "min"))
        operation = STATS_OP_MIN;
    else if (!strcmp(col_or_op, "max"))
        operation = STATS_OP_MAX;
    else if (!strcmp(col_or_op, "avg"))
        operation = STATS_OP_AVG;
    else if (!strcmp(col_or_op, "std"))
        operation = STATS_OP_STD;
    else if (!strcmp(col_or_op, "suminv"))
        operation = STATS_OP_SUMINV;
    else if (!strcmp(col_or_op, "avginv"))
        operation = STATS_OP_AVGINV;

    char *column_name;
    if (operation == STATS_OP_COUNT)
        column_name = col_or_op;
    else {
        // aggregation operator is followed by column name
        column_name = next_field(&line);
        if (!column_name) {
            _output->setError(RESPONSE_CODE_INVALID_HEADER, "missing column name in stats header");
            return;
        }
    }

    Column *column = _table->column(column_name);
    if (!column) {
        _output->setError(RESPONSE_CODE_INVALID_HEADER, "invalid stats header: table '%s' has no column '%s'", _table->name(), column_name);
        return;
    }

    StatsColumn *stats_col;
    if (operation == STATS_OP_COUNT)
    {
        char *operator_name = next_field(&line);
        if (!operator_name) {
            _output->setError(RESPONSE_CODE_INVALID_HEADER, "invalid stats header: missing operator after table '%s'", column_name);
            return;
        }
        int operator_id = lookupOperator(operator_name);
        if (operator_id == OP_INVALID) {
            _output->setError(RESPONSE_CODE_INVALID_HEADER, "invalid stats operator '%s'", operator_name);
            return;
        }
        char *value = lstrip(line);
        if (!value) {
            _output->setError(RESPONSE_CODE_INVALID_HEADER, "invalid stats: missing value after operator '%s'", operator_name);
            return;
        }

        Filter *filter = createFilter(column, operator_id, value);
        if (!filter)
            return;
        stats_col = new StatsColumn(column, filter, operation);
    }
    else
        stats_col = new StatsColumn(column, 0, operation);
    _stats_columns.push_back(stats_col);

    /* Default to old behaviour: do not output column headers if we
       do Stats queries */
    _show_column_headers = false;
}


void Query::parseFilterLine(char *line, bool is_filter)
{
    if (!_table)
        return;

    char *column_name = next_field(&line);
    if (!column_name) {
        _output->setError(RESPONSE_CODE_INVALID_HEADER, "empty filter line");
        return;
    }

    Column *column = _table->column(column_name);
    if (!column) {
        _output->setError(RESPONSE_CODE_INVALID_HEADER, "invalid filter: table '%s' has no column '%s'", _table->name(), column_name);
        return;
    }

    char *operator_name = next_field(&line);
    if (!operator_name) {
        _output->setError(RESPONSE_CODE_INVALID_HEADER, "invalid filter header: missing operator after table '%s'", column_name);
        return;
    }
    int operator_id = lookupOperator(operator_name);
    if (operator_id == OP_INVALID) {
        _output->setError(RESPONSE_CODE_INVALID_HEADER, "invalid filter operator '%s'", operator_name);
        return;
    }
    char *value = lstrip(line);
    if (!value) {
        _output->setError(RESPONSE_CODE_INVALID_HEADER, "invalid filter: missing value after operator '%s'", operator_name);
        return;
    }

    Filter *filter = createFilter(column, operator_id, value);
    if (filter) {
        if (is_filter)
            _filter.addSubfilter(filter);
        else
            _wait_condition.addSubfilter(filter);
    }
}

void Query::parseAuthUserHeader(char *line)
{
    if (!_table)
        return;
    _auth_user = find_contact(line);
    if (!_auth_user) {
        // Do not handle this as error any more. In a multi site setup
        // not all users might be present on all sites by design.
        _auth_user = UNKNOWN_AUTH_USER;
        // _output->setError(RESPONSE_CODE_UNAUTHORIZED, "AuthUser: no such user '%s'", line);
    }

}

void Query::parseStatsGroupLine(char *line)
{
    logger(LOG_WARNING, "Warning: StatsGroupBy is deprecated. "
                        "Please use Columns instead.");
    parseColumnsLine(line);
}


void Query::parseColumnsLine(char *line)
{
    if (!_table)
        return;
    char *column_name;
    while (0 != (column_name = next_field(&line))) {
        Column *column = _table->column(column_name);
        if (column)
            _columns.push_back(column);
        else {
            _output->setError(RESPONSE_CODE_INVALID_HEADER,
                   "Table '%s' has no column '%s'", _table->name(), column_name);
            Column *col = createDummyColumn(column_name);
            _columns.push_back(col);
        }
    }
    _show_column_headers = false;
}

void Query::parseSeparatorsLine(char *line)
{
    char dssep = 0, fieldsep = 0, listsep = 0, hssep = 0;
    char *token = next_field(&line);
    if (token) dssep = atoi(token);
    token = next_field(&line);
    if (token) fieldsep = atoi(token);
    token = next_field(&line);
    if (token) listsep = atoi(token);
    token = next_field(&line);
    if (token) hssep = atoi(token);

    // if (dssep == fieldsep
    //       || dssep == listsep
    //       || fieldsep == listsep
    //       || dssep == hssep
    //       || fieldsep == hssep
    //       || listsep == hssep)
    // {
    //    _output->setError(RESPONSE_CODE_INVALID_HEADER, "invalid Separators: need four different integers");
    //    return;
    // }
    _dataset_separator      = string(&dssep, 1);
    _field_separator        = string(&fieldsep, 1);
    _list_separator         = string(&listsep, 1);
    _host_service_separator = string(&hssep, 1);
}

void Query::parseOutputFormatLine(char *line)
{
    char *format = next_field(&line);
    if (!strcmp(format, "csv"))
        _output_format = OUTPUT_FORMAT_CSV;
    else if (!strcmp(format, "json"))
        _output_format = OUTPUT_FORMAT_JSON;
    else if (!strcmp(format, "python"))
        _output_format = OUTPUT_FORMAT_PYTHON;
    else
        _output->setError(RESPONSE_CODE_INVALID_HEADER,
               "Invalid output format. Only 'csv' and 'json' are available.");
}

void Query::parseColumnHeadersLine(char *line)
{
    char *value = next_field(&line);
    if (!strcmp(value, "on"))
        _show_column_headers = true;
    else if (!strcmp(value, "off"))
        _show_column_headers = false;
    else
        _output->setError(RESPONSE_CODE_INVALID_HEADER,
              "Invalid value for ColumnHeaders: must be 'on' or 'off'");
}

void Query::parseKeepAliveLine(char *line)
{
    char *value = next_field(&line);
    if (!strcmp(value, "on"))
        _output->setDoKeepalive(true);
    else if (!strcmp(value, "off"))
        _output->setDoKeepalive(false);
    else
        _output->setError(RESPONSE_CODE_INVALID_HEADER,
                "Invalid value for KeepAlive: must be 'on' or 'off'");
}

void Query::parseResponseHeaderLine(char *line)
{
    char *value = next_field(&line);
    if (!strcmp(value, "off"))
        _output->setResponseHeader(RESPONSE_HEADER_OFF);
    else if (!strcmp(value, "fixed16"))
        _output->setResponseHeader(RESPONSE_HEADER_FIXED16);
    else
        _output->setError(RESPONSE_CODE_INVALID_HEADER,
                "Invalid value '%s' for ResponseHeader: must be 'off' or 'fixed16'", value);
}

void Query::parseLimitLine(char *line)
{
    char *value = next_field(&line);
    if (!value) {
        _output->setError(RESPONSE_CODE_INVALID_HEADER, "Header Limit: missing value");
    }
    else {
        int limit = atoi(value);
        if (!isdigit(value[0]) || limit < 0)
            _output->setError(RESPONSE_CODE_INVALID_HEADER,
                    "Invalid value for Limit: must be non-negative integer");
        else
            _limit = limit;
    }
}

void Query::parseWaitTimeoutLine(char *line)
{
    char *value = next_field(&line);
    if (!value) {
        _output->setError(RESPONSE_CODE_INVALID_HEADER, "WaitTimeout: missing value");
    }
    else {
        int timeout = atoi(value);
        if (!isdigit(value[0]) || timeout < 0)
            _output->setError(RESPONSE_CODE_INVALID_HEADER,
                    "Invalid value for WaitTimeout: must be non-negative integer");
        else
            _wait_timeout = timeout;
    }
}

void Query::parseWaitTriggerLine(char *line)
{
    char *value = next_field(&line);
    if (!value) {
        _output->setError(RESPONSE_CODE_INVALID_HEADER, "WaitTrigger: missing keyword");
        return;
    }

    for (unsigned i=0; i < WT_NUM_TRIGGERS; i++)
    {
        if (!strcmp(value, wt_names[i])) {
            _wait_trigger = i;
            return;
        }
    }
    _output->setError(RESPONSE_CODE_INVALID_HEADER,
            "WaitTrigger: invalid trigger '%s'. Allowed are %s.", value, WT_ALLNAMES);
}

void Query::parseWaitObjectLine(char *line)
{
    if (!_table)
        return;

    char *objectspec = lstrip(line);
    _wait_object = _table->findObject(objectspec);
    if (!_wait_object) {
        _output->setError(RESPONSE_CODE_INVALID_HEADER,
                "WaitObject: object '%s' not found or not supported by this table", objectspec);
    }
}

void Query::parseLocaltimeLine(char *line)
{
    char *value = next_field(&line);
    if (!value) {
        _output->setError(RESPONSE_CODE_INVALID_HEADER, "Header Localtime: missing value");
        return;
    }
    time_t their_time = atoi(value);
    time_t our_time = time(0);

    // compute offset to be *added* each time we output our time and
    // *substracted* from reference value by filter headers
    int dif = their_time - our_time;

    // Round difference to half hour. We assume, that both clocks are more
    // or less synchronized and that the time offset is only due to being
    // in different time zones.
    int full = dif / 1800;
    int rem  = dif % 1800;
    if (rem <= -900)
        full --;
    else if (rem >= 900)
        full ++;
    if (full >= 48 || full <= -48) {
        _output->setError(RESPONSE_CODE_INVALID_HEADER,
                "Invalid Localtime header: timezone difference greater then 24 hours");
        return;
    }
    _timezone_offset = full * 1800;
    if (g_debug_level >= 2) {
        logger(LG_INFO, "Timezone difference is %.1f hours", _timezone_offset / 3600.0);
    }
}


bool Query::doStats()
{
    return _stats_columns.size() > 0;
}


void Query::start()
{
    doWait();

    _need_ds_separator = false;

    if (_output_format != OUTPUT_FORMAT_CSV)
        _output->addChar('[');

    if (doStats())
    {
        // if we have no StatsGroupBy: column, we allocate one only row of Aggregators,
        // directly in _stats_aggregators. When grouping the rows of aggregators
        // will be created each time a new group is found.
        if (_columns.size() == 0)
        {
            _stats_aggregators = new Aggregator *[_stats_columns.size()];
            for (unsigned i=0; i<_stats_columns.size(); i++)
                _stats_aggregators[i] = _stats_columns[i]->createAggregator();
        }
    }

    if (_show_column_headers)
    {
        outputDatasetBegin();
        bool first = true;

        for (_columns_t::iterator it = _columns.begin();
                it != _columns.end();
                ++it)
        {
            if (first)
                first = false;
            else
                outputFieldSeparator();
            Column *column = *it;
            outputString(column->name());
        }

        // Output dummy headers for stats columns
        int col = 1;
        char colheader[32];
        for (_stats_columns_t::iterator it = _stats_columns.begin();
                it != _stats_columns.end();
                ++it)
        {
            if (first)
                first = false;
            else
                outputFieldSeparator();
            snprintf(colheader, 32, "stats_%d", col);
            outputString(colheader);
            col ++;
        }

        outputDatasetEnd();
        _need_ds_separator = true;
    }
}


bool Query::processDataset(void *data)
{
    if (_output->size() > g_max_response_size) {
        logger(LG_INFO, "Maximum response size of %d bytes exceeded!", g_max_response_size);
        // _output->setError(RESPONSE_CODE_LIMIT_EXCEEDED, "Maximum response size of %d reached", g_max_response_size);
        // currently we only log an error into the log file and do
        // not abort the query. We handle it like Limit:
        return false;
    }

    if (_filter.accepts(data) && (!_auth_user || _table->isAuthorized(_auth_user, data))) {
        _current_line++;
        if (_limit >= 0 && (int)_current_line > _limit)
            return false;

        if (doStats())
        {
            Aggregator **aggr;
            // When doing grouped stats, we need to fetch/create a row
            // of aggregators for the current group
            if (_columns.size() > 0) {
                _stats_group_spec_t groupspec;
                computeStatsGroupSpec(groupspec, data);
                aggr = getStatsGroup(groupspec);
            }
            else
                aggr = _stats_aggregators;

            for (unsigned i=0; i<_stats_columns.size(); i++)
                aggr[i]->consume(data, this);

            // No output is done while processing the data, we only
            // collect stats.
        }
        else
        {
            // output data of current row
            if (_need_ds_separator && _output_format != OUTPUT_FORMAT_CSV)
                _output->addBuffer(",\n", 2);
            else
                _need_ds_separator = true;

            outputDatasetBegin();
            for (_columns_t::iterator it = _columns.begin();
                    it != _columns.end();
                    ++it)
            {
                if (it != _columns.begin())
                    outputFieldSeparator();
                Column *column = *it;
                column->output(data, this);
            }
            outputDatasetEnd();
        }
    }
    return true;
}

void Query::finish()
{
    // grouped stats
    if (doStats() && _columns.size() > 0)
    {
        // output values of all stats groups (output has been post poned until now)
        for (_stats_groups_t::iterator it = _stats_groups.begin();
                it != _stats_groups.end();
                ++it)
        {
            // dataset separator after first group
            if (it != _stats_groups.begin() && _output_format != OUTPUT_FORMAT_CSV)
                _output->addBuffer(",\n", 2);

            outputDatasetBegin();

            // output group columns first
            _stats_group_spec_t groupspec = it->first;
            bool first = true;
            for (_stats_group_spec_t::iterator iit = groupspec.begin();
                    iit != groupspec.end();
                    ++iit)
            {
                if (!first)
                    outputFieldSeparator();
                else
                    first = false;
                outputString((*iit).c_str());
            }

            Aggregator **aggr = it->second;
            for (unsigned i=0; i<_stats_columns.size(); i++) {
                outputFieldSeparator();
                aggr[i]->output(this);
                delete aggr[i]; // not needed any more
            }
            outputDatasetEnd();
            delete aggr;
        }
    }

    // stats without group column
    else if (doStats()) {
        outputDatasetBegin();
        for (unsigned i=0; i<_stats_columns.size(); i++)
        {
            if (i > 0)
                outputFieldSeparator();
            _stats_aggregators[i]->output(this);
            delete _stats_aggregators[i];
        }
        outputDatasetEnd();
        delete _stats_aggregators;
    }

    // normal query
    if (_output_format != OUTPUT_FORMAT_CSV)
        _output->addBuffer("]\n", 2);
}


void *Query::findIndexFilter(const char *columnname)
{
    return _filter.findIndexFilter(columnname);
}

void Query::findIntLimits(const char *columnname, int *lower, int *upper)
{
    return _filter.findIntLimits(columnname, lower, upper);
}

void Query::optimizeBitmask(const char *columnname, uint32_t *bitmask)
{
    _filter.optimizeBitmask(columnname, bitmask);
}

// output helpers, called from columns
void Query::outputDatasetBegin()
{
    if (_output_format != OUTPUT_FORMAT_CSV)
        _output->addChar('[');
}

void Query::outputDatasetEnd()
{
    if (_output_format == OUTPUT_FORMAT_CSV)
        _output->addBuffer(_dataset_separator.c_str(), _dataset_separator.size());
    else
        _output->addChar(']');
}

void Query::outputFieldSeparator()
{
    if (_output_format == OUTPUT_FORMAT_CSV)
        _output->addBuffer(_field_separator.c_str(), _field_separator.size());
    else
        _output->addChar(',');
}

void Query::outputInteger(int32_t value)
{
    char buf[32];
    int l = snprintf(buf, 32, "%d", value);
    _output->addBuffer(buf, l);
}

void Query::outputInteger64(int64_t value)
{
    char buf[32];
    int l = snprintf(buf, 32, "%lld", (long long int )value);
    _output->addBuffer(buf, l);
}

void Query::outputTime(int32_t value)
{
    value += _timezone_offset;
    outputInteger(value);
}


void Query::outputUnsignedLong(unsigned long value)
{
    char buf[64];
    int l = snprintf(buf, sizeof(buf), "%lu", value);
    _output->addBuffer(buf, l);
}

void Query::outputCounter(counter_t value)
{
    char buf[64];
    int l = snprintf(buf, sizeof(buf), "%llu", (unsigned long long)value);
    _output->addBuffer(buf, l);
}

void Query::outputDouble(double value)
{
    char buf[64];
    int l = snprintf(buf, sizeof(buf), "%.10e", value);
    _output->addBuffer(buf, l);
}

void Query::outputUnicodeEscape(unsigned value)
{
    char buf[8];
    snprintf(buf, sizeof(buf), "\\u%04x", value);
    _output->addBuffer(buf, 6);
}

void Query::outputHostService(const char *host_name, const char *service_description)
{
    if (_output_format == OUTPUT_FORMAT_CSV) {
        outputString(host_name);
        _output->addBuffer(_host_service_separator.c_str(), _host_service_separator.size());
        outputString(service_description);
    }
    else {
        _output->addChar('[');
        outputString(host_name);
        _output->addChar(',');
        outputString(service_description);
        _output->addChar(']');
    }
}

void Query::outputString(const char *value)
{
    if (!value) {
        if (_output_format != OUTPUT_FORMAT_CSV)
            _output->addBuffer("\"\"", 2);
        return;
    }

    else if (_output_format == OUTPUT_FORMAT_CSV)
        _output->addString(value);

    else // JSON
    {
        if (_output_format == OUTPUT_FORMAT_PYTHON)
            _output->addChar('u'); // mark strings as unicode
        _output->addChar('"');
        const char *r = value;
        int chars_left = strlen(r);
        while (*r) {
            // Always escape control characters (1..31)
            if (*r < 32 && *r >= 0)
                outputUnicodeEscape((unsigned)*r);

            // Output ASCII characters unencoded
            else if (*r >= 32) {
                if (*r == '"' || *r == '\\')
                    _output->addChar('\\');
                _output->addChar(*r);
            }

            // interprete two-Byte UTF-8 sequences in mode 'utf8' and 'mixed'
            else if ((g_data_encoding == ENCODING_UTF8 || g_data_encoding == ENCODING_MIXED)
                    && ((*r & 0xE0) == 0xC0)) {
                outputUnicodeEscape(((*r & 31) << 6) | (*(r+1) & 0x3F)); // 2 byte encoding
                r++;
                chars_left--;
            }

            // interprete 3/4-Byte UTF-8 sequences only in mode 'utf8'
            else if (g_data_encoding == ENCODING_UTF8) {
                // three-byte sequences (avoid buffer overflow!)
                if ((*r & 0xF0) == 0xE0) {
                    if (chars_left < 3) {
                        if (g_debug_level >= 2)
                            logger(LG_INFO, "Ignoring invalid UTF-8 sequence in string '%s'", value);
                        break; // end of string. No use in continuing
                    }
                    else {
                        outputUnicodeEscape(
                                ((*r     & 0x0F) << 12 |
                                 (*(r+1) & 0x3F) <<  6 |
                                 (*(r+2) & 0x3F)));
                        r += 2;
                        chars_left -= 2;
                    }
                }
                // four-byte sequences
                else if ((*r & 0xF8) == 0xF0) {
                    if (chars_left < 4) {
                        if (g_debug_level >= 2)
                            logger(LG_INFO, "Ignoring invalid UTF-8 sequence in string '%s'", value);
                        break; // end of string. No use in continuing
                    }
                    else {
                        outputUnicodeEscape(
                                ((*r     & 0x07) << 18 |
                                 (*(r+1) & 0x3F) <<  6 |
                                 (*(r+2) & 0x3F) <<  6 |
                                 (*(r+3) & 0x3F)));
                        r += 3;
                        chars_left -= 3;
                    }
                }
                else {
                    if (g_debug_level >= 2)
                        logger(LG_INFO, "Ignoring invalid UTF-8 sequence in string '%s'", value);
                }
            }

            // in latin1 and mixed mode interprete all other non-ASCII characters as latin1
            else {
                outputUnicodeEscape((unsigned)((int)*r + 256)); // assume latin1 encoding
            }

            r++;
            chars_left--;
        }
        _output->addChar('"');
    }
}

void Query::outputBeginList()
{
    if (_output_format != OUTPUT_FORMAT_CSV)
        _output->addChar('[');
}

void Query::outputListSeparator()
{
    if (_output_format == OUTPUT_FORMAT_CSV)
        _output->addBuffer(_list_separator.c_str(), _list_separator.size());
    else
        _output->addChar(',');
}

void Query::outputEndList()
{
    if (_output_format != OUTPUT_FORMAT_CSV)
        _output->addChar(']');
}

void Query::outputBeginSublist()
{
    if (_output_format != OUTPUT_FORMAT_CSV)
        _output->addChar('[');
}

void Query::outputSublistSeparator()
{
    if (_output_format == OUTPUT_FORMAT_CSV)
        _output->addBuffer(_host_service_separator.c_str(), _host_service_separator.size());
    else
        _output->addChar(',');
}

void Query::outputEndSublist()
{
    if (_output_format != OUTPUT_FORMAT_CSV)
        _output->addChar(']');
}

void Query::outputBeginDict()
{
    if (_output_format != OUTPUT_FORMAT_CSV)
        _output->addChar('{');
}

void Query::outputDictSeparator()
{
    outputListSeparator();
}

void Query::outputDictValueSeparator()
{
    if (_output_format == OUTPUT_FORMAT_CSV)
        _output->addBuffer(_host_service_separator.c_str(), _host_service_separator.size());
    else
        _output->addChar(':');
}

void Query::outputEndDict()
{
    if (_output_format != OUTPUT_FORMAT_CSV)
        _output->addChar('}');
}


Aggregator **Query::getStatsGroup(Query::_stats_group_spec_t &groupspec)
{
    _stats_groups_t::iterator it = _stats_groups.find(groupspec);
    if (it == _stats_groups.end()) {
        Aggregator **aggr = new Aggregator *[_stats_columns.size()];
        for (unsigned i=0; i<_stats_columns.size(); i++)
            aggr[i] = _stats_columns[i]->createAggregator();
        _stats_groups.insert(make_pair(groupspec, aggr));
        return aggr;
    }
    else
        return it->second;
}

void Query::computeStatsGroupSpec(Query::_stats_group_spec_t &groupspec, void *data)
{
    for (_columns_t::iterator it = _columns.begin();
            it != _columns.end();
            ++it)
    {
        Column *column = *it;
        groupspec.push_back(column->valueAsString(data, this));
    }
}


void Query::doWait()
{
    // If no wait condition and no trigger is set,
    // we do not wait at all.
    if (_wait_condition.numFilters() == 0 && _wait_trigger == WT_NONE)
        return;

    // If a condition is set, we check the condition. If it
    // is already true, we do not need to way
    if (_wait_condition.numFilters() > 0 &&
            _wait_condition.accepts(_wait_object))
    {
        if (g_debug_level >= 2)
            logger(LG_INFO, "Wait condition true, no waiting neccessary");
        return;
    }

    // No wait on specified trigger. If no trigger was specified
    // we use WT_ALL as default trigger.
    if (_wait_trigger == WT_NONE)
        _wait_trigger = WT_ALL;

    struct timeval now;
    gettimeofday(&now, NULL);
    struct timespec timeout;
    timeout.tv_sec = now.tv_sec + (_wait_timeout / 1000);
    timeout.tv_nsec = now.tv_usec * 1000 + 1000 * 1000 * (_wait_timeout % 1000);
    if (timeout.tv_nsec > 1000000000) {
        timeout.tv_sec ++;
        timeout.tv_nsec -= 1000000000;
    }

    do {
        if (_wait_timeout == 0) {
            if (g_debug_level >= 2)
                logger(LG_INFO, "Waiting unlimited until condition becomes true");
            pthread_mutex_lock(&g_wait_mutex);
            pthread_cond_wait(&g_wait_cond[_wait_trigger], &g_wait_mutex);
            pthread_mutex_unlock(&g_wait_mutex);
        }
        else {
            if (g_debug_level >= 2)
                logger(LG_INFO, "Waiting %d ms or until condition becomes true", _wait_timeout);
            pthread_mutex_lock(&g_wait_mutex);
            int ret = pthread_cond_timedwait(&g_wait_cond[_wait_trigger], &g_wait_mutex, &timeout);
            pthread_mutex_unlock(&g_wait_mutex);
            if (ret == ETIMEDOUT) {
                if (g_debug_level >= 2)
                    logger(LG_INFO, "WaitTimeout after %d ms", _wait_timeout);
                return; // timeout occurred. do not wait any longer
            }
        }
    } while (!_wait_condition.accepts(_wait_object));
}


