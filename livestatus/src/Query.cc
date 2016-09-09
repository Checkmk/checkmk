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
#include <cctype>
#include <cstdlib>
#include <cstring>
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
#include "StringUtils.h"
#include "Table.h"
#include "VariadicFilter.h"
#include "auth.h"
#include "opids.h"
#include "strutil.h"
#include "waittriggers.h"

extern unsigned long g_max_response_size;

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

Query::Query(const list<string> &lines, Table *table, Encoding data_encoding,
             int debug_level)
    : _data_encoding(data_encoding)
    , _debug_level(debug_level)
    , _response_header(OutputBuffer::ResponseHeader::off)
    , _do_keepalive(false)
    , _table(table)
    , _auth_user(nullptr)
    , _wait_timeout(0)
    , _wait_trigger(nullptr)
    , _wait_object(nullptr)
    , _separators("\n", ";", ",", "|")
    , _show_column_headers(true)
    , _output_format(OutputFormat::broken_csv)
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
        if (_debug_level >= 1) {
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
            invalidHeader("Undefined request header '" + string(buffer) + "'");
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

void Query::addColumn(Column *column) { _columns.push_back(column); }

void Query::setResponseHeader(OutputBuffer::ResponseHeader r) {
    _response_header = r;
}

void Query::setDoKeepalive(bool d) { _do_keepalive = d; }

void Query::invalidHeader(const string &message) {
    if (_invalid_header_message == "") {
        _invalid_header_message = message;
    }
}

void Query::invalidRequest(const string &message) {
    _renderer_query->setError(OutputBuffer::ResponseCode::invalid_request,
                              message);
}

Filter *Query::createFilter(Column *column, RelationalOperator relOp,
                            const string &value) {
    try {
        return column->createFilter(relOp, value);
    } catch (const runtime_error &e) {
        invalidHeader("error creating filter on table" + _table->name() + ": " +
                      e.what());
        return nullptr;
    }
}

void Query::parseAndOrLine(char *line, LogicalOperator andor,
                           VariadicFilter &filter, const string &header) {
    char *value = next_field(&line);
    if (value == nullptr) {
        invalidHeader("Missing value for " + header +
                      ": need positive integer number");
        return;
    }

    int number = atoi(value);
    if (isdigit(value[0]) == 0 || number <= 0) {
        invalidHeader("Invalid value for " + header +
                      ": need positive integer number");
        return;
    }

    filter.combineFilters(number, andor);
}

void Query::parseNegateLine(char *line, VariadicFilter &filter,
                            const string &header) {
    if (next_field(&line) != nullptr) {
        invalidHeader(header + ": does not take any arguments");
        return;
    }

    Filter *to_negate = filter.stealLastSubfiler();
    if (to_negate == nullptr) {
        invalidHeader(header + " nothing to negate");
        return;
    }

    filter.addSubfilter(new NegatingFilter(to_negate));
}

void Query::parseStatsAndOrLine(char *line, LogicalOperator andor) {
    string kind = andor == LogicalOperator::or_ ? "StatsOr" : "StatsAnd";
    char *value = next_field(&line);
    if (value == nullptr) {
        invalidHeader("Missing value for " + kind +
                      ": need non-zero integer number");
        return;
    }

    int number = atoi(value);
    if (isdigit(value[0]) == 0 || number <= 0) {
        invalidHeader("Invalid value for " + kind +
                      " : need non-zero integer number");
        return;
    }

    // The last 'number' StatsColumns must be of type StatsOperation::count
    auto variadic = VariadicFilter::make(andor);
    for (; number > 0; --number) {
        if (_stats_columns.empty()) {
            invalidHeader("Invalid count for " + kind +
                          ": too few Stats: headers available");
            return;
        }

        StatsColumn *col = _stats_columns.back();
        if (col->operation() != StatsOperation::count) {
            invalidHeader("Can use " + kind +
                          " only on Stats: headers of filter type");
            return;
        }
        variadic->addSubfilter(col->stealFilter());
        delete col;
        _stats_columns.pop_back();
    }
    // TODO(sp) Use unique_ptr in StatsColumn.
    _stats_columns.push_back(
        new StatsColumn(nullptr, variadic.release(), StatsOperation::count));
}

void Query::parseStatsNegateLine(char *line) {
    if (next_field(&line) != nullptr) {
        invalidHeader("StatsNegate: does not take any arguments");
        return;
    }
    if (_stats_columns.empty()) {
        invalidHeader("StatsNegate: no Stats: headers available");
        return;
    }
    StatsColumn *col = _stats_columns.back();
    if (col->operation() != StatsOperation::count) {
        invalidHeader(
            "Can use StatsNegate only on Stats: headers of filter type");
        return;
    }
    auto negated = new NegatingFilter(col->stealFilter());
    delete col;
    _stats_columns.pop_back();
    _stats_columns.push_back(
        new StatsColumn(nullptr, negated, StatsOperation::count));
}

void Query::parseStatsLine(char *line) {
    // first token is either aggregation operator or column name
    char *col_or_op = next_field(&line);
    if (col_or_op == nullptr) {
        invalidHeader("empty stats line");
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
            invalidHeader("missing column name in stats header");
            return;
        }
    }

    Column *column = _table->column(column_name);
    if (column == nullptr) {
        invalidHeader("invalid stats header: table '" + _table->name() +
                      "' has no column '" + string(column_name) + "'");
        return;
    }

    StatsColumn *stats_col;
    if (operation == StatsOperation::count) {
        char *operator_name = next_field(&line);
        if (operator_name == nullptr) {
            invalidHeader(
                "invalid stats header: missing operator after table '" +
                string(column_name) + "'");
            return;
        }
        RelationalOperator relOp;
        if (!relationalOperatorForName(operator_name, relOp)) {
            invalidHeader("invalid stats operator '" + string(operator_name) +
                          "'");
            return;
        }
        char *value = lstrip(line);
        if (value == nullptr) {
            invalidHeader("invalid stats: missing value after operator '" +
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
        invalidHeader("empty filter line");
        return;
    }

    Column *column = _table->column(column_name);
    if (column == nullptr) {
        invalidHeader("invalid filter: table '" + _table->name() +
                      "' has no column '" + string(column_name) + "'");
        return;
    }

    char *operator_name = next_field(&line);
    if (operator_name == nullptr) {
        invalidHeader("invalid filter header: missing operator after table '" +
                      string(column_name) + "'");
        return;
    }
    RelationalOperator relOp;
    if (!relationalOperatorForName(operator_name, relOp)) {
        invalidHeader("invalid filter operator '" + string(operator_name) +
                      "'");
        return;
    }
    char *value = lstrip(line);
    if (value == nullptr) {
        invalidHeader("invalid filter: missing value after operator '" +
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
    while (char *column_name = next_field(&line)) {
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
            // invalidHeader(
            //       "Table '%s' has no column '%s'", _table->name(),
            //       column_name);
            Column *col = createDummyColumn(column_name);
            _columns.push_back(col);
        }
    }
    _show_column_headers = false;
}

void Query::parseSeparatorsLine(char *line) {
    char *token = next_field(&line);
    string dsep =
        token == nullptr ? _separators.dataset() : string(1, char(atoi(token)));
    token = next_field(&line);
    string fsep =
        token == nullptr ? _separators.field() : string(1, char(atoi(token)));

    token = next_field(&line);
    string lsep =
        token == nullptr ? _separators.list() : string(1, char(atoi(token)));

    token = next_field(&line);
    string hsep = token == nullptr ? _separators.hostService()
                                   : string(1, char(atoi(token)));

    _separators = CSVSeparators(dsep, fsep, lsep, hsep);
}

namespace {
std::map<string, OutputFormat> formats{{"CSV", OutputFormat::csv},
                                       {"csv", OutputFormat::broken_csv},
                                       {"json", OutputFormat::json},
                                       {"python", OutputFormat::python},
                                       {"python3", OutputFormat::python3}};
}  // namespace

void Query::parseOutputFormatLine(char *line) {
    auto format_and_rest = mk::nextField(line);
    auto it = formats.find(format_and_rest.first);
    if (it == formats.end()) {
        string msg;
        for (const auto &entry : formats) {
            msg += string(msg.empty() ? "" : ", ") + "'" + entry.first + "'";
        }
        invalidHeader("Missing/invalid output format, use one of " + msg + ".");
        return;
    }
    if (!mk::strip(format_and_rest.second).empty()) {
        invalidHeader("OutputFormat: expects only 1 argument");
        return;
    }
    _output_format = it->second;
}

void Query::parseColumnHeadersLine(char *line) {
    char *value = next_field(&line);
    if (value == nullptr) {
        invalidHeader("Missing value for ColumnHeaders: must be 'on' or 'off'");
        return;
    }

    if (strcmp(value, "on") == 0) {
        _show_column_headers = true;
    } else if (strcmp(value, "off") == 0) {
        _show_column_headers = false;
    } else {
        invalidHeader("Invalid value for ColumnHeaders: must be 'on' or 'off'");
    }
}

void Query::parseKeepAliveLine(char *line) {
    char *value = next_field(&line);
    if (value == nullptr) {
        invalidHeader("Missing value for KeepAlive: must be 'on' or 'off'");
        return;
    }

    if (strcmp(value, "on") == 0) {
        setDoKeepalive(true);
    } else if (strcmp(value, "off") == 0) {
        setDoKeepalive(false);
    } else {
        invalidHeader("Invalid value for KeepAlive: must be 'on' or 'off'");
    }
}

void Query::parseResponseHeaderLine(char *line) {
    char *value = next_field(&line);
    if (value == nullptr) {
        invalidHeader(
            "Missing value for ResponseHeader: must be 'off' or 'fixed16'");
        return;
    }

    if (strcmp(value, "off") == 0) {
        setResponseHeader(OutputBuffer::ResponseHeader::off);
    } else if (strcmp(value, "fixed16") == 0) {
        setResponseHeader(OutputBuffer::ResponseHeader::fixed16);
    } else {
        invalidHeader("Invalid value '" + string(value) +
                      "' for ResponseHeader: must be 'off' or 'fixed16'");
    }
}

void Query::parseLimitLine(char *line) {
    char *value = next_field(&line);
    if (value == nullptr) {
        invalidHeader("Header Limit: missing value");
    } else {
        int limit = atoi(value);
        if ((isdigit(value[0]) == 0) || limit < 0) {
            invalidHeader(
                "Invalid value for Limit: must be non-negative integer");
        } else {
            _limit = limit;
        }
    }
}

void Query::parseTimelimitLine(char *line) {
    char *value = next_field(&line);
    if (value == nullptr) {
        invalidHeader("Header Timelimit: missing value");
    } else {
        int timelimit = atoi(value);
        if ((isdigit(value[0]) == 0) || timelimit < 0) {
            invalidHeader(
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
        invalidHeader("WaitTimeout: missing value");
    } else {
        int timeout = atoi(value);
        if ((isdigit(value[0]) == 0) || timeout < 0) {
            invalidHeader(
                "Invalid value for WaitTimeout: must be non-negative integer");
        } else {
            _wait_timeout = timeout;
        }
    }
}

void Query::parseWaitTriggerLine(char *line) {
    char *value = next_field(&line);
    if (value == nullptr) {
        invalidHeader("WaitTrigger: missing keyword");
        return;
    }
    struct trigger *t = trigger_find(value);
    if (t == nullptr) {
        invalidHeader("WaitTrigger: invalid trigger '" + string(value) +
                      "'. Allowed are " + trigger_all_names() + ".");
        return;
    }
    _wait_trigger = t;
}

void Query::parseWaitObjectLine(char *line) {
    char *objectspec = lstrip(line);
    _wait_object = _table->findObject(objectspec);
    if (_wait_object == nullptr) {
        invalidHeader("WaitObject: object '" + string(objectspec) +
                      "' not found or not supported by this table");
    }
}

void Query::parseLocaltimeLine(char *line) {
    char *value = next_field(&line);
    if (value == nullptr) {
        invalidHeader("Header Localtime: missing value");
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
        invalidHeader(
            "Invalid Localtime header: timezone difference "
            "greater then 24 hours");
        return;
    }
    _timezone_offset = full * 1800;
    if (_debug_level >= 2) {
        Informational() << "Timezone difference is "
                        << (_timezone_offset / 3600.0) << " hours";
    }
}

bool Query::doStats() { return !_stats_columns.empty(); }

void Query::process(OutputBuffer *output) {
    auto renderer =
        Renderer::make(_output_format, output, _response_header, _do_keepalive,
                       _invalid_header_message, _separators, _timezone_offset,
                       _data_encoding, _debug_level);
    doWait();
    QueryRenderer q(*renderer);
    _renderer_query = &q;
    start(q);
    _table->answerQuery(this);
    finish(q);
}

void Query::start(QueryRenderer &q) {
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
        RowRenderer r(q);
        for (const auto &column : _columns) {
            r.output(column->name());
        }

        // Output dummy headers for stats columns
        for (size_t col = 1; col <= _stats_columns.size(); ++col) {
            r.output(string("stats_") + to_string(col));
        }
    }
}

bool Query::timelimitReached() {
    if (_time_limit >= 0 && time(nullptr) >= _time_limit_timeout) {
        Informational() << "Maximum query time of " << _time_limit
                        << " seconds exceeded!";
        _renderer_query->setError(OutputBuffer::ResponseCode::limit_exceeded,
                                  "Maximum query time of " +
                                      to_string(_time_limit) +
                                      " seconds exceeded!");
        return true;
    }
    return false;
}

bool Query::processDataset(void *data) {
    if (_renderer_query->size() > g_max_response_size) {
        Informational() << "Maximum response size of " << g_max_response_size
                        << " bytes exceeded!";
        // currently we only log an error into the log file and do
        // not abort the query. We handle it like Limit:
        return false;
    }

    if (_filter.accepts(data, _auth_user, _timezone_offset) &&
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
                aggr[i]->consume(data, _auth_user, _timezone_offset);
            }

            // No output is done while processing the data, we only collect
            // stats.
        } else {
            RowRenderer r(*_renderer_query);
            for (auto column : _columns) {
                column->output(data, r, _auth_user);
            }
        }
    }
    return true;
}

void Query::finish(QueryRenderer &q) {
    // grouped stats
    if (doStats() && !_columns.empty()) {
        // output values of all stats groups (output has been post poned until
        // now)
        for (auto &stats_group : _stats_groups) {
            RowRenderer r(q);
            // output group columns first
            _stats_group_spec_t groupspec = stats_group.first;
            for (auto &iit : groupspec) {
                r.output(iit);
            }

            Aggregator **aggr = stats_group.second;
            for (unsigned i = 0; i < _stats_columns.size(); i++) {
                aggr[i]->output(r);
                delete aggr[i];  // not needed any more
            }
            delete[] aggr;
        }
    }

    // stats without group column
    else if (doStats()) {
        RowRenderer r(q);
        for (unsigned i = 0; i < _stats_columns.size(); i++) {
            _stats_aggregators[i]->output(r);
            delete _stats_aggregators[i];
        }
        delete[] _stats_aggregators;
    }
}

const string *Query::findValueForIndexing(const string &column_name) {
    return _filter.findValueForIndexing(column_name);
}

void Query::findIntLimits(const string &column_name, int *lower, int *upper) {
    return _filter.findIntLimits(column_name, lower, upper, _timezone_offset);
}

void Query::optimizeBitmask(const string &column_name, uint32_t *bitmask) {
    _filter.optimizeBitmask(column_name, bitmask, _timezone_offset);
}

Aggregator **Query::getStatsGroup(Query::_stats_group_spec_t &groupspec) {
    auto it = _stats_groups.find(groupspec);
    if (it == _stats_groups.end()) {
        auto aggr = new Aggregator *[_stats_columns.size()];
        for (unsigned i = 0; i < _stats_columns.size(); i++) {
            aggr[i] = _stats_columns[i]->createAggregator();
        }
        _stats_groups.emplace(groupspec, aggr);
        return aggr;
    }
    return it->second;
}

void Query::computeStatsGroupSpec(Query::_stats_group_spec_t &groupspec,
                                  void *data) {
    for (auto column : _columns) {
        groupspec.push_back(column->valueAsString(data, _auth_user));
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
        _wait_condition.accepts(_wait_object, _auth_user, _timezone_offset)) {
        if (_debug_level >= 2) {
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
            if (_debug_level >= 2) {
                Informational()
                    << "Waiting unlimited until condition becomes true";
            }
            trigger_wait(_wait_trigger);
        } else {
            if (_debug_level >= 2) {
                Informational() << "Waiting " << _wait_timeout
                                << "ms or until condition becomes true";
            }
            if (trigger_wait_for(_wait_trigger, _wait_timeout) == 0) {
                if (_debug_level >= 2) {
                    Informational() << "WaitTimeout after " << _wait_timeout
                                    << "ms";
                }
                return;  // timeout occurred. do not wait any longer
            }
        }
    } while (
        !_wait_condition.accepts(_wait_object, _auth_user, _timezone_offset));
}
