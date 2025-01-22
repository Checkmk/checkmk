// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef Query_h
#define Query_h

#include <bitset>
#include <chrono>
#include <cstdint>
#include <iosfwd>
#include <iterator>
#include <map>
#include <memory>
#include <optional>
#include <string>
#include <unordered_set>
#include <utility>
#include <vector>

#include "livestatus/Aggregator.h"  // IWYU pragma: keep
#include "livestatus/Filter.h"
#include "livestatus/ParsedQuery.h"
#include "livestatus/Renderer.h"
#include "livestatus/Sorter.h"
#include "livestatus/User.h"

class ICore;
class OutputBuffer;
class Row;
class Table;
class Logger;

class Query {
public:
    Query(ParsedQuery parsed_query, Table &table, ICore &core,
          OutputBuffer &output);

    bool process();

    // NOTE: We cannot make this 'const' right now, it increments current_line_
    // and calls the non-const getAggregatorsFor() member function.
    bool processDataset(Row row);

    bool timelimitReached() const;

    void badRequest(const std::string &message) const;
    void payloadTooLarge(const std::string &message) const;
    void invalidRequest(const std::string &message) const;
    void badGateway(const std::string &message) const;

    std::chrono::seconds timezoneOffset() const {
        return parsed_query_.timezone_offset;
    }

    std::unique_ptr<Filter> partialFilter(const std::string &message,
                                          columnNamePredicate predicate) const;
    std::optional<std::string> stringValueRestrictionFor(
        const std::string &column_name) const;
    std::optional<int32_t> greatestLowerBoundFor(
        const std::string &column_name) const;
    std::optional<int32_t> leastUpperBoundFor(
        const std::string &column_name) const;
    std::optional<std::bitset<32>> valueSetLeastUpperBoundFor(
        const std::string &column_name) const;

    const std::unordered_set<std::string> &allColumnNames() const;

private:
    const ParsedQuery parsed_query_;
    Table &table_;
    ICore &core_;
    OutputBuffer &output_;
    std::unique_ptr<const User> user_;

    std::unique_ptr<Renderer> renderer_;
    QueryRenderer query_renderer_;
    int current_line_;
    std::map<RowFragment, std::vector<std::unique_ptr<Aggregator>>>
        stats_groups_;
    std::vector<std::pair<Sorter::key_type, RowFragment>> sorted_rows_;

    [[nodiscard]] Logger *logger() const;
    bool doStats() const;
    bool hasOrderBy() const;
    [[nodiscard]] const OrderBy &orderBy() const;
    std::unique_ptr<Renderer> makeRenderer(std::ostream &os);
    void renderColumnHeaders();
    void renderSorters();
    void renderAggregators();
    void doWait();

    // NOTE: We cannot make this 'const' right now, it adds entries into
    // stats_groups_.
    const std::vector<std::unique_ptr<Aggregator>> &getAggregatorsFor(Row row);

    void renderColumns(Row row, QueryRenderer &q) const;
};

#endif  // Query_h
