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
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#include "Query.h"
#include <ctype.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/time.h>
#include <syslog.h>
#include <utility>
#include <vector>
#include "Aggregator.h"
#include "Column.h"
#include "Filter.h"
#include "NegatingFilter.h"
#include "NullColumn.h"
#include "OringFilter.h"
#include "OutputBuffer.h"
#include "StatsColumn.h"
#include "Table.h"
#include "auth.h"
#include "data_encoding.h"
#include "logger.h"
#include "opids.h"
#include "strutil.h"
#include "waittriggers.h"

extern int g_debug_level;
extern unsigned long g_max_response_size;
extern int g_data_encoding;

using std::list;
using std::string;
using std::vector;

Query::Query(const list<string> &lines, OutputBuffer *output, Table *table)
    : _output(output)
    , _table(table)
    , _auth_user(nullptr)
    , _wait_timeout(0)
    , _wait_trigger(nullptr)
    , _wait_object(nullptr)
    , _field_separator(";")
    , _dataset_separator("\n")
    , _list_separator(",")
    , _host_service_separator("|")
    , _show_column_headers(true)
    , _need_ds_separator(false)
    , _output_format(OUTPUT_FORMAT_CSV)
    , _limit(-1)
    , _time_limit(-1)
    , _time_limit_timeout(0)
    , _current_line(0)
    , _timezone_offset(0) {
    for (auto &line : lines) {
        vector<char> line_copy(line.begin(), line.end());
        line_copy.push_back('\0');
        char *buffer = &line_copy[0];
        rstrip(buffer);
        if (g_debug_level > 0) {
            logger(LG_INFO, "Query: %s", buffer);
        }
        if (strncmp(buffer, "Filter:", 7) == 0) {
            parseFilterLine(lstrip(buffer + 7), true);

        } else if (strncmp(buffer, "Or:", 3) == 0) {
            parseAndOrLine(lstrip(buffer + 3), ANDOR_OR, true);

        } else if (strncmp(buffer, "And:", 4) == 0) {
            parseAndOrLine(lstrip(buffer + 4), ANDOR_AND, true);

        } else if (strncmp(buffer, "Negate:", 7) == 0) {
            parseNegateLine(lstrip(buffer + 7), true);

        } else if (strncmp(buffer, "StatsOr:", 8) == 0) {
            parseStatsAndOrLine(lstrip(buffer + 8), ANDOR_OR);

        } else if (strncmp(buffer, "StatsAnd:", 9) == 0) {
            parseStatsAndOrLine(lstrip(buffer + 9), ANDOR_AND);

        } else if (strncmp(buffer, "StatsNegate:", 12) == 0) {
            parseStatsNegateLine(lstrip(buffer + 12));

        } else if (strncmp(buffer, "Stats:", 6) == 0) {
            parseStatsLine(lstrip(buffer + 6));

        } else if (strncmp(buffer, "StatsGroupBy:", 13) == 0) {
            parseStatsGroupLine(lstrip(buffer + 13));

        } else if (strncmp(buffer, "Columns:", 8) == 0) {
            parseColumnsLine(lstrip(buffer + 8));

        } else if (strncmp(buffer, "ColumnHeaders:", 14) == 0) {
            parseColumnHeadersLine(lstrip(buffer + 14));

        } else if (strncmp(buffer, "Limit:", 6) == 0) {
            parseLimitLine(lstrip(buffer + 6));

        } else if (strncmp(buffer, "Timelimit:", 10) == 0) {
            parseTimelimitLine(lstrip(buffer + 10));

        } else if (strncmp(buffer, "AuthUser:", 9) == 0) {
            parseAuthUserHeader(lstrip(buffer + 9));

        } else if (strncmp(buffer, "Separators:", 11) == 0) {
            parseSeparatorsLine(lstrip(buffer + 11));

        } else if (strncmp(buffer, "OutputFormat:", 13) == 0) {
            parseOutputFormatLine(lstrip(buffer + 13));

        } else if (strncmp(buffer, "ResponseHeader:", 15) == 0) {
            parseResponseHeaderLine(lstrip(buffer + 15));

        } else if (strncmp(buffer, "KeepAlive:", 10) == 0) {
            parseKeepAliveLine(lstrip(buffer + 10));

        } else if (strncmp(buffer, "WaitCondition:", 14) == 0) {
            parseFilterLine(lstrip(buffer + 14), false);

        } else if (strncmp(buffer, "WaitConditionAnd:", 17) == 0) {
            parseAndOrLine(lstrip(buffer + 17), ANDOR_AND, false);

        } else if (strncmp(buffer, "WaitConditionOr:", 16) == 0) {
            parseAndOrLine(lstrip(buffer + 16), ANDOR_OR, false);

        } else if (strncmp(buffer, "WaitConditionNegate:", 20) == 0) {
            parseNegateLine(lstrip(buffer + 20), false);

        } else if (strncmp(buffer, "WaitTrigger:", 12) == 0) {
            parseWaitTriggerLine(lstrip(buffer + 12));

        } else if (strncmp(buffer, "WaitObject:", 11) == 0) {
            parseWaitObjectLine(lstrip(buffer + 11));

        } else if (strncmp(buffer, "WaitTimeout:", 12) == 0) {
            parseWaitTimeoutLine(lstrip(buffer + 12));

        } else if (strncmp(buffer, "Localtime:", 10) == 0) {
            parseLocaltimeLine(lstrip(buffer + 10));

        } else if (buffer[0] == 0) {
            break;

        } else {
            output->setError(RESPONSE_CODE_INVALID_HEADER,
                             "Undefined request header '%s'", buffer);
            break;
        }
    }
}

Query::~Query() {
    // delete dynamic columns
    for (auto column : _columns) {
        if (column->mustDelete()) {
            delete column;
        }
    }

    for (auto &dummy_column : _dummy_columns) {
        delete dummy_column;
    }
    for (auto &stats_column : _stats_columns) {
        delete stats_column;
    }
}

Column *Query::createDummyColumn(const char *name) {
    Column *col = new NullColumn(name, "Non existing column");
    _dummy_columns.push_back(col);
    return col;
}

void Query::addColumn(Column *column) { _columns.push_back(column); }

void Query::setError(int error_code, const char *msg) {
    _output->setError(error_code, msg);
}

bool Query::hasNoColumns() { return _columns.empty() && !doStats(); }

int Query::lookupOperator(const char *opname) {
    int opid;
    int negate = 1;
    if (opname[0] == '!') {
        negate = -1;
        opname++;
    }

    if (strcmp(opname, "=") == 0) {
        opid = OP_EQUAL;
    } else if (strcmp(opname, "~") == 0) {
        opid = OP_REGEX;
    } else if (strcmp(opname, "=~") == 0) {
        opid = OP_EQUAL_ICASE;
    } else if (strcmp(opname, "~~") == 0) {
        opid = OP_REGEX_ICASE;
    } else if (strcmp(opname, ">") == 0) {
        opid = OP_GREATER;
    } else if (strcmp(opname, "<") == 0) {
        opid = OP_LESS;
    } else if (strcmp(opname, ">=") == 0) {
        opid = OP_LESS;
        negate = -negate;
    } else if (strcmp(opname, "<=") == 0) {
        opid = OP_GREATER;
        negate = -negate;
    } else {
        opid = OP_INVALID;
    }
    return negate * opid;
}

Filter *Query::createFilter(Column *column, int operator_id, char *value) {
    Filter *filter = column->createFilter(operator_id, value);
    if (filter == nullptr) {
        _output->setError(RESPONSE_CODE_INVALID_HEADER,
                          "cannot create filter on table %s", _table->name());
    } else if (filter->hasError()) {
        _output->setError(filter->errorCode(), "error in Filter header: %s",
                          filter->errorMessage().c_str());
        delete filter;
        filter = nullptr;
    } else {
        filter->setQuery(this);
        filter->setColumn(column);
    }
    return filter;
}

void Query::parseAndOrLine(char *line, int andor, bool filter) {
    char *value = next_field(&line);
    if (value == nullptr) {
        _output->setError(
            RESPONSE_CODE_INVALID_HEADER,
            "Missing value for %s%s: need non-zero integer number",
            filter ? "" : "WaitCondition", andor == ANDOR_OR ? "Or" : "And");
        return;
    }

    int number = atoi(value);
    if ((isdigit(value[0]) == 0) || number <= 0) {
        _output->setError(
            RESPONSE_CODE_INVALID_HEADER,
            "Invalid value for %s%s: need non-zero integer number",
            filter ? "" : "WaitCondition", andor == ANDOR_OR ? "Or" : "And");
        return;
    }
    if (filter) {
        _filter.combineFilters(number, andor);
    } else {
        _wait_condition.combineFilters(number, andor);
    }
}

void Query::parseNegateLine(char *line, bool filter) {
    if (next_field(&line) != nullptr) {
        _output->setError(
            RESPONSE_CODE_INVALID_HEADER,
            filter ? "Negate: does not take any arguments"
                   : "WaitConditionNegate: does not take any arguments");
        return;
    }

    Filter *to_negate;
    if (filter) {
        to_negate = _filter.stealLastSubfiler();
        if (to_negate == nullptr) {
            _output->setError(RESPONSE_CODE_INVALID_HEADER,
                              "Negate: no Filter: header to negate");
            return;
        }
    } else {
        to_negate = _wait_condition.stealLastSubfiler();
        if (to_negate == nullptr) {
            _output->setError(RESPONSE_CODE_INVALID_HEADER,
                              "Negate: no Wait:-condition negate");
            return;
        }
    }
    Filter *negated = new NegatingFilter(to_negate);
    if (filter) {
        _filter.addSubfilter(negated);
    } else {
        _wait_condition.addSubfilter(negated);
    }
}

void Query::parseStatsAndOrLine(char *line, int andor) {
    char *value = next_field(&line);
    if (value == nullptr) {
        _output->setError(
            RESPONSE_CODE_INVALID_HEADER,
            "Missing value for Stats%s: need non-zero integer number",
            andor == ANDOR_OR ? "Or" : "And");
        return;
    }

    int number = atoi(value);
    if ((isdigit(value[0]) == 0) || number <= 0) {
        _output->setError(
            RESPONSE_CODE_INVALID_HEADER,
            "Invalid value for Stats%s: need non-zero integer number",
            andor == ANDOR_OR ? "Or" : "And");
        return;
    }

    // The last 'number' StatsColumns must be of type STATS_OP_COUNT
    AndingFilter *anding =
        (andor == ANDOR_OR) ? new OringFilter() : new AndingFilter();
    while (number > 0) {
        if (_stats_columns.empty()) {
            _output->setError(
                RESPONSE_CODE_INVALID_HEADER,
                "Invalid count for Stats%s: too few Stats: headers available",
                andor == ANDOR_OR ? "Or" : "And");
            delete anding;
            return;
        }

        StatsColumn *col = _stats_columns.back();
        if (col->operation() != STATS_OP_COUNT) {
            _output->setError(
                RESPONSE_CODE_INVALID_HEADER,
                "Can use Stats%s only on Stats: headers of filter type",
                andor == ANDOR_OR ? "Or" : "And");
            delete anding;
            return;
        }
        anding->addSubfilter(col->stealFilter());
        delete col;
        _stats_columns.pop_back();
        number--;
    }
    _stats_columns.push_back(new StatsColumn(nullptr, anding, STATS_OP_COUNT));
}

void Query::parseStatsNegateLine(char *line) {
    if (next_field(&line) != nullptr) {
        _output->setError(RESPONSE_CODE_INVALID_HEADER,
                          "StatsNegate: does not take any arguments");
        return;
    }
    if (_stats_columns.empty()) {
        _output->setError(RESPONSE_CODE_INVALID_HEADER,
                          "StatsNegate: no Stats: headers available");
        return;
    }
    StatsColumn *col = _stats_columns.back();
    if (col->operation() != STATS_OP_COUNT) {
        _output->setError(
            RESPONSE_CODE_INVALID_HEADER,
            "Can use StatsNegate only on Stats: headers of filter type");
        return;
    }
    auto negated = new NegatingFilter(col->stealFilter());
    delete col;
    _stats_columns.pop_back();
    _stats_columns.push_back(new StatsColumn(nullptr, negated, STATS_OP_COUNT));
}

void Query::parseStatsLine(char *line) {
    if (_table == nullptr) {
        return;
    }

    // first token is either aggregation operator or column name
    char *col_or_op = next_field(&line);
    if (col_or_op == nullptr) {
        _output->setError(RESPONSE_CODE_INVALID_HEADER, "empty stats line");
        return;
    }

    int operation = STATS_OP_COUNT;
    if (strcmp(col_or_op, "sum") == 0) {
        operation = STATS_OP_SUM;
    } else if (strcmp(col_or_op, "min") == 0) {
        operation = STATS_OP_MIN;
    } else if (strcmp(col_or_op, "max") == 0) {
        operation = STATS_OP_MAX;
    } else if (strcmp(col_or_op, "avg") == 0) {
        operation = STATS_OP_AVG;
    } else if (strcmp(col_or_op, "std") == 0) {
        operation = STATS_OP_STD;
    } else if (strcmp(col_or_op, "suminv") == 0) {
        operation = STATS_OP_SUMINV;
    } else if (strcmp(col_or_op, "avginv") == 0) {
        operation = STATS_OP_AVGINV;
    }

    char *column_name;
    if (operation == STATS_OP_COUNT) {
        column_name = col_or_op;
    } else {
        // aggregation operator is followed by column name
        column_name = next_field(&line);
        if (column_name == nullptr) {
            _output->setError(RESPONSE_CODE_INVALID_HEADER,
                              "missing column name in stats header");
            return;
        }
    }

    Column *column = _table->column(column_name);
    if (column == nullptr) {
        _output->setError(RESPONSE_CODE_INVALID_HEADER,
                          "invalid stats header: table '%s' has no column '%s'",
                          _table->name(), column_name);
        return;
    }

    StatsColumn *stats_col;
    if (operation == STATS_OP_COUNT) {
        char *operator_name = next_field(&line);
        if (operator_name == nullptr) {
            _output->setError(
                RESPONSE_CODE_INVALID_HEADER,
                "invalid stats header: missing operator after table '%s'",
                column_name);
            return;
        }
        int operator_id = lookupOperator(operator_name);
        if (operator_id == OP_INVALID) {
            _output->setError(RESPONSE_CODE_INVALID_HEADER,
                              "invalid stats operator '%s'", operator_name);
            return;
        }
        char *value = lstrip(line);
        if (value == nullptr) {
            _output->setError(
                RESPONSE_CODE_INVALID_HEADER,
                "invalid stats: missing value after operator '%s'",
                operator_name);
            return;
        }

        Filter *filter = createFilter(column, operator_id, value);
        if (filter == nullptr) {
            return;
        }
        stats_col = new StatsColumn(column, filter, operation);
    } else {
        stats_col = new StatsColumn(column, nullptr, operation);
    }
    _stats_columns.push_back(stats_col);

    /* Default to old behaviour: do not output column headers if we
       do Stats queries */
    _show_column_headers = false;
}

void Query::parseFilterLine(char *line, bool is_filter) {
    if (_table == nullptr) {
        return;
    }

    char *column_name = next_field(&line);
    if (column_name == nullptr) {
        _output->setError(RESPONSE_CODE_INVALID_HEADER, "empty filter line");
        return;
    }

    Column *column = _table->column(column_name);
    if (column == nullptr) {
        _output->setError(RESPONSE_CODE_INVALID_HEADER,
                          "invalid filter: table '%s' has no column '%s'",
                          _table->name(), column_name);
        return;
    }

    char *operator_name = next_field(&line);
    if (operator_name == nullptr) {
        _output->setError(
            RESPONSE_CODE_INVALID_HEADER,
            "invalid filter header: missing operator after table '%s'",
            column_name);
        return;
    }
    int operator_id = lookupOperator(operator_name);
    if (operator_id == OP_INVALID) {
        _output->setError(RESPONSE_CODE_INVALID_HEADER,
                          "invalid filter operator '%s'", operator_name);
        return;
    }
    char *value = lstrip(line);
    if (value == nullptr) {
        _output->setError(RESPONSE_CODE_INVALID_HEADER,
                          "invalid filter: missing value after operator '%s'",
                          operator_name);
        return;
    }

    Filter *filter = createFilter(column, operator_id, value);
    if (filter != nullptr) {
        if (is_filter) {
            _filter.addSubfilter(filter);
        } else {
            _wait_condition.addSubfilter(filter);
        }
    }
}

void Query::parseAuthUserHeader(char *line) {
    if (_table == nullptr) {
        return;
    }
    _auth_user = find_contact(line);
    if (_auth_user == nullptr) {
        // Do not handle this as error any more. In a multi site setup
        // not all users might be present on all sites by design.
        _auth_user = UNKNOWN_AUTH_USER;
        // _output->setError(RESPONSE_CODE_UNAUTHORIZED, "AuthUser: no such user
        // '%s'", line);
    }
}

void Query::parseStatsGroupLine(char *line) {
    logger(LOG_WARNING,
           "Warning: StatsGroupBy is deprecated. "
           "Please use Columns instead.");
    parseColumnsLine(line);
}

void Query::parseColumnsLine(char *line) {
    if (_table == nullptr) {
        return;
    }
    char *column_name;
    while (nullptr != (column_name = next_field(&line))) {
        Column *column = _table->column(column_name);
        if (column != nullptr) {
            _columns.push_back(column);
        } else {
            logger(LOG_WARNING,
                   "Replacing non-existing column '%s' with null column",
                   column_name);
            // Do not fail any longer. We might want to make this configurable.
            // But not failing has the advantage that an updated GUI, that
            // expects new columns,
            // will be able to keep compatibility with older Livestatus
            // versions.
            // _output->setError(RESPONSE_CODE_INVALID_HEADER,
            //       "Table '%s' has no column '%s'", _table->name(),
            //       column_name);
            Column *col = createDummyColumn(column_name);
            _columns.push_back(col);
        }
    }
    _show_column_headers = false;
}

void Query::parseSeparatorsLine(char *line) {
    char dssep = 0, fieldsep = 0, listsep = 0, hssep = 0;
    char *token = next_field(&line);
    if (token != nullptr) {
        dssep = atoi(token);
    }
    token = next_field(&line);
    if (token != nullptr) {
        fieldsep = atoi(token);
    }
    token = next_field(&line);
    if (token != nullptr) {
        listsep = atoi(token);
    }
    token = next_field(&line);
    if (token != nullptr) {
        hssep = atoi(token);
    }

    // if (dssep == fieldsep
    //       || dssep == listsep
    //       || fieldsep == listsep
    //       || dssep == hssep
    //       || fieldsep == hssep
    //       || listsep == hssep)
    // {
    //    _output->setError(RESPONSE_CODE_INVALID_HEADER, "invalid Separators:
    //    need four different integers");
    //    return;
    // }
    _dataset_separator = string(&dssep, 1);
    _field_separator = string(&fieldsep, 1);
    _list_separator = string(&listsep, 1);
    _host_service_separator = string(&hssep, 1);
}

void Query::parseOutputFormatLine(char *line) {
    char *format = next_field(&line);
    if (format == nullptr) {
        _output->setError(
            RESPONSE_CODE_INVALID_HEADER,
            "Missing output format. Only 'csv' and 'json' are available.");
        return;
    }

    if (strcmp(format, "csv") == 0) {
        _output_format = OUTPUT_FORMAT_CSV;
    } else if (strcmp(format, "json") == 0) {
        _output_format = OUTPUT_FORMAT_JSON;
    } else if (strcmp(format, "python") == 0) {
        _output_format = OUTPUT_FORMAT_PYTHON;
    } else {
        _output->setError(
            RESPONSE_CODE_INVALID_HEADER,
            "Invalid output format. Only 'csv' and 'json' are available.");
    }
}

void Query::parseColumnHeadersLine(char *line) {
    char *value = next_field(&line);
    if (value == nullptr) {
        _output->setError(
            RESPONSE_CODE_INVALID_HEADER,
            "Missing value for ColumnHeaders: must be 'on' or 'off'");
        return;
    }

    if (strcmp(value, "on") == 0) {
        _show_column_headers = true;
    } else if (strcmp(value, "off") == 0) {
        _show_column_headers = false;
    } else {
        _output->setError(
            RESPONSE_CODE_INVALID_HEADER,
            "Invalid value for ColumnHeaders: must be 'on' or 'off'");
    }
}

void Query::parseKeepAliveLine(char *line) {
    char *value = next_field(&line);
    if (value == nullptr) {
        _output->setError(RESPONSE_CODE_INVALID_HEADER,
                          "Missing value for KeepAlive: must be 'on' or 'off'");
        return;
    }

    if (strcmp(value, "on") == 0) {
        _output->setDoKeepalive(true);
    } else if (strcmp(value, "off") == 0) {
        _output->setDoKeepalive(false);
    } else {
        _output->setError(RESPONSE_CODE_INVALID_HEADER,
                          "Invalid value for KeepAlive: must be 'on' or 'off'");
    }
}

void Query::parseResponseHeaderLine(char *line) {
    char *value = next_field(&line);
    if (value == nullptr) {
        _output->setError(
            RESPONSE_CODE_INVALID_HEADER,
            "Missing value for ResponseHeader: must be 'off' or 'fixed16'");
        return;
    }

    if (strcmp(value, "off") == 0) {
        _output->setResponseHeader(RESPONSE_HEADER_OFF);
    } else if (strcmp(value, "fixed16") == 0) {
        _output->setResponseHeader(RESPONSE_HEADER_FIXED16);
    } else {
        _output->setError(
            RESPONSE_CODE_INVALID_HEADER,
            "Invalid value '%s' for ResponseHeader: must be 'off' or 'fixed16'",
            value);
    }
}

void Query::parseLimitLine(char *line) {
    char *value = next_field(&line);
    if (value == nullptr) {
        _output->setError(RESPONSE_CODE_INVALID_HEADER,
                          "Header Limit: missing value");
    } else {
        int limit = atoi(value);
        if ((isdigit(value[0]) == 0) || limit < 0) {
            _output->setError(
                RESPONSE_CODE_INVALID_HEADER,
                "Invalid value for Limit: must be non-negative integer");
        } else {
            _limit = limit;
        }
    }
}

void Query::parseTimelimitLine(char *line) {
    char *value = next_field(&line);
    if (value == nullptr) {
        _output->setError(RESPONSE_CODE_INVALID_HEADER,
                          "Header Timelimit: missing value");
    } else {
        int timelimit = atoi(value);
        if ((isdigit(value[0]) == 0) || timelimit < 0) {
            _output->setError(RESPONSE_CODE_INVALID_HEADER,
                              "Invalid value for Timelimit: must be "
                              "non-negative integer (seconds)");
        } else {
            _time_limit = timelimit;
            _time_limit_timeout = time(nullptr) + _time_limit;
        }
    }
}

void Query::parseWaitTimeoutLine(char *line) {
    char *value = next_field(&line);
    if (value == nullptr) {
        _output->setError(RESPONSE_CODE_INVALID_HEADER,
                          "WaitTimeout: missing value");
    } else {
        int timeout = atoi(value);
        if ((isdigit(value[0]) == 0) || timeout < 0) {
            _output->setError(
                RESPONSE_CODE_INVALID_HEADER,
                "Invalid value for WaitTimeout: must be non-negative integer");
        } else {
            _wait_timeout = timeout;
        }
    }
}

void Query::parseWaitTriggerLine(char *line) {
    char *value = next_field(&line);
    if (value == nullptr) {
        _output->setError(RESPONSE_CODE_INVALID_HEADER,
                          "WaitTrigger: missing keyword");
        return;
    }
    struct trigger *t = trigger_find(value);
    if (t == nullptr) {
        _output->setError(RESPONSE_CODE_INVALID_HEADER,
                          "WaitTrigger: invalid trigger '%s'. Allowed are %s.",
                          value, trigger_all_names());
        return;
    }
    _wait_trigger = t;
}

void Query::parseWaitObjectLine(char *line) {
    if (_table == nullptr) {
        return;
    }

    char *objectspec = lstrip(line);
    _wait_object = _table->findObject(objectspec);
    if (_wait_object == nullptr) {
        _output->setError(
            RESPONSE_CODE_INVALID_HEADER,
            "WaitObject: object '%s' not found or not supported by this table",
            objectspec);
    }
}

void Query::parseLocaltimeLine(char *line) {
    char *value = next_field(&line);
    if (value == nullptr) {
        _output->setError(RESPONSE_CODE_INVALID_HEADER,
                          "Header Localtime: missing value");
        return;
    }
    time_t their_time = atoi(value);
    time_t our_time = time(nullptr);

    // compute offset to be *added* each time we output our time and
    // *substracted* from reference value by filter headers
    int dif = their_time - our_time;

    // Round difference to half hour. We assume, that both clocks are more
    // or less synchronized and that the time offset is only due to being
    // in different time zones.
    int full = dif / 1800;
    int rem = dif % 1800;
    if (rem <= -900) {
        full--;
    } else if (rem >= 900) {
        full++;
    }
    if (full >= 48 || full <= -48) {
        _output->setError(RESPONSE_CODE_INVALID_HEADER,
                          "Invalid Localtime header: timezone difference "
                          "greater then 24 hours");
        return;
    }
    _timezone_offset = full * 1800;
    if (g_debug_level >= 2) {
        logger(LG_INFO, "Timezone difference is %.1f hours",
               _timezone_offset / 3600.0);
    }
}

bool Query::doStats() { return !_stats_columns.empty(); }

void Query::start() {
    doWait();

    _need_ds_separator = false;

    if (_output_format != OUTPUT_FORMAT_CSV) {
        _output->addChar('[');
    }

    if (doStats()) {
        // if we have no StatsGroupBy: column, we allocate one only row of
        // Aggregators,
        // directly in _stats_aggregators. When grouping the rows of aggregators
        // will be created each time a new group is found.
        if (_columns.empty()) {
            _stats_aggregators = new Aggregator *[_stats_columns.size()];
            for (unsigned i = 0; i < _stats_columns.size(); i++) {
                _stats_aggregators[i] = _stats_columns[i]->createAggregator();
            }
        }
    }

    if (_show_column_headers) {
        outputDatasetBegin();
        bool first = true;

        for (const auto &column : _columns) {
            if (first) {
                first = false;
            } else {
                outputFieldSeparator();
            }
            outputString(column->name());
        }

        // Output dummy headers for stats columns
        int col = 1;
        for (const auto &stats_column : _stats_columns) {
            (void)stats_column;
            if (first) {
                first = false;
            } else {
                outputFieldSeparator();
            }
            char colheader[32];
            snprintf(colheader, 32, "stats_%d", col);
            outputString(colheader);
            col++;
        }

        outputDatasetEnd();
        _need_ds_separator = true;
    }
}

bool Query::timelimitReached() {
    if (_time_limit >= 0 && time(nullptr) >= _time_limit_timeout) {
        logger(LG_INFO, "Maximum query time of %d seconds exceeded!",
               _time_limit);
        _output->setError(RESPONSE_CODE_LIMIT_EXCEEDED,
                          "Maximum query time of %d seconds exceeded!",
                          _time_limit);
        return true;
    }
    return false;
}

bool Query::processDataset(void *data) {
    if (_output->size() > g_max_response_size) {
        logger(LG_INFO, "Maximum response size of %lu bytes exceeded!",
               g_max_response_size);
        // _output->setError(RESPONSE_CODE_LIMIT_EXCEEDED, "Maximum response
        // size of %d reached", g_max_response_size);
        // currently we only log an error into the log file and do
        // not abort the query. We handle it like Limit:
        return false;
    }

    if (_filter.accepts(data) &&
        ((_auth_user == nullptr) || _table->isAuthorized(_auth_user, data))) {
        _current_line++;
        if (_limit >= 0 && static_cast<int>(_current_line) > _limit) {
            return false;
        }

        // When we reach the time limit we let the query fail. Otherwise the
        // user will
        // not know that the answer is incomplete.
        if (timelimitReached()) {
            return false;
        }

        if (doStats()) {
            Aggregator **aggr;
            // When doing grouped stats, we need to fetch/create a row
            // of aggregators for the current group
            if (!_columns.empty()) {
                _stats_group_spec_t groupspec;
                computeStatsGroupSpec(groupspec, data);
                aggr = getStatsGroup(groupspec);
            } else {
                aggr = _stats_aggregators;
            }

            for (unsigned i = 0; i < _stats_columns.size(); i++) {
                aggr[i]->consume(data, this);
            }

            // No output is done while processing the data, we only
            // collect stats.
        } else {
            // output data of current row
            if (_need_ds_separator && _output_format != OUTPUT_FORMAT_CSV) {
                _output->addBuffer(",\n", 2);
            } else {
                _need_ds_separator = true;
            }

            outputDatasetBegin();
            bool first = true;
            for (auto column : _columns) {
                if (first) {
                    first = false;
                } else {
                    outputFieldSeparator();
                }
                column->output(data, this);
            }
            outputDatasetEnd();
        }
    }
    return true;
}

void Query::finish() {
    // grouped stats
    if (doStats() && !_columns.empty()) {
        // output values of all stats groups (output has been post poned until
        // now)
        for (auto &stats_group : _stats_groups) {
            if (_need_ds_separator && _output_format != OUTPUT_FORMAT_CSV) {
                _output->addBuffer(",\n", 2);
            } else {
                _need_ds_separator = true;
            }

            outputDatasetBegin();

            // output group columns first
            _stats_group_spec_t groupspec = stats_group.first;
            bool first = true;
            for (auto &iit : groupspec) {
                if (!first) {
                    outputFieldSeparator();
                } else {
                    first = false;
                }
                outputString(iit.c_str());
            }

            Aggregator **aggr = stats_group.second;
            for (unsigned i = 0; i < _stats_columns.size(); i++) {
                outputFieldSeparator();
                aggr[i]->output(this);
                delete aggr[i];  // not needed any more
            }
            outputDatasetEnd();
            delete[] aggr;
        }
    }

    // stats without group column
    else if (doStats()) {
        if (_need_ds_separator && _output_format != OUTPUT_FORMAT_CSV) {
            _output->addBuffer(",\n", 2);
        } else {
            _need_ds_separator = true;
        }

        outputDatasetBegin();
        for (unsigned i = 0; i < _stats_columns.size(); i++) {
            if (i > 0) {
                outputFieldSeparator();
            }
            _stats_aggregators[i]->output(this);
            delete _stats_aggregators[i];
        }
        outputDatasetEnd();
        delete[] _stats_aggregators;
    }

    // normal query
    if (_output_format != OUTPUT_FORMAT_CSV) {
        _output->addBuffer("]\n", 2);
    }
}

void *Query::findIndexFilter(const char *columnname) {
    return _filter.findIndexFilter(columnname);
}

void Query::findIntLimits(const char *columnname, int *lower, int *upper) {
    return _filter.findIntLimits(columnname, lower, upper);
}

void Query::optimizeBitmask(const char *columnname, uint32_t *bitmask) {
    _filter.optimizeBitmask(columnname, bitmask);
}

// output helpers, called from columns
void Query::outputDatasetBegin() {
    if (_output_format != OUTPUT_FORMAT_CSV) {
        _output->addChar('[');
    }
}

void Query::outputDatasetEnd() {
    if (_output_format == OUTPUT_FORMAT_CSV) {
        _output->addBuffer(_dataset_separator.c_str(),
                           _dataset_separator.size());
    } else {
        _output->addChar(']');
    }
}

void Query::outputFieldSeparator() {
    if (_output_format == OUTPUT_FORMAT_CSV) {
        _output->addBuffer(_field_separator.c_str(), _field_separator.size());
    } else {
        _output->addChar(',');
    }
}

void Query::outputInteger(int32_t value) {
    char buf[32];
    int l = snprintf(buf, 32, "%d", value);
    _output->addBuffer(buf, l);
}

void Query::outputInteger64(int64_t value) {
    char buf[32];
    int l = snprintf(buf, 32, "%lld", static_cast<long long int>(value));
    _output->addBuffer(buf, l);
}

void Query::outputTime(int32_t value) {
    value += _timezone_offset;
    outputInteger(value);
}

void Query::outputUnsignedLong(unsigned long value) {
    char buf[64];
    int l = snprintf(buf, sizeof(buf), "%lu", value);
    _output->addBuffer(buf, l);
}

void Query::outputCounter(counter_t value) {
    char buf[64];
    int l = snprintf(buf, sizeof(buf), "%llu",
                     static_cast<unsigned long long>(value));
    _output->addBuffer(buf, l);
}

void Query::outputDouble(double value) {
    if (isnan(value)) {
        outputNull();
    } else {
        char buf[64];
        int l = snprintf(buf, sizeof(buf), "%.10e", value);
        _output->addBuffer(buf, l);
    }
}

void Query::outputNull() {
    if (_output_format == OUTPUT_FORMAT_CSV) {
        // output empty cell
    } else if (_output_format == OUTPUT_FORMAT_PYTHON) {
        _output->addBuffer("None", 4);
    } else {
        _output->addBuffer("null", 4);  // JSON
    }
}

void Query::outputAsciiEscape(char value) {
    char buf[8];
    snprintf(buf, sizeof(buf), "\\%03o", value);
    _output->addBuffer(buf, 4);
}

void Query::outputUnicodeEscape(unsigned value) {
    char buf[8];
    snprintf(buf, sizeof(buf), "\\u%04x", value);
    _output->addBuffer(buf, 6);
}

void Query::outputBlob(const char *buffer, int size) {
    if (_output_format != OUTPUT_FORMAT_CSV) {
        outputString(buffer, size);
    } else {
        _output->addBuffer(buffer, size);
    }
}

// len = -1 -> use strlen(), len >= 0: consider
// output as blob, do not handle UTF-8.
void Query::outputString(const char *value, int len) {
    if (value == nullptr) {
        if (_output_format != OUTPUT_FORMAT_CSV) {
            _output->addBuffer("\"\"", 2);
        }
        return;
    }

    if (_output_format == OUTPUT_FORMAT_CSV) {
        _output->addString(value);

    } else  // JSON
    {
        if (_output_format == OUTPUT_FORMAT_PYTHON && len < 0) {
            _output->addChar('u');  // mark strings as unicode
        }
        _output->addChar('"');
        const char *r = value;
        int chars_left = len >= 0 ? len : strlen(r);
        while (*r != 0) {
            // Always escape control characters (1..31)
            if (*r < 32 && *r >= 0) {
                if (len < 0) {
                    outputUnicodeEscape(static_cast<unsigned>(*r));
                } else {
                    outputAsciiEscape(*r);
                }
            }

            // Output ASCII characters unencoded
            else if (*r >= 32 || len >= 0) {
                if (*r == '"' || *r == '\\') {
                    _output->addChar('\\');
                }
                _output->addChar(*r);
            }

            // interprete two-Byte UTF-8 sequences in mode 'utf8' and 'mixed'
            else if ((g_data_encoding == ENCODING_UTF8 ||
                      g_data_encoding == ENCODING_MIXED) &&
                     ((*r & 0xE0) == 0xC0)) {
                outputUnicodeEscape(((*r & 31) << 6) |
                                    (*(r + 1) & 0x3F));  // 2 byte encoding
                r++;
                chars_left--;
            }

            // interprete 3/4-Byte UTF-8 sequences only in mode 'utf8'
            else if (g_data_encoding == ENCODING_UTF8) {
                // three-byte sequences (avoid buffer overflow!)
                if ((*r & 0xF0) == 0xE0) {
                    if (chars_left < 3) {
                        if (g_debug_level >= 2) {
                            logger(LG_INFO,
                                   "Ignoring invalid UTF-8 sequence in string "
                                   "'%s'",
                                   value);
                        }
                        break;  // end of string. No use in continuing
                    } else {
                        outputUnicodeEscape(((*r & 0x0F) << 12 |
                                             (*(r + 1) & 0x3F) << 6 |
                                             (*(r + 2) & 0x3F)));
                        r += 2;
                        chars_left -= 2;
                    }
                }
                // four-byte sequences
                else if ((*r & 0xF8) == 0xF0) {
                    if (chars_left < 4) {
                        if (g_debug_level >= 2) {
                            logger(LG_INFO,
                                   "Ignoring invalid UTF-8 sequence in string "
                                   "'%s'",
                                   value);
                        }
                        break;  // end of string. No use in continuing
                    } else {
                        outputUnicodeEscape(
                            ((*r & 0x07) << 18 | (*(r + 1) & 0x3F) << 6 |
                             (*(r + 2) & 0x3F) << 6 | (*(r + 3) & 0x3F)));
                        r += 3;
                        chars_left -= 3;
                    }
                } else {
                    if (g_debug_level >= 2) {
                        logger(LG_INFO,
                               "Ignoring invalid UTF-8 sequence in string '%s'",
                               value);
                    }
                }
            }

            // in latin1 and mixed mode interprete all other non-ASCII
            // characters as latin1
            else {
                outputUnicodeEscape(static_cast<unsigned>(
                    static_cast<int>(*r) + 256));  // assume latin1 encoding
            }

            r++;
            chars_left--;
        }
        _output->addChar('"');
    }
}

void Query::outputBeginList() {
    if (_output_format != OUTPUT_FORMAT_CSV) {
        _output->addChar('[');
    }
}

void Query::outputListSeparator() {
    if (_output_format == OUTPUT_FORMAT_CSV) {
        _output->addBuffer(_list_separator.c_str(), _list_separator.size());
    } else {
        _output->addChar(',');
    }
}

void Query::outputEndList() {
    if (_output_format != OUTPUT_FORMAT_CSV) {
        _output->addChar(']');
    }
}

void Query::outputBeginSublist() {
    if (_output_format != OUTPUT_FORMAT_CSV) {
        _output->addChar('[');
    }
}

void Query::outputSublistSeparator() {
    if (_output_format == OUTPUT_FORMAT_CSV) {
        _output->addBuffer(_host_service_separator.c_str(),
                           _host_service_separator.size());
    } else {
        _output->addChar(',');
    }
}

void Query::outputEndSublist() {
    if (_output_format != OUTPUT_FORMAT_CSV) {
        _output->addChar(']');
    }
}

void Query::outputBeginDict() {
    if (_output_format != OUTPUT_FORMAT_CSV) {
        _output->addChar('{');
    }
}

void Query::outputDictSeparator() { outputListSeparator(); }

void Query::outputDictValueSeparator() {
    if (_output_format == OUTPUT_FORMAT_CSV) {
        _output->addBuffer(_host_service_separator.c_str(),
                           _host_service_separator.size());
    } else {
        _output->addChar(':');
    }
}

void Query::outputEndDict() {
    if (_output_format != OUTPUT_FORMAT_CSV) {
        _output->addChar('}');
    }
}

Aggregator **Query::getStatsGroup(Query::_stats_group_spec_t &groupspec) {
    auto it = _stats_groups.find(groupspec);
    if (it == _stats_groups.end()) {
        auto aggr = new Aggregator *[_stats_columns.size()];
        for (unsigned i = 0; i < _stats_columns.size(); i++) {
            aggr[i] = _stats_columns[i]->createAggregator();
        }
        _stats_groups.insert(make_pair(groupspec, aggr));
        return aggr;
    }
    return it->second;
}

void Query::computeStatsGroupSpec(Query::_stats_group_spec_t &groupspec,
                                  void *data) {
    for (auto column : _columns) {
        groupspec.push_back(column->valueAsString(data, this));
    }
}

void Query::doWait() {
    // If no wait condition and no trigger is set,
    // we do not wait at all.
    if (_wait_condition.numFilters() == 0 && _wait_trigger == nullptr) {
        return;
    }

    // If a condition is set, we check the condition. If it
    // is already true, we do not need to way
    if (_wait_condition.numFilters() > 0 &&
        _wait_condition.accepts(_wait_object)) {
        if (g_debug_level >= 2) {
            logger(LG_INFO, "Wait condition true, no waiting neccessary");
        }
        return;
    }

    // No wait on specified trigger. If no trigger was specified
    // we use WT_ALL as default trigger.
    if (_wait_trigger == nullptr) {
        _wait_trigger = trigger_all();
    }

    struct timeval now;
    gettimeofday(&now, nullptr);
    struct timespec timeout;
    timeout.tv_sec = now.tv_sec + (_wait_timeout / 1000);
    timeout.tv_nsec = now.tv_usec * 1000 + 1000 * 1000 * (_wait_timeout % 1000);
    if (timeout.tv_nsec > 1000000000) {
        timeout.tv_sec++;
        timeout.tv_nsec -= 1000000000;
    }

    do {
        if (_wait_timeout == 0) {
            if (g_debug_level >= 2) {
                logger(LG_INFO,
                       "Waiting unlimited until condition becomes true");
            }
            trigger_wait(_wait_trigger);
        } else {
            if (g_debug_level >= 2) {
                logger(LG_INFO, "Waiting %d ms or until condition becomes true",
                       _wait_timeout);
            }
            if (trigger_wait_until(_wait_trigger, &timeout) == 0) {
                if (g_debug_level >= 2) {
                    logger(LG_INFO, "WaitTimeout after %d ms", _wait_timeout);
                }
                return;  // timeout occurred. do not wait any longer
            }
        }
    } while (!_wait_condition.accepts(_wait_object));
}
