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

#include "Query.h"
#include <ctype.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <memory>
#include <ostream>
#include <stdexcept>
#include <utility>
#include <vector>
#include "Aggregator.h"
#include "Column.h"
#include "ColumnFilter.h"
#include "Filter.h"
#include "FilterVisitor.h"
#include "Logger.h"
#include "NegatingFilter.h"
#include "NullColumn.h"
#include "OutputBuffer.h"
#include "StatsColumn.h"
#include "Table.h"
#include "VariadicFilter.h"
#include "auth.h"
#include "data_encoding.h"
#include "opids.h"
#include "strutil.h"
#include "waittriggers.h"

extern int g_debug_level;
extern unsigned long g_max_response_size;
extern int g_data_encoding;

using std::list;
using std::runtime_error;
using std::string;
using std::to_string;
using std::unordered_set;
using std::vector;

namespace {
class ColumnCollector : public FilterVisitor {
public:
    explicit ColumnCollector(unordered_set<Column *> &columns)
        : _columns(columns) {}
    void visit(ColumnFilter &f) override { _columns.insert(f.column()); }
    void visit(NegatingFilter &f) override { f.subfilter()->accept(*this); }
    void visit(VariadicFilter &f) override {
        for (const auto &sub_filter : f) {
            sub_filter->accept(*this);
        }
    }

private:
    unordered_set<Column *> &_columns;
};
}  // namespace

Query::Query(const list<string> &lines, OutputBuffer *output, Table *table)
    : _output(output)
    , _table(table)
    , _filter(this)
    , _auth_user(nullptr)
    , _wait_condition(this)
    , _wait_timeout(0)
    , _wait_trigger(nullptr)
    , _wait_object(nullptr)
    , _field_separator(";")
    , _dataset_separator("\n")
    , _list_separator(",")
    , _host_service_separator("|")
    , _show_column_headers(true)
    , _need_ds_separator(false)
    , _output_format(OutputFormat::csv)
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
            Informational() << "Query: " << buffer;
        }
        if (strncmp(buffer, "Filter:", 7) == 0) {
            parseFilterLine(lstrip(buffer + 7), _filter);

        } else if (strncmp(buffer, "Or:", 3) == 0) {
            parseAndOrLine(lstrip(buffer + 3), LogicalOperator::or_, _filter,
                           "Or");

        } else if (strncmp(buffer, "And:", 4) == 0) {
            parseAndOrLine(lstrip(buffer + 4), LogicalOperator::and_, _filter,
                           "And");

        } else if (strncmp(buffer, "Negate:", 7) == 0) {
            parseNegateLine(lstrip(buffer + 7), _filter, "Negate");

        } else if (strncmp(buffer, "StatsOr:", 8) == 0) {
            parseStatsAndOrLine(lstrip(buffer + 8), LogicalOperator::or_);

        } else if (strncmp(buffer, "StatsAnd:", 9) == 0) {
            parseStatsAndOrLine(lstrip(buffer + 9), LogicalOperator::and_);

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
            parseFilterLine(lstrip(buffer + 14), _wait_condition);

        } else if (strncmp(buffer, "WaitConditionAnd:", 17) == 0) {
            parseAndOrLine(lstrip(buffer + 17), LogicalOperator::and_,
                           _wait_condition, "WaitConditionAnd");

        } else if (strncmp(buffer, "WaitConditionOr:", 16) == 0) {
            parseAndOrLine(lstrip(buffer + 16), LogicalOperator::or_,
                           _wait_condition, "WaitConditionOr");

        } else if (strncmp(buffer, "WaitConditionNegate:", 20) == 0) {
            parseNegateLine(lstrip(buffer + 20), _wait_condition,
                            "WaitConditionNegate");

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
            setError(OutputBuffer::ResponseCode::invalid_header,
                     "Undefined request header '" + string(buffer) + "'");
            break;
        }
    }

    if (_columns.empty() && !doStats()) {
        table->any_column([this](Column *c) { return addColumn(c), false; });
        // TODO(sp) We overwrite the value from a possible ColumnHeaders: line
        // here, is that really what we want?
        _show_column_headers = true;
    }

    _all_columns.insert(_columns.begin(), _columns.end());
    for (const auto &sc : _stats_columns) {
        _all_columns.insert(sc->column());
    }

    ColumnCollector cc(_all_columns);
    _filter.accept(cc);
    _wait_condition.accept(cc);
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

OutputFormat Query::getOutputFormat() const { return _output_format; }

void Query::setOutputFormat(OutputFormat format) { _output_format = format; }

void Query::addColumn(Column *column) { _columns.push_back(column); }

size_t Query::size() { return _output->size(); }

void Query::add(const string &str) { _output->add(str); }

void Query::add(const vector<char> &blob) { _output->add(blob); }

void Query::setResponseHeader(OutputBuffer::ResponseHeader r) {
    _output->setResponseHeader(r);
}

void Query::setDoKeepalive(bool d) { _output->setDoKeepalive(d); }

void Query::setError(OutputBuffer::ResponseCode code, const string &message) {
    _output->setError(code, message);
}

Filter *Query::createFilter(Column *column, RelationalOperator relOp,
                            const string &value) {
    try {
        return column->createFilter(this, relOp, value);
    } catch (const runtime_error &e) {
        setError(OutputBuffer::ResponseCode::invalid_header,
                 "error creating filter on table" + string(_table->name()) +
                     ": " + e.what());
        return nullptr;
    }
}

void Query::parseAndOrLine(char *line, LogicalOperator andor,
                           VariadicFilter &filter, string header) {
    char *value = next_field(&line);
    if (value == nullptr) {
        setError(
            OutputBuffer::ResponseCode::invalid_header,
            "Missing value for " + header + ": need positive integer number");
        return;
    }

    int number = atoi(value);
    if (isdigit(value[0]) == 0 || number <= 0) {
        setError(
            OutputBuffer::ResponseCode::invalid_header,
            "Invalid value for " + header + ": need positive integer number");
        return;
    }

    filter.combineFilters(this, number, andor);
}

void Query::parseNegateLine(char *line, VariadicFilter &filter, string header) {
    if (next_field(&line) != nullptr) {
        setError(OutputBuffer::ResponseCode::invalid_header,
                 header + ": does not take any arguments");
        return;
    }

    Filter *to_negate = filter.stealLastSubfiler();
    if (to_negate == nullptr) {
        setError(OutputBuffer::ResponseCode::invalid_header,
                 header + " nothing to negate");
        return;
    }

    filter.addSubfilter(new NegatingFilter(this, to_negate));
}

void Query::parseStatsAndOrLine(char *line, LogicalOperator andor) {
    string kind = andor == LogicalOperator::or_ ? "StatsOr" : "StatsAnd";
    char *value = next_field(&line);
    if (value == nullptr) {
        setError(
            OutputBuffer::ResponseCode::invalid_header,
            "Missing value for " + kind + ": need non-zero integer number");
        return;
    }

    int number = atoi(value);
    if ((isdigit(value[0]) == 0) || number <= 0) {
        setError(
            OutputBuffer::ResponseCode::invalid_header,
            "Invalid value for " + kind + " : need non-zero integer number");
        return;
    }

    // The last 'number' StatsColumns must be of type StatsOperation::count
    auto variadic = VariadicFilter::make(this, andor);
    while (number > 0) {
        if (_stats_columns.empty()) {
            setError(OutputBuffer::ResponseCode::invalid_header,
                     "Invalid count for " + kind +
                         ": too few Stats: headers available");
            return;
        }

        StatsColumn *col = _stats_columns.back();
        if (col->operation() != StatsOperation::count) {
            setError(
                OutputBuffer::ResponseCode::invalid_header,
                "Can use " + kind + " only on Stats: headers of filter type");
            return;
        }
        variadic->addSubfilter(col->stealFilter());
        delete col;
        _stats_columns.pop_back();
        number--;
    }
    // TODO(sp) Use unique_ptr in StatsColumn.
    _stats_columns.push_back(
        new StatsColumn(nullptr, variadic.release(), StatsOperation::count));
}

void Query::parseStatsNegateLine(char *line) {
    if (next_field(&line) != nullptr) {
        setError(OutputBuffer::ResponseCode::invalid_header,
                 "StatsNegate: does not take any arguments");
        return;
    }
    if (_stats_columns.empty()) {
        setError(OutputBuffer::ResponseCode::invalid_header,
                 "StatsNegate: no Stats: headers available");
        return;
    }
    StatsColumn *col = _stats_columns.back();
    if (col->operation() != StatsOperation::count) {
        setError(OutputBuffer::ResponseCode::invalid_header,
                 "Can use StatsNegate only on Stats: headers of filter type");
        return;
    }
    auto negated = new NegatingFilter(this, col->stealFilter());
    delete col;
    _stats_columns.pop_back();
    _stats_columns.push_back(
        new StatsColumn(nullptr, negated, StatsOperation::count));
}

void Query::parseStatsLine(char *line) {
    // first token is either aggregation operator or column name
    char *col_or_op = next_field(&line);
    if (col_or_op == nullptr) {
        setError(OutputBuffer::ResponseCode::invalid_header,
                 "empty stats line");
        return;
    }

    StatsOperation operation = StatsOperation::count;
    if (strcmp(col_or_op, "sum") == 0) {
        operation = StatsOperation::sum;
    } else if (strcmp(col_or_op, "min") == 0) {
        operation = StatsOperation::min;
    } else if (strcmp(col_or_op, "max") == 0) {
        operation = StatsOperation::max;
    } else if (strcmp(col_or_op, "avg") == 0) {
        operation = StatsOperation::avg;
    } else if (strcmp(col_or_op, "std") == 0) {
        operation = StatsOperation::std;
    } else if (strcmp(col_or_op, "suminv") == 0) {
        operation = StatsOperation::suminv;
    } else if (strcmp(col_or_op, "avginv") == 0) {
        operation = StatsOperation::avginv;
    }

    char *column_name;
    if (operation == StatsOperation::count) {
        column_name = col_or_op;
    } else {
        // aggregation operator is followed by column name
        column_name = next_field(&line);
        if (column_name == nullptr) {
            setError(OutputBuffer::ResponseCode::invalid_header,
                     "missing column name in stats header");
            return;
        }
    }

    Column *column = _table->column(column_name);
    if (column == nullptr) {
        setError(OutputBuffer::ResponseCode::invalid_header,
                 "invalid stats header: table '" + string(_table->name()) +
                     "' has no column '" + string(column_name) + "'");
        return;
    }

    StatsColumn *stats_col;
    if (operation == StatsOperation::count) {
        char *operator_name = next_field(&line);
        if (operator_name == nullptr) {
            setError(OutputBuffer::ResponseCode::invalid_header,
                     "invalid stats header: missing operator after table '" +
                         string(column_name) + "'");
            return;
        }
        RelationalOperator relOp;
        if (!relationalOperatorForName(operator_name, relOp)) {
            setError(OutputBuffer::ResponseCode::invalid_header,
                     "invalid stats operator '" + string(operator_name) + "'");
            return;
        }
        char *value = lstrip(line);
        if (value == nullptr) {
            setError(OutputBuffer::ResponseCode::invalid_header,
                     "invalid stats: missing value after operator '" +
                         string(operator_name) + "'");
            return;
        }

        Filter *filter = createFilter(column, relOp, value);
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

void Query::parseFilterLine(char *line, VariadicFilter &filter) {
    char *column_name = next_field(&line);
    if (column_name == nullptr) {
        setError(OutputBuffer::ResponseCode::invalid_header,
                 "empty filter line");
        return;
    }

    Column *column = _table->column(column_name);
    if (column == nullptr) {
        setError(OutputBuffer::ResponseCode::invalid_header,
                 "invalid filter: table '" + string(_table->name()) +
                     "' has no column '" + string(column_name) + "'");
        return;
    }

    char *operator_name = next_field(&line);
    if (operator_name == nullptr) {
        setError(OutputBuffer::ResponseCode::invalid_header,
                 "invalid filter header: missing operator after table '" +
                     string(column_name) + "'");
        return;
    }
    RelationalOperator relOp;
    if (!relationalOperatorForName(operator_name, relOp)) {
        setError(OutputBuffer::ResponseCode::invalid_header,
                 "invalid filter operator '" + string(operator_name) + "'");
        return;
    }
    char *value = lstrip(line);
    if (value == nullptr) {
        setError(OutputBuffer::ResponseCode::invalid_header,
                 "invalid filter: missing value after operator '" +
                     string(operator_name) + "'");
        return;
    }

    if (Filter *sub_filter = createFilter(column, relOp, value)) {
        filter.addSubfilter(sub_filter);
    }
}

void Query::parseAuthUserHeader(char *line) {
    _auth_user = find_contact(line);
    if (_auth_user == nullptr) {
        // Do not handle this as error any more. In a multi site setup
        // not all users might be present on all sites by design.
        _auth_user = UNKNOWN_AUTH_USER;
    }
}

void Query::parseStatsGroupLine(char *line) {
    Warning()
        << "Warning: StatsGroupBy is deprecated. Please use Columns instead.";
    parseColumnsLine(line);
}

void Query::parseColumnsLine(char *line) {
    char *column_name;
    while (nullptr != (column_name = next_field(&line))) {
        Column *column = _table->column(column_name);
        if (column != nullptr) {
            _columns.push_back(column);
        } else {
            Warning() << "Replacing non-existing column '"
                      << string(column_name) << "' with null column";
            // Do not fail any longer. We might want to make this configurable.
            // But not failing has the advantage that an updated GUI, that
            // expects new columns,
            // will be able to keep compatibility with older Livestatus
            // versions.
            // setError(OutputBuffer::ResponseCode::invalid_header,
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

    _dataset_separator = string(&dssep, 1);
    _field_separator = string(&fieldsep, 1);
    _list_separator = string(&listsep, 1);
    _host_service_separator = string(&hssep, 1);
}

void Query::parseOutputFormatLine(char *line) {
    char *format = next_field(&line);
    if (format == nullptr) {
        setError(OutputBuffer::ResponseCode::invalid_header,
                 "Missing output format. Only 'csv' and 'json' are available.");
        return;
    }

    if (strcmp(format, "csv") == 0) {
        setOutputFormat(OutputFormat::csv);
    } else if (strcmp(format, "json") == 0) {
        setOutputFormat(OutputFormat::json);
    } else if (strcmp(format, "python") == 0) {
        setOutputFormat(OutputFormat::python);
    } else {
        setError(OutputBuffer::ResponseCode::invalid_header,
                 "Invalid output format. Only 'csv' and 'json' are available.");
    }
}

void Query::parseColumnHeadersLine(char *line) {
    char *value = next_field(&line);
    if (value == nullptr) {
        setError(OutputBuffer::ResponseCode::invalid_header,
                 "Missing value for ColumnHeaders: must be 'on' or 'off'");
        return;
    }

    if (strcmp(value, "on") == 0) {
        _show_column_headers = true;
    } else if (strcmp(value, "off") == 0) {
        _show_column_headers = false;
    } else {
        setError(OutputBuffer::ResponseCode::invalid_header,
                 "Invalid value for ColumnHeaders: must be 'on' or 'off'");
    }
}

void Query::parseKeepAliveLine(char *line) {
    char *value = next_field(&line);
    if (value == nullptr) {
        setError(OutputBuffer::ResponseCode::invalid_header,
                 "Missing value for KeepAlive: must be 'on' or 'off'");
        return;
    }

    if (strcmp(value, "on") == 0) {
        setDoKeepalive(true);
    } else if (strcmp(value, "off") == 0) {
        setDoKeepalive(false);
    } else {
        setError(OutputBuffer::ResponseCode::invalid_header,
                 "Invalid value for KeepAlive: must be 'on' or 'off'");
    }
}

void Query::parseResponseHeaderLine(char *line) {
    char *value = next_field(&line);
    if (value == nullptr) {
        setError(
            OutputBuffer::ResponseCode::invalid_header,
            "Missing value for ResponseHeader: must be 'off' or 'fixed16'");
        return;
    }

    if (strcmp(value, "off") == 0) {
        setResponseHeader(OutputBuffer::ResponseHeader::off);
    } else if (strcmp(value, "fixed16") == 0) {
        setResponseHeader(OutputBuffer::ResponseHeader::fixed16);
    } else {
        setError(OutputBuffer::ResponseCode::invalid_header,
                 "Invalid value '" + string(value) +
                     "' for ResponseHeader: must be 'off' or 'fixed16'");
    }
}

void Query::parseLimitLine(char *line) {
    char *value = next_field(&line);
    if (value == nullptr) {
        setError(OutputBuffer::ResponseCode::invalid_header,
                 "Header Limit: missing value");
    } else {
        int limit = atoi(value);
        if ((isdigit(value[0]) == 0) || limit < 0) {
            setError(OutputBuffer::ResponseCode::invalid_header,
                     "Invalid value for Limit: must be non-negative integer");
        } else {
            _limit = limit;
        }
    }
}

void Query::parseTimelimitLine(char *line) {
    char *value = next_field(&line);
    if (value == nullptr) {
        setError(OutputBuffer::ResponseCode::invalid_header,
                 "Header Timelimit: missing value");
    } else {
        int timelimit = atoi(value);
        if ((isdigit(value[0]) == 0) || timelimit < 0) {
            setError(OutputBuffer::ResponseCode::invalid_header,
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
        setError(OutputBuffer::ResponseCode::invalid_header,
                 "WaitTimeout: missing value");
    } else {
        int timeout = atoi(value);
        if ((isdigit(value[0]) == 0) || timeout < 0) {
            setError(
                OutputBuffer::ResponseCode::invalid_header,
                "Invalid value for WaitTimeout: must be non-negative integer");
        } else {
            _wait_timeout = timeout;
        }
    }
}

void Query::parseWaitTriggerLine(char *line) {
    char *value = next_field(&line);
    if (value == nullptr) {
        setError(OutputBuffer::ResponseCode::invalid_header,
                 "WaitTrigger: missing keyword");
        return;
    }
    struct trigger *t = trigger_find(value);
    if (t == nullptr) {
        setError(OutputBuffer::ResponseCode::invalid_header,
                 "WaitTrigger: invalid trigger '" + string(value) +
                     "'. Allowed are " + trigger_all_names() + ".");
        return;
    }
    _wait_trigger = t;
}

void Query::parseWaitObjectLine(char *line) {
    char *objectspec = lstrip(line);
    _wait_object = _table->findObject(objectspec);
    if (_wait_object == nullptr) {
        setError(OutputBuffer::ResponseCode::invalid_header,
                 "WaitObject: object '" + string(objectspec) +
                     "' not found or not supported by this table");
    }
}

void Query::parseLocaltimeLine(char *line) {
    char *value = next_field(&line);
    if (value == nullptr) {
        setError(OutputBuffer::ResponseCode::invalid_header,
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
        setError(OutputBuffer::ResponseCode::invalid_header,
                 "Invalid Localtime header: timezone difference "
                 "greater then 24 hours");
        return;
    }
    _timezone_offset = full * 1800;
    if (g_debug_level >= 2) {
        Informational() << "Timezone difference is "
                        << (_timezone_offset / 3600.0) << " hours";
    }
}

bool Query::doStats() { return !_stats_columns.empty(); }

void Query::process() {
    start();
    _table->answerQuery(this);
    finish();
}

void Query::start() {
    doWait();

    _need_ds_separator = false;

    if (getOutputFormat() != OutputFormat::csv) {
        add("[");
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
        Informational() << "Maximum query time of " << _time_limit
                        << " seconds exceeded!";
        setError(OutputBuffer::ResponseCode::limit_exceeded,
                 "Maximum query time of " + to_string(_time_limit) +
                     " seconds exceeded!");
        return true;
    }
    return false;
}

bool Query::processDataset(void *data) {
    if (size() > g_max_response_size) {
        Informational() << "Maximum response size of " << g_max_response_size
                        << " bytes exceeded!";
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
        // user will not know that the answer is incomplete.
        if (timelimitReached()) {
            return false;
        }

        if (doStats()) {
            Aggregator **aggr;
            // When doing grouped stats, we need to fetch/create a row of
            // aggregators for the current group
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

            // No output is done while processing the data, we only collect
            // stats.
        } else {
            // output data of current row
            if (_need_ds_separator && getOutputFormat() != OutputFormat::csv) {
                add(",\n");
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
            if (_need_ds_separator && getOutputFormat() != OutputFormat::csv) {
                add(",\n");
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
        if (_need_ds_separator && getOutputFormat() != OutputFormat::csv) {
            add(",\n");
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
    if (getOutputFormat() != OutputFormat::csv) {
        add("]\n");
    }
}

void *Query::findIndexFilter(const string &column_name) {
    return _filter.findIndexFilter(column_name);
}

void Query::findIntLimits(const string &column_name, int *lower, int *upper) {
    return _filter.findIntLimits(column_name, lower, upper);
}

void Query::optimizeBitmask(const string &column_name, uint32_t *bitmask) {
    _filter.optimizeBitmask(column_name, bitmask);
}

// output helpers, called from columns
void Query::outputDatasetBegin() {
    if (getOutputFormat() != OutputFormat::csv) {
        add("[");
    }
}

void Query::outputDatasetEnd() {
    if (getOutputFormat() == OutputFormat::csv) {
        add(_dataset_separator);
    } else {
        add("]");
    }
}

void Query::outputFieldSeparator() {
    if (getOutputFormat() == OutputFormat::csv) {
        add(_field_separator);
    } else {
        add(",");
    }
}

void Query::outputInteger(int32_t value) { add(to_string(value)); }

void Query::outputInteger64(int64_t value) { add(to_string(value)); }

void Query::outputTime(int32_t value) {
    outputInteger(value + _timezone_offset);
}

void Query::outputUnsignedLong(unsigned long value) { add(to_string(value)); }

void Query::outputCounter(counter_t value) { add(to_string(value)); }

void Query::outputDouble(double value) {
    if (isnan(value)) {
        outputNull();
    } else {
        char buf[64];
        snprintf(buf, sizeof(buf), "%.10e", value);
        add(buf);
    }
}

void Query::outputNull() {
    if (getOutputFormat() == OutputFormat::csv) {
        // output empty cell
    } else if (getOutputFormat() == OutputFormat::python) {
        add("None");
    } else {
        add("null");  // JSON
    }
}

void Query::outputAsciiEscape(char value) {
    char buf[8];
    snprintf(buf, sizeof(buf), "\\%03o", value);
    add(buf);
}

void Query::outputUnicodeEscape(unsigned value) {
    char buf[8];
    snprintf(buf, sizeof(buf), "\\u%04x", value);
    add(buf);
}

void Query::outputBlob(const vector<char> *blob) {
    if (getOutputFormat() != OutputFormat::csv) {
        if (blob != nullptr) {
            outputString(&(*blob)[0], blob->size());
        } else {
            outputNull();
        }
    } else {
        if (blob != nullptr) {
            add(*blob);
        }
    }
}

// len = -1 -> use strlen(), len >= 0: consider
// output as blob, do not handle UTF-8.
void Query::outputString(const char *value, int len) {
    if (value == nullptr) {
        if (getOutputFormat() != OutputFormat::csv) {
            add("\"\"");
        }
        return;
    }

    if (getOutputFormat() == OutputFormat::csv) {
        add(value);

    } else  // JSON or PYTHON
    {
        if (getOutputFormat() == OutputFormat::python && len < 0) {
            add("u");  // mark strings as unicode
        }
        add("\"");
        const char *r = value;
        int chars_left = len >= 0 ? len : strlen(r);
        while (chars_left != 0) {
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
                    add("\\");
                }
                add(string(r, 1));
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
                            Informational()
                                << "Ignoring invalid UTF-8 sequence in string '"
                                << string(value) << "'";
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
                            Informational()
                                << "Ignoring invalid UTF-8 sequence in string '"
                                << string(value) << "'";
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
                        Informational()
                            << "Ignoring invalid UTF-8 sequence in string '"
                            << string(value) << "'";
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
        add("\"");
    }
}

void Query::outputBeginList() {
    if (getOutputFormat() != OutputFormat::csv) {
        add("[");
    }
}

void Query::outputListSeparator() {
    if (getOutputFormat() == OutputFormat::csv) {
        add(_list_separator);
    } else {
        add(",");
    }
}

void Query::outputEndList() {
    if (getOutputFormat() != OutputFormat::csv) {
        add("]");
    }
}

void Query::outputBeginSublist() {
    if (getOutputFormat() != OutputFormat::csv) {
        add("[");
    }
}

void Query::outputSublistSeparator() {
    if (getOutputFormat() == OutputFormat::csv) {
        add(_host_service_separator);
    } else {
        add(",");
    }
}

void Query::outputEndSublist() {
    if (getOutputFormat() != OutputFormat::csv) {
        add("]");
    }
}

void Query::outputBeginDict() {
    if (getOutputFormat() != OutputFormat::csv) {
        add("{");
    }
}

void Query::outputDictSeparator() { outputListSeparator(); }

void Query::outputDictValueSeparator() {
    if (getOutputFormat() == OutputFormat::csv) {
        add(_host_service_separator);
    } else {
        add(":");
    }
}

void Query::outputEndDict() {
    if (getOutputFormat() != OutputFormat::csv) {
        add("}");
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
    if (!_wait_condition.hasSubFilters() && _wait_trigger == nullptr) {
        return;
    }

    // If a condition is set, we check the condition. If it
    // is already true, we do not need to way
    if (_wait_condition.hasSubFilters() &&
        _wait_condition.accepts(_wait_object)) {
        if (g_debug_level >= 2) {
            Informational() << "Wait condition true, no waiting neccessary";
        }
        return;
    }

    // No wait on specified trigger. If no trigger was specified
    // we use WT_ALL as default trigger.
    if (_wait_trigger == nullptr) {
        _wait_trigger = trigger_all();
    }

    do {
        if (_wait_timeout == 0) {
            if (g_debug_level >= 2) {
                Informational()
                    << "Waiting unlimited until condition becomes true";
            }
            trigger_wait(_wait_trigger);
        } else {
            if (g_debug_level >= 2) {
                Informational() << "Waiting " << _wait_timeout
                                << "ms or until condition becomes true";
            }
            if (trigger_wait_for(_wait_trigger, _wait_timeout) == 0) {
                if (g_debug_level >= 2) {
                    Informational() << "WaitTimeout after " << _wait_timeout
                                    << "ms";
                }
                return;  // timeout occurred. do not wait any longer
            }
        }
    } while (!_wait_condition.accepts(_wait_object));
}
