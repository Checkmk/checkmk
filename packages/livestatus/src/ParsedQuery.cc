// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/ParsedQuery.h"

#include <algorithm>
#include <charconv>
#include <cmath>
#include <compare>
#include <cstddef>
#include <cstdint>
#include <iterator>
#include <map>
#include <ranges>
#include <ratio>
#include <stdexcept>
#include <system_error>

#include "livestatus/Aggregator.h"
#include "livestatus/AndingFilter.h"
#include "livestatus/Column.h"
#include "livestatus/NullColumn.h"
#include "livestatus/OringFilter.h"
#include "livestatus/StatsColumn.h"
#include "livestatus/StringUtils.h"
#include "livestatus/opids.h"

using namespace std::literals;

namespace {
std::string_view nextStringArgument(std::string_view &str) {
    str.remove_prefix(
        std::min(str.size(), str.find_first_not_of(mk::whitespace)));
    if (str.empty()) {
        throw std::runtime_error("missing argument");
    }
    auto argument = str.substr(0, str.find_first_of(mk::whitespace));
    str.remove_prefix(argument.size());
    return argument;
}

int nextNonNegativeIntegerArgument(std::string_view &str) {
    auto argument = nextStringArgument(str);
    int value{};
    auto [ptr, ec] = std::from_chars(argument.begin(), argument.end(), value);
    if (ec != std::errc{} || ptr != argument.end() || value < 0) {
        throw std::runtime_error("expected non-negative integer");
    }
    return value;
}

void checkNoArguments(std::string_view str) {
    if (!str.empty()) {
        throw std::runtime_error("superfluous argument(s)");
    }
}
}  // namespace

// NOLINTNEXTLINE(readability-function-cognitive-complexity)
ParsedQuery::ParsedQuery(
    const std::vector<std::string> &lines,
    const std::function<std::vector<std::shared_ptr<Column>>()> &all_columns,
    const ColumnCreator &make_column) {
    FilterStack filters;
    FilterStack wait_conditions;
    for (const auto &line_str : lines) {
        std::string_view line{line_str};
        auto header = line.substr(0, line.find(':'));
        line.remove_prefix(std::min(line.size(), header.size() + 1));
        line.remove_prefix(
            std::min(line.size(), line.find_first_not_of(mk::whitespace)));
        try {
            if (header == "Filter"sv) {
                parseFilterLine(line, filters, make_column);
            } else if (header == "Or"sv) {
                parseAndOrLine(line, Filter::Kind::row, OringFilter::make,
                               filters);
            } else if (header == "And"sv) {
                parseAndOrLine(line, Filter::Kind::row, AndingFilter::make,
                               filters);
            } else if (header == "Negate"sv) {
                parseNegateLine(line, filters);
            } else if (header == "StatsOr"sv) {
                parseStatsAndOrLine(line, OringFilter::make);
            } else if (header == "StatsAnd"sv) {
                parseStatsAndOrLine(line, AndingFilter::make);
            } else if (header == "StatsNegate"sv) {
                parseStatsNegateLine(line);
            } else if (header == "Stats"sv) {
                parseStatsLine(line, make_column);
            } else if (header == "Columns"sv) {
                parseColumnsLine(line, make_column);
            } else if (header == "ColumnHeaders"sv) {
                parseColumnHeadersLine(line);
            } else if (header == "Limit"sv) {
                parseLimitLine(line);
            } else if (header == "Timelimit"sv) {
                parseTimelimitLine(line);
            } else if (header == "AuthUser"sv) {
                parseAuthUserHeader(line);
            } else if (header == "Separators"sv) {
                parseSeparatorsLine(line);
            } else if (header == "OutputFormat"sv) {
                parseOutputFormatLine(line);
            } else if (header == "ResponseHeader"sv) {
                parseResponseHeaderLine(line);
            } else if (header == "KeepAlive"sv) {
                parseKeepAliveLine(line);
            } else if (header == "WaitCondition"sv) {
                parseFilterLine(line, wait_conditions, make_column);
            } else if (header == "WaitConditionAnd"sv) {
                parseAndOrLine(line, Filter::Kind::wait_condition,
                               AndingFilter::make, wait_conditions);
            } else if (header == "WaitConditionOr"sv) {
                parseAndOrLine(line, Filter::Kind::wait_condition,
                               OringFilter::make, wait_conditions);
            } else if (header == "WaitConditionNegate"sv) {
                ParsedQuery::parseNegateLine(line, wait_conditions);
            } else if (header == "WaitTrigger"sv) {
                parseWaitTriggerLine(line);
            } else if (header == "WaitObject"sv) {
                parseWaitObjectLine(line);
            } else if (header == "WaitTimeout"sv) {
                parseWaitTimeoutLine(line);
            } else if (header == "Localtime"sv) {
                parseLocaltimeLine(line);
            } else if (header == "OrderBy"sv) {
                parseOrderBy(line, make_column);
            } else {
                throw std::runtime_error("undefined request header");
            }
        } catch (const std::runtime_error &e) {
            if (!error) {
                error = "while processing header '" + std::string{header} +
                        "': "s + e.what();
            }
        }
    }

    if (columns.empty() && stats_columns.empty()) {
        for (const auto &c : all_columns()) {
            columns.push_back(c);
            all_column_names.insert(c->name());
        }
        // TODO(sp) We overwrite the value from a possible ColumnHeaders: line
        // here, is that really what we want?
        show_column_headers = true;
    }

    filter = AndingFilter::make(Filter::Kind::row, filters);
    wait_condition =
        AndingFilter::make(Filter::Kind ::wait_condition, wait_conditions);
}

namespace {
template <typename Stack>
Stack popN(Stack &stack, size_t n) {
    if (stack.size() < n) {
        throw std::runtime_error(
            "cannot combine filters: expecting " + std::to_string(n) + " " +
            (n == 1 ? "filter" : "filters") + ", but only " +
            std::to_string(stack.size()) + " " +
            (stack.size() == 1 ? "is" : "are") + " on stack");
    }
    Stack result;
    std::move(stack.end() - n, stack.end(), std::back_inserter(result));
    stack.erase(stack.end() - n, stack.end());
    return result;
}
}  // namespace

// static
void ParsedQuery::parseAndOrLine(std::string_view line, Filter::Kind kind,
                                 const LogicalConnective &connective,
                                 FilterStack &filters) {
    auto number = nextNonNegativeIntegerArgument(line);
    filters.push_back(connective(kind, popN(filters, number)));
}

// static
void ParsedQuery::parseNegateLine(std::string_view line, FilterStack &filters) {
    checkNoArguments(line);
    filters.push_back(popN(filters, 1)[0]->negate());
}

void ParsedQuery::parseStatsAndOrLine(std::string_view line,
                                      const LogicalConnective &connective) {
    auto number = nextNonNegativeIntegerArgument(line);
    auto v = popN(stats_columns, number) |  // TODO(sp): simplify with C++23
             std::views::transform([](auto &c) { return c->stealFilter(); });
    stats_columns.push_back(std::make_unique<StatsColumnCount>(
        connective(Filter::Kind::stats, Filters{v.begin(), v.end()})));
}

void ParsedQuery::parseStatsNegateLine(std::string_view line) {
    checkNoArguments(line);
    stats_columns.push_back(std::make_unique<StatsColumnCount>(
        popN(stats_columns, 1)[0]->stealFilter()->negate()));
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
        return sqrt((sum_of_squares_ / count_) - (mean * mean));
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

// NOLINTNEXTLINE(cert-err58-cpp)
const std::map<std::string_view, AggregationFactory> stats_ops{
    {"sum"sv, []() { return std::make_unique<SumAggregation>(); }},
    {"min"sv, []() { return std::make_unique<MinAggregation>(); }},
    {"max"sv, []() { return std::make_unique<MaxAggregation>(); }},
    {"avg"sv, []() { return std::make_unique<AvgAggregation>(); }},
    {"std"sv, []() { return std::make_unique<StdAggregation>(); }},
    {"suminv"sv, []() { return std::make_unique<SumInvAggregation>(); }},
    {"avginv"sv, []() { return std::make_unique<AvgInvAggregation>(); }}};
}  // namespace

void ParsedQuery::parseStatsLine(std::string_view line,
                                 const ColumnCreator &make_column) {
    // The first token is either the column name or the aggregation operator.
    auto col_or_aggr = nextStringArgument(line);
    auto it = stats_ops.find(col_or_aggr);
    if (it == stats_ops.end()) {
        auto column_name = std::string{col_or_aggr};
        auto rel_op = relationalOperatorForName(nextStringArgument(line));
        line.remove_prefix(
            std::min(line.size(), line.find_first_not_of(mk::whitespace)));
        auto value = std::string{line};
        stats_columns.push_back(std::make_unique<StatsColumnCount>(
            make_column(column_name)
                ->createFilter(Filter::Kind::stats, rel_op, value)));
        all_column_names.insert(column_name);
    } else {
        auto aggregation_factory = it->second;
        auto column_name = std::string{nextStringArgument(line)};
        stats_columns.push_back(std::make_unique<StatsColumnOp>(
            aggregation_factory, make_column(column_name)));
        all_column_names.insert(column_name);
    }
    // Default to old behaviour: do not output column headers if we do Stats
    // queries
    show_column_headers = false;
}

void ParsedQuery::parseFilterLine(std::string_view line, FilterStack &filters,
                                  const ColumnCreator &make_column) {
    auto column_name = std::string{nextStringArgument(line)};
    auto rel_op = relationalOperatorForName(nextStringArgument(line));
    line.remove_prefix(
        std::min(line.size(), line.find_first_not_of(mk::whitespace)));
    auto value = std::string{line};
    filters.push_back(make_column(column_name)
                          ->createFilter(Filter::Kind::row, rel_op, value));
    all_column_names.insert(column_name);
}

void ParsedQuery::parseAuthUserHeader(std::string_view line) { user = line; }

void ParsedQuery::parseColumnsLine(std::string_view line,
                                   const ColumnCreator &make_column) {
    while (!line.empty()) {
        auto column_name =
            std::string{line.substr(0, line.find_first_of(mk::whitespace))};
        line.remove_prefix(std::min(
            line.size(),
            line.find_first_not_of(mk::whitespace, column_name.size())));
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

void ParsedQuery::parseSeparatorsLine(std::string_view line) {
    const std::string dsep =
        std::string(1, static_cast<char>(nextNonNegativeIntegerArgument(line)));
    const std::string fsep =
        std::string(1, static_cast<char>(nextNonNegativeIntegerArgument(line)));
    const std::string lsep =
        std::string(1, static_cast<char>(nextNonNegativeIntegerArgument(line)));
    const std::string hsep =
        std::string(1, static_cast<char>(nextNonNegativeIntegerArgument(line)));
    separators = CSVSeparators{dsep, fsep, lsep, hsep};
}

namespace {
// NOLINTNEXTLINE(cert-err58-cpp)
const std::map<std::string_view, OutputFormat> formats{
    {"CSV"sv, OutputFormat::csv},
    {"csv"sv, OutputFormat::broken_csv},
    {"json"sv, OutputFormat::json},
    {"python"sv, OutputFormat::python3},  // just an alias, deprecate?
    {"python3"sv, OutputFormat::python3}};
}  // namespace

void ParsedQuery::parseOutputFormatLine(std::string_view line) {
    auto value = nextStringArgument(line);
    auto it = formats.find(value);
    if (it == formats.end()) {
        std::string msg;
        for (const auto &entry : formats) {
            msg += std::string{msg.empty() ? "" : ", "} + "'" +
                   std::string{entry.first} + "'";
        }
        throw std::runtime_error("missing/invalid output format, use one of " +
                                 msg);
    }
    output_format = it->second;
}

void ParsedQuery::parseColumnHeadersLine(std::string_view line) {
    auto value = nextStringArgument(line);
    if (value == "on"sv) {
        show_column_headers = true;
    } else if (value == "off"sv) {
        show_column_headers = false;
    } else {
        throw std::runtime_error("expected 'on' or 'off'");
    }
}

void ParsedQuery::parseKeepAliveLine(std::string_view line) {
    auto value = nextStringArgument(line);
    if (value == "on"sv) {
        keepalive = true;
    } else if (value == "off"sv) {
        keepalive = false;
    } else {
        throw std::runtime_error("expected 'on' or 'off'");
    }
}

void ParsedQuery::parseResponseHeaderLine(std::string_view line) {
    auto value = nextStringArgument(line);
    if (value == "off"sv) {
        response_header = OutputBuffer::ResponseHeader::off;
    } else if (value == "fixed16"sv) {
        response_header = OutputBuffer::ResponseHeader::fixed16;
    } else {
        throw std::runtime_error("expected 'off' or 'fixed16'");
    }
}

void ParsedQuery::parseLimitLine(std::string_view line) {
    limit = nextNonNegativeIntegerArgument(line);
}

void ParsedQuery::parseTimelimitLine(std::string_view line) {
    auto duration = std::chrono::seconds{nextNonNegativeIntegerArgument(line)};
    time_limit = {duration, std::chrono::steady_clock::now() + duration};
}

void ParsedQuery::parseWaitTimeoutLine(std::string_view line) {
    wait_timeout =
        std::chrono::milliseconds(nextNonNegativeIntegerArgument(line));
}

void ParsedQuery::parseWaitTriggerLine(std::string_view line) {
    wait_trigger = Triggers::find(std::string{nextStringArgument(line)});
}

void ParsedQuery::parseWaitObjectLine(std::string_view line) {
    wait_object = line;
}

void ParsedQuery::parseLocaltimeLine(std::string_view line) {
    // Compute the offset to be *added* each time we output our time and
    // *subtracted* from reference value by filter headers. We round the
    // difference to half an hour because we assume that both clocks are more or
    // less synchronized and that the time offset is only caused by being in
    // different time zones.
    using namespace std::chrono;
    auto offset{round<duration<seconds::rep, std::ratio<1800>>>(
        system_clock::from_time_t(nextNonNegativeIntegerArgument(line)) -
        system_clock::now())};
    if (abs(offset) >= 24h) {
        throw std::runtime_error{
            "timezone difference greater than or equal to 24 hours"};
    }
    timezone_offset = offset;
}

void ParsedQuery::parseOrderBy(std::string_view line,
                               const ColumnCreator &make_column) {
    // Use this header as: `OrderBy: COLUMN_NAME [asc,desc]`
    auto column = mk::next_argument(line);
    mk::skip_whitespace(line);
    auto direction = [line]() {
        if (line.empty() || line == "asc"sv) {
            return OrderByDirection::ascending;
        }
        if (line == "desc"sv) {
            return OrderByDirection::descending;
        }
        throw std::runtime_error("expected 'asc' or 'desc'");
    };
    auto dot = column.find('.');
    order_by.push_back(
        dot == std::string_view::npos
            ? OrderBy{.column = make_column(column),
                      .key = {},
                      .direction = direction()}
            : OrderBy{.column = make_column(column.substr(0, dot)),
                      .key = column.substr(dot + 1),
                      .direction = direction()});
}
