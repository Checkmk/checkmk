// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/ParsedQuery.h"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <compare>
#include <cstdint>
#include <cstdlib>
#include <map>
#include <ratio>
#include <stdexcept>

#include "livestatus/Aggregator.h"
#include "livestatus/AndingFilter.h"
#include "livestatus/ChronoUtils.h"
#include "livestatus/Column.h"
#include "livestatus/ICore.h"
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

ParsedQuery::ParsedQuery(const std::list<std::string> &lines,
                         const Table &table, OutputBuffer &output)
    : user{std::make_unique<NoAuthUser>()} {
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
                parseFilterLine(arguments, filters, make_column);
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
                parseStatsLine(arguments, make_column);
            } else if (header == "Columns") {
                parseColumnsLine(arguments, make_column);
            } else if (header == "ColumnHeaders") {
                parseColumnHeadersLine(arguments);
            } else if (header == "Limit") {
                parseLimitLine(arguments);
            } else if (header == "Timelimit") {
                parseTimelimitLine(arguments);
            } else if (header == "AuthUser") {
                parseAuthUserHeader(arguments, find_user);
            } else if (header == "Separators") {
                parseSeparatorsLine(arguments);
            } else if (header == "OutputFormat") {
                parseOutputFormatLine(arguments);
            } else if (header == "ResponseHeader") {
                parseResponseHeaderLine(arguments);
            } else if (header == "KeepAlive") {
                parseKeepAliveLine(arguments);
            } else if (header == "WaitCondition") {
                parseFilterLine(arguments, wait_conditions, make_column);
            } else if (header == "WaitConditionAnd") {
                parseAndOrLine(arguments, Filter::Kind::wait_condition,
                               AndingFilter::make, wait_conditions);
            } else if (header == "WaitConditionOr") {
                parseAndOrLine(arguments, Filter::Kind::wait_condition,
                               OringFilter::make, wait_conditions);
            } else if (header == "WaitConditionNegate") {
                ParsedQuery::parseNegateLine(arguments, wait_conditions);
            } else if (header == "WaitTrigger") {
                parseWaitTriggerLine(arguments);
            } else if (header == "WaitObject") {
                parseWaitObjectLine(arguments, get);
            } else if (header == "WaitTimeout") {
                parseWaitTimeoutLine(arguments);
            } else if (header == "Localtime") {
                parseLocaltimeLine(arguments);
            } else {
                throw std::runtime_error("undefined request header");
            }
        } catch (const std::runtime_error &e) {
            output.setError(OutputBuffer::ResponseCode::bad_request,
                            "while processing header '" + header +
                                "' for table '" + table.name() +
                                "': " + e.what());
        }
    }

    if (columns.empty() && stats_columns.empty()) {
        table.any_column([this](const auto &c) {
            return columns.push_back(c), all_column_names.insert(c->name()),
                   false;
        });
        // TODO(sp) We overwrite the value from a possible ColumnHeaders: line
        // here, is that really what we want?
        show_column_headers = true;
    }

    filter = AndingFilter::make(Filter::Kind::row, filters);
    wait_condition =
        AndingFilter::make(Filter::Kind ::wait_condition, wait_conditions);
    output.setResponseHeader(response_header);
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
void ParsedQuery::parseAndOrLine(char *line, Filter::Kind kind,
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
void ParsedQuery::parseNegateLine(char *line, FilterStack &filters) {
    checkNoArguments(line);
    if (filters.empty()) {
        stack_underflow(1, 0);
    }
    auto top = std::move(filters.back());
    filters.pop_back();
    filters.push_back(top->negate());
}

void ParsedQuery::parseStatsAndOrLine(char *line,
                                      const LogicalConnective &connective) {
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

void ParsedQuery::parseStatsNegateLine(char *line) {
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

void ParsedQuery::parseStatsLine(char *line, const ColumnCreator &make_column) {
    // first token is either aggregation operator or column name
    std::string column_name;
    std::unique_ptr<StatsColumn> sc;
    auto col_or_op = nextStringArgument(&line);
    auto it = stats_ops.find(col_or_op);
    if (it == stats_ops.end()) {
        column_name = col_or_op;
        auto rel_op = relationalOperatorForName(nextStringArgument(&line));
        auto operand = mk::lstrip(line);
        sc = std::make_unique<StatsColumnCount>(
            make_column(column_name)
                ->createFilter(Filter::Kind::stats, rel_op, operand));
    } else {
        column_name = nextStringArgument(&line);
        sc = std::make_unique<StatsColumnOp>(it->second,
                                             make_column(column_name));
    }
    stats_columns.push_back(std::move(sc));
    all_column_names.insert(column_name);
    // Default to old behaviour: do not output column headers if we do Stats
    // queries
    show_column_headers = false;
}

void ParsedQuery::parseFilterLine(char *line, FilterStack &filters,
                                  const ColumnCreator &make_column) {
    auto column_name = nextStringArgument(&line);
    auto rel_op = relationalOperatorForName(nextStringArgument(&line));
    auto operand = mk::lstrip(line);
    auto sub_filter = make_column(column_name)
                          ->createFilter(Filter::Kind::row, rel_op, operand);
    filters.push_back(std::move(sub_filter));
    all_column_names.insert(column_name);
}

void ParsedQuery::parseAuthUserHeader(
    const char *line,
    const std::function<std::unique_ptr<const User>(const std::string &)>
        &find_user) {
    user = find_user(line);
}

void ParsedQuery::parseColumnsLine(const char *line,
                                   const ColumnCreator &make_column) {
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
            // TODO(sp): Do we still need this fallback now that we require the
            // remote sites to be updated before the central site? We don't do
            // this for stats/filter lines, either.
            column = std::make_shared<NullColumn>(
                column_name, "non-existing column", ColumnOffsets{});
        }
        columns.push_back(column);
        all_column_names.insert(column_name);
    }
    show_column_headers = false;
}

void ParsedQuery::parseSeparatorsLine(char *line) {
    const std::string dsep = std::string(
        1, static_cast<char>(nextNonNegativeIntegerArgument(&line)));
    const std::string fsep = std::string(
        1, static_cast<char>(nextNonNegativeIntegerArgument(&line)));
    const std::string lsep = std::string(
        1, static_cast<char>(nextNonNegativeIntegerArgument(&line)));
    const std::string hsep = std::string(
        1, static_cast<char>(nextNonNegativeIntegerArgument(&line)));
    separators = CSVSeparators{dsep, fsep, lsep, hsep};
}

namespace {
const std::map<std::string, OutputFormat> formats{
    {"CSV", OutputFormat::csv},
    {"csv", OutputFormat::broken_csv},
    {"json", OutputFormat::json},
    {"python", OutputFormat::python3},  // just an alias, deprecate?
    {"python3", OutputFormat::python3}};
}  // namespace

void ParsedQuery::parseOutputFormatLine(const char *line) {
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

void ParsedQuery::parseColumnHeadersLine(char *line) {
    auto value = nextStringArgument(&line);
    if (value == "on") {
        show_column_headers = true;
    } else if (value == "off") {
        show_column_headers = false;
    } else {
        throw std::runtime_error("expected 'on' or 'off'");
    }
}

void ParsedQuery::parseKeepAliveLine(char *line) {
    auto value = nextStringArgument(&line);
    if (value == "on") {
        keepalive = true;
    } else if (value == "off") {
        keepalive = false;
    } else {
        throw std::runtime_error("expected 'on' or 'off'");
    }
}

void ParsedQuery::parseResponseHeaderLine(char *line) {
    auto value = nextStringArgument(&line);
    if (value == "off") {
        response_header = OutputBuffer::ResponseHeader::off;
    } else if (value == "fixed16") {
        response_header = OutputBuffer::ResponseHeader::fixed16;
    } else {
        throw std::runtime_error("expected 'off' or 'fixed16'");
    }
}

void ParsedQuery::parseLimitLine(char *line) {
    limit = nextNonNegativeIntegerArgument(&line);
}

void ParsedQuery::parseTimelimitLine(char *line) {
    auto duration = std::chrono::seconds{nextNonNegativeIntegerArgument(&line)};
    time_limit = {duration, std::chrono::steady_clock::now() + duration};
}

void ParsedQuery::parseWaitTimeoutLine(char *line) {
    wait_timeout =
        std::chrono::milliseconds(nextNonNegativeIntegerArgument(&line));
}

void ParsedQuery::parseWaitTriggerLine(char *line) {
    wait_trigger = Triggers::find(nextStringArgument(&line));
}

void ParsedQuery::parseWaitObjectLine(
    const char *line, const std::function<Row(const std::string &)> &get) {
    auto primary_key = mk::lstrip(line);
    wait_object = get(primary_key);
    if (wait_object.isNull()) {
        throw std::runtime_error("primary key '" + primary_key +
                                 "' not found or not supported by this table");
    }
}

void ParsedQuery::parseLocaltimeLine(char *line) {
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
    timezone_offset = offset;
}
