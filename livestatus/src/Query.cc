// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "Query.h"

#include <algorithm>
#include <cassert>
#include <cctype>
#include <cmath>
#include <cstdlib>
#include <memory>
#include <ratio>
#include <sstream>
#include <stdexcept>
#include <type_traits>

#include "Aggregator.h"
#include "AndingFilter.h"
#include "ChronoUtils.h"
#include "Column.h"
#include "Logger.h"
#include "MonitoringCore.h"
#include "NullColumn.h"
#include "OringFilter.h"
#include "OutputBuffer.h"
#include "StringUtils.h"
#include "Table.h"
#include "auth.h"
#include "opids.h"
#include "strutil.h"

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

Query::Query(const std::list<std::string> &lines, Table &table,
             Encoding data_encoding, size_t max_response_size,
             ServiceAuthorization service_auth, GroupAuthorization group_auth,
             OutputBuffer &output, Logger *logger)
    : _data_encoding(data_encoding)
    , _max_response_size(max_response_size)
    , _output(output)
    , _renderer_query(nullptr)
    , _table(table)
    , _keepalive(false)
    , _auth_user(no_auth_user())
    , _wait_timeout(0)
    , _wait_trigger(Triggers::Kind::all)
    , _wait_object(nullptr)
    , _separators("\n", ";", ",", "|")
    , _show_column_headers(true)
    , _output_format(OutputFormat::broken_csv)
    , _limit(-1)
    , _current_line(0)
    , _timezone_offset(0)
    , _logger(logger)
    , service_auth_{service_auth}
    , group_auth_{group_auth} {
    FilterStack filters;
    FilterStack wait_conditions;
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
        char *arguments = &rest_copy[0];
        try {
            if (header == "Filter") {
                parseFilterLine(arguments, filters);
            } else if (header == "Or") {
                parseAndOrLine(arguments, Filter::Kind::row, OringFilter::make,
                               filters);
            } else if (header == "And") {
                parseAndOrLine(arguments, Filter::Kind::row, AndingFilter::make,
                               filters);
            } else if (header == "Negate") {
                parseNegateLine(arguments, filters);
            } else if (header == "StatsOr") {
                parseStatsAndOrLine(arguments, OringFilter::make);
            } else if (header == "StatsAnd") {
                parseStatsAndOrLine(arguments, AndingFilter::make);
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
                parseAndOrLine(arguments, Filter::Kind::wait_condition,
                               AndingFilter::make, wait_conditions);
            } else if (header == "WaitConditionOr") {
                parseAndOrLine(arguments, Filter::Kind::wait_condition,
                               OringFilter::make, wait_conditions);
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
            _output.setError(OutputBuffer::ResponseCode::bad_request,
                             header + ": " + e.what());
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
}

void Query::invalidRequest(const std::string &message) const {
    _output.setError(OutputBuffer::ResponseCode::invalid_request, message);
}

void Query::badGateway(const std::string &message) const {
    _output.setError(OutputBuffer::ResponseCode::bad_gateaway, message);
}

void Query::parseAndOrLine(char *line, Filter::Kind kind,
                           const LogicalConnective &connective,
                           FilterStack &filters) {
    auto number = nextNonNegativeIntegerArgument(&line);
    Filters subfilters;
    for (auto i = 0; i < number; ++i) {
        if (filters.empty()) {
            throw std::runtime_error(
                "error combining filters for table '" + _table.name() +
                "': expected " + std::to_string(number) +
                " filters, but only " + std::to_string(i) + " " +
                (i == 1 ? "is" : "are") + " on stack");
        }
        subfilters.push_back(std::move(filters.back()));
        filters.pop_back();
    }
    std::reverse(subfilters.begin(), subfilters.end());
    filters.push_back(connective(kind, subfilters));
}

void Query::parseNegateLine(char *line, FilterStack &filters) {
    checkNoArguments(line);
    if (filters.empty()) {
        throw std::runtime_error(
            "error combining filters for table '" + _table.name() +
            "': expected 1 filters, but only 0 are on stack");
    }

    auto top = std::move(filters.back());
    filters.pop_back();
    filters.push_back(top->negate());
}

void Query::parseStatsAndOrLine(char *line,
                                const LogicalConnective &connective) {
    auto number = nextNonNegativeIntegerArgument(&line);
    Filters subfilters;
    for (auto i = 0; i < number; ++i) {
        if (_stats_columns.empty()) {
            throw std::runtime_error(
                "error combining filters for table '" + _table.name() +
                "': expected " + std::to_string(number) +
                " filters, but only " + std::to_string(i) + " " +
                (i == 1 ? "is" : "are") + " on stack");
        }
        subfilters.push_back(_stats_columns.back()->stealFilter());
        _stats_columns.pop_back();
    }
    std::reverse(subfilters.begin(), subfilters.end());
    _stats_columns.push_back(std::make_unique<StatsColumnCount>(
        connective(Filter::Kind::stats, subfilters)));
}

void Query::parseStatsNegateLine(char *line) {
    checkNoArguments(line);
    if (_stats_columns.empty()) {
        throw std::runtime_error(
            "error combining filters for table '" + _table.name() +
            "': expected 1 filters, but only 0 are on stack");
    }
    auto to_negate = _stats_columns.back()->stealFilter();
    _stats_columns.pop_back();
    _stats_columns.push_back(
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

void Query::parseStatsLine(char *line) {
    // first token is either aggregation operator or column name
    std::shared_ptr<Column> column;
    std::unique_ptr<StatsColumn> sc;
    auto col_or_op = nextStringArgument(&line);
    auto it = stats_ops.find(col_or_op);
    if (it == stats_ops.end()) {
        column = _table.column(col_or_op);
        auto rel_op = relationalOperatorForName(nextStringArgument(&line));
        auto operand = mk::lstrip(line);
        sc = std::make_unique<StatsColumnCount>(
            column->createFilter(Filter::Kind::stats, rel_op, operand));
    } else {
        column = _table.column(nextStringArgument(&line));
        sc = std::make_unique<StatsColumnOp>(it->second, column.get());
    }
    _stats_columns.push_back(std::move(sc));
    _all_columns.insert(column);
    // Default to old behaviour: do not output column headers if we do Stats
    // queries
    _show_column_headers = false;
}

void Query::parseFilterLine(char *line, FilterStack &filters) {
    auto column = _table.column(nextStringArgument(&line));
    auto rel_op = relationalOperatorForName(nextStringArgument(&line));
    auto operand = mk::lstrip(line);
    auto sub_filter = column->createFilter(Filter::Kind::row, rel_op, operand);
    filters.push_back(std::move(sub_filter));
    _all_columns.insert(column);
}

void Query::parseAuthUserHeader(const char *line) {
    // TODO(sp): Remove ugly cast.
    _auth_user =
        reinterpret_cast<const contact *>(_table.core()->find_contact(line));
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

void Query::parseColumnsLine(const char *line) {
    std::string str = line;
    std::string sep = " \t\n\v\f\r";
    for (auto pos = str.find_first_not_of(sep); pos != std::string::npos;) {
        auto space = str.find_first_of(sep, pos);
        auto column_name =
            str.substr(pos, space - (space == std::string::npos ? 0 : pos));
        pos = str.find_first_not_of(sep, space);
        std::shared_ptr<Column> column;
        try {
            column = _table.column(column_name);
        } catch (const std::runtime_error &e) {
            // Do not fail any longer. We might want to make this configurable.
            // But not failing has the advantage that an updated GUI, that
            // expects new columns, will be able to keep compatibility with
            // older Livestatus versions.
            Informational(_logger)
                << "replacing non-existing column '" << column_name
                << "' with null column, reason: " << e.what();
            column = std::make_shared<NullColumn>(
                column_name, "non-existing column", ColumnOffsets{});
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
const std::map<std::string, OutputFormat> formats{
    {"CSV", OutputFormat::csv},
    {"csv", OutputFormat::broken_csv},
    {"json", OutputFormat::json},
    {"python", OutputFormat::python},
    {"python3", OutputFormat::python3}};
}  // namespace

void Query::parseOutputFormatLine(const char *line) {
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
    auto duration = std::chrono::seconds{nextNonNegativeIntegerArgument(&line)};
    _time_limit = {duration, std::chrono::steady_clock::now() + duration};
}

void Query::parseWaitTimeoutLine(char *line) {
    _wait_timeout =
        std::chrono::milliseconds(nextNonNegativeIntegerArgument(&line));
}

void Query::parseWaitTriggerLine(char *line) {
    _wait_trigger = Triggers::find(nextStringArgument(&line));
}

void Query::parseWaitObjectLine(const char *line) {
    auto primary_key = mk::lstrip(line);
    _wait_object = _table.get(primary_key);
    if (_wait_object.isNull()) {
        throw std::runtime_error("primary key '" + primary_key +
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
    auto rounded = half_an_hour(round(mk::ticks<half_an_hour>(diff)));
    auto offset = std::chrono::duration_cast<std::chrono::seconds>(rounded);
    if (std::chrono::abs(offset) >= 24h) {
        throw std::runtime_error(
            "timezone difference greater than or equal to 24 hours");
    }

    if (offset != 0s) {
        using hour = std::chrono::duration<double, std::ratio<3600>>;
        Debug(_logger) << "timezone offset is " << mk::ticks<hour>(offset)
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
    // TODO(sp) The construct below is horrible, refactor this!
    _renderer_query = &q;
    start(q);
    _table.answerQuery(this, User{_auth_user, service_auth_, group_auth_});
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

    if (!_filter->accepts(row, _auth_user, _timezone_offset)) {
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
                column->output(row, r, _auth_user, _timezone_offset);
            }
        }
        for (const auto &aggr : getAggregatorsFor(RowFragment{os.str()})) {
            aggr->consume(row, _auth_user, timezoneOffset());
        }
    } else {
        assert(_renderer_query);  // Missing call to `process()`.
        RowRenderer r(*_renderer_query);
        for (const auto &column : _columns) {
            column->output(row, r, _auth_user, _timezone_offset);
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
        for (const auto &sc : _stats_columns) {
            aggrs.push_back(sc->createAggregator(_logger));
        }
        it = _stats_groups.emplace(groupspec, move(aggrs)).first;
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
        return _wait_condition->accepts(_wait_object, _auth_user,
                                        timezoneOffset());
    });
}
