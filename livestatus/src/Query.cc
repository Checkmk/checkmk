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

// duration_cast uses enable_if as an implementation detail, similar bug as
// https://github.com/include-what-you-use/include-what-you-use/issues/434
// IWYU pragma: no_include <type_traits>
#include "Query.h"
#include <cctype>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <ostream>
#include <ratio>
#include <stdexcept>
#include <utility>
#include "Aggregator.h"
#include "Column.h"
#include "Filter.h"
#include "Logger.h"
#include "MonitoringCore.h"
#include "NullColumn.h"
#include "OringFilter.h"
#include "OutputBuffer.h"
#include "StatsColumn.h"
#include "StringUtils.h"
#include "Table.h"
#include "Triggers.h"
#include "auth.h"
#include "opids.h"
#include "strutil.h"

// for find_contact, ugly...
#ifdef CMC
#include "cmc.h"
#else
#include "nagios.h"
#endif

namespace {
std::string nextStringArgument(char **line) {
    if (auto value = next_field(line)) {
        return value;
    }
    throw std::runtime_error("missing argument");
}

int nextNonNegativeIntegerArgument(char **line) {
    auto value = nextStringArgument(line);
    int number = atoi(value.c_str());
    if (isdigit(value[0]) == 0 || number < 0) {
        throw std::runtime_error("expected non-negative integer");
    }
    return number;
}

void checkNoArguments(const char *line) {
    if (line[0] != 0) {
        throw std::runtime_error("superfluous argument(s)");
    }
}
}  // namespace

Query::Query(const std::list<std::string> &lines, Table *table,
             Encoding data_encoding, size_t max_response_size,
             OutputBuffer &output)
    : _data_encoding(data_encoding)
    , _max_response_size(max_response_size)
    , _output(output)
    , _table(table)
    , _keepalive(false)
    , _auth_user(nullptr)
    , _wait_timeout(0)
    , _wait_trigger(Triggers::Kind::all)
    , _wait_object(nullptr)
    , _separators("\n", ";", ",", "|")
    , _show_column_headers(true)
    , _output_format(OutputFormat::broken_csv)
    , _limit(-1)
    , _time_limit(-1)
    , _time_limit_timeout(0)
    , _current_line(0)
    , _timezone_offset(0)
    , _logger(table->logger()) {
    FilterStack filters;
    FilterStack wait_conditions;
    for (auto &line : lines) {
        auto stripped_line = mk::rstrip(line);
        if (stripped_line.empty()) {
            break;
        }
        auto pos = stripped_line.find(':');
        std::string header;
        std::string rest;
        if (pos == std::string::npos) {
            header = stripped_line;
        } else {
            header = stripped_line.substr(0, pos);
            rest = mk::lstrip(stripped_line.substr(pos + 1));
        }
        std::vector<char> rest_copy(rest.begin(), rest.end());
        rest_copy.push_back('\0');
        char *arguments = &rest_copy[0];
        try {
            if (header == "Filter") {
                parseFilterLine(arguments, filters);
            } else if (header == "Or") {
                parseAndOrLine(arguments, LogicalOperator::or_, filters);
            } else if (header == "And") {
                parseAndOrLine(arguments, LogicalOperator::and_, filters);
            } else if (header == "Negate") {
                parseNegateLine(arguments, filters);
            } else if (header == "StatsOr") {
                parseStatsAndOrLine(arguments, LogicalOperator::or_);
            } else if (header == "StatsAnd") {
                parseStatsAndOrLine(arguments, LogicalOperator::and_);
            } else if (header == "StatsNegate") {
                parseStatsNegateLine(arguments);
            } else if (header == "Stats") {
                parseStatsLine(arguments);
            } else if (header == "StatsGroupBy") {
                parseStatsGroupLine(arguments);
            } else if (header == "Columns") {
                parseColumnsLine(arguments);
            } else if (header == "ColumnHeaders") {
                parseColumnHeadersLine(arguments);
            } else if (header == "Limit") {
                parseLimitLine(arguments);
            } else if (header == "Timelimit") {
                parseTimelimitLine(arguments);
            } else if (header == "AuthUser") {
                parseAuthUserHeader(arguments);
            } else if (header == "Separators") {
                parseSeparatorsLine(arguments);
            } else if (header == "OutputFormat") {
                parseOutputFormatLine(arguments);
            } else if (header == "ResponseHeader") {
                parseResponseHeaderLine(arguments);
            } else if (header == "KeepAlive") {
                parseKeepAliveLine(arguments);
            } else if (header == "WaitCondition") {
                parseFilterLine(arguments, wait_conditions);
            } else if (header == "WaitConditionAnd") {
                parseAndOrLine(arguments, LogicalOperator::and_,
                               wait_conditions);
            } else if (header == "WaitConditionOr") {
                parseAndOrLine(arguments, LogicalOperator::or_,
                               wait_conditions);
            } else if (header == "WaitConditionNegate") {
                parseNegateLine(arguments, wait_conditions);
            } else if (header == "WaitTrigger") {
                parseWaitTriggerLine(arguments);
            } else if (header == "WaitObject") {
                parseWaitObjectLine(arguments);
            } else if (header == "WaitTimeout") {
                parseWaitTimeoutLine(arguments);
            } else if (header == "Localtime") {
                parseLocaltimeLine(arguments);
            } else {
                throw std::runtime_error("undefined request header");
            }
        } catch (const std::runtime_error &e) {
            _output.setError(OutputBuffer::ResponseCode::invalid_header,
                             header + ": " + e.what());
        }
    }

    if (_columns.empty() && !doStats()) {
        table->any_column([this](std::shared_ptr<Column> c) {
            return _columns.push_back(c), _all_columns.insert(c), false;
        });
        // TODO(sp) We overwrite the value from a possible ColumnHeaders: line
        // here, is that really what we want?
        _show_column_headers = true;
    }

    _filter = std::make_unique<AndingFilter>(std::move(filters));
    _wait_condition =
        std::make_unique<AndingFilter>(std::move(wait_conditions));
}

void Query::invalidRequest(const std::string &message) const {
    _output.setError(OutputBuffer::ResponseCode::invalid_request, message);
}

namespace {
std::unique_ptr<Filter> makeFilter(
    Query::LogicalOperator op,
    std::vector<std::unique_ptr<Filter>> subfilters) {
    switch (op) {
        case Query::LogicalOperator::and_:
            return std::make_unique<AndingFilter>(std::move(subfilters));
            break;
        case Query::LogicalOperator::or_:
            return std::make_unique<OringFilter>(std::move(subfilters));
    }
    return nullptr;  // unreachable
}
}  // namespace

void Query::parseAndOrLine(char *line, LogicalOperator op,
                           FilterStack &filters) {
    auto number = nextNonNegativeIntegerArgument(&line);
    std::vector<std::unique_ptr<Filter>> subfilters;
    for (auto i = 0; i < number; ++i) {
        if (filters.empty()) {
            throw std::runtime_error(
                "error combining filters for table '" + _table->name() +
                "': expected " + std::to_string(number) +
                " filters, but only " + std::to_string(i) + " " +
                (i == 1 ? "is" : "are") + " on stack");
        }

        subfilters.push_back(std::move(filters.back()));
        filters.pop_back();
    }
    filters.push_back(makeFilter(op, std::move(subfilters)));
}

void Query::parseNegateLine(char *line, FilterStack &filters) {
    checkNoArguments(line);
    if (filters.empty()) {
        throw("error combining filters for table '" + _table->name() +
              "': expected 1 filters, but only 0 are on stack");
    }

    auto top = std::move(filters.back());
    filters.pop_back();
    filters.push_back(top->negate());
}

void Query::parseStatsAndOrLine(char *line, LogicalOperator op) {
    auto number = nextNonNegativeIntegerArgument(&line);
    // The last 'number' StatsColumns must be of type StatsOperation::count
    std::vector<std::unique_ptr<Filter>> subfilters;
    for (auto i = 0; i < number; ++i) {
        if (_stats_columns.empty()) {
            throw std::runtime_error(
                "error combining filters for table '" + _table->name() +
                "': expected " + std::to_string(number) +
                " filters, but only " + std::to_string(i) + " " +
                (i == 1 ? "is" : "are") + " on stack");
        }
        auto &col = _stats_columns.back();
        if (col->operation() != StatsOperation::count) {
            throw std::runtime_error(
                "only valid on Stats: headers of filter type");
        }
        subfilters.push_back(col->stealFilter());
        _stats_columns.pop_back();
    }
    _stats_columns.push_back(std::make_unique<StatsColumn>(
        nullptr, makeFilter(op, std::move(subfilters)), StatsOperation::count));
}

void Query::parseStatsNegateLine(char *line) {
    checkNoArguments(line);
    if (_stats_columns.empty()) {
        throw("error combining filters for table '" + _table->name() +
              "': expected 1 filters, but only 0 are on stack");
    }
    auto &col = _stats_columns.back();
    if (col->operation() != StatsOperation::count) {
        throw std::runtime_error("only valid on Stats: headers of filter type");
    }
    auto to_negate = col->stealFilter();
    _stats_columns.pop_back();
    _stats_columns.push_back(std::make_unique<StatsColumn>(
        nullptr, to_negate->negate(), StatsOperation::count));
}

void Query::parseStatsLine(char *line) {
    // first token is either aggregation operator or column name
    auto col_or_op = nextStringArgument(&line);
    StatsOperation operation;
    std::string column_name;
    if (col_or_op == "sum") {
        operation = StatsOperation::sum;
        column_name = nextStringArgument(&line);
    } else if (col_or_op == "min") {
        operation = StatsOperation::min;
        column_name = nextStringArgument(&line);
    } else if (col_or_op == "max") {
        operation = StatsOperation::max;
        column_name = nextStringArgument(&line);
    } else if (col_or_op == "avg") {
        operation = StatsOperation::avg;
        column_name = nextStringArgument(&line);
    } else if (col_or_op == "std") {
        operation = StatsOperation::std;
        column_name = nextStringArgument(&line);
    } else if (col_or_op == "suminv") {
        operation = StatsOperation::suminv;
        column_name = nextStringArgument(&line);
    } else if (col_or_op == "avginv") {
        operation = StatsOperation::avginv;
        column_name = nextStringArgument(&line);
    } else {
        operation = StatsOperation::count;
        column_name = col_or_op;
    }

    auto column = _table->column(column_name);
    std::unique_ptr<Filter> filter;
    if (operation == StatsOperation::count) {
        auto relOp = relationalOperatorForName(nextStringArgument(&line));
        auto operand = mk::lstrip(line);
        filter = column->createFilter(relOp, operand);
    } else {
        // create an "accept all" filter, just in case we fall back to counting
        filter = std::make_unique<AndingFilter>(
            std::vector<std::unique_ptr<Filter>>());
    }
    _stats_columns.push_back(
        std::make_unique<StatsColumn>(column.get(), move(filter), operation));
    _all_columns.insert(column);

    // Default to old behaviour: do not output column headers if we do Stats
    // queries
    _show_column_headers = false;
}

void Query::parseFilterLine(char *line, FilterStack &filters) {
    auto column = _table->column(nextStringArgument(&line));
    auto relOp = relationalOperatorForName(nextStringArgument(&line));
    auto operand = mk::lstrip(line);
    auto sub_filter = column->createFilter(relOp, operand);
    filters.push_back(std::move(sub_filter));
    _all_columns.insert(column);
}

void Query::parseAuthUserHeader(char *line) {
    _auth_user = find_contact(line);
    if (_auth_user == nullptr) {
        // Do not handle this as error any more. In a multi site setup
        // not all users might be present on all sites by design.
        _auth_user = unknown_auth_user();
    }
}

void Query::parseStatsGroupLine(char *line) {
    Warning(_logger)
        << "Warning: StatsGroupBy is deprecated. Please use Columns instead.";
    parseColumnsLine(line);
}

void Query::parseColumnsLine(char *line) {
    std::string str = line;
    const std::string sep = " \t\n\v\f\r";
    for (auto pos = str.find_first_not_of(sep); pos != std::string::npos;) {
        auto space = str.find_first_of(sep, pos);
        auto column_name =
            str.substr(pos, space - (space == std::string::npos ? 0 : pos));
        pos = str.find_first_not_of(sep, space);
        std::shared_ptr<Column> column;
        try {
            column = _table->column(column_name);
        } catch (const std::runtime_error &e) {
            // Do not fail any longer. We might want to make this configurable.
            // But not failing has the advantage that an updated GUI, that
            // expects new columns, will be able to keep compatibility with
            // older Livestatus versions.
            Informational(_logger) << "replacing non-existing column '"
                                   << column_name << "' with null column";
            column = std::make_shared<NullColumn>(
                column_name, "non-existing column", -1, -1, -1, 0);
        }
        _columns.push_back(column);
        _all_columns.insert(column);
    }
    _show_column_headers = false;
}

void Query::parseSeparatorsLine(char *line) {
    std::string dsep =
        std::string(1, char(nextNonNegativeIntegerArgument(&line)));
    std::string fsep =
        std::string(1, char(nextNonNegativeIntegerArgument(&line)));
    std::string lsep =
        std::string(1, char(nextNonNegativeIntegerArgument(&line)));
    std::string hsep =
        std::string(1, char(nextNonNegativeIntegerArgument(&line)));
    _separators = CSVSeparators(dsep, fsep, lsep, hsep);
}

namespace {
std::map<std::string, OutputFormat> formats{{"CSV", OutputFormat::csv},
                                            {"csv", OutputFormat::broken_csv},
                                            {"json", OutputFormat::json},
                                            {"python", OutputFormat::python},
                                            {"python3", OutputFormat::python3}};
}  // namespace

void Query::parseOutputFormatLine(char *line) {
    auto format_and_rest = mk::nextField(line);
    auto it = formats.find(format_and_rest.first);
    if (it == formats.end()) {
        std::string msg;
        for (const auto &entry : formats) {
            msg +=
                std::string(msg.empty() ? "" : ", ") + "'" + entry.first + "'";
        }
        throw std::runtime_error("missing/invalid output format, use one of " +
                                 msg);
    }
    if (!mk::strip(format_and_rest.second).empty()) {
        throw std::runtime_error("only 1 argument expected");
    }
    _output_format = it->second;
}

void Query::parseColumnHeadersLine(char *line) {
    auto value = nextStringArgument(&line);
    if (value == "on") {
        _show_column_headers = true;
    } else if (value == "off") {
        _show_column_headers = false;
    } else {
        throw std::runtime_error("expected 'on' or 'off'");
    }
}

void Query::parseKeepAliveLine(char *line) {
    auto value = nextStringArgument(&line);
    if (value == "on") {
        _keepalive = true;
    } else if (value == "off") {
        _keepalive = false;
    } else {
        throw std::runtime_error("expected 'on' or 'off'");
    }
}

void Query::parseResponseHeaderLine(char *line) {
    auto value = nextStringArgument(&line);
    if (value == "off") {
        _output.setResponseHeader(OutputBuffer::ResponseHeader::off);
    } else if (value == "fixed16") {
        _output.setResponseHeader(OutputBuffer::ResponseHeader::fixed16);
    } else {
        throw std::runtime_error("expected 'off' or 'fixed16'");
    }
}

void Query::parseLimitLine(char *line) {
    _limit = nextNonNegativeIntegerArgument(&line);
}

void Query::parseTimelimitLine(char *line) {
    _time_limit = nextNonNegativeIntegerArgument(&line);
    _time_limit_timeout = time(nullptr) + _time_limit;
}

void Query::parseWaitTimeoutLine(char *line) {
    _wait_timeout =
        std::chrono::milliseconds(nextNonNegativeIntegerArgument(&line));
}

void Query::parseWaitTriggerLine(char *line) {
    _wait_trigger = _table->core()->triggers().find(nextStringArgument(&line));
}

void Query::parseWaitObjectLine(char *line) {
    auto objectspec = mk::lstrip(line);
    _wait_object = _table->findObject(objectspec);
    if (_wait_object.isNull()) {
        throw std::runtime_error("object '" + objectspec +
                                 "' not found or not supported by this table");
    }
}

void Query::parseLocaltimeLine(char *line) {
    auto value = nextNonNegativeIntegerArgument(&line);
    // Compute offset to be *added* each time we output our time and
    // *subtracted* from reference value by filter headers
    auto diff = std::chrono::system_clock::from_time_t(value) -
                std::chrono::system_clock::now();

    // Round difference to half hour. We assume, that both clocks are more or
    // less synchronized and that the time offset is only due to being in
    // different time zones. This would be a one-liner if we already had C++17's
    // std::chrono::round().
    using half_an_hour = std::chrono::duration<double, std::ratio<1800>>;
    auto hah = std::chrono::duration_cast<half_an_hour>(diff);
    auto rounded = half_an_hour(round(hah.count()));
    auto offset = std::chrono::duration_cast<std::chrono::seconds>(rounded);
    if (offset <= std::chrono::hours(-24) || offset >= std::chrono::hours(24)) {
        throw std::runtime_error(
            "timezone difference greater than or equal to 24 hours");
    }

    if (offset != std::chrono::seconds(0)) {
        using hour = std::chrono::duration<double, std::ratio<3600>>;
        Debug(_logger) << "timezone offset is "
                       << std::chrono::duration_cast<hour>(offset).count()
                       << "h";
    }
    _timezone_offset = offset;
}

bool Query::doStats() const { return !_stats_columns.empty(); }

bool Query::process() {
    // Precondition: output has been reset
    auto start_time = std::chrono::system_clock::now();
    auto renderer =
        Renderer::make(_output_format, _output.os(), _output.getLogger(),
                       _separators, _data_encoding);
    doWait();
    QueryRenderer q(*renderer, EmitBeginEnd::on);
    _renderer_query = &q;
    start(q);
    _table->answerQuery(this);
    finish(q);
    auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::system_clock::now() - start_time);
    Informational(_logger) << "processed request in " << elapsed.count()
                           << " ms, replied with " << _output.os().tellp()
                           << " bytes";
    return _keepalive;
}

void Query::start(QueryRenderer &q) {
    if (_columns.empty()) {
        getAggregatorsFor({});
    }
    if (_show_column_headers) {
        RowRenderer r(q);
        for (const auto &column : _columns) {
            r.output(column->name());
        }

        // Output dummy headers for stats columns
        for (size_t col = 1; col <= _stats_columns.size(); ++col) {
            r.output(std::string("stats_") + std::to_string(col));
        }
    }
}

bool Query::timelimitReached() const {
    if (_time_limit >= 0 && time(nullptr) >= _time_limit_timeout) {
        _output.setError(OutputBuffer::ResponseCode::limit_exceeded,
                         "Maximum query time of " +
                             std::to_string(_time_limit) +
                             " seconds exceeded!");
        return true;
    }
    return false;
}

bool Query::processDataset(Row row) {
    if (static_cast<size_t>(_output.os().tellp()) > _max_response_size) {
        Informational(_logger) << "Maximum response size of "
                               << _max_response_size << " bytes exceeded!";
        // currently we only log an error into the log file and do
        // not abort the query. We handle it like Limit:
        return false;
    }

    if (_filter->accepts(row, _auth_user, _timezone_offset) &&
        ((_auth_user == nullptr) || _table->isAuthorized(row, _auth_user))) {
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
            // Things get a bit tricky here: For stats queries, we have to
            // combine rows with the same values in the non-stats columns. But
            // when we finally output those non-stats columns in finish(), we
            // don't have the row anymore, so we can't use Column::output()
            // then.  :-/ The slightly hacky workaround is to pre-render all
            // non-stats columns into a single string here (RowFragment) and
            // output it later in a verbatim manner.
            std::ostringstream os;
            {
                auto renderer =
                    Renderer::make(_output_format, os, _output.getLogger(),
                                   _separators, _data_encoding);
                QueryRenderer q(*renderer, EmitBeginEnd::off);
                RowRenderer r(q);
                for (const auto &column : _columns) {
                    column->output(row, r, _auth_user, _timezone_offset);
                }
            }
            for (const auto &aggr : getAggregatorsFor(RowFragment{os.str()})) {
                aggr->consume(row, _auth_user, timezoneOffset());
            }
        } else {
            RowRenderer r(*_renderer_query);
            for (const auto &column : _columns) {
                column->output(row, r, _auth_user, _timezone_offset);
            }
        }
    }
    return true;
}

void Query::finish(QueryRenderer &q) {
    if (doStats()) {
        for (const auto &group : _stats_groups) {
            RowRenderer r(q);
            if (!group.first._str.empty()) {
                r.output(group.first);
            }
            for (const auto &aggr : group.second) {
                aggr->output(r);
            }
        }
    }
}

const std::string *Query::findValueForIndexing(
    const std::string &column_name) const {
    return _filter->findValueForIndexing(column_name);
}

void Query::findIntLimits(const std::string &column_name, int *lower,
                          int *upper) const {
    return _filter->findIntLimits(column_name, lower, upper, timezoneOffset());
}

void Query::optimizeBitmask(const std::string &column_name,
                            uint32_t *bitmask) const {
    _filter->optimizeBitmask(column_name, bitmask, timezoneOffset());
}

const std::vector<std::unique_ptr<Aggregator>> &Query::getAggregatorsFor(
    const RowFragment &groupspec) {
    auto it = _stats_groups.find(groupspec);
    if (it == _stats_groups.end()) {
        std::vector<std::unique_ptr<Aggregator>> aggrs;
        for (const auto &sc : _stats_columns) {
            aggrs.push_back(sc->createAggregator(_logger));
        }
        it = _stats_groups.emplace(groupspec, move(aggrs)).first;
    }
    return it->second;
}

void Query::doWait() {
    _table->core()->triggers().wait_for(_wait_trigger, _wait_timeout, [this] {
        return _wait_condition->accepts(_wait_object, _auth_user,
                                        timezoneOffset());
    });
}
