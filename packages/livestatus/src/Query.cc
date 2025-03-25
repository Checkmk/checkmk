// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/Query.h"

#include <algorithm>
#include <compare>
#include <cstddef>
#include <sstream>
#include <stdexcept>
#include <utility>
#include <variant>

#include "livestatus/Aggregator.h"
#include "livestatus/ChronoUtils.h"
#include "livestatus/Column.h"
#include "livestatus/ICore.h"
#include "livestatus/Logger.h"
#include "livestatus/OutputBuffer.h"
#include "livestatus/Row.h"
#include "livestatus/Sorter.h"
#include "livestatus/StatsColumn.h"
#include "livestatus/StringUtils.h"
#include "livestatus/Table.h"
#include "livestatus/Triggers.h"

using namespace std::chrono_literals;

Query::Query(ParsedQuery parsed_query, Table &table, ICore &core,
             OutputBuffer &output)
    : parsed_query_{std::move(parsed_query)}
    , table_{table}
    , core_{core}
    , output_{output}
    , renderer_{makeRenderer(output_.os())}
    , query_renderer_{*renderer_, EmitBeginEnd::on}
    , current_line_{0} {
    // NOTE: Doing this in the initializer list above leads to a segfault with
    // clang-tidy-17's bugprone-unchecked-optional-access, there are various
    // issues like this on https://github.com/llvm/llvm-project/issues.
    user_ = parsed_query_.user ? core_.find_user(*parsed_query_.user)
                               : std::make_unique<NoAuthUser>();
}

void Query::badRequest(const std::string &message) const {
    output_.setError(OutputBuffer::ResponseCode::bad_request, message);
}

void Query::payloadTooLarge(const std::string &message) const {
    output_.setError(OutputBuffer::ResponseCode::payload_too_large, message);
}

void Query::invalidRequest(const std::string &message) const {
    output_.setError(OutputBuffer::ResponseCode::invalid_request, message);
}

void Query::badGateway(const std::string &message) const {
    output_.setError(OutputBuffer::ResponseCode::bad_gateaway, message);
}

Logger *Query::logger() const { return core_.loggerLivestatus(); }

bool Query::doStats() const { return !parsed_query_.stats_columns.empty(); }

bool Query::hasOrderBy() const { return !parsed_query_.order_by.empty(); }

const OrderBy &Query::orderBy() const {
    // We only handle a single OrderBy
    return parsed_query_.order_by[0];
}

bool Query::process() {
    output_.setResponseHeader(parsed_query_.response_header);
    if (parsed_query_.error) {
        badRequest(*parsed_query_.error);
    }
    // Precondition: output has been reset
    auto start_time = std::chrono::system_clock::now();
    doWait();
    if (parsed_query_.show_column_headers) {
        renderColumnHeaders();
    }
    table_.answerQuery(*this, *user_, core_);
    if (hasOrderBy()) {
        renderSorters();
    }
    // Non-Stats queries output all rows directly, so there's nothing left
    // to do in that case.
    if (doStats()) {
        renderAggregators();
    }
    auto elapsed_ms = mk::ticks<std::chrono::milliseconds>(
        std::chrono::system_clock::now() - start_time);
    Informational(core_.loggerLivestatus())
        << "processed request in " << elapsed_ms << " ms, replied with "
        << output_.os().tellp() << " bytes";
    return parsed_query_.keepalive;
}

std::unique_ptr<Renderer> Query::makeRenderer(std::ostream &os) {
    return Renderer::make(parsed_query_.output_format, os, output_.getLogger(),
                          parsed_query_.separators, core_.dataEncoding());
}

void Query::renderColumnHeaders() {
    RowRenderer r{query_renderer_};
    for (const auto &column : parsed_query_.columns) {
        r.output(column->name());
    }

    // Output dummy headers for stats columns
    for (size_t col = 1; col <= parsed_query_.stats_columns.size(); ++col) {
        r.output("stats_" + std::to_string(col));
    }
}

bool Query::timelimitReached() const {
    if (!parsed_query_.time_limit) {
        return false;
    }
    const auto &[duration, timeout] = *parsed_query_.time_limit;
    if (std::chrono::steady_clock::now() >= timeout) {
        payloadTooLarge(
            "Maximum query time of " +
            std::to_string(mk::ticks<std::chrono::seconds>(duration)) +
            " seconds exceeded!");
        return true;
    }
    return false;
}

bool Query::processDataset(Row row) {
    if (output_.shouldTerminate()) {
        // Not the perfect response code, but good enough...
        payloadTooLarge("core is shutting down");
        return false;
    }

    if (static_cast<size_t>(output_.os().tellp()) > core_.maxResponseSize()) {
        payloadTooLarge("Maximum response size of " +
                        std::to_string(core_.maxResponseSize()) +
                        " bytes exceeded!");
        return false;
    }

    if (!parsed_query_.filter->accepts(row, *user_,
                                       parsed_query_.timezone_offset)) {
        return true;
    }

    if (!hasOrderBy() && parsed_query_.limit &&
        ++current_line_ > *parsed_query_.limit) {
        // `hasOrderBy()` needs to process the whole dataset to sort it.
        return false;
    }

    // When we reach the time limit we let the query fail. Otherwise the user
    // will not know that the answer is incomplete.
    if (timelimitReached()) {
        return false;
    }

    if (doStats()) {
        for (const auto &aggregator : getAggregatorsFor(row)) {
            aggregator->consume(row, *user_, parsed_query_.timezone_offset);
        }
    } else if (hasOrderBy()) {
        // Query::getAggregatorsFor(Row)
        std::ostringstream os{};
        {
            auto renderer = makeRenderer(os);
            QueryRenderer q{*renderer, EmitBeginEnd::off};
            renderColumns(row, q);
        }
        const RowFragment row_fragment{os.str()};

        const auto order_by = orderBy();
        try {
            const auto sorter = order_by.column->createSorter();
            const auto key = sorter->getKey(row, order_by.key, *user_,
                                            parsed_query_.timezone_offset);

            sorted_rows_.emplace_back(key, row_fragment);
        } catch (const std::runtime_error &e) {
            Error(logger()) << "invalid request: " << e.what();
            return false;
        }
    } else {
        renderColumns(row, query_renderer_);
    }
    return true;
}

void Query::renderSorters() {
    // See also Query::renderAggregators()
    const auto &o = orderBy();
    std::ranges::sort(sorted_rows_, [&o](auto &&x, auto &&y) {
        return o.direction == OrderByDirection::ascending ? x < y : x > y;
    });
    for (auto &&[k, row_fragment] : sorted_rows_) {
        if (parsed_query_.limit && ++current_line_ > *parsed_query_.limit) {
            break;
        }
        RowRenderer r{query_renderer_};
        r.output(row_fragment);
    }
}

void Query::renderAggregators() {
    if (stats_groups_.empty()) {
        // We have a Stats query, but no row has passed filtering etc., so we
        // have to create a dummy RowFragment and a stats group for it.
        getAggregatorsFor(Row{nullptr});
    }
    for (const auto &[row_fragment, aggregators] : stats_groups_) {
        RowRenderer r{query_renderer_};
        if (!parsed_query_.columns.empty()) {
            r.output(row_fragment);
        }
        for (const auto &aggregator : aggregators) {
            aggregator->output(r);
        }
    }
}

std::unique_ptr<Filter> Query::partialFilter(
    const std::string &message, columnNamePredicate predicate) const {
    auto result = parsed_query_.filter->partialFilter(std::move(predicate));
    Debug(core_.loggerLivestatus())
        << "partial filter for " << message << ": " << *result;
    return result;
}

std::optional<std::string> Query::stringValueRestrictionFor(
    const std::string &column_name) const {
    auto result = parsed_query_.filter->stringValueRestrictionFor(column_name);
    if (result) {
        Debug(core_.loggerLivestatus())
            << "column " << table_.name() << "." << column_name
            << " is restricted to '" << *result << "'";
    } else {
        Debug(core_.loggerLivestatus()) << "column " << table_.name() << "."
                                        << column_name << " is unrestricted";
    }
    return result;
}

std::optional<int32_t> Query::greatestLowerBoundFor(
    const std::string &column_name) const {
    auto result = parsed_query_.filter->greatestLowerBoundFor(
        column_name, parsed_query_.timezone_offset);
    if (result) {
        Debug(core_.loggerLivestatus())
            << "column " << table_.name() << "." << column_name
            << " has greatest lower bound " << *result << " ("
            << FormattedTimePoint(
                   std::chrono::system_clock::from_time_t(*result))
            << ")";
    } else {
        Debug(core_.loggerLivestatus())
            << "column " << table_.name() << "." << column_name
            << " has no greatest lower bound";
    }
    return result;
}

std::optional<int32_t> Query::leastUpperBoundFor(
    const std::string &column_name) const {
    auto result = parsed_query_.filter->leastUpperBoundFor(
        column_name, parsed_query_.timezone_offset);
    if (result) {
        Debug(core_.loggerLivestatus())
            << "column " << table_.name() << "." << column_name
            << " has least upper bound " << *result << " ("
            << FormattedTimePoint(
                   std::chrono::system_clock::from_time_t(*result))
            << ")";
    } else {
        Debug(core_.loggerLivestatus())
            << "column " << table_.name() << "." << column_name
            << " has no least upper bound";
    }
    return result;
}

std::optional<std::bitset<32>> Query::valueSetLeastUpperBoundFor(
    const std::string &column_name) const {
    auto result = parsed_query_.filter->valueSetLeastUpperBoundFor(
        column_name, parsed_query_.timezone_offset);
    if (result) {
        Debug(core_.loggerLivestatus())
            << "column " << table_.name() << "." << column_name
            << " has possible values " << FormattedBitSet<32>{*result};
    } else {
        Debug(core_.loggerLivestatus())
            << "column " << table_.name() << "." << column_name
            << " has no value set restriction";
    }
    return result;
}

const std::unordered_set<std::string> &Query::allColumnNames() const {
    return parsed_query_.all_column_names;
}

void Query::renderColumns(Row row, QueryRenderer &q) const {
    RowRenderer r{q};
    for (const auto &column : parsed_query_.columns) {
        column->output(row, r, *user_, parsed_query_.timezone_offset);
    }
}

// Things get a bit tricky here: For stats queries, we have to combine rows with
// the same values in the non-stats columns. But when we finally output those
// non-stats columns in finish(), we don't have the row anymore, so we can't use
// Column::output() then. :-/ The slightly hacky workaround is to pre-render all
// non-stats columns into a single string here (RowFragment) and output it later
// in a verbatim manner.
const std::vector<std::unique_ptr<Aggregator>> &Query::getAggregatorsFor(
    Row row) {
    std::ostringstream os;
    {
        auto renderer = makeRenderer(os);
        QueryRenderer q{*renderer, EmitBeginEnd::off};
        renderColumns(row, q);
    }
    const RowFragment row_fragment{os.str()};
    auto it = stats_groups_.find(row_fragment);
    if (it == stats_groups_.end()) {
        std::vector<std::unique_ptr<Aggregator>> aggregators;
        aggregators.reserve(parsed_query_.stats_columns.size());
        for (const auto &sc : parsed_query_.stats_columns) {
            aggregators.push_back(
                sc->createAggregator(core_.loggerLivestatus()));
        }
        it = stats_groups_.emplace(row_fragment, std::move(aggregators)).first;
    }
    return it->second;
}

void Query::doWait() {
    if (parsed_query_.wait_condition->is_contradiction() &&
        parsed_query_.wait_timeout == 0ms) {
        invalidRequest("waiting for WaitCondition would hang forever");
        return;
    }

    Row wait_object{nullptr};
    if (parsed_query_.wait_object) {
        wait_object = table_.get(*parsed_query_.wait_object, core_);
        if (wait_object.isNull()) {
            invalidRequest("primary key '" + *parsed_query_.wait_object +
                           "' not found or not supported by table '" +
                           table_.name() + "'");
            return;
        }
    }

    if (!parsed_query_.wait_condition->is_tautology() && wait_object.isNull()) {
        wait_object = table_.getDefault(core_);
        if (wait_object.isNull()) {
            invalidRequest("missing WaitObject");
            return;
        }
    }

    core_.triggers().wait_for(parsed_query_.wait_trigger,
                              parsed_query_.wait_timeout, [this, &wait_object] {
                                  return parsed_query_.wait_condition->accepts(
                                      wait_object, *user_,
                                      parsed_query_.timezone_offset);
                              });
}
