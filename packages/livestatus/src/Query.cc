// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/Query.h"

#include <algorithm>
#include <cassert>
#include <cctype>
#include <cmath>
#include <cstdlib>
#include <ratio>
#include <sstream>
#include <stdexcept>
#include <type_traits>

#include "livestatus/AndingFilter.h"
#include "livestatus/ChronoUtils.h"
#include "livestatus/Column.h"
#include "livestatus/ICore.h"
#include "livestatus/Logger.h"
#include "livestatus/NullColumn.h"
#include "livestatus/OringFilter.h"
#include "livestatus/StringUtils.h"
#include "livestatus/Table.h"
#include "livestatus/opids.h"
#include "livestatus/strutil.h"

using namespace std::chrono_literals;

namespace {
std::string nextStringArgument(char **line) {
    if (auto *value = next_field(line)) {
        return value;
    }
    throw std::runtime_error("missing argument");
}

int nextNonNegativeIntegerArgument(char **line) {
    auto value = nextStringArgument(line);
    const int number = atoi(value.c_str());
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

Query::Query(const std::list<std::string> &lines, Table &table,
             Encoding data_encoding, size_t max_response_size,
             OutputBuffer &output, Logger *logger)
    : _data_encoding(data_encoding)
    , _max_response_size(max_response_size)
    , _output(output)
    , _renderer_query(nullptr)
    , _table(table)
    , _keepalive(false)
    , user_{std::make_unique<NoAuthUser>()}
    , _wait_timeout(0)
    , _wait_trigger(Triggers::Kind::all)
    , _wait_object(nullptr)
    , _separators("\n", ";", ",", "|")
    , _show_column_headers(true)
    , _output_format(OutputFormat::broken_csv)
    , _limit(-1)
    , _current_line(0)
    , _timezone_offset(0)
    , _logger(logger) {
    FilterStack filters;
    FilterStack wait_conditions;
    auto make_column = [&table](const std::string &colname) {
        return table.column(colname);
    };
    auto find_user = [&table](const std::string &name) {
        return table.core()->find_user(name);
    };
    auto get = [&table](const std::string &primary_key) {
        return table.get(primary_key);
    };
    auto response_header{OutputBuffer::ResponseHeader::off};
    for (const auto &line : lines) {
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
        char *arguments = rest_copy.data();
        try {
            if (header == "Filter") {
                parseFilterLine(arguments, filters, _all_columns, make_column);
            } else if (header == "Or") {
                parseAndOrLine(arguments, Filter::Kind::row, OringFilter::make,
                               filters);
            } else if (header == "And") {
                parseAndOrLine(arguments, Filter::Kind::row, AndingFilter::make,
                               filters);
            } else if (header == "Negate") {
                parseNegateLine(arguments, filters);
            } else if (header == "StatsOr") {
                parseStatsAndOrLine(arguments, OringFilter::make,
                                    _stats_columns);
            } else if (header == "StatsAnd") {
                parseStatsAndOrLine(arguments, AndingFilter::make,
                                    _stats_columns);
            } else if (header == "StatsNegate") {
                parseStatsNegateLine(arguments, _stats_columns);
            } else if (header == "Stats") {
                parseStatsLine(arguments, _stats_columns, _all_columns,
                               make_column, _show_column_headers);
            } else if (header == "StatsGroupBy") {
                Warning(_logger)
                    << "Warning: StatsGroupBy is deprecated. Please use Columns instead.";
                parseColumnsLine(arguments, _all_columns, make_column,
                                 _show_column_headers, _columns, _logger);
            } else if (header == "Columns") {
                parseColumnsLine(arguments, _all_columns, make_column,
                                 _show_column_headers, _columns, _logger);
            } else if (header == "ColumnHeaders") {
                parseColumnHeadersLine(arguments, _show_column_headers);
            } else if (header == "Limit") {
                parseLimitLine(arguments, _limit);
            } else if (header == "Timelimit") {
                parseTimelimitLine(arguments, _time_limit);
            } else if (header == "AuthUser") {
                parseAuthUserHeader(arguments, find_user, user_);
            } else if (header == "Separators") {
                parseSeparatorsLine(arguments, _separators);
            } else if (header == "OutputFormat") {
                parseOutputFormatLine(arguments, _output_format);
            } else if (header == "ResponseHeader") {
                parseResponseHeaderLine(arguments, response_header);
            } else if (header == "KeepAlive") {
                parseKeepAliveLine(arguments, _keepalive);
            } else if (header == "WaitCondition") {
                parseFilterLine(arguments, wait_conditions, _all_columns,
                                make_column);
            } else if (header == "WaitConditionAnd") {
                parseAndOrLine(arguments, Filter::Kind::wait_condition,
                               AndingFilter::make, wait_conditions);
            } else if (header == "WaitConditionOr") {
                parseAndOrLine(arguments, Filter::Kind::wait_condition,
                               OringFilter::make, wait_conditions);
            } else if (header == "WaitConditionNegate") {
                parseNegateLine(arguments, wait_conditions);
            } else if (header == "WaitTrigger") {
                parseWaitTriggerLine(arguments, _wait_trigger);
            } else if (header == "WaitObject") {
                parseWaitObjectLine(arguments, get, _wait_object);
            } else if (header == "WaitTimeout") {
                parseWaitTimeoutLine(arguments, _wait_timeout);
            } else if (header == "Localtime") {
                parseLocaltimeLine(arguments, _timezone_offset, _logger);
            } else {
                throw std::runtime_error("undefined request header");
            }
        } catch (const std::runtime_error &e) {
            _output.setError(OutputBuffer::ResponseCode::bad_request,
                             "while processing header '" + header +
                                 "' for table '" + _table.name() +
                                 "': " + e.what());
        }
    }

    if (_columns.empty() && !doStats()) {
        table.any_column([this](const auto &c) {
            return _columns.push_back(c), _all_columns.insert(c), false;
        });
        // TODO(sp) We overwrite the value from a possible ColumnHeaders: line
        // here, is that really what we want?
        _show_column_headers = true;
    }

    _filter = AndingFilter::make(Filter::Kind::row, filters);
    _wait_condition =
        AndingFilter::make(Filter::Kind ::wait_condition, wait_conditions);
    _output.setResponseHeader(response_header);
}

void Query::invalidRequest(const std::string &message) const {
    _output.setError(OutputBuffer::ResponseCode::invalid_request, message);
}

void Query::badGateway(const std::string &message) const {
    _output.setError(OutputBuffer::ResponseCode::bad_gateaway, message);
}

namespace {
[[noreturn]] void stack_underflow(int expected, int actual) {
    throw std::runtime_error("cannot combine filters: expecting " +
                             std::to_string(expected) + " " +
                             (expected == 1 ? "filter" : "filters") +
                             ", but only " + std::to_string(actual) + " " +
                             (actual == 1 ? "is" : "are") + " on stack");
}
}  // namespace

// static
void Query::parseAndOrLine(char *line, Filter::Kind kind,
                           const LogicalConnective &connective,
                           FilterStack &filters) {
    auto number = nextNonNegativeIntegerArgument(&line);
    Filters subfilters;
    for (auto i = 0; i < number; ++i) {
        if (filters.empty()) {
            stack_underflow(number, i);
        }
        subfilters.push_back(std::move(filters.back()));
        filters.pop_back();
    }
    std::reverse(subfilters.begin(), subfilters.end());
    filters.push_back(connective(kind, subfilters));
}

// static
void Query::parseNegateLine(char *line, FilterStack &filters) {
    checkNoArguments(line);
    if (filters.empty()) {
        stack_underflow(1, 0);
    }
    auto top = std::move(filters.back());
    filters.pop_back();
    filters.push_back(top->negate());
}

// static
void Query::parseStatsAndOrLine(char *line, const LogicalConnective &connective,
                                StatsColumns &stats_columns) {
    auto number = nextNonNegativeIntegerArgument(&line);
    Filters subfilters;
    for (auto i = 0; i < number; ++i) {
        if (stats_columns.empty()) {
            stack_underflow(number, i);
        }
        subfilters.push_back(stats_columns.back()->stealFilter());
        stats_columns.pop_back();
    }
    std::reverse(subfilters.begin(), subfilters.end());
    stats_columns.push_back(std::make_unique<StatsColumnCount>(
        connective(Filter::Kind::stats, subfilters)));
}

// static
void Query::parseStatsNegateLine(char *line, StatsColumns &stats_columns) {
    checkNoArguments(line);
    if (stats_columns.empty()) {
        stack_underflow(1, 0);
    }
    auto to_negate = stats_columns.back()->stealFilter();
    stats_columns.pop_back();
    stats_columns.push_back(
        std::make_unique<StatsColumnCount>(to_negate->negate()));
}

namespace {
class SumAggregation : public Aggregation {
public:
    void update(double value) override { sum_ += value; }
    [[nodiscard]] double value() const override { return sum_; }

private:
    double sum_{0};
};

class MinAggregation : public Aggregation {
public:
    void update(double value) override {
        if (first_ || value < sum_) {
            sum_ = value;
        }
        first_ = false;
    }

    [[nodiscard]] double value() const override { return sum_; }

private:
    bool first_{true};
    // NOTE: This default is wrong, the neutral element for min is +Inf. Apart
    // from being more consistent, using it would remove the need for first_.
    double sum_{0};
};

class MaxAggregation : public Aggregation {
public:
    void update(double value) override {
        if (first_ || value > sum_) {
            sum_ = value;
        }
        first_ = false;
    }

    [[nodiscard]] double value() const override { return sum_; }

private:
    bool first_{true};
    // NOTE: This default is wrong, the neutral element for max is -Inf. Apart
    // from being more consistent, using it would remove the need for first_.
    double sum_{0};
};

class AvgAggregation : public Aggregation {
public:
    void update(double value) override {
        count_++;
        sum_ += value;
    }

    [[nodiscard]] double value() const override { return sum_ / count_; }

private:
    std::uint32_t count_{0};
    double sum_{0};
};

class StdAggregation : public Aggregation {
public:
    void update(double value) override {
        count_++;
        sum_ += value;
        sum_of_squares_ += value * value;
    }

    [[nodiscard]] double value() const override {
        auto mean = sum_ / count_;
        return sqrt(sum_of_squares_ / count_ - mean * mean);
    }

private:
    std::uint32_t count_{0};
    double sum_{0};
    double sum_of_squares_{0};
};

class SumInvAggregation : public Aggregation {
public:
    void update(double value) override { sum_ += 1.0 / value; }
    [[nodiscard]] double value() const override { return sum_; }

private:
    double sum_{0};
};

class AvgInvAggregation : public Aggregation {
public:
    void update(double value) override {
        count_++;
        sum_ += 1.0 / value;
    }

    [[nodiscard]] double value() const override { return sum_ / count_; }

private:
    std::uint32_t count_{0};
    double sum_{0};
};

const std::map<std::string, AggregationFactory> stats_ops{
    {"sum", []() { return std::make_unique<SumAggregation>(); }},
    {"min", []() { return std::make_unique<MinAggregation>(); }},
    {"max", []() { return std::make_unique<MaxAggregation>(); }},
    {"avg", []() { return std::make_unique<AvgAggregation>(); }},
    {"std", []() { return std::make_unique<StdAggregation>(); }},
    {"suminv", []() { return std::make_unique<SumInvAggregation>(); }},
    {"avginv", []() { return std::make_unique<AvgInvAggregation>(); }}};
}  // namespace

// static
void Query::parseStatsLine(char *line, StatsColumns &stats_columns,
                           ColumnSet &all_columns,
                           const ColumnCreator &make_column,
                           bool &show_column_headers) {
    // first token is either aggregation operator or column name
    std::shared_ptr<Column> column;
    std::unique_ptr<StatsColumn> sc;
    auto col_or_op = nextStringArgument(&line);
    auto it = stats_ops.find(col_or_op);
    if (it == stats_ops.end()) {
        column = make_column(col_or_op);
        auto rel_op = relationalOperatorForName(nextStringArgument(&line));
        auto operand = mk::lstrip(line);
        sc = std::make_unique<StatsColumnCount>(
            column->createFilter(Filter::Kind::stats, rel_op, operand));
    } else {
        column = make_column(nextStringArgument(&line));
        sc = std::make_unique<StatsColumnOp>(it->second, column.get());
    }
    stats_columns.push_back(std::move(sc));
    all_columns.insert(column);
    // Default to old behaviour: do not output column headers if we do Stats
    // queries
    show_column_headers = false;
}

// static
void Query::parseFilterLine(char *line, FilterStack &filters,
                            ColumnSet &all_columns,
                            const ColumnCreator &make_column) {
    auto column = make_column(nextStringArgument(&line));
    auto rel_op = relationalOperatorForName(nextStringArgument(&line));
    auto operand = mk::lstrip(line);
    auto sub_filter = column->createFilter(Filter::Kind::row, rel_op, operand);
    filters.push_back(std::move(sub_filter));
    all_columns.insert(column);
}

// static
void Query::parseAuthUserHeader(
    const char *line,
    const std::function<std::unique_ptr<const User>(const std::string &)>
        &find_user,
    std::unique_ptr<const User> &user) {
    user = find_user(line);
}

// static
void Query::parseColumnsLine(const char *line, ColumnSet &all_columns,
                             const ColumnCreator &make_column,
                             bool &show_column_headers, Columns &columns,
                             Logger *logger) {
    const std::string str = line;
    const std::string sep = " \t\n\v\f\r";
    for (auto pos = str.find_first_not_of(sep); pos != std::string::npos;) {
        auto space = str.find_first_of(sep, pos);
        auto column_name =
            str.substr(pos, space - (space == std::string::npos ? 0 : pos));
        pos = str.find_first_not_of(sep, space);
        std::shared_ptr<Column> column;
        try {
            column = make_column(column_name);
        } catch (const std::runtime_error &e) {
            // Do not fail any longer. We might want to make this configurable.
            // But not failing has the advantage that an updated GUI, that
            // expects new columns, will be able to keep compatibility with
            // older Livestatus versions.
            Informational(logger)
                << "replacing non-existing column '" << column_name
                << "' with null column, reason: " << e.what();
            column = std::make_shared<NullColumn>(
                column_name, "non-existing column", ColumnOffsets{});
        }
        columns.push_back(column);
        all_columns.insert(column);
    }
    show_column_headers = false;
}

// static
void Query::parseSeparatorsLine(char *line, CSVSeparators &separators) {
    const std::string dsep = std::string(
        1, static_cast<char>(nextNonNegativeIntegerArgument(&line)));
    const std::string fsep = std::string(
        1, static_cast<char>(nextNonNegativeIntegerArgument(&line)));
    const std::string lsep = std::string(
        1, static_cast<char>(nextNonNegativeIntegerArgument(&line)));
    const std::string hsep = std::string(
        1, static_cast<char>(nextNonNegativeIntegerArgument(&line)));
    separators = CSVSeparators(dsep, fsep, lsep, hsep);
}

namespace {
const std::map<std::string, OutputFormat> formats{
    {"CSV", OutputFormat::csv},
    {"csv", OutputFormat::broken_csv},
    {"json", OutputFormat::json},
    {"python", OutputFormat::python3},  // just an alias, deprecate?
    {"python3", OutputFormat::python3}};
}  // namespace

// static
void Query::parseOutputFormatLine(const char *line,
                                  OutputFormat &output_format) {
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
    output_format = it->second;
}

// static
void Query::parseColumnHeadersLine(char *line, bool &show_column_headers) {
    auto value = nextStringArgument(&line);
    if (value == "on") {
        show_column_headers = true;
    } else if (value == "off") {
        show_column_headers = false;
    } else {
        throw std::runtime_error("expected 'on' or 'off'");
    }
}

// static
void Query::parseKeepAliveLine(char *line, bool &keepalive) {
    auto value = nextStringArgument(&line);
    if (value == "on") {
        keepalive = true;
    } else if (value == "off") {
        keepalive = false;
    } else {
        throw std::runtime_error("expected 'on' or 'off'");
    }
}

// static
void Query::parseResponseHeaderLine(
    char *line, OutputBuffer::ResponseHeader &response_header) {
    auto value = nextStringArgument(&line);
    if (value == "off") {
        response_header = OutputBuffer::ResponseHeader::off;
    } else if (value == "fixed16") {
        response_header = OutputBuffer::ResponseHeader::fixed16;
    } else {
        throw std::runtime_error("expected 'off' or 'fixed16'");
    }
}

// static
void Query::parseLimitLine(char *line, int &limit) {
    limit = nextNonNegativeIntegerArgument(&line);
}

// static
void Query::parseTimelimitLine(
    char *line,
    std::optional<
        std::pair<std::chrono::seconds, std::chrono::steady_clock::time_point>>
        &time_limit) {
    auto duration = std::chrono::seconds{nextNonNegativeIntegerArgument(&line)};
    time_limit = {duration, std::chrono::steady_clock::now() + duration};
}

// static
void Query::parseWaitTimeoutLine(char *line,
                                 std::chrono::milliseconds &wait_timeout) {
    wait_timeout =
        std::chrono::milliseconds(nextNonNegativeIntegerArgument(&line));
}

// static
void Query::parseWaitTriggerLine(char *line, Triggers::Kind &wait_trigger) {
    wait_trigger = Triggers::find(nextStringArgument(&line));
}

// static
void Query::parseWaitObjectLine(
    const char *line, const std::function<Row(const std::string &)> &get,
    Row &wait_object) {
    auto primary_key = mk::lstrip(line);
    wait_object = get(primary_key);
    if (wait_object.isNull()) {
        throw std::runtime_error("primary key '" + primary_key +
                                 "' not found or not supported by this table");
    }
}

// static
void Query::parseLocaltimeLine(char *line,
                               std::chrono::seconds &timezone_offset,
                               Logger *logger) {
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
    auto rounded = half_an_hour(round(mk::ticks<half_an_hour>(diff)));
    auto offset = std::chrono::duration_cast<std::chrono::seconds>(rounded);
    if (std::chrono::abs(offset) >= 24h) {
        throw std::runtime_error(
            "timezone difference greater than or equal to 24 hours");
    }

    if (offset != 0s) {
        using hour = std::chrono::duration<double, std::ratio<3600>>;
        Debug(logger) << "timezone offset is " << mk::ticks<hour>(offset)
                      << "h";
    }
    timezone_offset = offset;
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
    // TODO(sp) The construct below is horrible, refactor this!
    _renderer_query = &q;
    start(q);
    _table.answerQuery(*this, *user_);
    finish(q);
    auto elapsed_ms = mk::ticks<std::chrono::milliseconds>(
        std::chrono::system_clock::now() - start_time);
    Informational(_logger) << "processed request in " << elapsed_ms
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
            r.output("stats_" + std::to_string(col));
        }
    }
}

bool Query::timelimitReached() const {
    if (!_time_limit) {
        return false;
    }
    const auto &[duration, timeout] = *_time_limit;
    if (std::chrono::steady_clock::now() >= timeout) {
        _output.setError(
            OutputBuffer::ResponseCode::payload_too_large,
            "Maximum query time of " +
                std::to_string(mk::ticks<std::chrono::seconds>(duration)) +
                " seconds exceeded!");
        return true;
    }
    return false;
}

bool Query::processDataset(Row row) {
    if (_output.shouldTerminate()) {
        // Not the perfect response code, but good enough...
        _output.setError(OutputBuffer::ResponseCode::payload_too_large,
                         "core is shutting down");
        return false;
    }

    if (static_cast<size_t>(_output.os().tellp()) > _max_response_size) {
        _output.setError(OutputBuffer::ResponseCode::payload_too_large,
                         "Maximum response size of " +
                             std::to_string(_max_response_size) +
                             " bytes exceeded!");
        return false;
    }

    if (!_filter->accepts(row, *user_, _timezone_offset)) {
        return true;
    }

    _current_line++;
    if (_limit >= 0 && static_cast<int>(_current_line) > _limit) {
        return false;
    }

    // When we reach the time limit we let the query fail. Otherwise the user
    // will not know that the answer is incomplete.
    if (timelimitReached()) {
        return false;
    }

    if (doStats()) {
        // Things get a bit tricky here: For stats queries, we have to combine
        // rows with the same values in the non-stats columns. But when we
        // finally output those non-stats columns in finish(), we don't have the
        // row anymore, so we can't use Column::output() then.  :-/ The slightly
        // hacky workaround is to pre-render all non-stats columns into a single
        // string here (RowFragment) and output it later in a verbatim manner.
        std::ostringstream os;
        {
            auto renderer =
                Renderer::make(_output_format, os, _output.getLogger(),
                               _separators, _data_encoding);
            QueryRenderer q(*renderer, EmitBeginEnd::off);
            RowRenderer r(q);
            for (const auto &column : _columns) {
                column->output(row, r, *user_, _timezone_offset);
            }
        }
        for (const auto &aggr : getAggregatorsFor(RowFragment{os.str()})) {
            aggr->consume(row, *user_, timezoneOffset());
        }
    } else {
        assert(_renderer_query);  // Missing call to `process()`.
        RowRenderer r(*_renderer_query);
        for (const auto &column : _columns) {
            column->output(row, r, *user_, _timezone_offset);
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

std::unique_ptr<Filter> Query::partialFilter(
    const std::string &message, columnNamePredicate predicate) const {
    auto result = _filter->partialFilter(std::move(predicate));
    Debug(_logger) << "partial filter for " << message << ": " << *result;
    return result;
}

std::optional<std::string> Query::stringValueRestrictionFor(
    const std::string &column_name) const {
    auto result = _filter->stringValueRestrictionFor(column_name);
    if (result) {
        Debug(_logger) << "column " << _table.name() << "." << column_name
                       << " is restricted to '" << *result << "'";
    } else {
        Debug(_logger) << "column " << _table.name() << "." << column_name
                       << " is unrestricted";
    }
    return result;
}

std::optional<int32_t> Query::greatestLowerBoundFor(
    const std::string &column_name) const {
    auto result = _filter->greatestLowerBoundFor(column_name, timezoneOffset());
    if (result) {
        Debug(_logger) << "column " << _table.name() << "." << column_name
                       << " has greatest lower bound " << *result << " ("
                       << FormattedTimePoint(
                              std::chrono::system_clock::from_time_t(*result))
                       << ")";
    } else {
        Debug(_logger) << "column " << _table.name() << "." << column_name
                       << " has no greatest lower bound";
    }
    return result;
}

std::optional<int32_t> Query::leastUpperBoundFor(
    const std::string &column_name) const {
    auto result = _filter->leastUpperBoundFor(column_name, timezoneOffset());
    if (result) {
        Debug(_logger) << "column " << _table.name() << "." << column_name
                       << " has least upper bound " << *result << " ("
                       << FormattedTimePoint(
                              std::chrono::system_clock::from_time_t(*result))
                       << ")";
    } else {
        Debug(_logger) << "column " << _table.name() << "." << column_name
                       << " has no least upper bound";
    }
    return result;
}

std::optional<std::bitset<32>> Query::valueSetLeastUpperBoundFor(
    const std::string &column_name) const {
    auto result =
        _filter->valueSetLeastUpperBoundFor(column_name, timezoneOffset());
    if (result) {
        Debug(_logger) << "column " << _table.name() << "." << column_name
                       << " has possible values "
                       << FormattedBitSet<32>{*result};
    } else {
        Debug(_logger) << "column " << _table.name() << "." << column_name
                       << " has no value set restriction";
    }
    return result;
}

const std::vector<std::unique_ptr<Aggregator>> &Query::getAggregatorsFor(
    const RowFragment &groupspec) {
    auto it = _stats_groups.find(groupspec);
    if (it == _stats_groups.end()) {
        std::vector<std::unique_ptr<Aggregator>> aggrs;
        aggrs.reserve(_stats_columns.size());
        for (const auto &sc : _stats_columns) {
            aggrs.push_back(sc->createAggregator(_logger));
        }
        it = _stats_groups.emplace(groupspec, std::move(aggrs)).first;
    }
    return it->second;
}

void Query::doWait() {
    if (_wait_condition->is_contradiction() && _wait_timeout == 0ms) {
        invalidRequest("waiting for WaitCondition would hang forever");
        return;
    }
    if (!_wait_condition->is_tautology() && _wait_object.isNull()) {
        _wait_object = _table.getDefault();
        if (_wait_object.isNull()) {
            invalidRequest("missing WaitObject");
            return;
        }
    }
    _table.core()->triggers().wait_for(_wait_trigger, _wait_timeout, [this] {
        return _wait_condition->accepts(_wait_object, *user_, timezoneOffset());
    });
}
