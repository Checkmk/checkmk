// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/Query.h"

#include <algorithm>
#include <cassert>
#include <compare>
#include <cstddef>
#include <sstream>
#include <utility>

#include "livestatus/Aggregator.h"
#include "livestatus/ChronoUtils.h"
#include "livestatus/Column.h"
#include "livestatus/ICore.h"
#include "livestatus/Logger.h"
#include "livestatus/OutputBuffer.h"
#include "livestatus/Row.h"
#include "livestatus/StatsColumn.h"
#include "livestatus/StringUtils.h"
#include "livestatus/Table.h"
#include "livestatus/Triggers.h"

using namespace std::chrono_literals;

Query::Query(ParsedQuery parsed_query, Table &table, ICore &core,
             OutputBuffer &output)
    : parsed_query_{std::move(parsed_query)}
    , _table{table}
    , core_{core}
    , _output{output}
    , _renderer_query{nullptr}
    , _current_line{0} {
    // NOTE: Doing this in the initializer list above leads to a segfault with
    // clang-tidy-17's bugprone-unchecked-optional-access, there are various
    // issues like this on https://github.com/llvm/llvm-project/issues.
    user_ = parsed_query_.user ? core_.find_user(*parsed_query_.user)
                               : std::make_unique<NoAuthUser>();
}

void Query::badRequest(const std::string &message) const {
    _output.setError(OutputBuffer::ResponseCode::bad_request, message);
}

void Query::payloadTooLarge(const std::string &message) const {
    _output.setError(OutputBuffer::ResponseCode::payload_too_large, message);
}

void Query::invalidRequest(const std::string &message) const {
    _output.setError(OutputBuffer::ResponseCode::invalid_request, message);
}

void Query::badGateway(const std::string &message) const {
    _output.setError(OutputBuffer::ResponseCode::bad_gateaway, message);
}

bool Query::doStats() const { return !parsed_query_.stats_columns.empty(); }

bool Query::process() {
    _output.setResponseHeader(parsed_query_.response_header);
    if (parsed_query_.error) {
        badRequest(*parsed_query_.error);
    }
    // Precondition: output has been reset
    auto start_time = std::chrono::system_clock::now();
    auto renderer = Renderer::make(
        parsed_query_.output_format, _output.os(), _output.getLogger(),
        parsed_query_.separators, core_.dataEncoding());
    doWait();
    QueryRenderer q(*renderer, EmitBeginEnd::on);
    // TODO(sp) The construct below is horrible, refactor this!
    _renderer_query = &q;
    start(q);
    _table.answerQuery(*this, *user_, core_);
    finish(q);
    auto elapsed_ms = mk::ticks<std::chrono::milliseconds>(
        std::chrono::system_clock::now() - start_time);
    Informational(core_.loggerLivestatus())
        << "processed request in " << elapsed_ms << " ms, replied with "
        << _output.os().tellp() << " bytes";
    return parsed_query_.keepalive;
}

void Query::start(QueryRenderer &q) {
    if (parsed_query_.columns.empty()) {
        getAggregatorsFor({});
    }
    if (parsed_query_.show_column_headers) {
        RowRenderer r(q);
        for (const auto &column : parsed_query_.columns) {
            r.output(column->name());
        }

        // Output dummy headers for stats columns
        for (size_t col = 1; col <= parsed_query_.stats_columns.size(); ++col) {
            r.output("stats_" + std::to_string(col));
        }
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
    if (_output.shouldTerminate()) {
        // Not the perfect response code, but good enough...
        payloadTooLarge("core is shutting down");
        return false;
    }

    if (static_cast<size_t>(_output.os().tellp()) > core_.maxResponseSize()) {
        payloadTooLarge("Maximum response size of " +
                        std::to_string(core_.maxResponseSize()) +
                        " bytes exceeded!");
        return false;
    }

    if (!parsed_query_.filter->accepts(row, *user_,
                                       parsed_query_.timezone_offset)) {
        return true;
    }

    _current_line++;
    if (parsed_query_.limit >= 0 &&
        static_cast<int>(_current_line) > parsed_query_.limit) {
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
            auto renderer = Renderer::make(
                parsed_query_.output_format, os, _output.getLogger(),
                parsed_query_.separators, core_.dataEncoding());
            QueryRenderer q(*renderer, EmitBeginEnd::off);
            RowRenderer r(q);
            for (const auto &column : parsed_query_.columns) {
                column->output(row, r, *user_, parsed_query_.timezone_offset);
            }
        }
        for (const auto &aggr : getAggregatorsFor(RowFragment{os.str()})) {
            aggr->consume(row, *user_, parsed_query_.timezone_offset);
        }
    } else {
        assert(_renderer_query);  // Missing call to `process()`.
        RowRenderer r(*_renderer_query);
        for (const auto &column : parsed_query_.columns) {
            column->output(row, r, *user_, parsed_query_.timezone_offset);
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
            << "column " << _table.name() << "." << column_name
            << " is restricted to '" << *result << "'";
    } else {
        Debug(core_.loggerLivestatus()) << "column " << _table.name() << "."
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
            << "column " << _table.name() << "." << column_name
            << " has greatest lower bound " << *result << " ("
            << FormattedTimePoint(
                   std::chrono::system_clock::from_time_t(*result))
            << ")";
    } else {
        Debug(core_.loggerLivestatus())
            << "column " << _table.name() << "." << column_name
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
            << "column " << _table.name() << "." << column_name
            << " has least upper bound " << *result << " ("
            << FormattedTimePoint(
                   std::chrono::system_clock::from_time_t(*result))
            << ")";
    } else {
        Debug(core_.loggerLivestatus())
            << "column " << _table.name() << "." << column_name
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
            << "column " << _table.name() << "." << column_name
            << " has possible values " << FormattedBitSet<32>{*result};
    } else {
        Debug(core_.loggerLivestatus())
            << "column " << _table.name() << "." << column_name
            << " has no value set restriction";
    }
    return result;
}

const std::unordered_set<std::string> &Query::allColumnNames() const {
    return parsed_query_.all_column_names;
}

const std::vector<std::unique_ptr<Aggregator>> &Query::getAggregatorsFor(
    const RowFragment &groupspec) {
    auto it = _stats_groups.find(groupspec);
    if (it == _stats_groups.end()) {
        std::vector<std::unique_ptr<Aggregator>> aggrs;
        aggrs.reserve(parsed_query_.stats_columns.size());
        for (const auto &sc : parsed_query_.stats_columns) {
            aggrs.push_back(sc->createAggregator(core_.loggerLivestatus()));
        }
        it = _stats_groups.emplace(groupspec, std::move(aggrs)).first;
    }
    return it->second;
}

void Query::doWait() {
    if (parsed_query_.wait_condition->is_contradiction() &&
        parsed_query_.wait_timeout == 0ms) {
        invalidRequest("waiting for WaitCondition would hang forever");
        return;
    }
    auto wait_object = parsed_query_.wait_object;
    if (!parsed_query_.wait_condition->is_tautology() && wait_object.isNull()) {
        wait_object = _table.getDefault(core_);
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
